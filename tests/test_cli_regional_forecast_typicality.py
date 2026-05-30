from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_forecast_typicality import (
    _write_forecast_intervals,
    _write_incidence_panel,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_forecast_typicality_command_writes_outputs(
    tmp_path: Path,
) -> None:
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")
    intervals = _write_forecast_intervals(tmp_path / "intervals.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-forecast-typicality",
            "--regional-incidence-path",
            str(incidence),
            "--regional-annual-forecast-intervals-path",
            str(intervals),
            "--model-name",
            "empirical_bayes_spatial_regime_incidence",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_forecast_typicality_runs.csv" in result.stdout
    assert "regional_forecast_typicality.csv" in result.stdout
    assert (output_dir / "regional_forecast_typicality_runs.csv").exists()
    assert (output_dir / "regional_forecast_typicality.csv").exists()


def test_regional_forecast_typicality_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-forecast-typicality",
            "--regional-incidence-path",
            str(missing_path),
            "--regional-annual-forecast-intervals-path",
            str(tmp_path / "intervals.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional incidence panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
