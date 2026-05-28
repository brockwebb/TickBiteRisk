# Forecasting Update Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add forecasting update audit artifacts and then update README/dashboard explanatory surfaces to reflect TickBiteRisk as a cautious risk forecasting tool.

**Architecture:** Extend the existing `model-diagnostics` path because it already reads model-comparison predictions, optional intervals, and surveillance-regime context. Add row-level forecast-update audit records and summary records beside the existing surveillance/regional diagnostics. Public wording and dashboard metadata are updated only after the audit artifacts exist, preserving medical and forecast-safety caveats.

**Tech Stack:** Python stdlib dataclasses/csv/Typer, existing pytest/Typer CLI tests, static HTML/CSS/JS dashboard, Playwright dashboard smoke test.

---

## File Structure

- Modify: `tickbiterisk/modeling/model_diagnostics.py`
  - Add `ForecastUpdateAudit` and `ForecastUpdateSummary` dataclasses.
  - Add forecast contract metadata parameters to `build_model_diagnostics`.
  - Join prediction rows to optional interval rows by run/model/year/county.
  - Compute deterministic update interpretations.
- Modify: `tickbiterisk/modeling/model_diagnostics_build.py`
  - Add forecast-update CSV columns.
  - Write `forecast_update_audit.csv` and `forecast_update_summary.csv`.
  - Extend `ModelDiagnosticsOutputPaths`.
- Modify: `tickbiterisk/cli.py`
  - Add `model-diagnostics` options for `--as-of-date`, `--data-cutoff-date`, and `--source-vintage`.
  - Echo the two new output artifacts.
- Modify: `tests/test_model_diagnostics.py`
  - Add RED/GREEN tests for audit rows, interval joins, deterministic interpretations, and summary groups.
- Modify: `tests/test_cli_model_diagnostics.py`
  - Add RED/GREEN test for new CLI options and output files.
- Modify: `README.md`
  - Add `Why Forecast Lyme Risk?` and `How Forecast Updates Work`.
  - Update framing from baseline-only to forecasting-tool-in-progress while preserving medical caveats.
- Modify: `tickbiterisk/runtime/static_export.py`
  - Add `forecasting_status` to model card and `data_lag_and_update_policy` to source catalog.
- Modify: `tests/test_static_export.py`
  - Add assertions for the new public metadata fields.
- Modify: `public/index.html`
  - Add a dashboard explainer section.
- Modify: `public/app.js`
  - Render forecast/update policy metadata from `model_card.json` and `source_catalog.json`.
- Modify: `tests/test_public_dashboard_static.py`
  - Add static assertions for forecast explainer copy and rendering functions.
- Modify: `tests/browser/dashboard-smoke.spec.mjs`
  - Assert the dashboard shows the forecast explainer.
- Modify: `docs/data-manifest.md`, `docs/etl-pipeline.md`, and `docs/model-spec.md`
  - Document forecast-update artifacts and public wording boundary.

---

### Task 1: Forecast Update Audit Domain Model

**Files:**
- Modify: `tests/test_model_diagnostics.py`
- Modify: `tickbiterisk/modeling/model_diagnostics.py`

- [ ] **Step 1: Write RED test for row-level forecast update audit**

Append this test to `tests/test_model_diagnostics.py` after the regional diagnostics tests:

```python
def test_build_model_diagnostics_builds_forecast_update_audit_rows(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_intervals(tmp_path / "intervals.csv")

    result = build_model_diagnostics(
        predictions,
        intervals_path=intervals,
        as_of_date="2026-05-28",
        data_cutoff_date="2024-12-31",
        source_vintage="model_compare_fixture_v1",
    )

    audit = next(
        row
        for row in result.forecast_update_audit
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24009"
        and row.forecast_year == 2024
    )
    assert audit.run_id == "run-1"
    assert audit.model_family == "analog"
    assert audit.feature_profile == "analog_year"
    assert audit.source_file_sha256 == "abc123"
    assert audit.source_vintage == "model_compare_fixture_v1"
    assert audit.forecast_origin_year == 2023
    assert audit.as_of_date == "2026-05-28"
    assert audit.data_cutoff_date == "2024-12-31"
    assert audit.target_definition == "lyme_incidence_per_100k"
    assert audit.evaluation_mode == "rolling_origin_prior_years"
    assert audit.update_mode == "post_observed_outcome"
    assert audit.surveillance_regime == "mdh_probable_only_2024"
    assert audit.predicted_incidence_per_100k == 25.0
    assert audit.predicted_cases == 25.0
    assert audit.lower_80_incidence_per_100k == 20.0
    assert audit.median_incidence_per_100k == 30.0
    assert audit.upper_80_incidence_per_100k == 40.0
    assert audit.lower_95_incidence_per_100k == 10.0
    assert audit.upper_95_incidence_per_100k == 50.0
    assert audit.interval_available is True
    assert audit.covered_80 is True
    assert audit.covered_95 is True
    assert audit.actual_incidence_per_100k == 30.0
    assert audit.actual_cases == 30
    assert audit.residual_incidence_per_100k == 5.0
    assert audit.absolute_error_incidence_per_100k == 5.0
    assert audit.signed_percent_error == 20.0
    assert audit.update_direction == "observed_above_forecast"
    assert audit.update_interpretation == "ambiguous_signal"
    assert "mdh_probable_only_2024" in audit.model_feature_quality_flags
    assert audit.comparison_assumption_flags == "surveillance_reporting_sensitive"
```

- [ ] **Step 2: Run the RED test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py::test_build_model_diagnostics_builds_forecast_update_audit_rows -q
```

Expected: fail because `ModelDiagnosticsResult` has no `forecast_update_audit` field and `build_model_diagnostics` does not accept forecast metadata arguments.

- [ ] **Step 3: Implement dataclasses and builder parameters**

In `tickbiterisk/modeling/model_diagnostics.py`, add these constants and dataclasses after `RegionalCapacityInterval`:

```python
MATERIAL_RESIDUAL_INCIDENCE_PER_100K = 10.0
REPORTING_BREAK_REGIMES = {
    "covid_reporting_disruption",
    "case_definition_change_2022_plus",
    "mdh_probable_only_2024",
}


@dataclass(frozen=True)
class ForecastUpdateAudit:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    source_file_sha256: str
    source_vintage: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    target_definition: str
    evaluation_mode: str
    update_mode: str
    surveillance_regime: str
    predicted_incidence_per_100k: float
    predicted_cases: float
    lower_80_incidence_per_100k: float | None
    median_incidence_per_100k: float | None
    upper_80_incidence_per_100k: float | None
    lower_95_incidence_per_100k: float | None
    upper_95_incidence_per_100k: float | None
    interval_available: bool
    covered_80: bool | None
    covered_95: bool | None
    actual_incidence_per_100k: float
    actual_cases: int
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    signed_percent_error: float | None
    update_direction: str
    update_interpretation: str
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastUpdateSummary:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    source_file_sha256: str
    source_vintage: str
    evaluation_mode: str
    surveillance_regime: str
    forecast_year: int | None
    n_updates: int
    mean_residual_incidence_per_100k: float
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    interval_available_count: int
    covered_80_count: int
    covered_95_count: int
    forecast_signal_count: int
    surveillance_regime_signal_count: int
    ambiguous_signal_count: int
    insufficient_signal_count: int
    forecast_signal_share: float
    surveillance_regime_signal_share: float
    ambiguous_signal_share: float
    insufficient_signal_share: float
    comparison_assumption_flags: str
```

Extend `ModelDiagnosticsResult`:

```python
@dataclass(frozen=True)
class ModelDiagnosticsResult:
    surveillance_residuals: list[SurveillanceRegimeResidual]
    surveillance_summary: list[SurveillanceRegimeSummary]
    regional_hotspot_summary: list[RegionalHotspotSummary]
    regional_capacity_intervals: list[RegionalCapacityInterval]
    forecast_update_audit: list[ForecastUpdateAudit]
    forecast_update_summary: list[ForecastUpdateSummary]
```

Change the `build_model_diagnostics` signature:

```python
def build_model_diagnostics(
    predictions_path: Path,
    intervals_path: Path | None = None,
    *,
    as_of_date: str = "unspecified",
    data_cutoff_date: str = "unspecified",
    source_vintage: str | None = None,
) -> ModelDiagnosticsResult:
```

- [ ] **Step 4: Implement interval lookup and row creation**

In `build_model_diagnostics`, build audit rows after `interval_rows` is loaded:

```python
    interval_by_key = {_county_model_key(row): row for row in interval_rows}
    forecast_update_audit = _build_forecast_update_audit(
        prediction_rows,
        interval_by_key,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=source_vintage,
    )
```

Return the new fields:

```python
        forecast_update_audit=forecast_update_audit,
        forecast_update_summary=_build_forecast_update_summary(forecast_update_audit),
```

Add helper functions near `_build_residual`:

```python
def _build_forecast_update_audit(
    prediction_rows: list[dict[str, str]],
    interval_by_key: dict[
        tuple[str, str, str, str, str, str, int, str],
        dict[str, str],
    ],
    *,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> list[ForecastUpdateAudit]:
    rows = [
        _forecast_update_audit_row(
            row,
            interval_by_key.get(_county_model_key(row)),
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
        )
        for row in prediction_rows
    ]
    return sorted(
        rows,
        key=lambda row: (
            row.run_id,
            row.model_name,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
            row.forecast_year,
            row.county_fips,
        ),
    )


def _forecast_update_audit_row(
    row: dict[str, str],
    interval_row: dict[str, str] | None,
    *,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> ForecastUpdateAudit:
    forecast_year = _parse_int(row["test_year"], "test_year")
    forecast_origin_year = _parse_int(row["train_end_year"], "train_end_year")
    actual_incidence = _parse_float(
        row["actual_incidence_per_100k"],
        "actual_incidence_per_100k",
    )
    predicted_incidence = _parse_float(
        row["predicted_incidence_per_100k"],
        "predicted_incidence_per_100k",
    )
    predicted_cases = _parse_float(row["predicted_cases"], "predicted_cases")
    actual_cases = _parse_int(row["actual_cases"], "actual_cases")
    residual_incidence = _round(actual_incidence - predicted_incidence)
    quality_flags = row.get("model_feature_quality_flags", "")
    surveillance_regime = _classify_surveillance_regime(quality_flags, forecast_year)
    lower_80 = _optional_interval_float(interval_row, "lower_80_incidence_per_100k")
    median = _optional_interval_float(interval_row, "median_incidence_per_100k")
    upper_80 = _optional_interval_float(interval_row, "upper_80_incidence_per_100k")
    lower_95 = _optional_interval_float(interval_row, "lower_95_incidence_per_100k")
    upper_95 = _optional_interval_float(interval_row, "upper_95_incidence_per_100k")
    covered_80 = _optional_interval_bool(interval_row, "covered_80")
    covered_95 = _optional_interval_bool(interval_row, "covered_95")
    signed_percent_error = (
        None
        if abs(predicted_incidence) < 1e-12
        else _round(residual_incidence / predicted_incidence * 100)
    )
    interpretation = _classify_update_interpretation(
        surveillance_regime=surveillance_regime,
        residual_incidence=residual_incidence,
        covered_95=covered_95,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=source_vintage,
    )
    return ForecastUpdateAudit(
        run_id=row["run_id"],
        model_name=row["model_name"],
        model_family=row["model_family"],
        feature_profile=row["feature_profile"],
        source_file_sha256=row["source_file_sha256"],
        source_vintage=source_vintage or row["source_file_sha256"],
        county_fips=row["county_fips"].zfill(5),
        county_name=row["county_name"],
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        target_definition=row.get("target_definition", "lyme_incidence_per_100k"),
        evaluation_mode=row["evaluation_mode"],
        update_mode="post_observed_outcome",
        surveillance_regime=surveillance_regime,
        predicted_incidence_per_100k=_round(predicted_incidence),
        predicted_cases=_round(predicted_cases),
        lower_80_incidence_per_100k=lower_80,
        median_incidence_per_100k=median,
        upper_80_incidence_per_100k=upper_80,
        lower_95_incidence_per_100k=lower_95,
        upper_95_incidence_per_100k=upper_95,
        interval_available=interval_row is not None,
        covered_80=covered_80,
        covered_95=covered_95,
        actual_incidence_per_100k=_round(actual_incidence),
        actual_cases=actual_cases,
        residual_incidence_per_100k=residual_incidence,
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        signed_percent_error=signed_percent_error,
        update_direction=_update_direction(residual_incidence),
        update_interpretation=interpretation,
        model_feature_quality_flags=quality_flags,
        comparison_assumption_flags=row.get("comparison_assumption_flags", ""),
    )
```

Add utility helpers:

```python
def _optional_interval_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _round(_parse_float(row[column], column))


def _optional_interval_bool(row: dict[str, str] | None, column: str) -> bool | None:
    if row is None:
        return None
    return _parse_bool(row[column], column)


def _update_direction(residual_incidence: float) -> str:
    if residual_incidence > 0:
        return "observed_above_forecast"
    if residual_incidence < 0:
        return "observed_below_forecast"
    return "observed_matches_forecast"


def _classify_update_interpretation(
    *,
    surveillance_regime: str,
    residual_incidence: float,
    covered_95: bool | None,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> str:
    if as_of_date == "unspecified" or data_cutoff_date == "unspecified":
        return "insufficient_signal"
    if source_vintage in {None, "", "unspecified"}:
        return "insufficient_signal"
    if covered_95 is None:
        return "insufficient_signal"
    interval_break = covered_95 is False
    material_residual = abs(residual_incidence) >= MATERIAL_RESIDUAL_INCIDENCE_PER_100K
    if not interval_break and not material_residual:
        return "ambiguous_signal"
    if surveillance_regime in REPORTING_BREAK_REGIMES:
        return "surveillance_regime_signal"
    return "forecast_signal"
```

- [ ] **Step 5: Run the row-level test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py::test_build_model_diagnostics_builds_forecast_update_audit_rows -q
```

Expected: pass.

- [ ] **Step 6: Write RED tests for missing interval and cross-branch leakage**

Append these tests to `tests/test_model_diagnostics.py`:

```python
def test_forecast_update_audit_marks_missing_intervals_as_insufficient(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")

    result = build_model_diagnostics(
        predictions,
        as_of_date="2026-05-28",
        data_cutoff_date="2024-12-31",
        source_vintage="model_compare_fixture_v1",
    )

    audit = next(
        row
        for row in result.forecast_update_audit
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24009"
    )
    assert audit.interval_available is False
    assert audit.covered_80 is None
    assert audit.covered_95 is None
    assert audit.update_interpretation == "insufficient_signal"


def test_forecast_update_audit_does_not_reuse_wrong_model_interval(
    tmp_path: Path,
) -> None:
    predictions = tmp_path / "predictions.csv"
    analog_prediction = _prediction_row(
        county_fips="24009",
        county_name="County 24009",
        test_year=2024,
        actual_cases=30,
        predicted_cases=25,
        actual_incidence=30.0,
        predicted_incidence=25.0,
        quality_flags="mdh_probable_only_2024,lyme_case_definition_change",
        model_name="analog_year_forecast",
        model_family="analog",
        feature_profile="analog_year",
    )
    wrong_model_prediction = {
        **analog_prediction,
        "model_name": "different_model",
        "model_family": "baseline",
        "feature_profile": "different_profile",
    }
    _write_rows(predictions, [analog_prediction, wrong_model_prediction])
    intervals = _write_interval_rows(
        tmp_path / "intervals.csv",
        [
            {
                **_interval_row(
                    county_fips="24009",
                    county_name="County 24009",
                    lower_80_incidence=1.0,
                    median_incidence=2.0,
                    upper_80_incidence=3.0,
                    lower_95_incidence=0.5,
                    upper_95_incidence=3.5,
                    observed_incidence=30.0,
                ),
                "model_name": "different_model",
                "model_family": "baseline",
                "feature_profile": "different_profile",
            }
        ],
    )

    result = build_model_diagnostics(
        predictions,
        intervals_path=intervals,
        as_of_date="2026-05-28",
        data_cutoff_date="2024-12-31",
        source_vintage="model_compare_fixture_v1",
    )

    audit = next(
        row
        for row in result.forecast_update_audit
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24009"
    )
    assert audit.interval_available is False
    assert audit.lower_80_incidence_per_100k is None
    assert audit.update_interpretation == "insufficient_signal"
```

- [ ] **Step 7: Run missing-interval and leakage tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py::test_forecast_update_audit_marks_missing_intervals_as_insufficient tests/test_model_diagnostics.py::test_forecast_update_audit_does_not_reuse_wrong_model_interval -q
```

Expected: pass after the `covered_95 is None` classifier branch and full `_county_model_key` interval lookup are implemented.

- [ ] **Step 8: Commit Task 1**

Run:

```bash
git add tests/test_model_diagnostics.py tickbiterisk/modeling/model_diagnostics.py
git commit -m "feat: add forecast update audit rows"
```

---

### Task 2: Forecast Update Summary And Output Writer

**Files:**
- Modify: `tests/test_model_diagnostics.py`
- Modify: `tickbiterisk/modeling/model_diagnostics.py`
- Modify: `tickbiterisk/modeling/model_diagnostics_build.py`

- [ ] **Step 1: Write RED test for summary rows and writer columns**

Append this test to `tests/test_model_diagnostics.py`:

```python
def test_model_diagnostics_writes_forecast_update_outputs(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_intervals(tmp_path / "intervals.csv")

    result = build_model_diagnostics(
        predictions,
        intervals_path=intervals,
        as_of_date="2026-05-28",
        data_cutoff_date="2024-12-31",
        source_vintage="model_compare_fixture_v1",
    )
    outputs = write_model_diagnostics_outputs(result, tmp_path / "out")

    assert outputs.forecast_update_audit_path.exists()
    assert outputs.forecast_update_summary_path.exists()
    with outputs.forecast_update_audit_path.open(newline="", encoding="utf-8") as handle:
        audit_header = next(csv.reader(handle))
    assert audit_header == FORECAST_UPDATE_AUDIT_COLUMNS
    with outputs.forecast_update_summary_path.open(newline="", encoding="utf-8") as handle:
        summary_rows = list(csv.DictReader(handle))

    analog_summary = next(
        row
        for row in summary_rows
        if row["model_name"] == "analog_year_forecast"
        and row["surveillance_regime"] == "mdh_probable_only_2024"
        and row["forecast_year"] == "2024"
    )
    assert analog_summary["n_updates"] == "2"
    assert analog_summary["interval_available_count"] == "2"
    assert analog_summary["covered_80_count"] == "2"
    assert analog_summary["covered_95_count"] == "2"
    assert analog_summary["ambiguous_signal_count"] == "2"
    assert analog_summary["ambiguous_signal_share"] == "1.0"
```

Add imports at the top of the test file:

```python
    FORECAST_UPDATE_AUDIT_COLUMNS,
    FORECAST_UPDATE_SUMMARY_COLUMNS,
```

- [ ] **Step 2: Run the RED test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py::test_model_diagnostics_writes_forecast_update_outputs -q
```

Expected: fail because writer paths and columns do not exist.

- [ ] **Step 3: Implement summary builder**

In `tickbiterisk/modeling/model_diagnostics.py`, add:

```python
def _build_forecast_update_summary(
    audit_rows: list[ForecastUpdateAudit],
) -> list[ForecastUpdateSummary]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str, str, int | None],
        list[ForecastUpdateAudit],
    ] = {}
    for row in audit_rows:
        yearly_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            row.forecast_year,
        )
        overall_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            None,
        )
        grouped.setdefault(yearly_key, []).append(row)
        grouped.setdefault(overall_key, []).append(row)
    return [
        _forecast_update_summary_row(rows, key)
        for key, rows in sorted(grouped.items())
    ]


def _forecast_update_summary_row(
    rows: list[ForecastUpdateAudit],
    key: tuple[str, str, str, str, str, str, str, str, int | None],
) -> ForecastUpdateSummary:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        source_file_sha256,
        source_vintage,
        evaluation_mode,
        surveillance_regime,
        forecast_year,
    ) = key
    residuals = [row.residual_incidence_per_100k for row in rows]
    assumption_flags = sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.comparison_assumption_flags)
            if flag
        }
    )
    return ForecastUpdateSummary(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        source_file_sha256=source_file_sha256,
        source_vintage=source_vintage,
        evaluation_mode=evaluation_mode,
        surveillance_regime=surveillance_regime,
        forecast_year=forecast_year,
        n_updates=len(rows),
        mean_residual_incidence_per_100k=_round(mean(residuals)),
        mae_incidence_per_100k=_round(mean(abs(value) for value in residuals)),
        rmse_incidence_per_100k=_round(
            math.sqrt(mean(value * value for value in residuals))
        ),
        interval_available_count=sum(row.interval_available for row in rows),
        covered_80_count=sum(row.covered_80 is True for row in rows),
        covered_95_count=sum(row.covered_95 is True for row in rows),
        forecast_signal_count=sum(
            row.update_interpretation == "forecast_signal" for row in rows
        ),
        surveillance_regime_signal_count=sum(
            row.update_interpretation == "surveillance_regime_signal"
            for row in rows
        ),
        ambiguous_signal_count=sum(
            row.update_interpretation == "ambiguous_signal" for row in rows
        ),
        insufficient_signal_count=sum(
            row.update_interpretation == "insufficient_signal" for row in rows
        ),
        forecast_signal_share=_interpretation_share(rows, "forecast_signal"),
        surveillance_regime_signal_share=_interpretation_share(
            rows,
            "surveillance_regime_signal",
        ),
        ambiguous_signal_share=_interpretation_share(rows, "ambiguous_signal"),
        insufficient_signal_share=_interpretation_share(rows, "insufficient_signal"),
        comparison_assumption_flags=",".join(assumption_flags),
    )
```

Add this helper after `_forecast_update_summary_row`:

```python
def _interpretation_share(
    rows: list[ForecastUpdateAudit],
    interpretation: str,
) -> float:
    if not rows:
        return 0.0
    return _round(
        sum(row.update_interpretation == interpretation for row in rows) / len(rows)
    )
```

- [ ] **Step 4: Implement writer columns and output paths**

In `tickbiterisk/modeling/model_diagnostics_build.py`, add imports and columns:

```python
FORECAST_UPDATE_AUDIT_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "source_file_sha256",
    "source_vintage",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "target_definition",
    "evaluation_mode",
    "update_mode",
    "surveillance_regime",
    "predicted_incidence_per_100k",
    "predicted_cases",
    "lower_80_incidence_per_100k",
    "median_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "interval_available",
    "covered_80",
    "covered_95",
    "actual_incidence_per_100k",
    "actual_cases",
    "residual_incidence_per_100k",
    "absolute_error_incidence_per_100k",
    "signed_percent_error",
    "update_direction",
    "update_interpretation",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

FORECAST_UPDATE_SUMMARY_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "source_file_sha256",
    "source_vintage",
    "evaluation_mode",
    "surveillance_regime",
    "forecast_year",
    "n_updates",
    "mean_residual_incidence_per_100k",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "interval_available_count",
    "covered_80_count",
    "covered_95_count",
    "forecast_signal_count",
    "surveillance_regime_signal_count",
    "ambiguous_signal_count",
    "insufficient_signal_count",
    "forecast_signal_share",
    "surveillance_regime_signal_share",
    "ambiguous_signal_share",
    "insufficient_signal_share",
    "comparison_assumption_flags",
]
```

Extend `ModelDiagnosticsOutputPaths`:

```python
    forecast_update_audit_path: Path
    forecast_update_summary_path: Path
```

In `write_model_diagnostics_outputs`, add paths and writes:

```python
    forecast_update_audit_path = output_dir / "forecast_update_audit.csv"
    forecast_update_summary_path = output_dir / "forecast_update_summary.csv"
```

```python
    _write_records(
        forecast_update_audit_path,
        [asdict(row) for row in result.forecast_update_audit],
        FORECAST_UPDATE_AUDIT_COLUMNS,
    )
    _write_records(
        forecast_update_summary_path,
        [asdict(row) for row in result.forecast_update_summary],
        FORECAST_UPDATE_SUMMARY_COLUMNS,
    )
```

Return the new paths:

```python
        forecast_update_audit_path=forecast_update_audit_path,
        forecast_update_summary_path=forecast_update_summary_path,
```

- [ ] **Step 5: Run focused diagnostics tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_diagnostics.py -q
```

Expected: all model diagnostics tests pass.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add tests/test_model_diagnostics.py tickbiterisk/modeling/model_diagnostics.py tickbiterisk/modeling/model_diagnostics_build.py
git commit -m "feat: write forecast update diagnostics"
```

---

### Task 3: Forecast Update CLI Surface

**Files:**
- Modify: `tests/test_cli_model_diagnostics.py`
- Modify: `tickbiterisk/cli.py`

- [ ] **Step 1: Write RED CLI test**

Add this test to `tests/test_cli_model_diagnostics.py`:

```python
def test_model_diagnostics_command_writes_forecast_update_outputs(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(predictions),
            "--as-of-date",
            "2026-05-28",
            "--data-cutoff-date",
            "2024-12-31",
            "--source-vintage",
            "cli-test-vintage",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "forecast_update_audit.csv" in result.stdout
    assert "forecast_update_summary.csv" in result.stdout
    assert (output_dir / "forecast_update_audit.csv").exists()
    assert (output_dir / "forecast_update_summary.csv").exists()
```

- [ ] **Step 2: Run the RED CLI test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_model_diagnostics.py::test_model_diagnostics_command_writes_forecast_update_outputs -q
```

Expected: fail because the CLI has no forecast metadata options and does not echo new output files.

- [ ] **Step 3: Implement CLI options and output echoes**

In `tickbiterisk/cli.py`, add options to `model_diagnostics`:

```python
    as_of_date: str = typer.Option(
        "unspecified",
        help="Forecast artifact as-of date for update-audit provenance.",
    ),
    data_cutoff_date: str = typer.Option(
        "unspecified",
        help="Latest source data cutoff date represented in update-audit provenance.",
    ),
    source_vintage: str | None = typer.Option(
        None,
        help="Optional source release or artifact vintage label for update-audit provenance.",
    ),
```

Pass them into the builder:

```python
        result = build_model_diagnostics(
            predictions_path=predictions_path,
            intervals_path=intervals_path,
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
        )
```

Add echoes after the regional capacity echo:

```python
    typer.echo(
        f"Wrote {len(result.forecast_update_audit)} forecast update audit row(s) to "
        f"{outputs.forecast_update_audit_path}"
    )
    typer.echo(
        f"Wrote {len(result.forecast_update_summary)} forecast update summary row(s) to "
        f"{outputs.forecast_update_summary_path}"
    )
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_model_diagnostics.py -q
```

Expected: all CLI model diagnostics tests pass.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add tests/test_cli_model_diagnostics.py tickbiterisk/cli.py
git commit -m "feat: expose forecast update diagnostics cli"
```

---

### Task 4: Public Metadata And Dashboard Forecast Explainers

**Files:**
- Modify: `tests/test_static_export.py`
- Modify: `tickbiterisk/runtime/static_export.py`
- Modify: `tests/test_public_dashboard_static.py`
- Modify: `public/index.html`
- Modify: `public/app.js`
- Modify: `tests/browser/dashboard-smoke.spec.mjs`

- [ ] **Step 1: Write RED static export metadata assertions**

In `tests/test_static_export.py`, add assertions inside `test_export_static_risk_data_writes_public_json_files` after the existing model-card and source-catalog assertions:

```python
    assert model_card["forecasting_status"] == {
        "status": "forecasting_transition_research",
        "public_score_role": "relative county-week seasonal baseline with forecast-transition diagnostics",
        "update_policy": (
            "New surveillance and exposure signals are reconciled against prior "
            "forecasts before they are considered for future reviewed estimates."
        ),
    }
    assert source_catalog["data_lag_and_update_policy"]["summary"].startswith(
        "Official Lyme surveillance data lag"
    )
    assert source_catalog["data_lag_and_update_policy"]["forecast_boundary"] == (
        "Forecast-safe branches use prior-year and trailing data; nowcast or "
        "retrospective branches must be labeled separately."
    )
```

- [ ] **Step 2: Run the RED static export test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_static_export.py::test_export_static_risk_data_writes_public_json_files -q
```

Expected: fail because the JSON payloads do not include the new fields.

- [ ] **Step 3: Implement static export metadata fields**

In `_model_card_payload` in `tickbiterisk/runtime/static_export.py`, add:

```python
        "forecasting_status": {
            "status": "forecasting_transition_research",
            "public_score_role": "relative county-week seasonal baseline with forecast-transition diagnostics",
            "update_policy": (
                "New surveillance and exposure signals are reconciled against prior "
                "forecasts before they are considered for future reviewed estimates."
            ),
        },
```

In `_source_catalog_payload`, add:

```python
        "data_lag_and_update_policy": {
            "summary": (
                "Official Lyme surveillance data lag real-world exposure conditions, "
                "so TickBiteRisk treats forecasts as provisional informational "
                "estimates that improve as new validated data arrive."
            ),
            "forecast_boundary": (
                "Forecast-safe branches use prior-year and trailing data; nowcast or "
                "retrospective branches must be labeled separately."
            ),
            "medical_boundary": (
                "Forecasts do not diagnose disease, decide treatment, or determine "
                "whether an individual bite caused infection."
            ),
        },
```

- [ ] **Step 4: Write RED dashboard static assertions**

In `tests/test_public_dashboard_static.py`, add:

```python
def test_dashboard_explains_forecasting_and_update_policy() -> None:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "Why this is a forecast",
        "Official Lyme surveillance data lag",
        "How new data updates the model",
    ]:
        assert token in html

    for token in [
        "function renderForecastExplainer",
        "forecasting_status",
        "data_lag_and_update_policy",
        "Forecast-safe branches",
        "not diagnosis, treatment advice, or certainty about an individual bite",
    ]:
        assert token in js
```

- [ ] **Step 5: Run the RED dashboard static test**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_public_dashboard_static.py::test_dashboard_explains_forecasting_and_update_policy -q
```

Expected: fail because the explainer section and JS renderer do not exist.

- [ ] **Step 6: Add dashboard explainer section**

In `public/index.html`, add this section before the `validation-summary` section:

```html
      <section
        id="forecast-explainer"
        class="forecast-explainer"
        aria-labelledby="forecast-title"
      >
        <h2 id="forecast-title">Why this is a forecast</h2>
        <div id="forecast-content">
          <p>
            Official Lyme surveillance data lag real-world exposure conditions.
            TickBiteRisk uses historical patterns and forecast-safe signals to
            provide timely risk context while final case data catch up.
          </p>
          <h3>How new data updates the model</h3>
          <p>
            New surveillance, ecology, and exposure signals are reconciled
            against prior forecasts before they are fed forward into future
            estimates.
          </p>
        </div>
      </section>
```

In `public/app.js`, call the renderer in `init` after `renderValidationSummary();`:

```javascript
    renderForecastExplainer();
```

Add this function near `renderValidationSummary`:

```javascript
function renderForecastExplainer() {
  const container = document.getElementById("forecast-content");
  if (!container) return;
  const status = state.modelCard && state.modelCard.forecasting_status;
  const policy = state.sourceCatalog && state.sourceCatalog.data_lag_and_update_policy;
  const statusText =
    status && status.public_score_role
      ? status.public_score_role
      : "relative county-week seasonal baseline with forecast-transition diagnostics";
  const policyText =
    policy && policy.summary
      ? policy.summary
      : "Official Lyme surveillance data lag real-world exposure conditions.";
  const boundaryText =
    policy && policy.forecast_boundary
      ? policy.forecast_boundary
      : "Forecast-safe branches use prior-year and trailing data.";
  container.innerHTML = `
    <p>${escapeHtml(policyText)}</p>
    <p>${escapeHtml(statusText)}.</p>
    <h3>How new data updates the model</h3>
    <p>${escapeHtml(boundaryText)}</p>
    <p>Forecasts are informational estimates, not diagnosis, treatment advice, or certainty about an individual bite.</p>
  `;
}
```

- [ ] **Step 7: Update dashboard smoke test**

In `tests/browser/dashboard-smoke.spec.mjs`, add after the validation summary assertions:

```javascript
  await expect(page.locator("#forecast-explainer")).toContainText(
    "Why this is a forecast"
  );
  await expect(page.locator("#forecast-explainer")).toContainText(
    "How new data updates the model"
  );
```

- [ ] **Step 8: Run frontend/static focused tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_static_export.py tests/test_public_dashboard_static.py -q
npm run test:dashboard
```

Expected: Python static export/dashboard tests pass and Playwright dashboard smoke passes.

- [ ] **Step 9: Commit Task 4**

Run:

```bash
git add tests/test_static_export.py tickbiterisk/runtime/static_export.py tests/test_public_dashboard_static.py public/index.html public/app.js tests/browser/dashboard-smoke.spec.mjs
git commit -m "docs: explain forecasting in public surfaces"
```

---

### Task 5: README And Pipeline Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `docs/model-spec.md`

- [ ] **Step 1: Update README framing**

In `README.md`, replace the mission paragraph with:

```markdown
Build a transparent, Maryland-first tickborne disease risk forecasting research
product from open public data. The current implementation communicates relative
county-week Lyme seasonal baselines, forecast-update diagnostics, and a
single-bite Lyme decision-support score. Calibrated absolute infection
probabilities for any U.S. county remain a research goal.
```

Add this section after `quick start (static dashboard)`:

```markdown
## why forecast Lyme risk?

Official Lyme surveillance data often lag the conditions people are living
through now. Final county case counts may arrive months or years after the tick
season, while households, clinicians, parks, schools, and public health teams
need actionable risk context during the season itself.

TickBiteRisk treats forecasting as a way to make uncertainty visible before all
official data are final. The public score is informational risk context, not a
diagnosis, treatment recommendation, or certainty about any individual bite.

## how forecast updates work

The model starts with a prior forecast from historical Lyme incidence,
seasonality, forecast-safe weather/ecology and habitat context, host and human
exposure proxies, regional patterns, and surveillance caveats. When new
information arrives, the update-audit layer compares it with the prior forecast,
labels the source vintage and surveillance regime, and records whether the
change looks like disease-pressure signal, reporting-regime signal, or an
ambiguous update.

That reconciliation is the path toward stronger Bayesian or hierarchical
forecasting: new information should update the next forecast with its caveats
attached, not silently overwrite the model as if every source were equally
stable truth.
```

- [ ] **Step 2: Document new command in README ETL list**

In the Maryland ETL command block, add immediately after the `model-compare` command:

```bash
tickbiterisk etl model-diagnostics --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --intervals-path build/etl/model-comparison/model_comparison_intervals.csv --as-of-date 2026-05-28 --data-cutoff-date 2024-12-31 --source-vintage 2024-inclusive-local --output-dir build/etl/model-diagnostics
```

- [ ] **Step 3: Update docs/data-manifest.md**

Add to the `model_comparison` or diagnostics section:

```markdown
The forecast-update diagnostic layer writes `forecast_update_audit.csv` and
`forecast_update_summary.csv` under `build/etl/model-diagnostics`. These
artifacts replay held-out years as newly arrived data, preserving forecast
origin, as-of date, data cutoff, source vintage, surveillance regime, interval
coverage, and deterministic update interpretation. They are research artifacts
for forecasting validation and public wording review, not raw surveillance data.
```

- [ ] **Step 4: Update docs/etl-pipeline.md**

Under `tickbiterisk etl model-diagnostics`, add:

```markdown
    - Also writes `forecast_update_audit.csv` and
      `forecast_update_summary.csv`, which compare pre-update rolling-origin
      forecasts with newly observed held-out outcomes using explicit as-of,
      data-cutoff, source-vintage, and surveillance-regime fields.
```

Update the opening sentence that currently says the pipeline does not run a live disease forecast service to:

```markdown
This pipeline builds research-grade static forecast artifacts and a static
public dashboard. It does not run a live backend forecast service.
```

- [ ] **Step 5: Update docs/model-spec.md**

Add a `Forecast Update Contract` section:

```markdown
## Forecast Update Contract

Forecast-safe lanes use only prior-year and trailing information available
before the target year. Update-audit artifacts compare those prior forecasts
with later observed outcomes and preserve `forecast_year`,
`forecast_origin_year`, `as_of_date`, `data_cutoff_date`, `source_vintage`,
`evaluation_mode`, `update_mode`, and `surveillance_regime`.

Update interpretations are diagnostic labels. They do not convert observed
reported cases into latent true disease burden. Known reporting-break regimes
are kept separate from clean disease-pressure signals so future Bayesian or
hierarchical models can assign reliability to incoming evidence.
```

- [ ] **Step 6: Run docs/source tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_public_docs.py tests/test_public_dashboard_data.py -q
```

Expected: tests pass.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add README.md docs/data-manifest.md docs/etl-pipeline.md docs/model-spec.md
git commit -m "docs: document forecasting update workflow"
```

---

### Task 6: Live Rebuild And Final Verification

**Files:**
- No source edits expected unless verification reveals a defect.

- [ ] **Step 1: Rebuild model comparison and diagnostics artifacts**

Run:

```bash
PYTHONPATH=. ./.venv/bin/tickbiterisk etl model-compare \
  --design-matrix-path build/etl/model/model_design_matrix_county_year.csv \
  --start-year 2007 \
  --output-dir build/etl/model-comparison

PYTHONPATH=. ./.venv/bin/tickbiterisk etl model-diagnostics \
  --predictions-path build/etl/model-comparison/model_comparison_predictions.csv \
  --intervals-path build/etl/model-comparison/model_comparison_intervals.csv \
  --as-of-date 2026-05-28 \
  --data-cutoff-date 2024-12-31 \
  --source-vintage 2024-inclusive-local \
  --output-dir build/etl/model-diagnostics
```

Expected:

```text
forecast_update_audit.csv
forecast_update_summary.csv
```

are written under `build/etl/model-diagnostics`.

- [ ] **Step 2: Rebuild public dashboard data**

Run:

```bash
PYTHONPATH=. ./.venv/bin/tickbiterisk dashboard build-assets \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir public/data
```

Expected: `public/data/model_card.json` contains `forecasting_status`, and `public/data/source_catalog.json` contains `data_lag_and_update_policy`.

- [ ] **Step 3: Run full verification**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python -m pytest -q
PYTHONPATH=. ./.venv/bin/python -m ruff check .
npm run test:dashboard
git diff --check
```

Expected:

```text
397+ passed
All checks passed!
1 passed
```

The exact pytest count may increase after new tests land.

- [ ] **Step 4: Review model output summary**

Run:

```bash
head -n 5 build/etl/model-diagnostics/forecast_update_summary.csv
```

Expected: header includes `source_vintage`, `surveillance_regime`, `forecast_year`, and update interpretation counts.

- [ ] **Step 5: Commit rebuilt public data if it changed**

Run:

```bash
git status --short public/data
git add public/data
git commit -m "data: refresh public forecasting metadata"
```

If `git status --short public/data` prints no changed files, skip the commit and record that public data already matched the source changes.

---

## Self-Review Notes

- Spec coverage: Tasks 1-3 implement `forecast_update_audit.csv` and `forecast_update_summary.csv`; Task 4 captures dashboard metadata and visible explainers; Task 5 updates README and modeling/pipeline docs; Task 6 verifies live artifacts.
- Forecast safety: Audit rows carry `forecast_origin_year`, `as_of_date`, `data_cutoff_date`, `source_vintage`, `evaluation_mode`, `update_mode`, and `surveillance_regime`.
- Bayesian stance: The plan creates a Bayesian-ready update contract and a go/no-go evidence base, without adding PyMC/MCMC in this increment.
- Public boundary: Dashboard language describes a forecasting transition and a relative seasonal baseline while preserving "not diagnosis/treatment/personal infection certainty" caveats.
