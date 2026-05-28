import csv
import json
from pathlib import Path

from tickbiterisk.modeling import design_matrix
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
    assert row["feature_population_pct_change_prior_year"] == "0.0"
    assert row["feature_missing_population_pct_change_prior_year"] == "1"
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
    assert mast_row["feature_population_prior_year"] == "99000.0"
    assert mast_row["feature_population_change_prior_year"] == "1200.0"
    assert mast_row["feature_population_pct_change_prior_year"] == "1.23"
    assert mast_row["feature_population_pct_change_trailing_3yr_mean"] == "0.9"
    assert mast_row["feature_oni_prior_year_mean_anomaly_c"] == "-0.42"
    assert mast_row["feature_oni_prior_year_la_nina_season_count"] == "5.0"
    assert mast_row["feature_missing_usdm_dsci_mean"] == "0"
    assert mast_row["feature_missing_forest_pct"] == "0"
    assert mast_row["feature_missing_units_authorized_per_sqmi_prior_year"] == "0"
    assert mast_row["feature_missing_oni_prior_year_mean_anomaly_c"] == "0"
    assert "feature_usdm_dsci_mean" in result.schema.feature_columns
    assert "feature_usdm_prior_year_dsci_mean" in result.schema.feature_columns
    assert "feature_forest_pct" in result.schema.feature_columns
    assert "feature_oni_prior_year_mean_anomaly_c" in result.schema.feature_columns
    assert (
        "feature_units_authorized_per_sqmi_prior_year"
        in result.schema.feature_columns
    )
    assert "feature_population_pct_change_prior_year" in result.schema.feature_columns
    assert (
        "feature_missing_population_pct_change_prior_year"
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
    assert missing_new_row["feature_oni_prior_year_mean_anomaly_c"] == "0.0"
    assert missing_new_row["feature_missing_oni_prior_year_mean_anomaly_c"] == "1"


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


def test_build_model_design_matrix_adds_prior_year_neighbor_incidence_features(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = build_model_design_matrix(
        model_features_path=feature_matrix,
        lookback_years=2,
        county_adjacency_path=adjacency,
    )

    anne_2020 = next(
        row
        for row in result.rows
        if row["county_fips"] == "24003" and row["year"] == "2020"
    )
    assert anne_2020["feature_neighbor_prior_year_lyme_incidence_mean"] == "40.0"
    assert anne_2020["feature_neighbor_prior_year_lyme_incidence_max"] == "40.0"
    assert anne_2020["feature_neighbor_prior_year_count"] == "1"
    assert anne_2020["feature_missing_neighbor_prior_year_lyme_incidence"] == "0"
    assert "feature_neighbor_prior_year_lyme_incidence_mean" in (
        result.schema.feature_columns
    )
    assert result.schema.spatial_neighbor_source_path == str(adjacency)
    assert len(result.schema.spatial_neighbor_source_sha256 or "") == 64
    assert "spatial_neighbor" in result.schema.missing_value_strategy

    baltimore_2019 = next(
        row
        for row in result.rows
        if row["county_fips"] == "24005" and row["year"] == "2019"
    )
    assert baltimore_2019["feature_neighbor_prior_year_lyme_incidence_mean"] == "10.0"
    assert baltimore_2019["feature_neighbor_prior_year_count"] == "1"


def test_build_model_design_matrix_flags_empty_adjacency_as_missing(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")
    adjacency = _write_empty_adjacency(tmp_path / "empty_adjacency.csv")

    result = build_model_design_matrix(
        model_features_path=feature_matrix,
        lookback_years=2,
        county_adjacency_path=adjacency,
    )

    row = next(
        item
        for item in result.rows
        if item["county_fips"] == "24003" and item["year"] == "2020"
    )
    assert row["feature_neighbor_prior_year_lyme_incidence_mean"] == "0.0"
    assert row["feature_neighbor_prior_year_count"] == "0"
    assert row["feature_missing_neighbor_prior_year_lyme_incidence"] == "1"


def test_build_model_design_matrix_adds_forecast_safe_regional_signal_features(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")
    regional_signals = _write_regional_signals(tmp_path / "regional_signals.csv")

    result = build_model_design_matrix(
        model_features_path=feature_matrix,
        lookback_years=2,
        regional_signals_path=regional_signals,
    )

    anne_2020 = next(
        row
        for row in result.rows
        if row["county_fips"] == "24003" and row["year"] == "2020"
    )
    assert anne_2020["feature_regional_prior_year_total_cases"] == "20.0"
    assert (
        anne_2020["feature_regional_prior_year_county_share_of_midatlantic_cases"]
        == "0.25"
    )
    assert anne_2020["feature_regional_prior_year_midatlantic_total_cases"] == "80.0"
    assert (
        anne_2020["feature_regional_trailing_5yr_midatlantic_total_mean"]
        == "75.0"
    )
    assert anne_2020["feature_missing_regional_prior_year_total_cases"] == "0"
    assert (
        anne_2020["feature_missing_regional_trailing_5yr_midatlantic_total_mean"]
        == "0"
    )
    assert "regional_signal_candidate" in anne_2020["model_feature_quality_flags"]
    assert anne_2020["feature_flag_regional_signal_candidate"] == "1"
    assert "feature_regional_prior_year_midatlantic_total_cases" in (
        result.schema.feature_columns
    )
    assert "feature_missing_regional_prior_year_total_cases" in (
        result.schema.feature_columns
    )
    assert "diagnostic_midatlantic_total_cases" not in result.schema.feature_columns
    assert result.schema.regional_signal_source_path == str(regional_signals)
    assert len(result.schema.regional_signal_source_sha256 or "") == 64
    assert "regional_signal" in result.schema.missing_value_strategy


def test_read_regional_signals_discards_same_year_diagnostic_fields(
    tmp_path: Path,
) -> None:
    regional_signals = _write_regional_signals(tmp_path / "regional_signals.csv")

    rows = design_matrix._read_regional_signals(regional_signals)

    row = rows[("24003", 2020)]
    assert "diagnostic_midatlantic_total_cases" not in row
    assert "diagnostic_county_share_of_midatlantic_cases" not in row
    assert set(row) == {
        "county_fips",
        "year",
        "feature_quality_flags",
        *design_matrix.REGIONAL_SIGNAL_SOURCE_COLUMNS,
    }


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
                    "population_prior_year": "99000" if has_new_features else "",
                    "population_change_prior_year": "1200" if has_new_features else "",
                    "population_pct_change_prior_year": (
                        "1.23" if has_new_features else ""
                    ),
                    "population_pct_change_trailing_3yr_mean": (
                        "0.9" if has_new_features else ""
                    ),
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
                    "oni_prior_year_season_count": (
                        "12" if has_new_features else ""
                    ),
                    "oni_prior_year_mean_anomaly_c": (
                        "-0.42" if has_new_features else ""
                    ),
                    "oni_prior_year_max_anomaly_c": (
                        "0.1" if has_new_features else ""
                    ),
                    "oni_prior_year_min_anomaly_c": (
                        "-1.2" if has_new_features else ""
                    ),
                    "oni_prior_year_el_nino_season_count": (
                        "0" if has_new_features else ""
                    ),
                    "oni_prior_year_la_nina_season_count": (
                        "5" if has_new_features else ""
                    ),
                    "enso_source_ids": "noaa_cpc_oni" if has_new_features else "",
                    "enso_source_url_hashes": "hash" if has_new_features else "",
                    "enso_feature_quality_flags": (
                        "global_climate_index,not_maryland_specific,prior_year_signal"
                        if has_new_features
                        else ""
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


def _write_adjacency(path: Path) -> Path:
    rows = [
        {
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "neighbor_county_fips": "24005",
            "neighbor_county_name": "Baltimore County",
            "shared_boundary_segment_count": "1",
            "adjacency_method": "fixture",
            "feature_quality_flags": "county_adjacency_from_fixture",
        },
        {
            "county_fips": "24005",
            "county_name": "Baltimore County",
            "neighbor_county_fips": "24003",
            "neighbor_county_name": "Anne Arundel County",
            "shared_boundary_segment_count": "1",
            "adjacency_method": "fixture",
            "feature_quality_flags": "county_adjacency_from_fixture",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_empty_adjacency(path: Path) -> Path:
    rows = [
        {
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "neighbor_county_fips": "24003",
            "neighbor_county_name": "Anne Arundel County",
            "shared_boundary_segment_count": "0",
            "adjacency_method": "fixture",
            "feature_quality_flags": "self_row_ignored",
        }
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_regional_signals(path: Path) -> Path:
    rows = []
    for county_fips, county_name, prior_cases in [
        ("24003", "Anne Arundel County", "20"),
        ("24005", "Baltimore County", "40"),
    ]:
        for year in [2019, 2020]:
            rows.append(
                {
                    "state_fips": "24",
                    "state_abbr": "MD",
                    "state_name": "Maryland",
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": prior_cases,
                    "diagnostic_state_total_cases": "60",
                    "diagnostic_midatlantic_total_cases": "100",
                    "diagnostic_county_share_of_state_cases": "0.25",
                    "diagnostic_county_share_of_midatlantic_cases": "0.2",
                    "feature_prior_year_total_cases": prior_cases,
                    "feature_prior_year_county_share_of_state_cases": "0.333333",
                    "feature_prior_year_county_share_of_midatlantic_cases": "0.25",
                    "feature_prior_year_state_total_cases": "60",
                    "feature_prior_year_midatlantic_total_cases": "80",
                    "feature_trailing_5yr_midatlantic_total_min": "70",
                    "feature_trailing_5yr_midatlantic_total_mean": "75",
                    "feature_trailing_5yr_midatlantic_total_max": "80",
                    "diagnostic_midatlantic_total_within_trailing_5yr_band": "False",
                    "source_panel_sha256": "abc123",
                    "feature_quality_flags": (
                        "regional_signal_candidate,"
                        "same_year_diagnostics_not_forecast_features"
                    ),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
