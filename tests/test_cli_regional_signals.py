import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_signals_command_writes_signal_artifact(tmp_path: Path) -> None:
    panel_path = tmp_path / "midatlantic_lyme_county_year.csv"
    output_dir = tmp_path / "out"
    _write_panel(panel_path)

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-signals",
            "--regional-lyme-path",
            str(panel_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 9 Mid-Atlantic regional signal row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout
    with (output_dir / "midatlantic_regional_signals.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 9
    anne_2002 = next(
        row for row in rows if row["county_fips"] == "24003" and row["year"] == "2002"
    )
    assert anne_2002["feature_prior_year_midatlantic_total_cases"] == "20"
    assert anne_2002["diagnostic_midatlantic_total_within_trailing_5yr_band"] == "False"
    assert anne_2002["source_panel_sha256"]

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "midatlantic_regional_signals"
    ]
    provenance = provenance_rows[0]
    assert provenance["row_count"] == "9"
    assert "midatlantic_lyme_county_year.csv=" in provenance[
        "derived_artifact_sha256s"
    ]
    assert "midatlantic_regional_signals.csv=" in provenance[
        "derived_artifact_sha256s"
    ]
    assert str(tmp_path) not in provenance["derived_artifact_paths"]


def test_regional_signals_command_fails_cleanly_when_panel_missing(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "etl",
            "regional-signals",
            "--regional-lyme-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Regional Lyme panel not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()


def _write_panel(path: Path) -> None:
    from tests.test_regional_signals import _write_panel as write_fixture

    write_fixture(path)
