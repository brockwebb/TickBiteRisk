from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


COMPARISON_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_stress_test,"
    "not_public_maryland_default,"
    "population_denominator_sensitive"
)
EVALUATION_MODE = "rolling_origin_prior_years"
TARGET_DEFINITION = "reported_lyme_incidence_per_100k"
FEATURE_SET = "historical_incidence_shrinkage_analog_random_forest_baselines"
ANALOG_MODEL_FEATURE_FLAGS = (
    "analog_like_year_hindcast,"
    "forecast_origin_prior_year_only,"
    "analog_outcome_observed_before_test_year,"
    "forecast_safe_prior_outcomes_only"
)
RANDOM_FOREST_MODEL_FEATURE_FLAGS = (
    "random_forest_regional_research,"
    "forecast_safe_prior_outcomes_only,"
    "reported_incidence_history_only,"
    "not_public_maryland_default"
)
RANDOM_FOREST_N_ESTIMATORS = 200
RANDOM_FOREST_MIN_SAMPLES_LEAF = 3
RANDOM_FOREST_MAX_FEATURES = "sqrt"
RANDOM_FOREST_RANDOM_STATE = 1337
RANDOM_FOREST_ALLOWED_MAX_FEATURES = {"sqrt", "log2"}
REQUIRED_REGIONAL_INCIDENCE_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "population",
    "incidence_per_100k",
    "feature_quality_flags",
}


class RegionalIncidenceStressInputError(ValueError):
    """Raised when regional incidence stress test inputs are invalid."""


@dataclass(frozen=True)
class RegionalIncidenceStressRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    lookback_years: int
    shrinkage_strength: float
    random_forest_n_estimators: int
    random_forest_min_samples_leaf: int
    random_forest_max_features: str
    random_forest_random_state: int
    model_names: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    n_input_rows: int
    n_predictions: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceStressPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    source_file_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    train_year_count: int
    actual_incidence_per_100k: float
    predicted_incidence_per_100k: float
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    actual_cases: int
    actual_population: int | None
    predicted_cases: float | None
    analog_match_origin_year: int | None
    analog_match_observed_year: int | None
    analog_match_distance: float | None
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceStressMetric:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    source_file_sha256: str
    aggregation: str
    state_fips: str | None
    state_name: str | None
    test_year: int | None
    n_predictions: int
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    mean_bias_incidence_per_100k: float
    mae_cases: float
    rmse_cases: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceStressResult:
    run_id: str
    run: RegionalIncidenceStressRun
    predictions: list[RegionalIncidenceStressPrediction]
    metrics: list[RegionalIncidenceStressMetric]


@dataclass(frozen=True)
class _IncidenceRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    population: int | None
    incidence_per_100k: float | None
    feature_quality_flags: str


@dataclass(frozen=True)
class _ModelPrediction:
    predicted_incidence_per_100k: float
    predicted_cases: float | None
    train_start_year: int | None = None
    train_end_year: int | None = None
    train_year_count: int | None = None
    model_feature_quality_flags: str = ""
    analog_match_origin_year: int | None = None
    analog_match_observed_year: int | None = None
    analog_match_distance: float | None = None


@dataclass(frozen=True)
class _RegionalRandomForestModel:
    estimator: object
    train_start_year: int
    train_end_year: int
    train_year_count: int


def build_regional_incidence_stress(
    *,
    regional_incidence_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 3,
    shrinkage_strength: float = 5.0,
    random_forest_n_estimators: int = RANDOM_FOREST_N_ESTIMATORS,
    random_forest_min_samples_leaf: int = RANDOM_FOREST_MIN_SAMPLES_LEAF,
    random_forest_max_features: str = RANDOM_FOREST_MAX_FEATURES,
    random_forest_random_state: int = RANDOM_FOREST_RANDOM_STATE,
) -> RegionalIncidenceStressResult:
    if min_train_years < 1:
        raise RegionalIncidenceStressInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise RegionalIncidenceStressInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )
    if not math.isfinite(shrinkage_strength) or shrinkage_strength < 0:
        raise RegionalIncidenceStressInputError(
            "shrinkage_strength must be finite and non-negative"
        )
    if random_forest_n_estimators < 1:
        raise RegionalIncidenceStressInputError(
            "random_forest_n_estimators must be at least 1"
        )
    if random_forest_min_samples_leaf < 1:
        raise RegionalIncidenceStressInputError(
            "random_forest_min_samples_leaf must be at least 1"
        )
    if random_forest_max_features not in RANDOM_FOREST_ALLOWED_MAX_FEATURES:
        allowed = ", ".join(sorted(RANDOM_FOREST_ALLOWED_MAX_FEATURES))
        raise RegionalIncidenceStressInputError(
            "random_forest_max_features must be one of: " f"{allowed}"
        )

    rows = _read_incidence_rows(regional_incidence_path)
    if not rows:
        raise RegionalIncidenceStressInputError(
            "regional incidence panel has no input rows"
        )
    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise RegionalIncidenceStressInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise RegionalIncidenceStressInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise RegionalIncidenceStressInputError(
            "start_year must be less than or equal to end_year"
        )

    rows_by_county = _group_by_county(rows)
    rows_by_year = _group_by_year(rows)
    rows_by_county_year = {(row.county_fips, row.year): row for row in rows}
    source_file_sha256 = _sha256_file(regional_incidence_path)
    run_id = (
        f"regional_incidence_stress_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_lookback{lookback_years}_"
        f"shrinkage{_slug_float(shrinkage_strength)}_"
        f"rf{random_forest_n_estimators}_leaf{random_forest_min_samples_leaf}_"
        f"max{random_forest_max_features}_seed{random_forest_random_state}"
    )

    predictions = []
    for test_year in range(start_year, resolved_end_year + 1):
        train_window_start = test_year - lookback_years
        random_forest_model = _fit_regional_random_forest_model(
            rows=rows,
            rows_by_county=rows_by_county,
            rows_by_year=rows_by_year,
            test_year=test_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
            n_estimators=random_forest_n_estimators,
            min_samples_leaf=random_forest_min_samples_leaf,
            max_features=random_forest_max_features,
            random_state=random_forest_random_state,
        )
        year_rows = sorted(
            rows_by_year.get(test_year, []),
            key=lambda item: item.county_fips,
        )
        for row in year_rows:
            if row.incidence_per_100k is None:
                continue
            county_history = [
                prior
                for prior in rows_by_county[row.county_fips]
                if (
                    train_window_start <= prior.year < test_year
                    and prior.incidence_per_100k is not None
                )
            ]
            if len(county_history) < min_train_years:
                continue
            prior_year_row = rows_by_county_year.get((row.county_fips, test_year - 1))
            if prior_year_row is None or prior_year_row.incidence_per_100k is None:
                continue
            all_prior_county_history = [
                prior
                for prior in rows_by_county[row.county_fips]
                if prior.year < test_year and prior.incidence_per_100k is not None
            ]
            state_history = [
                prior
                for prior in rows
                if (
                    prior.state_fips == row.state_fips
                    and train_window_start <= prior.year < test_year
                    and prior.incidence_per_100k is not None
                )
            ]
            regional_history = [
                prior
                for prior in rows
                if (
                    train_window_start <= prior.year < test_year
                    and prior.incidence_per_100k is not None
                )
            ]
            train_start_year = min(prior.year for prior in county_history)
            train_end_year = max(prior.year for prior in county_history)
            model_predictions = _predict_incidence_baselines(
                row=row,
                county_history=county_history,
                prior_year_row=prior_year_row,
                all_prior_county_history=all_prior_county_history,
                test_year=test_year,
                state_history=state_history,
                regional_history=regional_history,
                shrinkage_strength=shrinkage_strength,
            )
            random_forest_prediction = _regional_random_forest_prediction(
                row=row,
                random_forest_model=random_forest_model,
                rows_by_county=rows_by_county,
                rows_by_year=rows_by_year,
                min_train_years=min_train_years,
                lookback_years=lookback_years,
            )
            if random_forest_prediction is not None:
                model_predictions["random_forest_regional_incidence"] = (
                    random_forest_prediction
                )
            flags = _combined_flags(row.feature_quality_flags, COMPARISON_ASSUMPTION_FLAGS)
            for model_name, model_prediction in model_predictions.items():
                predictions.append(
                    _prediction_row(
                        run_id=run_id,
                        model_name=model_name,
                        row=row,
                        model_prediction=model_prediction,
                        source_file_sha256=source_file_sha256,
                        default_train_start_year=train_start_year,
                        default_train_end_year=train_end_year,
                        default_train_year_count=len(county_history),
                        flags=flags,
                    )
                )

    predictions = sorted(
        predictions,
        key=lambda item: (item.test_year, item.model_name, item.county_fips),
    )
    metrics = _metric_rows(run_id, predictions, source_file_sha256)
    run = RegionalIncidenceStressRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=source_file_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        shrinkage_strength=shrinkage_strength,
        random_forest_n_estimators=random_forest_n_estimators,
        random_forest_min_samples_leaf=random_forest_min_samples_leaf,
        random_forest_max_features=random_forest_max_features,
        random_forest_random_state=random_forest_random_state,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        n_input_rows=len(rows),
        n_predictions=len(predictions),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )
    return RegionalIncidenceStressResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        metrics=metrics,
    )


def _read_incidence_rows(path: Path) -> list[_IncidenceRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_INCIDENCE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalIncidenceStressInputError(
                f"Missing regional incidence panel columns: {sorted(missing)}"
            )
        return sorted(
            [
                _IncidenceRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    year=int(row["year"]),
                    total_cases=_parse_int(row["total_cases"]),
                    population=_parse_optional_int(row.get("population", "")),
                    incidence_per_100k=_parse_optional_float(
                        row.get("incidence_per_100k", "")
                    ),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _group_by_county(rows: list[_IncidenceRow]) -> dict[str, list[_IncidenceRow]]:
    grouped: dict[str, list[_IncidenceRow]] = {}
    for row in rows:
        grouped.setdefault(row.county_fips, []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: row.year)
        for county_fips, county_rows in grouped.items()
    }


def _group_by_year(rows: list[_IncidenceRow]) -> dict[int, list[_IncidenceRow]]:
    grouped: dict[int, list[_IncidenceRow]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(row)
    return grouped


def _predict_incidence_baselines(
    *,
    row: _IncidenceRow,
    county_history: list[_IncidenceRow],
    prior_year_row: _IncidenceRow,
    all_prior_county_history: list[_IncidenceRow],
    test_year: int,
    state_history: list[_IncidenceRow],
    regional_history: list[_IncidenceRow],
    shrinkage_strength: float,
) -> dict[str, _ModelPrediction]:
    county_mean = mean(_known_incidence(prior) for prior in county_history)
    state_mean = (
        mean(_known_incidence(prior) for prior in state_history)
        if state_history
        else county_mean
    )
    regional_mean = (
        mean(_known_incidence(prior) for prior in regional_history)
        if regional_history
        else county_mean
    )
    state_prediction = _shrunk_mean(
        county_mean=county_mean,
        county_n=len(county_history),
        prior_mean=state_mean,
        prior_strength=shrinkage_strength,
    )
    regional_prediction = _shrunk_mean(
        county_mean=county_mean,
        county_n=len(county_history),
        prior_mean=regional_mean,
        prior_strength=shrinkage_strength,
    )
    predictions = {
        "prior_year_county_incidence": _model_prediction(
            predicted_incidence_per_100k=_known_incidence(prior_year_row),
            population=row.population,
        ),
        "trailing_mean_county_incidence": _model_prediction(
            predicted_incidence_per_100k=county_mean,
            population=row.population,
        ),
        "empirical_bayes_state_incidence": _model_prediction(
            predicted_incidence_per_100k=state_prediction,
            population=row.population,
        ),
        "empirical_bayes_midatlantic_incidence": _model_prediction(
            predicted_incidence_per_100k=regional_prediction,
            population=row.population,
        ),
    }
    analog_prediction = _analog_county_prediction(
        row=row,
        county_history=all_prior_county_history,
        test_year=test_year,
    )
    if analog_prediction is not None:
        predictions["analog_year_county_incidence"] = analog_prediction
    return predictions


def _prediction_row(
    *,
    run_id: str,
    model_name: str,
    row: _IncidenceRow,
    model_prediction: _ModelPrediction,
    source_file_sha256: str,
    default_train_start_year: int,
    default_train_end_year: int,
    default_train_year_count: int,
    flags: str,
) -> RegionalIncidenceStressPrediction:
    actual_incidence = _known_incidence(row)
    residual_incidence = _round(
        actual_incidence - model_prediction.predicted_incidence_per_100k
    )
    train_start_year = (
        model_prediction.train_start_year
        if model_prediction.train_start_year is not None
        else default_train_start_year
    )
    train_end_year = (
        model_prediction.train_end_year
        if model_prediction.train_end_year is not None
        else default_train_end_year
    )
    train_year_count = (
        model_prediction.train_year_count
        if model_prediction.train_year_count is not None
        else default_train_year_count
    )
    return RegionalIncidenceStressPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family=_model_family(model_name),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        source_file_sha256=source_file_sha256,
        state_fips=row.state_fips,
        state_abbr=row.state_abbr,
        state_name=row.state_name,
        county_fips=row.county_fips,
        county_name=row.county_name,
        test_year=row.year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=train_year_count,
        actual_incidence_per_100k=actual_incidence,
        predicted_incidence_per_100k=model_prediction.predicted_incidence_per_100k,
        residual_incidence_per_100k=residual_incidence,
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        actual_cases=row.total_cases,
        actual_population=row.population,
        predicted_cases=model_prediction.predicted_cases,
        analog_match_origin_year=model_prediction.analog_match_origin_year,
        analog_match_observed_year=model_prediction.analog_match_observed_year,
        analog_match_distance=model_prediction.analog_match_distance,
        model_feature_quality_flags=_combined_flags(
            row.feature_quality_flags,
            model_prediction.model_feature_quality_flags,
        ),
        comparison_assumption_flags=flags,
    )


def _metric_rows(
    run_id: str,
    predictions: list[RegionalIncidenceStressPrediction],
    source_file_sha256: str,
) -> list[RegionalIncidenceStressMetric]:
    metrics = []
    for model_name in sorted({row.model_name for row in predictions}):
        model_rows = [row for row in predictions if row.model_name == model_name]
        metrics.append(
            _metric_row(
                run_id=run_id,
                model_name=model_name,
                source_file_sha256=source_file_sha256,
                aggregation="overall",
                rows=model_rows,
            )
        )
        for state_fips in sorted({row.state_fips for row in model_rows}):
            state_rows = [row for row in model_rows if row.state_fips == state_fips]
            metrics.append(
                _metric_row(
                    run_id=run_id,
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    aggregation="state",
                    rows=state_rows,
                    state_fips=state_fips,
                    state_name=state_rows[0].state_name,
                )
            )
        for test_year in sorted({row.test_year for row in model_rows}):
            year_rows = [row for row in model_rows if row.test_year == test_year]
            metrics.append(
                _metric_row(
                    run_id=run_id,
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    aggregation="year",
                    rows=year_rows,
                    test_year=test_year,
                )
            )
    return metrics


def _metric_row(
    *,
    run_id: str,
    model_name: str,
    source_file_sha256: str,
    aggregation: str,
    rows: list[RegionalIncidenceStressPrediction],
    state_fips: str | None = None,
    state_name: str | None = None,
    test_year: int | None = None,
) -> RegionalIncidenceStressMetric:
    residuals = [row.residual_incidence_per_100k for row in rows]
    absolute_errors = [row.absolute_error_incidence_per_100k for row in rows]
    case_residuals = [
        row.actual_cases - row.predicted_cases
        for row in rows
        if row.predicted_cases is not None
    ]
    return RegionalIncidenceStressMetric(
        run_id=run_id,
        model_name=model_name,
        model_family=_model_family(model_name),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        source_file_sha256=source_file_sha256,
        aggregation=aggregation,
        state_fips=state_fips,
        state_name=state_name,
        test_year=test_year,
        n_predictions=len(rows),
        mae_incidence_per_100k=_round(mean(absolute_errors)) if absolute_errors else 0.0,
        rmse_incidence_per_100k=(
            _round(math.sqrt(mean(residual * residual for residual in residuals)))
            if residuals
            else 0.0
        ),
        mean_bias_incidence_per_100k=_round(mean(residuals)) if residuals else 0.0,
        mae_cases=(
            _round(mean(abs(residual) for residual in case_residuals))
            if case_residuals
            else 0.0
        ),
        rmse_cases=(
            _round(math.sqrt(mean(residual * residual for residual in case_residuals)))
            if case_residuals
            else 0.0
        ),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )


def _model_prediction(
    *,
    predicted_incidence_per_100k: float,
    population: int | None,
    train_start_year: int | None = None,
    train_end_year: int | None = None,
    train_year_count: int | None = None,
    model_feature_quality_flags: str = "",
    analog_match_origin_year: int | None = None,
    analog_match_observed_year: int | None = None,
    analog_match_distance: float | None = None,
) -> _ModelPrediction:
    predicted_incidence = _round(predicted_incidence_per_100k)
    predicted_cases = (
        _round((predicted_incidence * population) / 100000)
        if population is not None
        else None
    )
    return _ModelPrediction(
        predicted_incidence_per_100k=predicted_incidence,
        predicted_cases=predicted_cases,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=train_year_count,
        model_feature_quality_flags=model_feature_quality_flags,
        analog_match_origin_year=analog_match_origin_year,
        analog_match_observed_year=analog_match_observed_year,
        analog_match_distance=analog_match_distance,
    )


def _fit_regional_random_forest_model(
    *,
    rows: list[_IncidenceRow],
    rows_by_county: dict[str, list[_IncidenceRow]],
    rows_by_year: dict[int, list[_IncidenceRow]],
    test_year: int,
    min_train_years: int,
    lookback_years: int,
    n_estimators: int,
    min_samples_leaf: int,
    max_features: str,
    random_state: int,
) -> _RegionalRandomForestModel | None:
    x_rows = []
    y_values = []
    train_years = set()
    for candidate in rows:
        if candidate.year >= test_year or candidate.incidence_per_100k is None:
            continue
        features = _regional_random_forest_feature_vector(
            row=candidate,
            rows_by_county=rows_by_county,
            rows_by_year=rows_by_year,
            target_year=candidate.year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
        )
        if features is None:
            continue
        x_rows.append(features)
        y_values.append(candidate.incidence_per_100k)
        train_years.add(candidate.year)
    if not x_rows:
        return None

    from sklearn.ensemble import RandomForestRegressor

    estimator = RandomForestRegressor(
        n_estimators=n_estimators,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        random_state=random_state,
        n_jobs=1,
    )
    estimator.fit(x_rows, y_values)
    return _RegionalRandomForestModel(
        estimator=estimator,
        train_start_year=min(train_years),
        train_end_year=max(train_years),
        train_year_count=len(train_years),
    )


def _regional_random_forest_prediction(
    *,
    row: _IncidenceRow,
    random_forest_model: _RegionalRandomForestModel | None,
    rows_by_county: dict[str, list[_IncidenceRow]],
    rows_by_year: dict[int, list[_IncidenceRow]],
    min_train_years: int,
    lookback_years: int,
) -> _ModelPrediction | None:
    if random_forest_model is None:
        return None
    features = _regional_random_forest_feature_vector(
        row=row,
        rows_by_county=rows_by_county,
        rows_by_year=rows_by_year,
        target_year=row.year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
    )
    if features is None:
        return None
    prediction = float(random_forest_model.estimator.predict([features])[0])
    return _model_prediction(
        predicted_incidence_per_100k=max(prediction, 0.0),
        population=row.population,
        train_start_year=random_forest_model.train_start_year,
        train_end_year=random_forest_model.train_end_year,
        train_year_count=random_forest_model.train_year_count,
        model_feature_quality_flags=RANDOM_FOREST_MODEL_FEATURE_FLAGS,
    )


def _regional_random_forest_feature_vector(
    *,
    row: _IncidenceRow,
    rows_by_county: dict[str, list[_IncidenceRow]],
    rows_by_year: dict[int, list[_IncidenceRow]],
    target_year: int,
    min_train_years: int,
    lookback_years: int,
) -> list[float] | None:
    history = [
        prior
        for prior in rows_by_county[row.county_fips]
        if (
            target_year - lookback_years <= prior.year < target_year
            and prior.incidence_per_100k is not None
        )
    ]
    if len(history) < min_train_years:
        return None
    prior_year_row = next(
        (
            prior
            for prior in history
            if prior.year == target_year - 1
            and prior.incidence_per_100k is not None
        ),
        None,
    )
    if prior_year_row is None:
        return None

    county_values = [_known_incidence(prior) for prior in history]
    county_mean = mean(county_values)
    ordered_history = sorted(history, key=lambda prior: prior.year)
    state_prior_values = _known_year_values(
        rows_by_year.get(target_year - 1, []),
        state_fips=row.state_fips,
    )
    regional_prior_values = _known_year_values(rows_by_year.get(target_year - 1, []))
    state_history_values = _known_window_values(
        rows_by_year=rows_by_year,
        start_year=target_year - lookback_years,
        end_year=target_year,
        state_fips=row.state_fips,
    )
    regional_history_values = _known_window_values(
        rows_by_year=rows_by_year,
        start_year=target_year - lookback_years,
        end_year=target_year,
    )
    return [
        _known_incidence(prior_year_row),
        county_mean,
        min(county_values),
        max(county_values),
        _known_incidence(ordered_history[-1]) - _known_incidence(ordered_history[0]),
        float(len(history)),
        mean(state_prior_values) if state_prior_values else county_mean,
        mean(state_history_values) if state_history_values else county_mean,
        mean(regional_prior_values) if regional_prior_values else county_mean,
        mean(regional_history_values) if regional_history_values else county_mean,
    ]


def _known_year_values(
    rows: list[_IncidenceRow],
    *,
    state_fips: str | None = None,
) -> list[float]:
    return [
        _known_incidence(row)
        for row in rows
        if row.incidence_per_100k is not None
        and (state_fips is None or row.state_fips == state_fips)
    ]


def _known_window_values(
    *,
    rows_by_year: dict[int, list[_IncidenceRow]],
    start_year: int,
    end_year: int,
    state_fips: str | None = None,
) -> list[float]:
    values = []
    for year in range(start_year, end_year):
        values.extend(_known_year_values(rows_by_year.get(year, []), state_fips=state_fips))
    return values


def _analog_county_prediction(
    *,
    row: _IncidenceRow,
    county_history: list[_IncidenceRow],
    test_year: int,
) -> _ModelPrediction | None:
    history_by_year = {prior.year: prior for prior in county_history}
    current_origin_year = test_year - 1
    current_features = _analog_feature_vector(
        history_by_year=history_by_year,
        origin_year=current_origin_year,
    )
    if current_features is None:
        return None

    candidates = []
    for candidate_origin_year in sorted(history_by_year):
        if candidate_origin_year >= current_origin_year:
            continue
        observed_year = candidate_origin_year + 1
        if observed_year >= test_year:
            continue
        observed_row = history_by_year.get(observed_year)
        if observed_row is None or observed_row.incidence_per_100k is None:
            continue
        candidate_features = _analog_feature_vector(
            history_by_year=history_by_year,
            origin_year=candidate_origin_year,
        )
        if candidate_features is None:
            continue
        distance = _analog_distance(current_features, candidate_features)
        candidates.append((distance, candidate_origin_year, observed_year, observed_row))

    if not candidates:
        return None

    distance, origin_year, observed_year, observed_row = min(
        candidates,
        key=lambda item: (item[0], -item[1]),
    )
    train_years = [prior.year for prior in county_history]
    return _model_prediction(
        predicted_incidence_per_100k=_known_incidence(observed_row),
        population=row.population,
        train_start_year=min(train_years),
        train_end_year=max(train_years),
        train_year_count=len(train_years),
        model_feature_quality_flags=ANALOG_MODEL_FEATURE_FLAGS,
        analog_match_origin_year=origin_year,
        analog_match_observed_year=observed_year,
        analog_match_distance=_round(distance),
    )


def _analog_feature_vector(
    *,
    history_by_year: dict[int, _IncidenceRow],
    origin_year: int,
    trailing_years: int = 3,
) -> tuple[float, float] | None:
    origin = history_by_year.get(origin_year)
    if origin is None or origin.incidence_per_100k is None:
        return None
    trailing_values = [
        _known_incidence(history_by_year[year])
        for year in range(origin_year - trailing_years + 1, origin_year + 1)
        if year in history_by_year
        and history_by_year[year].incidence_per_100k is not None
    ]
    if not trailing_values:
        return None
    return (_known_incidence(origin), mean(trailing_values))


def _analog_distance(
    current_features: tuple[float, float],
    candidate_features: tuple[float, float],
) -> float:
    return sum(
        abs(current_value - candidate_value)
        for current_value, candidate_value in zip(
            current_features,
            candidate_features,
            strict=True,
        )
    )


def _model_family(model_name: str) -> str:
    if model_name.startswith("random_forest_"):
        return "random_forest_incidence"
    if model_name.startswith("analog_"):
        return "analog"
    if model_name.startswith("empirical_bayes_"):
        return "empirical_bayes_incidence_shrinkage"
    return "county_incidence_baseline"


def _known_incidence(row: _IncidenceRow) -> float:
    if row.incidence_per_100k is None:
        raise RegionalIncidenceStressInputError(
            "internal error: missing incidence used as known value"
        )
    return row.incidence_per_100k


def _shrunk_mean(
    *,
    county_mean: float,
    county_n: int,
    prior_mean: float,
    prior_strength: float,
) -> float:
    posterior_denominator = county_n + prior_strength
    if posterior_denominator <= 0:
        return county_mean
    return _round(
        ((county_mean * county_n) + (prior_mean * prior_strength))
        / posterior_denominator
    )


def _combined_flags(*flag_groups: str) -> str:
    flags = []
    for group in flag_groups:
        flags.extend(flag for flag in group.split(",") if flag)
    return ",".join(dict.fromkeys(flags))


def _parse_int(value: str) -> int:
    return int(float(value))


def _parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _parse_optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


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
