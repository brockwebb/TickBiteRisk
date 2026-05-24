from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.census_population import CensusCountyPopulation


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
    assert "secret-key" not in result.stdout
    assert not (tmp_path / "county_population_year.csv").exists()


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
