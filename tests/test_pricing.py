from models import AircraftCategory, RouteMatchStatus
from services.pricing_service import calculate_price_breakdown, format_usd

L, M, S, H = (AircraftCategory.LIGHT_JET, AircraftCategory.MID_SIZE_JET,
              AircraftCategory.SUPER_MID_SIZE_JET, AircraftCategory.HEAVY_JET)


def test_one_way_uses_exact_estimate(repo):
    p = calculate_price_breakdown(repo.lookup("New York", "South Florida"), None, M)
    assert p.outbound_estimate == 15000
    assert p.return_estimate is None
    assert p.currency == "USD" and p.price_basis == "one_way_estimate"
    assert any("taxes" in c for c in p.caveats)


def test_round_trip_combines_both_legs(repo):
    out = repo.lookup("New York", "South Florida")
    back = repo.lookup("South Florida", "New York")
    p = calculate_price_breakdown(out, back, L)
    assert (p.outbound_estimate, p.return_estimate, p.estimated_total) == (13000, 13000, 26000)
    assert p.return_match is RouteMatchStatus.REVERSE_MATCH
    assert any("Return-leg figure" in c for c in p.caveats)


def test_round_trip_uses_direction_specific_values(asymmetric_repo):
    out = asymmetric_repo.lookup("Alpha", "Beta")
    back = asymmetric_repo.lookup("Beta", "Alpha")
    p = calculate_price_breakdown(out, back, L)
    assert (p.outbound_estimate, p.return_estimate, p.estimated_total) == (10000, 11000, 21000)
    assert p.return_match is RouteMatchStatus.EXACT_MATCH


def test_round_trip_total_not_calculated_when_one_leg_missing(asymmetric_repo):
    out = asymmetric_repo.lookup("Alpha", "Beta")
    back = asymmetric_repo.lookup("Beta", "Alpha")
    p = calculate_price_breakdown(out, back, S)  # return leg is N/A for Super Mid
    assert p.outbound_estimate == 15000
    assert p.return_estimate is None
    assert p.estimated_total is None
    assert any("cannot be calculated" in c for c in p.caveats)


def test_unavailable_category_is_not_zero(repo):
    p = calculate_price_breakdown(repo.lookup("New York", "London"), None, L)
    assert p.outbound_estimate is None and p.estimated_total is None
    assert format_usd(p.outbound_estimate) == "Not published"
    assert format_usd(0) == "$0"  # formatting is honest for a genuine zero


def test_unknown_route_has_no_price(repo):
    out = repo.lookup("Boston", "Phoenix")
    back = repo.lookup("Phoenix", "Boston")
    for cat in AircraftCategory:
        p = calculate_price_breakdown(out, back, cat)
        assert p.outbound_estimate is None and p.return_estimate is None and p.estimated_total is None


def test_format_usd():
    assert format_usd(105000) == "$105,000"
    assert format_usd(None) == "Not published"
