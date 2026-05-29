from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.nj_reportable_tickborne import (
    NewJerseyReportableTickborneCountyYear,
)


NJ_DOH_REPORTABLE_TICKBORNE_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "report_year",
    "report_period_start",
    "report_period_end",
    "prepared_at",
    "jurisdiction",
    "county_name",
    "county_fips",
    "geography_type",
    "disease",
    "case_count",
    "source_id",
    "source_url",
    "parser_method",
    "feature_quality_flags",
]


def write_nj_doh_reportable_tickborne_output(
    rows: list[NewJerseyReportableTickborneCountyYear],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "nj_doh_reportable_tickborne_county_year.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NJ_DOH_REPORTABLE_TICKBORNE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record[column])
                for column in NJ_DOH_REPORTABLE_TICKBORNE_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
