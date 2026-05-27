# TickBiteRisk ETL Pipeline

## Current v0 ETL pipeline

The ETL layer turns acquired source files into reproducible Maryland county-year
and county-week artifacts. The current pipeline supports model comparison and a
static public dashboard. It does not run a live disease forecast service.

No live weekly ED scaler is wired into the current product. Weather, ecology,
deer, construction, and tick surveillance fields are model features or research
candidates until backtesting shows they improve the public score.

## Main flow

1. `tickbiterisk etl lyme-outcomes`
   - Reads ignored raw CDC Lyme source files.
   - Reconciles Maryland county-year Lyme counts across CDC public-use,
     dashboard, and geodata sources.
   - Writes `lyme_county_year_reconciled.csv`.

2. `tickbiterisk etl county-reference`
   - Builds Maryland county FIPS, names, area, and internal point reference.
   - Writes `county_reference.csv`.

3. `tickbiterisk etl census-population`
   - Fetches or refreshes county-year population denominators.
   - Writes `county_population_year.csv`.

4. `tickbiterisk etl noaa-weather-features`
   - Converts NOAA daily observations into weekly and monthly weather features.
   - Writes `weather_features_weekly.csv` and `weather_features_monthly.csv`.

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

12. `tickbiterisk etl seasonality-baseline`
    - Normalizes CDC Lyme onset exports by month and MMWR week.
    - Writes `seasonality_observations.csv` and `seasonality_baseline.csv`.

13. `tickbiterisk etl model-features`
    - Joins Lyme outcomes, population, weather, deer, contact-pressure,
      construction lags, prior-year mast/acorn, USDM drought, EnviroAtlas
      habitat, and optional surveillance features into the county-year feature
      matrix.
    - Writes `model_features_county_year.csv`.

14. `tickbiterisk etl model-design-matrix`
    - Converts the feature panel into numeric model inputs with missingness
      indicators and a schema sidecar.
    - Writes `model_design_matrix_county_year.csv` and
      `model_design_matrix_schema.json`.

15. `tickbiterisk etl model-compare`
    - Runs rolling-origin comparisons across transparent baseline and ridge
      branches.
    - Writes `model_comparison_runs.csv`,
      `model_comparison_predictions.csv`, `model_comparison_metrics.csv`, and
      `model_comparison_summary.csv`.

16. `tickbiterisk etl county-week-risk`
    - Applies CDC weekly Lyme seasonality to the selected annual model branch.
    - Writes `county_week_seasonal_risk_baseline.csv` and
      `risk_score_scale.csv`.

17. `tickbiterisk risk export-static`
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

Last updated: 2026-05-27.
