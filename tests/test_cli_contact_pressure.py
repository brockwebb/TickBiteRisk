from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.contact_pressure import ContactPressureFeature


runner = CliRunner()


def test_contact_pressure_command_writes_features(tmp_path, monkeypatch) -> None:
    building_permits = tmp_path / "bps.csv"
    county_reference = tmp_path / "county_reference.csv"
    population = tmp_path / "population.csv"
    building_permits.write_text("fixture", encoding="utf-8")
    county_reference.write_text("fixture", encoding="utf-8")
    population.write_text("fixture", encoding="utf-8")

    monkeypatch.setattr(
        "tickbiterisk.cli.build_contact_pressure_features",
        lambda *, building_permits_path, county_reference_path, population_path: [
            ContactPressureFeature(
                county_fips="24003",
                county_name="Anne Arundel County",
                year=2024,
                residential_units_authorized=120,
                units_authorized_per_sqmi=0.289292,
                units_authorized_per_100k=None,
                total_value_dollars=43000000,
                land_area_sqmi=414.806,
                population=None,
                source_id="census_bps_county_2024",
                source_url_hash="hash2024",
                feature_quality_flags="construction_proxy_only,missing_population",
            )
        ],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "contact-pressure",
            "--building-permits-path",
            str(building_permits),
            "--county-reference-path",
            str(county_reference),
            "--population-path",
            str(population),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 contact pressure feature row(s)" in result.stdout
    assert (tmp_path / "out" / "contact_pressure_features_county_year.csv").exists()
