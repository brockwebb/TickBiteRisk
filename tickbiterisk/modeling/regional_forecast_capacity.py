from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


CAPACITY_ASSUMPTION_FLAGS = (
    "forecast_capacity_control_limit,"
    "historical_reported_incidence_range,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_forecast,"
    "not_public_maryland_default,"
    "forecast_without_observed_target"
)
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
REQUIRED_FORECAST_COLUMNS = {
    "run_id",
    "model_name",
    "model_family",
    "feature_profile",
    "evaluation_mode",
    "source_vintage",
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "forecast_year",
    "forecast_origin_year",
    "forecast_population",
    "predicted_cases",
    "predicted_incidence_per_100k",
    "forecast_assumption_flags",
}


class RegionalForecastCapacityInputError(ValueError):
    """Raised when regional forecast capacity inputs are invalid."""


@dataclass(frozen=True)
class RegionalForecastCapacityRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    forecast_predictions_path: str
    forecast_predictions_sha256: str
    forecast_year: int
    forecast_origin_year: int
    history_start_year: int
    history_end_year: int
    model_names: str
    n_forecast_rows: int
    n_capacity_rows: int
    capacity_assumption_flags: str


@dataclass(frozen=True)
class RegionalForecastCapacitySummary:
    run_id: str
    source_forecast_run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_vintage: str
    geography_level: str
    region_id: str
    region_name: str
    forecast_year: int
    forecast_origin_year: int
    history_start_year: int
    history_end_year: int
    history_year_count: int
    n_counties: int
    forecast_total_cases: float
    forecast_population: int
    forecast_incidence_per_100k: float
    history_min_cases: float
    history_p10_cases: float
    history_mean_cases: float
    history_p90_cases: float
    history_max_cases: float
    history_min_incidence_per_100k: float
    history_p10_incidence_per_100k: float
    history_mean_incidence_per_100k: float
    history_p90_incidence_per_100k: float
    history_max_incidence_per_100k: float
    forecast_case_percentile_of_history: float
    forecast_incidence_percentile_of_history: float
    above_history_max_cases: bool
    below_history_min_cases: bool
    capacity_assumption_flags: str


@dataclass(frozen=True)
class RegionalForecastCapacityResult:
    run_id: str
    run: RegionalForecastCapacityRun
    capacity_summary: list[RegionalForecastCapacitySummary]


@dataclass(frozen=True)
class _IncidenceRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    year: int
    total_cases: int
    population: int
    incidence_per_100k: float
    feature_quality_flags: str


@dataclass(frozen=True)
class _ForecastRow:
    source_forecast_run_id: str
    model_name: str
    model_family: str
    feature_profile: str
    evaluation_mode: str
    source_vintage: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    forecast_year: int
    forecast_origin_year: int
    forecast_population: int
    predicted_cases: float
    predicted_incidence_per_100k: float
    forecast_assumption_flags: str


@dataclass(frozen=True)
class _AggregateYear:
    year: int
    total_cases: float
    population: int
    incidence_per_100k: float


def build_regional_forecast_capacity(
    *,
    regional_incidence_path: Path,
    forecast_predictions_path: Path,
) -> RegionalForecastCapacityResult:
    incidence_rows = _read_incidence_rows(regional_incidence_path)
    forecast_rows = _read_forecast_rows(forecast_predictions_path)
    if not forecast_rows:
        raise RegionalForecastCapacityInputError(
            "regional forecast predictions have no rows"
        )
    forecast_years = {row.forecast_year for row in forecast_rows}
    forecast_origin_years = {row.forecast_origin_year for row in forecast_rows}
    if len(forecast_years) != 1 or len(forecast_origin_years) != 1:
        raise RegionalForecastCapacityInputError(
            "regional forecast capacity requires one forecast year and origin year"
        )
    forecast_year = next(iter(forecast_years))
    forecast_origin_year = next(iter(forecast_origin_years))
    historical_rows = [
        row for row in incidence_rows if row.year <= forecast_origin_year
    ]
    if not historical_rows:
        raise RegionalForecastCapacityInputError(
            "regional incidence panel has no rows at or before forecast origin"
        )

    incidence_sha = _sha256_file(regional_incidence_path)
    forecast_sha = _sha256_file(forecast_predictions_path)
    run_id = (
        f"regional_forecast_capacity_forecast{forecast_year}_"
        f"origin{forecast_origin_year}"
    )
    summary_rows = _capacity_summary_rows(
        run_id=run_id,
        incidence_rows=historical_rows,
        forecast_rows=forecast_rows,
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
    )
    if not summary_rows:
        raise RegionalForecastCapacityInputError(
            "no regional forecast capacity rows could be summarized"
        )
    run = RegionalForecastCapacityRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=incidence_sha,
        forecast_predictions_path=str(forecast_predictions_path),
        forecast_predictions_sha256=forecast_sha,
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        history_start_year=min(row.history_start_year for row in summary_rows),
        history_end_year=max(row.history_end_year for row in summary_rows),
        model_names=",".join(sorted({row.model_name for row in forecast_rows})),
        n_forecast_rows=len(forecast_rows),
        n_capacity_rows=len(summary_rows),
        capacity_assumption_flags=CAPACITY_ASSUMPTION_FLAGS,
    )
    return RegionalForecastCapacityResult(
        run_id=run_id,
        run=run,
        capacity_summary=summary_rows,
    )


def _capacity_summary_rows(
    *,
    run_id: str,
    incidence_rows: list[_IncidenceRow],
    forecast_rows: list[_ForecastRow],
    forecast_year: int,
    forecast_origin_year: int,
) -> list[RegionalForecastCapacitySummary]:
    grouped_forecast: dict[tuple[str, str], list[_ForecastRow]] = {}
    for row in forecast_rows:
        for geography_level, region_id in _forecast_regions(row):
            grouped_forecast.setdefault((geography_level, region_id), [])
    for key in list(grouped_forecast):
        geography_level, region_id = key
        grouped_forecast[key] = [
            row
            for row in forecast_rows
            if any(
                geography_level == level and region_id == item_region
                for level, item_region in _forecast_regions(row)
            )
        ]

    rows = []
    for (geography_level, region_id), geography_forecasts in sorted(
        grouped_forecast.items()
    ):
        model_groups: dict[str, list[_ForecastRow]] = {}
        for forecast in geography_forecasts:
            model_groups.setdefault(forecast.model_name, []).append(forecast)
        for model_name, model_rows in sorted(model_groups.items()):
            county_fips = {row.county_fips for row in model_rows}
            history = _complete_history_aggregates(
                incidence_rows=incidence_rows,
                county_fips=county_fips,
                forecast_origin_year=forecast_origin_year,
            )
            if not history:
                continue
            rows.append(
                _summary_row(
                    run_id=run_id,
                    geography_level=geography_level,
                    region_id=region_id,
                    region_name=_region_name(geography_level, region_id, model_rows),
                    model_rows=model_rows,
                    history=history,
                    forecast_year=forecast_year,
                    forecast_origin_year=forecast_origin_year,
                )
            )
    return sorted(
        rows,
        key=lambda row: (row.model_name, row.geography_level, row.region_id),
    )


def _forecast_regions(row: _ForecastRow) -> tuple[tuple[str, str], ...]:
    return (
        ("regional", "midatlantic"),
        ("state", f"state_{row.state_fips}"),
    )


def _region_name(
    geography_level: str,
    region_id: str,
    rows: list[_ForecastRow],
) -> str:
    if geography_level == "regional":
        return "Mid-Atlantic"
    state_fips = region_id.removeprefix("state_")
    for row in rows:
        if row.state_fips == state_fips:
            return row.state_name
    return f"State {state_fips}"


def _complete_history_aggregates(
    *,
    incidence_rows: list[_IncidenceRow],
    county_fips: set[str],
    forecast_origin_year: int,
) -> list[_AggregateYear]:
    rows_by_year: dict[int, list[_IncidenceRow]] = {}
    for row in incidence_rows:
        if row.county_fips in county_fips and row.year <= forecast_origin_year:
            rows_by_year.setdefault(row.year, []).append(row)
    aggregates = []
    for year, rows in rows_by_year.items():
        if {row.county_fips for row in rows} != county_fips:
            continue
        total_cases = sum(row.total_cases for row in rows)
        population = sum(row.population for row in rows)
        if population <= 0:
            continue
        aggregates.append(
            _AggregateYear(
                year=year,
                total_cases=float(total_cases),
                population=population,
                incidence_per_100k=_round(total_cases * 100000 / population),
            )
        )
    return sorted(aggregates, key=lambda row: row.year)


def _summary_row(
    *,
    run_id: str,
    geography_level: str,
    region_id: str,
    region_name: str,
    model_rows: list[_ForecastRow],
    history: list[_AggregateYear],
    forecast_year: int,
    forecast_origin_year: int,
) -> RegionalForecastCapacitySummary:
    first = model_rows[0]
    forecast_total_cases = _round(sum(row.predicted_cases for row in model_rows))
    forecast_population = sum(row.forecast_population for row in model_rows)
    forecast_incidence = (
        _round(forecast_total_cases * 100000 / forecast_population)
        if forecast_population > 0
        else 0.0
    )
    history_cases = [row.total_cases for row in history]
    history_incidence = [row.incidence_per_100k for row in history]
    flags = _join_flags(
        CAPACITY_ASSUMPTION_FLAGS,
        *(row.forecast_assumption_flags for row in model_rows),
    )
    return RegionalForecastCapacitySummary(
        run_id=run_id,
        source_forecast_run_id=first.source_forecast_run_id,
        model_name=first.model_name,
        model_family=first.model_family,
        feature_profile=first.feature_profile,
        evaluation_mode=first.evaluation_mode,
        source_vintage=first.source_vintage,
        geography_level=geography_level,
        region_id=region_id,
        region_name=region_name,
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        history_start_year=min(row.year for row in history),
        history_end_year=max(row.year for row in history),
        history_year_count=len(history),
        n_counties=len(model_rows),
        forecast_total_cases=forecast_total_cases,
        forecast_population=forecast_population,
        forecast_incidence_per_100k=forecast_incidence,
        history_min_cases=_round(min(history_cases)),
        history_p10_cases=_round(_quantile(history_cases, 0.1)),
        history_mean_cases=_round(mean(history_cases)),
        history_p90_cases=_round(_quantile(history_cases, 0.9)),
        history_max_cases=_round(max(history_cases)),
        history_min_incidence_per_100k=_round(min(history_incidence)),
        history_p10_incidence_per_100k=_round(_quantile(history_incidence, 0.1)),
        history_mean_incidence_per_100k=_round(mean(history_incidence)),
        history_p90_incidence_per_100k=_round(_quantile(history_incidence, 0.9)),
        history_max_incidence_per_100k=_round(max(history_incidence)),
        forecast_case_percentile_of_history=_percentile_rank(
            history_cases, forecast_total_cases
        ),
        forecast_incidence_percentile_of_history=_percentile_rank(
            history_incidence, forecast_incidence
        ),
        above_history_max_cases=forecast_total_cases > max(history_cases),
        below_history_min_cases=forecast_total_cases < min(history_cases),
        capacity_assumption_flags=flags,
    )


def _read_incidence_rows(path: Path) -> list[_IncidenceRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_INCIDENCE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalForecastCapacityInputError(
                f"missing regional incidence columns: {sorted(missing)}"
            )
        rows = []
        for row in reader:
            incidence = _parse_optional_float(row.get("incidence_per_100k", ""))
            population = _parse_optional_int(row.get("population", ""))
            if incidence is None or population is None:
                continue
            rows.append(
                _IncidenceRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    year=_parse_int(row["year"], "year"),
                    total_cases=_parse_int(row["total_cases"], "total_cases"),
                    population=population,
                    incidence_per_100k=incidence,
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
            )
    return sorted(rows, key=lambda row: (row.year, row.county_fips))


def _read_forecast_rows(path: Path) -> list[_ForecastRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_FORECAST_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalForecastCapacityInputError(
                f"missing regional forecast columns: {sorted(missing)}"
            )
        return [
            _ForecastRow(
                source_forecast_run_id=str(row["run_id"]),
                model_name=str(row["model_name"]),
                model_family=str(row["model_family"]),
                feature_profile=str(row["feature_profile"]),
                evaluation_mode=str(row["evaluation_mode"]),
                source_vintage=str(row["source_vintage"]),
                state_fips=row["state_fips"].zfill(2),
                state_abbr=str(row["state_abbr"]),
                state_name=str(row["state_name"]),
                county_fips=row["county_fips"].zfill(5),
                forecast_year=_parse_int(row["forecast_year"], "forecast_year"),
                forecast_origin_year=_parse_int(
                    row["forecast_origin_year"],
                    "forecast_origin_year",
                ),
                forecast_population=_parse_int(
                    row["forecast_population"],
                    "forecast_population",
                ),
                predicted_cases=_parse_float(row["predicted_cases"], "predicted_cases"),
                predicted_incidence_per_100k=_parse_float(
                    row["predicted_incidence_per_100k"],
                    "predicted_incidence_per_100k",
                ),
                forecast_assumption_flags=str(row.get("forecast_assumption_flags", "")),
            )
            for row in reader
        ]


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


def _percentile_rank(values: list[float], observed: float) -> float:
    if not values:
        return 0.0
    return _round(sum(value <= observed for value in values) / len(values))


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


def _parse_int(value: str, field_name: str) -> int:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalForecastCapacityInputError(f"{field_name} must be an integer")
    number = float(cleaned)
    if not math.isfinite(number) or not number.is_integer():
        raise RegionalForecastCapacityInputError(f"{field_name} must be an integer")
    return int(number)


def _parse_optional_int(value: str | None) -> int | None:
    if str(value or "").strip() == "":
        return None
    return _parse_int(str(value), "integer value")


def _parse_float(value: str, field_name: str) -> float:
    cleaned = str(value or "").replace(",", "").strip()
    if cleaned == "":
        raise RegionalForecastCapacityInputError(f"{field_name} must be numeric")
    number = float(cleaned)
    if not math.isfinite(number):
        raise RegionalForecastCapacityInputError(f"{field_name} must be finite")
    return float(number)


def _parse_optional_float(value: str | None) -> float | None:
    if str(value or "").strip() == "":
        return None
    return _parse_float(str(value), "numeric value")


def _round(value: float) -> float:
    return round(float(value), 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
