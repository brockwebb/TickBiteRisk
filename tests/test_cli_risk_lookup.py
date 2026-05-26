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
