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
    "contact_pressure_total_value_dollars",
    "contact_pressure_feature_quality_flags",
    "deer_total_harvest_prior_season",
    "deer_harvest_per_sqmi_prior_season",
    "deer_is_derived_total",
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
