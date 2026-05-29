from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from tickbiterisk.modeling.model_diagnostics import _classify_surveillance_regime


BAYES_UPDATE_METHOD = "gamma_poisson_case_multiplier"
BAYES_INTERVAL_METHOD = "posterior_predictive_moment_normal_approximation"
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


class ForecastBayesianUpdateBacktestInputError(ValueError):
    """Raised when forecast Bayesian update inputs are invalid."""


@dataclass(frozen=True)
class ForecastBayesianUpdateBacktestRun:
    run_id: str
    predictions_path: str
    predictions_sha256: str
    start_year: int
    end_year: int
    min_prior_updates: int
    prior_strength_cases: float
    bayes_update_method: str
    interval_method: str
    model_names: str
    n_input_rows: int
    n_predictions: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastBayesianUpdateBacktestPrediction:
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
    update_scope: str
    n_prior_updates: int
    prior_actual_cases: int
    prior_predicted_cases: float
    posterior_alpha: float
    posterior_beta: float
    posterior_case_multiplier_mean: float
    posterior_case_multiplier_variance: float
    original_predicted_incidence_per_100k: float
    updated_predicted_incidence_per_100k: float
    actual_incidence_per_100k: float
    original_residual_incidence_per_100k: float
    updated_residual_incidence_per_100k: float
    original_absolute_error_incidence_per_100k: float
    updated_absolute_error_incidence_per_100k: float
    original_predicted_cases: float
    updated_predicted_cases: float
    lower_80_updated_cases: float
    upper_80_updated_cases: float
    lower_95_updated_cases: float
    upper_95_updated_cases: float
    actual_cases: int
    covered_80: bool
    covered_95: bool
    original_absolute_error_cases: float
    updated_absolute_error_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastBayesianUpdateBacktestMetric:
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
    updated_mae_incidence_per_100k: float
    mae_improvement_incidence_per_100k: float
    original_rmse_incidence_per_100k: float
    updated_rmse_incidence_per_100k: float
    original_mae_cases: float
    updated_mae_cases: float
    mae_improvement_cases: float
    coverage_80_count: int
    coverage_95_count: int
    coverage_80_share: float
    coverage_95_share: float
    update_gate_decision: str
    update_gate_reason: str
    recommended_update_use: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ForecastBayesianUpdateBacktestResult:
    run_id: str
    run: ForecastBayesianUpdateBacktestRun
    predictions: list[ForecastBayesianUpdateBacktestPrediction]
    metrics: list[ForecastBayesianUpdateBacktestMetric]


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
class _PosteriorUpdate:
    scope: str
    n_prior_updates: int
    prior_actual_cases: int
    prior_predicted_cases: float
    alpha: float
    beta: float

    @property
    def multiplier_mean(self) -> float:
        return self.alpha / self.beta

    @property
    def multiplier_variance(self) -> float:
        return self.alpha / (self.beta * self.beta)


def build_forecast_bayesian_update_backtest(
    *,
    predictions_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_prior_updates: int = 5,
    prior_strength_cases: float = 10.0,
) -> ForecastBayesianUpdateBacktestResult:
    if min_prior_updates < 1:
        raise ForecastBayesianUpdateBacktestInputError(
            "min_prior_updates must be at least 1"
        )
    if not math.isfinite(prior_strength_cases) or prior_strength_cases <= 0:
        raise ForecastBayesianUpdateBacktestInputError(
            "prior_strength_cases must be finite and greater than 0"
        )

    input_rows = _read_prediction_rows(predictions_path)
    if not input_rows:
        raise ForecastBayesianUpdateBacktestInputError("predictions CSV has no input rows")
    input_min_year = min(row.forecast_year for row in input_rows)
    input_max_year = max(row.forecast_year for row in input_rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise ForecastBayesianUpdateBacktestInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise ForecastBayesianUpdateBacktestInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise ForecastBayesianUpdateBacktestInputError(
            "start_year must be less than or equal to end_year"
        )

    predictions_sha256 = _sha256_file(predictions_path)
    run_id = (
        f"forecast_bayesian_update_backtest_start{start_year}_end{resolved_end_year}_"
        f"minprior{min_prior_updates}_priorcases{_slug_float(prior_strength_cases)}"
    )
    predictions = []
    for row in sorted(input_rows, key=lambda item: (item.forecast_year, item.county_fips)):
        if not (start_year <= row.forecast_year <= resolved_end_year):
            continue
        posterior = _posterior_for_row(
            row=row,
            rows=input_rows,
            min_prior_updates=min_prior_updates,
            prior_strength_cases=prior_strength_cases,
        )
        predictions.append(
            _prediction_row(
                run_id=run_id,
                row=row,
                posterior=posterior,
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
    run = ForecastBayesianUpdateBacktestRun(
        run_id=run_id,
        predictions_path=str(predictions_path),
        predictions_sha256=predictions_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_prior_updates=min_prior_updates,
        prior_strength_cases=prior_strength_cases,
        bayes_update_method=BAYES_UPDATE_METHOD,
        interval_method=BAYES_INTERVAL_METHOD,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        n_input_rows=len(input_rows),
        n_predictions=len(predictions),
        comparison_assumption_flags=_combined_flags(
            *(row.comparison_assumption_flags for row in predictions)
        ),
    )
    return ForecastBayesianUpdateBacktestResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        metrics=metrics,
    )


def _read_prediction_rows(path: Path) -> list[_PredictionRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ForecastBayesianUpdateBacktestInputError(
                "model comparison predictions CSV has no header"
            )
        missing = REQUIRED_PREDICTION_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ForecastBayesianUpdateBacktestInputError(
                "model comparison predictions missing required column(s): "
                + ", ".join(sorted(missing))
            )
        return [
            _PredictionRow(
                run_id=row["run_id"],
                model_name=row["model_name"],
                model_family=row["model_family"],
                feature_profile=row["feature_profile"],
                evaluation_mode=row["evaluation_mode"],
                source_file_sha256=row["source_file_sha256"],
                county_fips=row["county_fips"].zfill(5),
                county_name=row["county_name"],
                forecast_year=_parse_int(row["test_year"], "test_year"),
                surveillance_regime=_classify_surveillance_regime(
                    row.get("model_feature_quality_flags", ""),
                    _parse_int(row["test_year"], "test_year"),
                ),
                actual_incidence_per_100k=_parse_float(
                    row["actual_incidence_per_100k"],
                    "actual_incidence_per_100k",
                ),
                predicted_incidence_per_100k=_parse_float(
                    row["predicted_incidence_per_100k"],
                    "predicted_incidence_per_100k",
                ),
                actual_cases=_parse_nonnegative_int(
                    row["actual_cases"],
                    "actual_cases",
                ),
                predicted_cases=_parse_nonnegative_float(
                    row["predicted_cases"],
                    "predicted_cases",
                ),
                model_feature_quality_flags=row.get("model_feature_quality_flags", ""),
                comparison_assumption_flags=row.get("comparison_assumption_flags", ""),
            )
            for row in reader
        ]


def _posterior_for_row(
    *,
    row: _PredictionRow,
    rows: list[_PredictionRow],
    min_prior_updates: int,
    prior_strength_cases: float,
) -> _PosteriorUpdate:
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
    if len(same_regime_prior) >= min_prior_updates:
        return _posterior_from_prior(
            same_regime_prior,
            scope="same_regime_prior_years",
            prior_strength_cases=prior_strength_cases,
        )
    if len(same_model_prior) >= min_prior_updates:
        return _posterior_from_prior(
            same_model_prior,
            scope="all_regime_prior_years",
            prior_strength_cases=prior_strength_cases,
        )
    return _PosteriorUpdate(
        scope="prior_only_insufficient_updates",
        n_prior_updates=len(same_model_prior),
        prior_actual_cases=0,
        prior_predicted_cases=0.0,
        alpha=prior_strength_cases,
        beta=prior_strength_cases,
    )


def _posterior_from_prior(
    prior_rows: list[_PredictionRow],
    *,
    scope: str,
    prior_strength_cases: float,
) -> _PosteriorUpdate:
    return _PosteriorUpdate(
        scope=scope,
        n_prior_updates=len(prior_rows),
        prior_actual_cases=sum(row.actual_cases for row in prior_rows),
        prior_predicted_cases=sum(row.predicted_cases for row in prior_rows),
        alpha=prior_strength_cases + sum(row.actual_cases for row in prior_rows),
        beta=prior_strength_cases + sum(row.predicted_cases for row in prior_rows),
    )


def _prediction_row(
    *,
    run_id: str,
    row: _PredictionRow,
    posterior: _PosteriorUpdate,
) -> ForecastBayesianUpdateBacktestPrediction:
    multiplier = posterior.multiplier_mean
    updated_cases = row.predicted_cases * multiplier
    updated_incidence = row.predicted_incidence_per_100k * multiplier
    lower_80, upper_80 = _posterior_predictive_interval(
        predicted_cases=row.predicted_cases,
        posterior=posterior,
        z_score=1.281551565545,
    )
    lower_95, upper_95 = _posterior_predictive_interval(
        predicted_cases=row.predicted_cases,
        posterior=posterior,
        z_score=1.95996398454,
    )
    original_residual_incidence = (
        row.actual_incidence_per_100k - row.predicted_incidence_per_100k
    )
    updated_residual_incidence = row.actual_incidence_per_100k - updated_incidence
    return ForecastBayesianUpdateBacktestPrediction(
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
        update_scope=posterior.scope,
        n_prior_updates=posterior.n_prior_updates,
        prior_actual_cases=posterior.prior_actual_cases,
        prior_predicted_cases=_round(posterior.prior_predicted_cases),
        posterior_alpha=_round(posterior.alpha),
        posterior_beta=_round(posterior.beta),
        posterior_case_multiplier_mean=_round(multiplier),
        posterior_case_multiplier_variance=_round(posterior.multiplier_variance),
        original_predicted_incidence_per_100k=_round(
            row.predicted_incidence_per_100k
        ),
        updated_predicted_incidence_per_100k=_round(updated_incidence),
        actual_incidence_per_100k=_round(row.actual_incidence_per_100k),
        original_residual_incidence_per_100k=_round(original_residual_incidence),
        updated_residual_incidence_per_100k=_round(updated_residual_incidence),
        original_absolute_error_incidence_per_100k=_round(
            abs(original_residual_incidence)
        ),
        updated_absolute_error_incidence_per_100k=_round(
            abs(updated_residual_incidence)
        ),
        original_predicted_cases=_round(row.predicted_cases),
        updated_predicted_cases=_round(updated_cases),
        lower_80_updated_cases=_round(lower_80),
        upper_80_updated_cases=_round(upper_80),
        lower_95_updated_cases=_round(lower_95),
        upper_95_updated_cases=_round(upper_95),
        actual_cases=row.actual_cases,
        covered_80=lower_80 <= row.actual_cases <= upper_80,
        covered_95=lower_95 <= row.actual_cases <= upper_95,
        original_absolute_error_cases=_round(abs(row.actual_cases - row.predicted_cases)),
        updated_absolute_error_cases=_round(abs(row.actual_cases - updated_cases)),
        model_feature_quality_flags=row.model_feature_quality_flags,
        comparison_assumption_flags=_combined_flags(
            row.comparison_assumption_flags,
            "gamma_poisson_bayesian_update_backtest",
            "posterior_interval_moment_approximation",
            "not_public_default",
        ),
    )


def _posterior_predictive_interval(
    *,
    predicted_cases: float,
    posterior: _PosteriorUpdate,
    z_score: float,
) -> tuple[float, float]:
    mean_cases = predicted_cases * posterior.multiplier_mean
    variance_cases = (
        predicted_cases * posterior.multiplier_mean
        + predicted_cases * predicted_cases * posterior.multiplier_variance
    )
    half_width = z_score * math.sqrt(max(0.0, variance_cases))
    return max(0.0, mean_cases - half_width), mean_cases + half_width


def _metric_rows(
    run_id: str,
    predictions: list[ForecastBayesianUpdateBacktestPrediction],
) -> list[ForecastBayesianUpdateBacktestMetric]:
    return [
        _metric_row(run_id=run_id, rows=rows, key=key)
        for key, rows in sorted(_metric_groups(predictions).items())
    ]


def _metric_groups(
    predictions: list[ForecastBayesianUpdateBacktestPrediction],
) -> dict[
    tuple[str, str, str, str, str, str, str | None, int | None],
    list[ForecastBayesianUpdateBacktestPrediction],
]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str | None, int | None],
        list[ForecastBayesianUpdateBacktestPrediction],
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
    rows: list[ForecastBayesianUpdateBacktestPrediction],
    key: tuple[str, str, str, str, str, str, str | None, int | None],
) -> ForecastBayesianUpdateBacktestMetric:
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
    updated_incidence_errors = [
        row.updated_absolute_error_incidence_per_100k for row in rows
    ]
    original_case_errors = [row.original_absolute_error_cases for row in rows]
    updated_case_errors = [row.updated_absolute_error_cases for row in rows]
    original_mae_incidence = _round(mean(original_incidence_errors))
    updated_mae_incidence = _round(mean(updated_incidence_errors))
    original_mae_cases = _round(mean(original_case_errors))
    updated_mae_cases = _round(mean(updated_case_errors))
    mae_improvement_incidence = _round(original_mae_incidence - updated_mae_incidence)
    mae_improvement_cases = _round(original_mae_cases - updated_mae_cases)
    gate_decision, gate_reason = _update_gate(
        aggregation=aggregation,
        mae_improvement_incidence=mae_improvement_incidence,
        mae_improvement_cases=mae_improvement_cases,
    )
    coverage_80_count = sum(1 for row in rows if row.covered_80)
    coverage_95_count = sum(1 for row in rows if row.covered_95)
    return ForecastBayesianUpdateBacktestMetric(
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
        updated_mae_incidence_per_100k=updated_mae_incidence,
        mae_improvement_incidence_per_100k=mae_improvement_incidence,
        original_rmse_incidence_per_100k=_round(
            math.sqrt(
                mean(
                    row.original_residual_incidence_per_100k
                    * row.original_residual_incidence_per_100k
                    for row in rows
                )
            )
        ),
        updated_rmse_incidence_per_100k=_round(
            math.sqrt(
                mean(
                    row.updated_residual_incidence_per_100k
                    * row.updated_residual_incidence_per_100k
                    for row in rows
                )
            )
        ),
        original_mae_cases=original_mae_cases,
        updated_mae_cases=updated_mae_cases,
        mae_improvement_cases=mae_improvement_cases,
        coverage_80_count=coverage_80_count,
        coverage_95_count=coverage_95_count,
        coverage_80_share=_round(coverage_80_count / len(rows)),
        coverage_95_share=_round(coverage_95_count / len(rows)),
        update_gate_decision=gate_decision,
        update_gate_reason=gate_reason,
        recommended_update_use=RECOMMENDED_UPDATE_USE,
        comparison_assumption_flags=_combined_flags(
            *(row.comparison_assumption_flags for row in rows)
        ),
    )


def _update_gate(
    *,
    aggregation: str,
    mae_improvement_incidence: float,
    mae_improvement_cases: float,
) -> tuple[str, str]:
    if aggregation != "overall":
        return (
            "diagnostic_subgroup_only",
            "subgroup result is diagnostic evidence, not a standalone public update gate",
        )
    if mae_improvement_incidence > 0 and mae_improvement_cases > 0:
        return (
            "candidate_review_required",
            "Bayesian update improved overall held-out incidence and case MAE",
        )
    return (
        "do_not_apply_to_public_forecast",
        "Bayesian update did not improve overall held-out incidence and case MAE",
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
        raise ForecastBayesianUpdateBacktestInputError(
            f"missing required numeric value in {column}"
        )
    try:
        number = float(value)
    except ValueError as exc:
        raise ForecastBayesianUpdateBacktestInputError(
            f"invalid numeric value in {column}: {value}"
        ) from exc
    if not math.isfinite(number):
        raise ForecastBayesianUpdateBacktestInputError(
            f"non-finite numeric value in {column}: {value}"
        )
    return int(number)


def _parse_float(value: str, column: str) -> float:
    if value == "":
        raise ForecastBayesianUpdateBacktestInputError(
            f"missing required numeric value in {column}"
        )
    try:
        number = float(value)
    except ValueError as exc:
        raise ForecastBayesianUpdateBacktestInputError(
            f"invalid numeric value in {column}: {value}"
        ) from exc
    if not math.isfinite(number):
        raise ForecastBayesianUpdateBacktestInputError(
            f"non-finite numeric value in {column}: {value}"
        )
    return float(number)


def _parse_nonnegative_int(value: str, column: str) -> int:
    parsed = _parse_int(value, column)
    if parsed < 0:
        raise ForecastBayesianUpdateBacktestInputError(
            f"{column} must be non-negative"
        )
    return parsed


def _parse_nonnegative_float(value: str, column: str) -> float:
    parsed = _parse_float(value, column)
    if parsed < 0:
        raise ForecastBayesianUpdateBacktestInputError(
            f"{column} must be non-negative"
        )
    return parsed


def _round(value: float) -> float:
    return round(value, 6)


def _slug_float(value: float) -> str:
    return str(value).replace("-", "neg").replace(".", "p")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
