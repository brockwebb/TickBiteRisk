import csv
from pathlib import Path

from typer.testing import CliRunner

from tests.test_step1_forecast_skill_anchor import _write_observed_fit_comparisons
from tickbiterisk.cli import app


runner = CliRunner()


def test_step1_forecast_skill_anchor_command_writes_outputs(
    tmp_path: Path,
) -> None:
    comparisons = _write_observed_fit_comparisons(tmp_path)
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "step1-forecast-skill-anchor",
            "--observed-fit-comparisons-path",
            str(comparisons),
            "--forecast-year",
            "2024",
            "--state-abbr",
            "PA",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "step1_forecast_skill_anchor.csv" in result.stdout
    with (output_dir / "step1_forecast_skill_anchor.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["permitted_use"] == "interval_calibration_only"
    assert rows[0]["point_correction_allowed"] == "False"


def test_step1_forecast_skill_anchor_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "step1-forecast-skill-anchor",
            "--observed-fit-comparisons-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "Observed-fit comparisons not found" in result.output
    assert str(missing_path) in result.output
    assert "Traceback" not in result.output
