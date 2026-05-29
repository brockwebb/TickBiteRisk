import json
from pathlib import Path

from typer.testing import CliRunner

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.cli import app


runner = CliRunner()


def test_static_export_command_writes_public_json_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    model_summary_path = tmp_path / "model_summary.csv"
    model_summary_path.write_text(
        "\n".join(
            [
                (
                    "run_id,rank_by_mae,model_name,model_family,feature_profile,"
                    "n_predictions,mae_incidence_per_100k,rmse_incidence_per_100k,"
                    "pearson_correlation,comparison_assumption_flags"
                ),
                "run1,1,linear_blend_baseline,ensemble,lagged_outcome_blend,2,1.25,2.5,0.7,observational_not_causal",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
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
            "--model-summary-path",
            str(model_summary_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote static public risk export" in result.stdout
    weekly = json.loads(
        (output_dir / "md_county_risk_weekly.json").read_text(encoding="utf-8")
    )
    assert weekly["record_count"] == 2
    model_card = json.loads((output_dir / "model_card.json").read_text(encoding="utf-8"))
    assert model_card["validation_summary"]["mae_incidence_per_100k"] == 1.25
    assert (output_dir / "md_county_metadata.json").exists()
    assert (output_dir / "model_card.json").exists()
    assert (output_dir / "source_catalog.json").exists()
    assert (output_dir / "static_export_manifest.json").exists()


def test_static_export_command_accepts_regional_research_scope(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "regional-data"

    result = runner.invoke(
        app,
        [
            "risk",
            "export-static",
            "--scores-path",
            str(scores_path),
            "--output-dir",
            str(output_dir),
            "--geography-scope",
            "midatlantic_county_week",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "regional_county_risk_weekly.json").exists()
    assert (output_dir / "regional_county_metadata.json").exists()
    weekly = json.loads(
        (output_dir / "regional_county_risk_weekly.json").read_text(
            encoding="utf-8"
        )
    )
    assert weekly["scope"] == "midatlantic_county_week"


def test_static_export_command_rejects_regional_scope_default_public_output(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")

    result = runner.invoke(
        app,
        [
            "risk",
            "export-static",
            "--scores-path",
            str(scores_path),
            "--geography-scope",
            "midatlantic_county_week",
        ],
    )

    assert result.exit_code != 0
    assert "Regional research export requires" in result.output
    assert "non-public" in result.output
    assert "output-dir" in result.output
    assert "Traceback" not in result.output


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
