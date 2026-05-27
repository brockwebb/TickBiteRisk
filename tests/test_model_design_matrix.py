import csv
import json
from pathlib import Path

from tickbiterisk.modeling.design_matrix import build_model_design_matrix
from tickbiterisk.modeling.design_matrix_build import (
    write_model_design_matrix_outputs,
)


def test_build_model_design_matrix_writes_numeric_features_and_missing_indicators(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")

    result = build_model_design_matrix(
        model_features_path=feature_matrix,
        lookback_years=2,
    )

    assert len(result.rows) == 4
    row = next(
        item
        for item in result.rows
        if item["county_fips"] == "24003" and item["year"] == "2020"
    )
    assert row["target_total_cases"] == "30"
    assert row["target_lyme_incidence_per_100k"] == "30.0"
    assert row["feature_prior_year_lyme_incidence_per_100k"] == "20.0"
    assert row["feature_trailing_2yr_mean_lyme_incidence_per_100k"] == "15.0"
    assert row["feature_trailing_history_years"] == "2"
    assert row["feature_missing_prior_year_lyme_incidence"] == "0"
    assert row["feature_weather_temp_mean_f"] == "52.0"
    assert row["feature_missing_deer_harvest_prior_season"] == "1"
    assert row["feature_deer_harvest_per_sqmi_prior_season"] == "0.0"
    assert row["feature_missing_mast_index_prior_year"] == "1"
    assert row["feature_mast_index_prior_year"] == "0.0"
    assert row["feature_tick_ixodes_scapularis_established"] == "1"
    assert row["feature_tick_borrelia_burgdorferi_present"] == "1"
    assert row["feature_flag_missing_deer_harvest_prior_season"] == "1"
    assert row["feature_flag_current_status_retrospective_proxy"] == "1"
    assert row["feature_flag_no_records_not_absence"] == "1"
    assert row["model_feature_quality_flags"] == (
        "missing_deer_harvest_prior_season,"
        "current_status_retrospective_proxy,no_records_not_absence"
    )
    assert set(result.schema.id_columns) == {"county_fips", "county_name", "year"}
    assert result.schema.target_columns == [
        "target_total_cases",
        "target_lyme_incidence_per_100k",
        "target_population",
    ]
    assert "feature_weather_temp_mean_f" in result.schema.feature_columns
    assert "feature_mast_index_prior_year" in result.schema.feature_columns
    assert "feature_missing_mast_index_prior_year" in result.schema.feature_columns
    assert "feature_tick_ixodes_scapularis_established" in result.schema.feature_columns
    assert "feature_flag_missing_deer_harvest_prior_season" in result.schema.feature_columns
    assert result.schema.missing_value_strategy["numeric"] == (
        "empty optional numeric source values are imputed to 0.0 with paired "
        "feature_missing_* indicators"
    )
    assert len(result.schema.input_sha256) == 64

    mast_row = next(
        item
        for item in result.rows
        if item["county_fips"] == "24005" and item["year"] == "2020"
    )
    assert mast_row["feature_mast_index_prior_year"] == "11.91"
    assert mast_row["feature_acorn_index_prior_year"] == "11.91"
    assert mast_row["feature_black_oak_acorns_per_branch_prior_year"] == "17.02"
    assert mast_row["feature_white_oak_subjective_crown_pct_prior_year"] == "22.87"
    assert mast_row["feature_missing_mast_index_prior_year"] == "0"
    assert mast_row["feature_usdm_dsci_mean"] == "85.5"
    assert mast_row["feature_usdm_tick_season_dsci_mean"] == "92.25"
    assert mast_row["feature_usdm_prior_year_dsci_mean"] == "41.5"
    assert mast_row["feature_usdm_prior_year_tick_season_dsci_mean"] == "44.25"
    assert mast_row["feature_forest_pct"] == "36.1"
    assert mast_row["feature_impervious_pct"] == "9.7"
    assert mast_row["feature_units_authorized_per_sqmi_prior_year"] == "1.5"
    assert mast_row["feature_units_authorized_per_100k_trailing_3yr_mean"] == "30.0"
    assert mast_row["feature_missing_usdm_dsci_mean"] == "0"
    assert mast_row["feature_missing_forest_pct"] == "0"
    assert mast_row["feature_missing_units_authorized_per_sqmi_prior_year"] == "0"
    assert "feature_usdm_dsci_mean" in result.schema.feature_columns
    assert "feature_usdm_prior_year_dsci_mean" in result.schema.feature_columns
    assert "feature_forest_pct" in result.schema.feature_columns
    assert (
        "feature_units_authorized_per_sqmi_prior_year"
        in result.schema.feature_columns
    )

    missing_new_row = next(
        item
        for item in result.rows
        if item["county_fips"] == "24003" and item["year"] == "2020"
    )
    assert missing_new_row["feature_usdm_dsci_mean"] == "0.0"
    assert missing_new_row["feature_missing_usdm_dsci_mean"] == "1"
    assert missing_new_row["feature_usdm_prior_year_dsci_mean"] == "0.0"
    assert missing_new_row["feature_missing_usdm_prior_year_dsci_mean"] == "1"
    assert missing_new_row["feature_forest_pct"] == "0.0"
    assert missing_new_row["feature_missing_forest_pct"] == "1"


def test_write_model_design_matrix_outputs_writes_csv_and_schema_json(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")
    result = build_model_design_matrix(
        model_features_path=feature_matrix,
        lookback_years=2,
    )

    outputs = write_model_design_matrix_outputs(result, tmp_path / "out")

    assert outputs.matrix_path.name == "model_design_matrix_county_year.csv"
    assert outputs.schema_path.name == "model_design_matrix_schema.json"
    with outputs.matrix_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert rows[0]["county_fips"] == "24003"
    assert all(
        rows[0][column] != ""
        for column in result.schema.feature_columns
    )

    schema = json.loads(outputs.schema_path.read_text(encoding="utf-8"))
    assert schema["row_count"] == 4
    assert schema["lookback_years"] == 2
    assert schema["source_path"] == str(feature_matrix)
    assert schema["feature_columns"] == result.schema.feature_columns


def _write_feature_matrix(path: Path) -> Path:
    rows = []
    for county_fips, county_name, yearly_cases in [
        ("24003", "Anne Arundel County", [10, 20, 30]),
        ("24005", "Baltimore County", [50, 40, 35]),
    ]:
        for offset, cases in enumerate(yearly_cases):
            year = 2018 + offset
            has_deer = county_fips == "24005" and year == 2020
            has_mast = county_fips == "24005" and year == 2020
            has_new_features = county_fips == "24005" and year == 2020
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(cases),
                    "confirmed_cases": str(cases - 1),
                    "probable_cases": "1",
                    "population": "100000",
                    "lyme_incidence_per_100k": str(float(cases)),
                    "log_population_offset": "11.512925",
                    "lyme_canonical_source_id": "cdc_lyme_public_2008_2021",
                    "lyme_reconciliation_status": "matched",
                    "lyme_data_quality_flags": "",
                    "weather_weeks_observed": "52",
                    "weather_complete_week_count": "52",
                    "weather_days_observed": "365",
                    "weather_expected_days": "365",
                    "weather_observation_ratio": "1.0",
                    "weather_days_above_40f": str(250 + offset),
                    "weather_days_50_65f": str(90 + offset),
                    "weather_days_70_85f": str(60 + offset),
                    "weather_degree_days_above_40f": str(2500 + offset),
                    "weather_freeze_thaw_days": str(25 - offset),
                    "weather_precip_total_mm": str(1000 + offset),
                    "weather_snowfall_total_mm": str(100 - offset),
                    "weather_precip_days": str(95 + offset),
                    "weather_dry_spell_max_days": str(14 + offset),
                    "weather_temp_mean_f": str(50 + offset),
                    "weather_precip_mean_mm": str(2.7 + offset),
                    "weather_temp_anomaly_vs_10yr": str(0.1 * offset),
                    "weather_precip_anomaly_vs_10yr": str(-0.2 * offset),
                    "tick_season_days_above_40f": str(180 + offset),
                    "tick_season_days_70_85f": str(55 + offset),
                    "tick_season_precip_total_mm": str(600 + offset),
                    "spring_days_above_40f": str(70 + offset),
                    "summer_days_70_85f": str(50 + offset),
                    "weather_feature_quality_flags": "",
                    "residential_units_authorized": str(100 + offset),
                    "units_authorized_per_sqmi": str(1.5 + offset),
                    "units_authorized_per_100k": str(30 + offset),
                    "units_authorized_per_sqmi_prior_year": (
                        "1.5" if has_new_features else ""
                    ),
                    "units_authorized_per_100k_prior_year": (
                        "30.0" if has_new_features else ""
                    ),
                    "units_authorized_per_sqmi_trailing_3yr_mean": (
                        "1.25" if has_new_features else ""
                    ),
                    "units_authorized_per_100k_trailing_3yr_mean": (
                        "30.0" if has_new_features else ""
                    ),
                    "units_authorized_per_sqmi_yoy_change": (
                        "0.25" if has_new_features else ""
                    ),
                    "contact_pressure_total_value_dollars": str(1000000 + offset),
                    "contact_pressure_feature_quality_flags": "construction_proxy_only",
                    "deer_total_harvest_prior_season": "1200" if has_deer else "",
                    "deer_harvest_per_sqmi_prior_season": "3.5" if has_deer else "",
                    "deer_is_derived_total": "False" if has_deer else "",
                    "mast_index_prior_year": "11.91" if has_mast else "",
                    "acorn_index_prior_year": "11.91" if has_mast else "",
                    "hard_mast_index_prior_year": "11.91" if has_mast else "",
                    "soft_mast_index_prior_year": "",
                    "black_oak_acorns_per_branch_prior_year": (
                        "17.02" if has_mast else ""
                    ),
                    "white_oak_acorns_per_branch_prior_year": (
                        "6.80" if has_mast else ""
                    ),
                    "unit_average_acorns_per_branch_prior_year": (
                        "11.91" if has_mast else ""
                    ),
                    "white_oak_subjective_crown_pct_prior_year": (
                        "22.87" if has_mast else ""
                    ),
                    "black_oak_subjective_crown_pct_prior_year": (
                        "34.87" if has_mast else ""
                    ),
                    "mast_coverage_complete_prior_year": "",
                    "mast_source_ids_prior_year": (
                        "maryland_dnr_wmd_mast_survey_2021" if has_mast else ""
                    ),
                    "mast_source_report_year_prior_year": "2021" if has_mast else "",
                    "mast_parser_method_prior_year": (
                        "pypdfium_table_text" if has_mast else ""
                    ),
                    "mast_extraction_confidence_prior_year": "high" if has_mast else "",
                    "mast_feature_quality_flags_prior_year": (
                        "western_maryland_only,study_plot_not_countywide"
                        if has_mast
                        else ""
                    ),
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
                        "current_status_retrospective_proxy,no_records_not_absence"
                    ),
                    "usdm_week_count": "52" if has_new_features else "",
                    "usdm_dsci_mean": "85.5" if has_new_features else "",
                    "usdm_dsci_max": "250" if has_new_features else "",
                    "usdm_weeks_d0_or_worse": "20" if has_new_features else "",
                    "usdm_weeks_d1_or_worse": "8" if has_new_features else "",
                    "usdm_weeks_d2_or_worse": "2" if has_new_features else "",
                    "usdm_tick_season_week_count": (
                        "26" if has_new_features else ""
                    ),
                    "usdm_tick_season_dsci_mean": (
                        "92.25" if has_new_features else ""
                    ),
                    "usdm_tick_season_weeks_d1_or_worse": (
                        "5" if has_new_features else ""
                    ),
                    "usdm_source_ids": (
                        "usdm_county_statistics" if has_new_features else ""
                    ),
                    "usdm_feature_quality_flags": (
                        "drought_monitor_retro_observed"
                        if has_new_features
                        else ""
                    ),
                    "usdm_prior_year_week_count": (
                        "52" if has_new_features else ""
                    ),
                    "usdm_prior_year_dsci_mean": (
                        "41.5" if has_new_features else ""
                    ),
                    "usdm_prior_year_dsci_max": "120" if has_new_features else "",
                    "usdm_prior_year_weeks_d0_or_worse": (
                        "10" if has_new_features else ""
                    ),
                    "usdm_prior_year_weeks_d1_or_worse": (
                        "3" if has_new_features else ""
                    ),
                    "usdm_prior_year_weeks_d2_or_worse": (
                        "1" if has_new_features else ""
                    ),
                    "usdm_prior_year_tick_season_week_count": (
                        "26" if has_new_features else ""
                    ),
                    "usdm_prior_year_tick_season_dsci_mean": (
                        "44.25" if has_new_features else ""
                    ),
                    "usdm_prior_year_tick_season_weeks_d1_or_worse": (
                        "2" if has_new_features else ""
                    ),
                    "usdm_prior_year_source_ids": (
                        "usdm_county_statistics" if has_new_features else ""
                    ),
                    "usdm_prior_year_feature_quality_flags": (
                        "drought_monitor_retro_observed"
                        if has_new_features
                        else ""
                    ),
                    "forest_pct": "36.1" if has_new_features else "",
                    "forest_woody_wetland_pct": "37.9" if has_new_features else "",
                    "wetland_pct": "2.6" if has_new_features else "",
                    "emergent_wetland_pct": "0.8" if has_new_features else "",
                    "developed_pct": "35.6" if has_new_features else "",
                    "impervious_pct": "9.7" if has_new_features else "",
                    "agriculture_pct": "23.2" if has_new_features else "",
                    "pasture_hay_pct": "10.8" if has_new_features else "",
                    "cultivated_crop_pct": "12.4" if has_new_features else "",
                    "riparian_natural_45m_pct": "66.4" if has_new_features else "",
                    "riparian_forest_45m_pct": "53.2" if has_new_features else "",
                    "riparian_forest_woody_wetland_45m_pct": (
                        "61.6" if has_new_features else ""
                    ),
                    "natural_land_cover_index": "41.1" if has_new_features else "",
                    "enviroatlas_source_url_hash": (
                        "hash" if has_new_features else ""
                    ),
                    "enviroatlas_feature_quality_flags": (
                        "static_enviroatlas_2011" if has_new_features else ""
                    ),
                    "model_feature_quality_flags": (
                        "current_status_retrospective_proxy,no_records_not_absence"
                        if has_deer
                        else "missing_deer_harvest_prior_season,"
                        "current_status_retrospective_proxy,no_records_not_absence"
                    ),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
