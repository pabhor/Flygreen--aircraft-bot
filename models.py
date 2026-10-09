"""Typed domain models shared by every layer.

Plain frozen dataclasses keep the domain dependency-free and immutable.
Statuses are enums with stable string values; never infer status from text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class AircraftCategory(str, Enum):
    LIGHT_JET = "light_jet"
    MID_SIZE_JET = "mid_size_jet"
    SUPER_MID_SIZE_JET = "super_mid_size_jet"
    HEAVY_JET = "heavy_jet"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]

    @property
    def rank(self) -> int:
        """Size order as published (Light < Mid < Super Mid < Heavy)."""
        return CATEGORY_ORDER.index(self)


CATEGORY_ORDER: tuple[AircraftCategory, ...] = (
    AircraftCategory.LIGHT_JET,
    AircraftCategory.MID_SIZE_JET,
    AircraftCategory.SUPER_MID_SIZE_JET,
    AircraftCategory.HEAVY_JET,
)

CATEGORY_LABELS = {
    AircraftCategory.LIGHT_JET: "Light Jet",
    AircraftCategory.MID_SIZE_JET: "Mid-Size Jet",
    AircraftCategory.SUPER_MID_SIZE_JET: "Super Mid-Size Jet",
    AircraftCategory.HEAVY_JET: "Heavy Jet",
}


class RouteMatchStatus(str, Enum):
    EXACT_MATCH = "exact_match"
    REVERSE_MATCH = "reverse_match"
    NO_PUBLISHED_ESTIMATE = "no_published_estimate"


class MatchStatus(str, Enum):
    """Overall result status shown to the user."""

    EXACT_MATCH = "exact_match"
    REVERSE_MATCH = "reverse_match"
    NO_PUBLISHED_ESTIMATE = "no_published_estimate"
    NO_CAPACITY_MATCH = "no_capacity_match"


class Preference(str, Enum):
    LOWEST_PRICE = "lowest_price"
    MORE_SPACE = "more_space"
    BALANCED = "balanced"

    @property
    def label(self) -> str:
        return PREFERENCE_LABELS[self]


PREFERENCE_LABELS = {
    Preference.BALANCED: "Show balanced options",
    Preference.LOWEST_PRICE: "Lowest indicative price",
    Preference.MORE_SPACE: "More cabin space",
}


class ReasonKind(str, Enum):
    PUBLISHED_DATA = "Published data"
    APP_RULE = "App rule"
    ADVISOR = "Requires advisor confirmation"


@dataclass(frozen=True)
class TripRequest:
    origin: str
    destination: str
    departure_date: date
    passengers: int
    return_enabled: bool = False
    return_date: date | None = None
    preferences: Preference = Preference.BALANCED

    @property
    def trip_type(self) -> str:
        return "Round trip" if self.return_enabled else "One-way"


@dataclass(frozen=True)
class Aircraft:
    model_name: str
    category: AircraftCategory
    passenger_capacity: int
    source_url: str
    notes: str | None = None


@dataclass(frozen=True)
class RouteEstimate:
    region: str
    origin: str
    destination: str
    # None means the source shows "N/A": never treat it as $0.
    category_prices: dict[AircraftCategory, int | None]
    source_url: str
    price_basis: str = "one_way_estimate"

    def price_for(self, category: AircraftCategory) -> int | None:
        return self.category_prices.get(category)


@dataclass(frozen=True)
class RouteLookup:
    """Result of looking up one directional leg."""

    status: RouteMatchStatus
    estimate: RouteEstimate | None
    requested_origin: str
    requested_destination: str

    @property
    def direction_note(self) -> str | None:
        if self.status is RouteMatchStatus.REVERSE_MATCH and self.estimate:
            return (
                f"The source lists this city pair in the opposite direction "
                f"({self.estimate.origin} → {self.estimate.destination}). "
                f"Treat it as an indicative reference only."
            )
        return None


@dataclass(frozen=True)
class PriceBreakdown:
    outbound_estimate: int | None
    return_estimate: int | None
    estimated_total: int | None
    outbound_match: RouteMatchStatus
    return_match: RouteMatchStatus | None
    currency: str = "USD"
    price_basis: str = "one_way_estimate"
    caveats: tuple[str, ...] = ()


@dataclass(frozen=True)
class AircraftOption:
    category: AircraftCategory
    aircraft: tuple[Aircraft, ...]
    category_estimate: int | None
    pricing: PriceBreakdown
    why_it_matches: tuple[str, ...]
    limitations: tuple[str, ...]
    role: str  # e.g. "Lowest indicative price", "Larger-category alternative"


@dataclass(frozen=True)
class Reason:
    kind: ReasonKind
    text: str


@dataclass(frozen=True)
class SourceReference:
    title: str
    url: str


@dataclass(frozen=True)
class RecommendationResult:
    request: TripRequest
    route_match_status: RouteMatchStatus
    route_direction_note: str | None
    outbound_route: RouteLookup
    return_route: RouteLookup | None
    options: tuple[AircraftOption, ...]
    pricing: PriceBreakdown | None
    warnings: tuple[str, ...]
    reasons: tuple[Reason, ...]
    hourly_reference_rates: dict[AircraftCategory, int]
    source_references: tuple[SourceReference, ...]
    max_listed_capacity: int
    generated_explanation: str | None = None
    caveats: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status(self) -> MatchStatus:
        if not self.options:
            return MatchStatus.NO_CAPACITY_MATCH
        return MatchStatus(self.route_match_status.value)

    @property
    def has_published_estimate(self) -> bool:
        return self.route_match_status is not RouteMatchStatus.NO_PUBLISHED_ESTIMATE
