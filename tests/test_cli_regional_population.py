import csv

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.regional_population import RegionalCountyPopulation


runner = CliRunner()


def test_regional_population_dry_run_prints_sanitized_urls(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tickbiterisk.cli.get_census_api_key", lambda: "secret-key")

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-population",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "Planned Mid-Atlantic Census population query(s): 8" in result.stdout
    assert "co-est00int-alldata-10.csv" in result.stdout
    assert "co-est00int-alldata-54.csv" in result.stdout
    assert "co-est2019-alldata.csv" in result.stdout
    assert "co-est2023-alldata.csv" in result.stdout
    assert "secret-key" not in result.stdout
    assert not (tmp_path / "midatlantic_county_population_year.csv").exists()


def test_regional_population_command_writes_output_and_provenance(
    tmp_path,
    monkeypatch,
) -> None:
    rows = [
        RegionalCountyPopulation(
            state_fips="42",
            state_abbr="PA",
            state_name="Pennsylvania",
            county_fips="42001",
            county_name="Adams County",
            year=2023,
            population=104000,
            source_id="census_pep_2023_county_totals",
            census_dataset="2020-2023/counties/totals/co-est2023-alldata.csv",
            vintage=2023,
            source_url_hash="c" * 64,
            feature_quality_flags="regional_population_denominator",
        )
    ]

    def fake_fetch(**kwargs):
        assert kwargs["api_key"] == "secret-key"
        return rows

    monkeypatch.setattr("tickbiterisk.cli.get_census_api_key", lambda: "secret-key")
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_midatlantic_county_population_estimates",
        fake_fetch,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-population",
            "--output-dir",
            str(tmp_path),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "Wrote 1 Mid-Atlantic county-year population row(s)" in result.stdout
    assert (tmp_path / "midatlantic_county_population_year.csv").exists()
    manifest_path = tmp_path / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    assert len(manifest_rows) == 8
    assert all(row["source_id"].startswith("census_midatlantic_population_") for row in manifest_rows)
    assert all("secret-key" not in str(row) for row in manifest_rows)
    assert all("static CSV endpoint" in row["access_notes"] for row in manifest_rows)
    assert all("API endpoint" not in row["access_notes"] for row in manifest_rows)
    assert any(row["row_count"] == "1" for row in manifest_rows)
