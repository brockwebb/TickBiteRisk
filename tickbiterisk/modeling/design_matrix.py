from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ID_COLUMNS = ["county_fips", "county_name", "year"]
TARGET_COLUMNS = [
    "target_total_cases",
    "target_lyme_incidence_per_100k",
    "target_population",
]
PASSTHROUGH_COLUMNS = ["model_feature_quality_flags"]
STATUS_COLUMNS = [
    "ixodes_scapularis_status",
    "ixodes_pacificus_status",
    "borrelia_burgdorferi_status",
    "borrelia_miyamotoi_status",
    "anaplasma_phagocytophilum_status",
    "babesia_microti_status",
    "powassan_virus_status",
    "amblyomma_americanum_status",
]
NUMERIC_SOURCE_COLUMNS = [
    "log_population_offset",
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
    "residential_units_authorized",
    "units_authorized_per_sqmi",
    "units_authorized_per_100k",
    "units_authorized_per_sqmi_prior_year",
    "units_authorized_per_100k_prior_year",
    "units_authorized_per_sqmi_trailing_3yr_mean",
    "units_authorized_per_100k_trailing_3yr_mean",
    "units_authorized_per_sqmi_yoy_change",
    "contact_pressure_total_value_dollars",
    "deer_total_harvest_prior_season",
    "deer_harvest_per_sqmi_prior_season",
    "mast_index_prior_year",
    "acorn_index_prior_year",
    "hard_mast_index_prior_year",
    "soft_mast_index_prior_year",
    "black_oak_acorns_per_branch_prior_year",
    "white_oak_acorns_per_branch_prior_year",
    "unit_average_acorns_per_branch_prior_year",
    "white_oak_subjective_crown_pct_prior_year",
    "black_oak_subjective_crown_pct_prior_year",
    "usdm_dsci_mean",
    "usdm_dsci_max",
    "usdm_weeks_d0_or_worse",
    "usdm_weeks_d1_or_worse",
    "usdm_weeks_d2_or_worse",
    "usdm_tick_season_dsci_mean",
    "usdm_tick_season_weeks_d1_or_worse",
    "usdm_prior_year_dsci_mean",
    "usdm_prior_year_dsci_max",
    "usdm_prior_year_weeks_d0_or_worse",
    "usdm_prior_year_weeks_d1_or_worse",
    "usdm_prior_year_weeks_d2_or_worse",
    "usdm_prior_year_tick_season_dsci_mean",
    "usdm_prior_year_tick_season_weeks_d1_or_worse",
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
]
OPTIONAL_NUMERIC_COLUMNS = [
    "residential_units_authorized",
    "units_authorized_per_sqmi",
    "units_authorized_per_100k",
    "units_authorized_per_sqmi_prior_year",
    "units_authorized_per_100k_prior_year",
    "units_authorized_per_sqmi_trailing_3yr_mean",
    "units_authorized_per_100k_trailing_3yr_mean",
    "units_authorized_per_sqmi_yoy_change",
    "contact_pressure_total_value_dollars",
    "deer_total_harvest_prior_season",
    "deer_harvest_per_sqmi_prior_season",
    "mast_index_prior_year",
    "acorn_index_prior_year",
    "hard_mast_index_prior_year",
    "soft_mast_index_prior_year",
    "black_oak_acorns_per_branch_prior_year",
    "white_oak_acorns_per_branch_prior_year",
    "unit_average_acorns_per_branch_prior_year",
    "white_oak_subjective_crown_pct_prior_year",
    "black_oak_subjective_crown_pct_prior_year",
    "usdm_dsci_mean",
    "usdm_dsci_max",
    "usdm_weeks_d0_or_worse",
    "usdm_weeks_d1_or_worse",
    "usdm_weeks_d2_or_worse",
    "usdm_tick_season_dsci_mean",
    "usdm_tick_season_weeks_d1_or_worse",
    "usdm_prior_year_dsci_mean",
    "usdm_prior_year_dsci_max",
    "usdm_prior_year_weeks_d0_or_worse",
    "usdm_prior_year_weeks_d1_or_worse",
    "usdm_prior_year_weeks_d2_or_worse",
    "usdm_prior_year_tick_season_dsci_mean",
    "usdm_prior_year_tick_season_weeks_d1_or_worse",
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
]
REQUIRED_MODEL_FEATURE_COLUMNS = [
    "county_fips",
    "year",
    "total_cases",
    "population",
    "lyme_incidence_per_100k",
]


class ModelDesignMatrixInputError(ValueError):
    """Raised when model design matrix inputs or options are invalid."""


@dataclass(frozen=True)
class ModelDesignMatrixSchema:
    source_path: str
    input_sha256: str
    row_count: int
    lookback_years: int
    id_columns: list[str]
    target_columns: list[str]
    feature_columns: list[str]
    passthrough_columns: list[str]
    categorical_mappings: dict[str, list[str]]
    missing_value_strategy: dict[str, str]


@dataclass(frozen=True)
class ModelDesignMatrixResult:
    rows: list[dict[str, str]]
    schema: ModelDesignMatrixSchema


def build_model_design_matrix(
    *,
    model_features_path: Path,
    lookback_years: int = 5,
) -> ModelDesignMatrixResult:
    if lookback_years < 1:
        raise ModelDesignMatrixInputError("lookback_years must be at least 1")

    source_rows = _read_rows(model_features_path)
    rows_by_county = _rows_by_county(source_rows)
    rows_by_year = _rows_by_year(source_rows)
    categorical_mappings = _categorical_mappings(source_rows)
    quality_flags = _quality_flags(source_rows)
    feature_columns = _feature_columns(
        lookback_years=lookback_years,
        categorical_mappings=categorical_mappings,
        quality_flags=quality_flags,
    )

    output_rows = []
    for row in sorted(source_rows, key=lambda item: (item["county_fips"], int(item["year"]))):
        county_fips = row["county_fips"]
        year = int(row["year"])
        history = [
            prior
            for prior in rows_by_county[county_fips]
            if int(prior["year"]) < year
        ][-lookback_years:]
        if not history:
            continue
        output_rows.append(
            _design_row(
                row=row,
                history=history,
                rows_by_year=rows_by_year,
                lookback_years=lookback_years,
                categorical_mappings=categorical_mappings,
                quality_flags=quality_flags,
                feature_columns=feature_columns,
            )
        )

    schema = ModelDesignMatrixSchema(
        source_path=str(model_features_path),
        input_sha256=_sha256_file(model_features_path),
        row_count=len(output_rows),
        lookback_years=lookback_years,
        id_columns=ID_COLUMNS,
        target_columns=TARGET_COLUMNS,
        feature_columns=feature_columns,
        passthrough_columns=PASSTHROUGH_COLUMNS,
        categorical_mappings=categorical_mappings,
        missing_value_strategy={
            "numeric": (
                "empty optional numeric source values are imputed to 0.0 with paired "
                "feature_missing_* indicators"
            ),
            "categorical": "observed status values are one-hot encoded; empty statuses produce all-zero indicators",
            "lagged_outcome": "rows with no prior county history are excluded; missing exact prior-year incidence is imputed to 0.0 with feature_missing_prior_year_lyme_incidence",
        },
    )
    return ModelDesignMatrixResult(rows=output_rows, schema=schema)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = [
            column
            for column in REQUIRED_MODEL_FEATURE_COLUMNS
            if column not in fieldnames
        ]
        if missing_columns:
            raise ModelDesignMatrixInputError(
                "missing required model feature column(s): "
                f"{', '.join(missing_columns)}"
            )
        return [
            {
                **row,
                "county_fips": str(row["county_fips"]).zfill(5),
            }
            for row in reader
        ]


def _rows_by_county(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["county_fips"], []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: int(row["year"]))
        for county_fips, county_rows in grouped.items()
    }


def _rows_by_year(rows: list[dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(int(row["year"]), []).append(row)
    return grouped


def _categorical_mappings(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    mappings: dict[str, list[str]] = {}
    for column in STATUS_COLUMNS:
        values = sorted(
            {
                value
                for row in rows
                if (value := str(row.get(column, "")).strip())
            }
        )
        if values:
            mappings[column] = values
    return mappings


def _quality_flags(rows: list[dict[str, str]]) -> list[str]:
    return sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.get("model_feature_quality_flags", ""))
        }
    )


def _feature_columns(
    *,
    lookback_years: int,
    categorical_mappings: dict[str, list[str]],
    quality_flags: list[str],
) -> list[str]:
    columns = [
        "feature_year",
        "feature_prior_year_lyme_incidence_per_100k",
        f"feature_trailing_{lookback_years}yr_mean_lyme_incidence_per_100k",
        "feature_trailing_history_years",
        "feature_missing_prior_year_lyme_incidence",
        "feature_state_prior_year_lyme_incidence_per_100k",
        "feature_missing_state_prior_year_lyme_incidence",
    ]
    columns.extend(f"feature_{column}" for column in NUMERIC_SOURCE_COLUMNS)
    columns.extend(
        [
            "feature_missing_contact_pressure",
            "feature_missing_deer_harvest_prior_season",
        ]
    )
    columns.extend(f"feature_missing_{column}" for column in OPTIONAL_NUMERIC_COLUMNS)
    columns.append("feature_deer_is_derived_total")
    columns.append("feature_missing_deer_is_derived_total")
    for source_column, values in categorical_mappings.items():
        base = _status_feature_base(source_column)
        columns.extend(f"{base}_{_slug(value)}" for value in values)
    columns.extend(f"feature_flag_{_slug(flag)}" for flag in quality_flags)
    return columns


def _design_row(
    *,
    row: dict[str, str],
    history: list[dict[str, str]],
    rows_by_year: dict[int, list[dict[str, str]]],
    lookback_years: int,
    categorical_mappings: dict[str, list[str]],
    quality_flags: list[str],
    feature_columns: list[str],
) -> dict[str, str]:
    year = int(row["year"])
    prior_year_row = next(
        (prior for prior in history if int(prior["year"]) == year - 1),
        None,
    )
    state_prior_incidence = _state_incidence(rows_by_year.get(year - 1, []))
    record = {
        "county_fips": row["county_fips"],
        "county_name": row.get("county_name", ""),
        "year": str(year),
        "target_total_cases": _format_int(row.get("total_cases", "")),
        "target_lyme_incidence_per_100k": _format_float(
            row.get("lyme_incidence_per_100k", "")
        ),
        "target_population": _format_int(row.get("population", "")),
        "model_feature_quality_flags": row.get("model_feature_quality_flags", ""),
    }
    feature_values = {
        "feature_year": str(year),
        "feature_prior_year_lyme_incidence_per_100k": _format_float(
            "" if prior_year_row is None else prior_year_row.get("lyme_incidence_per_100k", "")
        ),
        f"feature_trailing_{lookback_years}yr_mean_lyme_incidence_per_100k": _format_number(
            mean(_parse_float(prior["lyme_incidence_per_100k"]) for prior in history)
        ),
        "feature_trailing_history_years": str(len(history)),
        "feature_missing_prior_year_lyme_incidence": "1" if prior_year_row is None else "0",
        "feature_state_prior_year_lyme_incidence_per_100k": _format_number(
            state_prior_incidence
        ),
        "feature_missing_state_prior_year_lyme_incidence": (
            "1" if state_prior_incidence is None else "0"
        ),
    }
    for column in NUMERIC_SOURCE_COLUMNS:
        feature_values[f"feature_{column}"] = _format_float(row.get(column, ""))
    for column in OPTIONAL_NUMERIC_COLUMNS:
        feature_values[f"feature_missing_{column}"] = (
            "1" if _is_blank(row.get(column, "")) else "0"
        )
    feature_values["feature_missing_contact_pressure"] = (
        "1" if _is_blank(row.get("residential_units_authorized", "")) else "0"
    )
    feature_values["feature_missing_deer_harvest_prior_season"] = (
        "1" if _is_blank(row.get("deer_harvest_per_sqmi_prior_season", "")) else "0"
    )
    deer_derived = _parse_bool_or_none(row.get("deer_is_derived_total", ""))
    feature_values["feature_deer_is_derived_total"] = "1" if deer_derived else "0"
    feature_values["feature_missing_deer_is_derived_total"] = (
        "1" if deer_derived is None else "0"
    )
    for source_column, values in categorical_mappings.items():
        observed = str(row.get(source_column, "")).strip()
        base = _status_feature_base(source_column)
        for value in values:
            feature_values[f"{base}_{_slug(value)}"] = "1" if observed == value else "0"
    observed_flags = set(_split_flags(row.get("model_feature_quality_flags", "")))
    for flag in quality_flags:
        feature_values[f"feature_flag_{_slug(flag)}"] = (
            "1" if flag in observed_flags else "0"
        )
    for column in feature_columns:
        record[column] = feature_values.get(column, "0")
    return record


def _state_incidence(rows: list[dict[str, str]]) -> float | None:
    if not rows:
        return None
    total_cases = sum(_parse_float(row.get("total_cases", "")) for row in rows)
    total_population = sum(_parse_float(row.get("population", "")) for row in rows)
    if total_population <= 0:
        return None
    return total_cases / total_population * 100000


def _status_feature_base(column: str) -> str:
    return f"feature_tick_{column.removesuffix('_status')}"


def _split_flags(value: str | None) -> list[str]:
    if value is None:
        return []
    normalized = str(value).replace(";", ",")
    return [
        item.strip()
        for item in normalized.split(",")
        if item.strip()
    ]


def _format_int(value: str) -> str:
    if _is_blank(value):
        return "0"
    return str(int(float(str(value).strip())))


def _format_float(value: str) -> str:
    if _is_blank(value):
        return "0.0"
    return _format_number(float(str(value).strip()))


def _format_number(value: float | None) -> str:
    if value is None:
        return "0.0"
    return str(round(float(value), 6))


def _parse_float(value: str) -> float:
    if _is_blank(value):
        return 0.0
    return float(str(value).strip())


def _parse_bool_or_none(value: str | None) -> bool | None:
    if _is_blank(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def _is_blank(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
