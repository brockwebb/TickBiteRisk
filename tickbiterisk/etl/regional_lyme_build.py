from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.regional_lyme import RegionalLymeCountyYear


REGIONAL_LYME_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "source_id",
    "feature_quality_flags",
]


def write_regional_lyme_output(
    rows: list[RegionalLymeCountyYear],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "midatlantic_lyme_county_year.csv"
    _write_regional_lyme_rows(rows, output_path)
    return output_path


def write_regional_lyme_state_validation_output(
    rows: list[RegionalLymeCountyYear],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "regional_lyme_state_source_validation.csv"
    _write_regional_lyme_rows(rows, output_path)
    return output_path


def _write_regional_lyme_rows(
    rows: list[RegionalLymeCountyYear],
    output_path: Path,
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGIONAL_LYME_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: str(record[column])
                for column in REGIONAL_LYME_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
