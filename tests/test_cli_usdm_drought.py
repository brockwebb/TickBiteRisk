from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_usdm_drought_command_writes_weekly_and_county_year_outputs(
    tmp_path,
    monkeypatch,
) -> None:
    dsci_csv = """State,County,FIPS,MapDate,DSCI
MD,Allegany County,24001,2020-04-07,100
MD,Allegany County,24001,2020-04-07,100
"""
    severity_csv = """MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4
2020-04-07,24001,Allegany County,MD,0,100,0,0,0,0
"""

    def fake_fetch(url: str) -> str:
        if "GetDSCI" in url:
            return dsci_csv
        return severity_csv

    monkeypatch.setattr("tickbiterisk.cli.fetch_usdm_text", fake_fetch)

    result = runner.invoke(
        app,
        [
            "etl",
            "usdm-drought",
            "--start-year",
            "2020",
            "--end-year",
            "2020",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 USDM weekly drought row(s)" in result.stdout
    assert "Wrote 1 USDM county-year drought feature row(s)" in result.stdout
    assert (tmp_path / "out" / "usdm_drought_weekly.csv").exists()
    assert (tmp_path / "out" / "usdm_drought_county_year.csv").exists()


def test_usdm_drought_command_rejects_invalid_year_range(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "usdm-drought",
            "--start-year",
            "2021",
            "--end-year",
            "2020",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "start-year must be less than or equal to end-year" in result.output
