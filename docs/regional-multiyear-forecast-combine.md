# Regional Multi-Year Forecast Combine

The deployed regional research dashboard (`public/research-data/regional/`) is
driven by a **multi-year** annual forecast covering 2024, 2025, and 2026. That
multi-year input is **not** produced by a single command — it is three
single-year forecast runs concatenated. The README's single-year
`etl regional-annual-forecast --target-year 2026` recipe produces only one year
and is **not** the path that produced the deployed forecast. This page
documents the actual combine.

The command sequence below is **verified**: run on 2026-05-31 it reproduces the
deployed artifacts byte-for-byte — `regional_annual_forecast_predictions.csv`
→ sha256 `247da9ea…` and `regional_annual_forecast_intervals.csv` →
sha256 `95c90156…`, the exact values recorded in
`model_card.annual_prediction_source`.

## Inputs

Three per-year forecast runs, all sharing forecast origin year **2023** and
identical parameters (`min-train-years 3`, `lookback-years 3`,
`shrinkage-strength 5.0`, spatial regimes), differing only in `--target-year`:

- `target2024_origin2023`, `target2025_origin2023`, `target2026_origin2023` —
  1,698 prediction rows each (5,094 combined).

Each run consumes (all under `build/etl/`, derived from `data/raw/lyme/…`):

- `regional-incidence/midatlantic_lyme_incidence_county_year.csv`
- `regional-population/midatlantic_county_population_year.csv`
- `regional-spatial-regimes/regional_spatial_regime_county_year.csv`
- `regional-incidence-stress/regional_incidence_stress_predictions.csv`
  (residual source for the intervals)

## The combine

For each target year, generate predictions and intervals into a per-year
scratch dir; then concatenate the three years (header once) into the multi-year
files. The forecast command **overwrites** its output dir, so per-year runs
must go to separate dirs before concatenation — running them into one dir would
leave only the last year.

```bash
for Y in 2024 2025 2026; do
  python -m tickbiterisk.cli etl regional-annual-forecast \
    --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv \
    --regional-population-path build/etl/regional-population/midatlantic_county_population_year.csv \
    --regional-spatial-regimes-path build/etl/regional-spatial-regimes/regional_spatial_regime_county_year.csv \
    --target-year "$Y" --forecast-origin-year 2023 \
    --as-of-date 2026-05-29 --data-cutoff-date 2023-12-31 \
    --source-vintage cdc_lyme_county_dashboard_2023 --update-mode pre_update \
    --output-dir build/etl/regional-annual-forecast-year-"$Y"

  python -m tickbiterisk.cli etl regional-annual-forecast-intervals \
    --forecast-predictions-path build/etl/regional-annual-forecast-year-"$Y"/regional_annual_forecast_predictions.csv \
    --regional-incidence-stress-predictions-path build/etl/regional-incidence-stress/regional_incidence_stress_predictions.csv \
    --output-dir build/etl/regional-annual-forecast-year-"$Y"
done

# Concatenate the three years into the multi-year inputs (header from the first only).
# NOTE: this concat is currently a manual step — there is no CLI subcommand or repo
# script for it. If it becomes routine, promote it to a `tickbiterisk` subcommand.
mkdir -p build/etl/regional-annual-forecast-multiyear
for name in regional_annual_forecast_predictions regional_annual_forecast_intervals; do
  { head -1 build/etl/regional-annual-forecast-year-2024/$name.csv
    for Y in 2024 2025 2026; do tail -n +2 build/etl/regional-annual-forecast-year-$Y/$name.csv; done
  } > build/etl/regional-annual-forecast-multiyear/$name.csv
done
```

`--forecast-origin-year 2023` is shown explicitly to match the recorded
run_ids. The README single-year recipe omits it; it then defaults to the latest
incidence year, which is 2023 for the current panel, so both yield origin 2023.

## Outputs

- `build/etl/regional-annual-forecast-multiyear/regional_annual_forecast_predictions.csv`
  — 5,094 rows; sha256 `247da9ea…` (recorded as
  `model_card.annual_prediction_source.sha256`).
- `…/regional_annual_forecast_intervals.csv` — 5,094 rows; sha256 `95c90156…`
  (recorded as `…interval_sha256`).

These two CSVs feed `dashboard build-regional-research-assets`
(`tickbiterisk/dashboard_assets.py`) via `--regional-annual-forecast-path`
(predictions) to produce the regional bundle's
`regional_county_risk_weekly.json` and annual records. The provenance-stamped
rebuild (`scripts/rebuild_regional_bundle.sh`) consumes these multi-year CSVs as
fixed inputs and reports if their recorded SHAs drift.

## Relation to the single-year recipe

The README pipeline block runs `etl regional-annual-forecast --target-year 2026`
once, writing `build/etl/regional-annual-forecast/` (one year, 1,698 rows). That
is a component, **not** the deployed forecast input. The deployed dashboard
forecast is the multi-year combine above
(`build/etl/regional-annual-forecast-multiyear/`, three years, 5,094 rows). When
refreshing the regional forecast, use this combine — not the single-year
command alone.
