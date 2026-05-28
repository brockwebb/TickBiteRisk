import csv

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
    manifest_path = tmp_path / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "census_bps_county_2024"
    assert row["source_url"] == "https://www2.census.gov/econ/bps/County/co2412y.txt"
    assert row["citation_url"] == "https://www.census.gov/construction/bps/"
    assert row["request_method"] == "GET"
    assert row["row_count"] == "2"
    assert row["parser_method"] == "parse_census_bps_county_text"
    assert row["extraction_quality"] == "accepted"
    assert "tickbiterisk etl building-permits" in row["acquisition_command"]
    assert "--provenance-manifest-path" in row["acquisition_command"]
    assert "maryland_building_permits_county_year.csv=" in row[
        "derived_artifact_sha256s"
    ]


def test_building_permits_command_reports_deduped_written_row_count(
    tmp_path, monkeypatch
) -> None:
    duplicate_anne_arundel = (
        "202412,24,003,3,5,Anne Arundel County,"
        "1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000,"
        "1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000"
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_census_bps_county_text",
        lambda url: f"{BPS_SAMPLE}\n{duplicate_anne_arundel}\n",
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

    output = tmp_path / "maryland_building_permits_county_year.csv"
    assert result.exit_code == 0
    assert "Wrote 2 building permit row(s)" in result.stdout
    assert output.exists()
    assert output.read_text(encoding="utf-8").count("\n") == 3


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


def test_building_permits_command_writes_one_provenance_row_per_year(
    tmp_path,
    monkeypatch,
) -> None:
    def fake_fetch(url: str) -> str:
        year_prefix = "202512" if "co2512y" in url else "202412"
        return BPS_SAMPLE.replace("202412", year_prefix)

    monkeypatch.setattr("tickbiterisk.cli.fetch_census_bps_county_text", fake_fetch)

    result = runner.invoke(
        app,
        [
            "etl",
            "building-permits",
            "--start-year",
            "2024",
            "--end-year",
            "2025",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert [row["source_id"] for row in rows] == [
        "census_bps_county_2024",
        "census_bps_county_2025",
    ]
    assert [row["row_count"] for row in rows] == ["2", "2"]
