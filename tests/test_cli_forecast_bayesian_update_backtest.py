from pathlib import Path

from typer.testing import CliRunner

from tests.test_forecast_calibration_backtest import _write_calibration_predictions
from tickbiterisk.cli import app


runner = CliRunner()


def test_forecast_bayesian_update_backtest_command_writes_outputs(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "forecast-bayesian-update-backtest",
            "--predictions-path",
            str(predictions),
            "--start-year",
            "2019",
            "--min-prior-updates",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "forecast_bayesian_update_backtest_predictions.csv" in result.stdout
    assert (output_dir / "forecast_bayesian_update_backtest_runs.csv").exists()
    assert (output_dir / "forecast_bayesian_update_backtest_predictions.csv").exists()
    assert (output_dir / "forecast_bayesian_update_backtest_metrics.csv").exists()


def test_forecast_bayesian_update_backtest_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "forecast-bayesian-update-backtest",
            "--predictions-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Model comparison predictions file not found: {missing_path}" in (
        result.output
    )
    assert "Traceback" not in result.output
