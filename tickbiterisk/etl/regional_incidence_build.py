from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.etl.regional_incidence import RegionalIncidenceResult


REGIONAL_INCIDENCE_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "population",
    "incidence_per_100k",
    "diagnostic_midatlantic_incidence_rank",
    "diagnostic_midatlantic_incidence_percentile",
    "diagnostic_midatlantic_incidence_tier",
    "diagnostic_prior_year_midatlantic_incidence_rank",
    "diagnostic_midatlantic_incidence_rank_change",
    "lyme_panel_sha256",
    "population_panel_sha256",
    "feature_quality_flags",
]

REGIONAL_INCIDENCE_SUMMARY_COLUMNS = [
    "year",
    "n_county_years",
    "n_with_population",
    "n_missing_population",
    "diagnostic_top_decile_incidence_count",
    "diagnostic_top_quintile_incidence_count",
    "diagnostic_persistent_top_quintile_incidence_count",
    "diagnostic_new_top_quintile_incidence_count",
    "diagnostic_exited_top_quintile_incidence_count",
    "lyme_panel_sha256",
    "population_panel_sha256",
    "feature_quality_flags",
]


@dataclass(frozen=True)
class RegionalIncidenceOutputPaths:
    county_year_path: Path
    summary_path: Path


def write_regional_incidence_outputs(
    result: RegionalIncidenceResult,
    output_dir: Path,
) -> RegionalIncidenceOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    county_year_path = output_dir / "midatlantic_lyme_incidence_county_year.csv"
    summary_path = output_dir / "midatlantic_lyme_incidence_summary.csv"
    _write_records(
        county_year_path,
        [asdict(row) for row in result.county_year_rows],
        REGIONAL_INCIDENCE_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary_rows],
        REGIONAL_INCIDENCE_SUMMARY_COLUMNS,
    )
    return RegionalIncidenceOutputPaths(
        county_year_path=county_year_path,
        summary_path=summary_path,
    )


def _write_records(
    output_path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record.get(column))
                for column in columns
            }
            for record in records
        )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
