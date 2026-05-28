from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_annual_forecast import (
    _write_incidence_panel,
    _write_population,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_annual_forecast_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    population = _write_population(tmp_path / "population.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast",
            "--regional-incidence-path",
            str(panel),
            "--regional-population-path",
            str(population),
            "--target-year",
            "2023",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_annual_forecast_predictions.csv" in result.stdout
    assert (output_dir / "regional_annual_forecast_runs.csv").exists()
    assert (output_dir / "regional_annual_forecast_predictions.csv").exists()


def test_regional_annual_forecast_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast",
            "--regional-incidence-path",
            str(missing_path),
            "--population-path",
            str(tmp_path / "population.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional incidence panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output


def test_regional_annual_forecast_command_rejects_non_future_target_year(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    population = _write_population(tmp_path / "population.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-annual-forecast",
            "--regional-incidence-path",
            str(panel),
            "--population-path",
            str(population),
            "--target-year",
            "2021",
            "--forecast-origin-year",
            "2021",
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "target-year must be greater than forecast-origin-year" in result.output
    assert "Traceback" not in result.output
