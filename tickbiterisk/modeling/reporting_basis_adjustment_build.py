from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.reporting_basis_adjustment import (
    ReportingBasisAdjustmentResult,
)


HIGH_INCIDENCE_CLASSIFICATION_COLUMNS = [
    "jurisdiction_fips",
    "classification",
    "qualifying_years",
    "threshold_per_100k",
    "consecutive_years_required",
    "pre_window",
    "source_panel_sha256",
    "source_citation_url",
    "assumption_flags",
    "notes",
]

REPORTING_BASIS_ADJUSTMENT_COLUMNS = [
    "adjustment_id",
    "jurisdiction_scope",
    "boundary_year",
    "source_regime",
    "target_reference_basis",
    "adjustment_method",
    "multiplicative_factor",
    "factor_se_log",
    "factor_ci80_low",
    "factor_ci80_high",
    "factor_ci95_low",
    "factor_ci95_high",
    "treatment_status",
    "n_control_jurisdictions",
    "n_observations_used",
    "identification_quality",
    "smoothed_on_adjacency",
    "displayed_as",
    "pre_window",
    "source_citation_url",
    "source_panel_sha256",
    "source_vintage",
    "assumption_flags",
    "notes",
]

DID_CONTROL_PANEL_COLUMNS = [
    "candidate_state_fips",
    "candidate_state_name",
    "county_fips",
    "county_name",
    "instrument_role",
    "forecast_exclusion",
    "candidate_pre_window",
    "candidate_low_incidence_status",
    "parallel_trends_status",
    "parallel_trends_treatment_slope",
    "parallel_trends_control_slope",
    "parallel_trends_slope_difference",
    "inclusion_decision",
    "failure_reason",
    "source_panel_sha256",
    "source_vintage",
    "assumption_flags",
    "notes",
]

REPORTING_BASIS_ADJUSTMENT_RUN_COLUMNS = [
    "run_id",
    "regional_incidence_path",
    "regional_incidence_sha256",
    "county_adjacency_path",
    "county_adjacency_sha256",
    "did_control_panel_path",
    "did_control_panel_sha256",
    "pre_window",
    "boundary_year",
    "target_reference_basis",
    "identification_method",
    "did_control_evaluated",
    "did_control_passed",
    "did_control_failure_reason",
    "did_control_decision_reference",
    "threshold_per_100k",
    "consecutive_years_required",
    "did_treatment_shift",
    "did_control_shift",
    "did_ratio",
    "parallel_trends_status",
    "parallel_trends_treatment_slope",
    "parallel_trends_control_slope",
    "parallel_trend_tolerance",
    "candidate_control_states_passed",
    "candidate_control_states_failed",
    "method_validation_2008_status",
    "method_validation_2008_observed_ratio",
    "method_validation_2017_status",
    "method_validation_2017_observed_ratio",
    "n_treatment_jurisdictions",
    "n_control_jurisdictions",
    "source_citation_url",
    "source_vintage",
]


@dataclass(frozen=True)
class ReportingBasisAdjustmentOutputPaths:
    run_path: Path
    classification_path: Path
    did_control_panel_path: Path
    adjustment_path: Path


def write_reporting_basis_adjustment_outputs(
    result: ReportingBasisAdjustmentResult,
    output_dir: Path,
) -> ReportingBasisAdjustmentOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / "reporting_basis_adjustment_runs.csv"
    classification_path = output_dir / "high_incidence_classification.csv"
    did_control_panel_path = output_dir / "did_control_panel.csv"
    adjustment_path = output_dir / "reporting_basis_adjustment.csv"
    _write_records(
        run_path,
        [asdict(result.run)],
        REPORTING_BASIS_ADJUSTMENT_RUN_COLUMNS,
    )
    _write_records(
        classification_path,
        [asdict(row) for row in result.classifications],
        HIGH_INCIDENCE_CLASSIFICATION_COLUMNS,
    )
    _write_records(
        did_control_panel_path,
        [asdict(row) for row in result.did_control_panel],
        DID_CONTROL_PANEL_COLUMNS,
    )
    _write_records(
        adjustment_path,
        [asdict(row) for row in result.adjustments],
        REPORTING_BASIS_ADJUSTMENT_COLUMNS,
    )
    return ReportingBasisAdjustmentOutputPaths(
        run_path=run_path,
        classification_path=classification_path,
        did_control_panel_path=did_control_panel_path,
        adjustment_path=adjustment_path,
    )


def _write_records(
    path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
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
