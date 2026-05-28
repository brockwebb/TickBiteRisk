from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


REGIONAL_INCIDENCE_QUALITY_FLAGS = (
    "regional_incidence_diagnostic,"
    "reported_cases_not_stable_true_incidence,"
    "population_denominator_join,"
    "diagnostic_same_year_not_forecast_feature,"
    "not_public_maryland_default"
)
TOP_QUINTILE_TIERS = {"top_decile", "top_quintile"}


@dataclass(frozen=True)
class RegionalIncidenceCountyYear:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    population: int | None
    incidence_per_100k: float | None
    diagnostic_midatlantic_incidence_rank: int | None
    diagnostic_midatlantic_incidence_percentile: float | None
    diagnostic_midatlantic_incidence_tier: str
    diagnostic_prior_year_midatlantic_incidence_rank: int | None
    diagnostic_midatlantic_incidence_rank_change: int | None
    lyme_panel_sha256: str
    population_panel_sha256: str
    feature_quality_flags: str


@dataclass(frozen=True)
class RegionalIncidenceSummary:
    year: int
    n_county_years: int
    n_with_population: int
    n_missing_population: int
    diagnostic_top_decile_incidence_count: int
    diagnostic_top_quintile_incidence_count: int
    diagnostic_persistent_top_quintile_incidence_count: int | None
    diagnostic_new_top_quintile_incidence_count: int | None
    diagnostic_exited_top_quintile_incidence_count: int | None
    lyme_panel_sha256: str
    population_panel_sha256: str
    feature_quality_flags: str


@dataclass(frozen=True)
class RegionalIncidenceResult:
    county_year_rows: list[RegionalIncidenceCountyYear]
    summary_rows: list[RegionalIncidenceSummary]


@dataclass(frozen=True)
class _LymeRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    feature_quality_flags: str


@dataclass(frozen=True)
class _PopulationRow:
    county_fips: str
    year: int
    population: int
    feature_quality_flags: str


def build_midatlantic_incidence_panel(
    *,
    regional_lyme_path: Path,
    regional_population_path: Path,
    lyme_panel_sha256: str,
    population_panel_sha256: str,
) -> RegionalIncidenceResult:
    lyme_rows = _read_lyme_rows(regional_lyme_path)
    population_by_key = {
        (row.county_fips, row.year): row
        for row in _read_population_rows(regional_population_path)
    }
    base_rows = []
    for row in lyme_rows:
        population_row = population_by_key.get((row.county_fips, row.year))
        population = population_row.population if population_row else None
        incidence = (
            _round((row.total_cases / population) * 100000)
            if population is not None and population > 0
            else None
        )
        base_rows.append(
            RegionalIncidenceCountyYear(
                state_fips=row.state_fips,
                state_abbr=row.state_abbr,
                state_name=row.state_name,
                county_fips=row.county_fips,
                county_name=row.county_name,
                year=row.year,
                total_cases=row.total_cases,
                population=population,
                incidence_per_100k=incidence,
                diagnostic_midatlantic_incidence_rank=None,
                diagnostic_midatlantic_incidence_percentile=None,
                diagnostic_midatlantic_incidence_tier="population_missing",
                diagnostic_prior_year_midatlantic_incidence_rank=None,
                diagnostic_midatlantic_incidence_rank_change=None,
                lyme_panel_sha256=lyme_panel_sha256,
                population_panel_sha256=population_panel_sha256,
                feature_quality_flags=_quality_flags(row, population_row),
            )
        )
    county_year_rows = _attach_incidence_ranks(base_rows)
    return RegionalIncidenceResult(
        county_year_rows=county_year_rows,
        summary_rows=_summary_rows(
            county_year_rows,
            lyme_panel_sha256=lyme_panel_sha256,
            population_panel_sha256=population_panel_sha256,
        ),
    )


def _read_lyme_rows(path: Path) -> list[_LymeRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return sorted(
            [
                _LymeRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=row["state_abbr"],
                    state_name=row["state_name"],
                    county_fips=row["county_fips"].zfill(5),
                    county_name=row["county_name"],
                    year=int(row["year"]),
                    total_cases=int(float(row["total_cases"])),
                    feature_quality_flags=row.get("feature_quality_flags", ""),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _read_population_rows(path: Path) -> list[_PopulationRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return sorted(
            [
                _PopulationRow(
                    county_fips=row["county_fips"].zfill(5),
                    year=int(row["year"]),
                    population=int(float(row["population"])),
                    feature_quality_flags=row.get("feature_quality_flags", ""),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _attach_incidence_ranks(
    rows: list[RegionalIncidenceCountyYear],
) -> list[RegionalIncidenceCountyYear]:
    rows_by_year: dict[int, list[RegionalIncidenceCountyYear]] = {}
    for row in rows:
        rows_by_year.setdefault(row.year, []).append(row)
    rank_by_key = {}
    count_by_year = {}
    for year, year_rows in rows_by_year.items():
        ranked_rows = sorted(
            [row for row in year_rows if row.incidence_per_100k is not None],
            key=lambda row: (-(row.incidence_per_100k or 0), row.county_fips),
        )
        count_by_year[year] = len(ranked_rows)
        for rank, row in enumerate(ranked_rows, start=1):
            rank_by_key[(row.county_fips, row.year)] = rank

    output = []
    for row in rows:
        rank = rank_by_key.get((row.county_fips, row.year))
        prior_rank = rank_by_key.get((row.county_fips, row.year - 1))
        count = count_by_year.get(row.year, 0)
        if rank is None:
            output.append(row)
            continue
        output.append(
            RegionalIncidenceCountyYear(
                **{
                    **row.__dict__,
                    "diagnostic_midatlantic_incidence_rank": rank,
                    "diagnostic_midatlantic_incidence_percentile": (
                        _hotspot_percentile(rank, count)
                    ),
                    "diagnostic_midatlantic_incidence_tier": _hotspot_tier(
                        rank=rank,
                        count=count,
                    ),
                    "diagnostic_prior_year_midatlantic_incidence_rank": prior_rank,
                    "diagnostic_midatlantic_incidence_rank_change": (
                        prior_rank - rank if prior_rank is not None else None
                    ),
                }
            )
        )
    return sorted(output, key=lambda row: (row.year, row.county_fips))


def _summary_rows(
    rows: list[RegionalIncidenceCountyYear],
    *,
    lyme_panel_sha256: str,
    population_panel_sha256: str,
) -> list[RegionalIncidenceSummary]:
    rows_by_year: dict[int, list[RegionalIncidenceCountyYear]] = {}
    for row in rows:
        rows_by_year.setdefault(row.year, []).append(row)
    summary = []
    for year, year_rows in sorted(rows_by_year.items()):
        current_top = {
            row.county_fips
            for row in year_rows
            if row.diagnostic_midatlantic_incidence_tier in TOP_QUINTILE_TIERS
        }
        prior_rows = rows_by_year.get(year - 1)
        prior_top = {
            row.county_fips
            for row in prior_rows or []
            if row.diagnostic_midatlantic_incidence_tier in TOP_QUINTILE_TIERS
        } if prior_rows is not None else None
        summary.append(
            RegionalIncidenceSummary(
                year=year,
                n_county_years=len(year_rows),
                n_with_population=sum(
                    1 for row in year_rows if row.population is not None
                ),
                n_missing_population=sum(
                    1 for row in year_rows if row.population is None
                ),
                diagnostic_top_decile_incidence_count=sum(
                    1
                    for row in year_rows
                    if row.diagnostic_midatlantic_incidence_tier == "top_decile"
                ),
                diagnostic_top_quintile_incidence_count=len(current_top),
                diagnostic_persistent_top_quintile_incidence_count=(
                    len(current_top & prior_top)
                    if prior_top is not None
                    else None
                ),
                diagnostic_new_top_quintile_incidence_count=(
                    len(current_top - prior_top)
                    if prior_top is not None
                    else None
                ),
                diagnostic_exited_top_quintile_incidence_count=(
                    len(prior_top - current_top)
                    if prior_top is not None
                    else None
                ),
                lyme_panel_sha256=lyme_panel_sha256,
                population_panel_sha256=population_panel_sha256,
                feature_quality_flags=REGIONAL_INCIDENCE_QUALITY_FLAGS,
            )
        )
    return summary


def _hotspot_tier(*, rank: int, count: int) -> str:
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


def _quality_flags(
    lyme_row: _LymeRow,
    population_row: _PopulationRow | None,
) -> str:
    flags = [*REGIONAL_INCIDENCE_QUALITY_FLAGS.split(",")]
    flags.extend(flag for flag in lyme_row.feature_quality_flags.split(",") if flag)
    if population_row is None:
        flags.append("missing_population_denominator")
    else:
        flags.extend(
            flag for flag in population_row.feature_quality_flags.split(",") if flag
        )
    return ",".join(dict.fromkeys(flags))


def _round(value: float) -> float:
    return round(value, 6)
