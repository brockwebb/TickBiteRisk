from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


class ModelDiagnosticsInputError(ValueError):
    """Raised when model diagnostics inputs are invalid."""


@dataclass(frozen=True)
class SurveillanceRegimeResidual:
    model_name: str
    model_family: str
    test_year: int
    county_fips: str
    county_name: str
    surveillance_regime: str
    actual_incidence_per_100k: float
    predicted_incidence_per_100k: float
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    actual_cases: int
    predicted_cases: float
    residual_cases: float
    absolute_error_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class SurveillanceRegimeSummary:
    model_name: str
    model_family: str
    surveillance_regime: str
    test_year: int | None
    n_predictions: int
    mean_residual_incidence_per_100k: float
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    mean_residual_cases: float
    mae_cases: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelDiagnosticsResult:
    surveillance_residuals: list[SurveillanceRegimeResidual]
    surveillance_summary: list[SurveillanceRegimeSummary]
    regional_hotspot_summary: list[dict[str, object]]
    regional_capacity_intervals: list[dict[str, object]]


REQUIRED_PREDICTION_COLUMNS = [
    "model_name",
    "model_family",
    "test_year",
    "county_fips",
    "county_name",
    "actual_incidence_per_100k",
    "predicted_incidence_per_100k",
    "actual_cases",
    "predicted_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]


def build_model_diagnostics(
    predictions_path: Path,
    intervals_path: Path | None = None,
) -> ModelDiagnosticsResult:
    del intervals_path
    prediction_rows = _read_prediction_rows(predictions_path)
    residuals = [_build_residual(row) for row in prediction_rows]
    return ModelDiagnosticsResult(
        surveillance_residuals=sorted(
            residuals,
            key=lambda row: (
                row.model_name,
                row.surveillance_regime,
                row.test_year,
                row.county_fips,
            ),
        ),
        surveillance_summary=_build_summary(residuals),
        regional_hotspot_summary=[],
        regional_capacity_intervals=[],
    )


def _read_prediction_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = [
            column for column in REQUIRED_PREDICTION_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ModelDiagnosticsInputError(
                "model comparison predictions missing required column(s): "
                + ", ".join(missing_columns)
            )
        return list(reader)


def _build_residual(row: dict[str, str]) -> SurveillanceRegimeResidual:
    test_year = _parse_int(row["test_year"], "test_year")
    actual_incidence = _parse_float(
        row["actual_incidence_per_100k"],
        "actual_incidence_per_100k",
    )
    predicted_incidence = _parse_float(
        row["predicted_incidence_per_100k"],
        "predicted_incidence_per_100k",
    )
    actual_cases = _parse_int(row["actual_cases"], "actual_cases")
    predicted_cases = _parse_float(row["predicted_cases"], "predicted_cases")
    residual_incidence = _round(actual_incidence - predicted_incidence)
    residual_cases = _round(actual_cases - predicted_cases)
    quality_flags = row.get("model_feature_quality_flags", "")
    return SurveillanceRegimeResidual(
        model_name=row["model_name"],
        model_family=row["model_family"],
        test_year=test_year,
        county_fips=row["county_fips"].zfill(5),
        county_name=row["county_name"],
        surveillance_regime=_classify_surveillance_regime(quality_flags, test_year),
        actual_incidence_per_100k=_round(actual_incidence),
        predicted_incidence_per_100k=_round(predicted_incidence),
        residual_incidence_per_100k=residual_incidence,
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        actual_cases=actual_cases,
        predicted_cases=_round(predicted_cases),
        residual_cases=residual_cases,
        absolute_error_cases=_round(abs(residual_cases)),
        model_feature_quality_flags=quality_flags,
        comparison_assumption_flags=row.get("comparison_assumption_flags", ""),
    )


def _classify_surveillance_regime(quality_flags: str, test_year: int) -> str:
    flags = _split_flags(quality_flags)
    if "mdh_probable_only_2024" in flags:
        return "mdh_probable_only_2024"
    if "covid_reporting_disruption" in flags or test_year == 2020:
        return "covid_reporting_disruption"
    if "lyme_case_definition_change" in flags or test_year >= 2022:
        return "case_definition_change_2022_plus"
    if test_year < 2020:
        return "pre_2020_baseline"
    return "other_surveillance_regime"


def _build_summary(
    residuals: list[SurveillanceRegimeResidual],
) -> list[SurveillanceRegimeSummary]:
    grouped: dict[
        tuple[str, str, str, int | None],
        list[SurveillanceRegimeResidual],
    ] = {}
    for row in residuals:
        yearly_key = (
            row.model_name,
            row.model_family,
            row.surveillance_regime,
            row.test_year,
        )
        overall_key = (
            row.model_name,
            row.model_family,
            row.surveillance_regime,
            None,
        )
        grouped.setdefault(yearly_key, []).append(row)
        grouped.setdefault(overall_key, []).append(row)

    return [
        _summarize_group(rows, key)
        for key, rows in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0],
                item[0][2],
                item[0][3] is None,
                item[0][3] or 0,
            ),
        )
    ]


def _summarize_group(
    rows: list[SurveillanceRegimeResidual],
    key: tuple[str, str, str, int | None],
) -> SurveillanceRegimeSummary:
    model_name, model_family, surveillance_regime, test_year = key
    residual_incidence = [row.residual_incidence_per_100k for row in rows]
    residual_cases = [row.residual_cases for row in rows]
    assumption_flags = sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.comparison_assumption_flags)
            if flag
        }
    )
    return SurveillanceRegimeSummary(
        model_name=model_name,
        model_family=model_family,
        surveillance_regime=surveillance_regime,
        test_year=test_year,
        n_predictions=len(rows),
        mean_residual_incidence_per_100k=_round(mean(residual_incidence)),
        mae_incidence_per_100k=_round(mean(abs(value) for value in residual_incidence)),
        rmse_incidence_per_100k=_round(
            math.sqrt(mean(value * value for value in residual_incidence))
        ),
        mean_residual_cases=_round(mean(residual_cases)),
        mae_cases=_round(mean(abs(value) for value in residual_cases)),
        comparison_assumption_flags=",".join(assumption_flags),
    )


def _split_flags(value: str) -> set[str]:
    return {flag.strip() for flag in value.split(",") if flag.strip()}


def _parse_int(value: str, column: str) -> int:
    try:
        return int(float(value))
    except ValueError as exc:
        raise ModelDiagnosticsInputError(f"invalid integer in {column}: {value}") from exc


def _parse_float(value: str, column: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ModelDiagnosticsInputError(f"invalid number in {column}: {value}") from exc


def _round(value: float) -> float:
    return round(value, 6)
