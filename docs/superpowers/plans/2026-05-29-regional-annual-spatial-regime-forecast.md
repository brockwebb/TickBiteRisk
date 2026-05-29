# Regional Annual Spatial Regime Forecast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a forecast-safe localized spatial-regime branch to the regional annual forecast artifact.

**Architecture:** Keep `regional-spatial-regimes` as the transparent intermediate artifact and have `regional-annual-forecast` optionally consume its `feature_*` prior fields. The annual forecast uses the regime row for `forecast_origin_year + 1` by default because that regime row is built from data available through the origin year; it never reads `diagnostic_*` target outcomes. The public Maryland dashboard remains unchanged.

**Tech Stack:** Python stdlib CSV/dataclasses, Typer CLI, pytest, ruff.

---

### Task 1: Annual Forecast Model Branch

**Files:**
- Modify: `tickbiterisk/modeling/regional_annual_forecast.py`
- Modify: `tickbiterisk/modeling/regional_annual_forecast_build.py`
- Modify: `tests/test_regional_annual_forecast.py`

- [x] **Step 1: Write failing model tests**

Add a test that writes a spatial-regime county-year fixture with `year == 2022` for a 2023 target / 2021 origin forecast. The fixture must include:

```text
source_file_sha256,regional_adjacency_sha256,county_fips,year,spatial_regime_id,feature_regime_trailing_mean_incidence_per_100k,diagnostic_actual_regime_incidence_per_100k,model_feature_quality_flags
```

Assert that `build_regional_annual_forecast(..., regional_spatial_regimes_path=regimes)` emits `empirical_bayes_spatial_regime_incidence`, uses the `feature_regime_trailing_mean_incidence_per_100k` prior, ignores the diagnostic value, carries localized/forecast-safe/not-public-default flags, and records the regime path/hash/run feature year.

- [x] **Step 2: Run RED**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_annual_forecast.py::test_regional_annual_forecast_uses_spatial_regime_prior_not_diagnostic_actual -q
```

Expected: fail because the keyword, schema fields, and model branch do not exist.

- [x] **Step 3: Implement branch**

Add optional builder arguments:

```python
regional_spatial_regimes_path: Path | None = None
regional_spatial_regime_feature_year: int | None = None
```

Read required regime columns and validate `source_file_sha256` against the regional incidence panel hash. If `regional_spatial_regime_feature_year` is omitted, use `forecast_origin_year + 1`. For each forecast county, shrink the county origin-window mean toward `feature_regime_trailing_mean_incidence_per_100k` with the existing `shrinkage_strength`.
Reject feature years greater than `forecast_origin_year + 1`, and reject a
supplied regime file when it has no rows for the selected feature year.

- [x] **Step 4: Update schema writer**

Add run columns:

```text
regional_spatial_regimes_path
regional_spatial_regimes_sha256
regional_spatial_regime_feature_year
```

Prediction columns do not need new fields because the model branch is self-describing through `model_name`, `model_family`, `feature_profile`, and flags.

- [x] **Step 5: Run GREEN**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_annual_forecast.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check tickbiterisk/modeling/regional_annual_forecast.py tickbiterisk/modeling/regional_annual_forecast_build.py tests/test_regional_annual_forecast.py
```

Expected: pass.

### Task 2: CLI Wiring

**Files:**
- Modify: `tickbiterisk/cli.py`
- Modify: `tests/test_cli_regional_annual_forecast.py`

- [x] **Step 1: Write failing CLI tests**

Add a CLI test that passes:

```bash
tickbiterisk etl regional-annual-forecast \
  --regional-spatial-regimes-path regional_spatial_regimes.csv \
  --regional-spatial-regime-feature-year 2022
```

Assert the prediction CSV contains `empirical_bayes_spatial_regime_incidence` and the run CSV records the regime path/hash/feature year. Add a clean failure test for a missing regime path.

- [x] **Step 2: Run RED**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_regional_annual_forecast.py -q
```

Expected: fail because the CLI options do not exist.

- [x] **Step 3: Implement CLI wiring**

Add options `--regional-spatial-regimes-path` and `--regional-spatial-regime-feature-year`, validate the optional file path, reject feature-year overrides when no regime path is supplied, and pass both through to the builder.

- [x] **Step 4: Run GREEN**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_annual_forecast.py tests/test_cli_regional_annual_forecast.py -q
```

Expected: pass.

### Task 3: Docs, Live ETL, Verification, Commit

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`

- [x] **Step 1: Update docs**

Document the optional regional annual forecast branch as a research-only localized spatial-regime branch. State that it consumes only `feature_*` regime priors, validates the incidence hash, defaults the regime feature year to `forecast_origin_year + 1`, and is not the public Maryland default.

- [x] **Step 2: Run live annual forecast with regimes**

```bash
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-annual-forecast \
  --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv \
  --regional-population-path build/etl/regional-population/midatlantic_county_population_year.csv \
  --regional-spatial-regimes-path build/etl/regional-spatial-regimes/regional_spatial_regime_county_year.csv \
  --target-year 2026 \
  --as-of-date 2026-05-29 \
  --data-cutoff-date 2023-12-31 \
  --source-vintage cdc_lyme_county_dashboard_2023 \
  --update-mode pre_update \
  --output-dir build/etl/regional-annual-forecast
```

- [x] **Step 3: Full verification**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl
npm run test:dashboard
node --check public/app.js
git diff --check
```

- [x] **Step 4: Commit**

```bash
git add README.md docs/data-manifest.md docs/etl-pipeline.md docs/superpowers/plans/2026-05-29-regional-annual-spatial-regime-forecast.md tickbiterisk/cli.py tickbiterisk/modeling/regional_annual_forecast.py tickbiterisk/modeling/regional_annual_forecast_build.py tests/test_regional_annual_forecast.py tests/test_cli_regional_annual_forecast.py
git commit -m "feat: add regional annual spatial regime forecast branch"
```

## Self-Review

This plan keeps the spatial-regime artifact transparent and forecast-safe, adds a single annual forecast model branch, validates source provenance, and avoids changing Maryland public outputs. The only open research question is promotion; this slice only materializes the branch for comparison and regional forecast review.
