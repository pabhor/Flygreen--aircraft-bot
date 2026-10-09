"""Build the sample route/price database from the scraped CSVs.

Inputs (from ``python -m scraper.flygreen_scraper``):
    data/aircraft.csv, data/published_routes.csv, data/hourly_rates.csv
Outputs:
    data/cities.csv             24 cities with coordinates
    data/category_profiles.csv  label, cruise speed, hourly rate, size rank per category
    data/routes.csv             every directed city pair with distance
    data/route_prices.csv       per route x category: hours, fuel stops, average price, source

Pricing model (sample data, clearly labelled):
* Published Flygreen estimates are used verbatim wherever the city pair is listed
  (either direction) - ``price_source = published``.
* Everything else is ``hours x published hourly rate x calibration factor``, where the
  factor is fitted per category so the model reproduces the published routes, and
  rounded to the nearest $500 - ``price_source = sample_estimate``.
* Transatlantic pairs are only offered for heavy and long-range jets (as published).

Run:  python -m scripts.build_sample_data
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CITIES = [
    # city, country, region, continent, lat, lon
    ("New York", "USA", "US", "Americas", 40.71, -74.01),
    ("Boston", "USA", "US", "Americas", 42.36, -71.06),
    ("Chicago", "USA", "US", "Americas", 41.88, -87.63),
    ("South Florida", "USA", "US", "Americas", 26.12, -80.14),
    ("Miami", "USA", "US", "Americas", 25.76, -80.19),
    ("Naples", "USA", "US", "Americas", 26.14, -81.79),
    ("Houston", "USA", "US", "Americas", 29.76, -95.37),
    ("Aspen", "USA", "US", "Americas", 39.19, -106.82),
    ("Phoenix", "USA", "US", "Americas", 33.45, -112.07),
    ("Las Vegas", "USA", "US", "Americas", 36.17, -115.14),
    ("Los Angeles", "USA", "US", "Americas", 34.05, -118.24),
    ("San Francisco", "USA", "US", "Americas", 37.77, -122.42),
    ("Nassau", "Bahamas", "Caribbean", "Americas", 25.04, -77.35),
    ("London", "UK", "Europe", "Europe", 51.51, -0.13),
    ("Paris", "France", "Europe", "Europe", 48.86, 2.35),
    ("Nice", "France", "Europe", "Europe", 43.70, 7.27),
    ("Geneva", "Switzerland", "Europe", "Europe", 46.20, 6.14),
    ("Frankfurt", "Germany", "Europe", "Europe", 50.11, 8.68),
    ("Milan", "Italy", "Europe", "Europe", 45.46, 9.19),
    ("Rome", "Italy", "Europe", "Europe", 41.90, 12.50),
    ("Madrid", "Spain", "Europe", "Europe", 40.42, -3.70),
    ("Ibiza", "Spain", "Europe", "Europe", 38.91, 1.43),
    ("Istanbul", "Turkey", "Europe", "Europe", 41.01, 28.98),
    ("Moscow", "Russia", "Europe", "Europe", 55.76, 37.62),
]

# category, label, cruise speed (kts), size rank, sample hourly rate when none is published
CATEGORY_PROFILES = [
    ("turboprop", "Turboprop", 280, 0, 1800),
    ("light_jet", "Light Jet", 400, 1, None),
    ("mid_size_jet", "Mid-Size Jet", 430, 2, None),
    ("super_mid_size_jet", "Super Mid-Size Jet", 460, 3, None),
    ("heavy_jet", "Heavy Jet", 475, 4, None),
    ("long_range_jet", "Long Range Jet", 490, 5, 8500),
]
OCEAN_CATEGORIES = {"heavy_jet", "long_range_jet"}
TURBOPROP_MAX_NM = 1000
ROUTING_FACTOR = 1.05       # airways are longer than great-circle
TAXI_CLIMB_HOURS = 0.4
FUEL_STOP_HOURS = 0.75
MIN_BILLABLE_HOURS = 1.5


def great_circle_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3440.065 * 2 * math.asin(math.sqrt(a))


def round_500(x: float) -> int:
    return int(round(x / 500.0) * 500)


def main() -> None:
    aircraft = pd.read_csv(DATA_DIR / "aircraft.csv")
    published = pd.read_csv(DATA_DIR / "published_routes.csv")
    rates = dict(pd.read_csv(DATA_DIR / "hourly_rates.csv").itertuples(index=False, name=None))

    # ---- category profiles ------------------------------------------------
    typical_range = aircraft.groupby("category")["max_range_hours"].median().to_dict()
    profiles = pd.DataFrame(
        [
            {
                "category": key, "label": label, "cruise_kts": kts, "size_rank": rank,
                "hourly_rate_usd": rates.get(key, sample_rate),
                "rate_source": "published" if key in rates else "sample_estimate",
                "typical_range_hours": round(float(typical_range.get(key, 0)), 1),
            }
            for key, label, kts, rank, sample_rate in CATEGORY_PROFILES
        ]
    )
    prof = profiles.set_index("category")

    # ---- cities & routes ---------------------------------------------------
    cities = pd.DataFrame(CITIES, columns=["city", "country", "region", "continent", "lat", "lon"])
    c = cities.set_index("city")
    routes = []
    for o in cities.city:
        for d in cities.city:
            if o == d:
                continue
            nm = great_circle_nm(c.at[o, "lat"], c.at[o, "lon"], c.at[d, "lat"], c.at[d, "lon"]) * ROUTING_FACTOR
            routes.append({
                "route_id": f"{o}|{d}".lower().replace(" ", "-"), "origin": o, "destination": d,
                "distance_nm": round(nm), "crosses_ocean": int(c.at[o, "continent"] != c.at[d, "continent"]),
            })
    routes = pd.DataFrame(routes)

    def flight(cat: str, nm: float) -> tuple[float, int]:
        airborne = nm / prof.at[cat, "cruise_kts"] + TAXI_CLIMB_HOURS
        stops = max(0, math.ceil(airborne / prof.at[cat, "typical_range_hours"]) - 1)
        return round(airborne + stops * FUEL_STOP_HOURS, 1), stops

    # ---- calibrate against published estimates ------------------------------
    pub_lookup: dict[tuple[str, str], dict] = {}
    for row in published.to_dict("records"):
        for pair in ((row["origin"], row["destination"]), (row["destination"], row["origin"])):
            pub_lookup[pair] = row
    r_idx = routes.set_index(["origin", "destination"])
    factors = {}
    for cat in rates:
        model_sum = pub_sum = 0.0
        for row in published.to_dict("records"):
            if pd.isna(row.get(cat)) or (row["origin"], row["destination"]) not in r_idx.index:
                continue
            hours, _ = flight(cat, r_idx.loc[(row["origin"], row["destination"]), "distance_nm"])
            model_sum += max(hours, MIN_BILLABLE_HOURS) * rates[cat]
            pub_sum += row[cat]
        factors[cat] = float(pub_sum / model_sum) if model_sum else 1.0
    # Unpublished categories borrow the factor of their nearest published neighbour.
    factors.setdefault("turboprop", factors["light_jet"])
    factors.setdefault("long_range_jet", factors["heavy_jet"])
    print("calibration factors:", {k: round(v, 2) for k, v in factors.items()})

    def from_published(pub: dict, cat: str) -> int | None:
        """Price an unlisted category on a published pair from the nearest published category,
        scaled by the hourly-rate ratio, so the published ordering is preserved."""
        rank = prof.at[cat, "size_rank"]
        listed = [k for k in rates if not pd.isna(pub.get(k))]
        if not listed:
            return None
        anchor = min(listed, key=lambda k: abs(prof.at[k, "size_rank"] - rank))
        return round_500(pub[anchor] * prof.at[cat, "hourly_rate_usd"] / prof.at[anchor, "hourly_rate_usd"])

    # ---- prices ------------------------------------------------------------
    prices = []
    for r in routes.itertuples(index=False):
        pub = pub_lookup.get((r.origin, r.destination))
        for cat in prof.index:
            hours, stops = flight(cat, r.distance_nm)
            feasible = True
            if r.crosses_ocean and cat not in OCEAN_CATEGORIES:
                feasible = False
            if cat == "turboprop" and r.distance_nm > TURBOPROP_MAX_NM:
                feasible = False
            if pub is not None and cat in pub:
                value = pub[cat]
                price = int(value) if not pd.isna(value) else None
                source = "published" if price is not None else "published_na"
                feasible = price is not None
            elif feasible and pub is not None:
                price = from_published(pub, cat)
                source = "sample_estimate" if price is not None else "not_offered"
                feasible = price is not None
            elif feasible:
                rate = prof.at[cat, "hourly_rate_usd"]
                price = round_500(max(hours, MIN_BILLABLE_HOURS) * rate * factors[cat])
                source = "sample_estimate"
            else:
                price, source = None, "not_offered"
            prices.append({
                "route_id": r.route_id, "category": cat, "est_flight_hours": hours, "fuel_stops": stops,
                "avg_price_usd": price, "price_source": source, "feasible": int(feasible),
            })
    prices = pd.DataFrame(prices)
    prices["avg_price_usd"] = prices["avg_price_usd"].astype("Int64")

    cities.to_csv(DATA_DIR / "cities.csv", index=False)
    profiles.to_csv(DATA_DIR / "category_profiles.csv", index=False)
    routes.to_csv(DATA_DIR / "routes.csv", index=False)
    prices.to_csv(DATA_DIR / "route_prices.csv", index=False)
    print(f"cities={len(cities)} routes={len(routes)} route_prices={len(prices)} "
          f"published={int((prices.price_source == 'published').sum())}")


if __name__ == "__main__":
    main()
