import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app

runner = CliRunner()


def test_model_features_command_writes_feature_matrix(tmp_path: Path) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24003",
                "year": "2022",
                "confirmed_cases": "10",
                "probable_cases": "5",
                "total_cases": "15",
                "canonical_source_id": "cdc_2022",
                "source_values_summary": "",
                "reconciliation_status": "matched",
                "data_quality_flags": "",
            }
        ],
    )
    population = _write_csv(
        tmp_path / "population.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "year": "2022",
                "population": "600000",
            }
        ],
    )
    weather = _write_csv(tmp_path / "weather.csv", [_weather_row()])
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-features",
            "--lyme-outcomes-path",
            str(lyme),
            "--population-path",
            str(population),
            "--weather-weekly-path",
            str(weather),
            "--contact-pressure-path",
            str(tmp_path / "missing-contact.csv"),
            "--deer-harvest-path",
            str(tmp_path / "missing-deer.csv"),
            "--output-dir",
            str(output_dir),
        ],
    )

    output_path = output_dir / "model_features_county_year.csv"
    assert result.exit_code == 0
    assert output_path.exists()
    assert f"Wrote 1 model feature row(s) to {output_path}" in result.stdout

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["lyme_incidence_per_100k"] == "2.5"
    assert rows[0]["model_feature_quality_flags"] == (
        "missing_contact_pressure,missing_deer_harvest_prior_season"
    )


def test_model_features_command_fails_cleanly_when_required_path_missing(
    tmp_path: Path,
) -> None:
    population = _write_csv(
        tmp_path / "population.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "year": "2022",
                "population": "600000",
            }
        ],
    )
    weather = _write_csv(tmp_path / "weather.csv", [_weather_row()])

    result = runner.invoke(
        app,
        [
            "etl",
            "model-features",
            "--lyme-outcomes-path",
            str(tmp_path / "missing-lyme.csv"),
            "--population-path",
            str(population),
            "--weather-weekly-path",
            str(weather),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Lyme outcomes file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_features_county_year.csv").exists()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _weather_row(**overrides: str) -> dict[str, str]:
    row = {
        "county_fips": "24003",
        "iso_year": "2022",
        "iso_week": "1",
        "week_start_date": "2022-01-03",
        "days_observed": "7",
        "expected_days": "7",
        "week_complete": "true",
        "days_above_40f": "7",
        "days_50_65f": "1",
        "days_70_85f": "0",
        "degree_days_above_40f": "50",
        "freeze_thaw_days": "1",
        "precip_total_mm": "4",
        "snowfall_total_mm": "1",
        "precip_days": "2",
        "dry_spell_max_days": "3",
        "temp_mean_f": "45",
        "precip_mean_mm": "0.5",
        "temp_anomaly_vs_10yr": "0",
        "precip_anomaly_vs_10yr": "0",
        "feature_quality_flags": "",
    }
    row.update(overrides)
    return row
