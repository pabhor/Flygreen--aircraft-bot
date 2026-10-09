"""Aircraft recommendation engine - weighted multi-criteria scoring.

Hard rules: an aircraft is never suggested if it has fewer seats than the group, or (on an
ocean crossing) if its listed range cannot cover the flight nonstop. Everything else is a
weighted score whose weights shift with what the customer asked for (luxury, luggage, value...).
Prices are average category prices from the CSV database, never invented.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from services.charter_db import CharterDB, RouteInfo
from services.nlp import TripNeeds

TAXI_CLIMB_HOURS = 0.4
DEFAULT_TRIP_HOURS = 2.0   # used only to illustrate a price when no route or duration is known

BASE_WEIGHTS = {"budget": 0.30, "fit": 0.25, "comfort": 0.12, "range": 0.13, "baggage": 0.08, "lavatory": 0.08, "speed": 0.04}
NEED_BOOSTS = {
    "value": {"budget": 0.35},
    "luxury": {"comfort": 0.4, "lavatory": 0.1, "fit": -0.15},
    "business": {"comfort": 0.1, "lavatory": 0.05},
    "baggage": {"baggage": 0.35},
    "lavatory": {"lavatory": 0.3},
    "family": {"lavatory": 0.15, "fit": 0.1, "baggage": 0.1},
    "long_haul": {"comfort": 0.2, "lavatory": 0.15, "range": 0.15},
    "speed": {"speed": 0.25, "range": 0.1},
    "nonstop": {"range": 0.3},
}


@dataclass(frozen=True)
class PriceQuote:
    amount: int
    basis: str            # "route_average" | "hourly_estimate"
    source: str           # "published" | "sample_estimate"
    hours: float | None
    hourly_rate: int


@dataclass(frozen=True)
class Candidate:
    slug: str
    model_name: str
    category: str
    category_label: str
    passengers: int
    max_range_hours: float
    baggage_cuft: float
    cabin: str
    lavatory: str
    image_url: str
    detail_url: str
    description: str
    price: PriceQuote
    fuel_stops: int
    score: float
    within_budget: bool | None
    reasons: tuple[str, ...]
    role: str = ""        # "Best match" | "Upgrade" | "Best value"


@dataclass(frozen=True)
class Recommendation:
    needs: TripNeeds
    route: RouteInfo | None
    picks: tuple[Candidate, ...]
    over_budget_only: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def best(self) -> Candidate | None:
        return self.picks[0] if self.picks else None


def _norm(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    return (series - lo) / (hi - lo) if hi > lo else pd.Series(1.0, index=series.index)


def _lavatory_score(value: str) -> float:
    v = (value or "").lower()
    if "full" in v or "enclosed" in v:
        return 1.0
    if "partial" in v:
        return 0.35
    return 0.5


def _fmt_usd(n: int) -> str:
    return f"${n:,.0f}"


def weights_for(needs: frozenset[str]) -> dict[str, float]:
    w = dict(BASE_WEIGHTS)
    for need in needs:
        for k, boost in NEED_BOOSTS.get(need, {}).items():
            w[k] += boost
    w = {k: max(v, 0.03) for k, v in w.items()}
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def _cabin_text(row: pd.Series) -> str:
    if pd.isna(row.cabin_height_ft) or pd.isna(row.cabin_length_ft):
        return "Not listed"
    return f"{row.cabin_height_ft:g}' h x {row.cabin_width_ft:g}' w x {row.cabin_length_ft:g}' l"


def build_candidates(db: CharterDB, needs: TripNeeds) -> tuple[pd.DataFrame, RouteInfo | None, list[str]]:
    """Every aircraft that passes the hard rules, with price, stops and raw features."""
    notes: list[str] = []
    df = db.aircraft.copy()
    if needs.passengers:
        df = df[df.passengers >= needs.passengers]
        if df.empty:
            notes.append(f"No aircraft in the guide seats {needs.passengers}; the largest seats {db.max_capacity}.")
            return df, None, notes

    route = db.route(needs.origin, needs.destination) if needs.origin and needs.destination else None
    rates = db.profiles["hourly_rate_usd"]
    cruise = db.profiles["cruise_kts"]

    if route:
        prices = db.route_prices(route.origin, route.destination)
        offered = prices[(prices.feasible == 1) & prices.avg_price_usd.notna()].set_index("category")
        df = df[df.category.isin(offered.index)].copy()
        df["price"] = df.category.map(offered.avg_price_usd).astype(int)
        df["price_source"] = df.category.map(offered.price_source)
        df["hours"] = df.category.map(offered.est_flight_hours)
        airborne = route.distance_nm / df.category.map(cruise) + TAXI_CLIMB_HOURS
        df["fuel_stops"] = [max(0, math.ceil(a / r) - 1) for a, r in zip(airborne, df.max_range_hours)]
        df["range_cover"] = (df.max_range_hours / airborne).clip(upper=2.0) / 2.0
        if route.crosses_ocean:
            before = len(df)
            df = df[df.fuel_stops == 0]
            if before and df.empty:
                notes.append("No aircraft that fits your group can make this ocean crossing nonstop.")
        df["basis"] = "route_average"
    else:
        hours = needs.flight_hours or DEFAULT_TRIP_HOURS
        df["hours"] = hours
        df["price"] = [int(round(rates[c] * hours / 500.0) * 500) for c in df.category]
        df["price_source"] = df.category.map(db.profiles["rate_source"])
        df["fuel_stops"] = [max(0, math.ceil((hours - TAXI_CLIMB_HOURS) / r) - 1) if needs.flight_hours else 0
                            for r in df.max_range_hours]
        df["range_cover"] = (df.max_range_hours / max(hours, 1)).clip(upper=2.0) / 2.0
        df["basis"] = "hourly_estimate"
        if needs.flight_hours and (df.fuel_stops == 0).any():
            df = df[df.fuel_stops == 0] if "nonstop" in needs.needs else df
    df["speed"] = df.category.map(cruise)
    return df, route, notes


def score(df: pd.DataFrame, needs: TripNeeds) -> pd.DataFrame:
    w = weights_for(needs.needs)
    df = df.copy()
    volume = (df.cabin_height_ft.fillna(df.cabin_height_ft.median())
              * df.cabin_width_ft.fillna(df.cabin_width_ft.median())
              * df.cabin_length_ft.fillna(df.cabin_length_ft.median()))
    comfort = 0.6 * _norm(volume) + 0.4 * _norm(df.cabin_height_ft.fillna(df.cabin_height_ft.median()))
    pax = needs.passengers or 2
    spare = (df.passengers - pax).clip(lower=0)
    fit = (-(spare - 2).clip(lower=0) / 3.5).apply(math.exp)   # up to 2 spare seats is ideal; empty seats cost money
    if needs.budget_usd:
        over = (df.price - needs.budget_usd).clip(lower=0) / needs.budget_usd
        budget = (1 - 3 * over).clip(lower=0) * (0.75 + 0.25 * (1 - df.price / max(needs.budget_usd, 1)).clip(lower=0))
    else:
        budget = 1 - _norm(df.price)
    df["s_budget"], df["s_comfort"], df["s_fit"] = budget, comfort, fit
    df["s_range"] = df.range_cover * (1 - 0.5 * (df.fuel_stops > 0))
    # Enough luggage room per passenger is what matters - more than enough adds nothing.
    per_pax = 15 if "baggage" in needs.needs else 8
    df["s_baggage"] = (df.baggage_cuft.fillna(df.baggage_cuft.median()) / (pax * per_pax)).clip(upper=1.0)
    df["s_lavatory"] = df.lavatory.map(_lavatory_score)
    df["s_speed"] = _norm(df.speed)
    df["score"] = sum(w[k] * df[f"s_{k}"] for k in w)
    return df.sort_values(["score", "price"], ascending=[False, True])


def reasons_for(row: pd.Series, needs: TripNeeds, route: RouteInfo | None) -> tuple[str, ...]:
    out = []
    pax = needs.passengers
    if pax:
        spare = int(row.passengers) - pax
        out.append(f"{int(row.passengers)} seats - room for your {pax}" + (f" plus {spare} to spare" if spare else ""))
    else:
        out.append(f"Seats up to {int(row.passengers)} passengers")
    price = _fmt_usd(int(row.price))
    if needs.budget_usd:
        diff = needs.budget_usd - int(row.price)
        out.append(f"{price} average - {_fmt_usd(diff)} under your {_fmt_usd(needs.budget_usd)} budget" if diff >= 0
                   else f"{price} average - {_fmt_usd(-diff)} above your {_fmt_usd(needs.budget_usd)} budget")
    if route:
        out.append(f"Nonstop: {row.max_range_hours:g} h range covers this {row.hours:g} h flight" if row.fuel_stops == 0
                   else f"{int(row.fuel_stops)} quick fuel stop on this route")
    elif "nonstop" in needs.needs or "long_haul" in needs.needs:
        out.append(f"Up to {row.max_range_hours:g} hours nonstop range")
    if {"luxury", "business", "long_haul"} & needs.needs and not pd.isna(row.cabin_height_ft):
        out.append(f"{row.cabin_height_ft:g} ft cabin height, {row.cabin_length_ft:g} ft long cabin")
    if {"baggage", "family"} & needs.needs and not pd.isna(row.baggage_cuft):
        out.append(f"{row.baggage_cuft:g} ft³ baggage space")
    if ({"lavatory", "family", "long_haul", "luxury"} & needs.needs) and row.lavatory:
        out.append(f"{row.lavatory} lavatory")
    return tuple(out[:5])


def _to_candidate(row: pd.Series, needs: TripNeeds, route: RouteInfo | None, db: CharterDB, role: str) -> Candidate:
    within = None if not needs.budget_usd else bool(row.price <= needs.budget_usd)
    return Candidate(
        slug=row.slug, model_name=row.model_name, category=row.category, category_label=row.category_label,
        passengers=int(row.passengers), max_range_hours=float(row.max_range_hours),
        baggage_cuft=float(row.baggage_cuft) if not pd.isna(row.baggage_cuft) else 0.0,
        cabin=_cabin_text(row), lavatory=row.lavatory or "Not listed", image_url=row.image_url,
        detail_url=row.detail_url, description=row.description,
        price=PriceQuote(int(row.price), row.basis, str(row.price_source),
                         float(row.hours) if not pd.isna(row.hours) else None,
                         int(db.profiles.at[row.category, "hourly_rate_usd"])),
        fuel_stops=int(row.fuel_stops), score=round(float(row.score), 3), within_budget=within,
        reasons=reasons_for(row, needs, route), role=role,
    )


def _next_size_up(df: pd.DataFrame, rank: int) -> pd.DataFrame:
    """Aircraft in the nearest larger category that is available - an upgrade is one step up."""
    larger = df[df.size_rank > rank]
    return larger[larger.size_rank == larger.size_rank.min()] if not larger.empty else larger


def recommend(db: CharterDB, needs: TripNeeds, exclude: set[str] | None = None,
              shift: str | None = None, anchor_slug: str | None = None) -> Recommendation:
    """shift: None | "cheaper" | "upgrade" - relative to ``anchor_slug`` (the last best pick)."""
    df, route, notes = build_candidates(db, needs)
    if df.empty:
        return Recommendation(needs, route, (), False, tuple(notes))
    if exclude:
        df = df[~df.slug.isin(exclude)] if len(df[~df.slug.isin(exclude)]) else df
    anchor = db.aircraft_by_slug(anchor_slug) if anchor_slug else None
    if shift and anchor is not None:
        anchor_price = df.loc[df.slug == anchor_slug, "price"]
        ref_price = int(anchor_price.iloc[0]) if len(anchor_price) else None
        if shift == "cheaper":
            sub = df[df.price < ref_price] if ref_price else df[df.size_rank < anchor["size_rank"]]
            if sub.empty:
                notes.append(f"The {anchor['model_name']} is already the most affordable option that fits.")
            else:
                df = sub
                needs = TripNeeds(**{**needs.__dict__, "needs": needs.needs | {"value"}})
        elif shift == "upgrade":
            sub = _next_size_up(df, anchor["size_rank"])
            if sub.empty:
                sub = df[(df.size_rank == anchor["size_rank"]) & (df.slug != anchor_slug)]
            if sub.empty:
                notes.append(f"The {anchor['model_name']} is already the largest category for this trip.")
            else:
                df = sub
                needs = TripNeeds(**{**needs.__dict__, "needs": needs.needs | {"luxury"}})

    ranked = score(df, needs)
    over_budget_only = False
    if needs.budget_usd:
        affordable = ranked[ranked.price <= needs.budget_usd]
        if affordable.empty:
            over_budget_only = True
            ranked = ranked.sort_values(["price", "score"], ascending=[True, False])  # closest to budget first
        elif needs.budget_is_cap:
            ranked = affordable

    best = ranked.iloc[0]
    picks = [_to_candidate(best, needs, route, db, "Best match")]
    upgrade = _next_size_up(ranked, best.size_rank)
    if upgrade.empty and not needs.budget_is_cap and not _next_size_up(df, best.size_rank).empty:
        upgrade = score(_next_size_up(df, best.size_rank), needs)
    if not upgrade.empty:
        picks.append(_to_candidate(upgrade.iloc[0], needs, route, db, "Upgrade"))
    value = ranked[(ranked.price < best.price) & (~ranked.slug.isin([p.slug for p in picks]))]
    if not value.empty:
        picks.append(_to_candidate(value.sort_values(["price", "score"], ascending=[True, False]).iloc[0],
                                   needs, route, db, "Best value"))
    elif len(ranked) > 1:
        alt = ranked[~ranked.slug.isin([p.slug for p in picks])]
        if not alt.empty and len(picks) < 3:
            picks.append(_to_candidate(alt.iloc[0], needs, route, db, "Alternative"))
    return Recommendation(needs, route, tuple(picks), over_budget_only, tuple(notes))


def compare(db: CharterDB, slugs: tuple[str, ...], needs: TripNeeds) -> list[Candidate]:
    df, route, _ = build_candidates(db, TripNeeds(**{**needs.__dict__, "passengers": None}))
    df = df[df.slug.isin(slugs)]
    if df.empty:
        return []
    ranked = score(df, needs)
    order = {s: i for i, s in enumerate(slugs)}
    rows = sorted((r for _, r in ranked.iterrows()), key=lambda r: order[r.slug])
    return [_to_candidate(r, needs, route, db, "") for r in rows]


def candidate_for(db: CharterDB, slug: str, needs: TripNeeds) -> Candidate | None:
    found = compare(db, (slug,), needs)
    return found[0] if found else None
