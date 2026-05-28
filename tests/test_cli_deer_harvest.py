import csv

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.deer_harvest import MarylandDnrDeerAnnualReportSource


runner = CliRunner()


def test_deer_harvest_command_writes_density_output(tmp_path, monkeypatch) -> None:
    county_reference = tmp_path / "county_reference.csv"
    county_reference.write_text(
        "\n".join(
            [
                "county_fips,state_fips,state,county_name,aland_sqmi,awater_sqmi,intptlat,intptlon,geography_source,source_url_hash",
                "24001,24,MD,Allegany County,422.199,5.68,39.612313,-78.703104,Census Gazetteer 2024 counties,cccc",
            ]
        ),
        encoding="utf-8",
    )
    sample_html = """
    <table>
      <tr><td colspan="10">Maryland Reported Antlered and Antlerless Deer Harvest for the 2024-2025 and 2025-2026 Hunting Seasons</td></tr>
      <tr><td></td><td colspan="3">Antlered</td><td colspan="3">Antlerless</td><td colspan="3">Total</td></tr>
      <tr><td>County</td><td>2024-25</td><td>2025-26</td><td>% Change</td><td>2024-25</td><td>2025-26</td><td>% Change</td><td>2024-25</td><td>2025-26</td><td>% Change</td></tr>
      <tr><td>Allegany</td><td>1,868</td><td>1,739</td><td>-6.9</td><td>1,544</td><td>1,185</td><td>-23.3</td><td>3,412</td><td>2,924</td><td>-14.3</td></tr>
      <tr><td>Allegany</td><td>1,868</td><td>1,739</td><td>-6.9</td><td>1,544</td><td>1,185</td><td>-23.3</td><td>3,412</td><td>2,924</td><td>-14.3</td></tr>
    </table>
    """

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_maryland_dnr_deer_harvest_html",
        lambda url: sample_html,
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.MARYLAND_DNR_DEER_HARVEST_URLS",
        ["https://example.test/deer-harvest"],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "deer-harvest",
            "--county-reference-path",
            str(county_reference),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 deer harvest row(s)" in result.stdout
    assert (tmp_path / "maryland_dnr_deer_harvest.csv").exists()
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "md_dnr_deer_harvest"
    assert row["source_name"] == "Maryland DNR deer harvest news table"
    assert row["source_url"] == "https://example.test/deer-harvest"
    assert row["citation_url"] == "https://example.test/deer-harvest"
    assert row["request_method"] == "GET"
    assert row["row_count"] == "4"
    assert row["parser_method"] == "parse_maryland_dnr_deer_harvest_html"
    assert row["extraction_quality"] == "accepted"
    assert "tickbiterisk etl deer-harvest" in row["acquisition_command"]
    assert "--provenance-manifest-path" in row["acquisition_command"]
    assert "--url https://example.test/deer-harvest" in row["acquisition_command"]
    assert "maryland_dnr_deer_harvest.csv=" in row["derived_artifact_sha256s"]


def test_deer_harvest_command_can_use_annual_report_pdfs(tmp_path, monkeypatch) -> None:
    county_reference = tmp_path / "county_reference.csv"
    county_reference.write_text(
        "\n".join(
            [
                "county_fips,state_fips,state,county_name,aland_sqmi,awater_sqmi,intptlat,intptlon,geography_source,source_url_hash",
                "24001,24,MD,Allegany County,422.199,5.68,39.612313,-78.703104,Census Gazetteer 2024 counties,cccc",
                "24011,24,MD,Caroline County,319.416,6.04,38.871531,-75.829040,Census Gazetteer 2024 counties,cccc",
            ]
        ),
        encoding="utf-8",
    )
    sample_markdown = """
    Maryland Reported Antlered and Antlerless Harvest for
    Archery, Firearm, and Muzzleloader Hunting Seasons
    by County, 2024-2025

    | County | Archery Antlered | Archery Antlerless | Archery Total | Firearm Antlered | Firearm Antlerless | Firearm Total | Muzzleloader Antlered | Muzzleloader Antlerless | Muzzleloader Total | Total Antlered | Total Antlerless | Total |
    | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
    | Allegany | 528 | 389 | 917 | 1,015 | 757 | 1,772 | 325 | 398 | 723 | 1,868 | 1,544 | 3,412 |
    | Caroline | | | | | | | | | | | | |
    | White-Tailed | 291 | 425 | 716 | 456 | 1,454 | 1,910 | 131 | 383 | 514 | 878 | 2,262 | 3,140 |
    | Sika | 1 | 1 | 2 | 1 | 0 | 1 | 0 | 1 | 1 | 2 | 2 | 4 |
    """

    monkeypatch.setattr("tickbiterisk.cli.MARYLAND_DNR_DEER_HARVEST_URLS", [])
    monkeypatch.setattr(
        "tickbiterisk.cli.MARYLAND_DNR_DEER_ANNUAL_REPORT_URLS",
        [
            MarylandDnrDeerAnnualReportSource(
                season_start_year=2024,
                season_label="2024-25",
                url="https://example.test/report.pdf",
            )
        ],
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.parse_maryland_dnr_deer_harvest_pdf",
        lambda source, *, source_url, source_id, parser: __import__(
            "tickbiterisk.etl.deer_harvest",
            fromlist=["parse_maryland_dnr_deer_harvest_text"],
        ).parse_maryland_dnr_deer_harvest_text(
            sample_markdown,
            source_url=source_url,
            source_id=source_id,
        ),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "deer-harvest",
            "--county-reference-path",
            str(county_reference),
            "--output-dir",
            str(tmp_path),
            "--include-annual-report-pdfs",
            "--skip-news-html",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 4 deer harvest row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "md_dnr_deer_annual_report_2024_2025"
    assert row["source_name"] == "Maryland DNR deer annual report PDF"
    assert row["source_url"] == "https://example.test/report.pdf"
    assert (
        row["citation_url"]
        == "https://dnr.maryland.gov/wildlife/Pages/hunt_trap/Deer_AnnualReports.aspx"
    )
    assert row["row_count"] == "4"
    assert row["parser_method"] == "parse_maryland_dnr_deer_harvest_pdf:pypdfium"
    assert "--include-annual-report-pdfs" in row["acquisition_command"]
    assert "--skip-news-html" in row["acquisition_command"]
