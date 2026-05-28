from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.acs_exposure import AcsExposureCountyYear


ACS_EXPOSURE_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "acs_total_population",
    "age_under_18_population",
    "age_18_64_population",
    "age_65_plus_population",
    "age_under_18_share",
    "age_18_64_share",
    "age_65_plus_share",
    "total_housing_units",
    "single_family_detached_units",
    "single_family_attached_units",
    "single_family_units",
    "single_family_detached_share",
    "single_family_share",
    "occupied_housing_units",
    "owner_occupied_units",
    "owner_occupied_share",
    "land_area_sqmi",
    "population_per_sqmi",
    "housing_units_per_sqmi",
    "single_family_units_per_sqmi",
    "source_id",
    "census_dataset",
    "vintage",
    "acs_source_url_hash",
    "geography_source_url_hash",
    "feature_quality_flags",
]


def write_acs_exposure_output(
    rows: list[AcsExposureCountyYear],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "midatlantic_acs_exposure_county_year.csv"
    keyed = {
        (row.county_fips, row.year): {
            column: _format_value(asdict(row).get(column))
            for column in ACS_EXPOSURE_COLUMNS
        }
        for row in rows
    }
    if append and output_path.exists():
        keyed = {
            **{
                _record_key(record): record
                for record in _read_existing_records(output_path)
            },
            **keyed,
        }
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACS_EXPOSURE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            [keyed[key] for key in sorted(keyed, key=lambda item: (item[0], item[1]))]
        )
    return output_path


def _format_value(value: object) -> object:
    if value is None:
        return ""
    return value


def _read_existing_records(output_path: Path) -> list[dict[str, str]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                **record,
                "county_fips": str(record["county_fips"]).zfill(5),
            }
            for record in reader
        ]


def _record_key(record: dict[str, object]) -> tuple[str, int]:
    return (str(record["county_fips"]).zfill(5), int(record["year"]))
