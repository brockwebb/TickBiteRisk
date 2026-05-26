import json
from pathlib import Path

from typer.testing import CliRunner

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.cli import app


runner = CliRunner()


def test_static_export_command_writes_public_json_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "public-data"

    result = runner.invoke(
        app,
        [
            "risk",
            "export-static",
            "--scores-path",
            str(scores_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote static public risk export" in result.stdout
    weekly = json.loads(
        (output_dir / "md_county_risk_weekly.json").read_text(encoding="utf-8")
    )
    assert weekly["record_count"] == 2
    assert (output_dir / "md_county_metadata.json").exists()
    assert (output_dir / "model_card.json").exists()
    assert (output_dir / "source_catalog.json").exists()
    assert (output_dir / "static_export_manifest.json").exists()


def test_static_export_command_fails_cleanly_when_scores_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "risk",
            "export-static",
            "--scores-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "public-data"),
        ],
    )

    assert result.exit_code != 0
    assert "Risk score file not found" in result.output
    assert "Traceback" not in result.output
