"""UI smoke tests with Streamlit's headless AppTest harness (no browser, no network)."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _text(at: AppTest) -> str:
    return "\n".join(str(m.value) for m in at.markdown) + "\n".join(str(c.value) for c in at.caption)


@pytest.fixture
def at():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    return app


def test_app_starts_with_greeting_disclaimer_and_guide(at):
    text = _text(at)
    assert "AI Charter Concierge" in text and "Not affiliated with Flygreen" in text
    assert "private charter concierge" in text
    assert "King Air 90" in text and "Global 6000" in text      # gallery rendered
    assert "Legal notice" in text


def test_chat_recommends_and_shows_cards(at):
    at.chat_input[0].set_value("4 of us, Miami to Nassau, around $20k").run()
    assert not at.exception, at.exception
    msgs = at.session_state.messages
    assert msgs[-1]["role"] == "assistant" and msgs[-1]["cards"]
    assert "Choose this aircraft" in [b.label for b in at.button]


def test_choose_button_closes_with_advisor_brief(at):
    at.chat_input[0].set_value("4 of us, Miami to Nassau").run()
    choose = next(b for b in at.button if b.label == "Choose this aircraft")
    choose.click().run()
    assert not at.exception, at.exception
    assert at.session_state.messages[-1]["chosen"] is not None
    assert any("CHARTER INQUIRY BRIEF" in str(c.value) for c in at.code)


def test_suggestion_button_starts_conversation(at):
    next(b for b in at.button if b.key == "sugg_0").click().run()
    assert not at.exception, at.exception
    assert len(at.session_state.messages) == 2
