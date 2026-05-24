from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.census_population import CensusCountyPopulation

COUNTY_POPULATION_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "population",
    "source_id",
    "census_dataset",
    "vintage",
    "source_url_hash",
]


def write_county_population_output(
    rows: list[CensusCountyPopulation],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "county_population_year.csv"
    df = pd.DataFrame([asdict(row) for row in rows], columns=COUNTY_POPULATION_COLUMNS)
    if append and output_path.exists():
        existing = pd.read_csv(output_path, dtype={"county_fips": str})
        df = pd.concat([existing, df], ignore_index=True)
    if not df.empty:
        df = df.drop_duplicates(subset=["county_fips", "year"], keep="last")
        df = df.sort_values(["county_fips", "year"]).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    return output_path
