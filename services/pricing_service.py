"""One-way and return estimate calculations.

Only published numbers are used. No hourly-rate x duration maths, no
assumed symmetric pricing, and N/A is ``None`` - never zero.
"""

from __future__ import annotations

from models import AircraftCategory, PriceBreakdown, RouteLookup, RouteMatchStatus

STANDARD_CAVEATS: tuple[str, ...] = (
    "Published estimates exclude taxes.",
    "Airport fees vary and are not included.",
    "This is not a live quote.",
    "No aircraft, operator or date availability has been checked.",
)


def leg_price(lookup: RouteLookup | None, category: AircraftCategory) -> int | None:
    if lookup is None or lookup.estimate is None:
        return None
    return lookup.estimate.price_for(category)


def calculate_price_breakdown(
    outbound: RouteLookup,
    return_leg: RouteLookup | None,
    category: AircraftCategory,
) -> PriceBreakdown:
    """Build a breakdown for one category.

    ``return_leg`` must be a lookup in the return direction (destination ->
    origin) so that a direction-specific published value is used whenever one
    exists; only if it does not exist does the lookup fall back to the
    (disclosed) opposite-direction entry.
    """
    outbound_price = leg_price(outbound, category)
    caveats = list(STANDARD_CAVEATS)

    if outbound.status is RouteMatchStatus.REVERSE_MATCH:
        caveats.append("Outbound figure is the source's opposite-direction listing (indicative reference only).")

    if return_leg is None:
        return PriceBreakdown(
            outbound_estimate=outbound_price,
            return_estimate=None,
            estimated_total=outbound_price,
            outbound_match=outbound.status,
            return_match=None,
            caveats=tuple(caveats),
        )

    return_price = leg_price(return_leg, category)
    if return_leg.status is RouteMatchStatus.REVERSE_MATCH and return_price is not None:
        caveats.append("Return-leg figure is the source's opposite-direction listing (indicative reference only).")

    if outbound_price is not None and return_price is not None:
        total: int | None = outbound_price + return_price
    else:
        total = None
        if outbound_price is not None or return_price is not None:
            caveats.append(
                "A complete round-trip estimate cannot be calculated from the published data "
                "because only one leg has a published estimate for this category."
            )

    return PriceBreakdown(
        outbound_estimate=outbound_price,
        return_estimate=return_price,
        estimated_total=total,
        outbound_match=outbound.status,
        return_match=return_leg.status,
        caveats=tuple(caveats),
    )


def format_usd(amount: int | None) -> str:
    """Render a USD amount; ``None`` renders as unavailable, never $0."""
    if amount is None:
        return "Not published"
    return f"${amount:,.0f}"
