from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


HOTSPOT_QUALITY_FLAGS = (
    "regional_hotspot_diagnostic,"
    "reported_cases_not_stable_true_incidence,"
    "case_count_not_population_rate,"
    "diagnostic_same_year_not_forecast_feature,"
    "not_public_maryland_default"
)
REQUIRED_REGIONAL_HOTSPOT_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
}
TOP_QUINTILE_TIERS = {"top_decile", "top_quintile"}


@dataclass(frozen=True)
class RegionalHotspotCountyYear:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    diagnostic_state_total_cases: int
    diagnostic_midatlantic_total_cases: int
    diagnostic_state_case_share: float | None
    diagnostic_midatlantic_case_share: float | None
    diagnostic_state_rank_cases: int
    diagnostic_midatlantic_rank_cases: int
    diagnostic_state_county_count: int
    diagnostic_midatlantic_county_count: int
    diagnostic_midatlantic_hotspot_percentile: float
    diagnostic_midatlantic_hotspot_tier: str
    diagnostic_prior_year_midatlantic_rank_cases: int | None
    diagnostic_midatlantic_rank_change: int | None
    diagnostic_prior_year_midatlantic_hotspot_tier: str | None
    diagnostic_year_over_year_case_change: int | None
    diagnostic_prior_3yr_top_quintile_count: int
    source_panel_sha256: str
    feature_quality_flags: str


@dataclass(frozen=True)
class RegionalHotspotSummary:
    year: int
    diagnostic_midatlantic_total_cases: int
    diagnostic_county_count: int
    diagnostic_top_decile_count: int
    diagnostic_top_quintile_count: int
    diagnostic_persistent_top_quintile_count: int | None
    diagnostic_new_top_quintile_count: int | None
    diagnostic_exited_top_quintile_count: int | None
    source_panel_sha256: str
    feature_quality_flags: str


@dataclass(frozen=True)
class RegionalHotspotResult:
    county_year_rows: list[RegionalHotspotCountyYear]
    summary_rows: list[RegionalHotspotSummary]


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


@dataclass(frozen=True)
class _RankedRow:
    row: _PanelRow
    rank: int
    count: int
    total_cases: int


def build_midatlantic_hotspot_diagnostics(
    regional_lyme_path: Path,
    *,
    source_panel_sha256: str,
) -> RegionalHotspotResult:
    rows = _read_panel_rows(regional_lyme_path)
    state_total_by_year = _state_totals(rows)
    regional_total_by_year = _regional_totals(rows)
    regional_rank_by_key = _regional_ranks(rows)
    state_rank_by_key = _state_ranks(rows)

    county_year_rows: list[RegionalHotspotCountyYear] = []
    rows_by_county_year = {(row.county_fips, row.year): row for row in rows}
    for row in rows:
        key = (row.county_fips, row.year)
        regional_rank = regional_rank_by_key[key]
        state_rank = state_rank_by_key[key]
        prior_row = rows_by_county_year.get((row.county_fips, row.year - 1))
        prior_key = (row.county_fips, row.year - 1)
        prior_rank = regional_rank_by_key.get(prior_key)
        current_tier = _hotspot_tier(
            total_cases=row.total_cases,
            rank=regional_rank.rank,
            count=regional_rank.count,
        )
        prior_tier = (
            _hotspot_tier(
                total_cases=prior_row.total_cases,
                rank=prior_rank.rank,
                count=prior_rank.count,
            )
            if prior_row is not None and prior_rank is not None
            else None
        )
        prior_3yr_top_quintile_count = _prior_top_quintile_count(
            row=row,
            rows_by_county_year=rows_by_county_year,
            regional_rank_by_key=regional_rank_by_key,
        )
        county_year_rows.append(
            RegionalHotspotCountyYear(
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
                diagnostic_midatlantic_total_cases=regional_total_by_year[row.year],
                diagnostic_state_case_share=_share(
                    row.total_cases,
                    state_total_by_year[(row.state_fips, row.year)],
                ),
                diagnostic_midatlantic_case_share=_share(
                    row.total_cases,
                    regional_total_by_year[row.year],
                ),
                diagnostic_state_rank_cases=state_rank.rank,
                diagnostic_midatlantic_rank_cases=regional_rank.rank,
                diagnostic_state_county_count=state_rank.count,
                diagnostic_midatlantic_county_count=regional_rank.count,
                diagnostic_midatlantic_hotspot_percentile=_hotspot_percentile(
                    regional_rank.rank,
                    regional_rank.count,
                ),
                diagnostic_midatlantic_hotspot_tier=current_tier,
                diagnostic_prior_year_midatlantic_rank_cases=(
                    prior_rank.rank if prior_rank is not None else None
                ),
                diagnostic_midatlantic_rank_change=(
                    prior_rank.rank - regional_rank.rank
                    if prior_rank is not None
                    else None
                ),
                diagnostic_prior_year_midatlantic_hotspot_tier=prior_tier,
                diagnostic_year_over_year_case_change=(
                    row.total_cases - prior_row.total_cases
                    if prior_row is not None
                    else None
                ),
                diagnostic_prior_3yr_top_quintile_count=prior_3yr_top_quintile_count,
                source_panel_sha256=source_panel_sha256,
                feature_quality_flags=_quality_flags(row, prior_row),
            )
        )

    county_year_rows = sorted(
        county_year_rows,
        key=lambda item: (item.year, item.diagnostic_midatlantic_rank_cases, item.county_fips),
    )
    summary_rows = _summary_rows(county_year_rows, source_panel_sha256)
    return RegionalHotspotResult(
        county_year_rows=county_year_rows,
        summary_rows=summary_rows,
    )


def _read_panel_rows(path: Path) -> list[_PanelRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_HOTSPOT_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing regional Lyme panel columns: {sorted(missing)}")
        return sorted(
            [
                _PanelRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row.get("state_abbr", "")),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    year=int(row["year"]),
                    total_cases=int(float(row["total_cases"])),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
                for row in reader
            ],
            key=lambda item: (item.county_fips, item.year),
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


def _regional_ranks(rows: list[_PanelRow]) -> dict[tuple[str, int], _RankedRow]:
    grouped: dict[int, list[_PanelRow]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(row)
    ranked = {}
    for year, year_rows in grouped.items():
        ranked.update(_rank_rows(year_rows, year))
    return ranked


def _state_ranks(rows: list[_PanelRow]) -> dict[tuple[str, int], _RankedRow]:
    grouped: dict[tuple[str, int], list[_PanelRow]] = {}
    for row in rows:
        grouped.setdefault((row.state_fips, row.year), []).append(row)
    ranked = {}
    for (_state_fips, year), year_rows in grouped.items():
        ranked.update(_rank_rows(year_rows, year))
    return ranked


def _rank_rows(rows: list[_PanelRow], year: int) -> dict[tuple[str, int], _RankedRow]:
    sorted_rows = sorted(rows, key=lambda row: (-row.total_cases, row.county_fips))
    total_cases = sum(row.total_cases for row in sorted_rows)
    count = len(sorted_rows)
    return {
        (row.county_fips, year): _RankedRow(
            row=row,
            rank=index,
            count=count,
            total_cases=total_cases,
        )
        for index, row in enumerate(sorted_rows, start=1)
    }


def _hotspot_tier(*, total_cases: int, rank: int, count: int) -> str:
    if total_cases <= 0:
        return "no_reported_cases"
    if rank <= max(1, math.ceil(count * 0.1)):
        return "top_decile"
    if rank <= max(1, math.ceil(count * 0.2)):
        return "top_quintile"
    if rank <= max(1, math.ceil(count * 0.5)):
        return "upper_half"
    return "lower_half"


def _hotspot_percentile(rank: int, count: int) -> float:
    if count <= 1:
        return 1.0
    return _round((count - rank) / (count - 1))


def _prior_top_quintile_count(
    *,
    row: _PanelRow,
    rows_by_county_year: dict[tuple[str, int], _PanelRow],
    regional_rank_by_key: dict[tuple[str, int], _RankedRow],
) -> int:
    count = 0
    for year in range(row.year - 3, row.year):
        prior_row = rows_by_county_year.get((row.county_fips, year))
        prior_rank = regional_rank_by_key.get((row.county_fips, year))
        if prior_row is None or prior_rank is None:
            continue
        tier = _hotspot_tier(
            total_cases=prior_row.total_cases,
            rank=prior_rank.rank,
            count=prior_rank.count,
        )
        if tier in TOP_QUINTILE_TIERS:
            count += 1
    return count


def _summary_rows(
    county_year_rows: list[RegionalHotspotCountyYear],
    source_panel_sha256: str,
) -> list[RegionalHotspotSummary]:
    rows_by_year: dict[int, list[RegionalHotspotCountyYear]] = {}
    for row in county_year_rows:
        rows_by_year.setdefault(row.year, []).append(row)
    summary_rows = []
    for year, rows in sorted(rows_by_year.items()):
        current_top = {
            row.county_fips
            for row in rows
            if row.diagnostic_midatlantic_hotspot_tier in TOP_QUINTILE_TIERS
        }
        prior_rows = rows_by_year.get(year - 1)
        prior_top = {
            row.county_fips
            for row in prior_rows or []
            if row.diagnostic_midatlantic_hotspot_tier in TOP_QUINTILE_TIERS
        } if prior_rows is not None else None
        summary_rows.append(
            RegionalHotspotSummary(
                year=year,
                diagnostic_midatlantic_total_cases=sum(row.total_cases for row in rows),
                diagnostic_county_count=len(rows),
                diagnostic_top_decile_count=sum(
                    1
                    for row in rows
                    if row.diagnostic_midatlantic_hotspot_tier == "top_decile"
                ),
                diagnostic_top_quintile_count=len(current_top),
                diagnostic_persistent_top_quintile_count=(
                    len(current_top & prior_top)
                    if prior_top is not None
                    else None
                ),
                diagnostic_new_top_quintile_count=(
                    len(current_top - prior_top)
                    if prior_top is not None
                    else None
                ),
                diagnostic_exited_top_quintile_count=(
                    len(prior_top - current_top)
                    if prior_top is not None
                    else None
                ),
                source_panel_sha256=source_panel_sha256,
                feature_quality_flags=HOTSPOT_QUALITY_FLAGS,
            )
        )
    return summary_rows


def _quality_flags(row: _PanelRow, prior_row: _PanelRow | None) -> str:
    flags = [*HOTSPOT_QUALITY_FLAGS.split(",")]
    if prior_row is None:
        flags.append("insufficient_prior_year_history")
    flags.extend(flag for flag in row.feature_quality_flags.split(",") if flag)
    return ",".join(dict.fromkeys(flags))


def _share(numerator: int, denominator: int | None) -> float | None:
    if denominator in (None, 0):
        return None
    return _round(numerator / denominator)


def _round(value: float) -> float:
    return round(value, 6)
