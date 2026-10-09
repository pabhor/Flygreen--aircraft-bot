"""Capacity filtering and category matching over the curated aircraft subset.

Hard rule: a model is NEVER returned when passengers > its listed capacity.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from config import AIRCRAFT_DATA_PATH
from models import CATEGORY_ORDER, Aircraft, AircraftCategory

MAX_MODELS_PER_CATEGORY = 2


class AircraftCatalog:
    def __init__(self, aircraft: list[Aircraft], source_url: str, curated_on: str) -> None:
        self._aircraft = tuple(aircraft)
        self.source_url = source_url
        self.curated_on = curated_on

    @classmethod
    def from_json(cls, path: Path) -> AircraftCatalog:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        items = []
        seen = set()
        for item in raw["aircraft"]:
            capacity = item["passenger_capacity"]
            if not isinstance(capacity, int) or capacity < 1:
                raise ValueError(f"Invalid capacity for {item.get('model_name')}")
            name = item["model_name"].strip()
            if name.casefold() in seen:
                raise ValueError(f"Duplicate aircraft model: {name}")
            seen.add(name.casefold())
            items.append(
                Aircraft(
                    model_name=name,
                    category=AircraftCategory(item["category"]),
                    passenger_capacity=capacity,
                    source_url=item["source_url"],
                    notes=item.get("notes"),
                )
            )
        return cls(items, raw["_meta"]["source_url"], raw["_meta"]["curated_on"])

    @property
    def aircraft(self) -> tuple[Aircraft, ...]:
        return self._aircraft

    @property
    def max_capacity(self) -> int:
        return max((a.passenger_capacity for a in self._aircraft), default=0)

    def models_that_fit(self, passengers: int, category: AircraftCategory | None = None) -> list[Aircraft]:
        """All models whose listed capacity >= passengers (optionally in one category)."""
        if passengers < 1:
            raise ValueError("passengers must be >= 1")
        return [
            a
            for a in self._aircraft
            if a.passenger_capacity >= passengers and (category is None or a.category is category)
        ]

    def suitable_categories(self, passengers: int) -> list[AircraftCategory]:
        """Categories (in size order) with at least one model that fits."""
        fitting = {a.category for a in self.models_that_fit(passengers)}
        return [c for c in CATEGORY_ORDER if c in fitting]

    def example_models(
        self, passengers: int, category: AircraftCategory, limit: int = MAX_MODELS_PER_CATEGORY
    ) -> tuple[Aircraft, ...]:
        """Up to ``limit`` fitting models, closest capacity fit first, then by name."""
        models = sorted(
            self.models_that_fit(passengers, category),
            key=lambda a: (a.passenger_capacity, a.model_name.casefold()),
        )
        return tuple(models[:limit])


@lru_cache(maxsize=1)
def get_aircraft_catalog() -> AircraftCatalog:
    return AircraftCatalog.from_json(AIRCRAFT_DATA_PATH)
