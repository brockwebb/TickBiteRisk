from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.regional_forecast_typicality import (
    RegionalForecastTypicalityResult,
)


REGIONAL_FORECAST_TYPICALITY_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "regional_annual_forecast_intervals_path",
    "regional_annual_forecast_intervals_sha256",
    "model_name",
    "comparison_scope",
    "typicality_method",
    "baseline_policy",
    "min_history_years",
    "n_forecast_rows",
    "n_typicality_rows",
    "assumption_flags",
]

REGIONAL_FORECAST_TYPICALITY_COLUMNS = [
    "run_id",
    "source_interval_run_id",
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
    "predicted_cases",
    "predicted_incidence_per_100k",
    "lower_80_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "comparison_scope",
    "comparison_year_start",
    "comparison_year_end",
    "baseline_year_count",
    "typical_median_incidence_per_100k",
    "typical_p25_incidence_per_100k",
    "typical_p75_incidence_per_100k",
    "forecast_percentile_of_county_history",
    "lower_80_percentile_of_county_history",
    "upper_80_percentile_of_county_history",
    "lower_95_percentile_of_county_history",
    "upper_95_percentile_of_county_history",
    "severity_label",
    "interval_severity_label",
    "typicality_evidence_level",
    "margin_to_typical_band_per_100k",
    "typicality_method",
    "baseline_policy",
    "protocol_policy",
    "assumption_flags",
]


@dataclass(frozen=True)
class RegionalForecastTypicalityOutputPaths:
    runs_path: Path
    typicality_path: Path


def write_regional_forecast_typicality_outputs(
    result: RegionalForecastTypicalityResult,
    output_dir: Path,
) -> RegionalForecastTypicalityOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_forecast_typicality_runs.csv"
    typicality_path = output_dir / "regional_forecast_typicality.csv"
    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_FORECAST_TYPICALITY_RUN_COLUMNS,
    )
    _write_records(
        typicality_path,
        [asdict(row) for row in result.rows],
        REGIONAL_FORECAST_TYPICALITY_COLUMNS,
    )
    return RegionalForecastTypicalityOutputPaths(
        runs_path=runs_path,
        typicality_path=typicality_path,
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
