"""Combines route lookup, capacity filtering and pricing into one result.

Everything here is deterministic. The LLM never feeds back into this module.
"""

from __future__ import annotations

import logging
import time

from models import (
    AircraftCategory,
    AircraftOption,
    Preference,
    Reason,
    ReasonKind,
    RecommendationResult,
    RouteLookup,
    RouteMatchStatus,
    SourceReference,
    TripRequest,
)
from services.aircraft_service import AircraftCatalog, get_aircraft_catalog
from services.pricing_service import (
    STANDARD_CAVEATS,
    calculate_price_breakdown,
    format_usd,
    leg_price,
)
from services.route_service import RouteRepository, get_route_repository

logger = logging.getLogger("flygreen.recommendation")

ADVISOR_ITEMS: tuple[str, ...] = (
    "Live aircraft and operator availability for your dates",
    "Final pricing, taxes and airport/handling fees",
    "Exact airports, routing, flight time and any fuel stops",
    "Baggage, cabin and onboard requirements",
    "Operator safety credentials for the specific flight",
)


def _select_categories(
    pool: list[AircraftCategory],
    preference: Preference,
    price_of: dict[AircraftCategory, int | None],
) -> list[tuple[AircraftCategory, str]]:
    """Return [(category, role label)] according to the documented app rules."""
    if not pool:
        return []
    # Cheapest published category; if none are priced, the smallest suitable one.
    base = min(pool, key=lambda c: (price_of.get(c) is None, price_of.get(c) or 0, c.rank))
    larger = sorted((c for c in pool if c.rank > base.rank), key=lambda c: c.rank)

    base_label = "Lowest indicative price" if price_of.get(base) is not None else "Smallest suitable category"
    alt_label = "Larger-category alternative"

    if preference is Preference.LOWEST_PRICE:
        return [(base, base_label)] + [(c, alt_label) for c in larger[:1]]
    if preference is Preference.MORE_SPACE:
        # Next larger published category first; cheapest kept as the alternative.
        if not larger:
            return [(base, base_label + " (only suitable category)")]
        return [(larger[0], "Larger category (your preference)"), (base, base_label)]
    # BALANCED: cheapest plus up to two larger categories for comparison.
    return [(base, base_label)] + [(c, alt_label) for c in larger[:2]]


def recommend(
    request: TripRequest,
    routes: RouteRepository | None = None,
    catalog: AircraftCatalog | None = None,
) -> RecommendationResult:
    started = time.perf_counter()
    routes = routes or get_route_repository()
    catalog = catalog or get_aircraft_catalog()

    outbound: RouteLookup = routes.lookup(request.origin, request.destination)
    return_leg: RouteLookup | None = (
        routes.lookup(request.destination, request.origin) if request.return_enabled else None
    )

    warnings: list[str] = []
    reasons: list[Reason] = []

    # ---- route facts ----------------------------------------------------
    if outbound.status is RouteMatchStatus.EXACT_MATCH:
        reasons.append(Reason(ReasonKind.PUBLISHED_DATA,
                              f"Exact route match: {request.origin} → {request.destination} is listed "
                              "in Popular Route Estimates (one-way, USD)."))
    elif outbound.status is RouteMatchStatus.REVERSE_MATCH:
        assert outbound.estimate is not None
        warnings.append(outbound.direction_note or "")
        reasons.append(Reason(ReasonKind.PUBLISHED_DATA,
                              f"Reverse-direction match: the source lists {outbound.estimate.origin} → "
                              f"{outbound.estimate.destination}. Shown as an indicative reference only."))
    else:
        warnings.append(
            f"No published estimate exists for {request.origin} ↔ {request.destination}. "
            "No route price is shown, and none has been estimated. A Flygreen advisor can quote this trip."
        )
        reasons.append(Reason(ReasonKind.APP_RULE,
                              "Prices are shown only for city pairs on the published list; "
                              "unlisted routes are never estimated."))

    if return_leg is not None:
        if return_leg.status is RouteMatchStatus.REVERSE_MATCH and outbound.status is not RouteMatchStatus.NO_PUBLISHED_ESTIMATE:
            warnings.append(
                "Return leg: " + (return_leg.direction_note or "")
            )
        reasons.append(Reason(ReasonKind.APP_RULE,
                              "The return leg is looked up in its own direction first; the opposite-direction "
                              "listing is used only when no direction-specific value is published, and is labelled."))

    # ---- capacity -------------------------------------------------------
    suitable = catalog.suitable_categories(request.passengers)
    reasons.append(Reason(ReasonKind.APP_RULE,
                          f"Capacity check: only models whose listed passenger capacity is at least "
                          f"{request.passengers} are shown."))

    price_of = {c: leg_price(outbound, c) for c in AircraftCategory}
    has_route = outbound.status is not RouteMatchStatus.NO_PUBLISHED_ESTIMATE

    if has_route:
        priced_pool = [c for c in suitable if price_of[c] is not None]
        unpriced = [c for c in suitable if price_of[c] is None]
        if unpriced and priced_pool:
            names = ", ".join(c.label for c in unpriced)
            warnings.append(f"The source shows N/A (no published estimate) for {names} on this route, "
                            "so those categories are not offered here.")
            reasons.append(Reason(ReasonKind.PUBLISHED_DATA,
                                  f"{names}: listed as N/A on this route by the source."))
        pool = priced_pool or suitable
        if suitable and not priced_pool:
            warnings.append("None of the categories that fit your group has a published estimate on this route.")
    else:
        pool = suitable

    reasons.append(Reason(ReasonKind.APP_RULE,
                          f"Preference “{request.preferences.label}” changes which categories are shown first. "
                          "It is a preference, not a guarantee."))

    options: list[AircraftOption] = []
    if not suitable:
        warnings.append(
            f"The curated demo catalogue has no listed model for {request.passengers} passengers "
            f"(largest listed capacity: {catalog.max_capacity}). An advisor must review this request; "
            "Flygreen's wider network is not represented in this demo."
        )
    else:
        for category, role in _select_categories(pool, request.preferences, price_of):
            models = catalog.example_models(request.passengers, category)
            pricing = calculate_price_breakdown(outbound, return_leg, category)
            why = tuple(
                f"{m.model_name}: listed capacity {m.passenger_capacity} passengers supports "
                f"{request.passengers} passenger{'s' if request.passengers != 1 else ''}."
                for m in models
            )
            limitations = [
                "Example model only - not confirmed available for your date.",
                "Luggage, cabin size, range and amenities are not verified in this demo.",
            ]
            if pricing.outbound_estimate is None:
                limitations.append("No published route estimate for this category.")
            options.append(
                AircraftOption(
                    category=category,
                    aircraft=models,
                    category_estimate=pricing.outbound_estimate,
                    pricing=pricing,
                    why_it_matches=why,
                    limitations=tuple(limitations),
                    role=role,
                )
            )
            if request.return_enabled and pricing.outbound_estimate is not None and pricing.estimated_total is None:
                warnings.append(
                    f"{category.label}: a complete round-trip estimate cannot be calculated from the "
                    "published data (only one leg has a published estimate)."
                )

    reasons.extend(Reason(ReasonKind.ADVISOR, item) for item in ADVISOR_ITEMS)

    result = RecommendationResult(
        request=request,
        route_match_status=outbound.status,
        route_direction_note=outbound.direction_note,
        outbound_route=outbound,
        return_route=return_leg,
        options=tuple(options),
        pricing=options[0].pricing if options else None,
        warnings=tuple(w for w in dict.fromkeys(warnings) if w),
        reasons=tuple(reasons),
        hourly_reference_rates=dict(routes.hourly_rates),
        source_references=(
            SourceReference("Flygreen Popular Route Estimates (snapshot " + routes.curated_on + ")", routes.source_url),
            SourceReference("Flygreen Aircraft Guide (snapshot " + catalog.curated_on + ")", catalog.source_url),
        ),
        max_listed_capacity=catalog.max_capacity,
        caveats=STANDARD_CAVEATS,
    )
    logger.info(
        "recommendation status=%s options=%d return=%s elapsed_ms=%.1f",
        result.status.value, len(options), request.return_enabled, (time.perf_counter() - started) * 1000,
    )
    return result


STATUS_TEXT = {
    "exact_match": "Exact published route",
    "reverse_match": "Published route (opposite direction - indicative reference)",
    "no_published_estimate": "No published estimate for this route",
    "no_capacity_match": "No listed model fits this group",
}


def build_trip_summary(result: RecommendationResult) -> str:
    """Plain-text, copyable summary built only from deterministic data."""
    r = result.request
    lines = [
        "AI Charter Trip Planner - indicative summary (independent demo concept)",
        f"Route: {r.origin} → {r.destination} ({r.trip_type})",
        f"Departure: {r.departure_date.isoformat()}",
    ]
    if r.return_enabled and r.return_date:
        lines.append(f"Return: {r.return_date.isoformat()}")
    lines += [
        f"Passengers: {r.passengers}",
        f"Preference: {r.preferences.label}",
        f"Match status: {STATUS_TEXT[result.status.value]}",
    ]
    if result.route_direction_note:
        lines.append(f"Note: {result.route_direction_note}")
    if result.options:
        lines.append("Options (USD, published one-way estimates):")
        for opt in result.options:
            models = ", ".join(f"{m.model_name} ({m.passenger_capacity} pax listed)" for m in opt.aircraft)
            p = opt.pricing
            lines.append(f"- {opt.category.label} [{opt.role}]: {models}")
            lines.append(f"  Outbound: {format_usd(p.outbound_estimate)}")
            if r.return_enabled:
                lines.append(f"  Return leg: {format_usd(p.return_estimate)}")
                total = format_usd(p.estimated_total) if p.estimated_total is not None else "Cannot be calculated from published data"
                lines.append(f"  Combined indicative total: {total}")
    else:
        lines.append("Options: none - advisor review required.")
    lines.append("Caveats: " + " ".join(result.caveats))
    lines.append("Sources: " + "; ".join(f"{s.title} {s.url}" for s in result.source_references))
    lines.append("Not a quote or booking. Confirm everything with a Flygreen advisor.")
    return "\n".join(lines)
