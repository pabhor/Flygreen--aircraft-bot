# Build & verification notes (8 October 2026)

## Source-data check
* Popular Route Estimates: all 18 routes × 4 categories and the 4 hourly rates matched the live page.
* Aircraft Guide: all 21 candidate models (name, category, capacity) matched the live page.
* Data gaps, handled without inventing facts:
  * "Naples" is under US routes, so it means Naples, Florida. "Naples, Italy" is rejected as ambiguous.
  * "South Florida" is a region. Miami has its own route, so no aliasing between them.
  * The guide has no verified range, baggage or cabin data in this subset, so none is shown.
  * The source lists each pair in one direction only. Return legs are therefore always
    "opposite-direction" references and are labelled as such.
  * Transatlantic routes publish Heavy Jet only. Other categories show as N/A, never $0.

## What ran in the build sandbox
The build sandbox could not reach PyPI (blocked by egress policy), so `streamlit` could not be installed there.

| Check | Result |
|---|---|
| `pytest` (unit + service integration + LLM fallback) | **119 passed** |
| `tests/test_app_smoke.py` (Streamlit AppTest) | **skipped**: Streamlit not installable in the sandbox. Run it locally. |
| OpenAI path | Exercised against the real `openai` 3.26.1 SDK (built from GitHub source) through a mock HTTP transport: request body, auth header, timeout, 401/404/429/500 |
| `app.py` end-to-end | Executed for 11 scenarios (empty, validation, exact round trip, reverse, unknown, transatlantic, no capacity, AI ok, AI ungrounded, AI timeout, HTML injection) with a recording stand-in for `streamlit`. No exceptions, correct statuses. |
| Visual check | Captured component HTML/CSS rendered in Chromium at 1200 px and 390 px. No horizontal scroll. |
| Streamlit API compatibility | Every Streamlit call checked against the 1.65.0 source |
| Lint | `ruff` (pyflakes, pycodestyle, bugbear, bandit, pyupgrade, isort): clean |
| Secret scan | No key-like strings in the project |

## Not verified
* A real OpenAI response (no API key was available).
* The real Streamlit runtime and browser UI. Run `pytest` (this un-skips the AppTest smoke tests
  once requirements are installed) and `streamlit run app.py`.
* Deployment. Nothing was deployed. See the README.
