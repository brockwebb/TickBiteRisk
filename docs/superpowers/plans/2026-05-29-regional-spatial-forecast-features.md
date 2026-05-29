# Regional Spatial Forecast Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a forecast-safe regional spatial-neighbor incidence branch to the Mid-Atlantic rolling-origin incidence stress test.

**Architecture:** Keep the regional public forecast untouched while adding an optional research lane behind a regional adjacency CSV option. Shared adjacency parsing and neighbor incidence summaries live in `tickbiterisk/modeling/spatial_neighbors.py`; `regional_incidence_stress` reads them only when explicitly provided and emits a lagged neighbor baseline plus provenance in the run row.

**Tech Stack:** Python stdlib CSV/dataclasses, Typer CLI, pytest, ruff.

---

### Task 1: Shared Neighbor Feature Helpers

**Files:**
- Modify: `tickbiterisk/modeling/spatial_neighbors.py`
- Modify: `tests/test_spatial_neighbors.py`

- [ ] **Step 1: Write the failing tests**

Add tests that prove adjacency CSV parsing is deterministic and that prior-year neighbor incidence summaries only use requested historical years.

```python
neighbors = read_county_neighbors(adjacency)
assert neighbors == {"24001": ["42001"], "42001": ["24001"]}

summary = summarize_neighbor_incidence(
    county_fips="24001",
    years=[2020],
    county_neighbors=neighbors,
    incidence_by_county_year={
        ("42001", 2020): 50.0,
        ("42001", 2021): 999.0,
    },
)
assert summary.mean_incidence_per_100k == 50.0
assert summary.max_incidence_per_100k == 50.0
assert summary.neighbor_count == 1
assert summary.start_year == 2020
assert summary.end_year == 2020
assert summary.missing_neighbor_incidence is False
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_spatial_neighbors.py -q
```

Expected: fail because `read_county_neighbors` and `summarize_neighbor_incidence` are not defined.

- [ ] **Step 3: Write minimal implementation**

Add:

```python
class CountyAdjacencyInputError(ValueError):
    """Raised when county adjacency inputs are invalid."""


@dataclass(frozen=True)
class NeighborIncidenceSummary:
    mean_incidence_per_100k: float
    max_incidence_per_100k: float
    neighbor_count: int
    start_year: int | None
    end_year: int | None
    year_count: int
    missing_neighbor_incidence: bool
```

Implement `read_county_neighbors(path: Path | None) -> dict[str, list[str]]` with required columns `county_fips` and `neighbor_county_fips`, self-edge removal, dedupe, zero-filled FIPS, and sorted output. Implement `summarize_neighbor_incidence(...)` over explicit year lists so callers control forecast-origin safety.

- [ ] **Step 4: Run GREEN**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_spatial_neighbors.py -q
```

Expected: pass.

### Task 2: Regional Incidence Stress Spatial Branch

**Files:**
- Modify: `tickbiterisk/modeling/regional_incidence_stress.py`
- Modify: `tickbiterisk/modeling/regional_incidence_stress_build.py`
- Modify: `tests/test_regional_incidence_stress.py`

- [ ] **Step 1: Write the failing test**

Add a test that calls `build_regional_incidence_stress(..., regional_adjacency_path=adjacency)` for 2021, where neighbor 42001 has 2020 incidence `20.0` and 2021 target incidence `30.0`. Assert the new spatial prediction uses `20.0`, never the held-out target year.

```python
spatial = next(
    row for row in result.predictions
    if row.model_name == "spatial_prior_year_neighbor_incidence"
    and row.county_fips == "24001"
)
assert spatial.predicted_incidence_per_100k == 20.0
assert spatial.predicted_incidence_per_100k != 30.0
assert spatial.train_start_year == 2020
assert spatial.train_end_year == 2020
assert "regional_county_adjacency_from_geojson" in spatial.model_feature_quality_flags
assert "spatial_neighbor_feature" in spatial.model_feature_quality_flags
assert "forecast_safe_prior_year_neighbor_signal" in spatial.model_feature_quality_flags
assert "not_public_default" in spatial.model_feature_quality_flags
```

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_incidence_stress.py -q
```

Expected: fail because `regional_adjacency_path` is not accepted or the model row is absent.

- [ ] **Step 3: Write minimal implementation**

Add optional `regional_adjacency_path: Path | None = None` to `build_regional_incidence_stress`. When present, read neighbors, add `regional_adjacency_path` and `regional_adjacency_sha256` to the run dataclass/output columns, and append `spatial_prior_year_neighbor_incidence` predictions only when at least one neighbor has incidence for `test_year - 1`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_incidence_stress.py -q
```

Expected: pass.

### Task 3: CLI Wiring And Docs

**Files:**
- Modify: `tickbiterisk/cli.py`
- Modify: `tests/test_cli_regional_incidence_stress.py`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`

- [ ] **Step 1: Write the failing CLI test**

Add a CLI test that passes `--regional-adjacency-path` and asserts the predictions CSV includes `spatial_prior_year_neighbor_incidence`. Add a missing-adjacency clean-failure assertion.

- [ ] **Step 2: Run RED**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_regional_incidence_stress.py -q
```

Expected: fail because the option is not wired.

- [ ] **Step 3: Implement CLI option and docs**

Add:

```python
regional_adjacency_path: Path | None = typer.Option(
    None,
    "--regional-adjacency-path",
    "--county-adjacency-path",
    help="Optional regional county adjacency CSV for spatial-neighbor research branches.",
)
```

Validate existence when provided, pass it into `build_regional_incidence_stress`, and update docs to describe the optional spatial branch as research-only and forecast-safe.

- [ ] **Step 4: Run focused verification**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_spatial_neighbors.py tests/test_regional_incidence_stress.py tests/test_cli_regional_incidence_stress.py tests/test_public_docs.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check tickbiterisk/modeling/spatial_neighbors.py tickbiterisk/modeling/regional_incidence_stress.py tickbiterisk/modeling/regional_incidence_stress_build.py tickbiterisk/cli.py tests/test_spatial_neighbors.py tests/test_regional_incidence_stress.py tests/test_cli_regional_incidence_stress.py
```

Expected: pass.

### Task 4: Live Backtest And Commit

**Files:**
- Modify only if live metrics require doc updates: `docs/data-manifest.md`

- [ ] **Step 1: Run the adjacency ETL if the ignored artifact is missing**

```bash
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-county-adjacency --fetch-census-geojson --output-dir build/etl/regional-county-adjacency
```

- [ ] **Step 2: Run the spatial incidence stress backtest**

```bash
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-incidence-stress --regional-adjacency-path build/etl/regional-county-adjacency/regional_county_adjacency.csv --output-dir build/etl/regional-incidence-stress
```

- [ ] **Step 3: Inspect metrics**

Read `build/etl/regional-incidence-stress/regional_incidence_stress_metrics.csv` and compare `spatial_prior_year_neighbor_incidence` MAE/RMSE against prior-year county, trailing county, analog, empirical Bayes, and random forest branches.

- [ ] **Step 4: Full verification**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl
npm run test:dashboard
node --check public/app.js
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-05-29-regional-spatial-forecast-features.md tickbiterisk/modeling/spatial_neighbors.py tickbiterisk/modeling/regional_incidence_stress.py tickbiterisk/modeling/regional_incidence_stress_build.py tickbiterisk/cli.py tests/test_spatial_neighbors.py tests/test_regional_incidence_stress.py tests/test_cli_regional_incidence_stress.py docs/data-manifest.md docs/etl-pipeline.md
git commit -m "feat: add regional spatial incidence stress branch"
```

## Self-Review

This plan implements only the first forecast-safe spatial modeling lane. It avoids same-year leakage by making callers pass explicit historical years into the neighbor summary and by using `test_year - 1` for the rolling-origin branch. It does not promote the Maryland public dashboard, and it does not add a regional annual forecast spatial branch until live backtest behavior justifies that follow-up.
