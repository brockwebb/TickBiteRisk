import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.regional_demographics import RegionalAgeDemographic


runner = CliRunner()


def test_regional_demographics_command_writes_output_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_urls(*, state_fips_list=("10", "11", "24", "42", "51", "54")):
        return [
            "https://www2.census.gov/programs-surveys/popest/datasets/"
            "2020-2024/counties/asrh/cc-est2024-agesex-24.csv"
        ]

    def fake_fetch(*, state_fips_list=("10", "11", "24", "42", "51", "54")):
        return [
            RegionalAgeDemographic(
                state_fips="24",
                state_abbr="MD",
                state_name="Maryland",
                county_fips="24011",
                county_name="Caroline County",
                year=2024,
                population=100,
                under5_population=5,
                age5_13_population=10,
                age14_17_population=5,
                age5_17_population=15,
                age18_24_population=8,
                age25_44_population=22,
                age45_64_population=30,
                age65plus_population=20,
                median_age=43.1,
                under5_share=0.05,
                age5_17_share=0.15,
                age18_24_share=0.08,
                age25_44_share=0.22,
                age45_64_share=0.3,
                age65plus_share=0.2,
                source_id="census_pep_2024_county_age_sex_24",
                census_dataset=(
                    "2020-2024/counties/asrh/cc-est2024-agesex-24.csv"
                ),
                vintage=2024,
                source_url_hash="fixture",
                feature_quality_flags=(
                    "population_structure_proxy,human_exposure_context_only,"
                    "not_tick_bite_counts,census_vintage_revision_sensitive"
                ),
            )
        ]

    monkeypatch.setattr("tickbiterisk.cli.build_midatlantic_age_sex_urls", fake_urls)
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_midatlantic_age_sex_demographics",
        fake_fetch,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-demographics",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 Mid-Atlantic county-year demographic row(s)" in result.stdout
    output_path = tmp_path / "out" / "midatlantic_age_demographics_county_year.csv"
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24011"
    assert rows[0]["age5_17_share"] == "0.15"
    assert rows[0]["feature_quality_flags"] == (
        "population_structure_proxy,human_exposure_context_only,"
        "not_tick_bite_counts,census_vintage_revision_sensitive"
    )

    with (tmp_path / "out" / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert provenance_rows[0]["source_id"] == "census_pep_2024_county_age_sex_24"
    assert "cc-est2024-agesex-24.csv" in provenance_rows[0]["source_url"]
    assert "midatlantic_age_demographics_county_year.csv=" in provenance_rows[0][
        "derived_artifact_sha256s"
    ]
