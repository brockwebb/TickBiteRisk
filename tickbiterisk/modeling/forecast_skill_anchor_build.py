from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.forecast_skill_anchor import (
    Step1ForecastSkillAnchorResult,
)


STEP1_FORECAST_SKILL_ANCHOR_RUN_COLUMNS = [
    "run_id",
    "observed_fit_comparisons_path",
    "observed_fit_comparisons_sha256",
    "source_comparison_run_id",
    "source_diagnostic_scope",
    "state_fips",
    "state_abbr",
    "state_name",
    "forecast_year",
    "forecast_origin_year",
    "model_name",
    "n_anchor_rows",
    "permitted_use",
    "prohibited_use",
    "anchor_assumption_flags",
]

STEP1_FORECAST_SKILL_ANCHOR_COLUMNS = [
    "anchor_id",
    "source_comparison_run_id",
    "source_diagnostic_scope",
    "source_comparisons_sha256",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "predicted_cases",
    "observed_cases",
    "case_residual",
    "absolute_case_error",
    "predicted_incidence_per_100k",
    "observed_incidence_per_100k",
    "incidence_residual_per_100k",
    "absolute_incidence_error_per_100k",
    "interval_calibration_weight",
    "point_correction_allowed",
    "permitted_use",
    "prohibited_use",
    "forecast_assumption_flags",
    "observed_quality_flags",
    "source_diagnostic_flags",
    "anchor_assumption_flags",
]


@dataclass(frozen=True)
class Step1ForecastSkillAnchorOutputPaths:
    run_path: Path
    anchor_path: Path


def write_step1_forecast_skill_anchor_outputs(
    result: Step1ForecastSkillAnchorResult,
    output_dir: Path,
) -> Step1ForecastSkillAnchorOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / "step1_forecast_skill_anchor_runs.csv"
    anchor_path = output_dir / "step1_forecast_skill_anchor.csv"
    _write_records(
        run_path,
        [asdict(result.run)],
        STEP1_FORECAST_SKILL_ANCHOR_RUN_COLUMNS,
    )
    _write_records(
        anchor_path,
        [asdict(row) for row in result.anchors],
        STEP1_FORECAST_SKILL_ANCHOR_COLUMNS,
    )
    return Step1ForecastSkillAnchorOutputPaths(
        run_path=run_path,
        anchor_path=anchor_path,
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
