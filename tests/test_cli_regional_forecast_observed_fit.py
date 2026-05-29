from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_forecast_observed_fit import (
    _write_forecast_predictions,
    _write_incidence_panel,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_forecast_observed_fit_command_writes_outputs(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-forecast-observed-fit",
            "--forecast-predictions-path",
            str(forecast),
            "--regional-incidence-path",
            str(incidence),
            "--forecast-year",
            "2024",
            "--state-abbr",
            "PA",
            "--model-name",
            "empirical_bayes_spatial_regime_incidence",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_forecast_observed_fit_comparisons.csv" in result.stdout
    assert (output_dir / "regional_forecast_observed_fit_runs.csv").exists()
    assert (output_dir / "regional_forecast_observed_fit_comparisons.csv").exists()
    assert (output_dir / "regional_forecast_observed_fit_summary.csv").exists()


def test_regional_forecast_observed_fit_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-forecast-observed-fit",
            "--forecast-predictions-path",
            str(missing_path),
            "--regional-incidence-path",
            str(tmp_path / "incidence.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional forecast predictions not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
