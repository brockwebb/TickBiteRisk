import csv

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
    manifest_path = tmp_path / "out" / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "usdm_county_statistics_md_2020"
    assert row["citation_url"] == "https://droughtmonitor.unl.edu/DmData/DataDownload.aspx"
    assert row["request_method"] == "GET"
    assert row["request_description"] == (
        "USDM CountyStatistics GetDSCI and "
        "GetDroughtSeverityStatisticsByAreaPercent requests for MD 2020."
    )
    assert row["parser_method"] == (
        "fetch_usdm_drought_year;parse_usdm_dsci_csv;parse_usdm_severity_csv"
    )
    assert row["extraction_quality"] == "accepted"
    assert row["row_count"] == "1"
    assert "tickbiterisk etl usdm-drought" in row["acquisition_command"]
    assert "--provenance-manifest-path" in row["acquisition_command"]
    assert "usdm_drought_weekly.csv=" in row["derived_artifact_sha256s"]
    assert "usdm_drought_county_year.csv=" in row["derived_artifact_sha256s"]
    assert "GetDSCI" in row["source_url"]
    assert "GetDroughtSeverityStatisticsByAreaPercent" in row["source_url"]


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


def test_usdm_drought_command_writes_one_provenance_row_per_year(
    tmp_path,
    monkeypatch,
) -> None:
    def fake_fetch(url: str) -> str:
        if "startdate=1%2F1%2F2021" in url and "GetDSCI" in url:
            return "State,County,FIPS,MapDate,DSCI\nMD,Allegany County,24001,2021-04-06,80\n"
        if "startdate=1%2F1%2F2021" in url:
            return (
                "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4\n"
                "2021-04-06,24001,Allegany County,MD,20,80,0,0,0,0\n"
            )
        if "GetDSCI" in url:
            return "State,County,FIPS,MapDate,DSCI\nMD,Allegany County,24001,2020-04-07,100\n"
        return (
            "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4\n"
            "2020-04-07,24001,Allegany County,MD,0,100,0,0,0,0\n"
        )

    monkeypatch.setattr("tickbiterisk.cli.fetch_usdm_text", fake_fetch)

    result = runner.invoke(
        app,
        [
            "etl",
            "usdm-drought",
            "--start-year",
            "2020",
            "--end-year",
            "2021",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    with (tmp_path / "out" / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert [row["source_id"] for row in rows] == [
        "usdm_county_statistics_md_2020",
        "usdm_county_statistics_md_2021",
    ]
    assert [row["row_count"] for row in rows] == ["1", "1"]
