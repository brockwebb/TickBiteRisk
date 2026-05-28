from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from tickbiterisk.modeling.model_diagnostics import _classify_surveillance_regime


CALIBRATION_METHOD = "forecast_safe_shrunken_case_ratio"
RECOMMENDED_UPDATE_USE = "research_backtest_only"
REQUIRED_PREDICTION_COLUMNS = {
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "county_fips",
    "county_name",
    "actual_incidence_per_100k",
    "predicted_incidence_per_100k",
    "actual_cases",
    "predicted_cases",
    "model_feature_quality_flags",
    "comparison_assumption_flags",
}


class ForecastCalibrationBacktestInputError(ValueError):
    """Raised when forecast calibration backtest inputs are invalid."""


@dataclass(frozen=True)
class ForecastCalibrationBacktestRun:
    run_id: str
    predictions_path: str
    predictions_sha256: str
    start_year: int
    end_year: int
    min_calibration_updates: int
    calibration_prior_strength: float
    calibration_method: str
    model_names: str
    n_input_rows: int
    n_predictions: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastCalibrationBacktestPrediction:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    forecast_year: int
    surveillance_regime: str
    calibration_scope: str
    n_calibration_updates: int
    raw_actual_to_predicted_case_ratio: float | None
    shrunken_case_multiplier: float
    original_predicted_incidence_per_100k: float
    calibrated_predicted_incidence_per_100k: float
    actual_incidence_per_100k: float
    original_residual_incidence_per_100k: float
    calibrated_residual_incidence_per_100k: float
    original_absolute_error_incidence_per_100k: float
    calibrated_absolute_error_incidence_per_100k: float
    original_predicted_cases: float
    calibrated_predicted_cases: float
    actual_cases: int
    original_absolute_error_cases: float
    calibrated_absolute_error_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastCalibrationBacktestMetric:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
    aggregation: str
    surveillance_regime: str | None
    forecast_year: int | None
    n_predictions: int
    original_mae_incidence_per_100k: float
    calibrated_mae_incidence_per_100k: float
    mae_improvement_incidence_per_100k: float
    original_rmse_incidence_per_100k: float
    calibrated_rmse_incidence_per_100k: float
    original_mae_cases: float
    calibrated_mae_cases: float
    mae_improvement_cases: float
    recommended_update_use: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastCalibrationBacktestResult:
    run_id: str
    run: ForecastCalibrationBacktestRun
    predictions: list[ForecastCalibrationBacktestPrediction]
    metrics: list[ForecastCalibrationBacktestMetric]


@dataclass(frozen=True)
class _PredictionRow:
    run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    forecast_year: int
    surveillance_regime: str
    actual_incidence_per_100k: float
    predicted_incidence_per_100k: float
    actual_cases: int
    predicted_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class _Calibration:
    scope: str
    n_updates: int
    raw_ratio: float | None
    multiplier: float


def build_forecast_calibration_backtest(
    *,
    predictions_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_calibration_updates: int = 5,
    calibration_prior_strength: float = 5.0,
) -> ForecastCalibrationBacktestResult:
    if min_calibration_updates < 1:
        raise ForecastCalibrationBacktestInputError(
            "min_calibration_updates must be at least 1"
        )
    if not math.isfinite(calibration_prior_strength) or calibration_prior_strength < 0:
        raise ForecastCalibrationBacktestInputError(
            "calibration_prior_strength must be finite and non-negative"
        )
    input_rows = _read_prediction_rows(predictions_path)
    if not input_rows:
        raise ForecastCalibrationBacktestInputError("predictions CSV has no input rows")
    input_min_year = min(row.forecast_year for row in input_rows)
    input_max_year = max(row.forecast_year for row in input_rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise ForecastCalibrationBacktestInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise ForecastCalibrationBacktestInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise ForecastCalibrationBacktestInputError(
            "start_year must be less than or equal to end_year"
        )

    predictions_sha256 = _sha256_file(predictions_path)
    run_id = (
        f"forecast_calibration_backtest_start{start_year}_end{resolved_end_year}_"
        f"minupdates{min_calibration_updates}_prior{_slug_float(calibration_prior_strength)}"
    )
    predictions = []
    for row in sorted(input_rows, key=lambda item: (item.forecast_year, item.county_fips)):
        if not (start_year <= row.forecast_year <= resolved_end_year):
            continue
        calibration = _calibration_for_row(
            row=row,
            rows=input_rows,
            min_calibration_updates=min_calibration_updates,
            calibration_prior_strength=calibration_prior_strength,
        )
        predictions.append(
            _prediction_row(
                run_id=run_id,
                row=row,
                calibration=calibration,
            )
        )

    predictions = sorted(
        predictions,
        key=lambda row: (
            row.forecast_year,
            row.model_name,
            row.feature_profile,
            row.county_fips,
        ),
    )
    metrics = _metric_rows(run_id, predictions)
    run = ForecastCalibrationBacktestRun(
        run_id=run_id,
        predictions_path=str(predictions_path),
        predictions_sha256=predictions_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_calibration_updates=min_calibration_updates,
        calibration_prior_strength=calibration_prior_strength,
        calibration_method=CALIBRATION_METHOD,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        n_input_rows=len(input_rows),
        n_predictions=len(predictions),
        comparison_assumption_flags=_combined_flags(
            *(row.comparison_assumption_flags for row in predictions)
        ),
    )
    return ForecastCalibrationBacktestResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        metrics=metrics,
    )


def _read_prediction_rows(path: Path) -> list[_PredictionRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ForecastCalibrationBacktestInputError(
                "model comparison predictions CSV has no header"
            )
        missing = REQUIRED_PREDICTION_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ForecastCalibrationBacktestInputError(
                "model comparison predictions missing required column(s): "
                + ", ".join(sorted(missing))
            )
        rows = []
        for row in reader:
            forecast_year = _parse_int(row["test_year"], "test_year")
            quality_flags = row.get("model_feature_quality_flags", "")
            rows.append(
                _PredictionRow(
                    run_id=row["run_id"],
                    model_name=row["model_name"],
                    model_family=row["model_family"],
                    feature_profile=row["feature_profile"],
                    evaluation_mode=row["evaluation_mode"],
                    source_file_sha256=row["source_file_sha256"],
                    county_fips=row["county_fips"].zfill(5),
                    county_name=row["county_name"],
                    forecast_year=forecast_year,
                    surveillance_regime=_classify_surveillance_regime(
                        quality_flags,
                        forecast_year,
                    ),
                    actual_incidence_per_100k=_parse_float(
                        row["actual_incidence_per_100k"],
                        "actual_incidence_per_100k",
                    ),
                    predicted_incidence_per_100k=_parse_float(
                        row["predicted_incidence_per_100k"],
                        "predicted_incidence_per_100k",
                    ),
                    actual_cases=_parse_int(row["actual_cases"], "actual_cases"),
                    predicted_cases=_parse_float(
                        row["predicted_cases"],
                        "predicted_cases",
                    ),
                    model_feature_quality_flags=quality_flags,
                    comparison_assumption_flags=row.get(
                        "comparison_assumption_flags",
                        "",
                    ),
                )
            )
        return rows


def _calibration_for_row(
    *,
    row: _PredictionRow,
    rows: list[_PredictionRow],
    min_calibration_updates: int,
    calibration_prior_strength: float,
) -> _Calibration:
    same_model_prior = [
        prior
        for prior in rows
        if _same_model_key(prior, row) and prior.forecast_year < row.forecast_year
    ]
    same_regime_prior = [
        prior
        for prior in same_model_prior
        if prior.surveillance_regime == row.surveillance_regime
    ]
    if (
        len(same_regime_prior) >= min_calibration_updates
        and _has_nonzero_predicted_cases(same_regime_prior)
    ):
        return _calibration_from_prior(
            same_regime_prior,
            scope="same_regime_prior_years",
            calibration_prior_strength=calibration_prior_strength,
        )
    if (
        len(same_model_prior) >= min_calibration_updates
        and _has_nonzero_predicted_cases(same_model_prior)
    ):
        return _calibration_from_prior(
            same_model_prior,
            scope="all_regime_prior_years",
            calibration_prior_strength=calibration_prior_strength,
        )
    if len(same_model_prior) >= min_calibration_updates:
        return _Calibration(
            scope="uncalibrated_zero_prior_prediction",
            n_updates=len(same_model_prior),
            raw_ratio=None,
            multiplier=1.0,
        )
    return _Calibration(
        scope="uncalibrated_insufficient_prior",
        n_updates=len(same_model_prior),
        raw_ratio=None,
        multiplier=1.0,
    )


def _calibration_from_prior(
    prior_rows: list[_PredictionRow],
    *,
    scope: str,
    calibration_prior_strength: float,
) -> _Calibration:
    predicted_cases = sum(row.predicted_cases for row in prior_rows)
    if abs(predicted_cases) < 1e-12:
        return _Calibration(
            scope="uncalibrated_zero_prior_prediction",
            n_updates=len(prior_rows),
            raw_ratio=None,
            multiplier=1.0,
        )
    actual_cases = sum(row.actual_cases for row in prior_rows)
    raw_ratio = actual_cases / predicted_cases
    multiplier = (
        (raw_ratio * len(prior_rows)) + calibration_prior_strength
    ) / (len(prior_rows) + calibration_prior_strength)
    return _Calibration(
        scope=scope,
        n_updates=len(prior_rows),
        raw_ratio=_round(raw_ratio),
        multiplier=multiplier,
    )


def _has_nonzero_predicted_cases(rows: list[_PredictionRow]) -> bool:
    return abs(sum(row.predicted_cases for row in rows)) >= 1e-12


def _prediction_row(
    *,
    run_id: str,
    row: _PredictionRow,
    calibration: _Calibration,
) -> ForecastCalibrationBacktestPrediction:
    calibrated_predicted_cases = _round(row.predicted_cases * calibration.multiplier)
    calibrated_predicted_incidence = _round(
        row.predicted_incidence_per_100k * calibration.multiplier
    )
    original_residual_incidence = _round(
        row.actual_incidence_per_100k - row.predicted_incidence_per_100k
    )
    calibrated_residual_incidence = _round(
        row.actual_incidence_per_100k - calibrated_predicted_incidence
    )
    return ForecastCalibrationBacktestPrediction(
        run_id=run_id,
        model_name=row.model_name,
        model_family=row.model_family,
        feature_profile=row.feature_profile,
        evaluation_mode=row.evaluation_mode,
        source_file_sha256=row.source_file_sha256,
        county_fips=row.county_fips,
        county_name=row.county_name,
        forecast_year=row.forecast_year,
        surveillance_regime=row.surveillance_regime,
        calibration_scope=calibration.scope,
        n_calibration_updates=calibration.n_updates,
        raw_actual_to_predicted_case_ratio=calibration.raw_ratio,
        shrunken_case_multiplier=_round(calibration.multiplier),
        original_predicted_incidence_per_100k=_round(
            row.predicted_incidence_per_100k
        ),
        calibrated_predicted_incidence_per_100k=calibrated_predicted_incidence,
        actual_incidence_per_100k=_round(row.actual_incidence_per_100k),
        original_residual_incidence_per_100k=original_residual_incidence,
        calibrated_residual_incidence_per_100k=calibrated_residual_incidence,
        original_absolute_error_incidence_per_100k=_round(
            abs(original_residual_incidence)
        ),
        calibrated_absolute_error_incidence_per_100k=_round(
            abs(calibrated_residual_incidence)
        ),
        original_predicted_cases=_round(row.predicted_cases),
        calibrated_predicted_cases=calibrated_predicted_cases,
        actual_cases=row.actual_cases,
        original_absolute_error_cases=_round(abs(row.actual_cases - row.predicted_cases)),
        calibrated_absolute_error_cases=_round(
            abs(row.actual_cases - calibrated_predicted_cases)
        ),
        model_feature_quality_flags=row.model_feature_quality_flags,
        comparison_assumption_flags=_combined_flags(
            row.comparison_assumption_flags,
            "forecast_safe_calibration_backtest",
            "not_public_default",
        ),
    )


def _metric_rows(
    run_id: str,
    predictions: list[ForecastCalibrationBacktestPrediction],
) -> list[ForecastCalibrationBacktestMetric]:
    metrics = []
    for key, rows in sorted(_metric_groups(predictions).items()):
        metrics.append(_metric_row(run_id=run_id, rows=rows, key=key))
    return metrics


def _metric_groups(
    predictions: list[ForecastCalibrationBacktestPrediction],
) -> dict[
    tuple[str, str, str, str, str, str, str | None, int | None],
    list[ForecastCalibrationBacktestPrediction],
]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str | None, int | None],
        list[ForecastCalibrationBacktestPrediction],
    ] = {}
    for row in predictions:
        base = (
            row.model_name,
            row.model_family,
            row.feature_profile,
            row.evaluation_mode,
            row.source_file_sha256,
        )
        grouped.setdefault((*base, "overall", None, None), []).append(row)
        grouped.setdefault(
            (*base, "surveillance_regime", row.surveillance_regime, None),
            [],
        ).append(row)
        grouped.setdefault((*base, "year", None, row.forecast_year), []).append(row)
    return grouped


def _metric_row(
    *,
    run_id: str,
    rows: list[ForecastCalibrationBacktestPrediction],
    key: tuple[str, str, str, str, str, str, str | None, int | None],
) -> ForecastCalibrationBacktestMetric:
    (
        model_name,
        model_family,
        feature_profile,
        evaluation_mode,
        source_file_sha256,
        aggregation,
        surveillance_regime,
        forecast_year,
    ) = key
    original_incidence_errors = [
        row.original_absolute_error_incidence_per_100k for row in rows
    ]
    calibrated_incidence_errors = [
        row.calibrated_absolute_error_incidence_per_100k for row in rows
    ]
    original_case_errors = [row.original_absolute_error_cases for row in rows]
    calibrated_case_errors = [row.calibrated_absolute_error_cases for row in rows]
    original_mae_incidence = _round(mean(original_incidence_errors))
    calibrated_mae_incidence = _round(mean(calibrated_incidence_errors))
    original_mae_cases = _round(mean(original_case_errors))
    calibrated_mae_cases = _round(mean(calibrated_case_errors))
    return ForecastCalibrationBacktestMetric(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        feature_profile=feature_profile,
        evaluation_mode=evaluation_mode,
        source_file_sha256=source_file_sha256,
        aggregation=aggregation,
        surveillance_regime=surveillance_regime,
        forecast_year=forecast_year,
        n_predictions=len(rows),
        original_mae_incidence_per_100k=original_mae_incidence,
        calibrated_mae_incidence_per_100k=calibrated_mae_incidence,
        mae_improvement_incidence_per_100k=_round(
            original_mae_incidence - calibrated_mae_incidence
        ),
        original_rmse_incidence_per_100k=_round(
            math.sqrt(
                mean(
                    row.original_residual_incidence_per_100k
                    * row.original_residual_incidence_per_100k
                    for row in rows
                )
            )
        ),
        calibrated_rmse_incidence_per_100k=_round(
            math.sqrt(
                mean(
                    row.calibrated_residual_incidence_per_100k
                    * row.calibrated_residual_incidence_per_100k
                    for row in rows
                )
            )
        ),
        original_mae_cases=original_mae_cases,
        calibrated_mae_cases=calibrated_mae_cases,
        mae_improvement_cases=_round(original_mae_cases - calibrated_mae_cases),
        recommended_update_use=RECOMMENDED_UPDATE_USE,
        comparison_assumption_flags=_combined_flags(
            *(row.comparison_assumption_flags for row in rows)
        ),
    )


def _same_model_key(left: _PredictionRow, right: _PredictionRow) -> bool:
    return (
        left.run_id == right.run_id
        and left.model_name == right.model_name
        and left.model_family == right.model_family
        and left.feature_profile == right.feature_profile
        and left.evaluation_mode == right.evaluation_mode
        and left.source_file_sha256 == right.source_file_sha256
    )


def _combined_flags(*flag_groups: str) -> str:
    flags = []
    for group in flag_groups:
        flags.extend(flag for flag in group.split(",") if flag)
    return ",".join(dict.fromkeys(flags))


def _parse_int(value: str, column: str) -> int:
    if value == "":
        raise ForecastCalibrationBacktestInputError(
            f"missing required numeric value in {column}"
        )
    try:
        number = float(value)
    except ValueError as exc:
        raise ForecastCalibrationBacktestInputError(
            f"invalid numeric value in {column}: {value}"
        ) from exc
    if not math.isfinite(number):
        raise ForecastCalibrationBacktestInputError(
            f"non-finite numeric value in {column}: {value}"
        )
    return int(number)


def _parse_float(value: str, column: str) -> float:
    if value == "":
        raise ForecastCalibrationBacktestInputError(
            f"missing required numeric value in {column}"
        )
    try:
        number = float(value)
    except ValueError as exc:
        raise ForecastCalibrationBacktestInputError(
            f"invalid numeric value in {column}: {value}"
        ) from exc
    if not math.isfinite(number):
        raise ForecastCalibrationBacktestInputError(
            f"non-finite numeric value in {column}: {value}"
        )
    return number


def _round(value: float) -> float:
    return round(value, 6)


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
