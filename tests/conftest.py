import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import (  # noqa: E402
    AircraftCategory,
    Preference,
    RouteEstimate,
    TripRequest,
)
from services.aircraft_service import get_aircraft_catalog  # noqa: E402
from services.route_service import RouteRepository, get_route_repository  # noqa: E402

FUTURE = date(2099, 6, 1)
FUTURE_RETURN = date(2099, 6, 8)


@pytest.fixture
def repo():
    return get_route_repository()


@pytest.fixture
def catalog():
    return get_aircraft_catalog()


@pytest.fixture(autouse=True)
def _no_real_openai_key(monkeypatch):
    """Tests must never hit the real API, even if a developer has a key set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def make_request(origin="New York", destination="South Florida", passengers=4,
                 return_enabled=False, preference=Preference.BALANCED):
    return TripRequest(
        origin=origin,
        destination=destination,
        departure_date=FUTURE,
        passengers=passengers,
        return_enabled=return_enabled,
        return_date=FUTURE_RETURN if return_enabled else None,
        preferences=preference,
    )


@pytest.fixture
def asymmetric_repo():
    """Fixture dataset where both directions are published with different values."""
    L, M, S, H = (AircraftCategory.LIGHT_JET, AircraftCategory.MID_SIZE_JET,
                  AircraftCategory.SUPER_MID_SIZE_JET, AircraftCategory.HEAVY_JET)
    routes = [
        RouteEstimate("Test", "Alpha", "Beta", {L: 10000, M: 12000, S: 15000, H: 20000}, "https://example.test"),
        RouteEstimate("Test", "Beta", "Alpha", {L: 11000, M: 13000, S: None, H: 21000}, "https://example.test"),
    ]
    rates = {L: 3000, M: 4000, S: 4800, H: 5800}
    return RouteRepository(routes, rates, "https://example.test", "2026-10-08", "test")
