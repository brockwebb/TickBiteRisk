from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.building_permits import CensusBuildingPermitCountyYear


BUILDING_PERMIT_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "month",
    "one_unit_units",
    "two_unit_units",
    "three_four_unit_units",
    "five_plus_unit_units",
    "total_units_authorized",
    "total_value_dollars",
    "source_id",
    "source_url_hash",
]


def write_building_permits_output(
    rows: list[CensusBuildingPermitCountyYear],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "maryland_building_permits_county_year.csv"
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record): record for record in records}
    ordered = sorted(
        keyed.values(),
        key=lambda record: (record["county_fips"], int(record["year"])),
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BUILDING_PERMIT_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: CensusBuildingPermitCountyYear) -> dict[str, object]:
    record = asdict(row)
    record["county_fips"] = str(record["county_fips"]).zfill(5)
    return record


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
