from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path


ANCHOR_ASSUMPTION_FLAGS = (
    "pa_2024_step1_anchor,"
    "interval_calibration_only,"
    "point_correction_prohibited,"
    "state_source_overlay_provisional"
)
PERMITTED_USE = "interval_calibration_only"
PROHIBITED_USE = "point_correction_multiplier"
REQUIRED_OBSERVED_FIT_COLUMNS = {
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
    "predicted_cases",
    "observed_cases",
    "case_residual",
    "absolute_case_error",
    "predicted_incidence_per_100k",
    "observed_incidence_per_100k",
    "incidence_residual_per_100k",
    "absolute_incidence_error_per_100k",
    "forecast_assumption_flags",
    "observed_quality_flags",
    "diagnostic_flags",
}


class ForecastSkillAnchorInputError(ValueError):
    """Raised when forecast skill anchor inputs or requested uses are invalid."""


@dataclass(frozen=True)
class Step1ForecastSkillAnchorRun:
    run_id: str
    observed_fit_comparisons_path: str
    observed_fit_comparisons_sha256: str
    source_comparison_run_id: str
    source_diagnostic_scope: str
    state_fips: str
    state_abbr: str
    state_name: str
    forecast_year: int
    forecast_origin_year: int
    model_name: str
    n_anchor_rows: int
    permitted_use: str
    prohibited_use: str
    anchor_assumption_flags: str


@dataclass(frozen=True)
class Step1ForecastSkillAnchor:
    anchor_id: str
    source_comparison_run_id: str
    source_diagnostic_scope: str
    source_comparisons_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    predicted_cases: float
    observed_cases: int
    case_residual: float
    absolute_case_error: float
    predicted_incidence_per_100k: float
    observed_incidence_per_100k: float
    incidence_residual_per_100k: float
    absolute_incidence_error_per_100k: float
    interval_calibration_weight: float
    point_correction_allowed: bool
    permitted_use: str
    prohibited_use: str
    forecast_assumption_flags: str
    observed_quality_flags: str
    source_diagnostic_flags: str
    anchor_assumption_flags: str


@dataclass(frozen=True)
class Step1ForecastSkillAnchorResult:
    run_id: str
    run: Step1ForecastSkillAnchorRun
    anchors: list[Step1ForecastSkillAnchor]


def build_step1_forecast_skill_anchor(
    *,
    observed_fit_comparisons_path: Path,
    forecast_year: int = 2024,
    state_abbr: str = "PA",
) -> Step1ForecastSkillAnchorResult:
    normalized_state = state_abbr.strip().upper()
    if not normalized_state:
        raise ForecastSkillAnchorInputError("state_abbr is required")
    if forecast_year < 1:
        raise ForecastSkillAnchorInputError("forecast_year must be positive")

    source_sha = _sha256_file(observed_fit_comparisons_path)
    source_rows = [
        row
        for row in _read_observed_fit_rows(observed_fit_comparisons_path)
        if row["state_abbr"].strip().upper() == normalized_state
        and _parse_int(row["forecast_year"]) == forecast_year
    ]
    if not source_rows:
        raise ForecastSkillAnchorInputError(
            "no observed-fit comparison rows matched the requested state/year"
        )
    forecast_origin_years = {
        _parse_int(row["forecast_origin_year"])
        for row in source_rows
    }
    if len(forecast_origin_years) != 1:
        raise ForecastSkillAnchorInputError(
            "step-1 anchor requires one forecast_origin_year"
        )
    forecast_origin_year = next(iter(forecast_origin_years))
    if forecast_origin_year != forecast_year - 1:
        raise ForecastSkillAnchorInputError(
            "step-1 anchor requires forecast_origin_year == forecast_year - 1"
        )
    _validate_interval_anchor_rows(source_rows)
    first = source_rows[0]
    anchors = [
        _anchor_row(row, source_sha=source_sha)
        for row in sorted(source_rows, key=lambda item: item["county_fips"])
    ]
    run_id = (
        f"step1_forecast_skill_anchor_{normalized_state.lower()}"
        f"{forecast_year}_origin{forecast_origin_year}_{source_sha[:12]}"
    )
    run = Step1ForecastSkillAnchorRun(
        run_id=run_id,
        observed_fit_comparisons_path=str(observed_fit_comparisons_path),
        observed_fit_comparisons_sha256=source_sha,
        source_comparison_run_id=first["run_id"],
        source_diagnostic_scope=first["diagnostic_scope"],
        state_fips=str(first["state_fips"]).zfill(2),
        state_abbr=normalized_state,
        state_name=first["state_name"],
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        model_name=first["model_name"],
        n_anchor_rows=len(anchors),
        permitted_use=PERMITTED_USE,
        prohibited_use=PROHIBITED_USE,
        anchor_assumption_flags=ANCHOR_ASSUMPTION_FLAGS,
    )
    return Step1ForecastSkillAnchorResult(
        run_id=run_id,
        run=run,
        anchors=anchors,
    )


def validate_step1_anchor_requested_use(requested_use: str) -> None:
    if requested_use != "interval_calibration":
        raise ForecastSkillAnchorInputError(
            "PA step-1 forecast skill anchor is interval calibration only; "
            "point correction multipliers are prohibited"
        )


def _read_observed_fit_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_OBSERVED_FIT_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ForecastSkillAnchorInputError(
                "observed-fit comparisons missing required column(s): "
                f"{', '.join(sorted(missing))}"
            )
        return list(reader)


def _validate_interval_anchor_rows(rows: list[dict[str, str]]) -> None:
    for row in rows:
        if "state_source_not_cdc_public_use" not in row["observed_quality_flags"]:
            raise ForecastSkillAnchorInputError(
                "step-1 anchor rows must come from a state-source overlay"
            )
        if "partial_state_overlay" not in row["diagnostic_flags"]:
            raise ForecastSkillAnchorInputError(
                "step-1 anchor rows must carry partial_state_overlay diagnostics"
            )


def _anchor_row(
    row: dict[str, str],
    *,
    source_sha: str,
) -> Step1ForecastSkillAnchor:
    state_abbr = row["state_abbr"].strip().upper()
    forecast_year = _parse_int(row["forecast_year"])
    county_fips = str(row["county_fips"]).zfill(5)
    return Step1ForecastSkillAnchor(
        anchor_id=(
            f"{state_abbr.lower()}_{forecast_year}_step1_anchor_{county_fips}"
        ),
        source_comparison_run_id=row["run_id"],
        source_diagnostic_scope=row["diagnostic_scope"],
        source_comparisons_sha256=source_sha,
        state_fips=str(row["state_fips"]).zfill(2),
        state_abbr=state_abbr,
        state_name=row["state_name"],
        county_fips=county_fips,
        county_name=row["county_name"],
        forecast_year=forecast_year,
        forecast_origin_year=_parse_int(row["forecast_origin_year"]),
        model_name=row["model_name"],
        model_family=row["model_family"],
        target_definition=row["target_definition"],
        feature_set=row["feature_set"],
        feature_profile=row["feature_profile"],
        evaluation_mode=row["evaluation_mode"],
        predicted_cases=_round(_parse_float(row["predicted_cases"])),
        observed_cases=_parse_int(row["observed_cases"]),
        case_residual=_round(_parse_float(row["case_residual"])),
        absolute_case_error=_round(_parse_float(row["absolute_case_error"])),
        predicted_incidence_per_100k=_round(
            _parse_float(row["predicted_incidence_per_100k"])
        ),
        observed_incidence_per_100k=_round(
            _parse_float(row["observed_incidence_per_100k"])
        ),
        incidence_residual_per_100k=_round(
            _parse_float(row["incidence_residual_per_100k"])
        ),
        absolute_incidence_error_per_100k=_round(
            _parse_float(row["absolute_incidence_error_per_100k"])
        ),
        interval_calibration_weight=1.0,
        point_correction_allowed=False,
        permitted_use=PERMITTED_USE,
        prohibited_use=PROHIBITED_USE,
        forecast_assumption_flags=row["forecast_assumption_flags"],
        observed_quality_flags=row["observed_quality_flags"],
        source_diagnostic_flags=row["diagnostic_flags"],
        anchor_assumption_flags=ANCHOR_ASSUMPTION_FLAGS,
    )


def _parse_int(value: str) -> int:
    return int(float(str(value).strip()))


def _parse_float(value: str) -> float:
    return float(str(value).strip())


def _round(value: float) -> float:
    return round(float(value), 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
