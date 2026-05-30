from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path


COMPARISON_SCOPE = "county_prior_history"
TYPICALITY_METHOD = "empirical_percentile_of_prior_county_history"
BASELINE_POLICY = "county history years <= forecast_origin_year"
PROTOCOL_POLICY = "raw_with_surveillance_protocol_caveat"
ASSUMPTION_FLAGS = (
    "forecast_typicality_county_prior_history,"
    "reported_cases_not_stable_true_incidence,"
    "raw_protocol_era_caveat,"
    "target_year_observed_rows_excluded,"
    "not_public_default"
)
REQUIRED_INCIDENCE_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "incidence_per_100k",
}
REQUIRED_INTERVAL_COLUMNS = {
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
    "lower_80_incidence_per_100k",
    "upper_80_incidence_per_100k",
    "lower_95_incidence_per_100k",
    "upper_95_incidence_per_100k",
}


class RegionalForecastTypicalityInputError(ValueError):
    """Raised when forecast typicality inputs cannot produce rows."""


@dataclass(frozen=True)
class RegionalForecastTypicalityRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    regional_annual_forecast_intervals_path: str
    regional_annual_forecast_intervals_sha256: str
    model_name: str
    comparison_scope: str
    typicality_method: str
    baseline_policy: str
    min_history_years: int
    n_forecast_rows: int
    n_typicality_rows: int
    assumption_flags: str


@dataclass(frozen=True)
class RegionalForecastTypicalityRow:
    run_id: str
    source_interval_run_id: str
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
    forecast_population: int | None
    predicted_cases: float
    predicted_incidence_per_100k: float
    lower_80_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    comparison_scope: str
    comparison_year_start: int
    comparison_year_end: int
    baseline_year_count: int
    typical_median_incidence_per_100k: float
    typical_p25_incidence_per_100k: float
    typical_p75_incidence_per_100k: float
    forecast_percentile_of_county_history: float
    lower_80_percentile_of_county_history: float
    upper_80_percentile_of_county_history: float
    lower_95_percentile_of_county_history: float
    upper_95_percentile_of_county_history: float
    severity_label: str
    interval_severity_label: str
    typicality_evidence_level: str
    margin_to_typical_band_per_100k: float
    typicality_method: str
    baseline_policy: str
    protocol_policy: str
    assumption_flags: str


@dataclass(frozen=True)
class RegionalForecastTypicalityResult:
    run_id: str
    run: RegionalForecastTypicalityRun
    rows: list[RegionalForecastTypicalityRow]


@dataclass(frozen=True)
class _ObservedIncidence:
    year: int
    incidence_per_100k: float


def build_regional_forecast_typicality(
    *,
    regional_incidence_path: Path,
    regional_annual_forecast_intervals_path: Path,
    model_name: str = "empirical_bayes_spatial_regime_incidence",
    min_history_years: int = 3,
) -> RegionalForecastTypicalityResult:
    if min_history_years < 1:
        raise RegionalForecastTypicalityInputError(
            "min_history_years must be at least 1"
        )

    incidence_rows = _read_csv_rows(
        regional_incidence_path,
        required_columns=REQUIRED_INCIDENCE_COLUMNS,
        label="regional incidence",
    )
    interval_rows = [
        row
        for row in _read_csv_rows(
            regional_annual_forecast_intervals_path,
            required_columns=REQUIRED_INTERVAL_COLUMNS,
            label="regional annual forecast intervals",
        )
        if row.get("model_name") == model_name
    ]
    if not interval_rows:
        raise RegionalForecastTypicalityInputError(
            f"no interval rows matched model_name={model_name}"
        )

    history_by_county = _observed_history_by_county(incidence_rows)
    incidence_sha = _sha256_file(regional_incidence_path)
    intervals_sha = _sha256_file(regional_annual_forecast_intervals_path)
    run_id = (
        f"regional_forecast_typicality_{model_name}_"
        f"{incidence_sha[:12]}_{intervals_sha[:12]}"
    )
    rows = [
        row
        for row in (
            _typicality_row(
                interval_row,
                run_id=run_id,
                county_history=history_by_county.get(
                    str(interval_row.get("county_fips", "")).zfill(5),
                    [],
                ),
                min_history_years=min_history_years,
            )
            for interval_row in interval_rows
        )
        if row is not None
    ]
    if not rows:
        raise RegionalForecastTypicalityInputError(
            "no forecast rows had enough prior county history"
        )

    run = RegionalForecastTypicalityRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=incidence_sha,
        regional_annual_forecast_intervals_path=str(
            regional_annual_forecast_intervals_path
        ),
        regional_annual_forecast_intervals_sha256=intervals_sha,
        model_name=model_name,
        comparison_scope=COMPARISON_SCOPE,
        typicality_method=TYPICALITY_METHOD,
        baseline_policy=BASELINE_POLICY,
        min_history_years=min_history_years,
        n_forecast_rows=len(interval_rows),
        n_typicality_rows=len(rows),
        assumption_flags=ASSUMPTION_FLAGS,
    )
    return RegionalForecastTypicalityResult(run_id=run_id, run=run, rows=rows)


def _typicality_row(
    row: dict[str, str],
    *,
    run_id: str,
    county_history: list[_ObservedIncidence],
    min_history_years: int,
) -> RegionalForecastTypicalityRow | None:
    forecast_origin_year = _required_int(
        row.get("forecast_origin_year"),
        "forecast_origin_year",
    )
    forecast_year = _required_int(row.get("forecast_year"), "forecast_year")
    if forecast_year <= forecast_origin_year:
        raise RegionalForecastTypicalityInputError(
            "forecast_year must be greater than forecast_origin_year"
        )
    prior_history = [
        record
        for record in county_history
        if record.year <= forecast_origin_year
    ]
    if len(prior_history) < min_history_years:
        return None

    values = sorted(record.incidence_per_100k for record in prior_history)
    predicted = _required_float(
        row.get("predicted_incidence_per_100k"),
        "predicted_incidence_per_100k",
    )
    lower_80 = _required_float(
        row.get("lower_80_incidence_per_100k"),
        "lower_80_incidence_per_100k",
    )
    upper_80 = _required_float(
        row.get("upper_80_incidence_per_100k"),
        "upper_80_incidence_per_100k",
    )
    lower_95 = _required_float(
        row.get("lower_95_incidence_per_100k"),
        "lower_95_incidence_per_100k",
    )
    upper_95 = _required_float(
        row.get("upper_95_incidence_per_100k"),
        "upper_95_incidence_per_100k",
    )
    p25 = _quantile(values, 0.25)
    p75 = _quantile(values, 0.75)
    predicted_percentile = _percentile_of_history(values, predicted)
    lower_80_percentile = _percentile_of_history(values, lower_80)
    upper_80_percentile = _percentile_of_history(values, upper_80)
    lower_95_percentile = _percentile_of_history(values, lower_95)
    upper_95_percentile = _percentile_of_history(values, upper_95)
    lower_label = _severity_label(lower_80_percentile)
    upper_label = _severity_label(upper_80_percentile)

    return RegionalForecastTypicalityRow(
        run_id=run_id,
        source_interval_run_id=str(row.get("run_id", "")),
        source_forecast_run_id=str(row.get("source_forecast_run_id", "")),
        model_name=str(row.get("model_name", "")),
        model_family=str(row.get("model_family", "")),
        target_definition=str(row.get("target_definition", "")),
        feature_set=str(row.get("feature_set", "")),
        feature_profile=str(row.get("feature_profile", "")),
        evaluation_mode=str(row.get("evaluation_mode", "")),
        state_fips=str(row.get("state_fips", "")).zfill(2),
        state_abbr=str(row.get("state_abbr", "")),
        state_name=str(row.get("state_name", "")),
        county_fips=str(row.get("county_fips", "")).zfill(5),
        county_name=str(row.get("county_name", "")),
        forecast_year=forecast_year,
        forecast_origin_year=forecast_origin_year,
        as_of_date=str(row.get("as_of_date", "")),
        data_cutoff_date=str(row.get("data_cutoff_date", "")),
        source_vintage=str(row.get("source_vintage", "")),
        update_mode=str(row.get("update_mode", "")),
        forecast_population=_optional_int(row.get("forecast_population")),
        predicted_cases=_round(
            _required_float(row.get("predicted_cases"), "predicted_cases")
        ),
        predicted_incidence_per_100k=_round(predicted),
        lower_80_incidence_per_100k=_round(lower_80),
        upper_80_incidence_per_100k=_round(upper_80),
        lower_95_incidence_per_100k=_round(lower_95),
        upper_95_incidence_per_100k=_round(upper_95),
        comparison_scope=COMPARISON_SCOPE,
        comparison_year_start=min(record.year for record in prior_history),
        comparison_year_end=max(record.year for record in prior_history),
        baseline_year_count=len(prior_history),
        typical_median_incidence_per_100k=_round(_quantile(values, 0.5)),
        typical_p25_incidence_per_100k=_round(p25),
        typical_p75_incidence_per_100k=_round(p75),
        forecast_percentile_of_county_history=_round(predicted_percentile),
        lower_80_percentile_of_county_history=_round(lower_80_percentile),
        upper_80_percentile_of_county_history=_round(upper_80_percentile),
        lower_95_percentile_of_county_history=_round(lower_95_percentile),
        upper_95_percentile_of_county_history=_round(upper_95_percentile),
        severity_label=_severity_label(predicted_percentile),
        interval_severity_label=_interval_severity_label(lower_label, upper_label),
        typicality_evidence_level=_evidence_level(len(prior_history)),
        margin_to_typical_band_per_100k=_round(
            _margin_to_typical_band(predicted, p25, p75)
        ),
        typicality_method=TYPICALITY_METHOD,
        baseline_policy=BASELINE_POLICY,
        protocol_policy=PROTOCOL_POLICY,
        assumption_flags=ASSUMPTION_FLAGS,
    )


def _observed_history_by_county(
    rows: list[dict[str, str]]
) -> dict[str, list[_ObservedIncidence]]:
    by_county: dict[str, list[_ObservedIncidence]] = {}
    for row in rows:
        incidence = _optional_float(row.get("incidence_per_100k"))
        if incidence is None:
            continue
        county_fips = str(row.get("county_fips", "")).zfill(5)
        by_county.setdefault(county_fips, []).append(
            _ObservedIncidence(
                year=_required_int(row.get("year"), "year"),
                incidence_per_100k=incidence,
            )
        )
    for county_rows in by_county.values():
        county_rows.sort(key=lambda record: record.year)
    return by_county


def _severity_label(percentile: float) -> str:
    if percentile < 25:
        return "below typical"
    if percentile <= 75:
        return "typical"
    if percentile < 90:
        return "above typical"
    return "much higher than typical"


def _interval_severity_label(lower_label: str, upper_label: str) -> str:
    if lower_label == upper_label:
        return lower_label
    return f"{lower_label} to {upper_label}"


def _evidence_level(history_year_count: int) -> str:
    if history_year_count < 5:
        return "very limited"
    if history_year_count < 10:
        return "limited"
    return "moderate"


def _margin_to_typical_band(value: float, p25: float, p75: float) -> float:
    if value < p25:
        return p25 - value
    if value > p75:
        return value - p75
    return 0.0


def _percentile_of_history(values: list[float], value: float) -> float:
    below_or_equal = sum(1 for candidate in values if candidate <= value)
    return 100.0 * below_or_equal / len(values)


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise RegionalForecastTypicalityInputError("cannot calculate empty quantile")
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return values[lower_index]
    weight = position - lower_index
    return values[lower_index] * (1 - weight) + values[upper_index] * weight


def _read_csv_rows(
    path: Path,
    *,
    required_columns: set[str],
    label: str,
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(required_columns - set(reader.fieldnames or []))
        if missing:
            raise RegionalForecastTypicalityInputError(
                f"{label} file is missing required columns: {', '.join(missing)}"
            )
        return list(reader)


def _required_int(value: str | None, field: str) -> int:
    if value is None or str(value).strip() == "":
        raise RegionalForecastTypicalityInputError(f"{field} is required")
    parsed = float(value)
    if not parsed.is_integer():
        raise RegionalForecastTypicalityInputError(f"{field} must be an integer")
    return int(parsed)


def _optional_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return _required_int(value, "optional integer")


def _required_float(value: str | None, field: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise RegionalForecastTypicalityInputError(f"{field} is required")
    return parsed


def _optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        raise RegionalForecastTypicalityInputError("numeric values must be finite")
    return parsed


def _round(value: float) -> float:
    return round(value, 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
