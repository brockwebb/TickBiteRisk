# TickBiteRisk

## mission

Build a transparent, Maryland-first tickborne disease risk data product from
open public data. The current implementation communicates relative county-week
Lyme risk baselines and a single-bite Lyme decision-support score. Calibrated
absolute infection probabilities for any U.S. county remain a research goal.

This project ships as self-hosted code; we do not currently provide a public API.

## current build status

The active implementation is a Maryland-first ETL, modeling, and static
dashboard prototype. The current code handles source cataloging, Maryland Lyme
county-year reconciliation, CDC seasonality baselines, tick/vector status
normalization, weather and ecological feature assembly, model comparison,
county-week seasonal risk baselines, runtime lookup over derived risk files,
static public JSON export, and a Postgres-ready warehouse schema.

The implemented product-facing bridges today are:

- `tickbiterisk risk lookup`, which reads the derived county-week baseline and
  returns plain JSON.
- `tickbiterisk risk single-bite`, which combines that baseline with tick
  identity, stage, attachment time, engorgement, removal timing, and CDC
  prophylaxis consideration criteria.
- `tickbiterisk risk export-static`, which writes public-safe derived JSON files
  for the static web product.
- `public/`, which can be served directly or published through GitHub Pages.

## quick start (current cli)

The current local Python path is the Maryland ETL plus runtime lookup against
derived CSV artifacts.

```bash
python -m pip install -e ".[dev]"

tickbiterisk risk lookup \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --pretty

tickbiterisk risk single-bite \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --tick-species blacklegged \
  --tick-stage nymph \
  --attachment-hours 40 \
  --engorgement engorged \
  --hours-since-removal 24 \
  --doxycycline-safe \
  --pretty

tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir build/public-risk
```

The `dev` extra is intentionally light for CI. Install
`python -m pip install -e ".[ocr]"` when you want the optional Docling parser
for PDF/OCR review.

The lookup output is a relative Maryland county-week seasonal Lyme baseline.
The single-bite output is a decision-support score and CDC criteria explainer.
Neither output is an absolute infection probability, diagnosis, treatment
recommendation, or weather-adjusted forecast.

## quick start (static dashboard)

The committed `public/data` files are derived, public-safe artifacts. Serve the
dashboard locally with:

```bash
python -m http.server 8000 --directory public
```

Then open `http://localhost:8000`.

GitHub Pages deployment uses the committed `public/` directory and requires no
runtime secrets or raw data access.

## data sources

| feed | current role |
| --- | --- |
| CDC Lyme public-use geography | County-year outcome spine |
| CDC Lyme dashboard/geodata exports | Reconciliation and validation context |
| CDC Lyme seasonality | Weekly/monthly disease-onset allocation |
| NOAA GHCND daily observations | Historical weather feature candidates |
| Census population and geography | Incidence denominators, county names, and land area |
| Maryland DNR deer harvest | County-season host-pressure proxy |
| CDC tick vector/pathogen status | Static surveillance status feature candidates |
| Census building permits | Contact/land-use pressure proxy |
| NLCD/MRLC land cover | Habitat source acquired for deeper feature extraction |
| Maryland DNR mast/acorn reports | Western Maryland study-plot ecology; prior-year model candidate |
| U.S. Drought Monitor | Retrospective county-year drought context |
| EPA EnviroAtlas | Static county habitat/context fields |
| USDA FIA | Official forest-composition source cataloged for future extraction |

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
tickbiterisk etl model-design-matrix --model-features-path build/etl/model/model_features_county_year.csv --output-dir build/etl/model
tickbiterisk etl model-compare --design-matrix-path build/etl/model/model_design_matrix_county_year.csv --output-dir build/etl/model-comparison
tickbiterisk etl model-backtest --model-features-path build/etl/model/model_features_county_year.csv --output-dir build/etl/backtest
tickbiterisk etl county-week-risk --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --seasonality-baseline-path build/etl/seasonality/seasonality_baseline.csv --output-dir build/etl/county-week-risk
tickbiterisk etl deer-harvest --county-reference-path build/etl/county-reference/county_reference.csv --output-dir build/etl/deer-harvest
tickbiterisk etl deer-harvest --county-reference-path build/etl/county-reference/county_reference.csv --output-dir build/etl/deer-harvest --include-annual-report-pdfs
tickbiterisk etl ecology-sources --raw-dir data/raw/ecology --manifest-path build/etl/ecology/source_manifest.csv
tickbiterisk etl building-permits --start-year 2000 --end-year 2025 --output-dir build/etl/building-permits
tickbiterisk etl contact-pressure --output-dir build/etl/contact-pressure
tickbiterisk etl mast-acorn --raw-dir data/raw/ecology/mast --output-dir build/etl/mast
tickbiterisk etl usdm-drought --start-year 2000 --end-year 2023 --output-dir build/etl/usdm-drought
tickbiterisk etl enviroatlas-habitat --output-dir build/etl/enviroatlas
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
tickbiterisk risk export-static --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv --model-summary-path build/etl/model-comparison/model_comparison_summary.csv --output-dir build/public-risk
```

Ecology source acquisition downloads official Annual NLCD/MRLC, Census BPS, Maryland DNR mast, EPA EnviroAtlas, USDA FIA, Maryland DNR archery survey, and USDA CDL source pages/files into ignored raw storage and writes a source manifest. `lyme-outcomes` reconciles the ignored raw CDC Lyme CSV exports into `lyme_county_year_reconciled.csv`; the 2026-05-25 live smoke wrote 700 Maryland county-year outcome rows for 24 jurisdictions from 1992-2023, preserving 33 source conflicts for review. `seasonality-baseline` turns CDC Lyme disease-onset month/week exports into 910 normalized seasonal observations and 65 empirical baseline rows, using annual shares rather than raw case levels because onset-dashboard totals are diagnostic rather than final surveillance totals. `mast-acorn` extracts 60 structured Western Maryland DNR source-report rows covering 2013-2021 study-plot acorn tables for Garrett, Allegany, Washington, and Frederick; model features use those values only as prior-year ecology context. `usdm-drought` materializes U.S. Drought Monitor weekly and county-year summaries for retrospective drought context; `enviroatlas-habitat` materializes static EPA county habitat fields. `model-features` joins Lyme outcomes to population, calendar-apportioned weekly NOAA weather, optional contact pressure and construction lags, optional prior-season deer harvest, optional prior-year mast/acorn, optional USDM drought, optional EnviroAtlas habitat, and static tick status; `model-design-matrix` converts that auditable joined panel into numeric features, lagged incidence features, missingness indicators, one-hot tick status fields, and expanded quality flags for the current v0 model comparison. `model-compare` runs rolling-origin annual comparisons from the numeric design matrix across transparent baselines, empirical Bayes, and ridge profiles; the 2026-05-27 expanded ecology run still ranked `linear_blend_baseline` first, so drought/habitat/construction-lag features remain research-lane inputs rather than the public default. `county-week-risk` converts selected annual model-comparison predictions plus a weekly onset curve into a relative county-week seasonal baseline. `risk lookup` turns that derived CSV into an API-ready JSON payload by county/date, using CDC MMWR week boundaries and the latest available baseline year when the requested year is not present. `risk export-static` selects one unambiguous derived score branch and writes public JSON artifacts with the latest available baseline per county/MMWR week, county metadata, model card, source catalog, and manifest; it does not publish raw data or require database credentials. NOAA CDO/GHCND is the primary observed historical weather source and reads `NOAA_TOKEN` from the environment. Open-Meteo does not require an API key and remains a secondary reanalysis/gap-fill path. Census population ETL reads `CENSUS_API_KEY` from the environment for current Census PEP calls. Maryland DNR deer harvest ETL uses Census land area to compute a county-level deer harvest density proxy. The default annual-report parser is `pypdfium2`; Docling remains available as an explicit parser option for future OCR/table extraction work.

## static dashboard

Build public dashboard assets:

```bash
tickbiterisk dashboard build-assets \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir public/data
```

Run locally:

```bash
python -m http.server 8000 --directory public
```

Open `http://localhost:8000`.

GitHub Pages deployment is handled by GitHub Actions from the committed `public/`
directory. In repository Settings > Pages, set the source to GitHub Actions; no
secrets or raw data access are required because `public/data` is the public-safe
committed data product used by the static dashboard.

## api summary

Implemented local lookup:

* `tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty` – relative county-week seasonal Lyme baseline JSON, not per-bite probability.
* `tickbiterisk risk single-bite --county-fips 24003 --date 2026-05-26 --tick-species blacklegged --tick-stage nymph --attachment-hours 40 --engorgement engorged --hours-since-removal 24 --doxycycline-safe --pretty` – single-bite Lyme decision-support score and CDC prophylaxis criteria summary, not an absolute infection probability.
* `tickbiterisk risk export-static --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv --model-summary-path build/etl/model-comparison/model_comparison_summary.csv --output-dir build/public-risk` – public-safe derived JSON bundle for static web/runtime use.

Roadmap HTTP API:

* `GET /risk?fips=24003&tau=24` – one attachment duration
* `GET /risk?fips=24003&tau=12&tau=36&k=2` – multiple τ, two ticks
  See [`/api/api-spec.md`](api/api-spec.md).

## contribute

1. Fork → create feature branch → commit tests.
2. Run `ruff check .`, `pytest -q`, `node --check public/app.js`, `npm ci`,
   and `npm run test:dashboard`.
3. Open PR; CI must pass lint, unit, public-data, and dashboard smoke tests.

Good first issues are labelled **`help wanted`**.

## licence

* **Code:** MIT (see `LICENSE`).
* **Derived data:** CC‑BY 4.0.
* **Third‑party feeds:** retain their original public‑domain or CC terms.

## cite

Formal citation metadata is not published yet. Until then, cite the repository
name, commit, and data/model artifact version used for your analysis.

## ai-generated assistance

Large-language-model tools were used to accelerate code scaffolding, literature
search, and first-draft text suggestions. All AI outputs were reviewed and
revised by the human authors, who take full responsibility for the final
content.

## disclaimer

This project offers **informational estimates only** and is **not medical
advice**. Users should follow CDC guidance and consult a healthcare professional
for diagnosis or treatment decisions.
