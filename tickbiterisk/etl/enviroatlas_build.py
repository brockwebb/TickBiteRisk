from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.enviroatlas import EnviroAtlasCountyHabitat


ENVIROATLAS_COUNTY_HABITAT_COLUMNS = [
    "county_fips",
    "county_name",
    "forest_pct",
    "forest_woody_wetland_pct",
    "wetland_pct",
    "emergent_wetland_pct",
    "developed_pct",
    "impervious_pct",
    "agriculture_pct",
    "pasture_hay_pct",
    "cultivated_crop_pct",
    "riparian_natural_45m_pct",
    "riparian_forest_45m_pct",
    "riparian_forest_woody_wetland_45m_pct",
    "natural_land_cover_index",
    "source_url_hash",
    "feature_quality_flags",
]


def write_enviroatlas_county_habitat_output(
    rows: list[EnviroAtlasCountyHabitat],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "enviroatlas_county_habitat.csv"
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record): record for record in records}
    ordered = sorted(keyed.values(), key=_record_key)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ENVIROATLAS_COUNTY_HABITAT_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: EnviroAtlasCountyHabitat) -> dict[str, object]:
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


def _record_key(record: dict[str, object]) -> str:
    return str(record["county_fips"]).zfill(5)
