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


class RiskScoreInputError(ValueError):
    """Raised when risk-score inputs cannot produce rows."""


@dataclass(frozen=True)
class SeasonalRiskScore:
    source_prediction_run_id: str
    source_prediction_sha256: str
    source_seasonality_sha256: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    weather_mode: str
    county_fips: str
    county_name: str
    year: int
    mmwr_week: int
    period_label: str
    predicted_annual_incidence_per_100k: float
    predicted_annual_cases: float
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
    evaluation_mode: str
    weather_mode: str
    county_fips: str
    county_name: str
    year: int
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


def build_seasonal_risk_scores(
    *,
    predictions_path: Path,
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
    seasonality_sha256 = _sha256_file(seasonality_baseline_path)
    predictions = [
        row
        for row in _read_predictions(predictions_path)
        if row.model_name == model_name
    ]
    if not predictions:
        raise RiskScoreInputError(
            f"No backtest predictions found for model_name={model_name}"
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
        for seasonality in seasonality_rows:
            weekly_incidence = (
                prediction.predicted_incidence_per_100k * seasonality.mean_share
            )
            pending_rows.append((prediction, seasonality, weekly_incidence))
    benchmark = _nearest_rank(
        [weekly_incidence for _, _, weekly_incidence in pending_rows],
        benchmark_quantile,
    )
    denominator = benchmark * headroom_multiplier
    rows = [
        _risk_score_row(
            prediction=prediction,
            seasonality=seasonality,
            weekly_incidence=weekly_incidence,
            denominator=denominator,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
            prediction_sha256=prediction_sha256,
            seasonality_sha256=seasonality_sha256,
        )
        for prediction, seasonality, weekly_incidence in pending_rows
    ]
    rows = sorted(rows, key=lambda row: (row.county_fips, row.year, row.mmwr_week))
    scale = RiskScoreScale(
        model_name=model_name,
        grain="mmwr_week",
        target_definition="lyme_incidence_per_100k",
        seasonality_source_id=seasonality_source_id,
        benchmark_quantile=benchmark_quantile,
        headroom_multiplier=headroom_multiplier,
        benchmark_weekly_incidence_per_100k=_round(benchmark),
        score_denominator=_round(denominator),
        n_score_rows=len(rows),
        source_prediction_sha256=prediction_sha256,
        source_seasonality_sha256=seasonality_sha256,
        scale_quality_flags="relative_to_maryland_backtest_distribution",
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
    seasonality: _SeasonalityInput,
    weekly_incidence: float,
    denominator: float,
    benchmark_quantile: float,
    headroom_multiplier: float,
    prediction_sha256: str,
    seasonality_sha256: str,
) -> SeasonalRiskScore:
    raw_score = 0.0 if denominator <= 0 else 10 * weekly_incidence / denominator
    score = _risk_score(raw_score)
    return SeasonalRiskScore(
        source_prediction_run_id=prediction.run_id,
        source_prediction_sha256=prediction_sha256,
        source_seasonality_sha256=seasonality_sha256,
        model_name=prediction.model_name,
        model_family=prediction.model_family,
        target_definition=prediction.target_definition,
        feature_set=prediction.feature_set,
        evaluation_mode=prediction.evaluation_mode,
        weather_mode=prediction.weather_mode,
        county_fips=prediction.county_fips,
        county_name=prediction.county_name,
        year=prediction.year,
        mmwr_week=seasonality.period,
        period_label=seasonality.period_label,
        predicted_annual_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k
        ),
        predicted_annual_cases=_round(prediction.predicted_cases),
        seasonal_mean_share=_round(seasonality.mean_share),
        seasonal_lower_80_share=_round(seasonality.lower_80_share),
        seasonal_upper_80_share=_round(seasonality.upper_80_share),
        seasonal_lower_95_share=_round(seasonality.lower_95_share),
        seasonal_upper_95_share=_round(seasonality.upper_95_share),
        predicted_weekly_incidence_per_100k=_round(weekly_incidence),
        lower_80_weekly_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k * seasonality.lower_80_share
        ),
        upper_80_weekly_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k * seasonality.upper_80_share
        ),
        lower_95_weekly_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k * seasonality.lower_95_share
        ),
        upper_95_weekly_incidence_per_100k=_round(
            prediction.predicted_incidence_per_100k * seasonality.upper_95_share
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
        model_feature_quality_flags=prediction.model_feature_quality_flags,
        seasonality_feature_quality_flags=seasonality.feature_quality_flags,
        feature_quality_flags=_join_flags(
            RISK_SCORE_FEATURE_FLAGS,
            prediction.model_feature_quality_flags,
            seasonality.feature_quality_flags,
        ),
        backtest_assumption_flags=prediction.backtest_assumption_flags,
    )


def _read_predictions(path: Path) -> list[_PredictionInput]:
    required_columns = [
        "run_id",
        "model_name",
        "model_family",
        "target_definition",
        "feature_set",
        "evaluation_mode",
        "weather_mode",
        "county_fips",
        "county_name",
        "test_year",
        "predicted_incidence_per_100k",
    ]
    rows = _read_csv(path, required_columns=required_columns)
    return [
            _PredictionInput(
                run_id=row["run_id"],
                model_name=row["model_name"],
                model_family=row["model_family"],
                target_definition=row["target_definition"],
                feature_set=row["feature_set"],
                evaluation_mode=row["evaluation_mode"],
                weather_mode=row["weather_mode"],
                county_fips=str(row["county_fips"]).zfill(5),
                county_name=row["county_name"],
                year=_parse_int(row["test_year"], "test_year"),
                predicted_cases=_parse_float(
                    row.get("predicted_cases", ""),
                    "predicted_cases",
                ),
                predicted_incidence_per_100k=_parse_float(
                    row["predicted_incidence_per_100k"],
                    "predicted_incidence_per_100k",
                ),
                model_feature_quality_flags=row.get(
                    "model_feature_quality_flags", ""
                ),
                backtest_assumption_flags=row.get("backtest_assumption_flags", ""),
            )
            for row in rows
    ]


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
        for flag in str(value).split(","):
            flag = flag.strip()
            if flag and flag not in flags:
                flags.append(flag)
    return ",".join(flags)


def _read_csv(path: Path, *, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = [
            column for column in required_columns if column not in fieldnames
        ]
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
