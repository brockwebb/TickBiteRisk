# Surveillance Analog Regional Modeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add leakage-aware surveillance diagnostics, an analog-year/bootstrap forecast lane, regional hotspot/capacity summaries, and exposure-source registry updates without changing the public dashboard default.

**Architecture:** Keep model comparison predictions as the core rolling-origin artifact. Add focused diagnostics modules that read model-comparison artifacts and write separate `build/etl/model-diagnostics/*` outputs. Extend `model_compare` with one transparent analog lane and a companion interval artifact rather than changing the existing prediction schema used by the dashboard.

**Tech Stack:** Python stdlib dataclasses/csv/math/random/statistics, Typer CLI, pytest, ruff, existing CSV writer patterns.

---

## File Structure

- Create `tickbiterisk/modeling/model_diagnostics.py`: pure functions and dataclasses for surveillance-regime residual summaries and regional/hotspot/capacity summaries from prediction and interval CSVs.
- Create `tickbiterisk/modeling/model_diagnostics_build.py`: CSV writer for model diagnostics outputs, mirroring `model_compare_build.py`.
- Modify `tickbiterisk/modeling/model_compare.py`: add `analog_year_forecast` prediction rows and `ModelComparisonInterval` rows using training-window-only analog matching and deterministic bootstrap intervals.
- Modify `tickbiterisk/modeling/model_compare_build.py`: write `model_comparison_intervals.csv` while preserving existing run/prediction/metric/summary files.
- Modify `tickbiterisk/cli.py`: add `tickbiterisk etl model-diagnostics`; update `model-compare` output logging for intervals.
- Modify `tests/test_model_comparison.py`: RED/GREEN tests for analog lane, no-future matching, and deterministic intervals.
- Modify `tests/test_cli_model_comparison.py`: RED/GREEN CLI test for interval artifact.
- Create `tests/test_model_diagnostics.py`: RED/GREEN tests for surveillance-regime and regional diagnostics.
- Create `tests/test_cli_model_diagnostics.py`: RED/GREEN tests for diagnostics CLI.
- Modify `tests/test_sources.py`, `docs/data-sources.md`, `docs/data-manifest.md`, `docs/model-spec.md`, and `docs/etl-pipeline.md`: source registry and model documentation updates.

## Task 1: Surveillance-Regime Diagnostics Artifact

**Files:**
- Create: `tickbiterisk/modeling/model_diagnostics.py`
- Create: `tickbiterisk/modeling/model_diagnostics_build.py`
- Create: `tests/test_model_diagnostics.py`
- Create: `tests/test_cli_model_diagnostics.py`
- Modify: `tickbiterisk/cli.py`

- [ ] **Step 1: Write failing diagnostics unit tests**

Add `tests/test_model_diagnostics.py` with this fixture shape and assertions:

```python
import csv
from pathlib import Path

from tickbiterisk.modeling.model_diagnostics import build_model_diagnostics
from tickbiterisk.modeling.model_diagnostics_build import (
    SURVEILLANCE_REGIME_RESIDUAL_COLUMNS,
    SURVEILLANCE_REGIME_SUMMARY_COLUMNS,
    write_model_diagnostics_outputs,
)


def test_build_model_diagnostics_labels_surveillance_regimes(tmp_path: Path) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")

    result = build_model_diagnostics(predictions_path=predictions)

    regimes = {(row.model_name, row.test_year, row.surveillance_regime) for row in result.surveillance_residuals}
    assert ("linear_blend_baseline", 2019, "pre_2020_baseline") in regimes
    assert ("linear_blend_baseline", 2020, "covid_reporting_disruption") in regimes
    assert ("linear_blend_baseline", 2022, "case_definition_change_2022_plus") in regimes
    assert ("linear_blend_baseline", 2024, "mdh_probable_only_2024") in regimes

    flagged = next(
        row for row in result.surveillance_summary
        if row.model_name == "linear_blend_baseline"
        and row.surveillance_regime == "case_definition_change_2022_plus"
        and row.test_year is None
    )
    assert flagged.n_predictions == 1
    assert flagged.mean_residual_incidence_per_100k == 20.0
    assert flagged.mae_incidence_per_100k == 20.0


def test_write_model_diagnostics_outputs_writes_expected_columns(tmp_path: Path) -> None:
    result = build_model_diagnostics(predictions_path=_write_predictions(tmp_path / "predictions.csv"))

    outputs = write_model_diagnostics_outputs(result, tmp_path / "out")

    with outputs.surveillance_residuals_path.open(newline="", encoding="utf-8") as handle:
        residuals = list(csv.DictReader(handle))
    with outputs.surveillance_summary_path.open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    assert list(residuals[0]) == SURVEILLANCE_REGIME_RESIDUAL_COLUMNS
    assert list(summary[0]) == SURVEILLANCE_REGIME_SUMMARY_COLUMNS
    assert {row["surveillance_regime"] for row in residuals} >= {
        "pre_2020_baseline",
        "covid_reporting_disruption",
        "case_definition_change_2022_plus",
        "mdh_probable_only_2024",
    }
```

Use helper `_write_predictions` in the same test file to write columns copied from `MODEL_COMPARISON_PREDICTION_COLUMNS`; include rows for 2019, 2020, 2022, and 2024 with quality flags `covid_reporting_disruption`, `lyme_case_definition_change`, and `mdh_probable_only_2024,state_source_not_cdc_public_use`.

- [ ] **Step 2: Run RED tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'tickbiterisk.modeling.model_diagnostics'`.

- [ ] **Step 3: Implement minimal diagnostics module and writer**

Create `tickbiterisk/modeling/model_diagnostics.py` with:

```python
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class SurveillanceRegimeResidual:
    model_name: str
    model_family: str
    test_year: int
    county_fips: str
    county_name: str
    surveillance_regime: str
    actual_incidence_per_100k: float
    predicted_incidence_per_100k: float
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    actual_cases: int
    predicted_cases: float
    residual_cases: float
    absolute_error_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class SurveillanceRegimeSummary:
    model_name: str
    model_family: str
    surveillance_regime: str
    test_year: int | None
    n_predictions: int
    mean_residual_incidence_per_100k: float
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    mean_residual_cases: float
    mae_cases: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelDiagnosticsResult:
    surveillance_residuals: list[SurveillanceRegimeResidual]
    surveillance_summary: list[SurveillanceRegimeSummary]
    regional_hotspot_summary: list[object]
    regional_capacity_intervals: list[object]


def build_model_diagnostics(*, predictions_path: Path, intervals_path: Path | None = None) -> ModelDiagnosticsResult:
    rows = _read_prediction_rows(predictions_path)
    residuals = [_surveillance_residual(row) for row in rows]
    return ModelDiagnosticsResult(
        surveillance_residuals=residuals,
        surveillance_summary=_surveillance_summary(residuals),
        regional_hotspot_summary=[],
        regional_capacity_intervals=[],
    )
```

Implement helpers `_read_prediction_rows`, `_surveillance_regime`, `_surveillance_residual`, `_surveillance_summary`, `_summary_row`, `_parse_int`, `_parse_float`, `_round`, and `_rmse`. Regime precedence must be `mdh_probable_only_2024`, then `covid_reporting_disruption` or year 2020, then `lyme_case_definition_change` or year >= 2022, then `pre_2020_baseline` for years < 2020, else `other_surveillance_regime`.

Create `tickbiterisk/modeling/model_diagnostics_build.py` with fixed columns and `_write_records` like `model_compare_build.py`. It should write:

```text
surveillance_regime_residuals.csv
surveillance_regime_summary.csv
regional_hotspot_summary.csv
regional_capacity_intervals.csv
```

The regional files can be header-only in Task 1.

- [ ] **Step 4: Verify GREEN for diagnostics unit tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py -q
```

Expected: pass.

- [ ] **Step 5: Add CLI RED test**

Add `tests/test_cli_model_diagnostics.py`:

```python
import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tests.test_model_diagnostics import _write_predictions


runner = CliRunner()


def test_model_diagnostics_command_writes_surveillance_outputs(tmp_path: Path) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    output_dir = tmp_path / "diagnostics"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(predictions),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "surveillance_regime_residuals.csv" in result.stdout
    assert (output_dir / "surveillance_regime_summary.csv").exists()
    with (output_dir / "surveillance_regime_summary.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert "mdh_probable_only_2024" in {row["surveillance_regime"] for row in rows}
```

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_model_diagnostics.py -q
```

Expected: fail because the `model-diagnostics` command does not exist.

- [ ] **Step 6: Implement CLI command**

In `tickbiterisk/cli.py`, import `build_model_diagnostics` and `write_model_diagnostics_outputs`, then add:

```python
@etl_app.command("model-diagnostics")
def model_diagnostics(
    predictions_path: Path = typer.Option(
        Path("build/etl/model-comparison/model_comparison_predictions.csv"),
        help="Input model comparison predictions CSV.",
    ),
    intervals_path: Path | None = typer.Option(
        None,
        help="Optional model comparison intervals CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/model-diagnostics"),
        help="Output directory for model diagnostics artifacts.",
    ),
) -> None:
    if not predictions_path.exists():
        raise typer.BadParameter(f"Model comparison predictions file not found: {predictions_path}")
    if intervals_path is not None and not intervals_path.exists():
        raise typer.BadParameter(f"Model comparison intervals file not found: {intervals_path}")
    result = build_model_diagnostics(
        predictions_path=predictions_path,
        intervals_path=intervals_path,
    )
    outputs = write_model_diagnostics_outputs(result, output_dir)
    typer.echo(f"Wrote {len(result.surveillance_residuals)} surveillance residual row(s) to {outputs.surveillance_residuals_path}")
    typer.echo(f"Wrote {len(result.surveillance_summary)} surveillance summary row(s) to {outputs.surveillance_summary_path}")
    typer.echo(f"Wrote {len(result.regional_hotspot_summary)} regional hotspot row(s) to {outputs.regional_hotspot_summary_path}")
    typer.echo(f"Wrote {len(result.regional_capacity_intervals)} regional capacity interval row(s) to {outputs.regional_capacity_intervals_path}")
```

- [ ] **Step 7: Verify Task 1 and commit**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check tickbiterisk/modeling/model_diagnostics.py tickbiterisk/modeling/model_diagnostics_build.py tickbiterisk/cli.py tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py
```

Expected: all pass.

Commit:

```bash
git add tickbiterisk/modeling/model_diagnostics.py tickbiterisk/modeling/model_diagnostics_build.py tickbiterisk/cli.py tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py
git commit -m "feat: add model surveillance diagnostics"
```

## Task 2: Analog-Year Forecast Lane and Bootstrap Intervals

**Files:**
- Modify: `tickbiterisk/modeling/model_compare.py`
- Modify: `tickbiterisk/modeling/model_compare_build.py`
- Modify: `tests/test_model_comparison.py`
- Modify: `tests/test_cli_model_comparison.py`

- [ ] **Step 1: Write RED tests for analog lane and intervals**

In `tests/test_model_comparison.py`, update expected model names in existing tests to include `analog_year_forecast`. Add:

```python
def test_analog_year_forecast_uses_training_rows_only_and_emits_intervals(tmp_path: Path) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")

    result = run_model_comparison(
        design_matrix_path=matrix,
        start_year=2021,
        min_train_years=1,
    )

    analog = next(
        row for row in result.predictions
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24001"
        and row.test_year == 2021
    )
    assert analog.model_family == "analog"
    assert analog.feature_profile == "forecast_safe_analog_years"
    assert analog.weather_mode == "not_used_by_forecast_safe_model"
    assert analog.train_end_year == 2020
    assert analog.predicted_incidence_per_100k >= 0

    interval = next(
        row for row in result.intervals
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24001"
        and row.test_year == 2021
    )
    assert interval.interval_method == "weighted_analog_bootstrap"
    assert interval.bootstrap_seed == 1337
    assert interval.bootstrap_iterations == 200
    assert interval.lower_80_incidence_per_100k <= interval.median_incidence_per_100k
    assert interval.median_incidence_per_100k <= interval.upper_80_incidence_per_100k
    assert "2021" not in interval.analog_years
```

Add writer assertions:

```python
from tickbiterisk.modeling.model_compare_build import MODEL_COMPARISON_INTERVAL_COLUMNS


def test_write_model_comparison_outputs_writes_interval_artifact(tmp_path: Path) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    result = run_model_comparison(design_matrix_path=matrix, start_year=2021, min_train_years=1)

    outputs = write_model_comparison_outputs(result, tmp_path / "out")

    assert outputs.intervals_path.exists()
    with outputs.intervals_path.open(newline="", encoding="utf-8") as handle:
        intervals = list(csv.DictReader(handle))
    assert list(intervals[0]) == MODEL_COMPARISON_INTERVAL_COLUMNS
    assert {row["model_name"] for row in intervals} == {"analog_year_forecast"}
```

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_comparison.py -q
```

Expected: fail because `analog_year_forecast`, `result.intervals`, and interval writer columns do not exist.

- [ ] **Step 2: Implement interval dataclass and result field**

In `model_compare.py`, add:

```python
@dataclass(frozen=True)
class ModelComparisonInterval:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    interval_method: str
    bootstrap_seed: int
    bootstrap_iterations: int
    analog_count: int
    analog_years: str
    analog_counties: str
    lower_80_incidence_per_100k: float
    median_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    observed_incidence_per_100k: float
    covered_80: int
    covered_95: int
    comparison_assumption_flags: str
```

Add `intervals: list[ModelComparisonInterval]` to `ModelComparisonResult`.

- [ ] **Step 3: Implement analog prediction and intervals**

Add constants:

```python
ANALOG_BOOTSTRAP_SEED = 1337
ANALOG_BOOTSTRAP_ITERATIONS = 200
ANALOG_NEIGHBOR_COUNT = 5
ANALOG_FEATURE_PROFILE = "forecast_safe_analog_years"
ANALOG_INTERVAL_METHOD = "weighted_analog_bootstrap"
```

In `run_model_comparison`, after appending predictions for a row, call a helper:

```python
analog_prediction, analog_interval = _analog_prediction_and_interval(
    row=row,
    train_rows=train_rows,
    feature_columns=feature_columns,
    run_id=run_id,
    source_sha=source_sha,
    train_start_year=train_start_year,
    train_end_year=train_end_year,
)
```

Append the analog prediction through `_prediction_row` and append `analog_interval` to the result interval list.

Implement `_analog_prediction_and_interval` to:

- select columns where `_is_forecast_spatial_feature_column(column) or _is_forecast_ecology_feature_column(column)`;
- standardize selected columns using `train_rows` means/scales only;
- compute Euclidean distance from the held-out row to each training row;
- sort by `(distance, year, county_fips)`;
- keep up to `ANALOG_NEIGHBOR_COUNT`;
- weight each analog by `1 / (distance + 1e-9)`, or equal weights if all distances are effectively zero;
- predict weighted mean of analog `incidence_per_100k`;
- bootstrap by drawing analog rows with replacement using `random.Random(ANALOG_BOOTSTRAP_SEED + row.year * 100000 + int(row.county_fips))`;
- compute 2.5, 10, 50, 90, and 97.5 percentiles from bootstrap predictions;
- return trailing mean fallback and an interval with repeated fallback values when no analog rows exist.

Add `_percentile(values, percentile)` with nearest-rank or linear interpolation. Keep output rounded with existing `_round`.

- [ ] **Step 4: Implement interval writer**

In `model_compare_build.py`, add `MODEL_COMPARISON_INTERVAL_COLUMNS`, add `intervals_path` to `ModelComparisonOutputPaths`, write `model_comparison_intervals.csv`, and dedupe on `(run_id, model_name, test_year, county_fips)`.

- [ ] **Step 5: Update CLI test and CLI output**

In `tests/test_cli_model_comparison.py`, assert:

```python
assert (output_dir / "model_comparison_intervals.csv").exists()
assert "model_comparison_intervals.csv" in result.stdout
assert "analog_year_forecast" in {row["model_name"] for row in summary}
```

In `tickbiterisk/cli.py`, after summary output add:

```python
typer.echo(
    f"Wrote {len(result.intervals)} model comparison interval row(s) to "
    f"{outputs.intervals_path}"
)
```

- [ ] **Step 6: Verify Task 2 and commit**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_comparison.py tests/test_cli_model_comparison.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check tickbiterisk/modeling/model_compare.py tickbiterisk/modeling/model_compare_build.py tickbiterisk/cli.py tests/test_model_comparison.py tests/test_cli_model_comparison.py
```

Expected: all pass.

Commit:

```bash
git add tickbiterisk/modeling/model_compare.py tickbiterisk/modeling/model_compare_build.py tickbiterisk/cli.py tests/test_model_comparison.py tests/test_cli_model_comparison.py
git commit -m "feat: add analog year model comparison lane"
```

## Task 3: Regional Hotspot and Capacity Diagnostics

**Files:**
- Modify: `tickbiterisk/modeling/model_diagnostics.py`
- Modify: `tickbiterisk/modeling/model_diagnostics_build.py`
- Modify: `tests/test_model_diagnostics.py`

- [ ] **Step 1: Write RED tests for regional outputs**

Add to `tests/test_model_diagnostics.py`:

```python
def test_model_diagnostics_builds_regional_hotspot_and_capacity_rows(tmp_path: Path) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_intervals(tmp_path / "intervals.csv")

    result = build_model_diagnostics(predictions_path=predictions, intervals_path=intervals)

    hotspot = next(
        row for row in result.regional_hotspot_summary
        if row.model_name == "linear_blend_baseline"
        and row.test_year == 2024
        and row.region_id == "state_24"
    )
    assert hotspot.n_counties == 2
    assert hotspot.predicted_total_cases > 0
    assert hotspot.actual_total_cases > 0
    assert hotspot.top3_hit_count >= 1
    assert hotspot.county_share_mae >= 0

    capacity = next(
        row for row in result.regional_capacity_intervals
        if row.model_name == "analog_year_forecast"
        and row.test_year == 2024
        and row.region_id == "state_24"
    )
    assert capacity.interval_method == "summed_county_intervals"
    assert capacity.lower_80_cases <= capacity.median_cases <= capacity.upper_80_cases
    assert capacity.covered_80 in {0, 1}
```

Add `_write_intervals` helper with columns from `MODEL_COMPARISON_INTERVAL_COLUMNS` and two `analog_year_forecast` rows for 2024 Maryland counties.

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py -q
```

Expected: fail because regional dataclasses and outputs are header-only/empty.

- [ ] **Step 2: Implement regional dataclasses and grouping**

In `model_diagnostics.py`, add:

```python
@dataclass(frozen=True)
class RegionalHotspotSummary:
    model_name: str
    model_family: str
    test_year: int
    region_id: str
    region_name: str
    n_counties: int
    actual_total_cases: int
    predicted_total_cases: float
    residual_cases: float
    absolute_error_cases: float
    actual_incidence_per_100k_mean: float
    predicted_incidence_per_100k_mean: float
    spearman_rank_correlation: float | None
    top3_hit_count: int
    top5_hit_count: int
    county_share_mae: float
    predicted_case_hhi: float
    actual_case_hhi: float
    comparison_assumption_flags: str
```

```python
@dataclass(frozen=True)
class RegionalCapacityInterval:
    model_name: str
    model_family: str
    test_year: int
    region_id: str
    region_name: str
    interval_method: str
    n_counties: int
    lower_80_cases: float
    median_cases: float
    upper_80_cases: float
    lower_95_cases: float
    upper_95_cases: float
    actual_cases: int
    covered_80: int
    covered_95: int
    comparison_assumption_flags: str
```

Implement `_regional_hotspot_summary(prediction_rows)` grouping by `(model_name, test_year, state_fips)` where `state_fips = county_fips[:2]` and `region_id = f"state_{state_fips}"`.

Implement `_regional_capacity_intervals(interval_rows, prediction_rows)` by summing county interval case estimates. Convert incidence intervals to cases using the matching prediction row population: `incidence / 100000 * actual_population`.

Add Spearman rank correlation with stdlib only, HHI as sum of squared county case shares, and share MAE between predicted and observed county case shares.

- [ ] **Step 3: Implement regional writer columns**

In `model_diagnostics_build.py`, replace the temporary empty regional output columns from Task 1 with fixed columns for regional hotspot and regional capacity dataclasses. Ensure header-only writes still work when lists are empty.

- [ ] **Step 4: Verify Task 3 and commit**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check tickbiterisk/modeling/model_diagnostics.py tickbiterisk/modeling/model_diagnostics_build.py tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py
```

Expected: all pass.

Commit:

```bash
git add tickbiterisk/modeling/model_diagnostics.py tickbiterisk/modeling/model_diagnostics_build.py tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py
git commit -m "feat: add regional model diagnostics"
```

## Task 4: Exposure Source Registry, Docs, and Live Rebuild

**Files:**
- Modify: `docs/data-sources.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/model-spec.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Write RED source-registry test**

In `tests/test_sources.py`, extend `test_project_manifest_tracks_remaining_candidate_sources`:

```python
    for source_id in [
        "cdc_tick_bite_tracker",
        "nssp_tick_bite_ed",
        "poison_center_tick_bite_inquiries",
        "park_attendance_county_year",
        "dog_license_pet_ownership_proxy",
        "parcel_low_density_residential_proxy",
        "surveillance_regime_calibration",
    ]:
        assert source_id in source_ids
```

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_sources.py::test_project_manifest_tracks_remaining_candidate_sources -q
```

Expected: fail for new missing source IDs.

- [ ] **Step 2: Update source docs**

In `docs/data-manifest.md`, add rows for:

- `nssp_tick_bite_ed`
- `poison_center_tick_bite_inquiries`
- `dog_license_pet_ownership_proxy`
- `parcel_low_density_residential_proxy`
- `surveillance_regime_calibration`

Use these status strings exactly: `candidate, needs_acquisition, needs_privacy_review, optional, not_public_default` for privacy-sensitive feeds and `candidate, needs_acquisition, optional, not_public_default` for public aggregate proxies. Notes must say these are exposure or calibration candidates, not confirmed disease truth labels.

In `docs/data-sources.md`, add matching rows under potential source and feature candidates. Keep `cdc_tick_bite_tracker` and `park_attendance_county_year` existing IDs and expand descriptions toward human exposure pressure.

- [ ] **Step 3: Update model and pipeline docs**

In `docs/model-spec.md`, add a short research-lane section covering:

- `analog_year_forecast`;
- bootstrap intervals;
- surveillance-regime diagnostics;
- regional hotspot/capacity diagnostics;
- no public dashboard branch change.

In `docs/etl-pipeline.md`, add `tickbiterisk etl model-diagnostics` after `model-compare` and mention the new `model_comparison_intervals.csv` companion artifact.

- [ ] **Step 4: Run live local rebuild for new artifacts**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_sources.py tests/test_model_comparison.py tests/test_cli_model_comparison.py tests/test_model_diagnostics.py tests/test_cli_model_diagnostics.py -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
tickbiterisk etl model-compare --design-matrix-path build/etl/model/model_design_matrix_county_year.csv --start-year 2007 --output-dir build/etl/model-comparison
tickbiterisk etl model-diagnostics --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --intervals-path build/etl/model-comparison/model_comparison_intervals.csv --output-dir build/etl/model-diagnostics
```

Expected:

- tests pass;
- ruff passes;
- model comparison writes intervals;
- model diagnostics writes surveillance, hotspot, and capacity CSVs under ignored `build/etl/model-diagnostics`.

- [ ] **Step 5: Full verification and commit**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
npm run test:dashboard
git diff --check
```

Expected: all pass. Do not stage ignored build artifacts unless they are already tracked and intentionally changed.

Commit:

```bash
git add docs/data-sources.md docs/data-manifest.md docs/model-spec.md docs/etl-pipeline.md tests/test_sources.py
git commit -m "docs: catalog exposure and analog diagnostics"
```

## Self-Review Checklist

- Spec coverage: Task 1 covers surveillance-regime diagnostics; Task 2 covers analog/bootstrap; Task 3 covers regional hotspot/capacity diagnostics; Task 4 covers exposure-source registry and docs.
- Leakage: Task 2 uses only training rows before the held-out year; Task 3 groups diagnostics and capacity intervals without borrowing actual held-out totals as anchors.
- Public boundary: no task changes `public/data` or the selected dashboard branch.
- TDD: each implementation task starts with a failing targeted test and verifies RED before GREEN.
- Frequent commits: each task ends with a focused commit.
