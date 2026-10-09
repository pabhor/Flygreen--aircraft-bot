import pytest

from services.charter_db import get_db
from services.nlp import (
    TripNeeds,
    detect_mood,
    extract_budget,
    extract_cities,
    extract_passengers,
    find_aircraft,
    parse_message,
)


@pytest.fixture(scope="module")
def db():
    return get_db()


@pytest.fixture(scope="module")
def models(db):
    return dict(zip(db.aircraft.model_name, db.aircraft.slug))


@pytest.mark.parametrize("text,expected", [
    ("6 of us flying", 6), ("family of four", 4), ("we are 3", 3), ("12 executives", 12),
    ("me and my wife", 2), ("just me", 1), ("a jet for 5 passengers", 5), ("for 3 hours", None),
    ("budget $20k", None),
])
def test_passengers(text, expected):
    assert extract_passengers(text) == expected


@pytest.mark.parametrize("text,amount,cap", [
    ("under $150k", 150_000, True), ("around 20k", 20_000, False), ("budget of 25,000 dollars", 25_000, False),
    ("max 1.2m", 1_200_000, True), ("6 people, 3 hours", None, False), ("$500 tip", None, False),
])
def test_budget(text, amount, cap):
    assert extract_budget(text) == (amount, cap)


def test_cities_with_alias_typo_and_direction(db):
    assert extract_cities("NYC to Lodnon", db.cities()) == ("New York", "London")
    assert extract_cities("to Aspen from Chicago", db.cities()) == ("Chicago", "Aspen")
    assert extract_cities("vegas trip", db.cities()) == ("Las Vegas", None)


def test_aircraft_names_shorthand_and_no_false_number_match(models):
    assert find_aircraft("compare Phenom 300 vs Citation CJ3", models) == ("phenom-300", "citation-cj3")
    assert find_aircraft("is the G650 nice?", models) == ("gulfstream-650",)
    assert "challenger-300" not in find_aircraft("Phenom 300 please", models)


def test_mood_from_sentiment_and_lexicon():
    assert detect_mood("I'm so stressed about this trip")[0] == "stressed"
    assert detect_mood("It's our honeymoon!")[0] == "celebrating"
    assert detect_mood("that's too expensive")[0] != "stressed"   # an objection, not distress


@pytest.mark.parametrize("text,intent", [
    ("compare Phenom 300 vs Citation CJ3", "compare"), ("too expensive", "cheaper"),
    ("can we go bigger?", "upgrade"), ("I'll take the Phenom 300", "choose"),
    ("tell me about the Falcon 7X", "details"), ("start over", "reset"),
    ("4 of us to Miami from Boston", "recommend"),
])
def test_intents(db, models, text, intent):
    assert parse_message(text, db.cities(), models).intent == intent


def test_needs_merge_keeps_earlier_facts():
    first = TripNeeds(passengers=4, origin="Miami", destination="Nassau", needs=frozenset({"baggage"}))
    merged = first.merge(TripNeeds(budget_usd=20_000, needs=frozenset({"family"})))
    assert merged.passengers == 4 and merged.origin == "Miami" and merged.budget_usd == 20_000
    assert merged.needs == {"baggage", "family"}
