import pytest

from services.charter_db import get_db
from services.nlp import TripNeeds
from services.recommender import compare, recommend


@pytest.fixture(scope="module")
def db():
    return get_db()


def test_never_suggests_too_few_seats(db):
    for pax in (1, 4, 8, 13, 19):
        rec = recommend(db, TripNeeds(passengers=pax))
        assert rec.picks and all(p.passengers >= pax for p in rec.picks)


def test_group_larger_than_any_aircraft(db):
    rec = recommend(db, TripNeeds(passengers=40))
    assert rec.picks == () and "largest seats" in rec.notes[0]


def test_right_sizes_small_group_on_short_route(db):
    best = recommend(db, TripNeeds(passengers=4, origin="Miami", destination="Nassau")).best
    assert best.category in ("turboprop", "light_jet")


def test_route_price_comes_from_database(db):
    rec = recommend(db, TripNeeds(passengers=4, origin="New York", destination="South Florida"))
    prices = db.route_prices("New York", "South Florida").set_index("category").avg_price_usd
    for p in rec.picks:
        assert p.price.amount == prices[p.category] and p.price.basis == "route_average"


def test_ocean_crossing_requires_nonstop_heavy_or_long_range(db):
    rec = recommend(db, TripNeeds(passengers=6, origin="New York", destination="London"))
    assert all(p.category in ("heavy_jet", "long_range_jet") and p.fuel_stops == 0 for p in rec.picks)
    assert rec.best.price.amount == 95_000


def test_hard_budget_cap_is_respected(db):
    rec = recommend(db, TripNeeds(passengers=4, budget_usd=12_000, budget_is_cap=True,
                                  origin="New York", destination="Miami"))
    assert rec.picks and all(p.price.amount <= 12_000 for p in rec.picks)


def test_impossible_budget_leads_with_closest_option(db):
    rec = recommend(db, TripNeeds(passengers=4, budget_usd=3_000, origin="New York", destination="Miami"))
    assert rec.over_budget_only
    assert rec.best.price.amount == min(p.price.amount for p in rec.picks)


def test_luxury_and_baggage_needs_change_the_pick(db):
    base = recommend(db, TripNeeds(passengers=6, flight_hours=3)).best
    lux = recommend(db, TripNeeds(passengers=6, flight_hours=3, needs=frozenset({"luxury"}))).best
    assert lux.price.amount > base.price.amount


def test_cheaper_and_upgrade_move_relative_to_anchor(db):
    needs = TripNeeds(passengers=4, origin="Miami", destination="Nassau")
    best = recommend(db, needs).best
    cheaper = recommend(db, needs, shift="cheaper", anchor_slug=best.slug).best
    upgrade = recommend(db, needs, shift="upgrade", anchor_slug=best.slug).best
    assert cheaper.price.amount < best.price.amount
    assert upgrade.price.amount > best.price.amount


def test_compare_keeps_requested_order(db):
    out = compare(db, ("citation-cj3", "phenom-300"), TripNeeds())
    assert [c.slug for c in out] == ["citation-cj3", "phenom-300"]
