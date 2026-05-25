from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


BACKTEST_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "intervention_history_unmodeled,"
    "surveillance_reporting_sensitive"
)


class BacktestInputError(ValueError):
    """Raised when backtest configuration is outside the input panel."""


@dataclass(frozen=True)
class ModelBacktestRun:
    run_id: str
    model_features_path: str
    model_features_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    lookback_years: int
    model_names: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    weather_mode: str
    n_feature_rows: int
    n_predictions: int
    backtest_assumption_flags: str


@dataclass(frozen=True)
class ModelBacktestPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    train_year_count: int
    actual_cases: int
    actual_population: int
    actual_incidence_per_100k: float
    predicted_cases: float
    predicted_incidence_per_100k: float
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    residual_cases: float
    absolute_error_cases: float
    model_feature_quality_flags: str
    backtest_assumption_flags: str


@dataclass(frozen=True)
class ModelBacktestMetric:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    aggregation: str
    test_year: int | None
    n_predictions: int
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    mean_bias_incidence_per_100k: float
    mae_cases: float
    rmse_cases: float
    pearson_correlation: float | None
    backtest_assumption_flags: str


@dataclass(frozen=True)
class ModelBacktestResult:
    run_id: str
    run: ModelBacktestRun
    predictions: list[ModelBacktestPrediction]
    metrics: list[ModelBacktestMetric]


@dataclass(frozen=True)
class _FeatureRow:
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    population: int
    incidence_per_100k: float
    model_feature_quality_flags: str


def run_baseline_backtests(
    *,
    model_features_path: Path,
    start_year: int,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 5,
) -> ModelBacktestResult:
    if min_train_years < 1:
        raise BacktestInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise BacktestInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )

    rows = _read_feature_rows(model_features_path)
    if not rows:
        raise BacktestInputError("model feature matrix has no usable rows")
    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise BacktestInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if end_year is not None and (
        end_year < input_min_year or end_year > input_max_year
    ):
        raise BacktestInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else max(row.year for row in rows)
    if start_year > resolved_end_year:
        raise BacktestInputError("start_year must be less than or equal to end_year")
    by_county = _group_by_county(rows)
    by_year = _group_by_year(rows)
    run_id = (
        f"baseline_backtest_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_lookback{lookback_years}"
    )
    source_file_sha256 = _sha256_file(model_features_path)
    predictions = []
    for row in sorted(rows, key=lambda item: (item.year, item.county_fips)):
        if row.year < start_year:
            continue
        if row.year > resolved_end_year:
            continue
        county_history = [
            prior
            for prior in by_county[row.county_fips]
            if prior.year < row.year
        ][-lookback_years:]
        if len(county_history) < min_train_years:
            continue
        train_start_year = min(prior.year for prior in county_history)
        train_end_year = max(prior.year for prior in county_history)
        model_predictions = _predict_baselines(
            row=row,
            county_history=county_history,
            state_history=by_year,
            lookback_years=lookback_years,
        )
        for model_name, predicted_incidence in model_predictions.items():
            predictions.append(
                _prediction_row(
                    run_id=run_id,
                    model_name=model_name,
                    row=row,
                    predicted_incidence=predicted_incidence,
                    source_file_sha256=source_file_sha256,
                    train_start_year=train_start_year,
                    train_end_year=train_end_year,
                    train_year_count=len(county_history),
                )
            )
    metrics = _metric_rows(run_id, predictions)
    run = ModelBacktestRun(
        run_id=run_id,
        model_features_path=str(model_features_path),
        model_features_sha256=source_file_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        target_definition="lyme_incidence_per_100k",
        feature_set="historical_outcome_baselines",
        evaluation_mode="forecast_prior_year",
        weather_mode="not_used_by_baseline",
        n_feature_rows=len(rows),
        n_predictions=len(predictions),
        backtest_assumption_flags=BACKTEST_ASSUMPTION_FLAGS,
    )
    return ModelBacktestResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        metrics=metrics,
    )


def _read_feature_rows(path: Path) -> list[_FeatureRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            _FeatureRow(
                county_fips=str(row["county_fips"]).zfill(5),
                county_name=str(row["county_name"]),
                year=int(row["year"]),
                total_cases=_parse_int(row["total_cases"]),
                population=_parse_int(row["population"]),
                incidence_per_100k=_parse_float(row["lyme_incidence_per_100k"]),
                model_feature_quality_flags=str(
                    row.get("model_feature_quality_flags", "")
                ),
            )
            for row in reader
            if _parse_int(row["population"]) > 0
        ]


def _group_by_county(rows: list[_FeatureRow]) -> dict[str, list[_FeatureRow]]:
    grouped: dict[str, list[_FeatureRow]] = {}
    for row in rows:
        grouped.setdefault(row.county_fips, []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: row.year)
        for county_fips, county_rows in grouped.items()
    }


def _group_by_year(rows: list[_FeatureRow]) -> dict[int, list[_FeatureRow]]:
    grouped: dict[int, list[_FeatureRow]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(row)
    return grouped


def _predict_baselines(
    *,
    row: _FeatureRow,
    county_history: list[_FeatureRow],
    state_history: dict[int, list[_FeatureRow]],
    lookback_years: int,
) -> dict[str, float]:
    trailing_mean = mean(prior.incidence_per_100k for prior in county_history)
    state_multiplier = _state_trend_multiplier(
        test_year=row.year,
        state_history=state_history,
        lookback_years=lookback_years,
    )
    state_adjusted = trailing_mean * state_multiplier
    predictions = {
        "county_trailing_mean_incidence": trailing_mean,
        "state_trend_adjusted_county_mean": state_adjusted,
    }
    prior_year_row = next(
        (prior for prior in county_history if prior.year == row.year - 1),
        None,
    )
    if prior_year_row is not None:
        prior_year = prior_year_row.incidence_per_100k
        predictions["prior_year_incidence"] = prior_year
        predictions["linear_blend_baseline"] = mean([prior_year, trailing_mean])
    return predictions


def _state_trend_multiplier(
    *,
    test_year: int,
    state_history: dict[int, list[_FeatureRow]],
    lookback_years: int,
) -> float:
    years = [
        year
        for year in sorted(state_history)
        if year < test_year
    ][-lookback_years:]
    if not years:
        return 1.0
    state_rates = [_state_incidence(state_history[year]) for year in years]
    baseline = mean(state_rates)
    if baseline == 0:
        return 1.0
    return state_rates[-1] / baseline


def _state_incidence(rows: list[_FeatureRow]) -> float:
    total_cases = sum(row.total_cases for row in rows)
    total_population = sum(row.population for row in rows)
    if total_population <= 0:
        return 0.0
    return total_cases / total_population * 100000


def _prediction_row(
    *,
    run_id: str,
    model_name: str,
    row: _FeatureRow,
    predicted_incidence: float,
    source_file_sha256: str,
    train_start_year: int,
    train_end_year: int,
    train_year_count: int,
) -> ModelBacktestPrediction:
    predicted_incidence = max(predicted_incidence, 0.0)
    predicted_cases = predicted_incidence / 100000 * row.population
    residual_incidence = row.incidence_per_100k - predicted_incidence
    residual_cases = row.total_cases - predicted_cases
    return ModelBacktestPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family="baseline",
        target_definition="lyme_incidence_per_100k",
        feature_set="historical_outcome_baselines",
        evaluation_mode="forecast_prior_year",
        weather_mode="not_used_by_baseline",
        source_file_sha256=source_file_sha256,
        county_fips=row.county_fips,
        county_name=row.county_name,
        test_year=row.year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=train_year_count,
        actual_cases=row.total_cases,
        actual_population=row.population,
        actual_incidence_per_100k=_round(row.incidence_per_100k),
        predicted_cases=_round(predicted_cases),
        predicted_incidence_per_100k=_round(predicted_incidence),
        residual_incidence_per_100k=_round(residual_incidence),
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        residual_cases=_round(residual_cases),
        absolute_error_cases=_round(abs(residual_cases)),
        model_feature_quality_flags=row.model_feature_quality_flags,
        backtest_assumption_flags=BACKTEST_ASSUMPTION_FLAGS,
    )


def _metric_rows(
    run_id: str,
    predictions: list[ModelBacktestPrediction],
) -> list[ModelBacktestMetric]:
    rows = []
    model_names = sorted({row.model_name for row in predictions})
    for model_name in model_names:
        model_rows = [row for row in predictions if row.model_name == model_name]
        for test_year in sorted({row.test_year for row in model_rows}):
            rows.append(
                _metric_row(
                    run_id=run_id,
                    model_name=model_name,
                    aggregation="test_year",
                    test_year=test_year,
                    predictions=[
                        row for row in model_rows if row.test_year == test_year
                    ],
                )
            )
        rows.append(
            _metric_row(
                run_id=run_id,
                model_name=model_name,
                aggregation="overall",
                test_year=None,
                predictions=model_rows,
            )
        )
    return rows


def _metric_row(
    *,
    run_id: str,
    model_name: str,
    aggregation: str,
    test_year: int | None,
    predictions: list[ModelBacktestPrediction],
) -> ModelBacktestMetric:
    incidence_errors = [row.residual_incidence_per_100k for row in predictions]
    case_errors = [row.residual_cases for row in predictions]
    actual = [row.actual_incidence_per_100k for row in predictions]
    predicted = [row.predicted_incidence_per_100k for row in predictions]
    return ModelBacktestMetric(
        run_id=run_id,
        model_name=model_name,
        model_family="baseline",
        target_definition="lyme_incidence_per_100k",
        feature_set="historical_outcome_baselines",
        evaluation_mode="forecast_prior_year",
        weather_mode=predictions[0].weather_mode,
        source_file_sha256=predictions[0].source_file_sha256,
        aggregation=aggregation,
        test_year=test_year,
        n_predictions=len(predictions),
        mae_incidence_per_100k=_round(mean(abs(value) for value in incidence_errors)),
        rmse_incidence_per_100k=_round(_rmse(incidence_errors)),
        mean_bias_incidence_per_100k=_round(mean(incidence_errors)),
        mae_cases=_round(mean(abs(value) for value in case_errors)),
        rmse_cases=_round(_rmse(case_errors)),
        pearson_correlation=_pearson(actual, predicted),
        backtest_assumption_flags=BACKTEST_ASSUMPTION_FLAGS,
    )


def _rmse(values: list[float]) -> float:
    return math.sqrt(mean(value * value for value in values))


def _pearson(actual: list[float], predicted: list[float]) -> float | None:
    if len(actual) < 2 or len(predicted) < 2:
        return None
    actual_mean = mean(actual)
    predicted_mean = mean(predicted)
    numerator = sum(
        (actual_value - actual_mean) * (predicted_value - predicted_mean)
        for actual_value, predicted_value in zip(actual, predicted)
    )
    actual_denominator = math.sqrt(
        sum((actual_value - actual_mean) ** 2 for actual_value in actual)
    )
    predicted_denominator = math.sqrt(
        sum((predicted_value - predicted_mean) ** 2 for predicted_value in predicted)
    )
    if actual_denominator == 0 or predicted_denominator == 0:
        return None
    return _round(numerator / (actual_denominator * predicted_denominator))


def _parse_int(value: str) -> int:
    number = float(str(value).strip().replace(",", ""))
    if not number.is_integer():
        raise ValueError(f"Expected integer-like value, got {value!r}")
    return int(number)


def _parse_float(value: str) -> float:
    return float(str(value).strip().replace(",", ""))


def _round(value: float) -> float:
    return round(value, 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
