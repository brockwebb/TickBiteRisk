from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.regional_population import RegionalCountyPopulation


REGIONAL_COUNTY_POPULATION_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "population",
    "source_id",
    "census_dataset",
    "vintage",
    "source_url_hash",
    "feature_quality_flags",
]


def write_regional_county_population_output(
    rows: list[RegionalCountyPopulation],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "midatlantic_county_population_year.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGIONAL_COUNTY_POPULATION_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: str(record[column])
                for column in REGIONAL_COUNTY_POPULATION_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path
