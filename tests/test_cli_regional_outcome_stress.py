from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_outcome_stress import _write_regional_panel
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_outcome_stress_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_regional_panel(tmp_path / "regional.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-outcome-stress",
            "--regional-lyme-path",
            str(panel),
            "--start-year",
            "2021",
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
    assert "regional_outcome_stress_predictions.csv" in result.stdout
    assert (output_dir / "regional_outcome_stress_runs.csv").exists()
    assert (output_dir / "regional_outcome_stress_predictions.csv").exists()
    assert (output_dir / "regional_outcome_stress_metrics.csv").exists()


def test_regional_outcome_stress_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-outcome-stress",
            "--regional-lyme-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional Lyme panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output


def test_regional_outcome_stress_command_rejects_nonfinite_share_prior(
    tmp_path: Path,
) -> None:
    panel = _write_regional_panel(tmp_path / "regional.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-outcome-stress",
            "--regional-lyme-path",
            str(panel),
            "--start-year",
            "2021",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--share-prior-strength",
            "nan",
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "share-prior-strength must be finite and non-negative" in result.output
    assert "Traceback" not in result.output
