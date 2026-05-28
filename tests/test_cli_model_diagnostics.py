from pathlib import Path

from typer.testing import CliRunner

from tests.test_model_diagnostics import _write_intervals, _write_predictions
from tickbiterisk.cli import app


runner = CliRunner()


def test_model_diagnostics_command_writes_surveillance_outputs(
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
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "surveillance_regime_residuals.csv" in result.stdout
    assert (output_dir / "surveillance_regime_residuals.csv").exists()
    assert (output_dir / "surveillance_regime_summary.csv").exists()


def test_model_diagnostics_command_writes_forecast_update_outputs(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_intervals(tmp_path / "intervals.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(predictions),
            "--intervals-path",
            str(intervals),
            "--output-dir",
            str(output_dir),
            "--as-of-date",
            "2026-05-28",
            "--data-cutoff-date",
            "2024-12-31",
            "--source-vintage",
            "model_compare_fixture_v1",
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "Wrote 7 forecast update audit row(s)" in result.stdout
    assert "forecast_update_audit.csv" in result.stdout
    assert "Wrote 10 forecast update summary row(s)" in result.stdout
    assert "forecast_update_summary.csv" in result.stdout
    assert "Wrote 10 forecast calibration summary row(s)" in result.stdout
    assert "forecast_calibration_summary.csv" in result.stdout

    audit_path = output_dir / "forecast_update_audit.csv"
    summary_path = output_dir / "forecast_update_summary.csv"
    calibration_path = output_dir / "forecast_calibration_summary.csv"
    assert audit_path.exists()
    assert summary_path.exists()
    assert calibration_path.exists()
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "2026-05-28" in audit_text
    assert "2024-12-31" in audit_text
    assert "model_compare_fixture_v1" in audit_text


def test_model_diagnostics_command_fails_cleanly_when_predictions_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Model comparison predictions file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "surveillance_regime_residuals.csv").exists()


def test_model_diagnostics_command_fails_cleanly_when_intervals_missing(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals_path = Path("missing_intervals.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(predictions),
            "--intervals-path",
            str(intervals_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert (
        f"Model comparison intervals file not found: {intervals_path}" in result.output
    )
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "surveillance_regime_residuals.csv").exists()


def test_model_diagnostics_command_fails_cleanly_for_blank_numeric_input(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    text = predictions.read_text(encoding="utf-8")
    predictions.write_text(text.replace(",10,100000,", ",,100000,", 1), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-diagnostics",
            "--predictions-path",
            str(predictions),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert "missing required numeric value in actual_cases" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "surveillance_regime_residuals.csv").exists()
