"""City normalization and exact / reverse route lookup.

Rules (spec §6):
* exact city-pair matching only - no fuzzy matching, no distance maths;
* a reverse-direction match is allowed but always flagged;
* an unlisted pair returns NO_PUBLISHED_ESTIMATE with no price at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from config import ROUTE_DATA_PATH
from models import AircraftCategory, RouteEstimate, RouteLookup, RouteMatchStatus

# Unambiguous aliases only. Keys are compared after casefold + whitespace collapse.
CITY_ALIASES: dict[str, str] = {
    "nyc": "New York",
    "new york city": "New York",
    "new york, ny": "New York",
    "new york ny": "New York",
    "los angeles, ca": "Los Angeles",
    "los angeles ca": "Los Angeles",
    "la": "Los Angeles",
    "las vegas, nv": "Las Vegas",
    "vegas": "Las Vegas",
    "phoenix, az": "Phoenix",
    "houston, tx": "Houston",
    "boston, ma": "Boston",
    "naples, fl": "Naples",
    "naples, florida": "Naples",
    "miami, fl": "Miami",
    "miami, florida": "Miami",
    "london, uk": "London",
    "london, england": "London",
    "london, united kingdom": "London",
    "nice, france": "Nice",
    "frankfurt am main": "Frankfurt",
    "frankfurt, germany": "Frankfurt",
    "paris, france": "Paris",
    "madrid, spain": "Madrid",
    "ibiza, spain": "Ibiza",
    "eivissa": "Ibiza",
    "milan, italy": "Milan",
    "milano": "Milan",
    "moscow, russia": "Moscow",
    "istanbul, turkey": "Istanbul",
    "istanbul, türkiye": "Istanbul",
    "nassau, bahamas": "Nassau",
    "rome, italy": "Rome",
    "roma": "Rome",
}

# Inputs we refuse to guess. Each maps to a user-facing explanation.
AMBIGUOUS_CITIES: dict[str, str] = {
    "florida": "“Florida” could mean South Florida, Miami or Naples - please choose one.",
    "fl": "“FL” could mean South Florida, Miami or Naples - please choose one.",
    "naples, italy": "The published Boston–Naples route is listed under US routes "
    "(Naples, Florida). Naples, Italy has no published estimate - choose another city "
    "or ask an advisor.",
    "napoli": "The published Boston–Naples route is listed under US routes "
    "(Naples, Florida). Naples, Italy has no published estimate - choose another city "
    "or ask an advisor.",
    "london, ontario": "Only London, UK appears in the published routes.",
    "london, on": "Only London, UK appears in the published routes.",
    "paris, texas": "Only Paris, France appears in the published routes.",
    "paris, tx": "Only Paris, France appears in the published routes.",
    "ny": "“NY” could mean the city or the state - please choose New York from the list.",
}

# Display hint for cities whose name alone could confuse a visitor.
CITY_HINTS: dict[str, str] = {
    "Naples": "Naples, Florida (listed under US routes)",
    "South Florida": "South Florida region",
}

_CITY_PATTERN = re.compile(r"^[^\W\d_][^\W_]*(?:[ .,'’()/-]+[^\W_]+)*[.)]?$", re.UNICODE)
MAX_CITY_CHARS = 60


class AmbiguousCityError(ValueError):
    """Raised when a typed city cannot be normalized safely."""


class InvalidCityError(ValueError):
    """Raised when a typed city is empty, too long or contains odd characters."""


@dataclass(frozen=True)
class NormalizedCity:
    name: str
    known: bool  # True if it appears in the published route list


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


class RouteRepository:
    """Read-only access to the curated route snapshot."""

    def __init__(
        self,
        routes: list[RouteEstimate],
        hourly_rates: dict[AircraftCategory, int],
        source_url: str,
        curated_on: str,
        source_caveat: str,
    ) -> None:
        self._routes = list(routes)
        self.hourly_rates = dict(hourly_rates)
        self.source_url = source_url
        self.curated_on = curated_on
        self.source_caveat = source_caveat
        self._index: dict[tuple[str, str], RouteEstimate] = {}
        for route in self._routes:
            pair = (_key(route.origin), _key(route.destination))
            if pair in self._index:
                raise ValueError(f"Duplicate route in dataset: {route.origin} -> {route.destination}")
            self._index[pair] = route
        self._cities = {_key(c): c for r in self._routes for c in (r.origin, r.destination)}

    # ----- data loading -------------------------------------------------
    @classmethod
    def from_json(cls, path: Path) -> RouteRepository:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        meta = raw["_meta"]
        routes = []
        for item in raw["routes"]:
            prices: dict[AircraftCategory, int | None] = {}
            for cat in AircraftCategory:
                value = item["category_prices"].get(cat.value)
                if value is not None and (not isinstance(value, int) or value <= 0):
                    raise ValueError(f"Invalid price for {item['origin']}->{item['destination']} {cat.value}")
                prices[cat] = value
            routes.append(
                RouteEstimate(
                    region=item["region"],
                    origin=item["origin"],
                    destination=item["destination"],
                    category_prices=prices,
                    source_url=item["source_url"],
                    price_basis=item.get("price_basis", "one_way_estimate"),
                )
            )
        rates = {AircraftCategory(k): int(v) for k, v in meta["hourly_reference_rates"].items()}
        return cls(routes, rates, meta["source_url"], meta["curated_on"], meta["source_caveat"])

    # ----- queries ------------------------------------------------------
    @property
    def routes(self) -> tuple[RouteEstimate, ...]:
        return tuple(self._routes)

    def known_cities(self) -> list[str]:
        return sorted(self._cities.values())

    def destinations_for(self, city: str) -> list[str]:
        """Cities with a published estimate to/from ``city`` (either direction)."""
        k = _key(city)
        out = set()
        for (o, d), r in self._index.items():
            if o == k:
                out.add(r.destination)
            elif d == k:
                out.add(r.origin)
        return sorted(out)

    def normalize_city(self, raw: str) -> NormalizedCity:
        if raw is None:
            raise InvalidCityError("City is required.")
        text = " ".join(str(raw).split())
        if not text:
            raise InvalidCityError("City is required.")
        if len(text) > MAX_CITY_CHARS:
            raise InvalidCityError(f"City must be {MAX_CITY_CHARS} characters or fewer.")
        if not _CITY_PATTERN.match(text):
            raise InvalidCityError("City may contain letters, spaces and basic punctuation only.")
        k = _key(text)
        if k in AMBIGUOUS_CITIES:
            raise AmbiguousCityError(AMBIGUOUS_CITIES[k])
        if k in self._cities:
            return NormalizedCity(self._cities[k], True)
        if k in CITY_ALIASES:
            return NormalizedCity(CITY_ALIASES[k], _key(CITY_ALIASES[k]) in self._cities)
        # Unknown: keep the user's text (cleaned) - it simply won't match a route.
        return NormalizedCity(text, False)

    def lookup(self, origin: str, destination: str) -> RouteLookup:
        o, d = _key(origin), _key(destination)
        exact = self._index.get((o, d))
        if exact is not None:
            return RouteLookup(RouteMatchStatus.EXACT_MATCH, exact, origin, destination)
        reverse = self._index.get((d, o))
        if reverse is not None:
            return RouteLookup(RouteMatchStatus.REVERSE_MATCH, reverse, origin, destination)
        return RouteLookup(RouteMatchStatus.NO_PUBLISHED_ESTIMATE, None, origin, destination)


@lru_cache(maxsize=1)
def get_route_repository() -> RouteRepository:
    return RouteRepository.from_json(ROUTE_DATA_PATH)
