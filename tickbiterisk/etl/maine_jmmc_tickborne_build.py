from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.maine_jmmc_tickborne import MaineJmmcTickborneCountyRate


MAINE_JMMC_TICKBORNE_RATES_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "year",
    "preliminary_as_of",
    "region_name",
    "county_name",
    "county_fips",
    "geography_type",
    "anaplasmosis_rate_per_100k",
    "babesiosis_rate_per_100k",
    "hard_tick_relapsing_fever_rate_per_100k",
    "lyme_disease_rate_per_100k",
    "powassan_virus_disease_rate_per_100k",
    "source_id",
    "source_url",
    "parser_method",
    "feature_quality_flags",
]


def write_maine_jmmc_tickborne_rates_output(
    rows: list[MaineJmmcTickborneCountyRate],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "maine_jmmc_tickborne_county_rates_2024.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MAINE_JMMC_TICKBORNE_RATES_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record[column])
                for column in MAINE_JMMC_TICKBORNE_RATES_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
