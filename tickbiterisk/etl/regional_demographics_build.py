from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.regional_demographics import RegionalAgeDemographic


REGIONAL_AGE_DEMOGRAPHICS_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "population",
    "under5_population",
    "age5_13_population",
    "age14_17_population",
    "age5_17_population",
    "age18_24_population",
    "age25_44_population",
    "age45_64_population",
    "age65plus_population",
    "median_age",
    "under5_share",
    "age5_17_share",
    "age18_24_share",
    "age25_44_share",
    "age45_64_share",
    "age65plus_share",
    "source_id",
    "census_dataset",
    "vintage",
    "source_url_hash",
    "feature_quality_flags",
]


def write_regional_age_demographics_output(
    rows: list[RegionalAgeDemographic],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "midatlantic_age_demographics_county_year.csv"
    keyed = {
        (row.county_fips, row.year): {
            column: _format_value(asdict(row).get(column))
            for column in REGIONAL_AGE_DEMOGRAPHICS_COLUMNS
        }
        for row in rows
    }
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=REGIONAL_AGE_DEMOGRAPHICS_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(
            [keyed[key] for key in sorted(keyed, key=lambda item: (item[0], item[1]))]
        )
    return output_path


def _format_value(value: object) -> object:
    if value is None:
        return ""
    return value
