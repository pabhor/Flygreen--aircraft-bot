# AI Charter Concierge (independent demo)

A chat-first private-jet sales assistant. The customer describes the trip in plain words; the AI
understands group size, budget, priorities and mood, recommends the right aircraft from the full
Flygreen Aircraft Guide (70 models), persuades, handles objections ("too expensive", "bigger?",
"X vs Y") and closes by handing a brief to an advisor.

> Independent demo concept. Not an official Flygreen product, not affiliated with or endorsed by
> Flygreen. No booking, payment or availability check. Prices are indicative averages.

## How it works

```
data pipeline (offline)
  scraper/flygreen_scraper.py   requests + BeautifulSoup -> data/aircraft.csv, published_routes.csv, hourly_rates.csv
  scripts/build_sample_data.py  -> data/cities.csv, category_profiles.csv, routes.csv, route_prices.csv

per chat message (app.py)
  services/nlp.py          TextBlob sentiment + spelling, regex entities, fuzzy city/aircraft match, intent
  services/recommender.py  hard rules (seats, ocean range) + weighted multi-criteria ranking
  services/sales_agent.py  sales funnel + reply writer: OpenAI (grounded on facts) or built-in templates
  ui/                      dark aviation theme, recommendation cards, aircraft guide gallery, spec panel
```

**AI methods:** TextBlob sentiment (reply tone) and spelling correction, regex entity extraction,
difflib fuzzy matching, keyword intent classification, weighted multi-criteria scoring, and an
optional OpenAI LLM for sales copy. Any LLM reply that mentions a price not in the database is
discarded and the template reply is used instead.

**Prices:** published Flygreen route estimates are used verbatim. Every other pair is a sample
estimate = flight hours x published hourly rate x a calibration factor fitted to the published
routes. Without a route, price = stated (or 2 h) flight time x hourly rate.

## Run locally (Windows PowerShell)

Requires Python 3.10 - 3.13 (3.12 recommended).

```powershell
cd flygreen-ai-charter-assistant
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m textblob.download_corpora lite   # optional: enables noun-phrase topics
Copy-Item .env.example .env                # optional: add OPENAI_API_KEY for LLM replies
streamlit run app.py
```

Refresh the data from the live site (optional - the CSVs are already in `data/`):

```powershell
python -m scraper.flygreen_scraper
python -m scripts.build_sample_data
```

Tests: `pytest` (offline; never calls OpenAI or the website).

## Try it

* "It's our anniversary - 2 of us, New York to Nassau, something special"
* "6 executives, Chicago to Aspen, lots of ski gear, under $40k" -> then "too expensive"
* "compare Phenom 300 vs Citation CJ3" -> "I'll take the Phenom 300"
* Aircraft Guide tab -> View details -> Choose this aircraft

## Legacy modules

`services/route_service.py`, `aircraft_service.py`, `pricing_service.py`, `recommendation_service.py`,
`llm_service.py`, `validation.py`, `models.py` and `data/*.json` belong to the earlier form-based
version. They are no longer used by `app.py` but are kept (with their tests) for reference.
