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
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
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
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
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
class RegionalHotspotSummary:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
    test_year: int
    region_id: str
    region_name: str
    n_counties: int
    actual_total_cases: int
    predicted_total_cases: float
    residual_cases: float
    absolute_error_cases: float
    actual_incidence_per_100k_mean: float
    predicted_incidence_per_100k_mean: float
    spearman_rank_correlation: float | None
    top3_hit_count: int
    top5_hit_count: int
    county_share_mae: float
    predicted_case_hhi: float
    actual_case_hhi: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalCapacityInterval:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
    test_year: int
    region_id: str
    region_name: str
    interval_method: str
    n_counties: int
    lower_80_cases: float
    median_cases: float
    upper_80_cases: float
    lower_95_cases: float
    upper_95_cases: float
    actual_cases: int
    covered_80: bool
    covered_95: bool
    comparison_assumption_flags: str


MATERIAL_RESIDUAL_INCIDENCE_PER_100K = 10.0
REPORTING_BREAK_REGIMES = {
    "covid_reporting_disruption",
    "case_definition_change_2022_plus",
    "mdh_probable_only_2024",
}


@dataclass(frozen=True)
class ForecastUpdateAudit:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    source_file_sha256: str
    source_vintage: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    target_definition: str
    evaluation_mode: str
    update_mode: str
    surveillance_regime: str
    predicted_incidence_per_100k: float
    predicted_cases: float
    lower_80_incidence_per_100k: float | None
    median_incidence_per_100k: float | None
    upper_80_incidence_per_100k: float | None
    lower_95_incidence_per_100k: float | None
    upper_95_incidence_per_100k: float | None
    interval_available: bool
    covered_80: bool | None
    covered_95: bool | None
    actual_incidence_per_100k: float
    actual_cases: int
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    signed_percent_error: float | None
    update_direction: str
    update_interpretation: str
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastUpdateSummary:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    source_file_sha256: str
    source_vintage: str
    evaluation_mode: str
    surveillance_regime: str
    forecast_year: int | None
    n_updates: int
    mean_residual_incidence_per_100k: float
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    interval_available_count: int
    covered_80_count: int
    covered_95_count: int
    forecast_signal_count: int
    surveillance_regime_signal_count: int
    ambiguous_signal_count: int
    insufficient_signal_count: int
    forecast_signal_share: float
    surveillance_regime_signal_share: float
    ambiguous_signal_share: float
    insufficient_signal_share: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastCalibrationSummary:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    source_file_sha256: str
    source_vintage: str
    evaluation_mode: str
    surveillance_regime: str
    forecast_year: int | None
    calibration_method: str
    n_updates: int
    total_actual_cases: int
    total_predicted_cases: float
    actual_to_predicted_case_ratio: float | None
    mean_actual_incidence_per_100k: float
    mean_predicted_incidence_per_100k: float
    additive_residual_offset_incidence_per_100k: float
    actual_to_predicted_incidence_ratio: float | None
    mae_incidence_per_100k: float
    recommended_update_use: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelDiagnosticsResult:
    surveillance_residuals: list[SurveillanceRegimeResidual]
    surveillance_summary: list[SurveillanceRegimeSummary]
    regional_hotspot_summary: list[RegionalHotspotSummary]
    regional_capacity_intervals: list[RegionalCapacityInterval]
    forecast_update_audit: list[ForecastUpdateAudit]
    forecast_update_summary: list[ForecastUpdateSummary]
    forecast_calibration_summary: list[ForecastCalibrationSummary]


REQUIRED_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "train_end_year",
    "county_fips",
    "county_name",
    "actual_incidence_per_100k",
    "predicted_incidence_per_100k",
    "actual_cases",
    "actual_population",
    "predicted_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
]

REQUIRED_INTERVAL_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "county_fips",
    "test_year",
    "interval_method",
    "lower_80_incidence_per_100k",
    "median_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "covered_80",
    "covered_95",
    "comparison_assumption_flags",
]


def build_model_diagnostics(
    predictions_path: Path,
    intervals_path: Path | None = None,
    *,
    as_of_date: str = "unspecified",
    data_cutoff_date: str = "unspecified",
    source_vintage: str | None = None,
) -> ModelDiagnosticsResult:
    prediction_rows = _read_prediction_rows(predictions_path)
    residuals = [_build_residual(row) for row in prediction_rows]
    interval_rows = _read_interval_rows(intervals_path) if intervals_path else []
    interval_by_key = {_county_model_key(row): row for row in interval_rows}
    forecast_update_audit = _build_forecast_update_audit(
        prediction_rows,
        interval_by_key,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=source_vintage,
    )
    return ModelDiagnosticsResult(
        surveillance_residuals=sorted(
            residuals,
            key=lambda row: (
                row.run_id,
                row.model_name,
                row.feature_profile,
                row.evaluation_mode,
                row.source_file_sha256,
                row.surveillance_regime,
                row.test_year,
                row.county_fips,
            ),
        ),
        surveillance_summary=_build_summary(residuals),
        regional_hotspot_summary=_build_regional_hotspot_summary(residuals),
        regional_capacity_intervals=_build_regional_capacity_intervals(
            prediction_rows,
            interval_rows,
        ),
        forecast_update_audit=forecast_update_audit,
        forecast_update_summary=_build_forecast_update_summary(forecast_update_audit),
        forecast_calibration_summary=_build_forecast_calibration_summary(
            forecast_update_audit
        ),
    )


def _read_prediction_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ModelDiagnosticsInputError(
                "model comparison predictions CSV has no header"
            )
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
        run_id=row["run_id"],
        model_name=row["model_name"],
        model_family=row["model_family"],
        feature_profile=row["feature_profile"],
        evaluation_mode=row["evaluation_mode"],
        source_file_sha256=row["source_file_sha256"],
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


def _build_forecast_update_audit(
    prediction_rows: list[dict[str, str]],
    interval_by_key: dict[
        tuple[str, str, str, str, str, str, int, str],
        dict[str, str],
    ],
    *,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> list[ForecastUpdateAudit]:
    rows = [
        _forecast_update_audit_row(
            row,
            interval_by_key.get(_county_model_key(row)),
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
        )
        for row in prediction_rows
    ]
    return sorted(
        rows,
        key=lambda row: (
            row.run_id,
            row.model_name,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
            row.forecast_year,
            row.county_fips,
        ),
    )


def _forecast_update_audit_row(
    row: dict[str, str],
    interval_row: dict[str, str] | None,
    *,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> ForecastUpdateAudit:
    forecast_year = _parse_int(row["test_year"], "test_year")
    forecast_origin_year = _parse_int(row["train_end_year"], "train_end_year")
    effective_source_vintage = (
        row["source_file_sha256"] if source_vintage is None else source_vintage
    )
    actual_incidence = _parse_float(
        row["actual_incidence_per_100k"],
        "actual_incidence_per_100k",
    )
    predicted_incidence = _parse_float(
        row["predicted_incidence_per_100k"],
        "predicted_incidence_per_100k",
    )
    predicted_cases = _parse_float(row["predicted_cases"], "predicted_cases")
    actual_cases = _parse_int(row["actual_cases"], "actual_cases")
    residual_incidence = _round(actual_incidence - predicted_incidence)
    quality_flags = row.get("model_feature_quality_flags", "")
    surveillance_regime = _classify_surveillance_regime(quality_flags, forecast_year)
    lower_80 = _optional_interval_float(interval_row, "lower_80_incidence_per_100k")
    median = _optional_interval_float(interval_row, "median_incidence_per_100k")
    upper_80 = _optional_interval_float(interval_row, "upper_80_incidence_per_100k")
    lower_95 = _optional_interval_float(interval_row, "lower_95_incidence_per_100k")
    upper_95 = _optional_interval_float(interval_row, "upper_95_incidence_per_100k")
    covered_80 = _optional_interval_bool(interval_row, "covered_80")
    covered_95 = _optional_interval_bool(interval_row, "covered_95")
    signed_percent_error = (
        None
        if abs(predicted_incidence) < 1e-12
        else _round(residual_incidence / predicted_incidence * 100)
    )
    interpretation = _classify_update_interpretation(
        surveillance_regime=surveillance_regime,
        residual_incidence=residual_incidence,
        covered_95=covered_95,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=effective_source_vintage,
    )
    return ForecastUpdateAudit(
        run_id=row["run_id"],
        model_name=row["model_name"],
        model_family=row["model_family"],
        feature_profile=row["feature_profile"],
        source_file_sha256=row["source_file_sha256"],
        source_vintage=effective_source_vintage,
        county_fips=row["county_fips"].zfill(5),
        county_name=row["county_name"],
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        target_definition=row.get("target_definition", "lyme_incidence_per_100k"),
        evaluation_mode=row["evaluation_mode"],
        update_mode="post_observed_outcome",
        surveillance_regime=surveillance_regime,
        predicted_incidence_per_100k=_round(predicted_incidence),
        predicted_cases=_round(predicted_cases),
        lower_80_incidence_per_100k=lower_80,
        median_incidence_per_100k=median,
        upper_80_incidence_per_100k=upper_80,
        lower_95_incidence_per_100k=lower_95,
        upper_95_incidence_per_100k=upper_95,
        interval_available=interval_row is not None,
        covered_80=covered_80,
        covered_95=covered_95,
        actual_incidence_per_100k=_round(actual_incidence),
        actual_cases=actual_cases,
        residual_incidence_per_100k=residual_incidence,
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        signed_percent_error=signed_percent_error,
        update_direction=_update_direction(residual_incidence),
        update_interpretation=interpretation,
        model_feature_quality_flags=quality_flags,
        comparison_assumption_flags=row.get("comparison_assumption_flags", ""),
    )


def _build_forecast_update_summary(
    audit_rows: list[ForecastUpdateAudit],
) -> list[ForecastUpdateSummary]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str, str, int | None],
        list[ForecastUpdateAudit],
    ] = {}
    for row in audit_rows:
        yearly_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            row.forecast_year,
        )
        overall_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            None,
        )
        grouped.setdefault(yearly_key, []).append(row)
        grouped.setdefault(overall_key, []).append(row)
    return [
        _forecast_update_summary_row(rows, key)
        for key, rows in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0],
                item[0][1],
                item[0][3],
                item[0][4],
                item[0][5],
                item[0][6],
                item[0][7],
                item[0][8] is None,
                item[0][8] or 0,
            ),
        )
    ]


def _forecast_update_summary_row(
    rows: list[ForecastUpdateAudit],
    key: tuple[str, str, str, str, str, str, str, str, int | None],
) -> ForecastUpdateSummary:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        source_file_sha256,
        source_vintage,
        evaluation_mode,
        surveillance_regime,
        forecast_year,
    ) = key
    residuals = [row.residual_incidence_per_100k for row in rows]
    assumption_flags = sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.comparison_assumption_flags)
            if flag
        }
    )
    return ForecastUpdateSummary(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        source_file_sha256=source_file_sha256,
        source_vintage=source_vintage,
        evaluation_mode=evaluation_mode,
        surveillance_regime=surveillance_regime,
        forecast_year=forecast_year,
        n_updates=len(rows),
        mean_residual_incidence_per_100k=_round(mean(residuals)),
        mae_incidence_per_100k=_round(mean(abs(value) for value in residuals)),
        rmse_incidence_per_100k=_round(
            math.sqrt(mean(value * value for value in residuals))
        ),
        interval_available_count=sum(row.interval_available for row in rows),
        covered_80_count=sum(row.covered_80 is True for row in rows),
        covered_95_count=sum(row.covered_95 is True for row in rows),
        forecast_signal_count=sum(
            row.update_interpretation == "forecast_signal" for row in rows
        ),
        surveillance_regime_signal_count=sum(
            row.update_interpretation == "surveillance_regime_signal"
            for row in rows
        ),
        ambiguous_signal_count=sum(
            row.update_interpretation == "ambiguous_signal" for row in rows
        ),
        insufficient_signal_count=sum(
            row.update_interpretation == "insufficient_signal" for row in rows
        ),
        forecast_signal_share=_interpretation_share(rows, "forecast_signal"),
        surveillance_regime_signal_share=_interpretation_share(
            rows,
            "surveillance_regime_signal",
        ),
        ambiguous_signal_share=_interpretation_share(rows, "ambiguous_signal"),
        insufficient_signal_share=_interpretation_share(rows, "insufficient_signal"),
        comparison_assumption_flags=",".join(assumption_flags),
    )


def _build_forecast_calibration_summary(
    audit_rows: list[ForecastUpdateAudit],
) -> list[ForecastCalibrationSummary]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str, str, int | None],
        list[ForecastUpdateAudit],
    ] = {}
    for row in audit_rows:
        yearly_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            row.forecast_year,
        )
        overall_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.source_file_sha256,
            row.source_vintage,
            row.evaluation_mode,
            row.surveillance_regime,
            None,
        )
        grouped.setdefault(yearly_key, []).append(row)
        grouped.setdefault(overall_key, []).append(row)
    return [
        _forecast_calibration_summary_row(rows, key)
        for key, rows in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][0],
                item[0][1],
                item[0][3],
                item[0][4],
                item[0][5],
                item[0][6],
                item[0][7],
                item[0][8] is None,
                item[0][8] or 0,
            ),
        )
    ]


def _forecast_calibration_summary_row(
    rows: list[ForecastUpdateAudit],
    key: tuple[str, str, str, str, str, str, str, str, int | None],
) -> ForecastCalibrationSummary:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        source_file_sha256,
        source_vintage,
        evaluation_mode,
        surveillance_regime,
        forecast_year,
    ) = key
    actual_cases = sum(row.actual_cases for row in rows)
    predicted_cases = sum(row.predicted_cases for row in rows)
    actual_incidence_values = [row.actual_incidence_per_100k for row in rows]
    predicted_incidence_values = [row.predicted_incidence_per_100k for row in rows]
    residual_incidence_values = [row.residual_incidence_per_100k for row in rows]
    assumption_flags = sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.comparison_assumption_flags)
            if flag
        }
    )
    mean_actual_incidence = _round(mean(actual_incidence_values))
    mean_predicted_incidence = _round(mean(predicted_incidence_values))
    return ForecastCalibrationSummary(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        source_file_sha256=source_file_sha256,
        source_vintage=source_vintage,
        evaluation_mode=evaluation_mode,
        surveillance_regime=surveillance_regime,
        forecast_year=forecast_year,
        calibration_method="empirical_observed_to_predicted_ratio",
        n_updates=len(rows),
        total_actual_cases=actual_cases,
        total_predicted_cases=_round(predicted_cases),
        actual_to_predicted_case_ratio=_safe_ratio(actual_cases, predicted_cases),
        mean_actual_incidence_per_100k=mean_actual_incidence,
        mean_predicted_incidence_per_100k=mean_predicted_incidence,
        additive_residual_offset_incidence_per_100k=_round(
            mean(residual_incidence_values)
        ),
        actual_to_predicted_incidence_ratio=_safe_ratio(
            mean_actual_incidence,
            mean_predicted_incidence,
        ),
        mae_incidence_per_100k=_round(
            mean(abs(value) for value in residual_incidence_values)
        ),
        recommended_update_use="diagnostic_calibration_prior_only",
        comparison_assumption_flags=",".join(assumption_flags),
    )


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if abs(denominator) < 1e-12:
        return None
    return _round(numerator / denominator)


def _interpretation_share(
    rows: list[ForecastUpdateAudit],
    interpretation: str,
) -> float:
    if not rows:
        return 0.0
    return _round(
        sum(row.update_interpretation == interpretation for row in rows) / len(rows)
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
        tuple[str, str, str, str, str, str, str, int | None],
        list[SurveillanceRegimeResidual],
    ] = {}
    for row in residuals:
        yearly_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
            row.surveillance_regime,
            row.test_year,
        )
        overall_key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
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
                item[0][1],
                item[0][3],
                item[0][4],
                item[0][5],
                item[0][6],
                item[0][7] is None,
                item[0][7] or 0,
            ),
        )
    ]


def _build_regional_hotspot_summary(
    residuals: list[SurveillanceRegimeResidual],
) -> list[RegionalHotspotSummary]:
    grouped: dict[
        tuple[str, str, str, str, str, str, int, str],
        list[SurveillanceRegimeResidual],
    ] = {}
    for row in residuals:
        region_id, _region_name = _state_region(row.county_fips)
        key = (
            row.run_id,
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
            row.test_year,
            region_id,
        )
        grouped.setdefault(key, []).append(row)

    return [
        _summarize_regional_hotspot(rows, key)
        for key, rows in sorted(grouped.items())
    ]


def _summarize_regional_hotspot(
    rows: list[SurveillanceRegimeResidual],
    key: tuple[str, str, str, str, str, str, int, str],
) -> RegionalHotspotSummary:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        evaluation_mode,
        source_file_sha256,
        test_year,
        region_id,
    ) = key
    region_name = f"State {region_id.removeprefix('state_')}"
    actual_total = sum(row.actual_cases for row in rows)
    predicted_total = sum(row.predicted_cases for row in rows)
    residual_cases = actual_total - predicted_total
    assumption_flags = sorted(
        {
            flag
            for row in rows
            for flag in _split_flags(row.comparison_assumption_flags)
            if flag
        }
    )
    return RegionalHotspotSummary(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        evaluation_mode=evaluation_mode,
        source_file_sha256=source_file_sha256,
        test_year=test_year,
        region_id=region_id,
        region_name=region_name,
        n_counties=len(rows),
        actual_total_cases=actual_total,
        predicted_total_cases=_round(predicted_total),
        residual_cases=_round(residual_cases),
        absolute_error_cases=_round(abs(residual_cases)),
        actual_incidence_per_100k_mean=_round(
            mean(row.actual_incidence_per_100k for row in rows)
        ),
        predicted_incidence_per_100k_mean=_round(
            mean(row.predicted_incidence_per_100k for row in rows)
        ),
        spearman_rank_correlation=_spearman_rank_correlation(
            [row.actual_cases for row in rows],
            [row.predicted_cases for row in rows],
        ),
        top3_hit_count=_top_hit_count(rows, 3),
        top5_hit_count=_top_hit_count(rows, 5),
        county_share_mae=_round(
            mean(
                abs(predicted_share - actual_share)
                for predicted_share, actual_share in zip(
                    _shares([row.predicted_cases for row in rows]),
                    _shares([row.actual_cases for row in rows]),
                    strict=True,
                )
            )
        ),
        predicted_case_hhi=_round(_hhi([row.predicted_cases for row in rows])),
        actual_case_hhi=_round(_hhi([row.actual_cases for row in rows])),
        comparison_assumption_flags=",".join(assumption_flags),
    )


def _build_regional_capacity_intervals(
    prediction_rows: list[dict[str, str]],
    interval_rows: list[dict[str, str]],
) -> list[RegionalCapacityInterval]:
    population_by_key = {
        _county_model_key(row): _parse_int(row["actual_population"], "actual_population")
        for row in prediction_rows
    }
    actual_cases_by_key = {
        _county_model_key(row): _parse_int(row["actual_cases"], "actual_cases")
        for row in prediction_rows
    }
    grouped: dict[
        tuple[str, str, str, str, str, str, int, str],
        list[dict[str, str]],
    ] = {}
    for row in interval_rows:
        county_fips = row["county_fips"].zfill(5)
        region_id, _region_name = _state_region(county_fips)
        key = (
            row["run_id"],
            row["model_name"],
            row["model_family"],
            row["feature_profile"],
            row["evaluation_mode"],
            row["source_file_sha256"],
            _parse_int(row["test_year"], "test_year"),
            region_id,
        )
        grouped.setdefault(key, []).append(row)

    return [
        _summarize_regional_capacity_interval(
            rows,
            key,
            population_by_key,
            actual_cases_by_key,
        )
        for key, rows in sorted(grouped.items())
    ]


def _summarize_regional_capacity_interval(
    rows: list[dict[str, str]],
    key: tuple[str, str, str, str, str, str, int, str],
    population_by_key: dict[tuple[str, str, str, str, str, str, int, str], int],
    actual_cases_by_key: dict[tuple[str, str, str, str, str, str, int, str], int],
) -> RegionalCapacityInterval:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        evaluation_mode,
        source_file_sha256,
        test_year,
        region_id,
    ) = key
    region_name = f"State {region_id.removeprefix('state_')}"
    lower_80 = median = upper_80 = lower_95 = upper_95 = 0.0
    actual_cases = 0
    assumption_flags: set[str] = set()
    n_counties = 0
    interval_methods = {row["interval_method"] for row in rows}
    if len(interval_methods) > 1:
        raise ModelDiagnosticsInputError(
            "model interval regional group has mixed interval_method values "
            f"for run_id={run_id} model_name={model_name} test_year={test_year} "
            f"region_id={region_id}: {', '.join(sorted(interval_methods))}"
        )
    for row in rows:
        model_key = _county_model_key(row)
        population = population_by_key.get(model_key)
        if population is None:
            raise ModelDiagnosticsInputError(
                "model interval row has no matching prediction row for "
                f"run_id={row['run_id']} model_name={row['model_name']} "
                f"test_year={row['test_year']} county_fips={row['county_fips'].zfill(5)}"
            )
        n_counties += 1
        actual_cases += actual_cases_by_key[model_key]
        lower_80 += _incidence_to_cases(row, "lower_80_incidence_per_100k", population)
        median += _incidence_to_cases(row, "median_incidence_per_100k", population)
        upper_80 += _incidence_to_cases(row, "upper_80_incidence_per_100k", population)
        lower_95 += _incidence_to_cases(row, "lower_95_incidence_per_100k", population)
        upper_95 += _incidence_to_cases(row, "upper_95_incidence_per_100k", population)
        _parse_bool(row["covered_80"], "covered_80")
        _parse_bool(row["covered_95"], "covered_95")
        assumption_flags.update(_split_flags(row.get("comparison_assumption_flags", "")))

    return RegionalCapacityInterval(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        evaluation_mode=evaluation_mode,
        source_file_sha256=source_file_sha256,
        test_year=test_year,
        region_id=region_id,
        region_name=region_name,
        interval_method="summed_county_intervals",
        n_counties=n_counties,
        lower_80_cases=_round(lower_80),
        median_cases=_round(median),
        upper_80_cases=_round(upper_80),
        lower_95_cases=_round(lower_95),
        upper_95_cases=_round(upper_95),
        actual_cases=actual_cases,
        covered_80=n_counties > 0 and lower_80 <= actual_cases <= upper_80,
        covered_95=n_counties > 0 and lower_95 <= actual_cases <= upper_95,
        comparison_assumption_flags=",".join(sorted(assumption_flags)),
    )


def _summarize_group(
    rows: list[SurveillanceRegimeResidual],
    key: tuple[str, str, str, str, str, str, str, int | None],
) -> SurveillanceRegimeSummary:
    (
        run_id,
        model_name,
        model_family,
        feature_profile,
        evaluation_mode,
        source_file_sha256,
        surveillance_regime,
        test_year,
    ) = key
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
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        evaluation_mode=evaluation_mode,
        source_file_sha256=source_file_sha256,
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


def _optional_interval_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _round(_parse_float(row[column], column))


def _optional_interval_bool(row: dict[str, str] | None, column: str) -> bool | None:
    if row is None:
        return None
    return _parse_bool(row[column], column)


def _update_direction(residual_incidence: float) -> str:
    if residual_incidence > 0:
        return "observed_above_forecast"
    if residual_incidence < 0:
        return "observed_below_forecast"
    return "observed_matches_forecast"


def _classify_update_interpretation(
    *,
    surveillance_regime: str,
    residual_incidence: float,
    covered_95: bool | None,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str | None,
) -> str:
    if as_of_date == "unspecified" or data_cutoff_date == "unspecified":
        return "insufficient_signal"
    if source_vintage in {None, "", "unspecified"}:
        return "insufficient_signal"
    if covered_95 is None:
        return "insufficient_signal"
    interval_break = covered_95 is False
    material_residual = abs(residual_incidence) >= MATERIAL_RESIDUAL_INCIDENCE_PER_100K
    if not interval_break and not material_residual:
        return "ambiguous_signal"
    if surveillance_regime in REPORTING_BREAK_REGIMES:
        return "surveillance_regime_signal"
    return "forecast_signal"


def _read_interval_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ModelDiagnosticsInputError("model comparison intervals CSV has no header")
        missing_columns = [
            column for column in REQUIRED_INTERVAL_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            raise ModelDiagnosticsInputError(
                "model comparison intervals missing required column(s): "
                + ", ".join(missing_columns)
            )
        return list(reader)


def _state_region(county_fips: str) -> tuple[str, str]:
    state_fips = county_fips[:2]
    return f"state_{state_fips}", f"State {state_fips}"


def _county_model_key(
    row: dict[str, str],
) -> tuple[str, str, str, str, str, str, int, str]:
    return (
        row["run_id"],
        row["model_name"],
        row["model_family"],
        row["feature_profile"],
        row["evaluation_mode"],
        row["source_file_sha256"],
        _parse_int(row["test_year"], "test_year"),
        row["county_fips"].zfill(5),
    )


def _incidence_to_cases(row: dict[str, str], column: str, population: int) -> float:
    return _parse_float(row[column], column) / 100000 * population


def _top_hit_count(rows: list[SurveillanceRegimeResidual], limit: int) -> int:
    count = min(limit, len(rows))
    actual_top = {
        row.county_fips
        for row in sorted(rows, key=lambda row: (-row.actual_cases, row.county_fips))[
            :count
        ]
    }
    predicted_top = {
        row.county_fips
        for row in sorted(rows, key=lambda row: (-row.predicted_cases, row.county_fips))[
            :count
        ]
    }
    return len(actual_top & predicted_top)


def _shares(values: list[float | int]) -> list[float]:
    total = sum(values)
    if total == 0:
        return [0.0 for _value in values]
    return [value / total for value in values]


def _hhi(values: list[float | int]) -> float:
    return sum(share * share for share in _shares(values))


def _spearman_rank_correlation(
    actual_values: list[float | int],
    predicted_values: list[float | int],
) -> float | None:
    if (
        len(actual_values) < 2
        or len(set(actual_values)) < 2
        or len(set(predicted_values)) < 2
    ):
        return None
    actual_ranks = _ranks(actual_values)
    predicted_ranks = _ranks(predicted_values)
    actual_mean = mean(actual_ranks)
    predicted_mean = mean(predicted_ranks)
    actual_delta = [rank - actual_mean for rank in actual_ranks]
    predicted_delta = [rank - predicted_mean for rank in predicted_ranks]
    denominator = math.sqrt(
        sum(value * value for value in actual_delta)
        * sum(value * value for value in predicted_delta)
    )
    if denominator == 0:
        return None
    return _round(
        sum(
            actual * predicted
            for actual, predicted in zip(actual_delta, predicted_delta, strict=True)
        )
        / denominator
    )


def _ranks(values: list[float | int]) -> list[float]:
    sorted_values = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0 for _value in values]
    position = 0
    while position < len(sorted_values):
        end = position + 1
        while (
            end < len(sorted_values)
            and sorted_values[end][0] == sorted_values[position][0]
        ):
            end += 1
        average_rank = (position + 1 + end) / 2
        for _value, original_index in sorted_values[position:end]:
            ranks[original_index] = average_rank
        position = end
    return ranks


def _parse_bool(value: str | None, column: str) -> bool:
    if value is None or not value.strip():
        raise ModelDiagnosticsInputError(f"missing required boolean value in {column}")
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ModelDiagnosticsInputError(f"invalid boolean in {column}: {value}")


def _parse_int(value: str | None, column: str) -> int:
    value = _require_numeric_value(value, column)
    try:
        return int(float(value))
    except ValueError as exc:
        raise ModelDiagnosticsInputError(f"invalid integer in {column}: {value}") from exc


def _parse_float(value: str | None, column: str) -> float:
    value = _require_numeric_value(value, column)
    try:
        return float(value)
    except ValueError as exc:
        raise ModelDiagnosticsInputError(f"invalid number in {column}: {value}") from exc


def _require_numeric_value(value: str | None, column: str) -> str:
    if value is None or not value.strip():
        raise ModelDiagnosticsInputError(
            f"missing required numeric value in {column}"
        )
    return value


def _round(value: float) -> float:
    return round(value, 6)
