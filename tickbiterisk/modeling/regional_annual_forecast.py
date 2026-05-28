from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


FORECAST_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_forecast,"
    "not_public_maryland_default,"
    "population_denominator_forecast,"
    "forecast_without_observed_target"
)
EVALUATION_MODE = "regional_annual_forecast_no_observed_target"
TARGET_DEFINITION = "reported_lyme_incidence_per_100k"
FEATURE_SET = "historical_incidence_forecast_baselines"
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
REQUIRED_REGIONAL_POPULATION_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "population",
    "source_id",
    "vintage",
    "feature_quality_flags",
}
MODEL_SPECS = (
    "latest_observed_county_incidence",
    "trailing_mean_county_incidence",
    "empirical_bayes_state_incidence",
    "empirical_bayes_midatlantic_incidence",
)
FORECAST_ORIGIN_ASSUMPTION_FLAG_ALLOWLIST = {
    "covid_reporting_disruption",
    "lyme_case_definition_change",
    "reported_cases_not_stable_true_incidence",
    "regional_expansion_stress_test",
    "not_public_maryland_default",
    "cdc_dashboard_total_cases",
}


class RegionalAnnualForecastInputError(ValueError):
    """Raised when regional annual forecast inputs cannot produce rows."""


@dataclass(frozen=True)
class RegionalAnnualForecastRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    regional_population_path: str
    regional_population_sha256: str
    target_year: int
    forecast_origin_year: int
    min_train_years: int
    lookback_years: int
    shrinkage_strength: float
    model_names: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    n_training_rows: int
    n_forecast_counties: int
    n_forecast_rows: int
    forecast_assumption_flags: str


@dataclass(frozen=True)
class RegionalAnnualForecastPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    regional_incidence_sha256: str
    regional_population_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    forecast_horizon_years: int
    train_start_year: int
    train_end_year: int
    train_year_count: int
    forecast_population: int
    population_source_id: str
    population_vintage: int
    population_feature_quality_flags: str
    predicted_cases: float
    predicted_incidence_per_100k: float
    model_feature_quality_flags: str
    forecast_assumption_flags: str


@dataclass(frozen=True)
class RegionalAnnualForecastResult:
    run_id: str
    run: RegionalAnnualForecastRun
    predictions: list[RegionalAnnualForecastPrediction]


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
class _PopulationRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    population: int
    source_id: str
    vintage: int
    feature_quality_flags: str


def build_regional_annual_forecast(
    *,
    regional_incidence_path: Path,
    population_path: Path,
    target_year: int = 2026,
    forecast_origin_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 3,
    shrinkage_strength: float = 5.0,
) -> RegionalAnnualForecastResult:
    if min_train_years < 1:
        raise RegionalAnnualForecastInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise RegionalAnnualForecastInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )
    if not math.isfinite(shrinkage_strength) or shrinkage_strength < 0:
        raise RegionalAnnualForecastInputError(
            "shrinkage_strength must be finite and non-negative"
        )

    rows = _read_incidence_rows(regional_incidence_path)
    if not rows:
        raise RegionalAnnualForecastInputError(
            "regional incidence panel has no input rows"
        )
    usable_origin_rows = [row for row in rows if row.incidence_per_100k is not None]
    if not usable_origin_rows:
        raise RegionalAnnualForecastInputError(
            "regional incidence panel has no usable incidence rows"
        )
    resolved_origin_year = (
        forecast_origin_year
        if forecast_origin_year is not None
        else max(row.year for row in usable_origin_rows)
    )
    if target_year <= resolved_origin_year:
        raise RegionalAnnualForecastInputError(
            "target-year must be greater than forecast-origin-year"
        )
    population = _read_population_rows(population_path, target_year=target_year)
    if not population:
        raise RegionalAnnualForecastInputError(
            "population panel has no target-year rows"
        )

    regional_incidence_sha = _sha256_file(regional_incidence_path)
    population_sha = _sha256_file(population_path)
    run_id = (
        f"regional_annual_forecast_target{target_year}_"
        f"origin{resolved_origin_year}_mintrain{min_train_years}_"
        f"lookback{lookback_years}_shrink{_slug_float(shrinkage_strength)}"
    )
    rows_by_county = _group_by_county(rows)
    forecast_rows = _forecast_rows(
        rows=rows,
        rows_by_county=rows_by_county,
        population=population,
        target_year=target_year,
        forecast_origin_year=resolved_origin_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        shrinkage_strength=shrinkage_strength,
        run_id=run_id,
        regional_incidence_sha=regional_incidence_sha,
        population_sha=population_sha,
    )
    if not forecast_rows:
        raise RegionalAnnualForecastInputError(
            "no forecast rows with sufficient history and target-year population"
        )
    training_window_start = resolved_origin_year - lookback_years + 1
    run = RegionalAnnualForecastRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=regional_incidence_sha,
        regional_population_path=str(population_path),
        regional_population_sha256=population_sha,
        target_year=target_year,
        forecast_origin_year=resolved_origin_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        shrinkage_strength=shrinkage_strength,
        model_names=",".join(sorted({row.model_name for row in forecast_rows})),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        n_training_rows=len(
            [
                row
                for row in rows
                if training_window_start <= row.year <= resolved_origin_year
                and row.incidence_per_100k is not None
            ]
        ),
        n_forecast_counties=len({row.county_fips for row in forecast_rows}),
        n_forecast_rows=len(forecast_rows),
        forecast_assumption_flags=FORECAST_ASSUMPTION_FLAGS,
    )
    return RegionalAnnualForecastResult(
        run_id=run_id,
        run=run,
        predictions=forecast_rows,
    )


def _forecast_rows(
    *,
    rows: list[_IncidenceRow],
    rows_by_county: dict[str, list[_IncidenceRow]],
    population: dict[str, _PopulationRow],
    target_year: int,
    forecast_origin_year: int,
    min_train_years: int,
    lookback_years: int,
    shrinkage_strength: float,
    run_id: str,
    regional_incidence_sha: str,
    population_sha: str,
) -> list[RegionalAnnualForecastPrediction]:
    predictions = []
    window_start = forecast_origin_year - lookback_years + 1
    regional_history = [
        row
        for row in rows
        if window_start <= row.year <= forecast_origin_year
        and row.incidence_per_100k is not None
    ]
    for county_fips in sorted(rows_by_county):
        population_row = population.get(county_fips)
        if population_row is None or population_row.population <= 0:
            continue
        county_history = [
            row
            for row in rows_by_county[county_fips]
            if window_start <= row.year <= forecast_origin_year
            and row.incidence_per_100k is not None
        ]
        if len(county_history) < min_train_years:
            continue
        latest = county_history[-1]
        if latest.year != forecast_origin_year:
            continue
        state_history = [
            row
            for row in regional_history
            if row.state_fips == latest.state_fips
        ]
        model_predictions = _predict_models(
            county_history=county_history,
            state_history=state_history,
            regional_history=regional_history,
            shrinkage_strength=shrinkage_strength,
        )
        flags = _join_flags(
            FORECAST_ASSUMPTION_FLAGS,
            _forecast_origin_assumption_flags(latest.feature_quality_flags),
            population_row.feature_quality_flags,
        )
        for model_name in MODEL_SPECS:
            predictions.append(
                _prediction_row(
                    run_id=run_id,
                    model_name=model_name,
                    latest=latest,
                    population_row=population_row,
                    target_year=target_year,
                    forecast_origin_year=forecast_origin_year,
                    train_start_year=min(row.year for row in county_history),
                    train_end_year=max(row.year for row in county_history),
                    train_year_count=len(county_history),
                    predicted_incidence=model_predictions[model_name],
                    regional_incidence_sha=regional_incidence_sha,
                    population_sha=population_sha,
                    flags=flags,
                )
            )
    return sorted(
        predictions,
        key=lambda row: (row.forecast_year, row.model_name, row.county_fips),
    )


def _predict_models(
    *,
    county_history: list[_IncidenceRow],
    state_history: list[_IncidenceRow],
    regional_history: list[_IncidenceRow],
    shrinkage_strength: float,
) -> dict[str, float]:
    latest = _known_incidence(county_history[-1])
    county_mean = mean(_known_incidence(row) for row in county_history)
    state_mean = (
        mean(_known_incidence(row) for row in state_history)
        if state_history
        else county_mean
    )
    regional_mean = (
        mean(_known_incidence(row) for row in regional_history)
        if regional_history
        else county_mean
    )
    return {
        "latest_observed_county_incidence": latest,
        "trailing_mean_county_incidence": county_mean,
        "empirical_bayes_state_incidence": _shrunk_mean(
            county_mean=county_mean,
            county_n=len(county_history),
            prior_mean=state_mean,
            prior_strength=shrinkage_strength,
        ),
        "empirical_bayes_midatlantic_incidence": _shrunk_mean(
            county_mean=county_mean,
            county_n=len(county_history),
            prior_mean=regional_mean,
            prior_strength=shrinkage_strength,
        ),
    }


def _prediction_row(
    *,
    run_id: str,
    model_name: str,
    latest: _IncidenceRow,
    population_row: _PopulationRow,
    target_year: int,
    forecast_origin_year: int,
    train_start_year: int,
    train_end_year: int,
    train_year_count: int,
    predicted_incidence: float,
    regional_incidence_sha: str,
    population_sha: str,
    flags: str,
) -> RegionalAnnualForecastPrediction:
    predicted_incidence = _round(max(predicted_incidence, 0.0))
    predicted_cases = _round(predicted_incidence * population_row.population / 100000)
    return RegionalAnnualForecastPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family=_model_family(model_name),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        feature_profile=_feature_profile(model_name),
        evaluation_mode=EVALUATION_MODE,
        regional_incidence_sha256=regional_incidence_sha,
        regional_population_sha256=population_sha,
        state_fips=latest.state_fips,
        state_abbr=latest.state_abbr,
        state_name=latest.state_name,
        county_fips=latest.county_fips,
        county_name=latest.county_name,
        forecast_year=target_year,
        forecast_origin_year=forecast_origin_year,
        forecast_horizon_years=target_year - forecast_origin_year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=train_year_count,
        forecast_population=population_row.population,
        population_source_id=population_row.source_id,
        population_vintage=population_row.vintage,
        population_feature_quality_flags=population_row.feature_quality_flags,
        predicted_cases=predicted_cases,
        predicted_incidence_per_100k=predicted_incidence,
        model_feature_quality_flags=latest.feature_quality_flags,
        forecast_assumption_flags=flags,
    )


def _read_incidence_rows(path: Path) -> list[_IncidenceRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_INCIDENCE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalAnnualForecastInputError(
                f"missing regional incidence panel columns: {sorted(missing)}"
            )
        return sorted(
            [
                _IncidenceRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    year=_parse_int(row["year"], "year"),
                    total_cases=_parse_int(row["total_cases"], "total_cases"),
                    population=_parse_optional_int(row.get("population", "")),
                    incidence_per_100k=_parse_optional_float(
                        row.get("incidence_per_100k", ""),
                        "incidence_per_100k",
                    ),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _read_population_rows(path: Path, *, target_year: int) -> dict[str, _PopulationRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_POPULATION_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalAnnualForecastInputError(
                f"missing regional population panel columns: {sorted(missing)}"
            )
        rows = {}
        for row in reader:
            year = _parse_int(row["year"], "year")
            if year != target_year:
                continue
            county_fips = row["county_fips"].zfill(5)
            rows[county_fips] = _PopulationRow(
                state_fips=row["state_fips"].zfill(2),
                state_abbr=str(row["state_abbr"]),
                state_name=str(row["state_name"]),
                county_fips=county_fips,
                county_name=str(row["county_name"]),
                year=year,
                population=_parse_int(row["population"], "population"),
                source_id=str(row["source_id"]),
                vintage=_parse_int(row["vintage"], "vintage"),
                feature_quality_flags=str(row.get("feature_quality_flags", "")),
            )
    return rows


def _group_by_county(rows: list[_IncidenceRow]) -> dict[str, list[_IncidenceRow]]:
    grouped: dict[str, list[_IncidenceRow]] = {}
    for row in rows:
        grouped.setdefault(row.county_fips, []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: row.year)
        for county_fips, county_rows in grouped.items()
    }


def _known_incidence(row: _IncidenceRow) -> float:
    if row.incidence_per_100k is None:
        raise RegionalAnnualForecastInputError(
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
    if prior_strength == 0:
        return county_mean
    return (county_n * county_mean + prior_strength * prior_mean) / (
        county_n + prior_strength
    )


def _model_family(model_name: str) -> str:
    if model_name.startswith("empirical_bayes_"):
        return "empirical_bayes_incidence_shrinkage"
    return "county_incidence_baseline"


def _feature_profile(model_name: str) -> str:
    return {
        "latest_observed_county_incidence": "latest_observed_origin_incidence",
        "trailing_mean_county_incidence": "trailing_county_incidence",
        "empirical_bayes_state_incidence": "state_shrunken_incidence",
        "empirical_bayes_midatlantic_incidence": "midatlantic_shrunken_incidence",
    }[model_name]


def _join_flags(*values: str) -> str:
    flags = []
    seen = set()
    for value in values:
        for raw_flag in str(value or "").split(","):
            flag = raw_flag.strip()
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


def _parse_int(value: str, field_name: str) -> int:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalAnnualForecastInputError(f"{field_name} must be an integer")
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise RegionalAnnualForecastInputError(
            f"{field_name} must be an integer"
        ) from exc
    if not math.isfinite(number) or not number.is_integer():
        raise RegionalAnnualForecastInputError(f"{field_name} must be an integer")
    return int(number)


def _parse_optional_int(value: str) -> int | None:
    if str(value or "").strip() == "":
        return None
    return _parse_int(value, "integer value")


def _parse_optional_float(value: str, field_name: str) -> float | None:
    if str(value or "").strip() == "":
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise RegionalAnnualForecastInputError(
            f"{field_name} must be numeric"
        ) from exc
    if not math.isfinite(number):
        raise RegionalAnnualForecastInputError(f"{field_name} must be finite")
    return number


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p").replace("-", "m")


def _round(value: float) -> float:
    return round(float(value), 6)
