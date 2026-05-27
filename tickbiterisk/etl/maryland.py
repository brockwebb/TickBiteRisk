from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class MarylandJurisdiction:
    county_fips: str
    state_fips: str
    state: str
    county_name: str


def load_maryland_jurisdictions() -> list[MarylandJurisdiction]:
    resource = files("tickbiterisk.resources").joinpath("maryland_jurisdictions.csv")
    with resource.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    jurisdictions = [
        MarylandJurisdiction(
            county_fips=str(row["county_fips"]).zfill(5),
            state_fips=str(row["state_fips"]).zfill(2),
            state=row["state"],
            county_name=row["county_name"],
        )
        for row in rows
    ]
    if len(jurisdictions) != 24:
        raise ValueError(f"Expected 24 Maryland jurisdictions, found {len(jurisdictions)}")
    return jurisdictions


def maryland_fips_set() -> set[str]:
    return {row.county_fips for row in load_maryland_jurisdictions()}
