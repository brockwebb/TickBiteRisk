# Drought Habitat Construction Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add USDM drought, EPA EnviroAtlas habitat, and lagged construction-pressure features to the Maryland county-year model comparison pipeline.

**Architecture:** Build each feature family as its own ETL module and CSV artifact, then join them through the existing `model-features` and `model-design-matrix` layers. Keep raw source features auditable and keep forecast-safe model selectors timing-aware.

**Tech Stack:** Python stdlib CSV/JSON/urllib, Typer CLI, existing dataclass writer patterns, pytest, ruff.

---

### Task 1: USDM Drought ETL

**Files:**
- Create: `tickbiterisk/etl/usdm_drought.py`
- Create: `tickbiterisk/etl/usdm_drought_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_usdm_drought.py`
- Test: `tests/test_cli_usdm_drought.py`

- [ ] Write failing parser tests for `GetDSCI` CSV rows and drought severity percent rows keyed by Maryland county FIPS and map date.
- [ ] Write failing aggregation tests for county-year fields: `usdm_dsci_mean`, `usdm_dsci_max`, `usdm_weeks_d0_or_worse`, `usdm_weeks_d1_or_worse`, `usdm_weeks_d2_or_worse`, `usdm_tick_season_dsci_mean`, `usdm_tick_season_weeks_d1_or_worse`.
- [ ] Implement URL builders and injectable fetchers so tests do not need live network access.
- [ ] Implement CSV writers for raw weekly and county-year drought feature outputs with stable sort/dedupe.
- [ ] Add `tickbiterisk etl usdm-drought` with `--start-year`, `--end-year`, `--output-dir`, and optional `--aoi MD`.
- [ ] Run focused tests and commit.

### Task 2: EPA EnviroAtlas Habitat ETL

**Files:**
- Create: `tickbiterisk/etl/enviroatlas.py`
- Create: `tickbiterisk/etl/enviroatlas_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_enviroatlas.py`
- Test: `tests/test_cli_enviroatlas.py`

- [ ] Write failing tests for parsing an ArcGIS REST JSON response with 24 Maryland county records.
- [ ] Map EnviroAtlas fields to stable output names: `forest_pct`, `forest_woody_wetland_pct`, `wetland_pct`, `emergent_wetland_pct`, `developed_pct`, `impervious_pct`, `agriculture_pct`, `pasture_hay_pct`, `cultivated_crop_pct`, `riparian_natural_45m_pct`, `riparian_forest_45m_pct`, `riparian_forest_woody_wetland_45m_pct`, `natural_land_cover_index`.
- [ ] Implement an injectable fetch path for the Maryland query URL.
- [ ] Write `enviroatlas_county_habitat.csv` with FIPS normalization and source URL hash.
- [ ] Add `tickbiterisk etl enviroatlas-habitat --output-dir build/etl/enviroatlas`.
- [ ] Run focused tests and commit.

### Task 3: Construction Lag Features

**Files:**
- Modify: `tickbiterisk/etl/contact_pressure.py`
- Modify: `tickbiterisk/etl/contact_pressure_build.py`
- Test: `tests/test_contact_pressure.py`

- [ ] Write failing tests showing prior-year and trailing 3-year construction metrics are computed from existing county-year contact pressure rows.
- [ ] Add fields: `units_authorized_per_sqmi_prior_year`, `units_authorized_per_100k_prior_year`, `units_authorized_per_sqmi_trailing_3yr_mean`, `units_authorized_per_100k_trailing_3yr_mean`, `units_authorized_per_sqmi_yoy_change`.
- [ ] Add `missing_construction_lag` quality flag when lag/trailing history is unavailable.
- [ ] Preserve existing contact-pressure output compatibility and stable key behavior.
- [ ] Run focused tests and commit.

### Task 4: Model Feature Joins

**Files:**
- Modify: `tickbiterisk/etl/model_features.py`
- Modify: `tickbiterisk/etl/model_features_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_model_features.py`
- Test: `tests/test_cli_model_features.py`

- [ ] Write failing tests proving drought and habitat CSVs join by `(county_fips, year)` and `county_fips`, respectively.
- [ ] Add optional `usdm_drought_path` and `enviroatlas_habitat_path` to `build_model_feature_matrix` and CLI.
- [ ] Propagate drought and habitat quality flags: `drought_monitor_retro_observed`, `static_enviroatlas_2011`, `missing_usdm_drought`, `missing_enviroatlas_habitat`.
- [ ] Add construction lag columns from the updated contact-pressure artifact.
- [ ] Run focused tests and commit.

### Task 5: Design Matrix And Model Selectors

**Files:**
- Modify: `tickbiterisk/modeling/design_matrix.py`
- Modify: `tickbiterisk/modeling/model_compare.py`
- Test: `tests/test_model_design_matrix.py`
- Test: `tests/test_model_comparison.py`

- [ ] Write failing tests for drought, habitat, and construction-lag numeric features and missing indicators.
- [ ] Include static habitat and prior/trailing construction features in ecology lanes.
- [ ] Keep same-year USDM drought out of `ridge_forecast_safe`; include it in retrospective weather/ecology lanes.
- [ ] Include prior/trailing construction features in `ridge_forecast_ecology` only when timing is defensible.
- [ ] Exclude source/caveat quality flags as predictors when they encode source coverage rather than biology.
- [ ] Run focused tests and commit.

### Task 6: Docs, Live Rebuild, And Review

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `docs/model-spec.md`
- Generated: `build/etl/usdm-drought/*`
- Generated: `build/etl/enviroatlas/*`
- Generated: `build/etl/contact-pressure/*`
- Generated: `build/etl/model/*`
- Generated: `build/etl/model-comparison/*`

- [ ] Update docs with source caveats and feature timing.
- [ ] Run USDM live acquisition for Maryland years 2000-2023 or latest model year.
- [ ] Run EnviroAtlas live acquisition for Maryland counties.
- [ ] Rebuild contact pressure, model features, design matrix, and model comparison.
- [ ] Report whether the new feature families improve held-out MAE.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m pytest -q`.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m ruff check .`.
- [ ] Run `npm run test:dashboard`.
- [ ] Request code review and fix important findings.
- [ ] Commit docs and any tracked generated artifacts.
