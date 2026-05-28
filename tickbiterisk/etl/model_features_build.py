from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.model_features import ModelCountyYearFeature

MODEL_FEATURE_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "confirmed_cases",
    "probable_cases",
    "population",
    "lyme_incidence_per_100k",
    "log_population_offset",
    "population_prior_year",
    "population_change_prior_year",
    "population_pct_change_prior_year",
    "population_pct_change_trailing_3yr_mean",
    "age_structure_median_age_prior_year",
    "age_structure_under5_share_prior_year",
    "age_structure_age5_17_share_prior_year",
    "age_structure_age18_24_share_prior_year",
    "age_structure_age25_44_share_prior_year",
    "age_structure_age45_64_share_prior_year",
    "age_structure_age65plus_share_prior_year",
    "age_structure_source_id_prior_year",
    "age_structure_census_dataset_prior_year",
    "age_structure_vintage_prior_year",
    "age_structure_source_url_hash_prior_year",
    "age_structure_feature_quality_flags_prior_year",
    "lyme_canonical_source_id",
    "lyme_reconciliation_status",
    "lyme_data_quality_flags",
    "weather_weeks_observed",
    "weather_complete_week_count",
    "weather_days_observed",
    "weather_expected_days",
    "weather_observation_ratio",
    "weather_days_above_40f",
    "weather_days_50_65f",
    "weather_days_70_85f",
    "weather_degree_days_above_40f",
    "weather_freeze_thaw_days",
    "weather_precip_total_mm",
    "weather_snowfall_total_mm",
    "weather_precip_days",
    "weather_dry_spell_max_days",
    "weather_temp_mean_f",
    "weather_precip_mean_mm",
    "weather_temp_anomaly_vs_10yr",
    "weather_precip_anomaly_vs_10yr",
    "tick_season_days_above_40f",
    "tick_season_days_70_85f",
    "tick_season_precip_total_mm",
    "spring_days_above_40f",
    "summer_days_70_85f",
    "weather_feature_quality_flags",
    "residential_units_authorized",
    "units_authorized_per_sqmi",
    "units_authorized_per_100k",
    "units_authorized_per_sqmi_prior_year",
    "units_authorized_per_100k_prior_year",
    "units_authorized_per_sqmi_trailing_3yr_mean",
    "units_authorized_per_100k_trailing_3yr_mean",
    "units_authorized_per_sqmi_yoy_change",
    "contact_pressure_total_value_dollars",
    "contact_pressure_feature_quality_flags",
    "deer_total_harvest_prior_season",
    "deer_harvest_per_sqmi_prior_season",
    "deer_is_derived_total",
    "mast_index_prior_year",
    "acorn_index_prior_year",
    "hard_mast_index_prior_year",
    "soft_mast_index_prior_year",
    "black_oak_acorns_per_branch_prior_year",
    "white_oak_acorns_per_branch_prior_year",
    "unit_average_acorns_per_branch_prior_year",
    "white_oak_subjective_crown_pct_prior_year",
    "black_oak_subjective_crown_pct_prior_year",
    "mast_coverage_complete_prior_year",
    "mast_source_ids_prior_year",
    "mast_source_report_year_prior_year",
    "mast_parser_method_prior_year",
    "mast_extraction_confidence_prior_year",
    "mast_feature_quality_flags_prior_year",
    "ixodes_scapularis_status",
    "ixodes_pacificus_status",
    "borrelia_burgdorferi_status",
    "borrelia_miyamotoi_status",
    "anaplasma_phagocytophilum_status",
    "babesia_microti_status",
    "powassan_virus_status",
    "amblyomma_americanum_status",
    "tick_status_source_ids",
    "tick_status_feature_quality_flags",
    "usdm_week_count",
    "usdm_dsci_mean",
    "usdm_dsci_max",
    "usdm_weeks_d0_or_worse",
    "usdm_weeks_d1_or_worse",
    "usdm_weeks_d2_or_worse",
    "usdm_tick_season_week_count",
    "usdm_tick_season_dsci_mean",
    "usdm_tick_season_weeks_d1_or_worse",
    "usdm_source_ids",
    "usdm_feature_quality_flags",
    "usdm_prior_year_week_count",
    "usdm_prior_year_dsci_mean",
    "usdm_prior_year_dsci_max",
    "usdm_prior_year_weeks_d0_or_worse",
    "usdm_prior_year_weeks_d1_or_worse",
    "usdm_prior_year_weeks_d2_or_worse",
    "usdm_prior_year_tick_season_week_count",
    "usdm_prior_year_tick_season_dsci_mean",
    "usdm_prior_year_tick_season_weeks_d1_or_worse",
    "usdm_prior_year_source_ids",
    "usdm_prior_year_feature_quality_flags",
    "forest_pct",
    "forest_woody_wetland_pct",
    "wetland_pct",
    "emergent_wetland_pct",
    "developed_pct",
    "impervious_pct",
    "agriculture_pct",
    "pasture_hay_pct",
    "cultivated_crop_pct",
    "riparian_natural_45m_pct",
    "riparian_forest_45m_pct",
    "riparian_forest_woody_wetland_45m_pct",
    "natural_land_cover_index",
    "enviroatlas_source_url_hash",
    "enviroatlas_feature_quality_flags",
    "oni_prior_year_season_count",
    "oni_prior_year_mean_anomaly_c",
    "oni_prior_year_max_anomaly_c",
    "oni_prior_year_min_anomaly_c",
    "oni_prior_year_el_nino_season_count",
    "oni_prior_year_la_nina_season_count",
    "enso_source_ids",
    "enso_source_url_hashes",
    "enso_feature_quality_flags",
    "mei_v2_prior_year_month_count",
    "mei_v2_prior_year_mean",
    "mei_v2_prior_year_max",
    "mei_v2_prior_year_min",
    "mei_v2_prior_year_positive_month_count",
    "mei_v2_prior_year_negative_month_count",
    "mei_v2_source_ids",
    "mei_v2_source_url_hashes",
    "mei_v2_feature_quality_flags",
    "model_feature_quality_flags",
]


def write_model_feature_matrix_output(
    rows: list[ModelCountyYearFeature],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "model_features_county_year.csv"
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record): record for record in records}
    ordered = sorted(
        keyed.values(),
        key=lambda record: (record["county_fips"], int(record["year"])),
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MODEL_FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: ModelCountyYearFeature) -> dict[str, object]:
    record = asdict(row)
    record["county_fips"] = str(record["county_fips"]).zfill(5)
    return record


def _read_existing_records(output_path: Path) -> list[dict[str, str]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                **record,
                "county_fips": str(record["county_fips"]).zfill(5),
            }
            for record in reader
        ]


def _record_key(record: dict[str, object]) -> tuple[str, int]:
    return (str(record["county_fips"]).zfill(5), int(record["year"]))
