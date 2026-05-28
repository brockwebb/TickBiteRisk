from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


REQUIRED_REGIONAL_PANEL_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "feature_quality_flags",
}


@dataclass(frozen=True)
class RegionalSignalRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    diagnostic_state_total_cases: int
    diagnostic_midatlantic_total_cases: int
    diagnostic_county_share_of_state_cases: float | None
    diagnostic_county_share_of_midatlantic_cases: float | None
    feature_prior_year_total_cases: int | None
    feature_prior_year_county_share_of_state_cases: float | None
    feature_prior_year_county_share_of_midatlantic_cases: float | None
    feature_prior_year_state_total_cases: int | None
    feature_prior_year_midatlantic_total_cases: int | None
    feature_trailing_5yr_midatlantic_total_min: int | None
    feature_trailing_5yr_midatlantic_total_mean: float | None
    feature_trailing_5yr_midatlantic_total_max: int | None
    diagnostic_midatlantic_total_within_trailing_5yr_band: bool | None
    source_panel_sha256: str
    feature_quality_flags: str


@dataclass(frozen=True)
class _PanelRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    feature_quality_flags: str


def build_midatlantic_regional_signals(
    regional_lyme_path: Path,
    *,
    source_panel_sha256: str,
) -> list[RegionalSignalRow]:
    panel_rows = _read_panel_rows(regional_lyme_path)
    rows_by_county_year = {
        (row.county_fips, row.year): row for row in panel_rows
    }
    state_total_by_year = _state_totals(panel_rows)
    regional_total_by_year = _regional_totals(panel_rows)

    signal_rows = []
    for row in panel_rows:
        prior = rows_by_county_year.get((row.county_fips, row.year - 1))
        prior_state_total = state_total_by_year.get((row.state_fips, row.year - 1))
        prior_regional_total = regional_total_by_year.get(row.year - 1)
        trailing_totals = [
            regional_total_by_year[year]
            for year in range(row.year - 5, row.year)
            if year in regional_total_by_year
        ]
        diagnostic_regional_total = regional_total_by_year[row.year]
        signal_rows.append(
            RegionalSignalRow(
                state_fips=row.state_fips,
                state_abbr=row.state_abbr,
                state_name=row.state_name,
                county_fips=row.county_fips,
                county_name=row.county_name,
                year=row.year,
                total_cases=row.total_cases,
                diagnostic_state_total_cases=state_total_by_year[
                    (row.state_fips, row.year)
                ],
                diagnostic_midatlantic_total_cases=diagnostic_regional_total,
                diagnostic_county_share_of_state_cases=_share(
                    row.total_cases,
                    state_total_by_year[(row.state_fips, row.year)],
                ),
                diagnostic_county_share_of_midatlantic_cases=_share(
                    row.total_cases,
                    diagnostic_regional_total,
                ),
                feature_prior_year_total_cases=(
                    prior.total_cases if prior is not None else None
                ),
                feature_prior_year_county_share_of_state_cases=(
                    _share(prior.total_cases, prior_state_total)
                    if prior is not None
                    else None
                ),
                feature_prior_year_county_share_of_midatlantic_cases=(
                    _share(prior.total_cases, prior_regional_total)
                    if prior is not None
                    else None
                ),
                feature_prior_year_state_total_cases=prior_state_total,
                feature_prior_year_midatlantic_total_cases=prior_regional_total,
                feature_trailing_5yr_midatlantic_total_min=(
                    min(trailing_totals) if trailing_totals else None
                ),
                feature_trailing_5yr_midatlantic_total_mean=(
                    _round(mean(trailing_totals)) if trailing_totals else None
                ),
                feature_trailing_5yr_midatlantic_total_max=(
                    max(trailing_totals) if trailing_totals else None
                ),
                diagnostic_midatlantic_total_within_trailing_5yr_band=(
                    min(trailing_totals)
                    <= diagnostic_regional_total
                    <= max(trailing_totals)
                    if trailing_totals
                    else None
                ),
                source_panel_sha256=source_panel_sha256,
                feature_quality_flags=",".join(
                    _signal_quality_flags(row, prior, trailing_totals)
                ),
            )
        )
    return sorted(signal_rows, key=lambda item: (item.county_fips, item.year))


def _read_panel_rows(path: Path) -> list[_PanelRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_PANEL_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing regional Lyme panel columns: {sorted(missing)}")
        return sorted(
            [
                _PanelRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=row["state_abbr"],
                    state_name=row["state_name"],
                    county_fips=row["county_fips"].zfill(5),
                    county_name=row["county_name"],
                    year=int(row["year"]),
                    total_cases=int(row["total_cases"]),
                    feature_quality_flags=row.get("feature_quality_flags", ""),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _state_totals(rows: list[_PanelRow]) -> dict[tuple[str, int], int]:
    totals: dict[tuple[str, int], int] = {}
    for row in rows:
        key = (row.state_fips, row.year)
        totals[key] = totals.get(key, 0) + row.total_cases
    return totals


def _regional_totals(rows: list[_PanelRow]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in rows:
        totals[row.year] = totals.get(row.year, 0) + row.total_cases
    return totals


def _signal_quality_flags(
    row: _PanelRow,
    prior: _PanelRow | None,
    trailing_totals: list[int],
) -> list[str]:
    flags = [
        "regional_signal_candidate",
        "reported_cases_not_stable_true_incidence",
        "case_count_not_population_rate",
        "same_year_diagnostics_not_forecast_features",
    ]
    if prior is None:
        flags.append("insufficient_prior_year_history")
    if not trailing_totals:
        flags.append("insufficient_trailing_regional_history")
    elif len(trailing_totals) < 5:
        flags.append("partial_trailing_regional_history")
    flags.extend(flag for flag in row.feature_quality_flags.split(",") if flag)
    return list(dict.fromkeys(flags))


def _share(numerator: int, denominator: int | None) -> float | None:
    if denominator in (None, 0):
        return None
    return _round(numerator / denominator)


def _round(value: float) -> float:
    return round(value, 6)
