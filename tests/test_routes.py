from datetime import date

import pytest

from models import AircraftCategory, RouteMatchStatus
from services.route_service import AmbiguousCityError, InvalidCityError
from services.validation import validate_trip_input
from tests.conftest import FUTURE, FUTURE_RETURN

L, M, S, H = (AircraftCategory.LIGHT_JET, AircraftCategory.MID_SIZE_JET,
              AircraftCategory.SUPER_MID_SIZE_JET, AircraftCategory.HEAVY_JET)


def test_dataset_matches_published_snapshot(repo):
    assert len(repo.routes) == 18
    r = repo.lookup("New York", "South Florida").estimate
    assert [r.price_for(c) for c in (L, M, S, H)] == [13000, 15000, 20000, 25000]
    assert repo.lookup("London", "Nice").estimate.price_for(M) == 10500
    assert repo.lookup("Nassau", "Moscow").estimate.price_for(H) == 110000
    assert repo.hourly_rates == {L: 3000, M: 4000, S: 4800, H: 5800}


def test_exact_route_returns_configured_estimate(repo):
    lk = repo.lookup("Los Angeles", "Las Vegas")
    assert lk.status is RouteMatchStatus.EXACT_MATCH
    assert lk.estimate.price_for(L) == 5000
    assert lk.direction_note is None


def test_lookup_is_case_and_whitespace_insensitive(repo):
    assert repo.lookup("  los   angeles ", "LAS VEGAS").status is RouteMatchStatus.EXACT_MATCH


def test_reverse_route_is_flagged(repo):
    lk = repo.lookup("South Florida", "New York")
    assert lk.status is RouteMatchStatus.REVERSE_MATCH
    assert lk.estimate.origin == "New York"
    assert "opposite direction" in lk.direction_note


def test_unknown_route_has_no_estimate(repo):
    lk = repo.lookup("Boston", "Las Vegas")  # both cities known, pair unpublished
    assert lk.status is RouteMatchStatus.NO_PUBLISHED_ESTIMATE
    assert lk.estimate is None


def test_unavailable_category_is_none_not_zero(repo):
    est = repo.lookup("New York", "London").estimate
    assert est.price_for(L) is None
    assert est.price_for(M) is None
    assert est.price_for(H) == 95000


def test_direction_specific_value_preferred(asymmetric_repo):
    assert asymmetric_repo.lookup("Beta", "Alpha").status is RouteMatchStatus.EXACT_MATCH
    assert asymmetric_repo.lookup("Beta", "Alpha").estimate.price_for(L) == 11000


@pytest.mark.parametrize("raw,expected", [
    ("NYC", "New York"), ("new york city", "New York"), ("LA", "Los Angeles"),
    ("Vegas", "Las Vegas"), ("Naples, FL", "Naples"), ("Milano", "Milan"), ("  paris ", "Paris"),
])
def test_known_aliases_normalize(repo, raw, expected):
    n = repo.normalize_city(raw)
    assert n.name == expected and n.known


@pytest.mark.parametrize("raw", ["Florida", "Naples, Italy", "napoli", "London, Ontario", "NY"])
def test_ambiguous_cities_are_not_guessed(repo, raw):
    with pytest.raises(AmbiguousCityError):
        repo.normalize_city(raw)


@pytest.mark.parametrize("raw", ["", "   ", "<script>", "a" * 61, "123"])
def test_invalid_city_rejected(repo, raw):
    with pytest.raises(InvalidCityError):
        repo.normalize_city(raw)


def test_unknown_city_kept_without_fuzzy_guess(repo):
    n = repo.normalize_city("Los Angles")  # typo must NOT become Los Angeles
    assert n.name == "Los Angles" and not n.known


# ---- validation -------------------------------------------------------------
def _validate(repo, **kw):
    base = dict(origin="New York", destination="South Florida", departure_date=FUTURE,
                passengers=4, return_enabled=False, return_date=None, preference="balanced",
                today=date(2026, 10, 8))
    base.update(kw)
    return validate_trip_input(repo, **base)


def test_valid_request(repo):
    out = _validate(repo, origin="nyc")
    assert out.ok and out.request.origin == "New York"


def test_same_origin_destination_rejected(repo):
    out = _validate(repo, destination="NYC")
    assert not out.ok and "destination" in out.errors


def test_missing_fields_rejected(repo):
    out = _validate(repo, origin="", destination=None, departure_date=None)
    assert {"origin", "destination", "departure_date"} <= set(out.errors)


@pytest.mark.parametrize("pax", [0, -1, 1.5, "4", True, None, 31])
def test_invalid_passenger_count_rejected(repo, pax):
    assert "passengers" in _validate(repo, passengers=pax).errors


def test_return_before_departure_rejected(repo):
    out = _validate(repo, return_enabled=True, return_date=date(2099, 5, 31))
    assert "return_date" in out.errors


def test_return_same_day_allowed(repo):
    assert _validate(repo, return_enabled=True, return_date=FUTURE).ok


def test_return_date_required_when_enabled(repo):
    assert "return_date" in _validate(repo, return_enabled=True, return_date=None).errors


def test_return_date_ignored_when_disabled(repo):
    out = _validate(repo, return_enabled=False, return_date=FUTURE_RETURN)
    assert out.ok and out.request.return_date is None


def test_past_departure_rejected(repo):
    assert "departure_date" in _validate(repo, departure_date=date(2020, 1, 1)).errors
