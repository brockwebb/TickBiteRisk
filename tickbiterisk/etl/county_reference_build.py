from __future__ import annotations

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
