# TickBiteRisk ETL Pipeline

## Current v0 ETL pipeline

The ETL layer turns acquired source files into reproducible Maryland county-year
and county-week artifacts. This pipeline builds research-grade static forecast
artifacts and a static public dashboard. It does not run a live backend forecast
service.

No live weekly ED scaler is wired into the current product. Weather, ecology,
deer, construction, and tick surveillance fields are model features or research
candidates until backtesting shows they improve the public score.

## Acquisition provenance contract

Every new acquired source should leave a saved, secret-free acquisition trail
before it feeds model features or public artifacts. At minimum, the trail should
record the source URL or API endpoint, a rerunnable command or procedure, the
citation URL or official evidence page, local raw path, checksum, retrieval timestamp,
parser method, extraction quality, redistribution/access notes, and modeling
caveats. Query URLs that include credentials must be logged only in
sanitized form; secrets stay in the local environment and never in manifests,
docs, or public JSON.

`tickbiterisk etl ecology-sources` now writes this contract into its raw source
manifest for catalog-style acquisitions. Because that command only acquires raw
files/pages, parser method and extraction quality are recorded as explicit
not-yet-evaluated placeholders until a downstream parser writes source-specific
extraction summaries. Direct API and raw-source ETL run manifests use
`acquisition_provenance.csv`; ENSO, EnviroAtlas, USDM drought, Census population, regional population, regional demographics, building permits, county reference, deer harvest, Open-Meteo weather backfill, NOAA weather primitives, NOAA weather backfill, Lyme outcomes, aggregate Lyme validation, regional Lyme outcomes, regional signals, NSSP coverage, seasonality baseline, tick status, and mast/acorn
are wired to that pattern,
preserving request URL, rerunnable command, parser/extraction status, derived
artifact checksums, and source caveats. Other API ETLs may still keep lineage in
source URL hashes and output fields, but this is the target shape for future
request/run manifests as those sources graduate into the modeling lane.
Run `tickbiterisk etl provenance-audit --root-dir build/etl` to scan
`acquisition_provenance.csv` and `source_manifest.csv` files for source URLs,
citation URLs, rerunnable commands, secret-free requests, derived-artifact
checksums, retrieval timestamps, parser methods, extraction quality, and
source caveats before promoting new data into model features or public
artifacts.

## Main flow

1. `tickbiterisk etl lyme-outcomes`
   - Reads ignored raw CDC Lyme source files and, when present, the official
     MDH 2013-2024 Lyme PDF.
   - Reconciles Maryland county-year Lyme counts across CDC public-use,
     dashboard, and geodata sources.
   - Includes MDH 2024 rows only, preserving CDC as canonical for overlapping
     2013-2023 history and flagging the 2024 state/probable-only caveats.
   - Writes `lyme_county_year_reconciled.csv` and
     `acquisition_provenance.csv` with official CDC/MDH source URLs, local
     raw-file checksums, parser method, contributed row count, and the
     surveillance-regime caveats needed by forecasting models.

1b. `tickbiterisk etl lyme-aggregate-validation`
   - Normalizes CDC dashboard exports for state/locality, U.S. Census region,
     and national Lyme cases/rates.
   - Writes `cdc_lyme_state_year.csv`, `cdc_lyme_region_year.csv`,
     `cdc_lyme_national_year.csv`, and `acquisition_provenance.csv`.
   - These rows are aggregate validation and regional-capacity anchors only;
     they are not county outcomes or direct exposure observations.

1c. `tickbiterisk etl regional-population`
   - Pulls keyless static Census county population CSVs for DE, DC, MD, PA,
     VA, and WV.
   - Writes `midatlantic_county_population_year.csv` and
     `acquisition_provenance.csv`.
   - These rows are denominator estimates for regional incidence/rate
     diagnostics, not exposure evidence. Boundary changes can create gaps; the
     first live run lacks Bedford city, VA denominators for 2010-2023.

1c-2. `tickbiterisk etl regional-demographics`
   - Pulls keyless static Census PEP county age/sex CSVs for DE, DC, MD, PA,
     VA, and WV.
   - Writes `midatlantic_age_demographics_county_year.csv` and
     `acquisition_provenance.csv`.
   - These rows are age-structure context for human-exposure research only;
     they are not tick-bite counts, direct exposure evidence, or Lyme outcomes.

1d. `tickbiterisk etl regional-lyme-outcomes`
   - Reshapes the CDC county dashboard export into DE, DC, MD, PA, VA, and WV
     county/county-equivalent annual Lyme totals for 2001-2023.
   - Writes `midatlantic_lyme_county_year.csv` and
     `acquisition_provenance.csv`.
   - This panel is a regional expansion/stress-test artifact for hotspot,
     spatial-neighbor, and capacity diagnostics; it does not replace the
     reconciled Maryland outcome target or the public Maryland default.

1e. `tickbiterisk etl regional-signals`
   - Derives Mid-Atlantic reported-case structure from
     `midatlantic_lyme_county_year.csv`.
   - Writes `midatlantic_regional_signals.csv`.
   - `diagnostic_*` columns describe same-year regional totals and county
     shares for retrospective hotspot/capacity review. `feature_*` columns use
     prior-year or trailing regional history and are the only columns intended
     for forecast-time model experiments.

1f. `tickbiterisk etl regional-hotspots`
   - Summarizes same-year Mid-Atlantic reported-case rank, share, hotspot
     tier, prior-year movement, and top-quintile entry/exit diagnostics.
   - Writes `midatlantic_hotspot_county_year.csv` and
     `midatlantic_hotspot_summary.csv`.
   - Every hotspot field is `diagnostic_*`; these outputs are for regional
     movement review and surveillance-regime inspection, not forecast-time
     public scoring.

1g. `tickbiterisk etl regional-incidence`
   - Joins the Mid-Atlantic reported-case panel to the Mid-Atlantic
     population denominator panel and computes county-year incidence per 100k.
   - Writes `midatlantic_lyme_incidence_county_year.csv` and
     `midatlantic_lyme_incidence_summary.csv`.
   - Missing denominators stay explicit. The first live run preserves missing
     Bedford city, VA rates for 2010-2023 rather than filling across a boundary
     change.

1h. `tickbiterisk etl regional-outcome-stress`
   - Runs rolling-origin, outcome-only stress tests against the Mid-Atlantic
     county panel.
   - Writes `regional_outcome_stress_runs.csv`,
     `regional_outcome_stress_predictions.csv`, and
     `regional_outcome_stress_metrics.csv`.
   - Compares prior-year county cases, trailing county cases, state capacity
     shares, Mid-Atlantic capacity shares, and empirical-Bayes shrunken share
     variants as transparent historical-range baselines. These are research
     diagnostics over reported case counts, not population-normalized public
     forecasts or latent true disease estimates.

1i. `tickbiterisk etl regional-incidence-stress`
   - Runs rolling-origin, incidence-rate stress tests against the Mid-Atlantic
     county incidence panel.
   - Writes `regional_incidence_stress_runs.csv`,
     `regional_incidence_stress_predictions.csv`, and
     `regional_incidence_stress_metrics.csv`.
   - Compares prior-year county incidence, trailing county incidence, and
     state/Mid-Atlantic empirical-Bayes shrinkage baselines as transparent
     historical-range tests. These are research diagnostics over reported
     incidence per 100k, not public forecasts or latent true disease estimates.

1j. `tickbiterisk etl regional-incidence-clusters`
   - Assigns county-years to low, moderate, high, and very-high regional
     incidence-pressure bands using only prior-year/trailing county incidence.
   - Writes `regional_incidence_cluster_runs.csv`,
     `regional_incidence_cluster_county_year.csv`, and
     `regional_incidence_cluster_summary.csv`.
   - The summary rows keep prior cluster min/mean/max incidence bands and
     same-year held-out actual incidence for diagnostics. These cluster bands
     are regional forecasting research artifacts, not selected public score
     inputs.

2. `tickbiterisk etl county-reference`
   - Builds Maryland county FIPS, names, area, and internal point reference.
   - Writes `county_reference.csv`.

3. `tickbiterisk etl census-population`
   - Fetches or refreshes county-year population denominators.
   - Use `--latest-only --append` to refresh the official Census 2024-2025
     county totals CSV without requiring a Census API key.
   - Writes `county_population_year.csv`.

4. `tickbiterisk etl noaa-weather-features`
   - Converts NOAA daily observations into weekly and monthly weather features.
   - Writes `weather_features_weekly.csv` and `weather_features_monthly.csv`.

4b. `tickbiterisk etl noaa-stations` and `tickbiterisk etl noaa-daily`
   - Pull NOAA CDO GHCND station discovery and daily station observations.
   - Write `acquisition_provenance.csv` with secret-free request URLs; the
     local `NOAA_TOKEN` request header is not logged.

4c. `tickbiterisk etl noaa-backfill-county` and
   `tickbiterisk etl noaa-backfill-maryland`
   - Orchestrate station selection plus daily station-observation pulls.
   - Write `acquisition_provenance.csv` for successful station-discovery and
     daily-observation records, using canonical NOAA CDO URLs and preserving
     selected-station IDs.

4a. `tickbiterisk etl weather-backfill-open-meteo-maryland`
   - Pulls chunked Open-Meteo archive weather at Maryland county internal
     points as a secondary reanalysis/gap-fill source.
   - Writes `weather_daily.csv`, `weather_features_weekly.csv`, and
     `weather_features_monthly.csv` under the chosen Open-Meteo output
     directory.
   - Writes `acquisition_provenance.csv` with saved chunk request URLs and
     artifact checksums.
   - `tickbiterisk etl open-meteo-weather-features` can rebuild weekly/monthly
     features from an existing Open-Meteo daily CSV without another API call.

5. `tickbiterisk etl deer-harvest`
   - Normalizes Maryland DNR deer harvest tables and text-extractable annual
     reports.
   - Writes `maryland_dnr_deer_harvest.csv` and
     `acquisition_provenance.csv`.

6. `tickbiterisk etl ecology-sources`
   - Catalogs NLCD/MRLC, Census BPS, mast/acorn, and related ecological source
     files.
   - Writes `source_manifest.csv`.

7. `tickbiterisk etl building-permits`
   - Normalizes Census county building permit data as a contact/land-use
     pressure proxy.
   - Writes `maryland_building_permits_county_year.csv`.

8. `tickbiterisk etl contact-pressure`
   - Combines building permits, population, and county area into per-capita and
     per-square-mile features, including prior-year and trailing construction
     pressure lags for modeling.
   - Writes `contact_pressure_features_county_year.csv`.

9. `tickbiterisk etl mast-acorn`
   - Extracts text-supported Western Maryland DNR rolling mast/acorn tables.
   - Writes source-report rows, extraction summaries, and
     `acquisition_provenance.csv` with PDF source URLs, parser method,
     extraction status, raw/output checksums, and study-plot caveats.
   - Optional manual observations remain separate, anecdotal, and
     not-public-default.

10. `tickbiterisk etl usdm-drought`
    - Pulls U.S. Drought Monitor county weekly DSCI and severity statistics.
    - Writes `usdm_drought_weekly.csv` and `usdm_drought_county_year.csv`.

11. `tickbiterisk etl enviroatlas-habitat`
    - Pulls EPA EnviroAtlas county landscape habitat fields for Maryland.
    - Writes `enviroatlas_county_habitat.csv`.

11a. `tickbiterisk etl enso-oni`
    - Pulls the NOAA CPC ONI ASCII table as a global ENSO climate context
      source.
    - Writes `noaa_cpc_oni_seasons.csv` and
      `noaa_cpc_oni_model_year_features.csv`.
    - Model-year rows use only complete 12-season prior years and remain
      optional; ONI is not Maryland-specific and is not a public-default input.

11b. `tickbiterisk etl tick-status`
    - Normalizes local CDC Ixodes, pathogen, and lone-star tick status
      workbooks into Maryland county status features. The current default
      metadata targets CDC May 2026 workbook files covering status through
      2025 for Ixodes/pathogens and the 2025 lone-star map data.
    - Writes `tick_vector_status.csv`, `tick_pathogen_status.csv`,
      `lone_star_status.csv`, `tick_status_county_features.csv`, and
      `acquisition_provenance.csv` with workbook checksums, parser methods,
      row counts, and status-only/not-prevalence caveats.

11c. `tickbiterisk etl nssp-coverage`
    - Downloads or reads the public CDC NSSP county coverage table and
      normalizes Maryland emergency-care participation status.
    - Writes `nssp_coverage_county_status.csv` and
      `acquisition_provenance.csv`.
    - This is coverage feasibility only: it is not a tick-bite ED feed, not
      a Lyme outcome, and not a current public model input.

12. `tickbiterisk etl seasonality-baseline`
    - Normalizes CDC Lyme onset exports by month and MMWR week.
    - Writes `seasonality_observations.csv`, `seasonality_baseline.csv`, and
      `acquisition_provenance.csv` with official CDC source citation, raw-file
      checksums, parser method, row counts, and national-curve caveats.

13. `tickbiterisk etl model-features`
    - Joins Lyme outcomes, population, timing-safe prior-year population
      growth, weather, deer, contact-pressure, construction lags, prior-year
      mast/acorn, USDM drought, EnviroAtlas habitat, complete prior-year ONI,
      and optional surveillance features into the county-year feature matrix.
    - Writes `model_features_county_year.csv`.

14. `tickbiterisk etl county-adjacency`
    - Derives directed Maryland county-neighbor pairs from public county
      GeoJSON using shared boundary segments.
    - Writes `md_county_adjacency.csv`.

15. `tickbiterisk etl model-design-matrix`
    - Converts the feature panel into numeric model inputs with missingness
      indicators, optional prior-year neighbor incidence features, optional
      regional signal features, a fixed-scale ecological pressure composite,
      and a schema sidecar.
    - Writes `model_design_matrix_county_year.csv` and
      `model_design_matrix_schema.json`.

16. `tickbiterisk etl model-compare`
    - Runs rolling-origin comparisons across transparent baseline and ridge
      branches, including forecast spatial and forecast-safe regional signal
      lanes when those optional feature columns are present.
    - Writes `model_comparison_runs.csv`,
      `model_comparison_predictions.csv`,
      `model_comparison_intervals.csv`, `model_comparison_metrics.csv`, and
      `model_comparison_summary.csv`.

17. `tickbiterisk etl model-diagnostics`
    - Summarizes comparison predictions and bootstrap intervals into research
      diagnostics for branch uncertainty, surveillance-regime checks, regional
      hotspot patterns, and capacity-sensitive error review.
    - Also writes `forecast_update_audit.csv`,
      `forecast_update_summary.csv`, and
      `forecast_calibration_summary.csv`, which compare pre-update
      rolling-origin forecasts with newly observed held-out outcomes using
      explicit as-of, data-cutoff, source-vintage, and surveillance-regime
      fields.
    - The calibration summary records empirical observed-to-predicted case
      ratios and additive incidence offsets for later Bayesian or hierarchical
      update research; it is not a public score correction.
    - Writes diagnostics under the chosen model-diagnostics output directory.

17b. `tickbiterisk etl forecast-calibration-backtest`
    - Applies forecast-safe shrunken calibration multipliers learned only from
      prior update rows for the same model branch.
    - Writes `forecast_calibration_backtest_runs.csv`,
      `forecast_calibration_backtest_predictions.csv`, and
      `forecast_calibration_backtest_metrics.csv`.
    - This is a falsification harness for calibration/update ideas. A
      calibration multiplier can remain useful as a research prior even when it
      does not improve held-out MAE enough to become a public correction.

18. `tickbiterisk etl county-week-risk`
    - Applies CDC weekly Lyme seasonality to the selected annual model branch.
    - Writes `county_week_seasonal_risk_baseline.csv` and
      `risk_score_scale.csv`.

19. `tickbiterisk risk export-static`
    - Selects one unambiguous model/source/scale branch for public use.
    - Writes dashboard JSON files under `public/data`.

## Runtime lookup

The local lookup command reads the derived county-week forecast:

```bash
tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty
```

It converts the date to CDC MMWR week and returns the relative Maryland Lyme
forecast for that county-week. The value is not a personal infection
probability or a treatment recommendation.

## Idempotency and lineage

- Writers use stable keys and append/dedupe behavior or explicit replacement.
- Each derived artifact keeps source IDs, source SHA-256 values, branch labels,
  quality flags, or sidecar metadata where practical.
- Raw files live under ignored data paths.
- Public exports include model and source metadata so a static site can explain
  what produced each score.

## Source limitations kept visible

- Deer harvest is a host-pressure proxy, not direct deer population.
- Building permits are a contact/land-use pressure proxy, not proof of
  migration or exposure.
- Prior-year population growth is a demographic/contact-pressure proxy derived
  from Census denominators, not proof of exposure or new construction.
- The ecological pressure composite is a transparent fixed-scale average of
  timing-safe component proxies; component columns stay visible and should be
  reviewed alongside the index.
- Mast/acorn values are Western Maryland study-plot observations, not statewide
  countywide mast production; model joins use only prior-year values.
- USDM drought values are same-year retrospective observed conditions in the
  retrospective comparison, not a forecast-time drought forecast. Prior-year
  USDM drought summaries are also joined as timing-safe ecology candidates.
- EnviroAtlas habitat fields are static county context, not annual land-cover
  change.
- Same-year weather branches are retrospective comparisons unless replaced by a
  true forecast-time feature set.
- Spatial lag features use prior-year neighbor outcomes only; same-year
  neighbor outcomes are not forecast-safe.
- MDH 2024 Lyme rows are latest-outcome context, not a CDC public-use update.
  They join into local model features only because matching Census 2024
  population denominators and NOAA 2024 weather aggregates are now present.
- The current population output mixes Census API-era 2020-2023 rows with
  Vintage 2025 CSV rows for 2024-2025; use source IDs and vintages when
  comparing denominators across vintages.

Last updated: 2026-05-28.
