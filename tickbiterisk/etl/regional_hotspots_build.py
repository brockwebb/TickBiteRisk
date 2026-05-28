from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.etl.regional_hotspots import RegionalHotspotResult


REGIONAL_HOTSPOT_COUNTY_YEAR_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "diagnostic_state_total_cases",
    "diagnostic_midatlantic_total_cases",
    "diagnostic_state_case_share",
    "diagnostic_midatlantic_case_share",
    "diagnostic_state_rank_cases",
    "diagnostic_midatlantic_rank_cases",
    "diagnostic_state_county_count",
    "diagnostic_midatlantic_county_count",
    "diagnostic_midatlantic_hotspot_percentile",
    "diagnostic_midatlantic_hotspot_tier",
    "diagnostic_prior_year_midatlantic_rank_cases",
    "diagnostic_midatlantic_rank_change",
    "diagnostic_prior_year_midatlantic_hotspot_tier",
    "diagnostic_year_over_year_case_change",
    "diagnostic_prior_3yr_top_quintile_count",
    "source_panel_sha256",
    "feature_quality_flags",
]

REGIONAL_HOTSPOT_SUMMARY_COLUMNS = [
    "year",
    "diagnostic_midatlantic_total_cases",
    "diagnostic_county_count",
    "diagnostic_top_decile_count",
    "diagnostic_top_quintile_count",
    "diagnostic_persistent_top_quintile_count",
    "diagnostic_new_top_quintile_count",
    "diagnostic_exited_top_quintile_count",
    "source_panel_sha256",
    "feature_quality_flags",
]


@dataclass(frozen=True)
class RegionalHotspotOutputPaths:
    county_year_path: Path
    summary_path: Path


def write_regional_hotspot_outputs(
    result: RegionalHotspotResult,
    output_dir: Path,
) -> RegionalHotspotOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    county_year_path = output_dir / "midatlantic_hotspot_county_year.csv"
    summary_path = output_dir / "midatlantic_hotspot_summary.csv"
    _write_records(
        county_year_path,
        [asdict(row) for row in result.county_year_rows],
        REGIONAL_HOTSPOT_COUNTY_YEAR_COLUMNS,
    )
    _write_records(
        summary_path,
        [asdict(row) for row in result.summary_rows],
        REGIONAL_HOTSPOT_SUMMARY_COLUMNS,
    )
    return RegionalHotspotOutputPaths(
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
