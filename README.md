# ** THIS IS A NEW PROJECT AND BEING BUILT OUT** June 8, 2025
# tickbiterisk

> **Root file** – this README lives at repo root, not in `/docs`.  All lowercase filename per project convention.

---

## mission

Build a transparent, Maryland-first tickborne disease risk data product from open public data. The current implementation communicates relative county-week Lyme risk baselines; per-bite Lyme probability for any U.S. county is a roadmap goal.

This project ships as self-hosted code; we do not currently provide a public API.

## current build status

The active implementation is a Maryland-first ETL and modeling prototype. The current code focuses on source manifest parsing, Maryland Lyme county-year reconciliation, CDC seasonality baselines, tick/vector status normalization, model feature assembly, baseline backtesting, county-week seasonal risk baselines, runtime lookup over derived risk files, and a Postgres-ready warehouse schema. The HTTP API endpoint described below is roadmap behavior; the implemented product-facing bridge today is `tickbiterisk risk lookup`, which reads the derived county-week baseline and returns a plain JSON response.

## quick start (docker)

```bash
# clone repository
git clone https://github.com/yourhandle/tickbiterisk.git
cd tickbiterisk

# future target: spin up database, model fit, and API
docker compose up -d            # roadmap until compose/API wiring lands

# future target: query per-bite risk (Anne Arundel, MD; 24-h attachment)
curl 'http://localhost:8000/risk?fips=24003&tau=24'
```

Returns JSON:

```jsonc
{"risk": [0.022], "ci95": [[0.011, 0.041]], ...}
```

## quick start (python)

The current local Python path is the Maryland ETL plus `tickbiterisk risk lookup` against derived CSV artifacts. Package/server commands such as `init-data` and `runserver` are roadmap behavior.

## data sources

| feed                                             | cadence | licence          |
| ------------------------------------------------ | ------- | ---------------- |
| CDC Tick Surveillance CSV                        | annual  | US public domain |
| FARS deer collisions                             | annual  | US public domain |
| NSSP ED tick‑bite index                          | weekly  | US public domain |
| NLCD land‑cover                                  | static  | US public domain |
| Census PEP/intercensal population               | annual  | US public domain |
| CAPC dog serology\*                              | monthly | CC‑BY‑NC 4.0     |
| \*CAPC not redistributed; fetch script provided. |         |                  |

Full details: [`/docs/data-sources.md`](docs/data-sources.md)

## maryland ETL

The Maryland weather ETL has two acquisition paths: NOAA CDO/GHCND for observed station history, and Open-Meteo as a secondary reanalysis/gap-fill source using Census Gazetteer county internal points. The planned NOAA backfill range is 1992-01-01 through the current year.

```bash
tickbiterisk etl weather-locations --output-dir build/etl
tickbiterisk etl county-reference --output-dir build/etl/county-reference
tickbiterisk etl census-population --output-dir build/etl/population
tickbiterisk etl lyme-outcomes --raw-dir data/raw/lyme --output-dir build/etl/lyme
tickbiterisk etl seasonality-baseline --raw-dir data/raw/seasonality --output-dir build/etl/seasonality
tickbiterisk etl model-features --output-dir build/etl/model
tickbiterisk etl model-backtest --model-features-path build/etl/model/model_features_county_year.csv --output-dir build/etl/backtest
tickbiterisk etl county-week-risk --backtest-predictions-path build/etl/backtest/model_backtest_predictions.csv --seasonality-baseline-path build/etl/seasonality/seasonality_baseline.csv --output-dir build/etl/county-week-risk
tickbiterisk etl deer-harvest --county-reference-path build/etl/county-reference/county_reference.csv --output-dir build/etl/deer-harvest
tickbiterisk etl deer-harvest --county-reference-path build/etl/county-reference/county_reference.csv --output-dir build/etl/deer-harvest --include-annual-report-pdfs
tickbiterisk etl ecology-sources --raw-dir data/raw/ecology --manifest-path build/etl/ecology/source_manifest.csv
tickbiterisk etl building-permits --start-year 2000 --end-year 2025 --output-dir build/etl/building-permits
tickbiterisk etl contact-pressure --output-dir build/etl/contact-pressure
tickbiterisk etl mast-acorn --raw-dir data/raw/ecology/mast --output-dir build/etl/mast
tickbiterisk etl weather-backfill-open-meteo --county-fips 24003 --start-date 2020-01-01 --end-date 2020-01-03 --output-dir build/etl/weather-smoke
tickbiterisk etl noaa-stations --county-fips 24003 --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa
tickbiterisk etl noaa-daily --county-fips 24003 --station-id GHCND:USW00093721 --start-date 1992-05-01 --end-date 1992-05-07 --output-dir build/etl/noaa
tickbiterisk etl noaa-backfill-county --county-fips 24003 --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa
tickbiterisk etl noaa-audit-stations --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa-station-audit
tickbiterisk etl noaa-audit-stations --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa-station-audit-fallback --nearest-station-fallback
tickbiterisk etl noaa-backfill-maryland --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa --county-fips 24003 --dry-run
tickbiterisk etl noaa-backfill-maryland --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa --nearest-station-fallback
tickbiterisk etl noaa-weather-features --input-path build/etl/noaa/noaa_ghcnd_daily_observations.csv --output-dir build/etl/noaa
tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv --pretty
```

Ecology source acquisition downloads official Annual NLCD/MRLC, Census BPS, Maryland DNR mast, and USDA CDL source pages/files into ignored raw storage and writes a source manifest; a 2026-05-25 smoke run catalogued 12 source files. `lyme-outcomes` reconciles the ignored raw CDC Lyme CSV exports into `lyme_county_year_reconciled.csv`; the 2026-05-25 live smoke wrote 700 Maryland county-year outcome rows for 24 jurisdictions from 1992-2023, preserving 33 source conflicts for review. `seasonality-baseline` turns CDC Lyme disease-onset month/week exports into 910 normalized seasonal observations and 65 empirical baseline rows, using annual shares rather than raw case levels because onset-dashboard totals are diagnostic rather than final surveillance totals. `model-features` joins Lyme outcomes to population, calendar-apportioned weekly NOAA weather, optional contact pressure, and optional prior-season deer harvest; the 2026-05-25 live smoke wrote 676 model-ready county-year rows for 1992-2023. `county-week-risk` converts annual backtest predictions plus a selected weekly onset curve into a relative county-week seasonal baseline; rows preserve the seasonality source, score calibration, input SHA-256 values, and the `not_weather_adjusted` limitation in `feature_quality_flags`. `risk lookup` turns that derived CSV into an API-ready JSON payload by county/date, using CDC MMWR week boundaries and the latest available baseline year when the requested year is not present. Census BPS county annual files are normalized for Maryland county-year construction pressure starting with the practical 2000-2025 range available in the public county ASCII index; the full smoke run wrote 435 deduped rows because historical files have fewer than 24 Maryland jurisdictions before 2022. A 2026-05-25 live smoke wrote 435 contact-pressure feature rows with 48 `missing_population` rows; the cautious mast/acorn parser wrote 0 structured rows and 3 extraction-summary rows, all `no_supported_values`, so mast/acorn remains limited and summary-visible rather than model-default. NOAA CDO/GHCND is the primary observed historical weather source and reads `NOAA_TOKEN` from the environment. `noaa-audit-stations` checks station metadata before a large daily pull; on 2026-05-24, the strict 1992-current internal-station audit found 11 of 24 Maryland jurisdictions ready and 13 needing fallback. With `--nearest-station-fallback`, the metadata audit covered all 24 Maryland jurisdictions by assigning the nearest qualifying Maryland station where no internal long-history station exists. `noaa-backfill-county` discovers county stations, selects long-coverage stations, and writes raw station plus daily observation CSVs with append/dedupe semantics. `noaa-backfill-maryland` loops that same county runner across all Maryland jurisdictions, or a repeated `--county-fips` subset for smoke runs, and can use `--nearest-station-fallback` for full-state runs. The full 1992-01-01 to 2026-05-24 Maryland run completed on 2026-05-24 with 283,420 raw daily rows for 24/24 jurisdictions. `noaa-weather-features` converts those raw station observations to model-grain weekly and monthly feature CSVs; the 2026-05-24 transform produced 40,919 weekly rows and 9,421 monthly rows. NOAA does not provide humidity, soil, evapotranspiration, or rain/snow split fields, so those feature outputs carry nulls plus `feature_quality_flags` such as `no_humidity` and `no_soil_data`. Open-Meteo does not require an API key and remains a secondary reanalysis/gap-fill path. Census county reference ETL reads the 2024 Gazetteer county ZIP and writes 24 Maryland land/water area rows for density features. Census population ETL reads `CENSUS_API_KEY` from the environment for current Census PEP calls; the 1992-2023 Maryland pull completed on 2026-05-24 with 768 county-year denominator rows. Maryland DNR deer harvest ETL uses Census land area to compute a county-level deer harvest density proxy; the news-table pull covers 2019-20 through 2025-26, and `--include-annual-report-pdfs` extends the text-extractable historical series to 2011-12 through 2024-25. The default annual-report parser is `pypdfium2`; Docling is available as an explicit `--annual-report-parser docling` option for future OCR/table extraction work.

## api summary

Implemented local lookup:

* `tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty` – relative county-week seasonal Lyme baseline JSON, not per-bite probability.

Roadmap HTTP API:

* `GET /risk?fips=24003&tau=24` – one attachment duration
* `GET /risk?fips=24003&tau=12&tau=36&k=2` – multiple τ, two ticks
  See [`/api/api-spec.md`](api/api-spec.md).

## contribute

1. Fork → create feature branch → commit tests.
2. Run `pre-commit run --all-files`.
3. Open PR; CI must pass lint, unit, and mini‑model tests.

Good first issues are labelled **`help wanted`**.

## licence

* **Code:** MIT (see `LICENSE`).
* **Derived data:** CC‑BY 4.0.
* **Third‑party feeds:** retain their original public‑domain or CC terms.

## cite

```
@software{tickbiterisk,
  title = {TickBiteRisk: Maryland-first tickborne disease risk data toolkit},
  author = {Webb, Brock and Contributors},
  year   = 2025,
  url    = {https://github.com/yourhandle/tickbiterisk},
  doi    = {10.5281/zenodo.xxxxxxx}
}
```

(Manuscript: *arXiv:2506.xxxxx*).

## ai-generated assistance

Large‑language‑model tools (OpenAI GPT‑4o, June 2025) were used to accelerate code scaffolding, literature search, and first‑draft text suggestions. All AI outputs were reviewed and revised by the human authors, who take full responsibility for the final content.

## disclaimer

This project offers **informational estimates only** and is **not medical advice**.  Users should consult a healthcare professional for diagnosis or treatment decisions.

---

*Logo & badge graphics forthcoming.*
