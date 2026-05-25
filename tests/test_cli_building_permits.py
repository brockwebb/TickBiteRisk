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
