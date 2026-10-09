from types import SimpleNamespace

import openai
import pytest

from config import LLMSettings
from services.charter_db import get_db
from services.sales_agent import AgentState, SalesAgent, ungrounded_amounts

KEYED = LLMSettings(api_key="sk-test", model="gpt-test", timeout_seconds=5, max_output_tokens=300)


@pytest.fixture(scope="module")
def db():
    return get_db()


def _fake_client(text=None, exc=None):
    def create(**kwargs):
        if exc:
            raise exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def run(agent, *messages):
    state, reply = AgentState(), None
    for m in messages:
        reply, state = agent.respond(m, state)
    return reply, state


def test_full_sales_funnel_without_llm(db):
    agent = SalesAgent(db)
    assert not agent.llm_enabled
    reply, state = run(agent, "4 of us, Miami to Nassau, around $20k")
    assert reply.engine == "template" and len(reply.cards) >= 2
    assert reply.cards[0].model_name in reply.text and "Choose this aircraft" in reply.text
    reply, state = agent.respond("too expensive", state)
    assert reply.cards[0].price.amount < state.needs.budget_usd
    reply, state = agent.respond("ok I'll take it", state)
    assert reply.chosen is not None and state.chosen == reply.chosen.slug
    assert "advisor brief" in reply.text


def test_asks_discovery_question_when_nothing_is_known(db):
    reply, _ = run(SalesAgent(db), "hello")
    assert not reply.cards and "how many people" in reply.text


def test_asks_for_first_missing_item(db):
    reply, _ = run(SalesAgent(db), "we want something luxurious")
    assert "How many passengers" in reply.text


def test_stressed_customer_gets_reassuring_tone(db):
    reply, _ = run(SalesAgent(db), "I'm so stressed, 3 of us need Boston to Chicago")
    assert reply.text.startswith("I completely understand")


def test_compare_returns_side_by_side(db):
    reply, _ = run(SalesAgent(db), "compare Phenom 300 vs Citation CJ3")
    assert [c.model_name for c in reply.comparison] == ["Phenom 300", "Citation CJ3"]


def test_llm_reply_used_when_grounded(db):
    agent = SalesAgent(db, KEYED, client_factory=lambda s: _fake_client("The **Phenom 300** is ideal for you."))
    reply, _ = run(agent, "4 of us from New York to Boston")
    assert reply.engine == "openai" and "Phenom 300" in reply.text


def test_llm_reply_with_invented_price_falls_back(db):
    agent = SalesAgent(db, KEYED, client_factory=lambda s: _fake_client("Only $1,234 today!"))
    reply, _ = run(agent, "4 of us from New York to Boston")
    assert reply.engine == "template" and "$1,234" not in reply.text


@pytest.mark.parametrize("exc", [openai.APITimeoutError(request=None), openai.OpenAIError("boom")])
def test_llm_errors_fall_back_to_template(db, exc):
    agent = SalesAgent(db, KEYED, client_factory=lambda s: _fake_client(exc=exc))
    reply, _ = run(agent, "4 of us from New York to Boston")
    assert reply.engine == "template" and reply.cards


def test_grounding_check_accepts_known_and_rejects_new_amounts():
    facts = {"options": [{"price_usd": 13000}], "customer": {"budget_usd": 20000}}
    assert ungrounded_amounts("Just $13,000, under your $20k budget", facts) == []
    assert ungrounded_amounts("Only $9,999", facts) == ["$9,999"]
