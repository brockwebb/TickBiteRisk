from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.county_reference import CountyReference


COUNTY_REFERENCE_COLUMNS = [
    "county_fips",
    "state_fips",
    "state",
    "county_name",
    "aland_sqmi",
    "awater_sqmi",
    "intptlat",
    "intptlon",
    "geography_source",
    "source_url_hash",
]


def write_county_reference_output(
    rows: list[CountyReference],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "county_reference.csv"
    df = pd.DataFrame([asdict(row) for row in rows], columns=COUNTY_REFERENCE_COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["county_fips"], keep="last")
        df = df.sort_values(["county_fips"]).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    return output_path


def read_county_reference_output(input_path: Path) -> list[CountyReference]:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            CountyReference(
                county_fips=str(row["county_fips"]).zfill(5),
                state_fips=str(row["state_fips"]).zfill(2),
                state=row["state"],
                county_name=row["county_name"],
                aland_sqmi=float(row["aland_sqmi"]),
                awater_sqmi=float(row["awater_sqmi"]),
                intptlat=float(row["intptlat"]),
                intptlon=float(row["intptlon"]),
                geography_source=row["geography_source"],
                source_url_hash=row["source_url_hash"],
            )
            for row in reader
        ]
