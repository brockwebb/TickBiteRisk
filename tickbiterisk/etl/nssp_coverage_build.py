from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.nssp_coverage import NsspCoverageCountyStatus


NSSP_COVERAGE_COLUMNS = [
    "county_fips",
    "state_abbr",
    "county_name",
    "nssp_county_name",
    "nssp_coverage_status",
    "nssp_coverage_category",
    "recent_data_in_nssp",
    "coverage_as_of_date",
    "source_id",
    "source_url",
    "feature_quality_flags",
]


def write_nssp_coverage_output(
    rows: list[NsspCoverageCountyStatus],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "nssp_coverage_county_status.csv"
    keyed = {
        row.county_fips: {
            column: _format_value(asdict(row).get(column))
            for column in NSSP_COVERAGE_COLUMNS
        }
        for row in rows
    }
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NSSP_COVERAGE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            [keyed[county_fips] for county_fips in sorted(keyed)]
        )
    return output_path


def _format_value(value: object) -> object:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value
