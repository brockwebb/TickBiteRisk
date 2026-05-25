from typer.testing import CliRunner

from tests.test_building_permits import BPS_SAMPLE
from tickbiterisk.cli import app


runner = CliRunner()


def test_building_permits_command_writes_county_year_output(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_census_bps_county_text",
        lambda url: BPS_SAMPLE,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "building-permits",
            "--start-year",
            "2024",
            "--end-year",
            "2024",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 building permit row(s)" in result.stdout
    assert (tmp_path / "maryland_building_permits_county_year.csv").exists()


def test_building_permits_rejects_unsupported_year_without_traceback(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "building-permits",
            "--start-year",
            "2026",
            "--end-year",
            "2026",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "2000-2025" in result.output
    assert "Traceback" not in result.output


def test_building_permits_rejects_inverted_year_range(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "building-permits",
            "--start-year",
            "2025",
            "--end-year",
            "2024",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "start-year must be less than or equal to end-year" in result.output
    assert "Traceback" not in result.output
