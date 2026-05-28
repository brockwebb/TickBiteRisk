from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.model_diagnostics import ModelDiagnosticsResult


SURVEILLANCE_REGIME_RESIDUAL_COLUMNS = [
    "model_name",
    "model_family",
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
    "model_name",
    "model_family",
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

REGIONAL_HOTSPOT_SUMMARY_COLUMNS = ["model_name"]
REGIONAL_CAPACITY_INTERVAL_COLUMNS = ["model_name"]


@dataclass(frozen=True)
class ModelDiagnosticsOutputPaths:
    surveillance_residuals_path: Path
    surveillance_summary_path: Path
    regional_hotspot_summary_path: Path
    regional_capacity_intervals_path: Path


def write_model_diagnostics_outputs(
    result: ModelDiagnosticsResult,
    output_dir: Path,
) -> ModelDiagnosticsOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    surveillance_residuals_path = output_dir / "surveillance_regime_residuals.csv"
    surveillance_summary_path = output_dir / "surveillance_regime_summary.csv"
    regional_hotspot_summary_path = output_dir / "regional_hotspot_summary.csv"
    regional_capacity_intervals_path = output_dir / "regional_capacity_intervals.csv"

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
        result.regional_hotspot_summary,
        REGIONAL_HOTSPOT_SUMMARY_COLUMNS,
    )
    _write_records(
        regional_capacity_intervals_path,
        result.regional_capacity_intervals,
        REGIONAL_CAPACITY_INTERVAL_COLUMNS,
    )
    return ModelDiagnosticsOutputPaths(
        surveillance_residuals_path=surveillance_residuals_path,
        surveillance_summary_path=surveillance_summary_path,
        regional_hotspot_summary_path=regional_hotspot_summary_path,
        regional_capacity_intervals_path=regional_capacity_intervals_path,
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
