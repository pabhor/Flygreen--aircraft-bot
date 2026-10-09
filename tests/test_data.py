"""Integrity of the CSV database."""

import pandas as pd
import pytest

from config import DATA_DIR
from services.charter_db import CATEGORY_ORDER, get_db


@pytest.fixture(scope="module")
def db():
    return get_db()


def test_aircraft_table_is_complete(db):
    a = db.aircraft
    assert len(a) >= 60
    assert set(a.category) == set(CATEGORY_ORDER)
    assert a.slug.is_unique and (a.passengers > 0).all() and (a.max_range_hours > 0).all()
    assert a.image_url.str.startswith("https://www.flygreen.co/").all()


def test_every_directed_pair_has_a_price_row_per_category(db):
    n = len(db.cities())
    assert len(db.routes) == n * (n - 1)
    assert len(db.prices) == len(db.routes) * len(CATEGORY_ORDER)


def test_published_prices_are_used_verbatim(db):
    published = pd.read_csv(DATA_DIR / "published_routes.csv")
    for row in published.to_dict("records"):
        for o, d in ((row["origin"], row["destination"]), (row["destination"], row["origin"])):
            p = db.route_prices(o, d).set_index("category")
            for cat in ("light_jet", "mid_size_jet", "super_mid_size_jet", "heavy_jet"):
                if pd.isna(row[cat]):
                    assert pd.isna(p.at[cat, "avg_price_usd"])
                else:
                    assert p.at[cat, "avg_price_usd"] == row[cat]
                    assert p.at[cat, "price_source"] == "published"


def test_prices_rise_with_aircraft_size_on_every_route(db):
    m = db.prices.dropna(subset=["avg_price_usd"]).copy()
    m["rank"] = m.category.map(db.profiles.size_rank)
    for _, grp in m.sort_values("rank").groupby("route_id"):
        assert grp.avg_price_usd.is_monotonic_increasing


def test_ocean_crossings_only_offer_heavy_and_long_range(db):
    p = db.route_prices("New York", "London")
    offered = set(p[p.feasible == 1].category)
    assert offered == {"heavy_jet", "long_range_jet"}
