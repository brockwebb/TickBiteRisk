from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_forecast_capacity import (
    RegionalForecastCapacityResult,
)


REGIONAL_FORECAST_CAPACITY_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "forecast_predictions_path",
    "forecast_predictions_sha256",
    "forecast_year",
    "forecast_origin_year",
    "history_start_year",
    "history_end_year",
    "model_names",
    "n_forecast_rows",
    "n_capacity_rows",
    "capacity_assumption_flags",
]

REGIONAL_FORECAST_CAPACITY_SUMMARY_COLUMNS = [
    "run_id",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_vintage",
    "geography_level",
    "region_id",
    "region_name",
    "forecast_year",
    "forecast_origin_year",
    "history_start_year",
    "history_end_year",
    "history_year_count",
    "n_counties",
    "forecast_total_cases",
    "forecast_population",
    "forecast_incidence_per_100k",
    "history_min_cases",
    "history_p10_cases",
    "history_mean_cases",
    "history_p90_cases",
    "history_max_cases",
    "history_min_incidence_per_100k",
    "history_p10_incidence_per_100k",
    "history_mean_incidence_per_100k",
    "history_p90_incidence_per_100k",
    "history_max_incidence_per_100k",
    "forecast_case_percentile_of_history",
    "forecast_incidence_percentile_of_history",
    "above_history_max_cases",
    "below_history_min_cases",
    "capacity_assumption_flags",
]


@dataclass(frozen=True)
class RegionalForecastCapacityOutputPaths:
    runs_path: Path
    capacity_summary_path: Path


def write_regional_forecast_capacity_outputs(
    result: RegionalForecastCapacityResult,
    output_dir: Path,
) -> RegionalForecastCapacityOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_forecast_capacity_runs.csv"
    capacity_summary_path = output_dir / "regional_forecast_capacity_summary.csv"
    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_FORECAST_CAPACITY_RUN_COLUMNS,
    )
    _write_records(
        capacity_summary_path,
        [asdict(row) for row in result.capacity_summary],
        REGIONAL_FORECAST_CAPACITY_SUMMARY_COLUMNS,
    )
    return RegionalForecastCapacityOutputPaths(
        runs_path=runs_path,
        capacity_summary_path=capacity_summary_path,
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
