import json
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tests.test_runtime_risk_lookup import _write_scores


runner = CliRunner()


def test_risk_lookup_command_returns_json_response(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")

    result = runner.invoke(
        app,
        [
            "risk",
            "lookup",
            "--county-fips",
            "24003",
            "--date",
            "2023-01-01",
            "--scores-path",
            str(scores_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["county_fips"] == "24003"
    assert payload["risk_score"] == 7
    assert payload["risk_category"] == "high"
    assert payload["query_date"] == "2023-01-01"
    assert payload["model_family"] == "ensemble"
    assert payload["feature_set"] == "historical_outcome_baselines"
    assert payload["evaluation_mode"] == "forecast_prior_year"
    assert payload["weather_mode"] == "not_used_by_baseline"
    assert "clinical_disclaimer" in payload


def test_risk_lookup_command_fails_cleanly_when_scores_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "risk",
            "lookup",
            "--county-fips",
            "24003",
            "--date",
            "2023-01-01",
            "--scores-path",
            str(tmp_path / "missing.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "Risk score file not found" in result.output
    assert "Traceback" not in result.output


def test_risk_single_bite_command_returns_decision_support_json(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")

    result = runner.invoke(
        app,
        [
            "risk",
            "single-bite",
            "--county-fips",
            "24003",
            "--date",
            "2023-01-01",
            "--scores-path",
            str(scores_path),
            "--tick-species",
            "blacklegged",
            "--tick-stage",
            "nymph",
            "--attachment-hours",
            "40",
            "--engorgement",
            "engorged",
            "--hours-since-removal",
            "24",
            "--doxycycline-safe",
            "--pretty",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["county_fips"] == "24003"
    assert payload["single_bite_risk_score"] >= payload["baseline_context"][
        "county_week_risk_score"
    ]
    assert payload["pep_consideration"] == "meets_cdc_consideration_criteria"
    assert payload["input_summary"]["tick_species"] == "ixodes_scapularis"
    assert "clinical_disclaimer" in payload


def test_risk_single_bite_command_fails_cleanly_when_scores_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "risk",
            "single-bite",
            "--county-fips",
            "24003",
            "--scores-path",
            str(tmp_path / "missing.csv"),
            "--tick-species",
            "blacklegged",
        ],
    )

    assert result.exit_code != 0
    assert "Risk score file not found" in result.output
    assert "Traceback" not in result.output
