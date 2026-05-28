from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_incidence_clusters import (
    RegionalIncidenceClusterResult,
)


REGIONAL_INCIDENCE_CLUSTER_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "start_year",
    "end_year",
    "min_train_years",
    "lookback_years",
    "n_clusters",
    "clustering_method",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "n_input_rows",
    "n_county_years",
    "n_summary_rows",
    "comparison_assumption_flags",
]

REGIONAL_INCIDENCE_CLUSTER_COUNTY_YEAR_COLUMNS = [
    "run_id",
    "source_file_sha256",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "cluster_id",
    "cluster_rank",
    "cluster_label",
    "cluster_centroid_prior_mean_incidence_per_100k",
    "feature_prior_mean_incidence_per_100k",
    "feature_prior_min_incidence_per_100k",
    "feature_prior_max_incidence_per_100k",
    "feature_prior_sd_incidence_per_100k",
    "feature_prior_year_incidence_per_100k",
    "train_start_year",
    "train_end_year",
    "train_year_count",
    "actual_incidence_per_100k",
    "actual_cases",
    "actual_population",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

REGIONAL_INCIDENCE_CLUSTER_SUMMARY_COLUMNS = [
    "run_id",
    "source_file_sha256",
    "year",
    "cluster_id",
    "cluster_rank",
    "cluster_label",
    "n_counties",
    "feature_prior_cluster_min_incidence_per_100k",
    "feature_prior_cluster_mean_incidence_per_100k",
    "feature_prior_cluster_max_incidence_per_100k",
    "feature_prior_cluster_sd_incidence_per_100k",
    "diagnostic_actual_cluster_incidence_per_100k",
    "diagnostic_actual_cluster_cases",
    "diagnostic_actual_cluster_population",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class RegionalIncidenceClusterOutputPaths:
    runs_path: Path
    county_year_path: Path
    summary_path: Path


def write_regional_incidence_cluster_outputs(
    result: RegionalIncidenceClusterResult,
    output_dir: Path,
) -> RegionalIncidenceClusterOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_incidence_cluster_runs.csv"
    county_year_path = output_dir / "regional_incidence_cluster_county_year.csv"
    summary_path = output_dir / "regional_incidence_cluster_summary.csv"

    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_INCIDENCE_CLUSTER_RUN_COLUMNS,
    )
    _write_records(
        county_year_path,
        [asdict(row) for row in result.county_year_rows],
        REGIONAL_INCIDENCE_CLUSTER_COUNTY_YEAR_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary_rows],
        REGIONAL_INCIDENCE_CLUSTER_SUMMARY_COLUMNS,
    )
    return RegionalIncidenceClusterOutputPaths(
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
