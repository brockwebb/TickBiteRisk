import csv

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.census_population import CensusCountyPopulation
from tickbiterisk.etl.county_reference import CENSUS_GAZETTEER_COUNTIES_2024_URL


runner = CliRunner()


def test_census_population_dry_run_prints_sanitized_urls(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tickbiterisk.cli.get_census_api_key", lambda: "secret-key")

    result = runner.invoke(
        app,
        [
            "etl",
            "census-population",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Planned Census population query(s)" in result.stdout
    assert "1990/pep/int_charagegroups" in result.stdout
    assert "2023/pep/charv" in result.stdout
    assert "co-est2025-alldata.csv" in result.stdout
    assert "secret-key" not in result.stdout
    assert not (tmp_path / "county_population_year.csv").exists()
    assert not (tmp_path / "acquisition_provenance.csv").exists()


def test_census_population_latest_only_dry_run_uses_static_csv_without_api_key(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("tickbiterisk.cli.get_census_api_key", lambda: "secret-key")

    result = runner.invoke(
        app,
        [
            "etl",
            "census-population",
            "--output-dir",
            str(tmp_path),
            "--latest-only",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Planned Census population query(s): 1" in result.stdout
    assert "co-est2025-alldata.csv" in result.stdout
    assert "secret-key" not in result.stdout
    assert "api.census.gov" not in result.stdout
    assert not (tmp_path / "acquisition_provenance.csv").exists()


def test_census_population_command_writes_population_output(tmp_path, monkeypatch) -> None:
    rows = [
        CensusCountyPopulation(
            county_fips="24003",
            county_name="Anne Arundel County",
            year=2023,
            population=590336,
            source_id="census_pep_2023_charv",
            census_dataset="2023/pep/charv",
            vintage=2023,
            source_url_hash="c" * 64,
        )
    ]

    def fake_fetch(**kwargs):
        assert kwargs["api_key"] == "secret-key"
        return rows

    monkeypatch.setattr("tickbiterisk.cli.get_census_api_key", lambda: "secret-key")
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_maryland_county_population_estimates",
        fake_fetch,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "census-population",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 county-year population row(s)" in result.stdout
    assert (tmp_path / "county_population_year.csv").exists()
    manifest_path = tmp_path / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    assert len(manifest_rows) == 8
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert "secret-key" not in manifest_text
    assert "key=%3Credacted%3E" in manifest_text
    assert all(row["source_id"].startswith("census_population_") for row in manifest_rows)
    assert all(row["request_method"] == "GET" for row in manifest_rows)
    assert all(row["citation_url"].startswith("https://www.census.gov/") for row in manifest_rows)
    assert all("county_population_year.csv=" in row["derived_artifact_sha256s"] for row in manifest_rows)
    assert any(row["row_count"] == "1" for row in manifest_rows)
    assert all("tickbiterisk etl census-population" in row["acquisition_command"] for row in manifest_rows)
    assert all("--provenance-manifest-path" in row["acquisition_command"] for row in manifest_rows)


def test_census_population_latest_only_appends_to_existing_output(tmp_path, monkeypatch) -> None:
    output = tmp_path / "county_population_year.csv"
    output.write_text(
        "county_fips,county_name,year,population,source_id,census_dataset,vintage,source_url_hash\n"
        "24003,Anne Arundel County,2023,590336,census_pep_2023_charv,2023/pep/charv,2023,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        encoding="utf-8",
    )
    rows = [
        CensusCountyPopulation(
            county_fips="24003",
            county_name="Anne Arundel County",
            year=2024,
            population=594582,
            source_id="census_pep_2025_county_totals",
            census_dataset="2020-2025/counties/totals/co-est2025-alldata.csv",
            vintage=2025,
            source_url_hash="d" * 64,
        )
    ]

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_maryland_latest_county_population_estimates",
        lambda: rows,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "census-population",
            "--output-dir",
            str(tmp_path),
            "--latest-only",
            "--append",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 county-year population row(s)" in result.stdout
    assert "append=True" in result.stdout
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert "24003,Anne Arundel County,2023,590336" in lines[1]
    assert "24003,Anne Arundel County,2024,594582" in lines[2]
    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        manifest_rows = list(csv.DictReader(handle))
    assert len(manifest_rows) == 1
    row = manifest_rows[0]
    assert row["source_id"] == "census_population_2025_county_totals"
    assert "co-est2025-alldata.csv" in row["source_url"]
    assert row["row_count"] == "1"
    assert "--latest-only" in row["acquisition_command"]
    assert "--append" in row["acquisition_command"]


def test_county_reference_command_writes_maryland_gazetteer_output(
    tmp_path,
    monkeypatch,
) -> None:
    sample = (
        "USPS\tGEOID\tANSICODE\tNAME\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG\n"
        "MD\t24003\t01710958\tAnne Arundel County\t1074169609\t448789171\t414.739\t173.278\t38.991617\t-76.560894\n"
    )

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_census_gazetteer_counties_text",
        lambda url=CENSUS_GAZETTEER_COUNTIES_2024_URL: sample,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "county-reference",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 county reference row(s)" in result.stdout
    assert (tmp_path / "county_reference.csv").exists()
    manifest_path = tmp_path / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_id"] == "census_county_reference_2024"
    assert rows[0]["source_url"] == CENSUS_GAZETTEER_COUNTIES_2024_URL
    assert rows[0]["citation_url"] == "https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html"
    assert rows[0]["request_method"] == "GET"
    assert rows[0]["row_count"] == "1"
    assert rows[0]["parser_method"] == "parse_census_gazetteer_counties"
    assert rows[0]["extraction_quality"] == "accepted"
    assert "county_reference.csv=" in rows[0]["derived_artifact_sha256s"]
    assert "tickbiterisk etl county-reference" in rows[0]["acquisition_command"]
    assert "--provenance-manifest-path" in rows[0]["acquisition_command"]
