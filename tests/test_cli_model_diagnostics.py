from pathlib import Path

from typer.testing import CliRunner

from tests.test_model_diagnostics import _write_predictions
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
