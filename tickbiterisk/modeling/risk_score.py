from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path


RISK_SCORE_FEATURE_FLAGS = (
    "relative_seasonal_baseline,"
    "static_seasonality_prior,"
    "not_weather_adjusted"
)
LAGGED_OUTCOME_MODEL_NAMES = {
    "latest_observed_incidence",
    "prior_year_incidence",
    "trailing_mean_incidence",
    "linear_blend_baseline",
    "empirical_bayes_shrinkage",
}
LAGGED_OUTCOME_FEATURE_PROFILES = {
    "",
    "lagged_outcome",
    "lagged_outcome_blend",
    "lagged_outcome_with_shrinkage",
    "latest_observed_lag",
    "trailing_county_history",
    "latest_observed_trailing_blend",
    "county_history_with_state_shrinkage",
}
LAGGED_OUTCOME_PUBLIC_MODEL_FLAGS = {
    "covid_reporting_disruption",
    "lyme_case_definition_change",
    "mdh_probable_only_2024",
    "state_source_not_cdc_public_use",
    "missing_population",
}


class RiskScoreInputError(ValueError):
    """Raised when risk-score inputs cannot produce rows."""


@dataclass(frozen=True)
class SeasonalRiskScore:
    source_prediction_run_id: str
    source_prediction_sha256: str
    source_seasonality_sha256: str
    source_prediction_interval_sha256: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    weather_mode: str
    county_fips: str
    county_name: str
    year: int
    forecast_origin_year: int | None
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    mmwr_week: int
    period_label: str
    predicted_annual_incidence_per_100k: float
    predicted_annual_cases: float
    annual_interval_method: str
    annual_interval_available: bool
    seasonal_mean_share: float
    seasonal_lower_80_share: float
    seasonal_upper_80_share: float
    seasonal_lower_95_share: float
    seasonal_upper_95_share: float
    predicted_weekly_incidence_per_100k: float
    lower_80_weekly_incidence_per_100k: float
    upper_80_weekly_incidence_per_100k: float
    lower_95_weekly_incidence_per_100k: float
    upper_95_weekly_incidence_per_100k: float
    predicted_weekly_cases: float
    benchmark_quantile: float
    headroom_multiplier: float
    score_denominator: float
    risk_score_raw: float
    risk_score: int
    risk_category: str
    seasonality_source_id: str
    model_feature_quality_flags: str
    seasonality_feature_quality_flags: str
    feature_quality_flags: str
    backtest_assumption_flags: str


@dataclass(frozen=True)
class RiskScoreScale:
    model_name: str
    grain: str
    target_definition: str
    seasonality_source_id: str
    benchmark_quantile: float
    headroom_multiplier: float
    benchmark_weekly_incidence_per_100k: float
    score_denominator: float
    n_score_rows: int
    source_prediction_sha256: str
    source_seasonality_sha256: str
    source_prediction_interval_sha256: str
    scale_quality_flags: str


@dataclass(frozen=True)
class SeasonalRiskScoreResult:
    rows: list[SeasonalRiskScore]
    scale: RiskScoreScale
    source_prediction_sha256: str
    source_seasonality_sha256: str


@dataclass(frozen=True)
class _PredictionInput:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    county_fips: str
    county_name: str
    year: int
    forecast_origin_year: int | None
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    predicted_cases: float
    predicted_incidence_per_100k: float
    model_feature_quality_flags: str
    backtest_assumption_flags: str


@dataclass(frozen=True)
class _SeasonalityInput:
    source_id: str
    period: int
    period_label: str
    mean_share: float
    lower_80_share: float
    upper_80_share: float
    lower_95_share: float
    upper_95_share: float
    feature_quality_flags: str


@dataclass(frozen=True)
class _PredictionIntervalInput:
    source_forecast_run_id: str
    model_name: str
    county_fips: str
    forecast_year: int
    interval_method: str
    lower_80_incidence_per_100k: float
    median_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    interval_assumption_flags: str


def build_seasonal_risk_scores(
    *,
    predictions_path: Path,
    prediction_intervals_path: Path | None = None,
    seasonality_baseline_path: Path,
    model_name: str = "linear_blend_baseline",
    seasonality_source_id: str = "cdc_seasonality_week_2023",
    benchmark_quantile: float = 0.95,
    headroom_multiplier: float = 1.2,
) -> SeasonalRiskScoreResult:
    if benchmark_quantile <= 0 or benchmark_quantile > 1:
        raise RiskScoreInputError("benchmark_quantile must be greater than 0 and <= 1")
    if headroom_multiplier <= 0:
        raise RiskScoreInputError("headroom_multiplier must be greater than 0")

    prediction_sha256 = _sha256_file(predictions_path)
    prediction_interval_sha256 = (
        "" if prediction_intervals_path is None else _sha256_file(prediction_intervals_path)
    )
    seasonality_sha256 = _sha256_file(seasonality_baseline_path)
    predictions = [
        row
        for row in _read_predictions(predictions_path)
        if row.model_name == model_name
    ]
    if not predictions:
        raise RiskScoreInputError(
            f"No annual predictions found for model_name={model_name}"
        )
    prediction_intervals = (
        None
        if prediction_intervals_path is None
        else _read_prediction_intervals(prediction_intervals_path)
    )
    seasonality_rows = _read_weekly_lyme_seasonality(
        seasonality_baseline_path,
        seasonality_source_id=seasonality_source_id,
    )
    if not seasonality_rows:
        raise RiskScoreInputError(
            "No seasonality baseline rows found for "
            f"source_id={seasonality_source_id}, grain=mmwr_week"
        )

    pending_rows = []
    for prediction in predictions:
        prediction_interval = _prediction_interval_for(
            prediction,
            prediction_intervals,
        )
        for seasonality in seasonality_rows:
            weekly_incidence = (
                prediction.predicted_incidence_per_100k * seasonality.mean_share
            )
            pending_rows.append(
                (prediction, prediction_interval, seasonality, weekly_incidence)
            )
    benchmark = _nearest_rank(
        [weekly_incidence for _, _, _, weekly_incidence in pending_rows],
        benchmark_quantile,
    )
    denominator = benchmark * headroom_multiplier
    rows = [
        _risk_score_row(
            prediction=prediction,
            prediction_interval=prediction_interval,
            seasonality=seasonality,
            weekly_incidence=weekly_incidence,
            denominator=denominator,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
            prediction_sha256=prediction_sha256,
            prediction_interval_sha256=prediction_interval_sha256,
            seasonality_sha256=seasonality_sha256,
        )
        for prediction, prediction_interval, seasonality, weekly_incidence in pending_rows
    ]
    rows = sorted(rows, key=lambda row: (row.county_fips, row.year, row.mmwr_week))
    scale = RiskScoreScale(
        model_name=model_name,
        grain="mmwr_week",
        target_definition=_scale_target_definition(predictions),
        seasonality_source_id=seasonality_source_id,
        benchmark_quantile=benchmark_quantile,
        headroom_multiplier=headroom_multiplier,
        benchmark_weekly_incidence_per_100k=_round(benchmark),
        score_denominator=_round(denominator),
        n_score_rows=len(rows),
        source_prediction_sha256=prediction_sha256,
        source_seasonality_sha256=seasonality_sha256,
        source_prediction_interval_sha256=prediction_interval_sha256,
        scale_quality_flags=_scale_quality_flags(predictions),
    )
    return SeasonalRiskScoreResult(
        rows=rows,
        scale=scale,
        source_prediction_sha256=prediction_sha256,
        source_seasonality_sha256=seasonality_sha256,
    )


def _risk_score_row(
    *,
    prediction: _PredictionInput,
    prediction_interval: _PredictionIntervalInput | None,
    seasonality: _SeasonalityInput,
    weekly_incidence: float,
    denominator: float,
    benchmark_quantile: float,
    headroom_multiplier: float,
    prediction_sha256: str,
    prediction_interval_sha256: str,
    seasonality_sha256: str,
) -> SeasonalRiskScore:
    raw_score = 0.0 if denominator <= 0 else 10 * weekly_incidence / denominator
    score = _risk_score(raw_score)
    model_feature_quality_flags = _score_model_feature_quality_flags(prediction)
    annual_lower_80 = (
        prediction.predicted_incidence_per_100k
        if prediction_interval is None
        else prediction_interval.lower_80_incidence_per_100k
    )
    annual_upper_80 = (
        prediction.predicted_incidence_per_100k
        if prediction_interval is None
        else prediction_interval.upper_80_incidence_per_100k
    )
    annual_lower_95 = (
        prediction.predicted_incidence_per_100k
        if prediction_interval is None
        else prediction_interval.lower_95_incidence_per_100k
    )
    annual_upper_95 = (
        prediction.predicted_incidence_per_100k
        if prediction_interval is None
        else prediction_interval.upper_95_incidence_per_100k
    )
    return SeasonalRiskScore(
        source_prediction_run_id=prediction.run_id,
        source_prediction_sha256=prediction_sha256,
        source_seasonality_sha256=seasonality_sha256,
        source_prediction_interval_sha256=prediction_interval_sha256,
        model_name=prediction.model_name,
        model_family=prediction.model_family,
        target_definition=prediction.target_definition,
        feature_set=prediction.feature_set,
        evaluation_mode=prediction.evaluation_mode,
        weather_mode=prediction.weather_mode,
        county_fips=prediction.county_fips,
        county_name=prediction.county_name,
        year=prediction.year,
        forecast_origin_year=prediction.forecast_origin_year,
        as_of_date=prediction.as_of_date,
        data_cutoff_date=prediction.data_cutoff_date,
        source_vintage=prediction.source_vintage,
        update_mode=prediction.update_mode,
        mmwr_week=seasonality.period,
        period_label=seasonality.period_label,
        predicted_annual_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k
        ),
        predicted_annual_cases=_round(prediction.predicted_cases),
        annual_interval_method=(
            "" if prediction_interval is None else prediction_interval.interval_method
        ),
        annual_interval_available=prediction_interval is not None,
        seasonal_mean_share=_round(seasonality.mean_share),
        seasonal_lower_80_share=_round(seasonality.lower_80_share),
        seasonal_upper_80_share=_round(seasonality.upper_80_share),
        seasonal_lower_95_share=_round(seasonality.lower_95_share),
        seasonal_upper_95_share=_round(seasonality.upper_95_share),
        predicted_weekly_incidence_per_100k=_round(weekly_incidence),
        lower_80_weekly_incidence_per_100k=_round(
            annual_lower_80 * seasonality.lower_80_share
        ),
        upper_80_weekly_incidence_per_100k=_round(
            annual_upper_80 * seasonality.upper_80_share
        ),
        lower_95_weekly_incidence_per_100k=_round(
            annual_lower_95 * seasonality.lower_95_share
        ),
        upper_95_weekly_incidence_per_100k=_round(
            annual_upper_95 * seasonality.upper_95_share
        ),
        predicted_weekly_cases=_round(
            prediction.predicted_cases * seasonality.mean_share
        ),
        benchmark_quantile=benchmark_quantile,
        headroom_multiplier=headroom_multiplier,
        score_denominator=_round(denominator),
        risk_score_raw=_round(raw_score),
        risk_score=score,
        risk_category=_risk_category(score),
        seasonality_source_id=seasonality.source_id,
        model_feature_quality_flags=model_feature_quality_flags,
        seasonality_feature_quality_flags=seasonality.feature_quality_flags,
        feature_quality_flags=_join_flags(
            RISK_SCORE_FEATURE_FLAGS,
            model_feature_quality_flags,
            "annual_forecast_interval_applied" if prediction_interval else "",
            seasonality.feature_quality_flags,
        ),
        backtest_assumption_flags=_join_flags(
            prediction.backtest_assumption_flags,
            "" if prediction_interval is None else prediction_interval.interval_assumption_flags,
        ),
    )


def _read_predictions(path: Path) -> list[_PredictionInput]:
    required_columns = [
        "run_id",
        "model_name",
        "model_family",
        "target_definition",
        "feature_set",
        "evaluation_mode",
        "county_fips",
        "county_name",
        "predicted_incidence_per_100k",
    ]
    rows = _read_csv(
        path,
        required_columns=required_columns,
        one_of_columns=[("test_year", "forecast_year")],
    )
    return [
        _PredictionInput(
            run_id=row["run_id"],
            model_name=row["model_name"],
            model_family=row["model_family"],
            target_definition=row["target_definition"],
            feature_set=row["feature_set"],
            feature_profile=row.get("feature_profile", ""),
            evaluation_mode=row["evaluation_mode"],
            weather_mode=row.get("weather_mode", "") or _default_weather_mode(row),
            county_fips=str(row["county_fips"]).zfill(5),
            county_name=row["county_name"],
            year=_parse_prediction_year(row),
            forecast_origin_year=_parse_prediction_origin_year(row),
            as_of_date=row.get("as_of_date", "") or "unspecified",
            data_cutoff_date=row.get("data_cutoff_date", "") or "unspecified",
            source_vintage=(
                row.get("source_vintage", "")
                or row.get("source_file_sha256", "")
                or row.get("design_matrix_sha256", "")
                or "unspecified"
            ),
            update_mode=row.get("update_mode", "") or "pre_update",
            predicted_cases=_parse_float(
                row.get("predicted_cases", ""),
                "predicted_cases",
            ),
            predicted_incidence_per_100k=_parse_float(
                row["predicted_incidence_per_100k"],
                "predicted_incidence_per_100k",
            ),
            model_feature_quality_flags=row.get("model_feature_quality_flags", ""),
            backtest_assumption_flags=(
                row.get("backtest_assumption_flags", "")
                or row.get("comparison_assumption_flags", "")
                or row.get("forecast_assumption_flags", "")
            ),
        )
        for row in rows
    ]


def _read_prediction_intervals(path: Path) -> dict[tuple[str, str, str, int], _PredictionIntervalInput]:
    required_columns = [
        "source_forecast_run_id",
        "model_name",
        "county_fips",
        "forecast_year",
        "interval_method",
        "lower_80_incidence_per_100k",
        "median_incidence_per_100k",
        "upper_80_incidence_per_100k",
        "lower_95_incidence_per_100k",
        "upper_95_incidence_per_100k",
    ]
    rows = _read_csv(path, required_columns=required_columns)
    intervals = {}
    for row in rows:
        interval = _PredictionIntervalInput(
            source_forecast_run_id=row["source_forecast_run_id"],
            model_name=row["model_name"],
            county_fips=str(row["county_fips"]).zfill(5),
            forecast_year=_parse_int(row["forecast_year"], "forecast_year"),
            interval_method=row["interval_method"],
            lower_80_incidence_per_100k=_parse_float(
                row["lower_80_incidence_per_100k"],
                "lower_80_incidence_per_100k",
            ),
            median_incidence_per_100k=_parse_float(
                row["median_incidence_per_100k"],
                "median_incidence_per_100k",
            ),
            upper_80_incidence_per_100k=_parse_float(
                row["upper_80_incidence_per_100k"],
                "upper_80_incidence_per_100k",
            ),
            lower_95_incidence_per_100k=_parse_float(
                row["lower_95_incidence_per_100k"],
                "lower_95_incidence_per_100k",
            ),
            upper_95_incidence_per_100k=_parse_float(
                row["upper_95_incidence_per_100k"],
                "upper_95_incidence_per_100k",
            ),
            interval_assumption_flags=row.get("interval_assumption_flags", ""),
        )
        key = _prediction_interval_key(
            interval.source_forecast_run_id,
            interval.model_name,
            interval.county_fips,
            interval.forecast_year,
        )
        if key in intervals:
            raise RiskScoreInputError(
                "duplicate annual prediction interval row for "
                f"{interval.source_forecast_run_id}, {interval.model_name}, "
                f"{interval.county_fips}, {interval.forecast_year}"
            )
        intervals[key] = interval
    return intervals


def _prediction_interval_for(
    prediction: _PredictionInput,
    intervals: dict[tuple[str, str, str, int], _PredictionIntervalInput] | None,
) -> _PredictionIntervalInput | None:
    if intervals is None:
        return None
    key = _prediction_interval_key(
        prediction.run_id,
        prediction.model_name,
        prediction.county_fips,
        prediction.year,
    )
    interval = intervals.get(key)
    if interval is None:
        raise RiskScoreInputError(
            "missing annual prediction interval for "
            f"{prediction.run_id}, {prediction.model_name}, "
            f"{prediction.county_fips}, {prediction.year}"
        )
    return interval


def _prediction_interval_key(
    run_id: str,
    model_name: str,
    county_fips: str,
    year: int,
) -> tuple[str, str, str, int]:
    return (run_id, model_name, str(county_fips).zfill(5), int(year))


def _default_weather_mode(row: dict[str, str]) -> str:
    if row.get("evaluation_mode") == "regional_annual_forecast_no_observed_target":
        return "not_used_by_regional_annual_forecast"
    if "annual_forecast" in row.get("evaluation_mode", ""):
        return "not_used_by_annual_forecast"
    return "unspecified"


def _scale_target_definition(predictions: list[_PredictionInput]) -> str:
    target_definitions = {row.target_definition for row in predictions}
    if len(target_definitions) == 1:
        return next(iter(target_definitions))
    return "mixed_target_definitions"


def _scale_quality_flags(predictions: list[_PredictionInput]) -> str:
    if any(
        row.evaluation_mode == "regional_annual_forecast_no_observed_target"
        for row in predictions
    ):
        return "relative_to_regional_prediction_distribution,not_public_default"
    return "relative_to_maryland_prediction_distribution"


def _parse_prediction_year(row: dict[str, str]) -> int:
    if "test_year" in row:
        return _parse_int(row["test_year"], "test_year")
    return _parse_int(row.get("forecast_year", ""), "forecast_year")


def _parse_prediction_origin_year(row: dict[str, str]) -> int | None:
    value = (
        row.get("forecast_origin_year", "")
        or row.get("train_end_year", "")
    )
    if not value:
        return None
    return _parse_int(value, "forecast_origin_year")


def _score_model_feature_quality_flags(prediction: _PredictionInput) -> str:
    flags = _split_flags(prediction.model_feature_quality_flags)
    if (
        prediction.model_name in LAGGED_OUTCOME_MODEL_NAMES
        and prediction.feature_profile in LAGGED_OUTCOME_FEATURE_PROFILES
    ):
        flags = [
            flag
            for flag in flags
            if flag in LAGGED_OUTCOME_PUBLIC_MODEL_FLAGS
        ]
    return ",".join(flags)


def _read_weekly_lyme_seasonality(
    path: Path,
    *,
    seasonality_source_id: str,
) -> list[_SeasonalityInput]:
    required_columns = [
        "source_id",
        "disease",
        "grain",
        "period",
        "period_label",
        "mean_share",
        "lower_80_share",
        "upper_80_share",
        "lower_95_share",
        "upper_95_share",
    ]
    rows = []
    for row in _read_csv(path, required_columns=required_columns):
        if (
            row.get("source_id") != seasonality_source_id
            or row.get("disease") != "lyme"
            or row.get("grain") != "mmwr_week"
        ):
            continue
        rows.append(
            _SeasonalityInput(
                source_id=row["source_id"],
                period=_parse_int(row["period"], "period"),
                period_label=row["period_label"],
                mean_share=_parse_float(row["mean_share"], "mean_share"),
                lower_80_share=_parse_float(
                    row["lower_80_share"],
                    "lower_80_share",
                ),
                upper_80_share=_parse_float(
                    row["upper_80_share"],
                    "upper_80_share",
                ),
                lower_95_share=_parse_float(
                    row["lower_95_share"],
                    "lower_95_share",
                ),
                upper_95_share=_parse_float(
                    row["upper_95_share"],
                    "upper_95_share",
                ),
                feature_quality_flags=row.get("feature_quality_flags", ""),
            )
        )
    return sorted(rows, key=lambda row: row.period)


def _nearest_rank(values: list[float], probability: float) -> float:
    if not values:
        raise RiskScoreInputError("Cannot compute score benchmark for zero rows")
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def _risk_score(raw_score: float) -> int:
    return max(1, min(10, int(round(raw_score))))


def _risk_category(score: int) -> str:
    if score <= 2:
        return "very_low"
    if score <= 4:
        return "low"
    if score <= 6:
        return "moderate"
    if score <= 8:
        return "high"
    return "very_high"


def _join_flags(*values: str) -> str:
    flags = []
    for value in values:
        for flag in _split_flags(value):
            if flag not in flags:
                flags.append(flag)
    return ",".join(flags)


def _split_flags(value: str) -> list[str]:
    return [
        flag
        for raw_flag in str(value).split(",")
        if (flag := raw_flag.strip())
    ]


def _read_csv(
    path: Path,
    *,
    required_columns: list[str],
    one_of_columns: list[tuple[str, ...]] | None = None,
) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = [
            column for column in required_columns if column not in fieldnames
        ]
        for alternatives in one_of_columns or []:
            if not any(column in fieldnames for column in alternatives):
                missing_columns.append(" or ".join(alternatives))
        if missing_columns:
            raise RiskScoreInputError(
                "missing required risk score column(s): "
                f"{', '.join(missing_columns)}"
            )
        return list(reader)


def _parse_int(value: str, field_name: str) -> int:
    try:
        parsed = int(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise RiskScoreInputError(f"{field_name} must be an integer") from exc
    return parsed


def _parse_float(value: str, field_name: str) -> float:
    if value == "":
        return 0.0
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise RiskScoreInputError(f"{field_name} must be numeric") from exc


def _round(value: float) -> float:
    return round(value, 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
