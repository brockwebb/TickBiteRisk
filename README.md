# TickBiteRisk

## mission

Build a transparent, Maryland-first tickborne disease risk forecasting research
product from open public data. The current implementation is a risk forecasting tool
that communicates relative county-week Lyme forecasts, forecast-update diagnostics, and a
single-bite Lyme decision-support score. Calibrated absolute infection
probabilities for any U.S. county remain a research goal.

This project ships as self-hosted code; we do not currently provide a public API.

## current build status

The active implementation is a Maryland-first ETL, modeling, and static
dashboard prototype. The current code handles source cataloging, Maryland Lyme
county-year reconciliation, CDC seasonality baselines, tick/vector status
normalization, weather and ecological feature assembly, model comparison,
county-week seasonal risk forecasts, runtime lookup over derived risk files,
static public JSON export, and a Postgres-ready warehouse schema.

The implemented product-facing bridges today are:

- `tickbiterisk risk lookup`, which reads the derived county-week forecast and
  returns plain JSON.
- `tickbiterisk risk single-bite`, which combines that forecast with tick
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

The lookup output is a relative Maryland county-week seasonal Lyme forecast.
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

## why forecast Lyme risk?

Official Lyme surveillance data often lag the conditions people are living
through now. Final county case counts may arrive months or years after the tick
season, while households, clinicians, parks, schools, and public health teams
need actionable risk context during the season itself.

TickBiteRisk treats forecasting as a way to make uncertainty visible before all
official data are final. The public score is informational risk context, not a
diagnosis, treatment recommendation, or certainty about any individual bite.

## how forecast updates work

The current public score starts with a selected annual comparison branch and a
static CDC seasonality prior. Research forecast lanes also test historical Lyme
incidence, forecast-safe ecology and habitat context, host and human exposure
proxies, regional patterns, and surveillance caveats. When new information
arrives, the update-audit layer compares it with the prior forecast, labels the
source vintage and surveillance regime, and records whether the change looks
like disease-pressure signal, reporting-regime signal, or an ambiguous update.

That reconciliation is the path toward stronger Bayesian or hierarchical
forecasting: new information should update the next forecast with its caveats
attached, not silently overwrite the model as if every source were equally
stable truth.

## data sources

| feed | current role |
| --- | --- |
| CDC Lyme public-use geography | County-year outcome spine |
| CDC Lyme dashboard/geodata exports | Reconciliation and validation context |
| CDC Lyme seasonality | Weekly/monthly disease-onset allocation |
| NOAA GHCND daily observations | Historical weather feature candidates |
| Census population and geography | Incidence denominators, county names, and land area |
| Census PEP county age/sex estimates | Regional demographic exposure-context proxy |
| Census ACS 5-year table summaries | Residential form, tenure, age, and density exposure-context proxy |
| Maryland DNR deer harvest | County-season host-pressure proxy |
| CDC tick vector/pathogen status | Static surveillance status feature candidates through 2025 |
| Census building permits | Contact/land-use pressure proxy |
| CDC NSSP coverage table | Emergency-care feed coverage feasibility only, not tick-bite counts |
| NLCD/MRLC land cover | Habitat source acquired for deeper feature extraction |
| Maryland DNR mast/acorn reports | Western Maryland study-plot ecology; prior-year model candidate |
| U.S. Drought Monitor | Retrospective county-year drought context |
| NOAA CPC/PSL ENSO indices | Global prior-year climate context candidates |
| EPA EnviroAtlas | Static county habitat/context fields |
| USDA FIA | Official forest-composition source cataloged for future extraction |

Full details: [`/docs/data-sources.md`](docs/data-sources.md)

## maryland ETL

The Maryland weather ETL has two acquisition paths: NOAA CDO/GHCND for observed station history, and Open-Meteo as a secondary reanalysis/gap-fill source using Census Gazetteer county internal points. The planned NOAA backfill range is 1992-01-01 through the current year.

```bash
tickbiterisk etl weather-locations --output-dir build/etl
tickbiterisk etl county-reference --output-dir build/etl/county-reference
tickbiterisk etl census-population --output-dir build/etl/population
tickbiterisk etl census-population --output-dir build/etl/population --latest-only --append
tickbiterisk etl lyme-outcomes --raw-dir data/raw/lyme --output-dir build/etl/lyme
tickbiterisk etl regional-population --output-dir build/etl/regional-population
tickbiterisk etl regional-demographics --output-dir build/etl/regional-demographics
tickbiterisk etl acs-exposure --year 2023 --output-dir build/etl/acs-exposure --append
tickbiterisk etl acs-exposure --year 2024 --output-dir build/etl/acs-exposure --append
tickbiterisk etl regional-lyme-outcomes --raw-dir data/raw/lyme --output-dir build/etl/regional-lyme
tickbiterisk etl regional-signals --regional-lyme-path build/etl/regional-lyme/midatlantic_lyme_county_year.csv --output-dir build/etl/regional-signals
tickbiterisk etl regional-hotspots --regional-lyme-path build/etl/regional-lyme/midatlantic_lyme_county_year.csv --output-dir build/etl/regional-hotspots
tickbiterisk etl regional-incidence --regional-lyme-path build/etl/regional-lyme/midatlantic_lyme_county_year.csv --regional-population-path build/etl/regional-population/midatlantic_county_population_year.csv --output-dir build/etl/regional-incidence
tickbiterisk etl regional-outcome-stress --regional-lyme-path build/etl/regional-lyme/midatlantic_lyme_county_year.csv --output-dir build/etl/regional-outcome-stress
tickbiterisk etl regional-incidence-stress --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv --output-dir build/etl/regional-incidence-stress
tickbiterisk etl regional-incidence-clusters --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv --output-dir build/etl/regional-incidence-clusters
tickbiterisk etl provenance-audit --root-dir build/etl
tickbiterisk etl nssp-coverage --county-reference-path build/etl/county-reference/county_reference.csv --output-dir build/etl/nssp-coverage
tickbiterisk etl seasonality-baseline --raw-dir data/raw/seasonality --output-dir build/etl/seasonality
tickbiterisk etl model-features --output-dir build/etl/model
tickbiterisk etl county-adjacency --county-geojson-path public/data/md_counties.geojson --output-dir build/etl/county-adjacency
tickbiterisk etl model-design-matrix --model-features-path build/etl/model/model_features_county_year.csv --county-adjacency-path build/etl/county-adjacency/md_county_adjacency.csv --regional-signals-path build/etl/regional-signals/midatlantic_regional_signals.csv --output-dir build/etl/model
tickbiterisk etl model-compare --design-matrix-path build/etl/model/model_design_matrix_county_year.csv --output-dir build/etl/model-comparison
tickbiterisk etl model-diagnostics --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --intervals-path build/etl/model-comparison/model_comparison_intervals.csv --as-of-date 2026-05-28 --data-cutoff-date 2024-12-31 --source-vintage 2024-inclusive-local --output-dir build/etl/model-diagnostics
tickbiterisk etl forecast-calibration-backtest --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --output-dir build/etl/forecast-calibration-backtest
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
tickbiterisk etl enso-oni --output-dir build/etl/enso
tickbiterisk etl enso-mei-v2 --output-dir build/etl/enso
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

Ecology source acquisition downloads official Annual NLCD/MRLC, Census BPS, Maryland DNR mast, EPA EnviroAtlas, USDA FIA, Maryland DNR archery survey, and USDA CDL source pages/files into ignored raw storage and writes a source manifest. `lyme-outcomes` reconciles the ignored raw CDC Lyme CSV exports and optional MDH 2013-2024 Lyme PDF into `lyme_county_year_reconciled.csv`; the 2026-05-28 live smoke wrote 724 Maryland county-year outcome rows for 24 jurisdictions from 1992-2024, preserving 33 source conflicts for review and adding 24 MDH-backed 2024 rows with probable-only/state-source caveats. `regional-population` pulls keyless static Census county population CSVs for DE/DC/MD/PA/VA/WV and writes 6,518 county-year denominator rows for 2001-2023 plus acquisition provenance; the only missing regional Lyme panel denominator years are Bedford city, VA, 2010-2023, a boundary-change caveat. `regional-demographics` pulls keyless static Census PEP age/sex CSVs for DE/DC/MD/PA/VA/WV and writes 4,245 county-year age-structure rows for 2010-2024; these are human exposure-context proxies, not tick-bite counts or disease outcomes. `acs-exposure` reads keyless 2023-2024 ACS 5-year table-based summary files plus the 2024 Census Gazetteer and writes 566 DE/DC/MD/PA/VA/WV county-equivalent residential-form, tenure, age, and density proxy rows with 9 provenance records; ACS values are rolling survey context, not annual observed exposure or disease truth. `regional-lyme-outcomes` reshapes the same CDC county dashboard export into `midatlantic_lyme_county_year.csv`, a 6,532-row DE/DC/MD/PA/VA/WV county-equivalent panel for regional stress tests, hotspot diagnostics, and future spatial model expansion; it is not the public Maryland default, and rows carry reported-cases, 2020 COVID disruption, and 2022+ case-definition caveats. `regional-signals` derives `midatlantic_regional_signals.csv`, keeping same-year regional totals under `diagnostic_*` columns and prior-year/trailing history under `feature_*` columns for forecast-safe model experiments. `regional-hotspots` writes count/share/rank movement diagnostics from the same panel; the live run wrote 6,532 county-year rows and 23 annual summaries, including top-quintile entry/exit counts that make regime breaks and hotspot movement easier to inspect. `regional-incidence` joins the regional Lyme panel to regional population denominators and writes 6,532 incidence diagnostic rows plus 23 summaries; 2010-2023 each preserve one missing denominator for Bedford city, VA rather than inventing rates. `regional-outcome-stress` writes count-based rolling-origin capacity diagnostics from that same regional panel; the latest live smoke wrote 28,968 prediction rows and 144 metric rows, with empirical-Bayes share shrinkage slightly improving the state and Mid-Atlantic capacity-share baselines, but prior-year county cases still ahead on overall case MAE. `regional-incidence-stress` writes population-normalized rolling-origin diagnostics from the Mid-Atlantic incidence panel; the live run wrote 19,256 prediction rows and 96 metric rows, and prior-year county incidence still had the lowest overall incidence MAE at 21.009541 per 100k. `regional-incidence-clusters` assigns county-years to forecast-safe low/moderate/high/very-high prior-incidence bands and writes 4,814 county-year assignments plus 68 capacity-band summaries; from 2007-2023, mean actual incidence rises from 13.373727 per 100k in the low band to 237.827443 per 100k in the very-high band. These rate-scale outputs are regional forecasting research diagnostics, not public Maryland score inputs or latent true disease estimates. `census-population --latest-only --append` materializes official Census 2024-2025 county totals from the keyless `CO-EST2025-alldata` CSV, bringing local Maryland population denominators to 816 rows for 1992-2025 while preserving source IDs and vintages. `seasonality-baseline` turns CDC Lyme disease-onset month/week exports into 910 normalized seasonal observations and 65 empirical baseline rows, using annual shares rather than raw case levels because onset-dashboard totals are diagnostic rather than final surveillance totals. `mast-acorn` extracts 60 structured Western Maryland DNR source-report rows covering 2013-2021 study-plot acorn tables for Garrett, Allegany, Washington, and Frederick; model features use those values only as prior-year ecology context. `usdm-drought` materializes U.S. Drought Monitor weekly and county-year summaries for same-year retrospective drought context and prior-year ecology candidates; `enviroatlas-habitat` materializes static EPA county habitat fields. `enso-oni` and `enso-mei-v2` materialize official keyless NOAA CPC/PSL global ENSO context artifacts; the latest live run wrote 915 ONI seasonal rows, 76 ONI complete prior-year feature rows, 576 MEI.v2 monthly rows, and 47 MEI.v2 complete prior-year feature rows, all flagged as global, not Maryland-specific, and not public-default without model evidence. `model-features` joins Lyme outcomes to population, timing-safe prior-year population growth, calendar-apportioned weekly NOAA weather, optional contact pressure and construction lags, optional prior-season deer harvest, optional prior-year mast/acorn, optional same-year and prior-year USDM drought, optional EnviroAtlas habitat, and static tick status; the 2024-inclusive local run wrote 700 county-year rows. `county-adjacency` derives shared-boundary Maryland county neighbors from public county GeoJSON; `model-design-matrix` converts that auditable joined panel into numeric features, lagged incidence features, optional prior-year neighbor incidence features, optional regional signal features, a fixed-scale ecological pressure composite, missingness indicators, one-hot tick status fields, and expanded quality flags for the current v0 model comparison. `model-compare` runs rolling-origin annual comparisons from the numeric design matrix across transparent baselines, empirical Bayes, and ridge profiles, including a forecast-safe regional signal lane when regional features are present; the 2026-05-28 2024-inclusive run ranked `prior_year_incidence` first, narrowly ahead of `linear_blend_baseline`, while spatial/ecology/regional/population-growth/composite-pressure features remain research-lane inputs rather than the public default. `model-diagnostics` now writes 4,320 forecast update audit rows and 230 empirical calibration rows; in the 2024 MDH probable-only regime, `linear_blend_baseline` observed cases were 1.609636x predicted cases, while `prior_year_incidence` was 1.277427x predicted cases. `forecast-calibration-backtest` then applies those ideas using only prior update evidence; the first live run wrote 4,320 calibrated predictions and 240 metrics, but default shrunken calibration worsened overall MAE for all branches, including `prior_year_incidence` from 18.21318 to 22.045798 per 100k and `linear_blend_baseline` from 18.47245 to 22.19535 per 100k. These calibration factors are research priors for future Bayesian updating, not automatic public score corrections. `county-week-risk` converts selected annual model-comparison predictions plus a weekly onset curve into a relative county-week seasonal forecast. `risk lookup` turns that derived CSV into an API-ready JSON payload by county/date, using CDC MMWR week boundaries and the latest available forecast year when the requested year is not present. `risk export-static` selects one unambiguous derived score branch and writes public JSON artifacts with the latest available forecast per county/MMWR week, county metadata, model card, source catalog, and manifest; it does not publish raw data or require database credentials. NOAA CDO/GHCND is the primary observed historical weather source and reads `NOAA_TOKEN` from the environment. Open-Meteo does not require an API key and remains a secondary reanalysis/gap-fill path. Census API-era Maryland population ETL can read `CENSUS_API_KEY` from the environment; regional population, regional demographics, ACS exposure, and latest Maryland county totals use public Census files. Maryland DNR deer harvest ETL uses Census land area to compute a county-level deer harvest density proxy. The default annual-report parser is `pypdfium2`; Docling remains available as an explicit parser option for future OCR/table extraction work.

Current ACS exposure note: `acs-exposure` now materializes supported 2023 and
2024 ACS 5-year vintages into one Mid-Atlantic panel when run with `--append`.
These are rolling-survey residential context proxies using 2024 Gazetteer land
area for density fields, not observed tick encounters, disease outcomes, or
public-default score inputs.

Current model-feature note: `model-features` now also joins optional complete
prior-year NOAA CPC ONI and NOAA PSL MEI.v2 climate-context artifacts when the
default ENSO outputs exist. `model-design-matrix` promotes those fields into
research-lane numeric predictors with missingness indicators; they remain
global climate context and are not public-default score inputs without
time-aware validation.

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

* `tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty` – relative county-week seasonal Lyme forecast JSON, not per-bite probability.
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
