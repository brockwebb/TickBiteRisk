from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_spatial_regimes import (
    RegionalSpatialRegimeResult,
)


REGIONAL_SPATIAL_REGIME_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "regional_adjacency_path",
    "regional_adjacency_sha256",
    "start_year",
    "end_year",
    "min_train_years",
    "lookback_years",
    "max_prior_mean_difference",
    "max_prior_year_difference",
    "max_trend_difference",
    "regime_method",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "n_input_rows",
    "n_county_years",
    "n_summary_rows",
    "comparison_assumption_flags",
]

REGIONAL_SPATIAL_REGIME_COUNTY_YEAR_COLUMNS = [
    "run_id",
    "source_file_sha256",
    "regional_adjacency_sha256",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "spatial_regime_id",
    "spatial_regime_rank",
    "spatial_regime_member_count",
    "spatial_regime_neighbor_count",
    "feature_county_prior_mean_incidence_per_100k",
    "feature_county_prior_year_incidence_per_100k",
    "feature_county_prior_trend_incidence_per_100k",
    "feature_regime_trailing_mean_incidence_per_100k",
    "feature_regime_prior_year_mean_incidence_per_100k",
    "feature_regime_min_prior_mean_incidence_per_100k",
    "feature_regime_max_prior_mean_incidence_per_100k",
    "feature_regime_sd_prior_mean_incidence_per_100k",
    "train_start_year",
    "train_end_year",
    "train_year_count",
    "diagnostic_actual_incidence_per_100k",
    "diagnostic_actual_cases",
    "diagnostic_actual_population",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

REGIONAL_SPATIAL_REGIME_SUMMARY_COLUMNS = [
    "run_id",
    "source_file_sha256",
    "regional_adjacency_sha256",
    "year",
    "spatial_regime_id",
    "spatial_regime_rank",
    "n_counties",
    "county_fips_list",
    "feature_regime_trailing_mean_incidence_per_100k",
    "feature_regime_prior_year_mean_incidence_per_100k",
    "feature_regime_min_prior_mean_incidence_per_100k",
    "feature_regime_max_prior_mean_incidence_per_100k",
    "feature_regime_sd_prior_mean_incidence_per_100k",
    "diagnostic_actual_regime_incidence_per_100k",
    "diagnostic_actual_regime_cases",
    "diagnostic_actual_regime_population",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class RegionalSpatialRegimeOutputPaths:
    runs_path: Path
    county_year_path: Path
    summary_path: Path


def write_regional_spatial_regime_outputs(
    result: RegionalSpatialRegimeResult,
    output_dir: Path,
) -> RegionalSpatialRegimeOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_spatial_regime_runs.csv"
    county_year_path = output_dir / "regional_spatial_regime_county_year.csv"
    summary_path = output_dir / "regional_spatial_regime_summary.csv"

    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_SPATIAL_REGIME_RUN_COLUMNS,
    )
    _write_records(
        county_year_path,
        [asdict(row) for row in result.county_year_rows],
        REGIONAL_SPATIAL_REGIME_COUNTY_YEAR_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary_rows],
        REGIONAL_SPATIAL_REGIME_SUMMARY_COLUMNS,
    )
    return RegionalSpatialRegimeOutputPaths(
        runs_path=runs_path,
        county_year_path=county_year_path,
        summary_path=summary_path,
    )


def _write_records(
    output_path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {column: _format_value(record.get(column)) for column in columns}
            for record in records
        )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
