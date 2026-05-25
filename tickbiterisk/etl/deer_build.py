from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.deer_harvest import MarylandDeerHarvest


DEER_HARVEST_COLUMNS = [
    "county_fips",
    "county_name",
    "season_start_year",
    "season_label",
    "species",
    "antlered_harvest",
    "antlerless_harvest",
    "total_harvest",
    "land_area_sqmi",
    "harvest_per_sqmi",
    "is_derived_total",
    "source_id",
    "source_url_hash",
]


def write_deer_harvest_output(
    rows: list[MarylandDeerHarvest],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "maryland_dnr_deer_harvest.csv"
    df = pd.DataFrame([asdict(row) for row in rows], columns=DEER_HARVEST_COLUMNS)
    if append and output_path.exists():
        existing = pd.read_csv(output_path, dtype={"county_fips": str})
        df = pd.concat([existing, df], ignore_index=True)
    if not df.empty:
        df["county_fips"] = df["county_fips"].astype(str).str.zfill(5)
        df = df.drop_duplicates(
            subset=["county_fips", "season_start_year", "species"],
            keep="last",
        )
        df = df.sort_values(
            ["county_fips", "season_start_year", "species"]
        ).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    return output_path


def dedupe_deer_harvest_rows(
    rows: list[MarylandDeerHarvest],
) -> list[MarylandDeerHarvest]:
    keyed = {
        (row.county_fips, row.season_start_year, row.species): row for row in rows
    }
    return sorted(
        keyed.values(),
        key=lambda row: (row.county_fips, row.season_start_year, row.species),
    )
