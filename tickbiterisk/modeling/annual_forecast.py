from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from tickbiterisk.modeling.model_compare import (
    ANALOG_FEATURE_PROFILE,
    FORECAST_SAFE_TOP4_ENSEMBLE_PROFILE,
    FORECAST_SAFE_WEATHER_MODE,
    LAGGED_WEATHER_MODE,
    ModelComparisonInputError,
    TARGET_DEFINITION,
    _DesignRow,
    _analog_prediction,
    _empirical_bayes_prediction,
    _has_training_depth,
    _is_forecast_safe_feature_column,
    _is_forecast_spatial_feature_column,
    _is_trailing_mean_incidence_feature,
    _read_design_rows,
    _ridge_prediction,
    _round,
)


FORECAST_EVALUATION_MODE = "annual_forecast_no_observed_target"
FORECAST_FEATURE_SET = "lagged_outcome_forecast"
FORECAST_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "intervention_history_unmodeled,"
    "surveillance_reporting_sensitive,"
    "forecast_without_observed_target,"
    "population_denominator_forecast,"
    "not_weather_adjusted"
)
FORECAST_MODEL_SPECS = (
    (
        "latest_observed_incidence",
        "baseline",
        "latest_observed_lag",
    ),
    (
        "trailing_mean_incidence",
        "baseline",
        "trailing_county_history",
    ),
    (
        "linear_blend_baseline",
        "ensemble",
        "latest_observed_trailing_blend",
    ),
    (
        "empirical_bayes_shrinkage",
        "empirical_bayes",
        "county_history_with_state_shrinkage",
    ),
    (
        "analog_year_forecast",
        "analog",
        ANALOG_FEATURE_PROFILE,
    ),
)
ANNUAL_ANALOG_EXACT_FEATURES = {
    "feature_prior_year_lyme_incidence_per_100k",
    "feature_trailing_history_years",
    "feature_missing_prior_year_lyme_incidence",
    "feature_state_prior_year_lyme_incidence_per_100k",
    "feature_missing_state_prior_year_lyme_incidence",
}
FORECAST_ORIGIN_ASSUMPTION_FLAG_ALLOWLIST = {
    "covid_reporting_disruption",
    "lyme_case_definition_change",
    "mdh_probable_only_2024",
    "state_source_not_cdc_public_use",
    "reported_cases_not_stable_true_incidence",
}
ALLOWED_UPDATE_MODES = {"pre_update", "post_observed_outcome"}


class AnnualForecastInputError(ValueError):
    """Raised when annual forecast inputs cannot produce forecast rows."""


@dataclass(frozen=True)
class AnnualForecastRun:
    run_id: str
    design_matrix_path: str
    design_matrix_sha256: str
    population_path: str
    population_sha256: str
    county_adjacency_path: str | None
    county_adjacency_sha256: str | None
    target_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    min_train_years: int
    ridge_alpha: float
    shrinkage_strength: float
    model_names: str
    target_definition: str
    evaluation_mode: str
    feature_set: str
    n_training_rows: int
    n_forecast_counties: int
    n_forecast_rows: int
    forecast_assumption_flags: str


@dataclass(frozen=True)
class AnnualForecastPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    design_matrix_sha256: str
    population_sha256: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    forecast_horizon_years: int
    train_start_year: int
    train_end_year: int
    train_row_count: int
    train_county_count: int
    forecast_population: int
    population_source_id: str
    population_vintage: int
    population_feature_quality_flags: str
    predicted_cases: float
    predicted_incidence_per_100k: float
    model_feature_quality_flags: str
    forecast_assumption_flags: str


@dataclass(frozen=True)
class AnnualForecastResult:
    run_id: str
    run: AnnualForecastRun
    predictions: list[AnnualForecastPrediction]


@dataclass(frozen=True)
class _PopulationRow:
    county_fips: str
    county_name: str
    year: int
    population: int
    source_id: str
    vintage: int
    feature_quality_flags: str


def build_annual_forecast(
    *,
    design_matrix_path: Path,
    population_path: Path,
    county_adjacency_path: Path | None = None,
    target_year: int,
    forecast_origin_year: int,
    min_train_years: int = 5,
    ridge_alpha: float = 1.0,
    shrinkage_strength: float = 5.0,
    as_of_date: str = "unspecified",
    data_cutoff_date: str = "unspecified",
    source_vintage: str | None = None,
    update_mode: str = "pre_update",
) -> AnnualForecastResult:
    if target_year <= forecast_origin_year:
        raise AnnualForecastInputError(
            "target-year must be greater than forecast-origin-year"
        )
    if min_train_years < 1:
        raise AnnualForecastInputError("min_train_years must be at least 1")
    if ridge_alpha <= 0:
        raise AnnualForecastInputError("ridge_alpha must be greater than 0")
    if shrinkage_strength < 0:
        raise AnnualForecastInputError("shrinkage_strength must be non-negative")
    if update_mode not in ALLOWED_UPDATE_MODES:
        allowed = ", ".join(sorted(ALLOWED_UPDATE_MODES))
        raise AnnualForecastInputError(f"update_mode must be one of: {allowed}")

    rows, feature_columns = _read_training_design_rows(design_matrix_path)
    county_neighbors = _read_county_adjacency(county_adjacency_path)
    train_rows = [row for row in rows if row.year <= forecast_origin_year]
    if not train_rows:
        raise AnnualForecastInputError("no training rows at or before forecast origin")
    if not _has_training_depth(train_rows, min_train_years=min_train_years):
        raise AnnualForecastInputError(
            "not enough prior county history for annual forecast"
        )

    population = _read_forecast_population(population_path, target_year=target_year)
    forecast_rows = _forecast_design_rows(
        train_rows=train_rows,
        population=population,
        target_year=target_year,
        forecast_origin_year=forecast_origin_year,
        min_train_years=min_train_years,
        feature_columns=feature_columns,
        county_neighbors=county_neighbors,
    )
    if not forecast_rows:
        raise AnnualForecastInputError("no forecast rows with target-year population")

    source_sha = _sha256_file(design_matrix_path)
    population_sha = _sha256_file(population_path)
    county_adjacency_sha = (
        _sha256_file(county_adjacency_path)
        if county_adjacency_path is not None
        else None
    )
    resolved_source_vintage = source_vintage or source_sha
    train_start_year = min(row.year for row in train_rows)
    train_end_year = max(row.year for row in train_rows)
    train_county_count = len({row.county_fips for row in train_rows})
    run_id = (
        f"annual_forecast_target{target_year}_origin{forecast_origin_year}_"
        f"mintrain{min_train_years}_ridge{_slug_float(ridge_alpha)}_"
        f"shrink{_slug_float(shrinkage_strength)}"
    )
    predictions = []
    ridge_cache = {}
    for row, population_row in forecast_rows:
        for model_name, model_family, feature_profile, predicted in _forecast_models(
            row=row,
            train_rows=train_rows,
            feature_columns=feature_columns,
            ridge_alpha=ridge_alpha,
            shrinkage_strength=shrinkage_strength,
            ridge_cache=ridge_cache,
            include_spatial_forecast=bool(county_neighbors),
        ):
            predictions.append(
                _forecast_prediction_row(
                    run_id=run_id,
                    model_name=model_name,
                    model_family=model_family,
                    feature_profile=feature_profile,
                    row=row,
                    population_row=population_row,
                    predicted_incidence=predicted,
                    design_matrix_sha=source_sha,
                    population_sha=population_sha,
                    forecast_origin_year=forecast_origin_year,
                    as_of_date=as_of_date,
                    data_cutoff_date=data_cutoff_date,
                    source_vintage=resolved_source_vintage,
                    update_mode=update_mode,
                    train_start_year=train_start_year,
                    train_end_year=train_end_year,
                    train_row_count=len(train_rows),
                    train_county_count=train_county_count,
                )
            )

    run = AnnualForecastRun(
        run_id=run_id,
        design_matrix_path=str(design_matrix_path),
        design_matrix_sha256=source_sha,
        population_path=str(population_path),
        population_sha256=population_sha,
        county_adjacency_path=(
            None if county_adjacency_path is None else str(county_adjacency_path)
        ),
        county_adjacency_sha256=county_adjacency_sha,
        target_year=target_year,
        forecast_origin_year=forecast_origin_year,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=resolved_source_vintage,
        update_mode=update_mode,
        min_train_years=min_train_years,
        ridge_alpha=ridge_alpha,
        shrinkage_strength=shrinkage_strength,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        target_definition=TARGET_DEFINITION,
        evaluation_mode=FORECAST_EVALUATION_MODE,
        feature_set=FORECAST_FEATURE_SET,
        n_training_rows=len(train_rows),
        n_forecast_counties=len(forecast_rows),
        n_forecast_rows=len(predictions),
        forecast_assumption_flags=FORECAST_ASSUMPTION_FLAGS,
    )
    return AnnualForecastResult(run_id=run_id, run=run, predictions=predictions)


def _forecast_models(
    *,
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    ridge_alpha: float,
    shrinkage_strength: float,
    ridge_cache: dict,
    include_spatial_forecast: bool,
) -> list[tuple[str, str, str, float]]:
    latest = row.features.get("feature_prior_year_lyme_incidence_per_100k", 0.0)
    trailing = _county_trailing_mean(row, train_rows)
    blend = mean([latest, trailing])
    analog_columns = _annual_analog_feature_columns(feature_columns)
    forecast_columns = [
        column for column in feature_columns if _is_forecast_safe_feature_column(column)
    ]
    safe_ridge_prediction = _ridge_prediction(
        row=row,
        train_rows=train_rows,
        feature_columns=forecast_columns,
        ridge_alpha=ridge_alpha,
        ridge_cache=ridge_cache,
    )
    values = {
        "latest_observed_incidence": latest,
        "trailing_mean_incidence": trailing,
        "linear_blend_baseline": blend,
        "empirical_bayes_shrinkage": _empirical_bayes_prediction(
            row,
            train_rows,
            shrinkage_strength,
        ),
        "analog_year_forecast": _analog_prediction(row, train_rows, analog_columns),
    }
    predictions = [
        (model_name, model_family, feature_profile, values[model_name])
        for model_name, model_family, feature_profile in FORECAST_MODEL_SPECS
    ]
    predictions.append(
        (
            "ridge_forecast_safe",
            "regularized_linear",
            "forecast_safe_lagged",
            safe_ridge_prediction,
        )
    )
    if include_spatial_forecast and _has_spatial_feature_columns(feature_columns):
        spatial_columns = [
            column
            for column in feature_columns
            if _is_forecast_spatial_feature_column(column)
        ]
        spatial_ridge_prediction = _ridge_prediction(
            row=row,
            train_rows=train_rows,
            feature_columns=spatial_columns,
            ridge_alpha=ridge_alpha,
            ridge_cache=ridge_cache,
        )
        predictions.append(
            (
                "ridge_forecast_spatial",
                "regularized_linear",
                "forecast_safe_lagged_spatial",
                spatial_ridge_prediction,
            )
        )
        predictions.append(
            (
                "forecast_safe_top4_ensemble",
                "ensemble",
                FORECAST_SAFE_TOP4_ENSEMBLE_PROFILE,
                mean([latest, blend, safe_ridge_prediction, spatial_ridge_prediction]),
            )
        )
    return predictions


def _has_spatial_feature_columns(feature_columns: list[str]) -> bool:
    return any(
        _is_forecast_spatial_feature_column(column)
        and not _is_forecast_safe_feature_column(column)
        for column in feature_columns
    )


def _annual_analog_feature_columns(feature_columns: list[str]) -> list[str]:
    return [
        column
        for column in feature_columns
        if column in ANNUAL_ANALOG_EXACT_FEATURES
        or _is_trailing_mean_incidence_feature(column)
    ]


def _forecast_design_rows(
    *,
    train_rows: list[_DesignRow],
    population: dict[str, _PopulationRow],
    target_year: int,
    forecast_origin_year: int,
    min_train_years: int,
    feature_columns: list[str],
    county_neighbors: dict[str, list[str]],
) -> list[tuple[_DesignRow, _PopulationRow]]:
    rows_by_county: dict[str, list[_DesignRow]] = {}
    for row in sorted(train_rows, key=lambda row: (row.county_fips, row.year)):
        rows_by_county.setdefault(row.county_fips, []).append(row)

    forecast_rows = []
    origin_rows = [row for row in train_rows if row.year == forecast_origin_year]
    origin_state_incidence, origin_state_missing = _annual_state_prior_incidence(
        origin_rows
    )
    for county_fips in sorted(rows_by_county):
        population_row = population.get(county_fips)
        if population_row is None or population_row.population <= 0:
            continue
        county_train_rows = rows_by_county[county_fips]
        if len(county_train_rows) < min_train_years:
            continue
        latest = county_train_rows[-1]
        if latest.year != forecast_origin_year:
            continue
        features = {
            **latest.features,
            "feature_year": float(target_year),
            "feature_prior_year_lyme_incidence_per_100k": latest.incidence_per_100k,
            "feature_missing_prior_year_lyme_incidence": 0.0,
            "feature_state_prior_year_lyme_incidence_per_100k": origin_state_incidence,
            "feature_missing_state_prior_year_lyme_incidence": origin_state_missing,
            "feature_trailing_history_years": _annual_trailing_history_years(
                county_train_rows,
                feature_columns,
            ),
            "feature_log_population_offset": round(
                math.log(population_row.population),
                6,
            ),
        }
        for column in feature_columns:
            if _is_trailing_mean_incidence_feature(column):
                features[column] = _annual_trailing_feature_value(
                    county_train_rows,
                    column,
                )
        if county_neighbors:
            features.update(
                _annual_spatial_neighbor_features(
                    county_fips=county_fips,
                    train_rows=train_rows,
                    forecast_origin_year=forecast_origin_year,
                    county_neighbors=county_neighbors,
                )
            )
        forecast_rows.append(
            (
                _DesignRow(
                    county_fips=county_fips,
                    county_name=latest.county_name,
                    year=target_year,
                    actual_cases=0,
                    population=population_row.population,
                    incidence_per_100k=0.0,
                    features=features,
                    model_feature_quality_flags=latest.model_feature_quality_flags,
                ),
                population_row,
            )
        )
    return forecast_rows


def _annual_state_prior_incidence(
    origin_rows: list[_DesignRow],
) -> tuple[float, float]:
    total_population = sum(row.population for row in origin_rows)
    if total_population <= 0:
        return 0.0, 1.0
    total_cases = sum(row.actual_cases for row in origin_rows)
    return _round(total_cases / total_population * 100000), 0.0


def _annual_trailing_history_years(
    county_train_rows: list[_DesignRow],
    feature_columns: list[str],
) -> float:
    windows = [
        window
        for column in feature_columns
        if (window := _trailing_window_from_feature_column(column)) is not None
    ]
    if not windows:
        return float(len(county_train_rows))
    return float(min(len(county_train_rows), max(windows)))


def _annual_trailing_feature_value(
    county_train_rows: list[_DesignRow],
    column: str,
) -> float:
    window = _trailing_window_from_feature_column(column)
    rows = county_train_rows[-window:] if window is not None else county_train_rows
    return _round(mean(row.incidence_per_100k for row in rows)) if rows else 0.0


def _trailing_window_from_feature_column(column: str) -> int | None:
    prefix = "feature_trailing_"
    suffix = "yr_mean_lyme_incidence_per_100k"
    if not (column.startswith(prefix) and column.endswith(suffix)):
        return None
    value = column[len(prefix) : -len(suffix)]
    return int(value) if value.isdigit() else None


def _annual_spatial_neighbor_features(
    *,
    county_fips: str,
    train_rows: list[_DesignRow],
    forecast_origin_year: int,
    county_neighbors: dict[str, list[str]],
) -> dict[str, float]:
    origin_rows_by_county = {
        row.county_fips: row
        for row in train_rows
        if row.year == forecast_origin_year
    }
    values = [
        neighbor.incidence_per_100k
        for neighbor_fips in county_neighbors.get(county_fips, [])
        if (neighbor := origin_rows_by_county.get(neighbor_fips)) is not None
    ]
    if not values:
        return {
            "feature_neighbor_prior_year_lyme_incidence_mean": 0.0,
            "feature_neighbor_prior_year_lyme_incidence_max": 0.0,
            "feature_neighbor_prior_year_count": 0.0,
            "feature_missing_neighbor_prior_year_lyme_incidence": 1.0,
        }
    return {
        "feature_neighbor_prior_year_lyme_incidence_mean": _round(mean(values)),
        "feature_neighbor_prior_year_lyme_incidence_max": _round(max(values)),
        "feature_neighbor_prior_year_count": float(len(values)),
        "feature_missing_neighbor_prior_year_lyme_incidence": 0.0,
    }


def _read_training_design_rows(path: Path) -> tuple[list[_DesignRow], list[str]]:
    try:
        return _read_design_rows(path)
    except ModelComparisonInputError as exc:
        raise AnnualForecastInputError(str(exc)) from exc
    except ValueError as exc:
        raise AnnualForecastInputError(
            f"invalid annual forecast design matrix: {exc}"
        ) from exc


def _read_county_adjacency(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    if not path.exists():
        raise AnnualForecastInputError(f"county adjacency file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = {"county_fips", "neighbor_county_fips"} - fieldnames
        if missing_columns:
            raise AnnualForecastInputError(
                "missing required county adjacency column(s): "
                f"{', '.join(sorted(missing_columns))}"
            )
        neighbors: dict[str, set[str]] = {}
        for row in reader:
            county_fips = str(row["county_fips"]).zfill(5)
            neighbor_county_fips = str(row["neighbor_county_fips"]).zfill(5)
            if county_fips == neighbor_county_fips:
                continue
            neighbors.setdefault(county_fips, set()).add(neighbor_county_fips)
    return {
        county_fips: sorted(county_neighbors)
        for county_fips, county_neighbors in neighbors.items()
    }


def _forecast_prediction_row(
    *,
    run_id: str,
    model_name: str,
    model_family: str,
    feature_profile: str,
    row: _DesignRow,
    population_row: _PopulationRow,
    predicted_incidence: float,
    design_matrix_sha: str,
    population_sha: str,
    forecast_origin_year: int,
    as_of_date: str,
    data_cutoff_date: str,
    source_vintage: str,
    update_mode: str,
    train_start_year: int,
    train_end_year: int,
    train_row_count: int,
    train_county_count: int,
) -> AnnualForecastPrediction:
    predicted_incidence = max(predicted_incidence, 0.0)
    predicted_cases = predicted_incidence / 100000 * row.population
    flags = _join_flags(
        FORECAST_ASSUMPTION_FLAGS,
        population_row.feature_quality_flags,
        _forecast_origin_assumption_flags(row.model_feature_quality_flags),
    )
    return AnnualForecastPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        target_definition=TARGET_DEFINITION,
        feature_set=FORECAST_FEATURE_SET,
        feature_profile=feature_profile,
        evaluation_mode=FORECAST_EVALUATION_MODE,
        weather_mode=(
            FORECAST_SAFE_WEATHER_MODE
            if feature_profile.startswith("forecast_safe")
            else LAGGED_WEATHER_MODE
        ),
        design_matrix_sha256=design_matrix_sha,
        population_sha256=population_sha,
        county_fips=row.county_fips,
        county_name=row.county_name,
        forecast_year=row.year,
        forecast_origin_year=forecast_origin_year,
        as_of_date=as_of_date,
        data_cutoff_date=data_cutoff_date,
        source_vintage=source_vintage,
        update_mode=update_mode,
        forecast_horizon_years=row.year - forecast_origin_year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_row_count=train_row_count,
        train_county_count=train_county_count,
        forecast_population=row.population,
        population_source_id=population_row.source_id,
        population_vintage=population_row.vintage,
        population_feature_quality_flags=population_row.feature_quality_flags,
        predicted_cases=_round(predicted_cases),
        predicted_incidence_per_100k=_round(predicted_incidence),
        model_feature_quality_flags=row.model_feature_quality_flags,
        forecast_assumption_flags=flags,
    )


def _county_trailing_mean(row: _DesignRow, train_rows: list[_DesignRow]) -> float:
    county_rows = [
        prior.incidence_per_100k
        for prior in train_rows
        if prior.county_fips == row.county_fips
    ]
    if not county_rows:
        state_rows = [prior.incidence_per_100k for prior in train_rows]
        return mean(state_rows) if state_rows else 0.0
    return mean(county_rows)


def _read_forecast_population(
    path: Path,
    *,
    target_year: int,
) -> dict[str, _PopulationRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        required = {
            "county_fips",
            "county_name",
            "year",
            "population",
            "source_id",
            "vintage",
            "feature_quality_flags",
        }
        missing = required - fieldnames
        if missing:
            raise AnnualForecastInputError(
                "missing required forecast population column(s): "
                f"{', '.join(sorted(missing))}"
            )
        rows = {}
        for row in reader:
            year = _parse_int_field(row["year"], "year")
            if year != target_year:
                continue
            county_fips = str(row["county_fips"]).zfill(5)
            rows[county_fips] = _PopulationRow(
                county_fips=county_fips,
                county_name=str(row.get("county_name", "")),
                year=year,
                population=_parse_int_field(row["population"], "population"),
                source_id=str(row["source_id"]),
                vintage=_parse_int_field(row["vintage"], "vintage"),
                feature_quality_flags=str(row.get("feature_quality_flags", "")),
            )
    return rows


def _parse_int_field(value: str, field_name: str) -> int:
    try:
        return int(float(str(value or "").replace(",", "").strip() or "0"))
    except ValueError as exc:
        raise AnnualForecastInputError(f"{field_name} must be an integer") from exc


def _join_flags(*values: str) -> str:
    flags = []
    seen = set()
    for value in values:
        for flag in str(value or "").split(","):
            flag = flag.strip()
            if flag and flag not in seen:
                flags.append(flag)
                seen.add(flag)
    return ",".join(flags)


def _forecast_origin_assumption_flags(value: str) -> str:
    return ",".join(
        flag
        for flag in str(value or "").split(",")
        if flag.strip() in FORECAST_ORIGIN_ASSUMPTION_FLAG_ALLOWLIST
    )


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p").replace("-", "m")
