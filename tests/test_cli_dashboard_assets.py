import json
from pathlib import Path

from typer.testing import CliRunner

from tests.test_runtime_risk_lookup import _write_scores
from tests.test_static_export import _write_ambiguous_scores
from tickbiterisk.cli import app


runner = CliRunner()


def test_dashboard_build_assets_writes_public_data_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "public" / "data"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-assets",
            "--scores-path",
            str(scores_path),
            "--output-dir",
            str(output_dir),
            "--use-fixture-geometry",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote dashboard assets" in result.stdout
    assert (output_dir / "md_county_risk_weekly.json").exists()
    assert (output_dir / "md_counties.geojson").exists()
    geojson = json.loads(
        (output_dir / "md_counties.geojson").read_text(encoding="utf-8")
    )
    assert geojson["metadata"]["feature_count"] == 24


def test_dashboard_build_assets_fails_cleanly_when_scores_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-assets",
            "--scores-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "public" / "data"),
        ],
    )

    assert result.exit_code != 0
    assert "Risk score file not found" in result.output
    assert "Traceback" not in result.output


def test_dashboard_build_assets_help_uses_forecast_language() -> None:
    result = runner.invoke(app, ["dashboard", "build-assets", "--help"])
    normalized = " ".join(result.output.split())

    assert result.exit_code == 0
    assert "risk forecast" in normalized
    assert "CSV" in normalized
    assert "risk baseline CSV" not in normalized


def test_dashboard_build_assets_accepts_source_branch_selectors(
    tmp_path: Path,
) -> None:
    scores_path = _write_ambiguous_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "public" / "data"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-assets",
            "--scores-path",
            str(scores_path),
            "--output-dir",
            str(output_dir),
            "--source-prediction-sha256",
            "c" * 64,
            "--use-fixture-geometry",
        ],
    )

    assert result.exit_code == 0
    weekly = json.loads(
        (output_dir / "md_county_risk_weekly.json").read_text(encoding="utf-8")
    )
    assert weekly["selected_score_config"]["source_prediction_sha256"] == "c" * 64
    assert weekly["records"][0]["risk_score"] == 8
