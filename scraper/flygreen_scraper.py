"""Scrape the public Flygreen Aircraft Guide and Popular Route Estimates pages.

Uses requests + BeautifulSoup. Writes three CSV files into ``data/``:

* ``aircraft.csv``          every aircraft in the guide with its detail-page specs
* ``published_routes.csv``  the published one-way estimates per category (N/A kept empty)
* ``hourly_rates.csv``      the published average cost per hour per category

Run:  python -m scraper.flygreen_scraper
robots.txt on flygreen.co allows all paths; requests are throttled and identified.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.flygreen.co"
GUIDE_URL = f"{BASE_URL}/aircraft-guide"
ROUTES_URL = f"{BASE_URL}/popular-route-estimates"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (charter-assistant-demo; educational scraper)"}
REQUEST_DELAY_SECONDS = 0.4

# Guide section title -> internal category key.
CATEGORY_KEYS = {
    "turboprop": "turboprop",
    "light jet": "light_jet",
    "mid-size jet": "mid_size_jet",
    "midsize jet": "mid_size_jet",
    "super mid-size jet": "super_mid_size_jet",
    "super midsize jet": "super_mid_size_jet",
    "heavy jet": "heavy_jet",
    "long range jet": "long_range_jet",
    "ultra long range jet": "long_range_jet",
}
ROUTE_COLUMN_KEYS = {"light": "light_jet", "mid-size": "mid_size_jet",
                     "super mid-size": "super_mid_size_jet", "heavy": "heavy_jet"}
RATE_KEYS = {"light jets": "light_jet", "mid-size jets": "mid_size_jet",
             "super mid-size jets": "super_mid_size_jet", "heavy jets": "heavy_jet"}

AIRCRAFT_FIELDS = [
    "model_name", "slug", "category", "passengers", "cabin_height_ft", "cabin_width_ft",
    "cabin_length_ft", "max_range_hours", "baggage_cuft", "lavatory", "description",
    "image_url", "detail_url", "scraped_on",
]

logger = logging.getLogger("scraper")


def fetch(session: requests.Session, url: str) -> BeautifulSoup:
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    return BeautifulSoup(resp.text, "html.parser")


def _number(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group()) if m else None


def _category_key(title: str) -> str:
    key = " ".join(title.lower().split())
    return CATEGORY_KEYS.get(key, key.replace(" ", "_").replace("-", "_"))


# ------------------------------------------------------------- aircraft ------
def parse_guide(soup: BeautifulSoup) -> list[dict]:
    """List page: section title -> cards (name, seats, image, detail link)."""
    rows = []
    for section in soup.select("div.plane-guide-list div.product"):
        title = section.select_one(".plane-guide-section-title")
        if not title:
            continue
        category = _category_key(title.get_text(strip=True))
        for item in section.select(".plane-guide-item a[href]"):
            specs = item.select(".plane-guide-specs-item")
            img = item.select_one("img")
            rows.append({
                "model_name": specs[0].get_text(strip=True) if specs else img.get("alt", ""),
                "slug": item["href"].rstrip("/").rsplit("/", 1)[-1],
                "category": category,
                "passengers": int(_number(specs[1].get_text()) or 0) if len(specs) > 1 else None,
                "image_url": urljoin(BASE_URL, img["src"]) if img and img.get("src") else "",
                "detail_url": urljoin(BASE_URL, item["href"]),
            })
    return rows


def parse_detail(soup: BeautifulSoup) -> dict:
    """Detail page: the spec strip and the first description paragraph."""
    specs: dict[str, str] = {}
    for item in soup.select(".jet-info-specs .jet-info-item"):
        title = item.select_one(".title")
        value = item.select_one(".spec")
        if title and value:
            specs[title.get_text(strip=True).lower()] = value.get_text(" ", strip=True)

    out: dict = {}
    if "passengers" in specs:
        out["passengers"] = int(_number(specs["passengers"]) or 0)
    cabin = specs.get("cabin size", "")
    dims = re.findall(r"(\d+(?:\.\d+)?)\s*'?\s*([hwl])", cabin.replace("’", "'"))
    for value, axis in dims:
        out[{"h": "cabin_height_ft", "w": "cabin_width_ft", "l": "cabin_length_ft"}[axis]] = float(value)
    out["max_range_hours"] = _number(specs.get("maximum range"))
    out["baggage_cuft"] = _number(specs.get("baggage space"))
    out["lavatory"] = specs.get("lavatory", "")

    # First paragraph only - the second one is a phone/contact call-to-action.
    para = soup.select_one(".jet-specs-right p")
    out["description"] = para.get_text(" ", strip=True) if para else ""
    return out


def scrape_aircraft(session: requests.Session) -> list[dict]:
    cards = parse_guide(fetch(session, GUIDE_URL))
    logger.info("found %d aircraft on the guide page", len(cards))
    today = date.today().isoformat()
    rows = []
    for i, card in enumerate(cards, 1):
        try:
            detail = parse_detail(fetch(session, card["detail_url"]))
        except requests.RequestException as exc:
            logger.warning("detail page failed for %s: %s", card["slug"], exc)
            detail = {}
        row = {**card, **{k: v for k, v in detail.items() if v not in (None, "")}, "scraped_on": today}
        rows.append({f: row.get(f, "") for f in AIRCRAFT_FIELDS})
        logger.info("[%d/%d] %s", i, len(cards), card["model_name"])
    return rows


# --------------------------------------------------------------- routes ------
def parse_routes(soup: BeautifulSoup) -> tuple[list[dict], list[dict]]:
    rates = []
    for item in soup.select(".our-aircrafts-caption-item"):
        title = item.select_one(".our-aircrafts-caption-title")
        cost = item.select_one(".our-aircrafts-caption-cost")
        if title and cost:
            key = RATE_KEYS.get(title.get_text(strip=True).lower())
            if key:
                rates.append({"category": key, "hourly_rate_usd": int(_number(cost.get_text()) or 0)})

    routes = []
    for table in soup.select("div.table"):
        header = [td.get_text(strip=True) for td in table.select(".th .td")]
        if not header:
            continue
        region = header[0] if len(header[0]) <= 3 else header[0].title()  # keep "US" upper-case
        columns = [ROUTE_COLUMN_KEYS.get(h.lower()) for h in header[1:]]
        for tr in table.select(".tr"):
            cells = [td.get_text(strip=True) for td in tr.select(".td")]
            if len(cells) < 2 or " - " not in cells[0]:
                continue
            origin, destination = (c.strip().title() for c in cells[0].split(" - ", 1))
            row = {"region": region, "origin": origin, "destination": destination}
            for key, cell in zip(columns, cells[1:]):
                if key:
                    value = _number(cell)
                    row[key] = int(value) if value else ""  # N/A stays empty, never 0
            routes.append(row)
    return routes, rates


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("wrote %d rows -> %s", len(rows), path.relative_to(DATA_DIR.parent))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with requests.Session() as session:
        routes, rates = parse_routes(fetch(session, ROUTES_URL))
        aircraft = scrape_aircraft(session)
    if not aircraft or not routes:
        logger.error("scrape returned no data - page structure may have changed; CSVs left untouched")
        return 1
    write_csv(DATA_DIR / "aircraft.csv", aircraft, AIRCRAFT_FIELDS)
    write_csv(DATA_DIR / "published_routes.csv", routes,
              ["region", "origin", "destination", *ROUTE_COLUMN_KEYS.values()])
    write_csv(DATA_DIR / "hourly_rates.csv", rates, ["category", "hourly_rate_usd"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
