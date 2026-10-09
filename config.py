"""Central configuration.

All tunables and secrets come from environment variables (optionally loaded
from a local ``.env`` file via python-dotenv). Nothing secret is hard-coded.
The OpenAI model name is defined here and nowhere else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ROUTE_DATA_PATH = DATA_DIR / "route_estimates.json"
AIRCRAFT_DATA_PATH = DATA_DIR / "aircraft_catalog.json"

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 20.0
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 450

# UI-only bound for the passenger input. It is NOT a safety or aircraft limit;
# requests above the largest listed capacity get an explicit "no match" state.
UI_MAX_PASSENGERS = 30
MAX_QUESTION_CHARS = 300

# load_dotenv never overrides variables already set in the real environment.
load_dotenv(BASE_DIR / ".env", override=False)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class LLMSettings:
    api_key: str | None
    model: str
    timeout_seconds: float
    max_output_tokens: int

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def __repr__(self) -> str:  # never leak the key through logs/reprs
        return (
            f"LLMSettings(api_key={'set' if self.api_key else 'missing'}, "
            f"model={self.model!r}, timeout_seconds={self.timeout_seconds}, "
            f"max_output_tokens={self.max_output_tokens})"
        )


def get_llm_settings() -> LLMSettings:
    """Read OpenAI settings fresh from the environment on each call."""
    key = os.getenv("OPENAI_API_KEY", "").strip() or None
    if key and key.startswith("sk-your"):  # placeholder from .env.example
        key = None
    return LLMSettings(
        api_key=key,
        model=os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL,
        timeout_seconds=_float_env("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS),
        max_output_tokens=_int_env("OPENAI_MAX_OUTPUT_TOKENS", DEFAULT_OPENAI_MAX_OUTPUT_TOKENS),
    )


def get_log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
