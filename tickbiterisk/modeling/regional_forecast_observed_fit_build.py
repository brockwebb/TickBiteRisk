from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_forecast_observed_fit import (
    RegionalForecastObservedFitResult,
)


REGIONAL_FORECAST_OBSERVED_FIT_RUN_COLUMNS = [
    "run_id",
    "diagnostic_scope",
    "forecast_predictions_path",
    "forecast_predictions_sha256",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "state_fips",
    "state_abbr",
    "state_name",
    "n_forecast_rows",
    "n_observed_rows",
    "n_matched_counties",
    "diagnostic_flags",
]

REGIONAL_FORECAST_OBSERVED_FIT_COMPARISON_COLUMNS = [
    "run_id",
    "diagnostic_scope",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "forecast_population",
    "observed_population",
    "predicted_cases",
    "observed_cases",
    "case_residual",
    "absolute_case_error",
    "predicted_incidence_per_100k",
    "observed_incidence_per_100k",
    "incidence_residual_per_100k",
    "absolute_incidence_error_per_100k",
    "model_feature_quality_flags",
    "forecast_assumption_flags",
    "observed_quality_flags",
    "diagnostic_flags",
]

REGIONAL_FORECAST_OBSERVED_FIT_SUMMARY_COLUMNS = [
    "run_id",
    "diagnostic_scope",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "state_fips",
    "state_abbr",
    "state_name",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "n_counties",
    "predicted_total_cases",
    "observed_total_cases",
    "case_total_residual",
    "mean_case_residual",
    "mae_cases",
    "rmse_cases",
    "predicted_population",
    "observed_population",
    "predicted_incidence_per_100k",
    "observed_incidence_per_100k",
    "incidence_residual_per_100k",
    "mean_incidence_residual_per_100k",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "under_prediction_count",
    "over_prediction_count",
    "exact_prediction_count",
    "diagnostic_flags",
]


@dataclass(frozen=True)
class RegionalForecastObservedFitOutputPaths:
    runs_path: Path
    comparisons_path: Path
    summary_path: Path


def write_regional_forecast_observed_fit_outputs(
    result: RegionalForecastObservedFitResult,
    output_dir: Path,
) -> RegionalForecastObservedFitOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_forecast_observed_fit_runs.csv"
    comparisons_path = output_dir / "regional_forecast_observed_fit_comparisons.csv"
    summary_path = output_dir / "regional_forecast_observed_fit_summary.csv"
    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_FORECAST_OBSERVED_FIT_RUN_COLUMNS,
    )
    _write_records(
        comparisons_path,
        [asdict(row) for row in result.comparisons],
        REGIONAL_FORECAST_OBSERVED_FIT_COMPARISON_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary],
        REGIONAL_FORECAST_OBSERVED_FIT_SUMMARY_COLUMNS,
    )
    return RegionalForecastObservedFitOutputPaths(
        runs_path=runs_path,
        comparisons_path=comparisons_path,
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
