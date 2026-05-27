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
    tick_status = _write_csv(
        tmp_path / "tick_status.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "ixodes_scapularis_status": "established",
                "ixodes_pacificus_status": "no_records",
                "borrelia_burgdorferi_status": "present",
                "borrelia_miyamotoi_status": "no_records",
                "anaplasma_phagocytophilum_status": "present",
                "babesia_microti_status": "no_records",
                "powassan_virus_status": "no_records",
                "amblyomma_americanum_status": "established",
                "tick_status_source_ids": "cdc_ixodes_county_status_2025",
                "tick_status_feature_quality_flags": (
                    "current_status_retrospective_proxy,"
                    "status_only_not_prevalence"
                ),
            }
        ],
    )
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
            "--mast-acorn-path",
            str(tmp_path / "missing-mast.csv"),
            "--usdm-drought-path",
            str(tmp_path / "missing-drought.csv"),
            "--enviroatlas-habitat-path",
            str(tmp_path / "missing-habitat.csv"),
            "--tick-status-path",
            str(tick_status),
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
    assert rows[0]["ixodes_scapularis_status"] == "established"
    assert rows[0]["borrelia_burgdorferi_status"] == "present"
    assert rows[0]["model_feature_quality_flags"] == (
        "missing_contact_pressure,missing_deer_harvest_prior_season,"
        "current_status_retrospective_proxy,status_only_not_prevalence,"
        "no_records_not_absence"
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


def test_model_features_command_fails_cleanly_when_explicit_tick_status_missing(
    tmp_path: Path,
) -> None:
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
            "--tick-status-path",
            str(tmp_path / "missing-tick-status.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Tick status file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_features_county_year.csv").exists()


def test_model_features_command_accepts_mast_acorn_path(tmp_path: Path) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24001",
                "year": "2022",
                "confirmed_cases": "10",
                "probable_cases": "0",
                "total_cases": "10",
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
                "county_fips": "24001",
                "county_name": "Allegany County",
                "year": "2022",
                "population": "100000",
            }
        ],
    )
    weather = _write_csv(
        tmp_path / "weather.csv",
        [_weather_row(county_fips="24001", iso_year="2022")],
    )
    mast = _write_csv(
        tmp_path / "mast.csv",
        [
            {
                "county_fips": "24001",
                "county_name": "Allegany County",
                "year": "2021",
                "region": "Western Maryland",
                "mast_category": "oak_acorn_abundance",
                "mast_index": "1.92",
                "mast_rating": "mast_failure",
                "acorn_index": "1.92",
                "hard_mast_index": "1.92",
                "soft_mast_index": "",
                "plots_observed": "",
                "expected_plots": "",
                "coverage_complete": "",
                "source_id": "maryland_dnr_wmd_mast_survey_2021",
                "source_url_hash": "hash",
                "source_report_year": "2021",
                "parser_method": "pypdfium_table_text",
                "extraction_confidence": "high",
                "black_oak_acorns_per_branch": "1.97",
                "white_oak_acorns_per_branch": "1.90",
                "unit_average_acorns_per_branch": "1.92",
                "black_oak_mast_rating": "I",
                "white_oak_mast_rating": "I",
                "unit_average_mast_rating": "I",
                "white_oak_subjective_crown_pct": "3.75",
                "black_oak_subjective_crown_pct": "1.45",
                "feature_quality_flags": (
                    "western_maryland_only,study_plot_not_countywide"
                ),
                "extracted_text_excerpt": "excerpt",
            }
        ],
    )
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
            "--mast-acorn-path",
            str(mast),
            "--usdm-drought-path",
            str(tmp_path / "missing-drought.csv"),
            "--enviroatlas-habitat-path",
            str(tmp_path / "missing-habitat.csv"),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "model_features_county_year.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["mast_index_prior_year"] == "1.92"
    assert rows[0]["black_oak_acorns_per_branch_prior_year"] == "1.97"
    assert "western_maryland_only" in rows[0]["model_feature_quality_flags"]


def test_model_features_command_accepts_drought_and_habitat_paths(
    tmp_path: Path,
) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24003",
                "year": "2022",
                "confirmed_cases": "10",
                "probable_cases": "0",
                "total_cases": "10",
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
                "population": "100000",
            }
        ],
    )
    weather = _write_csv(tmp_path / "weather.csv", [_weather_row()])
    drought = _write_csv(
        tmp_path / "drought.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "year": "2022",
                "usdm_week_count": "52",
                "usdm_dsci_mean": "85.5",
                "usdm_dsci_max": "250",
                "usdm_weeks_d0_or_worse": "20",
                "usdm_weeks_d1_or_worse": "8",
                "usdm_weeks_d2_or_worse": "2",
                "usdm_tick_season_week_count": "26",
                "usdm_tick_season_dsci_mean": "92.25",
                "usdm_tick_season_weeks_d1_or_worse": "5",
                "source_ids": "usdm_county_statistics",
                "feature_quality_flags": "drought_monitor_retro_observed",
            }
        ],
    )
    habitat = _write_csv(
        tmp_path / "habitat.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "forest_pct": "35.6",
                "forest_woody_wetland_pct": "45.3",
                "wetland_pct": "10.8",
                "emergent_wetland_pct": "1.2",
                "developed_pct": "39.7",
                "impervious_pct": "11.8",
                "agriculture_pct": "11.8",
                "pasture_hay_pct": "3.4",
                "cultivated_crop_pct": "8.4",
                "riparian_natural_45m_pct": "75.0",
                "riparian_forest_45m_pct": "34.5",
                "riparian_forest_woody_wetland_45m_pct": "68.8",
                "natural_land_cover_index": "48.4",
                "source_url_hash": "hash",
                "feature_quality_flags": "static_enviroatlas_2011",
            }
        ],
    )
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
            "--usdm-drought-path",
            str(drought),
            "--enviroatlas-habitat-path",
            str(habitat),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "model_features_county_year.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["usdm_dsci_mean"] == "85.5"
    assert rows[0]["forest_pct"] == "35.6"
    assert "drought_monitor_retro_observed" in rows[0]["model_feature_quality_flags"]
    assert "static_enviroatlas_2011" in rows[0]["model_feature_quality_flags"]


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
