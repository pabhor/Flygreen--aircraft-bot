"""Integration tests for the application service (route + aircraft + pricing)."""

import pytest

from models import AircraftCategory, MatchStatus, Preference, ReasonKind
from services.recommendation_service import build_trip_summary, recommend
from tests.conftest import make_request

L, M, S, H = (AircraftCategory.LIGHT_JET, AircraftCategory.MID_SIZE_JET,
              AircraftCategory.SUPER_MID_SIZE_JET, AircraftCategory.HEAVY_JET)


def test_exact_route_lowest_price_plus_larger_alternative(repo, catalog):
    res = recommend(make_request(passengers=4, preference=Preference.LOWEST_PRICE), repo, catalog)
    assert res.status is MatchStatus.EXACT_MATCH
    assert [o.category for o in res.options] == [L, M]
    assert res.options[0].category_estimate == 13000
    assert res.options[0].role == "Lowest indicative price"
    assert res.options[1].category_estimate == 15000


def test_balanced_shows_up_to_three(repo, catalog):
    res = recommend(make_request(passengers=4), repo, catalog)
    assert [o.category for o in res.options] == [L, M, S]


def test_more_space_puts_larger_category_first(repo, catalog):
    res = recommend(make_request(passengers=4, preference=Preference.MORE_SPACE), repo, catalog)
    assert [o.category for o in res.options] == [M, L]


def test_reverse_route_flagged_in_result(repo, catalog):
    res = recommend(make_request(origin="South Florida", destination="New York"), repo, catalog)
    assert res.status is MatchStatus.REVERSE_MATCH
    assert res.route_direction_note and "opposite direction" in res.route_direction_note
    assert any("opposite direction" in w for w in res.warnings)
    assert "opposite direction" in build_trip_summary(res)


def test_unknown_route_no_fabricated_price(repo, catalog):
    res = recommend(make_request(origin="Boston", destination="Las Vegas", return_enabled=True), repo, catalog)
    assert res.status is MatchStatus.NO_PUBLISHED_ESTIMATE
    assert res.options  # aircraft examples still shown
    for o in res.options:
        assert o.category_estimate is None
        assert o.pricing.estimated_total is None and o.pricing.return_estimate is None
    assert any("No published estimate" in w for w in res.warnings)
    assert "$" not in build_trip_summary(res).split("Caveats:")[0]


@pytest.mark.parametrize("pax", [1, 5, 7, 8, 9, 10, 12, 13, 14])
def test_capacity_never_exceeded(repo, catalog, pax):
    res = recommend(make_request(passengers=pax), repo, catalog)
    for o in res.options:
        assert o.aircraft
        for a in o.aircraft:
            assert a.passenger_capacity >= pax


def test_no_capacity_match(repo, catalog):
    res = recommend(make_request(passengers=15), repo, catalog)
    assert res.status is MatchStatus.NO_CAPACITY_MATCH
    assert res.options == () and res.pricing is None
    assert any("advisor must review" in w for w in res.warnings)
    assert "advisor review required" in build_trip_summary(res)


def test_transatlantic_only_heavy_priced(repo, catalog):
    res = recommend(make_request(origin="New York", destination="London", passengers=3), repo, catalog)
    assert [o.category for o in res.options] == [H]
    assert res.options[0].category_estimate == 95000
    assert any("N/A" in w for w in res.warnings)


def test_round_trip_total(repo, catalog):
    res = recommend(make_request(passengers=6, return_enabled=True, preference=Preference.LOWEST_PRICE), repo, catalog)
    light = res.options[0]
    assert light.category is L
    assert (light.pricing.outbound_estimate, light.pricing.return_estimate, light.pricing.estimated_total) == (13000, 13000, 26000)
    assert res.return_route is not None


def test_round_trip_partial_leg_warning(asymmetric_repo, catalog):
    res = recommend(make_request(origin="Alpha", destination="Beta", passengers=9, return_enabled=True),
                    asymmetric_repo, catalog)
    sm = next(o for o in res.options if o.category is S)
    assert sm.pricing.estimated_total is None
    assert any("cannot be calculated" in w for w in res.warnings)
    heavy = next(o for o in res.options if o.category is H)
    assert heavy.pricing.estimated_total == 41000  # 20000 + 21000 direction-specific


def test_reasons_are_labelled(repo, catalog):
    res = recommend(make_request(), repo, catalog)
    kinds = {r.kind for r in res.reasons}
    assert kinds == {ReasonKind.PUBLISHED_DATA, ReasonKind.APP_RULE, ReasonKind.ADVISOR}


def test_why_it_matches_uses_capacity_facts_only(repo, catalog):
    res = recommend(make_request(passengers=6), repo, catalog)
    for o in res.options:
        for line in o.why_it_matches:
            assert "listed capacity" in line
            for banned in ("range", "baggage", "luggage", "spacious", "luxur"):
                assert banned not in line.lower()


def test_summary_contains_key_fields(repo, catalog):
    res = recommend(make_request(return_enabled=True), repo, catalog)
    s = build_trip_summary(res)
    for needle in ("New York → South Florida", "Round trip", "Passengers: 4", "Exact published route",
                   "$13,000", "$26,000", "taxes", "flygreen.co/popular-route-estimates"):
        assert needle in s
