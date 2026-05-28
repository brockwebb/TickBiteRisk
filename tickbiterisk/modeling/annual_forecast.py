from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from tickbiterisk.modeling.model_compare import (
    LAGGED_WEATHER_MODE,
    ModelComparisonInputError,
    TARGET_DEFINITION,
    _DesignRow,
    _empirical_bayes_prediction,
    _has_training_depth,
    _read_design_rows,
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
)
FORECAST_ORIGIN_ASSUMPTION_FLAG_ALLOWLIST = {
    "covid_reporting_disruption",
    "lyme_case_definition_change",
    "mdh_probable_only_2024",
    "state_source_not_cdc_public_use",
    "reported_cases_not_stable_true_incidence",
}


class AnnualForecastInputError(ValueError):
    """Raised when annual forecast inputs cannot produce forecast rows."""


@dataclass(frozen=True)
class AnnualForecastRun:
    run_id: str
    design_matrix_path: str
    design_matrix_sha256: str
    population_path: str
    population_sha256: str
    target_year: int
    forecast_origin_year: int
    min_train_years: int
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
    target_year: int,
    forecast_origin_year: int,
    min_train_years: int = 5,
    shrinkage_strength: float = 5.0,
) -> AnnualForecastResult:
    if target_year <= forecast_origin_year:
        raise AnnualForecastInputError(
            "target-year must be greater than forecast-origin-year"
        )
    if min_train_years < 1:
        raise AnnualForecastInputError("min_train_years must be at least 1")
    if shrinkage_strength < 0:
        raise AnnualForecastInputError("shrinkage_strength must be non-negative")

    rows, _feature_columns = _read_training_design_rows(design_matrix_path)
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
    )
    if not forecast_rows:
        raise AnnualForecastInputError("no forecast rows with target-year population")

    source_sha = _sha256_file(design_matrix_path)
    population_sha = _sha256_file(population_path)
    train_start_year = min(row.year for row in train_rows)
    train_end_year = max(row.year for row in train_rows)
    train_county_count = len({row.county_fips for row in train_rows})
    run_id = (
        f"annual_forecast_target{target_year}_origin{forecast_origin_year}_"
        f"mintrain{min_train_years}_shrink{_slug_float(shrinkage_strength)}"
    )
    predictions = []
    for row, population_row in forecast_rows:
        for model_name, model_family, feature_profile, predicted in _forecast_models(
            row=row,
            train_rows=train_rows,
            shrinkage_strength=shrinkage_strength,
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
        target_year=target_year,
        forecast_origin_year=forecast_origin_year,
        min_train_years=min_train_years,
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
    shrinkage_strength: float,
) -> list[tuple[str, str, str, float]]:
    latest = row.features.get("feature_prior_year_lyme_incidence_per_100k", 0.0)
    trailing = _county_trailing_mean(row, train_rows)
    values = {
        "latest_observed_incidence": latest,
        "trailing_mean_incidence": trailing,
        "linear_blend_baseline": mean([latest, trailing]),
        "empirical_bayes_shrinkage": _empirical_bayes_prediction(
            row,
            train_rows,
            shrinkage_strength,
        ),
    }
    return [
        (model_name, model_family, feature_profile, values[model_name])
        for model_name, model_family, feature_profile in FORECAST_MODEL_SPECS
    ]


def _forecast_design_rows(
    *,
    train_rows: list[_DesignRow],
    population: dict[str, _PopulationRow],
    target_year: int,
    forecast_origin_year: int,
    min_train_years: int,
) -> list[tuple[_DesignRow, _PopulationRow]]:
    rows_by_county: dict[str, list[_DesignRow]] = {}
    for row in sorted(train_rows, key=lambda row: (row.county_fips, row.year)):
        rows_by_county.setdefault(row.county_fips, []).append(row)

    forecast_rows = []
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
            "feature_log_population_offset": latest.features.get(
                "feature_log_population_offset",
                0.0,
            ),
        }
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


def _read_training_design_rows(path: Path) -> tuple[list[_DesignRow], list[str]]:
    try:
        return _read_design_rows(path)
    except ModelComparisonInputError as exc:
        raise AnnualForecastInputError(str(exc)) from exc
    except ValueError as exc:
        raise AnnualForecastInputError(
            f"invalid annual forecast design matrix: {exc}"
        ) from exc


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
        weather_mode=LAGGED_WEATHER_MODE,
        design_matrix_sha256=design_matrix_sha,
        population_sha256=population_sha,
        county_fips=row.county_fips,
        county_name=row.county_name,
        forecast_year=row.year,
        forecast_origin_year=forecast_origin_year,
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
