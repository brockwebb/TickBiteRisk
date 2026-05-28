from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_incidence_stress import (
    RegionalIncidenceStressResult,
)


REGIONAL_INCIDENCE_STRESS_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "start_year",
    "end_year",
    "min_train_years",
    "lookback_years",
    "shrinkage_strength",
    "model_names",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "n_input_rows",
    "n_predictions",
    "comparison_assumption_flags",
]

REGIONAL_INCIDENCE_STRESS_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "source_file_sha256",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "test_year",
    "train_start_year",
    "train_end_year",
    "train_year_count",
    "actual_incidence_per_100k",
    "predicted_incidence_per_100k",
    "residual_incidence_per_100k",
    "absolute_error_incidence_per_100k",
    "actual_cases",
    "actual_population",
    "predicted_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

REGIONAL_INCIDENCE_STRESS_METRIC_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "source_file_sha256",
    "aggregation",
    "state_fips",
    "state_name",
    "test_year",
    "n_predictions",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "mean_bias_incidence_per_100k",
    "mae_cases",
    "rmse_cases",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class RegionalIncidenceStressOutputPaths:
    runs_path: Path
    predictions_path: Path
    metrics_path: Path


def write_regional_incidence_stress_outputs(
    result: RegionalIncidenceStressResult,
    output_dir: Path,
) -> RegionalIncidenceStressOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_incidence_stress_runs.csv"
    predictions_path = output_dir / "regional_incidence_stress_predictions.csv"
    metrics_path = output_dir / "regional_incidence_stress_metrics.csv"

    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_INCIDENCE_STRESS_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        [asdict(row) for row in result.predictions],
        REGIONAL_INCIDENCE_STRESS_PREDICTION_COLUMNS,
    )
    _write_records(
        metrics_path,
        [asdict(row) for row in result.metrics],
        REGIONAL_INCIDENCE_STRESS_METRIC_COLUMNS,
    )
    return RegionalIncidenceStressOutputPaths(
        runs_path=runs_path,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
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
