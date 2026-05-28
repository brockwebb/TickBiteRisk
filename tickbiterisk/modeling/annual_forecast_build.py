from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.annual_forecast import AnnualForecastResult


ANNUAL_FORECAST_RUN_COLUMNS = [
    "run_id",
    "design_matrix_path",
    "design_matrix_sha256",
    "population_path",
    "population_sha256",
    "target_year",
    "forecast_origin_year",
    "min_train_years",
    "shrinkage_strength",
    "model_names",
    "target_definition",
    "evaluation_mode",
    "feature_set",
    "n_training_rows",
    "n_forecast_counties",
    "n_forecast_rows",
    "forecast_assumption_flags",
]

ANNUAL_FORECAST_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "weather_mode",
    "design_matrix_sha256",
    "population_sha256",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "forecast_horizon_years",
    "train_start_year",
    "train_end_year",
    "train_row_count",
    "train_county_count",
    "forecast_population",
    "population_source_id",
    "population_vintage",
    "population_feature_quality_flags",
    "predicted_cases",
    "predicted_incidence_per_100k",
    "model_feature_quality_flags",
    "forecast_assumption_flags",
]


@dataclass(frozen=True)
class AnnualForecastOutputPaths:
    runs_path: Path
    predictions_path: Path


def write_annual_forecast_outputs(
    result: AnnualForecastResult,
    output_dir: Path,
) -> AnnualForecastOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "annual_forecast_runs.csv"
    predictions_path = output_dir / "annual_forecast_predictions.csv"
    _write_records(runs_path, [asdict(result.run)], ANNUAL_FORECAST_RUN_COLUMNS)
    _write_records(
        predictions_path,
        [asdict(row) for row in result.predictions],
        ANNUAL_FORECAST_PREDICTION_COLUMNS,
    )
    return AnnualForecastOutputPaths(
        runs_path=runs_path,
        predictions_path=predictions_path,
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
            {
                column: _format_value(record.get(column))
                for column in columns
            }
            for record in records
        )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
