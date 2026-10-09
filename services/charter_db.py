"""Read-only data access over the CSV "database" in ``data/``.

Tables (built by ``scraper.flygreen_scraper`` and ``scripts.build_sample_data``):
aircraft, category_profiles, cities, routes, route_prices.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from config import DATA_DIR

CATEGORY_ORDER = ["turboprop", "light_jet", "mid_size_jet", "super_mid_size_jet", "heavy_jet", "long_range_jet"]


@dataclass(frozen=True)
class RouteInfo:
    origin: str
    destination: str
    distance_nm: int
    crosses_ocean: bool
    published: bool  # any category on this pair comes from the published Flygreen table


class CharterDB:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.aircraft = pd.read_csv(data_dir / "aircraft.csv")
        self.profiles = pd.read_csv(data_dir / "category_profiles.csv").set_index("category")
        self.cities_df = pd.read_csv(data_dir / "cities.csv")
        self.routes = pd.read_csv(data_dir / "routes.csv")
        self.prices = pd.read_csv(data_dir / "route_prices.csv")
        self.prices["avg_price_usd"] = self.prices["avg_price_usd"].astype("Int64")
        self.aircraft["lavatory"] = self.aircraft["lavatory"].fillna("")
        self.aircraft["category_label"] = self.aircraft["category"].map(self.profiles["label"])
        self.aircraft["size_rank"] = self.aircraft["category"].map(self.profiles["size_rank"])
        self._route_index = self.routes.set_index(["origin", "destination"])
        self.scraped_on = str(self.aircraft["scraped_on"].iloc[0]) if len(self.aircraft) else ""

    # ----- cities & routes -------------------------------------------------
    def cities(self) -> list[str]:
        return sorted(self.cities_df["city"].tolist())

    def route(self, origin: str, destination: str) -> RouteInfo | None:
        key = (origin, destination)
        if key not in self._route_index.index:
            return None
        row = self._route_index.loc[key]
        sources = self.prices.loc[self.prices.route_id == row.route_id, "price_source"]
        return RouteInfo(origin, destination, int(row.distance_nm), bool(row.crosses_ocean),
                         bool(sources.isin(["published", "published_na"]).any()))

    def route_prices(self, origin: str, destination: str) -> pd.DataFrame:
        """One row per category with label, hours, stops, average price and source."""
        key = (origin, destination)
        if key not in self._route_index.index:
            return self.prices.iloc[0:0]
        route_id = self._route_index.loc[key, "route_id"]
        df = self.prices[self.prices.route_id == route_id].copy()
        df["label"] = df["category"].map(self.profiles["label"])
        df["size_rank"] = df["category"].map(self.profiles["size_rank"])
        return df.sort_values("size_rank").reset_index(drop=True)

    # ----- aircraft --------------------------------------------------------
    def aircraft_in(self, category: str | None = None) -> pd.DataFrame:
        df = self.aircraft if category is None else self.aircraft[self.aircraft.category == category]
        return df.sort_values(["size_rank", "passengers", "model_name"])

    def aircraft_by_slug(self, slug: str) -> dict | None:
        rows = self.aircraft[self.aircraft.slug == slug]
        return rows.iloc[0].to_dict() if len(rows) else None

    def category_label(self, category: str) -> str:
        return str(self.profiles.at[category, "label"])

    @property
    def max_capacity(self) -> int:
        return int(self.aircraft["passengers"].max())


@lru_cache(maxsize=1)
def get_db() -> CharterDB:
    return CharterDB()
