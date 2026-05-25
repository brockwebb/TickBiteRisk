from __future__ import annotations

import calendar
import csv
import math
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median


SEASONALITY_FEATURE_FLAGS = (
    "national_curve_not_county_specific,"
    "shares_normalized_by_annual_total,"
    "empirical_prediction_band"
)


class SeasonalityInputError(ValueError):
    """Raised when a seasonality source file has invalid values."""


@dataclass(frozen=True)
class SeasonalityObservation:
    source_id: str
    disease: str
    grain: str
    year: int
    period: int
    period_label: str
    cases: int
    annual_cases: int
    seasonal_share: float


@dataclass(frozen=True)
class SeasonalityBaseline:
    source_id: str
    disease: str
    grain: str
    period: int
    period_label: str
    years_observed: int
    mean_cases: float
    median_cases: float
    min_cases: int
    max_cases: int
    mean_share: float
    median_share: float
    lower_80_share: float
    upper_80_share: float
    lower_95_share: float
    upper_95_share: float
    peak_rank: int
    cumulative_mean_share: float
    feature_quality_flags: str


def parse_cdc_lyme_monthly_onset(
    path: Path,
    *,
    source_id: str,
) -> list[SeasonalityObservation]:
    raw_rows = _read_csv(path, required_columns=["Year", "Onset Month", "Cases"])
    rows = [
        {
            "source_id": source_id,
            "disease": "lyme",
            "grain": "month",
            "year": _parse_nonnegative_int(row["Year"], "Year"),
            "period": _month_number(row["Onset Month"]),
            "period_label": row["Onset Month"].strip(),
            "cases": _parse_nonnegative_int(row["Cases"], "Cases"),
        }
        for row in raw_rows
    ]
    _validate_unique_periods(rows)
    return _attach_annual_shares(rows)


def parse_cdc_lyme_weekly_onset(
    path: Path,
    *,
    source_id: str,
) -> list[SeasonalityObservation]:
    raw_rows = _read_csv(path, required_columns=["Year", "MMWR Week", "Cases"])
    rows = [
        {
            "source_id": source_id,
            "disease": "lyme",
            "grain": "mmwr_week",
            "year": _parse_nonnegative_int(row["Year"], "Year"),
            "period": _parse_week(row["MMWR Week"]),
            "period_label": f"MMWR Week {_parse_week(row['MMWR Week'])}",
            "cases": _parse_nonnegative_int(row["Cases"], "Cases"),
        }
        for row in raw_rows
    ]
    _validate_unique_periods(rows)
    return _attach_annual_shares(rows)


def build_seasonality_baseline(
    observations: list[SeasonalityObservation],
) -> list[SeasonalityBaseline]:
    grouped: dict[tuple[str, str, str, int], list[SeasonalityObservation]] = {}
    for row in observations:
        grouped.setdefault(
            (row.source_id, row.disease, row.grain, row.period), []
        ).append(row)

    rows = []
    for (source_id, disease, grain, period), period_rows in grouped.items():
        cases = [row.cases for row in period_rows]
        shares = [row.seasonal_share for row in period_rows]
        rows.append(
            SeasonalityBaseline(
                source_id=source_id,
                disease=disease,
                grain=grain,
                period=period,
                period_label=period_rows[0].period_label,
                years_observed=len({row.year for row in period_rows}),
                mean_cases=_round(mean(cases)),
                median_cases=_round(median(cases)),
                min_cases=min(cases),
                max_cases=max(cases),
                mean_share=_round(mean(shares)),
                median_share=_round(median(shares)),
                lower_80_share=_round(_nearest_rank(shares, 0.10)),
                upper_80_share=_round(_nearest_rank(shares, 0.90)),
                lower_95_share=_round(_nearest_rank(shares, 0.025)),
                upper_95_share=_round(_nearest_rank(shares, 0.975)),
                peak_rank=0,
                cumulative_mean_share=0.0,
                feature_quality_flags=SEASONALITY_FEATURE_FLAGS,
            )
        )
    return _attach_ranks_and_cumulative(rows)


def _attach_annual_shares(
    rows: list[dict[str, object]]
) -> list[SeasonalityObservation]:
    annual_totals: dict[tuple[str, str, str, int], int] = {}
    for row in rows:
        key = (
            str(row["source_id"]),
            str(row["disease"]),
            str(row["grain"]),
            int(row["year"]),
        )
        annual_totals[key] = (
            annual_totals.get(key, 0)
            + int(row["cases"])
        )
    observations = []
    for row in rows:
        key = (
            str(row["source_id"]),
            str(row["disease"]),
            str(row["grain"]),
            int(row["year"]),
        )
        annual_cases = annual_totals[key]
        seasonal_share = 0.0 if annual_cases == 0 else int(row["cases"]) / annual_cases
        observations.append(
            SeasonalityObservation(
                source_id=str(row["source_id"]),
                disease=str(row["disease"]),
                grain=str(row["grain"]),
                year=int(row["year"]),
                period=int(row["period"]),
                period_label=str(row["period_label"]),
                cases=int(row["cases"]),
                annual_cases=annual_cases,
                seasonal_share=_round(seasonal_share),
            )
        )
    return sorted(observations, key=lambda row: (row.grain, row.year, row.period))


def _attach_ranks_and_cumulative(
    rows: list[SeasonalityBaseline],
) -> list[SeasonalityBaseline]:
    output = []
    groups = sorted({(row.source_id, row.disease, row.grain) for row in rows})
    for source_id, disease, grain in groups:
        grain_rows = sorted(
            [
                row
                for row in rows
                if (
                    row.source_id == source_id
                    and row.disease == disease
                    and row.grain == grain
                )
            ],
            key=lambda row: row.period,
        )
        ranked = {
            id(row): rank
            for rank, row in enumerate(
                sorted(grain_rows, key=lambda row: (-row.mean_share, row.period)),
                start=1,
            )
        }
        cumulative = 0.0
        for row in grain_rows:
            cumulative += row.mean_share
            output.append(
                replace(
                    row,
                    peak_rank=ranked[id(row)],
                    cumulative_mean_share=_round(min(cumulative, 1.0)),
                )
            )
    return output


def _read_csv(path: Path, *, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = [
            column for column in required_columns if column not in fieldnames
        ]
        if missing_columns:
            raise SeasonalityInputError(
                "missing required seasonality column(s): "
                f"{', '.join(missing_columns)}"
            )
        return list(reader)


def _month_number(value: str) -> int:
    month_lookup = {
        name: number for number, name in enumerate(calendar.month_name) if name
    }
    month = month_lookup.get(value.strip())
    if month is None:
        raise SeasonalityInputError(f"Unknown month name: {value!r}")
    return month


def _nearest_rank(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile for empty values")
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def _parse_week(value: str) -> int:
    week = _parse_nonnegative_int(value, "MMWR Week")
    if week < 1 or week > 53:
        raise SeasonalityInputError(f"MMWR Week must be between 1 and 53: {value!r}")
    return week


def _parse_nonnegative_int(value: str, field_name: str) -> int:
    try:
        parsed = int(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise SeasonalityInputError(
            f"{field_name} must be a nonnegative integer: {value!r}"
        ) from exc
    if parsed < 0:
        raise SeasonalityInputError(
            f"{field_name} must be a nonnegative integer: {value!r}"
        )
    return parsed


def _validate_unique_periods(rows: list[dict[str, object]]) -> None:
    seen: set[tuple[str, str, str, int, int]] = set()
    for row in rows:
        key = (
            str(row["source_id"]),
            str(row["disease"]),
            str(row["grain"]),
            int(row["year"]),
            int(row["period"]),
        )
        if key in seen:
            raise SeasonalityInputError(
                "duplicate seasonality period for "
                f"source_id={key[0]}, disease={key[1]}, grain={key[2]}, "
                f"year={key[3]}, period={key[4]}"
            )
        seen.add(key)


def _round(value: float) -> float:
    return round(value, 6)
