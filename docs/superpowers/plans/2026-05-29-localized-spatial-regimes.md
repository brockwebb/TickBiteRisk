# Localized Spatial Regimes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize forecast-safe localized spatial regimes and compare a spatial-regime empirical-Bayes branch against state and Mid-Atlantic baselines.

**Architecture:** Add a transparent `regional-spatial-regimes` modeling artifact built from the regional incidence panel plus the regional county adjacency graph. A county joins a local regime only through adjacency edges whose prior-history level and trend are similar before the held-out year; `regional-incidence-stress` can then read the safe `feature_*` regime fields and emit `empirical_bayes_spatial_regime_incidence` without using same-year diagnostics.

**Tech Stack:** Python stdlib CSV/dataclasses, Typer CLI, pytest, ruff.

---

### Task 1: Spatial Regime Builder And Writer

**Files:**
- Create: `tickbiterisk/modeling/regional_spatial_regimes.py`
- Create: `tickbiterisk/modeling/regional_spatial_regimes_build.py`
- Create: `tests/test_regional_spatial_regimes.py`

- [x] **Step 1: Write failing tests**

Create `tests/test_regional_spatial_regimes.py` with a four-county fixture:

```python
series = {
    ("24", "MD", "Maryland", "24001", "Allegany County"): [100, 110, 120, 130],
    ("42", "PA", "Pennsylvania", "42001", "Adams County"): [105, 115, 125, 135],
    ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [10, 12, 11, 12],
    ("51", "VA", "Virginia", "51810", "Virginia Beach city"): [8, 9, 10, 11],
}
```

Write adjacency rows for `24001 <-> 42001`, `24001 <-> 24003`, and `24003 <-> 51810`.

Assert that `build_regional_spatial_regimes(..., start_year=2021, min_train_years=2, lookback_years=2, max_prior_mean_difference=25.0, max_prior_year_difference=25.0, max_trend_difference=10.0)` assigns `24001` and `42001` to the same regime, keeps `24003` out of that high-incidence regime, uses only years `2019-2020`, and writes stable run/county-year/summary schemas.

- [x] **Step 2: Run RED**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_spatial_regimes.py -q
```

Expected: import failure because the module does not exist.

- [x] **Step 3: Implement the builder**

Implement:

```python
def build_regional_spatial_regimes(
    *,
    regional_incidence_path: Path,
    regional_adjacency_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 3,
    max_prior_mean_difference: float = 25.0,
    max_prior_year_difference: float = 25.0,
    max_trend_difference: float = 25.0,
) -> RegionalSpatialRegimeResult:
```

For each held-out `year`, build candidate signatures from `year - lookback_years` through `year - 1`. Do not require target-year outcomes to construct regime features; counties with enough prior history remain eligible even when the held-out outcome row is absent or incomplete. Retain an undirected adjacency edge only when both counties have enough prior history and the absolute differences in prior mean, prior-year incidence, and prior-window trend are within thresholds. Connected components become regimes. Emit county-year rows with forecast-safe `feature_regime_*` fields and diagnostic same-year actual fields kept separate under `diagnostic_*`.

- [x] **Step 4: Implement the writer**

Add `write_regional_spatial_regime_outputs(result, output_dir)` writing:

```text
regional_spatial_regime_runs.csv
regional_spatial_regime_county_year.csv
regional_spatial_regime_summary.csv
```

- [x] **Step 5: Run GREEN**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_spatial_regimes.py -q
```

Expected: pass.

### Task 2: CLI Command

**Files:**
- Modify: `tickbiterisk/cli.py`
- Create: `tests/test_cli_regional_spatial_regimes.py`

- [x] **Step 1: Write failing CLI tests**

Add one test that runs:

```bash
tickbiterisk etl regional-spatial-regimes \
  --regional-incidence-path incidence.csv \
  --regional-adjacency-path adjacency.csv \
  --start-year 2021 \
  --min-train-years 2 \
  --lookback-years 2 \
  --output-dir out
```

Assert all three CSV outputs exist and stdout mentions `regional_spatial_regime_county_year.csv`. Add clean-failure tests for missing incidence and missing adjacency paths.

- [x] **Step 2: Run RED**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_regional_spatial_regimes.py -q
```

Expected: command missing.

- [x] **Step 3: Implement CLI wiring**

Import the new builder/writer and add `@etl_app.command("regional-spatial-regimes")` with options for incidence path, adjacency path, start/end year, min train years, lookback years, the three similarity thresholds, and output directory. Validate paths and numeric thresholds before calling the builder.

- [x] **Step 4: Run GREEN**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_spatial_regimes.py tests/test_cli_regional_spatial_regimes.py -q
```

Expected: pass.

### Task 3: Regional Incidence Stress Branch

**Files:**
- Modify: `tickbiterisk/modeling/regional_incidence_stress.py`
- Modify: `tickbiterisk/modeling/regional_incidence_stress_build.py`
- Modify: `tests/test_regional_incidence_stress.py`
- Modify: `tests/test_cli_regional_incidence_stress.py`
- Modify: `tickbiterisk/cli.py`

- [x] **Step 1: Write failing model test**

Add a test that writes the spatial-regime county-year fixture and calls:

```python
result = build_regional_incidence_stress(
    regional_incidence_path=panel,
    regional_spatial_regimes_path=regimes,
    start_year=2021,
    min_train_years=2,
    lookback_years=2,
    random_forest_n_estimators=5,
)
```

Assert `empirical_bayes_spatial_regime_incidence` exists, uses the regime `feature_regime_trailing_mean_incidence_per_100k`, has `model_family == "empirical_bayes_spatial_regime"`, carries `localized_spatial_regime_feature`, `forecast_safe_prior_history_spatial_regime`, and `not_public_default`, and does not read `diagnostic_actual_regime_incidence_per_100k`.

- [x] **Step 2: Run RED**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_incidence_stress.py -q
```

Expected: keyword or model missing.

- [x] **Step 3: Implement branch**

Add optional `regional_spatial_regimes_path: Path | None = None` to the builder and CLI. Read required columns:

```text
source_file_sha256,regional_adjacency_sha256,county_fips,year,spatial_regime_id,feature_regime_trailing_mean_incidence_per_100k,model_feature_quality_flags
```

Ignore all `diagnostic_*` columns. For each county-year with a regime row, emit `empirical_bayes_spatial_regime_incidence` using `_shrunk_mean(county_mean, len(county_history), regime_mean, shrinkage_strength)`.
Reject stale spatial-regime artifacts when `source_file_sha256` does not match
the regional incidence panel and, when an adjacency input is supplied, when
`regional_adjacency_sha256` does not match the adjacency graph.

- [x] **Step 4: Run GREEN**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_incidence_stress.py tests/test_cli_regional_incidence_stress.py -q
```

Expected: pass.

### Task 4: Docs, Live ETL, Verification, Commit

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/data-sources.md`
- Modify: `docs/etl-pipeline.md`

- [x] **Step 1: Update docs**

Document `regional-spatial-regimes` as a transparent research artifact for localized cross-border risk regimes. Say that it uses prior-history similarity over the adjacency graph, separates `feature_*` from `diagnostic_*`, and is not the public default.

- [x] **Step 2: Run live spatial-regime ETL**

```bash
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-spatial-regimes \
  --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv \
  --regional-adjacency-path build/etl/regional-county-adjacency/regional_county_adjacency.csv \
  --output-dir build/etl/regional-spatial-regimes
```

- [x] **Step 3: Run live stress comparison**

```bash
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-incidence-stress \
  --regional-adjacency-path build/etl/regional-county-adjacency/regional_county_adjacency.csv \
  --regional-spatial-regimes-path build/etl/regional-spatial-regimes/regional_spatial_regime_county_year.csv \
  --output-dir build/etl/regional-incidence-stress
```

Inspect overall metrics and record whether `empirical_bayes_spatial_regime_incidence` improves on state empirical Bayes, Mid-Atlantic empirical Bayes, or county-history branches.

- [x] **Step 4: Full verification**

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl
npm run test:dashboard
node --check public/app.js
git diff --check
```

- [x] **Step 5: Commit**

```bash
git add README.md docs/data-manifest.md docs/data-sources.md docs/etl-pipeline.md docs/superpowers/plans/2026-05-29-localized-spatial-regimes.md tickbiterisk/cli.py tickbiterisk/modeling/regional_spatial_regimes.py tickbiterisk/modeling/regional_spatial_regimes_build.py tickbiterisk/modeling/regional_incidence_stress.py tickbiterisk/modeling/regional_incidence_stress_build.py tests/test_regional_spatial_regimes.py tests/test_cli_regional_spatial_regimes.py tests/test_regional_incidence_stress.py tests/test_cli_regional_incidence_stress.py
git commit -m "feat: add localized spatial regime modeling lane"
```

## Self-Review

The plan covers the spec nuance by creating an auditable intermediate regime artifact and a forecast-safe model comparison branch. It keeps risk-product language separate from reported-incidence inputs, does not use same-year target outcomes as features, and leaves regional annual forecast/public promotion for a later evidence-based decision.
