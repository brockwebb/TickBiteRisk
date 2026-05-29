from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path


INTERVAL_METHOD = "empirical_rolling_origin_residual_quantile"
INTERVAL_ASSUMPTION_FLAGS = (
    "empirical_rolling_origin_residual_interval,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_forecast,"
    "forecast_without_observed_target,"
    "not_public_default"
)
INTERVAL_FEATURE_FLAGS = (
    "forecast_safe_prior_origin_residuals,"
    "residual_test_year_lte_forecast_origin,"
    "not_public_default"
)
SUMMARY_ASSUMPTION_FLAGS = (
    "summed_county_empirical_intervals,"
    "planning_aggregate_not_joint_posterior,"
    "not_public_default"
)
EXPECTED_STRESS_FEATURE_SET = (
    "historical_incidence_shrinkage_analog_random_forest_baselines"
)
EXPECTED_STRESS_EVALUATION_MODE = "rolling_origin_prior_years"
MODEL_RESIDUAL_ALIASES = {
    "latest_observed_county_incidence": "prior_year_county_incidence",
}
REQUIRED_FORECAST_COLUMNS = {
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "regional_incidence_sha256",
    "regional_population_sha256",
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
REQUIRED_STRESS_COLUMNS = {
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "source_file_sha256",
    "test_year",
    "residual_incidence_per_100k",
    "comparison_assumption_flags",
}

REGIONAL_ANNUAL_FORECAST_INTERVAL_RUN_COLUMNS = [
    "run_id",
    "forecast_predictions_path",
    "forecast_predictions_sha256",
    "regional_incidence_stress_predictions_path",
    "regional_incidence_stress_predictions_sha256",
    "source_forecast_run_id",
    "residual_source_run_id",
    "regional_incidence_sha256",
    "forecast_year",
    "forecast_origin_year",
    "interval_method",
    "min_residual_count",
    "model_names",
    "residual_test_start_year",
    "residual_test_end_year",
    "n_forecast_rows",
    "n_interval_rows",
    "interval_assumption_flags",
]

REGIONAL_ANNUAL_FORECAST_INTERVAL_COLUMNS = [
    "run_id",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "regional_incidence_sha256",
    "regional_population_sha256",
    "residual_source_run_id",
    "residual_model_name",
    "residual_source_file_sha256",
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
    "interval_method",
    "residual_count",
    "residual_test_start_year",
    "residual_test_end_year",
    "lower_80_incidence_per_100k",
    "median_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "lower_80_cases",
    "median_cases",
    "upper_80_cases",
    "lower_95_cases",
    "upper_95_cases",
    "interval_feature_quality_flags",
    "interval_assumption_flags",
]

REGIONAL_ANNUAL_FORECAST_INTERVAL_SUMMARY_COLUMNS = [
    "run_id",
    "source_forecast_run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "geography_level",
    "region_id",
    "region_name",
    "forecast_year",
    "forecast_origin_year",
    "interval_method",
    "n_counties",
    "forecast_population",
    "predicted_total_cases",
    "predicted_incidence_per_100k",
    "lower_80_cases",
    "median_cases",
    "upper_80_cases",
    "lower_95_cases",
    "upper_95_cases",
    "lower_80_incidence_per_100k",
    "median_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
    "residual_count_min",
    "residual_count_max",
    "residual_test_start_year",
    "residual_test_end_year",
    "summary_assumption_flags",
]


class RegionalAnnualForecastIntervalInputError(ValueError):
    """Raised when regional annual forecast interval inputs are invalid."""


@dataclass(frozen=True)
class RegionalAnnualForecastIntervalRun:
    run_id: str
    forecast_predictions_path: str
    forecast_predictions_sha256: str
    regional_incidence_stress_predictions_path: str
    regional_incidence_stress_predictions_sha256: str
    source_forecast_run_id: str
    residual_source_run_id: str
    regional_incidence_sha256: str
    forecast_year: int
    forecast_origin_year: int
    interval_method: str
    min_residual_count: int
    model_names: str
    residual_test_start_year: int
    residual_test_end_year: int
    n_forecast_rows: int
    n_interval_rows: int
    interval_assumption_flags: str


@dataclass(frozen=True)
class RegionalAnnualForecastInterval:
    run_id: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    regional_incidence_sha256: str
    regional_population_sha256: str
    residual_source_run_id: str
    residual_model_name: str
    residual_source_file_sha256: str
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
    interval_method: str
    residual_count: int
    residual_test_start_year: int
    residual_test_end_year: int
    lower_80_incidence_per_100k: float
    median_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    lower_80_cases: float
    median_cases: float
    upper_80_cases: float
    lower_95_cases: float
    upper_95_cases: float
    interval_feature_quality_flags: str
    interval_assumption_flags: str


@dataclass(frozen=True)
class RegionalAnnualForecastIntervalSummary:
    run_id: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    geography_level: str
    region_id: str
    region_name: str
    forecast_year: int
    forecast_origin_year: int
    interval_method: str
    n_counties: int
    forecast_population: int
    predicted_total_cases: float
    predicted_incidence_per_100k: float
    lower_80_cases: float
    median_cases: float
    upper_80_cases: float
    lower_95_cases: float
    upper_95_cases: float
    lower_80_incidence_per_100k: float
    median_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    residual_count_min: int
    residual_count_max: int
    residual_test_start_year: int
    residual_test_end_year: int
    summary_assumption_flags: str


@dataclass(frozen=True)
class RegionalAnnualForecastIntervalResult:
    run_id: str
    run: RegionalAnnualForecastIntervalRun
    intervals: list[RegionalAnnualForecastInterval]
    summary: list[RegionalAnnualForecastIntervalSummary]


@dataclass(frozen=True)
class RegionalAnnualForecastIntervalOutputPaths:
    runs_path: Path
    intervals_path: Path
    summary_path: Path


@dataclass(frozen=True)
class _ForecastRow:
    source_forecast_run_id: str
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
class _StressResidual:
    residual_source_run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    source_file_sha256: str
    test_year: int
    residual_incidence_per_100k: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class _ResidualBranch:
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    residuals: list[_StressResidual]


def build_regional_annual_forecast_intervals(
    *,
    forecast_predictions_path: Path,
    regional_incidence_stress_predictions_path: Path,
    min_residual_count: int = 30,
) -> RegionalAnnualForecastIntervalResult:
    if min_residual_count < 1:
        raise RegionalAnnualForecastIntervalInputError(
            "min_residual_count must be at least 1"
        )
    forecast_rows = _read_forecast_rows(forecast_predictions_path)
    if not forecast_rows:
        raise RegionalAnnualForecastIntervalInputError(
            "regional annual forecast predictions have no rows"
        )
    stress_residuals = _read_stress_residuals(
        regional_incidence_stress_predictions_path
    )
    if not stress_residuals:
        raise RegionalAnnualForecastIntervalInputError(
            "regional incidence stress predictions have no residual rows"
        )

    source_forecast_run_id = _single_value(
        {row.source_forecast_run_id for row in forecast_rows},
        "forecast run_id",
    )
    forecast_year = _single_value(
        {row.forecast_year for row in forecast_rows},
        "forecast_year",
    )
    forecast_origin_year = _single_value(
        {row.forecast_origin_year for row in forecast_rows},
        "forecast_origin_year",
    )
    regional_incidence_sha256 = _single_value(
        {row.regional_incidence_sha256 for row in forecast_rows},
        "regional_incidence_sha256",
    )
    residual_source_run_id = _single_value(
        {row.residual_source_run_id for row in stress_residuals},
        "regional incidence stress run_id",
    )
    residual_source_hash = _single_value(
        {row.source_file_sha256 for row in stress_residuals},
        "source_file_sha256",
    )
    if residual_source_hash != regional_incidence_sha256:
        raise RegionalAnnualForecastIntervalInputError(
            "regional incidence stress source_file_sha256 does not match "
            "regional annual forecast regional_incidence_sha256"
        )

    residuals_by_model = _residuals_by_model(
        stress_residuals,
        forecast_origin_year=forecast_origin_year,
    )
    if not residuals_by_model:
        raise RegionalAnnualForecastIntervalInputError(
            "regional incidence stress residuals have no rows at or before "
            "forecast_origin_year"
        )

    forecast_sha = _sha256_file(forecast_predictions_path)
    stress_sha = _sha256_file(regional_incidence_stress_predictions_path)
    run_id = (
        f"regional_annual_forecast_intervals_forecast{forecast_year}_"
        f"origin{forecast_origin_year}_minres{min_residual_count}_"
        f"{forecast_sha[:12]}_{stress_sha[:12]}"
    )
    intervals = [
        _interval_row(
            run_id=run_id,
            row=row,
            residual_source_run_id=residual_source_run_id,
            residual_source_hash=residual_source_hash,
            residuals_by_model=residuals_by_model,
            min_residual_count=min_residual_count,
        )
        for row in forecast_rows
    ]
    residual_test_years = sorted(
        {
            residual.test_year
            for branch in residuals_by_model.values()
            for residual in branch.residuals
        }
    )
    run = RegionalAnnualForecastIntervalRun(
        run_id=run_id,
        forecast_predictions_path=str(forecast_predictions_path),
        forecast_predictions_sha256=forecast_sha,
        regional_incidence_stress_predictions_path=str(
            regional_incidence_stress_predictions_path
        ),
        regional_incidence_stress_predictions_sha256=stress_sha,
        source_forecast_run_id=source_forecast_run_id,
        residual_source_run_id=residual_source_run_id,
        regional_incidence_sha256=regional_incidence_sha256,
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        interval_method=INTERVAL_METHOD,
        min_residual_count=min_residual_count,
        model_names=",".join(sorted({row.model_name for row in intervals})),
        residual_test_start_year=min(residual_test_years),
        residual_test_end_year=max(residual_test_years),
        n_forecast_rows=len(forecast_rows),
        n_interval_rows=len(intervals),
        interval_assumption_flags=INTERVAL_ASSUMPTION_FLAGS,
    )
    intervals = sorted(
        intervals,
        key=lambda row: (
            row.source_forecast_run_id,
            row.model_name,
            row.forecast_year,
            row.forecast_origin_year,
            row.state_fips,
            row.county_fips,
        ),
    )
    return RegionalAnnualForecastIntervalResult(
        run_id=run_id,
        run=run,
        intervals=intervals,
        summary=_summary_rows(intervals),
    )


def write_regional_annual_forecast_interval_outputs(
    result: RegionalAnnualForecastIntervalResult,
    output_dir: Path,
) -> RegionalAnnualForecastIntervalOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "regional_annual_forecast_interval_runs.csv"
    intervals_path = output_dir / "regional_annual_forecast_intervals.csv"
    summary_path = output_dir / "regional_annual_forecast_interval_summary.csv"
    _write_records(
        runs_path,
        [asdict(result.run)],
        REGIONAL_ANNUAL_FORECAST_INTERVAL_RUN_COLUMNS,
    )
    _write_records(
        intervals_path,
        [asdict(row) for row in result.intervals],
        REGIONAL_ANNUAL_FORECAST_INTERVAL_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary],
        REGIONAL_ANNUAL_FORECAST_INTERVAL_SUMMARY_COLUMNS,
    )
    return RegionalAnnualForecastIntervalOutputPaths(
        runs_path=runs_path,
        intervals_path=intervals_path,
        summary_path=summary_path,
    )


def _summary_rows(
    intervals: list[RegionalAnnualForecastInterval],
) -> list[RegionalAnnualForecastIntervalSummary]:
    groups: dict[tuple[str, str, str], list[RegionalAnnualForecastInterval]] = {}
    for interval in intervals:
        for geography_level, region_id in _summary_regions(interval):
            groups.setdefault(
                (interval.model_name, geography_level, region_id),
                [],
            ).append(interval)

    rows = [
        _summary_row(
            geography_level=geography_level,
            region_id=region_id,
            intervals=rows,
        )
        for (_model_name, geography_level, region_id), rows in sorted(groups.items())
    ]
    return sorted(
        rows,
        key=lambda row: (
            row.model_name,
            row.forecast_year,
            row.forecast_origin_year,
            row.geography_level,
            row.region_id,
        ),
    )


def _summary_row(
    *,
    geography_level: str,
    region_id: str,
    intervals: list[RegionalAnnualForecastInterval],
) -> RegionalAnnualForecastIntervalSummary:
    first = intervals[0]
    forecast_population = sum(row.forecast_population for row in intervals)
    predicted_total_cases = _round(sum(row.predicted_cases for row in intervals))
    lower_80_cases = _round(sum(row.lower_80_cases for row in intervals))
    median_cases = _round(sum(row.median_cases for row in intervals))
    upper_80_cases = _round(sum(row.upper_80_cases for row in intervals))
    lower_95_cases = _round(sum(row.lower_95_cases for row in intervals))
    upper_95_cases = _round(sum(row.upper_95_cases for row in intervals))
    return RegionalAnnualForecastIntervalSummary(
        run_id=first.run_id,
        source_forecast_run_id=first.source_forecast_run_id,
        model_name=first.model_name,
        model_family=first.model_family,
        target_definition=first.target_definition,
        feature_set=first.feature_set,
        feature_profile=first.feature_profile,
        evaluation_mode=first.evaluation_mode,
        geography_level=geography_level,
        region_id=region_id,
        region_name=_summary_region_name(
            geography_level,
            region_id,
            intervals,
        ),
        forecast_year=first.forecast_year,
        forecast_origin_year=first.forecast_origin_year,
        interval_method="summed_county_empirical_residual_intervals",
        n_counties=len({row.county_fips for row in intervals}),
        forecast_population=forecast_population,
        predicted_total_cases=predicted_total_cases,
        predicted_incidence_per_100k=_cases_to_incidence(
            predicted_total_cases,
            forecast_population,
        ),
        lower_80_cases=lower_80_cases,
        median_cases=median_cases,
        upper_80_cases=upper_80_cases,
        lower_95_cases=lower_95_cases,
        upper_95_cases=upper_95_cases,
        lower_80_incidence_per_100k=_cases_to_incidence(
            lower_80_cases,
            forecast_population,
        ),
        median_incidence_per_100k=_cases_to_incidence(
            median_cases,
            forecast_population,
        ),
        upper_80_incidence_per_100k=_cases_to_incidence(
            upper_80_cases,
            forecast_population,
        ),
        lower_95_incidence_per_100k=_cases_to_incidence(
            lower_95_cases,
            forecast_population,
        ),
        upper_95_incidence_per_100k=_cases_to_incidence(
            upper_95_cases,
            forecast_population,
        ),
        residual_count_min=min(row.residual_count for row in intervals),
        residual_count_max=max(row.residual_count for row in intervals),
        residual_test_start_year=min(row.residual_test_start_year for row in intervals),
        residual_test_end_year=max(row.residual_test_end_year for row in intervals),
        summary_assumption_flags=_join_flags(
            SUMMARY_ASSUMPTION_FLAGS,
            *(row.interval_assumption_flags for row in intervals),
        ),
    )


def _summary_regions(
    interval: RegionalAnnualForecastInterval,
) -> tuple[tuple[str, str], tuple[str, str]]:
    return (
        ("state", interval.state_fips),
        ("midatlantic", "midatlantic"),
    )


def _summary_region_name(
    geography_level: str,
    region_id: str,
    intervals: list[RegionalAnnualForecastInterval],
) -> str:
    if geography_level == "midatlantic":
        return "DE/DC/MD/PA/VA/WV"
    if geography_level == "state":
        state_names = {row.state_name for row in intervals if row.state_fips == region_id}
        if len(state_names) == 1:
            return next(iter(state_names))
    return region_id


def _interval_row(
    *,
    run_id: str,
    row: _ForecastRow,
    residual_source_run_id: str,
    residual_source_hash: str,
    residuals_by_model: dict[str, _ResidualBranch],
    min_residual_count: int,
) -> RegionalAnnualForecastInterval:
    residual_model_name = MODEL_RESIDUAL_ALIASES.get(row.model_name, row.model_name)
    branch = residuals_by_model.get(residual_model_name)
    residuals = [] if branch is None else branch.residuals
    if len(residuals) < min_residual_count:
        raise RegionalAnnualForecastIntervalInputError(
            f"{row.model_name} requires at least {min_residual_count} "
            f"prior-origin residual rows from {residual_model_name}; found "
            f"{len(residuals)}"
        )
    _validate_residual_branch(row, branch)

    residual_values = [
        residual.residual_incidence_per_100k for residual in residuals
    ]
    lower_80_incidence = _bounded_incidence(
        row.predicted_incidence_per_100k + _quantile(residual_values, 0.10)
    )
    median_incidence = _bounded_incidence(
        row.predicted_incidence_per_100k + _quantile(residual_values, 0.50)
    )
    upper_80_incidence = _bounded_incidence(
        row.predicted_incidence_per_100k + _quantile(residual_values, 0.90)
    )
    lower_95_incidence = _bounded_incidence(
        row.predicted_incidence_per_100k + _quantile(residual_values, 0.025)
    )
    upper_95_incidence = _bounded_incidence(
        row.predicted_incidence_per_100k + _quantile(residual_values, 0.975)
    )
    interval_feature_flags = INTERVAL_FEATURE_FLAGS
    if residual_model_name != row.model_name:
        interval_feature_flags = _join_flags(
            interval_feature_flags,
            f"residual_model_alias_{residual_model_name}",
        )
    residual_years = [residual.test_year for residual in residuals]
    return RegionalAnnualForecastInterval(
        run_id=run_id,
        source_forecast_run_id=row.source_forecast_run_id,
        model_name=row.model_name,
        model_family=row.model_family,
        target_definition=row.target_definition,
        feature_set=row.feature_set,
        feature_profile=row.feature_profile,
        evaluation_mode=row.evaluation_mode,
        regional_incidence_sha256=row.regional_incidence_sha256,
        regional_population_sha256=row.regional_population_sha256,
        residual_source_run_id=residual_source_run_id,
        residual_model_name=residual_model_name,
        residual_source_file_sha256=residual_source_hash,
        state_fips=row.state_fips,
        state_abbr=row.state_abbr,
        state_name=row.state_name,
        county_fips=row.county_fips,
        county_name=row.county_name,
        forecast_year=row.forecast_year,
        forecast_origin_year=row.forecast_origin_year,
        as_of_date=row.as_of_date,
        data_cutoff_date=row.data_cutoff_date,
        source_vintage=row.source_vintage,
        update_mode=row.update_mode,
        forecast_population=row.forecast_population,
        predicted_cases=row.predicted_cases,
        predicted_incidence_per_100k=row.predicted_incidence_per_100k,
        interval_method=INTERVAL_METHOD,
        residual_count=len(residuals),
        residual_test_start_year=min(residual_years),
        residual_test_end_year=max(residual_years),
        lower_80_incidence_per_100k=lower_80_incidence,
        median_incidence_per_100k=median_incidence,
        upper_80_incidence_per_100k=upper_80_incidence,
        lower_95_incidence_per_100k=lower_95_incidence,
        upper_95_incidence_per_100k=upper_95_incidence,
        lower_80_cases=_incidence_to_cases(
            lower_80_incidence,
            row.forecast_population,
        ),
        median_cases=_incidence_to_cases(
            median_incidence,
            row.forecast_population,
        ),
        upper_80_cases=_incidence_to_cases(
            upper_80_incidence,
            row.forecast_population,
        ),
        lower_95_cases=_incidence_to_cases(
            lower_95_incidence,
            row.forecast_population,
        ),
        upper_95_cases=_incidence_to_cases(
            upper_95_incidence,
            row.forecast_population,
        ),
        interval_feature_quality_flags=interval_feature_flags,
        interval_assumption_flags=_join_flags(
            INTERVAL_ASSUMPTION_FLAGS,
            row.forecast_assumption_flags,
        ),
    )


def _residuals_by_model(
    residuals: list[_StressResidual],
    *,
    forecast_origin_year: int,
) -> dict[str, _ResidualBranch]:
    by_model: dict[str, list[_StressResidual]] = {}
    for residual in residuals:
        if residual.test_year > forecast_origin_year:
            continue
        by_model.setdefault(residual.model_name, []).append(residual)
    branches = {}
    for model_name, rows in sorted(by_model.items()):
        metadata = {
            (
                row.model_family,
                row.target_definition,
                row.feature_set,
                row.evaluation_mode,
            )
            for row in rows
        }
        if len(metadata) != 1:
            raise RegionalAnnualForecastIntervalInputError(
                f"mixed residual metadata for {model_name}"
            )
        model_family, target_definition, feature_set, evaluation_mode = next(
            iter(metadata)
        )
        branches[model_name] = _ResidualBranch(
            model_name=model_name,
            model_family=model_family,
            target_definition=target_definition,
            feature_set=feature_set,
            evaluation_mode=evaluation_mode,
            residuals=sorted(rows, key=lambda row: row.test_year),
        )
    return branches


def _validate_residual_branch(
    row: _ForecastRow,
    branch: _ResidualBranch | None,
) -> None:
    if branch is None:
        return
    if branch.model_family != row.model_family:
        raise RegionalAnnualForecastIntervalInputError(
            f"{row.model_name} residual model_family mismatch: "
            f"{branch.model_family} != {row.model_family}"
        )
    if branch.target_definition != row.target_definition:
        raise RegionalAnnualForecastIntervalInputError(
            f"{row.model_name} residual target_definition mismatch: "
            f"{branch.target_definition} != {row.target_definition}"
        )
    if branch.feature_set != EXPECTED_STRESS_FEATURE_SET:
        raise RegionalAnnualForecastIntervalInputError(
            f"{branch.model_name} residual feature_set mismatch: "
            f"{branch.feature_set} != {EXPECTED_STRESS_FEATURE_SET}"
        )
    if branch.evaluation_mode != EXPECTED_STRESS_EVALUATION_MODE:
        raise RegionalAnnualForecastIntervalInputError(
            f"{branch.model_name} residual evaluation_mode mismatch: "
            f"{branch.evaluation_mode} != {EXPECTED_STRESS_EVALUATION_MODE}"
        )


def _read_forecast_rows(path: Path) -> list[_ForecastRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RegionalAnnualForecastIntervalInputError(
                "regional annual forecast predictions CSV has no header"
            )
        missing_columns = REQUIRED_FORECAST_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise RegionalAnnualForecastIntervalInputError(
                "regional annual forecast predictions missing required column(s): "
                f"{', '.join(sorted(missing_columns))}"
            )
        rows = [
            _ForecastRow(
                source_forecast_run_id=str(row["run_id"]),
                model_name=str(row["model_name"]),
                model_family=str(row["model_family"]),
                target_definition=str(row["target_definition"]),
                feature_set=str(row["feature_set"]),
                feature_profile=str(row["feature_profile"]),
                evaluation_mode=str(row["evaluation_mode"]),
                regional_incidence_sha256=str(row["regional_incidence_sha256"]),
                regional_population_sha256=str(row["regional_population_sha256"]),
                state_fips=str(row["state_fips"]).zfill(2),
                state_abbr=str(row["state_abbr"]),
                state_name=str(row["state_name"]),
                county_fips=str(row["county_fips"]).zfill(5),
                county_name=str(row["county_name"]),
                forecast_year=_parse_int(row["forecast_year"], "forecast_year"),
                forecast_origin_year=_parse_int(
                    row["forecast_origin_year"],
                    "forecast_origin_year",
                ),
                as_of_date=str(row["as_of_date"]),
                data_cutoff_date=str(row["data_cutoff_date"]),
                source_vintage=str(row["source_vintage"]),
                update_mode=str(row["update_mode"]),
                forecast_population=_parse_int(
                    row["forecast_population"],
                    "forecast_population",
                ),
                predicted_cases=_parse_float(
                    row["predicted_cases"],
                    "predicted_cases",
                ),
                predicted_incidence_per_100k=_parse_float(
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
            for row in reader
        ]
    _reject_duplicate_forecast_rows(rows)
    return rows


def _read_stress_residuals(path: Path) -> list[_StressResidual]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RegionalAnnualForecastIntervalInputError(
                "regional incidence stress predictions CSV has no header"
            )
        missing_columns = REQUIRED_STRESS_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise RegionalAnnualForecastIntervalInputError(
                "regional incidence stress predictions missing required column(s): "
                f"{', '.join(sorted(missing_columns))}"
            )
        return [
            _StressResidual(
                residual_source_run_id=str(row["run_id"]),
                model_name=str(row["model_name"]),
                model_family=str(row["model_family"]),
                target_definition=str(row["target_definition"]),
                feature_set=str(row["feature_set"]),
                evaluation_mode=str(row["evaluation_mode"]),
                source_file_sha256=str(row["source_file_sha256"]),
                test_year=_parse_int(row["test_year"], "test_year"),
                residual_incidence_per_100k=_parse_float(
                    row["residual_incidence_per_100k"],
                    "residual_incidence_per_100k",
                ),
                comparison_assumption_flags=str(
                    row.get("comparison_assumption_flags", "")
                ),
            )
            for row in reader
        ]


def _reject_duplicate_forecast_rows(rows: list[_ForecastRow]) -> None:
    seen = set()
    for row in rows:
        key = (
            row.source_forecast_run_id,
            row.model_name,
            row.county_fips,
            row.forecast_year,
            row.forecast_origin_year,
        )
        if key in seen:
            raise RegionalAnnualForecastIntervalInputError(
                "duplicate regional annual forecast prediction row for "
                f"{row.source_forecast_run_id}, {row.model_name}, "
                f"{row.county_fips}, {row.forecast_year}"
            )
        seen.add(key)


def _write_records(
    output_path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {column: _format_value(record.get(column)) for column in columns}
            for record in records
        )


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    return lower + (upper - lower) * (position - lower_index)


def _incidence_to_cases(incidence: float, population: int) -> float:
    return _round(incidence * population / 100000)


def _cases_to_incidence(cases: float, population: int) -> float:
    if population <= 0:
        return 0.0
    return _round(cases / population * 100000)


def _bounded_incidence(value: float) -> float:
    return _round(max(0.0, value))


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


def _single_value(values: set[object], field_name: str):
    if len(values) != 1:
        raise RegionalAnnualForecastIntervalInputError(
            f"regional annual forecast intervals require one {field_name}"
        )
    return next(iter(values))


def _parse_int(value: str, field_name: str) -> int:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be an integer"
        )
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be an integer"
        ) from exc
    if not math.isfinite(number) or not number.is_integer():
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be an integer"
        )
    return int(number)


def _parse_float(value: str, field_name: str) -> float:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be numeric"
        )
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be numeric"
        ) from exc
    if not math.isfinite(number):
        raise RegionalAnnualForecastIntervalInputError(
            f"{field_name} must be finite"
        )
    return float(number)


def _round(value: float) -> float:
    return round(float(value), 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
