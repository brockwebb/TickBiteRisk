from __future__ import annotations

import csv
import hashlib
import math
from datetime import date
from dataclasses import dataclass
from pathlib import Path


DIAGNOSTIC_FLAGS = (
    "forecast_vs_observed_research_diagnostic,"
    "partial_state_overlay,"
    "post_forecast_diagnostic,"
    "not_regional_truth,"
    "not_training_feature,"
    "not_public_default,"
    "not_public_maryland_default,"
    "reported_cases_not_stable_true_incidence"
)
REQUIRED_FORECAST_COLUMNS = {
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "forecast_population",
    "predicted_cases",
    "predicted_incidence_per_100k",
    "model_feature_quality_flags",
    "forecast_assumption_flags",
}
REQUIRED_INCIDENCE_COLUMNS = {
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


class RegionalForecastObservedFitInputError(ValueError):
    """Raised when regional forecast/observed fit inputs are invalid."""


@dataclass(frozen=True)
class RegionalForecastObservedFitRun:
    run_id: str
    diagnostic_scope: str
    forecast_predictions_path: str
    forecast_predictions_sha256: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    state_fips: str
    state_abbr: str
    state_name: str
    n_forecast_rows: int
    n_observed_rows: int
    n_matched_counties: int
    diagnostic_flags: str


@dataclass(frozen=True)
class RegionalForecastObservedFitComparison:
    run_id: str
    diagnostic_scope: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    forecast_population: int
    observed_population: int
    predicted_cases: float
    observed_cases: int
    case_residual: float
    absolute_case_error: float
    predicted_incidence_per_100k: float
    observed_incidence_per_100k: float
    incidence_residual_per_100k: float
    absolute_incidence_error_per_100k: float
    model_feature_quality_flags: str
    forecast_assumption_flags: str
    observed_quality_flags: str
    diagnostic_flags: str


@dataclass(frozen=True)
class RegionalForecastObservedFitSummary:
    run_id: str
    diagnostic_scope: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    state_fips: str
    state_abbr: str
    state_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    n_counties: int
    predicted_total_cases: float
    observed_total_cases: float
    case_total_residual: float
    mean_case_residual: float
    mae_cases: float
    rmse_cases: float
    predicted_population: int
    observed_population: int
    predicted_incidence_per_100k: float
    observed_incidence_per_100k: float
    incidence_residual_per_100k: float
    mean_incidence_residual_per_100k: float
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    under_prediction_count: int
    over_prediction_count: int
    exact_prediction_count: int
    diagnostic_flags: str


@dataclass(frozen=True)
class RegionalForecastObservedFitResult:
    run_id: str
    run: RegionalForecastObservedFitRun
    comparisons: list[RegionalForecastObservedFitComparison]
    summary: list[RegionalForecastObservedFitSummary]


@dataclass(frozen=True)
class _ForecastRow:
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    forecast_year: int
    forecast_origin_year: int
    as_of_date: str
    data_cutoff_date: str
    source_vintage: str
    update_mode: str
    forecast_population: int
    predicted_cases: float
    predicted_incidence_per_100k: float
    model_feature_quality_flags: str
    forecast_assumption_flags: str


@dataclass(frozen=True)
class _ObservedRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    population: int
    incidence_per_100k: float
    feature_quality_flags: str


def build_regional_forecast_observed_fit(
    *,
    forecast_predictions_path: Path,
    regional_incidence_path: Path,
    forecast_year: int = 2024,
    state_abbr: str = "PA",
    model_name: str = "empirical_bayes_spatial_regime_incidence",
) -> RegionalForecastObservedFitResult:
    normalized_state = state_abbr.strip().upper()
    if not normalized_state:
        raise RegionalForecastObservedFitInputError("state_abbr is required")
    if forecast_year < 1:
        raise RegionalForecastObservedFitInputError("forecast_year must be positive")
    if not model_name.strip():
        raise RegionalForecastObservedFitInputError("model_name is required")

    forecast_rows = _read_forecast_rows(
        forecast_predictions_path,
        forecast_year=forecast_year,
        state_abbr=normalized_state,
        model_name=model_name,
    )
    observed_rows = _read_observed_rows(
        regional_incidence_path,
        forecast_year=forecast_year,
        state_abbr=normalized_state,
    )
    if not forecast_rows:
        raise RegionalForecastObservedFitInputError(
            "no selected regional forecast rows were found"
        )
    if not observed_rows:
        raise RegionalForecastObservedFitInputError(
            "no selected observed incidence rows were found"
        )

    forecasts_by_county = _unique_forecasts_by_county(forecast_rows)
    observed_by_county = _unique_observed_by_county(observed_rows)
    _validate_state_source_overlay_rows(observed_rows)
    _validate_forecast_pre_observed_rows(forecast_rows, forecast_year)
    missing_forecasts = sorted(set(observed_by_county) - set(forecasts_by_county))
    if missing_forecasts:
        raise RegionalForecastObservedFitInputError(
            "missing selected forecast rows for observed county FIPS: "
            + ", ".join(missing_forecasts)
        )
    missing_observed = sorted(set(forecasts_by_county) - set(observed_by_county))
    if missing_observed:
        raise RegionalForecastObservedFitInputError(
            "missing selected observed rows for forecast county FIPS: "
            + ", ".join(missing_observed)
        )

    first = forecast_rows[0]
    _validate_consistent_forecast_metadata(forecast_rows)
    diagnostic_scope = f"{normalized_state.lower()}_{forecast_year}_partial_state_overlay"
    run_id = (
        f"regional_forecast_observed_fit_{normalized_state.lower()}"
        f"{forecast_year}_origin{first.forecast_origin_year}_{model_name}"
    )
    comparisons = [
        _comparison_row(
            run_id=run_id,
            diagnostic_scope=diagnostic_scope,
            forecast=forecasts_by_county[county_fips],
            observed=observed,
        )
        for county_fips, observed in sorted(observed_by_county.items())
    ]
    summary = [_summary_row(run_id, diagnostic_scope, comparisons)]
    run = RegionalForecastObservedFitRun(
        run_id=run_id,
        diagnostic_scope=diagnostic_scope,
        forecast_predictions_path=str(forecast_predictions_path),
        forecast_predictions_sha256=_sha256_file(forecast_predictions_path),
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=_sha256_file(regional_incidence_path),
        source_forecast_run_id=first.source_forecast_run_id,
        model_name=first.model_name,
        model_family=first.model_family,
        target_definition=first.target_definition,
        feature_set=first.feature_set,
        feature_profile=first.feature_profile,
        evaluation_mode=first.evaluation_mode,
        forecast_year=forecast_year,
        forecast_origin_year=first.forecast_origin_year,
        as_of_date=first.as_of_date,
        data_cutoff_date=first.data_cutoff_date,
        source_vintage=first.source_vintage,
        update_mode=first.update_mode,
        state_fips=first.state_fips,
        state_abbr=first.state_abbr,
        state_name=first.state_name,
        n_forecast_rows=len(forecast_rows),
        n_observed_rows=len(observed_rows),
        n_matched_counties=len(comparisons),
        diagnostic_flags=_joined_comparison_flags(comparisons),
    )
    return RegionalForecastObservedFitResult(
        run_id=run_id,
        run=run,
        comparisons=comparisons,
        summary=summary,
    )


def _comparison_row(
    *,
    run_id: str,
    diagnostic_scope: str,
    forecast: _ForecastRow,
    observed: _ObservedRow,
) -> RegionalForecastObservedFitComparison:
    case_residual = _round(observed.total_cases - forecast.predicted_cases)
    incidence_residual = _round(
        observed.incidence_per_100k - forecast.predicted_incidence_per_100k
    )
    flags = _join_flags(
        DIAGNOSTIC_FLAGS,
        forecast.forecast_assumption_flags,
        observed.feature_quality_flags,
    )
    return RegionalForecastObservedFitComparison(
        run_id=run_id,
        diagnostic_scope=diagnostic_scope,
        source_forecast_run_id=forecast.source_forecast_run_id,
        model_name=forecast.model_name,
        model_family=forecast.model_family,
        target_definition=forecast.target_definition,
        feature_set=forecast.feature_set,
        feature_profile=forecast.feature_profile,
        evaluation_mode=forecast.evaluation_mode,
        state_fips=forecast.state_fips,
        state_abbr=forecast.state_abbr,
        state_name=forecast.state_name,
        county_fips=forecast.county_fips,
        county_name=forecast.county_name,
        forecast_year=forecast.forecast_year,
        forecast_origin_year=forecast.forecast_origin_year,
        as_of_date=forecast.as_of_date,
        data_cutoff_date=forecast.data_cutoff_date,
        source_vintage=forecast.source_vintage,
        update_mode=forecast.update_mode,
        forecast_population=forecast.forecast_population,
        observed_population=observed.population,
        predicted_cases=_round(forecast.predicted_cases),
        observed_cases=observed.total_cases,
        case_residual=case_residual,
        absolute_case_error=abs(case_residual),
        predicted_incidence_per_100k=_round(forecast.predicted_incidence_per_100k),
        observed_incidence_per_100k=_round(observed.incidence_per_100k),
        incidence_residual_per_100k=incidence_residual,
        absolute_incidence_error_per_100k=abs(incidence_residual),
        model_feature_quality_flags=forecast.model_feature_quality_flags,
        forecast_assumption_flags=forecast.forecast_assumption_flags,
        observed_quality_flags=observed.feature_quality_flags,
        diagnostic_flags=flags,
    )


def _summary_row(
    run_id: str,
    diagnostic_scope: str,
    comparisons: list[RegionalForecastObservedFitComparison],
) -> RegionalForecastObservedFitSummary:
    if not comparisons:
        raise RegionalForecastObservedFitInputError(
            "regional forecast observed fit has no matched comparison rows"
        )
    first = comparisons[0]
    predicted_total_cases = _round(sum(row.predicted_cases for row in comparisons))
    observed_total_cases = _round(sum(row.observed_cases for row in comparisons))
    case_residuals = [row.case_residual for row in comparisons]
    incidence_residuals = [row.incidence_residual_per_100k for row in comparisons]
    predicted_population = sum(row.forecast_population for row in comparisons)
    observed_population = sum(row.observed_population for row in comparisons)
    if predicted_population <= 0 or observed_population <= 0:
        raise RegionalForecastObservedFitInputError(
            "summary populations must be positive"
        )
    predicted_incidence = _round(predicted_total_cases * 100000 / predicted_population)
    observed_incidence = _round(observed_total_cases * 100000 / observed_population)
    return RegionalForecastObservedFitSummary(
        run_id=run_id,
        diagnostic_scope=diagnostic_scope,
        source_forecast_run_id=first.source_forecast_run_id,
        model_name=first.model_name,
        model_family=first.model_family,
        target_definition=first.target_definition,
        feature_set=first.feature_set,
        feature_profile=first.feature_profile,
        evaluation_mode=first.evaluation_mode,
        state_fips=first.state_fips,
        state_abbr=first.state_abbr,
        state_name=first.state_name,
        forecast_year=first.forecast_year,
        forecast_origin_year=first.forecast_origin_year,
        as_of_date=first.as_of_date,
        data_cutoff_date=first.data_cutoff_date,
        source_vintage=first.source_vintage,
        update_mode=first.update_mode,
        n_counties=len(comparisons),
        predicted_total_cases=predicted_total_cases,
        observed_total_cases=observed_total_cases,
        case_total_residual=_round(observed_total_cases - predicted_total_cases),
        mean_case_residual=_mean(case_residuals),
        mae_cases=_mean([row.absolute_case_error for row in comparisons]),
        rmse_cases=_rmse(case_residuals),
        predicted_population=predicted_population,
        observed_population=observed_population,
        predicted_incidence_per_100k=predicted_incidence,
        observed_incidence_per_100k=observed_incidence,
        incidence_residual_per_100k=_round(observed_incidence - predicted_incidence),
        mean_incidence_residual_per_100k=_mean(incidence_residuals),
        mae_incidence_per_100k=_mean(
            [row.absolute_incidence_error_per_100k for row in comparisons]
        ),
        rmse_incidence_per_100k=_rmse(incidence_residuals),
        under_prediction_count=sum(row.case_residual > 0 for row in comparisons),
        over_prediction_count=sum(row.case_residual < 0 for row in comparisons),
        exact_prediction_count=sum(row.case_residual == 0 for row in comparisons),
        diagnostic_flags=_joined_comparison_flags(comparisons),
    )


def _read_forecast_rows(
    path: Path,
    *,
    forecast_year: int,
    state_abbr: str,
    model_name: str,
) -> list[_ForecastRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_FORECAST_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalForecastObservedFitInputError(
                "missing regional forecast columns: " + ", ".join(sorted(missing))
            )
        rows = []
        for row in reader:
            if str(row["state_abbr"]).strip().upper() != state_abbr:
                continue
            if str(row["model_name"]).strip() != model_name:
                continue
            if _parse_int(row["forecast_year"], "forecast_year") != forecast_year:
                continue
            rows.append(
                _ForecastRow(
                    source_forecast_run_id=str(row["run_id"]),
                    model_name=str(row["model_name"]),
                    model_family=str(row["model_family"]),
                    target_definition=str(row["target_definition"]),
                    feature_set=str(row["feature_set"]),
                    feature_profile=str(row["feature_profile"]),
                    evaluation_mode=str(row["evaluation_mode"]),
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    forecast_year=forecast_year,
                    forecast_origin_year=_parse_int(
                        row["forecast_origin_year"],
                        "forecast_origin_year",
                    ),
                    as_of_date=str(row["as_of_date"]),
                    data_cutoff_date=str(row["data_cutoff_date"]),
                    source_vintage=str(row["source_vintage"]),
                    update_mode=str(row["update_mode"]),
                    forecast_population=_parse_positive_int(
                        row["forecast_population"],
                        "forecast_population",
                    ),
                    predicted_cases=_parse_nonnegative_float(
                        row["predicted_cases"],
                        "predicted_cases",
                    ),
                    predicted_incidence_per_100k=_parse_nonnegative_float(
                        row["predicted_incidence_per_100k"],
                        "predicted_incidence_per_100k",
                    ),
                    model_feature_quality_flags=str(
                        row.get("model_feature_quality_flags", "")
                    ),
                    forecast_assumption_flags=str(
                        row.get("forecast_assumption_flags", "")
                    ),
                )
            )
    return sorted(rows, key=lambda row: row.county_fips)


def _read_observed_rows(
    path: Path,
    *,
    forecast_year: int,
    state_abbr: str,
) -> list[_ObservedRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_INCIDENCE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalForecastObservedFitInputError(
                "missing regional incidence columns: " + ", ".join(sorted(missing))
            )
        rows = []
        for row in reader:
            if str(row["state_abbr"]).strip().upper() != state_abbr:
                continue
            if _parse_int(row["year"], "year") != forecast_year:
                continue
            rows.append(
                _ObservedRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    year=forecast_year,
                    total_cases=_parse_nonnegative_int(
                        row["total_cases"],
                        "total_cases",
                    ),
                    population=_parse_positive_int(row["population"], "population"),
                    incidence_per_100k=_parse_nonnegative_float(
                        row["incidence_per_100k"],
                        "incidence_per_100k",
                    ),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
            )
    return sorted(rows, key=lambda row: row.county_fips)


def _unique_forecasts_by_county(rows: list[_ForecastRow]) -> dict[str, _ForecastRow]:
    by_county: dict[str, _ForecastRow] = {}
    duplicates = set()
    for row in rows:
        if row.county_fips in by_county:
            duplicates.add(row.county_fips)
        by_county[row.county_fips] = row
    if duplicates:
        raise RegionalForecastObservedFitInputError(
            "multiple selected forecast rows for county FIPS: "
            + ", ".join(sorted(duplicates))
        )
    return by_county


def _unique_observed_by_county(rows: list[_ObservedRow]) -> dict[str, _ObservedRow]:
    by_county: dict[str, _ObservedRow] = {}
    duplicates = set()
    for row in rows:
        if row.county_fips in by_county:
            duplicates.add(row.county_fips)
        by_county[row.county_fips] = row
    if duplicates:
        raise RegionalForecastObservedFitInputError(
            "multiple selected observed rows for county FIPS: "
            + ", ".join(sorted(duplicates))
        )
    return by_county


def _validate_consistent_forecast_metadata(rows: list[_ForecastRow]) -> None:
    fields = (
        "source_forecast_run_id",
        "model_name",
        "model_family",
        "target_definition",
        "feature_set",
        "feature_profile",
        "evaluation_mode",
        "forecast_year",
        "forecast_origin_year",
        "as_of_date",
        "data_cutoff_date",
        "source_vintage",
        "update_mode",
        "state_fips",
        "state_abbr",
        "state_name",
    )
    for field in fields:
        values = {getattr(row, field) for row in rows}
        if len(values) > 1:
            raise RegionalForecastObservedFitInputError(
                f"selected forecast rows have multiple {field} values"
            )


def _validate_state_source_overlay_rows(rows: list[_ObservedRow]) -> None:
    bad_counties = [
        row.county_fips
        for row in rows
        if "state_source_not_cdc_public_use"
        not in _quality_flag_set(row.feature_quality_flags)
    ]
    if bad_counties:
        raise RegionalForecastObservedFitInputError(
            "selected observed rows must carry state_source_not_cdc_public_use: "
            + ", ".join(sorted(bad_counties))
        )


def _validate_forecast_pre_observed_rows(
    rows: list[_ForecastRow],
    forecast_year: int,
) -> None:
    bad_update_modes = sorted(
        {
            row.update_mode
            for row in rows
            if row.update_mode.strip().lower() != "pre_update"
        }
    )
    if bad_update_modes:
        raise RegionalForecastObservedFitInputError(
            "selected forecast rows must have update_mode pre_update"
        )
    bad_origin_counties = [
        row.county_fips for row in rows if row.forecast_origin_year >= forecast_year
    ]
    if bad_origin_counties:
        raise RegionalForecastObservedFitInputError(
            "forecast_origin_year must be before forecast_year for county FIPS: "
            + ", ".join(sorted(bad_origin_counties))
        )
    for row in rows:
        try:
            cutoff = date.fromisoformat(row.data_cutoff_date)
        except ValueError as exc:
            raise RegionalForecastObservedFitInputError(
                "data_cutoff_date must be before forecast_year and use ISO YYYY-MM-DD"
            ) from exc
        if cutoff >= date(forecast_year, 1, 1):
            raise RegionalForecastObservedFitInputError(
                "data_cutoff_date must be before forecast_year"
            )


def _quality_flag_set(value: str) -> set[str]:
    return {flag.strip() for flag in str(value or "").split(",") if flag.strip()}


def _joined_comparison_flags(
    comparisons: list[RegionalForecastObservedFitComparison],
) -> str:
    return _join_flags(*(row.diagnostic_flags for row in comparisons))


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


def _mean(values: list[float]) -> float:
    return _round(sum(values) / len(values))


def _rmse(values: list[float]) -> float:
    return _round(math.sqrt(sum(value**2 for value in values) / len(values)))


def _parse_int(value: str, field_name: str) -> int:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalForecastObservedFitInputError(f"{field_name} must be an integer")
    number = float(cleaned)
    if not math.isfinite(number) or not number.is_integer():
        raise RegionalForecastObservedFitInputError(f"{field_name} must be an integer")
    return int(number)


def _parse_nonnegative_int(value: str, field_name: str) -> int:
    number = _parse_int(value, field_name)
    if number < 0:
        raise RegionalForecastObservedFitInputError(
            f"{field_name} must be non-negative"
        )
    return number


def _parse_positive_int(value: str, field_name: str) -> int:
    number = _parse_int(value, field_name)
    if number <= 0:
        raise RegionalForecastObservedFitInputError(f"{field_name} must be positive")
    return number


def _parse_float(value: str, field_name: str) -> float:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalForecastObservedFitInputError(f"{field_name} must be numeric")
    number = float(cleaned)
    if not math.isfinite(number):
        raise RegionalForecastObservedFitInputError(f"{field_name} must be finite")
    return float(number)


def _parse_nonnegative_float(value: str, field_name: str) -> float:
    number = _parse_float(value, field_name)
    if number < 0:
        raise RegionalForecastObservedFitInputError(
            f"{field_name} must be non-negative"
        )
    return number


def _round(value: float) -> float:
    return round(float(value), 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
