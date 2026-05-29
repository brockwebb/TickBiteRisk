from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.forecast_bayesian_update_backtest import (
    ForecastBayesianUpdateBacktestResult,
)


FORECAST_BAYESIAN_UPDATE_BACKTEST_RUN_COLUMNS = [
    "run_id",
    "predictions_path",
    "predictions_sha256",
    "start_year",
    "end_year",
    "min_prior_updates",
    "prior_strength_cases",
    "bayes_update_method",
    "interval_method",
    "model_names",
    "n_input_rows",
    "n_predictions",
    "comparison_assumption_flags",
]

FORECAST_BAYESIAN_UPDATE_BACKTEST_PREDICTION_COLUMNS = [
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
    "update_scope",
    "n_prior_updates",
    "prior_actual_cases",
    "prior_predicted_cases",
    "posterior_alpha",
    "posterior_beta",
    "posterior_case_multiplier_mean",
    "posterior_case_multiplier_variance",
    "original_predicted_incidence_per_100k",
    "updated_predicted_incidence_per_100k",
    "actual_incidence_per_100k",
    "original_residual_incidence_per_100k",
    "updated_residual_incidence_per_100k",
    "original_absolute_error_incidence_per_100k",
    "updated_absolute_error_incidence_per_100k",
    "original_predicted_cases",
    "updated_predicted_cases",
    "lower_80_updated_cases",
    "upper_80_updated_cases",
    "lower_95_updated_cases",
    "upper_95_updated_cases",
    "actual_cases",
    "covered_80",
    "covered_95",
    "original_absolute_error_cases",
    "updated_absolute_error_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

FORECAST_BAYESIAN_UPDATE_BACKTEST_METRIC_COLUMNS = [
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
    "updated_mae_incidence_per_100k",
    "mae_improvement_incidence_per_100k",
    "original_rmse_incidence_per_100k",
    "updated_rmse_incidence_per_100k",
    "original_mae_cases",
    "updated_mae_cases",
    "mae_improvement_cases",
    "coverage_80_count",
    "coverage_95_count",
    "coverage_80_share",
    "coverage_95_share",
    "update_gate_decision",
    "update_gate_reason",
    "recommended_update_use",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class ForecastBayesianUpdateBacktestOutputPaths:
    runs_path: Path
    predictions_path: Path
    metrics_path: Path


def write_forecast_bayesian_update_backtest_outputs(
    result: ForecastBayesianUpdateBacktestResult,
    output_dir: Path,
) -> ForecastBayesianUpdateBacktestOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "forecast_bayesian_update_backtest_runs.csv"
    predictions_path = output_dir / "forecast_bayesian_update_backtest_predictions.csv"
    metrics_path = output_dir / "forecast_bayesian_update_backtest_metrics.csv"

    _write_records(
        runs_path,
        [asdict(result.run)],
        FORECAST_BAYESIAN_UPDATE_BACKTEST_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        [asdict(row) for row in result.predictions],
        FORECAST_BAYESIAN_UPDATE_BACKTEST_PREDICTION_COLUMNS,
    )
    _write_records(
        metrics_path,
        [asdict(row) for row in result.metrics],
        FORECAST_BAYESIAN_UPDATE_BACKTEST_METRIC_COLUMNS,
    )
    return ForecastBayesianUpdateBacktestOutputPaths(
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
