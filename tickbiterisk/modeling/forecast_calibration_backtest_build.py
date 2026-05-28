from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.forecast_calibration_backtest import (
    ForecastCalibrationBacktestResult,
)


FORECAST_CALIBRATION_BACKTEST_RUN_COLUMNS = [
    "run_id",
    "predictions_path",
    "predictions_sha256",
    "start_year",
    "end_year",
    "min_calibration_updates",
    "calibration_prior_strength",
    "calibration_method",
    "model_names",
    "n_input_rows",
    "n_predictions",
    "comparison_assumption_flags",
]

FORECAST_CALIBRATION_BACKTEST_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "county_fips",
    "county_name",
    "forecast_year",
    "surveillance_regime",
    "calibration_scope",
    "n_calibration_updates",
    "raw_actual_to_predicted_case_ratio",
    "shrunken_case_multiplier",
    "original_predicted_incidence_per_100k",
    "calibrated_predicted_incidence_per_100k",
    "actual_incidence_per_100k",
    "original_residual_incidence_per_100k",
    "calibrated_residual_incidence_per_100k",
    "original_absolute_error_incidence_per_100k",
    "calibrated_absolute_error_incidence_per_100k",
    "original_predicted_cases",
    "calibrated_predicted_cases",
    "actual_cases",
    "original_absolute_error_cases",
    "calibrated_absolute_error_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

FORECAST_CALIBRATION_BACKTEST_METRIC_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "aggregation",
    "surveillance_regime",
    "forecast_year",
    "n_predictions",
    "original_mae_incidence_per_100k",
    "calibrated_mae_incidence_per_100k",
    "mae_improvement_incidence_per_100k",
    "original_rmse_incidence_per_100k",
    "calibrated_rmse_incidence_per_100k",
    "original_mae_cases",
    "calibrated_mae_cases",
    "mae_improvement_cases",
    "recommended_update_use",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class ForecastCalibrationBacktestOutputPaths:
    runs_path: Path
    predictions_path: Path
    metrics_path: Path


def write_forecast_calibration_backtest_outputs(
    result: ForecastCalibrationBacktestResult,
    output_dir: Path,
) -> ForecastCalibrationBacktestOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "forecast_calibration_backtest_runs.csv"
    predictions_path = output_dir / "forecast_calibration_backtest_predictions.csv"
    metrics_path = output_dir / "forecast_calibration_backtest_metrics.csv"

    _write_records(
        runs_path,
        [asdict(result.run)],
        FORECAST_CALIBRATION_BACKTEST_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        [asdict(row) for row in result.predictions],
        FORECAST_CALIBRATION_BACKTEST_PREDICTION_COLUMNS,
    )
    _write_records(
        metrics_path,
        [asdict(row) for row in result.metrics],
        FORECAST_CALIBRATION_BACKTEST_METRIC_COLUMNS,
    )
    return ForecastCalibrationBacktestOutputPaths(
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
