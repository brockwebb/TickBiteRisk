from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import maryland_fips_set


@dataclass(frozen=True)
class LymeCountyYearValue:
    source_id: str
    county_fips: str
    year: int
    confirmed_cases: int | None
    probable_cases: int | None
    total_cases: int


def _frequency_to_int(value: object) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "N", "U", "Suppressed"}:
        return 0
    return int(float(text))


def parse_cdc_lyme_public_use(path: Path, source_id: str) -> list[LymeCountyYearValue]:
    df = pd.read_csv(path, dtype=str)
    df.columns = [column.strip().lower() for column in df.columns]
    required = {"year", "state", "fips", "case_status", "frequency"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CDC Lyme public-use columns: {sorted(missing)}")

    md_fips = maryland_fips_set()
    df = df[df["state"].eq("MD")].copy()
    df["fips"] = df["fips"].astype(str).str.strip().str.zfill(5)
    df = df[df["fips"].isin(md_fips)].copy()
    df["frequency_int"] = df["frequency"].map(_frequency_to_int)
    grouped = (
        df.groupby(["fips", "year", "case_status"], dropna=False)["frequency_int"]
        .sum()
        .reset_index()
    )

    rows: list[LymeCountyYearValue] = []
    for (fips, year), group in grouped.groupby(["fips", "year"]):
        statuses = {
            str(row.case_status).strip().lower(): int(row.frequency_int)
            for row in group.itertuples(index=False)
        }
        confirmed = statuses.get("confirmed")
        probable = statuses.get("probable")
        total = sum(statuses.values())
        rows.append(
            LymeCountyYearValue(
                source_id=source_id,
                county_fips=str(fips).zfill(5),
                year=int(year),
                confirmed_cases=confirmed,
                probable_cases=probable,
                total_cases=total,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))
