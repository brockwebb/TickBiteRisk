from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_annual_forecast import (
    RegionalAnnualForecastResult,
)


REGIONAL_ANNUAL_FORECAST_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "regional_population_path",
    "regional_population_sha256",
    "regional_spatial_regimes_path",
    "regional_spatial_regimes_sha256",
    "regional_spatial_regime_feature_year",
    "target_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "min_train_years",
    "lookback_years",
    "shrinkage_strength",
    "model_names",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "n_training_rows",
    "n_forecast_counties",
    "n_forecast_rows",
    "forecast_assumption_flags",
]

REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "regional_incidence_sha256",
    "regional_population_sha256",
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
    "forecast_horizon_years",
    "train_start_year",
    "train_end_year",
    "train_year_count",
    "forecast_population",
    "population_source_id",
    "population_vintage",
    "population_feature_quality_flags",
    "predicted_cases",
    "predicted_incidence_per_100k",
    "analog_match_origin_year",
    "analog_match_observed_year",
    "analog_match_distance",
    "model_feature_quality_flags",
    "forecast_assumption_flags",
]


@dataclass(frozen=True)
class RegionalAnnualForecastOutputPaths:
    runs_path: Path
    predictions_path: Path


def write_regional_annual_forecast_outputs(
    result: RegionalAnnualForecastResult,
    output_dir: Path,
) -> RegionalAnnualForecastOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_annual_forecast_runs.csv"
    predictions_path = output_dir / "regional_annual_forecast_predictions.csv"
    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_ANNUAL_FORECAST_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        [asdict(row) for row in result.predictions],
        REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS,
    )
    return RegionalAnnualForecastOutputPaths(
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
            {column: _format_value(record.get(column)) for column in columns}
            for record in records
        )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
