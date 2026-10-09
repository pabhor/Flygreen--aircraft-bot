# Data provenance

Both files are **curated local snapshots**. The app never scrapes Flygreen at runtime.

| File | Source | Checked / curated |
|---|---|---|
| `route_estimates.json` | https://www.flygreen.co/popular-route-estimates | 8 October 2026 |
| `aircraft_catalog.json` | https://www.flygreen.co/aircraft-guide | 8 October 2026 |

## route_estimates.json

* 18 city pairs (US, Europe, Transatlantic) exactly as listed on the source page, in the
  direction the source lists them.
* Prices are **USD, one-way**, per category: `light_jet`, `mid_size_jet`,
  `super_mid_size_jet`, `heavy_jet`.
* `null` means the source shows **N/A**. The app treats it as "no published estimate". It is never
  treated as zero and never filled in.
* `_meta.hourly_reference_rates` holds the published average hourly rates
  (Light $3,000, Mid-Size $4,000, Super Mid-Size $4,800, Heavy $5,800). The app shows them as
  **reference only** and never multiplies them by a flight duration.
* Source caveat, verbatim: *"No taxes, airport fees vary, all routes pricing is based on one ways."*
* "Naples" appears under the source's **US** routes (Boston – Naples), so the app reads it as
  Naples, Florida and rejects "Naples, Italy" instead of guessing.

## aircraft_catalog.json

* 21 models, the candidate list in the engineering brief. Each model's **name, category and
  passenger capacity** was checked against the live Aircraft Guide on the curated date, and all 21
  matched.
* Only those three facts plus `source_url` are stored. Range, baggage, cabin size, speed and
  amenities were **not** verified, so they are deliberately absent. Do not add them from memory.
* The guide also lists Turboprop and Long Range Jet categories and many more models. They are
  excluded because the route estimates only cover the four jet categories above.
* This is a small sample. It does not represent Flygreen's network, and no listed aircraft is
  implied to be available on any date.

## Updating the snapshot

1. Open both source pages and compare every value. Prices and capacities can change.
2. Edit the JSON (keep `null` for N/A and keep `source_url` on every record).
3. Update `curated_on` in each file's `_meta` and the table above.
4. Update the expectations in `tests/test_routes.py` (`test_dataset_matches_published_snapshot`) and
   `tests/test_aircraft.py`, then run `pytest`.

> **Maintainer note:** this is a demo snapshot. Re-check prices against the live pages before
> showing the app publicly.
