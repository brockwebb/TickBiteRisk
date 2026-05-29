import csv
from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_annual_forecast_intervals import (
    _write_interval_artifact,
    _write_forecast_predictions,
    _write_spatial_regime_assignments,
    _write_stress_predictions,
)
from tests.test_regional_annual_forecast import _sha256_file
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_annual_forecast_intervals_command_writes_outputs(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast-intervals",
            "--forecast-predictions-path",
            str(forecast_predictions),
            "--regional-incidence-stress-predictions-path",
            str(stress_predictions),
            "--min-residual-count",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_annual_forecast_intervals.csv" in result.stdout
    assert "regional_annual_forecast_interval_summary.csv" in result.stdout
    assert (output_dir / "regional_annual_forecast_interval_runs.csv").exists()
    assert (output_dir / "regional_annual_forecast_intervals.csv").exists()
    assert (output_dir / "regional_annual_forecast_interval_summary.csv").exists()
    with (output_dir / "regional_annual_forecast_intervals.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["forecast_year"] for row in rows} == {"2023"}
    assert {row["forecast_origin_year"] for row in rows} == {"2021"}
    assert "actual_cases" not in rows[0]
    assert "covered_95" not in rows[0]


def test_regional_annual_forecast_intervals_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast-intervals",
            "--forecast-predictions-path",
            str(missing_path),
            "--regional-incidence-stress-predictions-path",
            str(tmp_path / "stress.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional forecast predictions not found: {missing_path}" in result.output
    assert "Traceback" not in result.output


def test_regional_annual_forecast_intervals_command_fails_cleanly_for_bad_numeric(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
    )
    _replace_csv_value(
        stress_predictions,
        row_index=0,
        column="residual_incidence_per_100k",
        value="not-a-number",
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast-intervals",
            "--forecast-predictions-path",
            str(forecast_predictions),
            "--regional-incidence-stress-predictions-path",
            str(stress_predictions),
            "--min-residual-count",
            "2",
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "residual_incidence_per_100k must be numeric" in result.output
    assert "Traceback" not in result.output


def test_regional_spatial_regime_forecast_interval_summary_command_writes_outputs(
    tmp_path: Path,
) -> None:
    intervals_path = _write_interval_artifact(tmp_path)
    regimes_path = _write_spatial_regime_assignments(
        tmp_path / "regional_spatial_regime_county_year.csv",
        source_file_sha256=_sha256_file(tmp_path / "incidence.csv"),
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-spatial-regime-forecast-interval-summary",
            "--regional-annual-forecast-intervals-path",
            str(intervals_path),
            "--regional-spatial-regime-county-year-path",
            str(regimes_path),
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_spatial_regime_forecast_interval_summary.csv" in result.stdout
    assert (
        output_dir / "regional_spatial_regime_forecast_interval_summary_runs.csv"
    ).exists()
    assert (
        output_dir / "regional_spatial_regime_forecast_interval_summary.csv"
    ).exists()
    with (
        output_dir / "regional_spatial_regime_forecast_interval_summary.csv"
    ).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["geography_level"] for row in rows} == {"spatial_regime"}
    assert {row["spatial_regime_feature_year"] for row in rows} == {"2022"}


def test_regional_spatial_regime_forecast_interval_summary_command_fails_cleanly(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing_intervals.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-spatial-regime-forecast-interval-summary",
            "--regional-annual-forecast-intervals-path",
            str(missing_path),
            "--regional-spatial-regime-county-year-path",
            str(tmp_path / "regimes.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "Regional annual forecast intervals not found" in result.output
    assert str(missing_path) in result.output
    assert "Traceback" not in result.output


def _replace_csv_value(
    path: Path,
    *,
    row_index: int,
    column: str,
    value: str,
) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    rows[row_index][column] = value
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
