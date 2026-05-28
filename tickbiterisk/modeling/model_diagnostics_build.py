from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.model_diagnostics import ModelDiagnosticsResult


SURVEILLANCE_REGIME_RESIDUAL_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "county_fips",
    "county_name",
    "surveillance_regime",
    "actual_incidence_per_100k",
    "predicted_incidence_per_100k",
    "residual_incidence_per_100k",
    "absolute_error_incidence_per_100k",
    "actual_cases",
    "predicted_cases",
    "residual_cases",
    "absolute_error_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

SURVEILLANCE_REGIME_SUMMARY_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "surveillance_regime",
    "test_year",
    "n_predictions",
    "mean_residual_incidence_per_100k",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "mean_residual_cases",
    "mae_cases",
    "comparison_assumption_flags",
]

REGIONAL_HOTSPOT_SUMMARY_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "region_id",
    "region_name",
    "n_counties",
    "actual_total_cases",
    "predicted_total_cases",
    "residual_cases",
    "absolute_error_cases",
    "actual_incidence_per_100k_mean",
    "predicted_incidence_per_100k_mean",
    "spearman_rank_correlation",
    "top3_hit_count",
    "top5_hit_count",
    "county_share_mae",
    "predicted_case_hhi",
    "actual_case_hhi",
    "comparison_assumption_flags",
]
REGIONAL_CAPACITY_INTERVAL_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "region_id",
    "region_name",
    "interval_method",
    "n_counties",
    "lower_80_cases",
    "median_cases",
    "upper_80_cases",
    "lower_95_cases",
    "upper_95_cases",
    "actual_cases",
    "covered_80",
    "covered_95",
    "comparison_assumption_flags",
]

FORECAST_UPDATE_AUDIT_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "source_file_sha256",
    "source_vintage",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "target_definition",
    "evaluation_mode",
    "update_mode",
    "surveillance_regime",
    "predicted_incidence_per_100k",
    "predicted_cases",
    "lower_80_incidence_per_100k",
    "median_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "interval_available",
    "covered_80",
    "covered_95",
    "actual_incidence_per_100k",
    "actual_cases",
    "residual_incidence_per_100k",
    "absolute_error_incidence_per_100k",
    "signed_percent_error",
    "update_direction",
    "update_interpretation",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

FORECAST_UPDATE_SUMMARY_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "source_file_sha256",
    "source_vintage",
    "evaluation_mode",
    "surveillance_regime",
    "forecast_year",
    "n_updates",
    "mean_residual_incidence_per_100k",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "interval_available_count",
    "covered_80_count",
    "covered_95_count",
    "forecast_signal_count",
    "surveillance_regime_signal_count",
    "ambiguous_signal_count",
    "insufficient_signal_count",
    "forecast_signal_share",
    "surveillance_regime_signal_share",
    "ambiguous_signal_share",
    "insufficient_signal_share",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class ModelDiagnosticsOutputPaths:
    surveillance_residuals_path: Path
    surveillance_summary_path: Path
    regional_hotspot_summary_path: Path
    regional_capacity_intervals_path: Path
    forecast_update_audit_path: Path
    forecast_update_summary_path: Path


def write_model_diagnostics_outputs(
    result: ModelDiagnosticsResult,
    output_dir: Path,
) -> ModelDiagnosticsOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    surveillance_residuals_path = output_dir / "surveillance_regime_residuals.csv"
    surveillance_summary_path = output_dir / "surveillance_regime_summary.csv"
    regional_hotspot_summary_path = output_dir / "regional_hotspot_summary.csv"
    regional_capacity_intervals_path = output_dir / "regional_capacity_intervals.csv"
    forecast_update_audit_path = output_dir / "forecast_update_audit.csv"
    forecast_update_summary_path = output_dir / "forecast_update_summary.csv"

    _write_records(
        surveillance_residuals_path,
        [asdict(row) for row in result.surveillance_residuals],
        SURVEILLANCE_REGIME_RESIDUAL_COLUMNS,
    )
    _write_records(
        surveillance_summary_path,
        [asdict(row) for row in result.surveillance_summary],
        SURVEILLANCE_REGIME_SUMMARY_COLUMNS,
    )
    _write_records(
        regional_hotspot_summary_path,
        [asdict(row) for row in result.regional_hotspot_summary],
        REGIONAL_HOTSPOT_SUMMARY_COLUMNS,
    )
    _write_records(
        regional_capacity_intervals_path,
        [asdict(row) for row in result.regional_capacity_intervals],
        REGIONAL_CAPACITY_INTERVAL_COLUMNS,
    )
    _write_records(
        forecast_update_audit_path,
        [asdict(row) for row in result.forecast_update_audit],
        FORECAST_UPDATE_AUDIT_COLUMNS,
    )
    _write_records(
        forecast_update_summary_path,
        [asdict(row) for row in result.forecast_update_summary],
        FORECAST_UPDATE_SUMMARY_COLUMNS,
    )
    return ModelDiagnosticsOutputPaths(
        surveillance_residuals_path=surveillance_residuals_path,
        surveillance_summary_path=surveillance_summary_path,
        regional_hotspot_summary_path=regional_hotspot_summary_path,
        regional_capacity_intervals_path=regional_capacity_intervals_path,
        forecast_update_audit_path=forecast_update_audit_path,
        forecast_update_summary_path=forecast_update_summary_path,
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
