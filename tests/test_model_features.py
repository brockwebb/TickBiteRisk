import csv
import math
from dataclasses import replace
from pathlib import Path

from tickbiterisk.etl.model_features import (
    ModelCountyYearFeature,
    build_model_feature_matrix,
)
from tickbiterisk.etl.model_features_build import (
    MODEL_FEATURE_COLUMNS,
    write_model_feature_matrix_output,
)


def test_build_model_feature_matrix_aggregates_required_and_optional_inputs(
    tmp_path: Path,
) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24003",
                "year": "2022",
                "confirmed_cases": "10.0",
                "probable_cases": "5.0",
                "total_cases": "15.0",
                "canonical_source_id": "cdc_2022",
                "source_values_summary": "cdc=15",
                "reconciliation_status": "matched",
                "data_quality_flags": "reviewed;legacy_source",
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
                "extra": "ignored",
            }
        ],
    )
    weather = _write_csv(
        tmp_path / "weather.csv",
        [
            _weather_row(
                week_start_date="2022-04-04",
                week_end_date="2022-04-10",
                days_observed="7.0",
                expected_days="7.0",
                week_complete="true",
                days_above_40f="7.0",
                days_50_65f="3.0",
                days_70_85f="1.0",
                degree_days_above_40f="70.5",
                freeze_thaw_days="2.0",
                precip_total_mm="10.25",
                snowfall_total_mm="0",
                precip_days="2.0",
                dry_spell_max_days="4.0",
                temp_mean_f="50",
                precip_mean_mm="1",
                temp_anomaly_vs_10yr="2",
                precip_anomaly_vs_10yr="0.5",
                feature_quality_flags="estimated_station",
            ),
            _weather_row(
                week_start_date="2022-07-04",
                week_end_date="2022-07-10",
                days_observed="3.0",
                expected_days="7.0",
                week_complete="false",
                days_above_40f="3.0",
                days_50_65f="0",
                days_70_85f="3.0",
                degree_days_above_40f="120.25",
                freeze_thaw_days="0",
                precip_total_mm="5",
                snowfall_total_mm="0",
                precip_days="1.0",
                dry_spell_max_days="6.0",
                temp_mean_f="80",
                precip_mean_mm="2",
                temp_anomaly_vs_10yr="-1",
                precip_anomaly_vs_10yr="1.5",
                feature_quality_flags="partial_week",
            ),
        ],
    )
    contact = _write_csv(
        tmp_path / "contact.csv",
        [
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "year": "2022",
                "residential_units_authorized": "1200",
                "units_authorized_per_sqmi": "2.5",
                "units_authorized_per_100k": "200",
                "total_value_dollars": "450000000",
                "feature_quality_flags": "construction_proxy_only",
            }
        ],
    )
    deer = _write_csv(
        tmp_path / "deer.csv",
        [
            {
                "county_fips": "24003",
                "season_start_year": "2021",
                "species": "all_deer",
                "total_harvest": "1600",
                "harvest_per_sqmi": "3.25",
                "is_derived_total": "true",
            },
            {
                "county_fips": "24003",
                "season_start_year": "2022",
                "species": "all_deer",
                "total_harvest": "9999",
                "harvest_per_sqmi": "99",
                "is_derived_total": "false",
            },
        ],
    )
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
                "tick_status_source_ids": (
                    "cdc_ixodes_county_status_2025,"
                    "cdc_ixodes_pathogen_status_2025,"
                    "cdc_lone_star_status_2024"
                ),
                "tick_status_feature_quality_flags": (
                    "current_status_retrospective_proxy,"
                    "no_records_not_absence,status_only_not_prevalence"
                ),
            }
        ],
    )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
        contact_pressure_path=contact,
        deer_harvest_path=deer,
        tick_status_path=tick_status,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24003"
    assert row.county_name == "Anne Arundel County"
    assert row.lyme_incidence_per_100k == 2.5
    assert row.log_population_offset == round(math.log(600000), 6)
    assert row.weather_weeks_observed == 2
    assert row.weather_complete_week_count == 1
    assert row.weather_days_observed == 10
    assert row.weather_expected_days == 14
    assert row.weather_observation_ratio == 0.714286
    assert row.weather_days_above_40f == 10
    assert row.weather_days_70_85f == 4
    assert row.weather_degree_days_above_40f == 190.75
    assert row.weather_precip_total_mm == 15.25
    assert row.weather_dry_spell_max_days == 6
    assert row.weather_temp_mean_f == 59.0
    assert row.weather_precip_mean_mm == 1.3
    assert row.weather_temp_anomaly_vs_10yr == 1.1
    assert row.weather_precip_anomaly_vs_10yr == 0.8
    assert row.tick_season_days_above_40f == 10
    assert row.tick_season_days_70_85f == 4
    assert row.tick_season_precip_total_mm == 15.25
    assert row.spring_days_above_40f == 7
    assert row.summer_days_70_85f == 3
    assert row.weather_feature_quality_flags == "estimated_station,partial_week"
    assert row.residential_units_authorized == 1200
    assert row.contact_pressure_total_value_dollars == 450000000
    assert row.deer_total_harvest_prior_season == 1600
    assert row.deer_harvest_per_sqmi_prior_season == 3.25
    assert row.deer_is_derived_total is True
    assert row.ixodes_scapularis_status == "established"
    assert row.borrelia_burgdorferi_status == "present"
    assert row.amblyomma_americanum_status == "established"
    assert row.tick_status_feature_quality_flags == (
        "current_status_retrospective_proxy,"
        "no_records_not_absence,status_only_not_prevalence"
    )
    assert row.model_feature_quality_flags == (
        "reviewed,legacy_source,partial_weather_year,"
        "deer_prior_season_derived_total,current_status_retrospective_proxy,"
        "no_records_not_absence,status_only_not_prevalence"
    )


def test_build_model_feature_matrix_preserves_rows_when_optional_inputs_missing(
    tmp_path: Path,
) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24001",
                "year": "2021",
                "confirmed_cases": "4",
                "probable_cases": "1",
                "total_cases": "5",
                "canonical_source_id": "cdc_2021",
                "source_values_summary": "",
                "reconciliation_status": "conflict",
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
                "year": "2021",
                "population": "100000",
            }
        ],
    )
    weather = _write_csv(
        tmp_path / "weather.csv",
        [
            _weather_row(
                county_fips="24001",
                iso_year="2021",
                week_start_date="2021-01-04",
            )
        ],
    )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
        contact_pressure_path=None,
        deer_harvest_path=None,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.residential_units_authorized is None
    assert row.deer_total_harvest_prior_season is None
    assert row.model_feature_quality_flags == (
        "lyme_source_conflict,missing_contact_pressure,"
        "missing_deer_harvest_prior_season"
    )


def test_build_model_feature_matrix_joins_mast_acorn_as_prior_year_feature(
    tmp_path: Path,
) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            _lyme_row("24001", 2020, 8),
            _lyme_row("24001", 2021, 10),
            _lyme_row("24001", 2022, 12),
        ],
    )
    population = _write_csv(
        tmp_path / "population.csv",
        [
            _population_row("24001", "Allegany County", 2020),
            _population_row("24001", "Allegany County", 2021),
            _population_row("24001", "Allegany County", 2022),
        ],
    )
    weather = _write_csv(
        tmp_path / "weather.csv",
        [
            _weather_row(
                county_fips="24001",
                iso_year="2020",
                week_start_date="2020-01-06",
            ),
            _weather_row(
                county_fips="24001",
                iso_year="2021",
                week_start_date="2021-01-04",
            ),
            _weather_row(
                county_fips="24001",
                iso_year="2022",
                week_start_date="2022-01-03",
            ),
        ],
    )
    mast = _write_csv(
        tmp_path / "mast.csv",
        [
            _mast_row(
                county_fips="24001",
                county_name="Allegany County",
                year=2020,
                source_report_year=2020,
                mast_index="7.76",
                black_oak="0.75",
                source_id="maryland_dnr_wmd_mast_survey_2020",
            ),
            _mast_row(
                county_fips="24001",
                county_name="Allegany County",
                year=2020,
                source_report_year=2021,
                mast_index="99.0",
                black_oak="88.0",
                source_id="maryland_dnr_wmd_mast_survey_2021",
            ),
            _mast_row(
                county_fips="24001",
                county_name="Allegany County",
                year=2021,
                source_report_year=2021,
                mast_index="1.92",
                black_oak="1.97",
                source_id="maryland_dnr_wmd_mast_survey_2021",
            ),
        ],
    )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
        mast_acorn_path=mast,
    )

    row_2020 = next(row for row in rows if row.year == 2020)
    assert row_2020.mast_index_prior_year is None
    assert "missing_mast_acorn_prior_year" in row_2020.model_feature_quality_flags

    row_2021 = next(row for row in rows if row.year == 2021)
    assert row_2021.mast_index_prior_year == 99.0
    assert row_2021.acorn_index_prior_year == 99.0
    assert row_2021.hard_mast_index_prior_year == 99.0
    assert row_2021.black_oak_acorns_per_branch_prior_year == 88.0
    assert row_2021.white_oak_acorns_per_branch_prior_year == 14.77
    assert row_2021.unit_average_acorns_per_branch_prior_year == 99.0
    assert row_2021.white_oak_subjective_crown_pct_prior_year == 1.75
    assert row_2021.black_oak_subjective_crown_pct_prior_year == 34.0
    assert row_2021.mast_source_ids_prior_year == "maryland_dnr_wmd_mast_survey_2021"
    assert row_2021.mast_source_report_year_prior_year == 2021
    assert row_2021.mast_feature_quality_flags_prior_year == (
        "western_maryland_only,study_plot_not_countywide"
    )
    assert "western_maryland_only" in row_2021.model_feature_quality_flags
    assert "study_plot_not_countywide" in row_2021.model_feature_quality_flags

    row_2022 = next(row for row in rows if row.year == 2022)
    assert row_2022.mast_index_prior_year == 1.92


def test_build_model_feature_matrix_flags_missing_tick_status_only_when_opted_in(
    tmp_path: Path,
) -> None:
    lyme, population, weather = _minimal_required_inputs(tmp_path, county_fips="24003")
    tick_status = _write_csv(
        tmp_path / "tick_status.csv",
        [
            {
                "county_fips": "24005",
                "county_name": "Baltimore County",
                "ixodes_scapularis_status": "established",
                "ixodes_pacificus_status": "no_records",
                "borrelia_burgdorferi_status": "present",
                "borrelia_miyamotoi_status": "no_records",
                "anaplasma_phagocytophilum_status": "no_records",
                "babesia_microti_status": "no_records",
                "powassan_virus_status": "no_records",
                "amblyomma_americanum_status": "established",
                "tick_status_source_ids": "cdc_ixodes_county_status_2025",
                "tick_status_feature_quality_flags": (
                    "current_status_retrospective_proxy,"
                    "status_only_not_prevalence,no_records_not_absence"
                ),
            }
        ],
    )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
        tick_status_path=tick_status,
    )

    assert len(rows) == 1
    assert "missing_tick_status" in rows[0].model_feature_quality_flags.split(",")


def test_build_model_feature_matrix_adds_no_records_guard_from_status_values(
    tmp_path: Path,
) -> None:
    lyme, population, weather = _minimal_required_inputs(tmp_path, county_fips="24003")
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

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
        tick_status_path=tick_status,
    )

    assert "no_records_not_absence" in rows[0].model_feature_quality_flags.split(",")


def test_build_model_feature_matrix_apportions_boundary_weeks_to_calendar_year(
    tmp_path: Path,
) -> None:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": "24003",
                "year": "2022",
                "confirmed_cases": "4.0",
                "probable_cases": "1.0",
                "total_cases": "5.0",
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
    weather = _write_csv(
        tmp_path / "weather.csv",
        [
            _weather_row(
                iso_year="2021",
                week_start_date="2021-12-27",
                week_end_date="2022-01-02",
                days_observed="7",
                expected_days="7",
                days_above_40f="7",
                precip_total_mm="14",
                dry_spell_max_days="7",
                temp_mean_f="49",
            )
        ],
    )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme,
        population_path=population,
        weather_weekly_path=weather,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.weather_expected_days == 2
    assert row.weather_days_observed == 2
    assert row.weather_days_above_40f == 2
    assert row.weather_precip_total_mm == 4
    assert row.weather_dry_spell_max_days == 2
    assert row.weather_temp_mean_f == 49


def test_write_model_feature_matrix_output_orders_and_dedupes_rows(
    tmp_path: Path,
) -> None:
    first = _model_row(county_fips="2403", year=2022, total_cases=15)
    second = _model_row(county_fips="24001", year=2021, total_cases=5)
    replacement = replace(first, county_fips="02403", total_cases=20)

    write_model_feature_matrix_output([first, second], tmp_path)
    output = write_model_feature_matrix_output([replacement], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))

    assert output.name == "model_features_county_year.csv"
    assert list(records[0].keys()) == MODEL_FEATURE_COLUMNS
    assert [(row["county_fips"], row["year"]) for row in records] == [
        ("02403", "2022"),
        ("24001", "2021"),
    ]
    assert records[0]["total_cases"] == "20"


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
        "week_end_date": "2022-01-09",
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


def _minimal_required_inputs(
    tmp_path: Path,
    *,
    county_fips: str,
) -> tuple[Path, Path, Path]:
    lyme = _write_csv(
        tmp_path / "lyme.csv",
        [
            {
                "county_fips": county_fips,
                "year": "2022",
                "confirmed_cases": "4",
                "probable_cases": "1",
                "total_cases": "5",
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
                "county_fips": county_fips,
                "county_name": "Anne Arundel County",
                "year": "2022",
                "population": "100000",
            }
        ],
    )
    weather = _write_csv(
        tmp_path / "weather.csv",
        [_weather_row(county_fips=county_fips, week_start_date="2022-01-03")],
    )
    return lyme, population, weather


def _lyme_row(county_fips: str, year: int, total_cases: int) -> dict[str, str]:
    return {
        "county_fips": county_fips,
        "year": str(year),
        "confirmed_cases": str(total_cases),
        "probable_cases": "0",
        "total_cases": str(total_cases),
        "canonical_source_id": f"cdc_{year}",
        "source_values_summary": "",
        "reconciliation_status": "matched",
        "data_quality_flags": "",
    }


def _population_row(
    county_fips: str,
    county_name: str,
    year: int,
) -> dict[str, str]:
    return {
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "population": "100000",
    }


def _mast_row(
    *,
    county_fips: str,
    county_name: str,
    year: int,
    source_report_year: int,
    mast_index: str,
    black_oak: str,
    source_id: str,
) -> dict[str, str]:
    return {
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "region": "Western Maryland",
        "mast_category": "oak_acorn_abundance",
        "mast_index": mast_index,
        "mast_rating": "poor_and_spotty",
        "acorn_index": mast_index,
        "hard_mast_index": mast_index,
        "soft_mast_index": "",
        "plots_observed": "",
        "expected_plots": "",
        "coverage_complete": "",
        "source_id": source_id,
        "source_url_hash": "hash",
        "source_report_year": str(source_report_year),
        "parser_method": "pypdfium_table_text",
        "extraction_confidence": "high",
        "black_oak_acorns_per_branch": black_oak,
        "white_oak_acorns_per_branch": "14.77",
        "unit_average_acorns_per_branch": mast_index,
        "black_oak_mast_rating": "I",
        "white_oak_mast_rating": "III",
        "unit_average_mast_rating": "II",
        "white_oak_subjective_crown_pct": "1.75",
        "black_oak_subjective_crown_pct": "34.00",
        "feature_quality_flags": "western_maryland_only,study_plot_not_countywide",
        "extracted_text_excerpt": "excerpt",
    }


def _model_row(
    *,
    county_fips: str,
    year: int,
    total_cases: int,
) -> ModelCountyYearFeature:
    return ModelCountyYearFeature(
        county_fips=county_fips,
        county_name="County",
        year=year,
        total_cases=total_cases,
        confirmed_cases=total_cases,
        probable_cases=0,
        population=100000,
        lyme_incidence_per_100k=float(total_cases),
        log_population_offset=11.512925,
        lyme_canonical_source_id="cdc",
        lyme_reconciliation_status="matched",
        lyme_data_quality_flags="",
        weather_weeks_observed=1,
        weather_complete_week_count=1,
        weather_days_observed=7,
        weather_expected_days=7,
        weather_observation_ratio=1.0,
        weather_days_above_40f=7,
        weather_days_50_65f=1,
        weather_days_70_85f=0,
        weather_degree_days_above_40f=50.0,
        weather_freeze_thaw_days=1,
        weather_precip_total_mm=4.0,
        weather_snowfall_total_mm=1.0,
        weather_precip_days=2,
        weather_dry_spell_max_days=3,
        weather_temp_mean_f=45.0,
        weather_precip_mean_mm=0.5,
        weather_temp_anomaly_vs_10yr=0.0,
        weather_precip_anomaly_vs_10yr=0.0,
        tick_season_days_above_40f=0,
        tick_season_days_70_85f=0,
        tick_season_precip_total_mm=0.0,
        spring_days_above_40f=0,
        summer_days_70_85f=0,
        weather_feature_quality_flags="",
        residential_units_authorized=None,
        units_authorized_per_sqmi=None,
        units_authorized_per_100k=None,
        contact_pressure_total_value_dollars=None,
        contact_pressure_feature_quality_flags=None,
        deer_total_harvest_prior_season=None,
        deer_harvest_per_sqmi_prior_season=None,
        deer_is_derived_total=None,
        mast_index_prior_year=None,
        acorn_index_prior_year=None,
        hard_mast_index_prior_year=None,
        soft_mast_index_prior_year=None,
        black_oak_acorns_per_branch_prior_year=None,
        white_oak_acorns_per_branch_prior_year=None,
        unit_average_acorns_per_branch_prior_year=None,
        white_oak_subjective_crown_pct_prior_year=None,
        black_oak_subjective_crown_pct_prior_year=None,
        mast_coverage_complete_prior_year=None,
        mast_source_ids_prior_year=None,
        mast_source_report_year_prior_year=None,
        mast_parser_method_prior_year=None,
        mast_extraction_confidence_prior_year=None,
        mast_feature_quality_flags_prior_year=None,
        ixodes_scapularis_status=None,
        ixodes_pacificus_status=None,
        borrelia_burgdorferi_status=None,
        borrelia_miyamotoi_status=None,
        anaplasma_phagocytophilum_status=None,
        babesia_microti_status=None,
        powassan_virus_status=None,
        amblyomma_americanum_status=None,
        tick_status_source_ids=None,
        tick_status_feature_quality_flags=None,
        model_feature_quality_flags="",
    )
