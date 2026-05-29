from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.wv_vectorborne import WestVirginiaVectorborneStateSummary


WV_VECTORBORNE_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "report_year",
    "as_of_date",
    "disease",
    "confirmed_probable_cases",
    "counties_reported",
    "source_id",
    "source_url",
    "parser_method",
    "feature_quality_flags",
]


def write_wv_vectorborne_state_summary(
    rows: list[WestVirginiaVectorborneStateSummary],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "wv_vectorborne_state_summary.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WV_VECTORBORNE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record[column])
                for column in WV_VECTORBORNE_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
