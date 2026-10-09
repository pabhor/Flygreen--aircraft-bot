"""Boundary validation: raw form values in, a typed TripRequest (or errors) out."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from config import UI_MAX_PASSENGERS
from models import Preference, TripRequest
from services.route_service import AmbiguousCityError, InvalidCityError, RouteRepository


@dataclass
class ValidationOutcome:
    request: TripRequest | None
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.request is not None and not self.errors


def validate_trip_input(
    repo: RouteRepository,
    *,
    origin: str | None,
    destination: str | None,
    departure_date: date | None,
    passengers: object,
    return_enabled: bool,
    return_date: date | None,
    preference: Preference | str | None,
    today: date | None = None,
) -> ValidationOutcome:
    """Validate and normalize. Field keys in ``errors`` match form field names."""
    errors: dict[str, str] = {}
    today = today or date.today()

    norm_origin = norm_dest = None
    for field_name, raw in (("origin", origin), ("destination", destination)):
        try:
            norm = repo.normalize_city(raw or "")
        except (AmbiguousCityError, InvalidCityError) as exc:
            errors[field_name] = str(exc)
            continue
        if field_name == "origin":
            norm_origin = norm
        else:
            norm_dest = norm

    if norm_origin and norm_dest and norm_origin.name.casefold() == norm_dest.name.casefold():
        errors["destination"] = "Arrival city must be different from the departure city."

    if not isinstance(departure_date, date):
        errors["departure_date"] = "Departure date is required."
    elif departure_date < today:
        errors["departure_date"] = "Departure date cannot be in the past."

    pax: int | None = None
    if isinstance(passengers, bool) or not isinstance(passengers, int):
        errors["passengers"] = "Passengers must be a whole number."
    elif passengers < 1:
        errors["passengers"] = "At least 1 passenger is required."
    elif passengers > UI_MAX_PASSENGERS:
        errors["passengers"] = (
            f"This demo form accepts up to {UI_MAX_PASSENGERS} passengers. "
            "Larger groups need an advisor."
        )
    else:
        pax = passengers

    ret: date | None = None
    if return_enabled:
        if not isinstance(return_date, date):
            errors["return_date"] = "Return date is required for a round trip."
        elif isinstance(departure_date, date) and return_date < departure_date:
            errors["return_date"] = "Return date must be on or after the departure date."
        else:
            ret = return_date

    try:
        pref = Preference(preference) if preference is not None else Preference.BALANCED
    except ValueError:
        errors["preferences"] = "Unknown preference."
        pref = Preference.BALANCED

    if errors:
        return ValidationOutcome(None, errors)

    assert norm_origin and norm_dest and pax is not None and isinstance(departure_date, date)
    return ValidationOutcome(
        TripRequest(
            origin=norm_origin.name,
            destination=norm_dest.name,
            departure_date=departure_date,
            passengers=pax,
            return_enabled=bool(return_enabled),
            return_date=ret,
            preferences=pref,
        )
    )
