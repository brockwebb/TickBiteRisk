import json
from pathlib import Path

from typer.testing import CliRunner

from tests.test_runtime_risk_lookup import _write_scores
from tests.test_static_export import _write_ambiguous_scores
from tests.test_dashboard_assets import (
    _regional_geojson,
    _write_regional_overlay_summary,
)
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


def test_dashboard_build_regional_research_assets_writes_bundle(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    regional_geojson_path = tmp_path / "regional_counties.geojson"
    regional_geojson_path.write_text(
        json.dumps(_regional_geojson()),
        encoding="utf-8",
    )
    overlay_path = _write_regional_overlay_summary(tmp_path / "overlays.csv")
    output_dir = tmp_path / "regional-dashboard"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-regional-research-assets",
            "--scores-path",
            str(scores_path),
            "--regional-counties-geojson-path",
            str(regional_geojson_path),
            "--spatial-regime-summary-path",
            str(overlay_path),
            "--output-dir",
            str(output_dir),
            "--model-name",
            "linear_blend_baseline",
        ],
    )

    assert result.exit_code == 0
    assert "regional research dashboard assets" in result.stdout
    assert (output_dir / "regional_county_risk_weekly.json").exists()
    assert (output_dir / "regional_counties.geojson").exists()
    assert (output_dir / "regional_spatial_regime_overlays.json").exists()


def test_dashboard_build_regional_research_assets_fails_when_geometry_missing(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    missing_geojson = tmp_path / "missing.geojson"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-regional-research-assets",
            "--scores-path",
            str(scores_path),
            "--regional-counties-geojson-path",
            str(missing_geojson),
            "--output-dir",
            str(tmp_path / "regional-dashboard"),
        ],
    )

    assert result.exit_code != 0
    assert "Regional county GeoJSON file not found" in result.output
    assert "Traceback" not in result.output


def test_dashboard_build_regional_research_assets_can_skip_overlay(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    regional_geojson_path = tmp_path / "regional_counties.geojson"
    regional_geojson_path.write_text(
        json.dumps(_regional_geojson()),
        encoding="utf-8",
    )
    output_dir = tmp_path / "regional-dashboard"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-regional-research-assets",
            "--scores-path",
            str(scores_path),
            "--regional-counties-geojson-path",
            str(regional_geojson_path),
            "--no-spatial-regime-overlays",
            "--output-dir",
            str(output_dir),
            "--model-name",
            "linear_blend_baseline",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "regional_county_risk_weekly.json").exists()
    assert (output_dir / "regional_counties.geojson").exists()
    assert not (output_dir / "regional_spatial_regime_overlays.json").exists()
