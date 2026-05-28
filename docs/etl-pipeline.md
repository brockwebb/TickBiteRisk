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
extraction summaries. Direct API ETLs may still keep lineage in source URL
hashes and output fields, but the same contract is the target shape for future
API request/run manifests as those sources graduate into the modeling lane.

## Main flow

1. `tickbiterisk etl lyme-outcomes`
   - Reads ignored raw CDC Lyme source files and, when present, the official
     MDH 2013-2024 Lyme PDF.
   - Reconciles Maryland county-year Lyme counts across CDC public-use,
     dashboard, and geodata sources.
   - Includes MDH 2024 rows only, preserving CDC as canonical for overlapping
     2013-2023 history and flagging the 2024 state/probable-only caveats.
   - Writes `lyme_county_year_reconciled.csv`.

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

4a. `tickbiterisk etl weather-backfill-open-meteo-maryland`
   - Pulls chunked Open-Meteo archive weather at Maryland county internal
     points as a secondary reanalysis/gap-fill source.
   - Writes `weather_daily.csv`, `weather_features_weekly.csv`, and
     `weather_features_monthly.csv` under the chosen Open-Meteo output
     directory.
   - `tickbiterisk etl open-meteo-weather-features` can rebuild weekly/monthly
     features from an existing Open-Meteo daily CSV without another API call.

5. `tickbiterisk etl deer-harvest`
   - Normalizes Maryland DNR deer harvest tables and text-extractable annual
     reports.
   - Writes `maryland_dnr_deer_harvest.csv`.

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
   - Writes source-report rows and extraction summaries with study-plot caveats.

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

12. `tickbiterisk etl seasonality-baseline`
    - Normalizes CDC Lyme onset exports by month and MMWR week.
    - Writes `seasonality_observations.csv` and `seasonality_baseline.csv`.

13. `tickbiterisk etl model-features`
    - Joins Lyme outcomes, population, weather, deer, contact-pressure,
      construction lags, prior-year mast/acorn, USDM drought, EnviroAtlas
      habitat, complete prior-year ONI, and optional surveillance features into
      the county-year feature matrix.
    - Writes `model_features_county_year.csv`.

14. `tickbiterisk etl county-adjacency`
    - Derives directed Maryland county-neighbor pairs from public county
      GeoJSON using shared boundary segments.
    - Writes `md_county_adjacency.csv`.

15. `tickbiterisk etl model-design-matrix`
    - Converts the feature panel into numeric model inputs with missingness
      indicators, optional prior-year neighbor incidence features, and a schema
      sidecar.
    - Writes `model_design_matrix_county_year.csv` and
      `model_design_matrix_schema.json`.

16. `tickbiterisk etl model-compare`
    - Runs rolling-origin comparisons across transparent baseline and ridge
      branches, including the forecast spatial diagnostic lane.
    - Writes `model_comparison_runs.csv`,
      `model_comparison_predictions.csv`,
      `model_comparison_intervals.csv`, `model_comparison_metrics.csv`, and
      `model_comparison_summary.csv`.

17. `tickbiterisk etl model-diagnostics`
    - Summarizes comparison predictions and bootstrap intervals into research
      diagnostics for branch uncertainty, surveillance-regime checks, regional
      hotspot patterns, and capacity-sensitive error review.
    - Also writes `forecast_update_audit.csv` and
      `forecast_update_summary.csv`, which compare pre-update rolling-origin
      forecasts with newly observed held-out outcomes using explicit as-of,
      data-cutoff, source-vintage, and surveillance-regime fields.
    - Writes diagnostics under the chosen model-diagnostics output directory.

18. `tickbiterisk etl county-week-risk`
    - Applies CDC weekly Lyme seasonality to the selected annual model branch.
    - Writes `county_week_seasonal_risk_baseline.csv` and
      `risk_score_scale.csv`.

19. `tickbiterisk risk export-static`
    - Selects one unambiguous model/source/scale branch for public use.
    - Writes dashboard JSON files under `public/data`.

## Runtime lookup

The local lookup command reads the derived county-week baseline:

```bash
tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty
```

It converts the date to CDC MMWR week and returns the relative Maryland Lyme
baseline for that county-week. The value is not a personal infection
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
