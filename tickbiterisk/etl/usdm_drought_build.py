from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.usdm_drought import (
    UsdmDroughtCountyYear,
    UsdmDroughtWeekly,
)


USDM_WEEKLY_COLUMNS = [
    "county_fips",
    "county_name",
    "state",
    "map_date",
    "dsci",
    "pct_none",
    "pct_d0",
    "pct_d1",
    "pct_d2",
    "pct_d3",
    "pct_d4",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
]

USDM_COUNTY_YEAR_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "usdm_week_count",
    "usdm_dsci_mean",
    "usdm_dsci_max",
    "usdm_weeks_d0_or_worse",
    "usdm_weeks_d1_or_worse",
    "usdm_weeks_d2_or_worse",
    "usdm_tick_season_week_count",
    "usdm_tick_season_dsci_mean",
    "usdm_tick_season_weeks_d1_or_worse",
    "source_ids",
    "feature_quality_flags",
]


def write_usdm_weekly_output(
    rows: list[UsdmDroughtWeekly],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "usdm_drought_weekly.csv",
        USDM_WEEKLY_COLUMNS,
        append=append,
        key=lambda record: (
            _normalize_fips(record["county_fips"]),
            str(record["map_date"]),
        ),
        sort_key=lambda record: (
            _normalize_fips(record["county_fips"]),
            str(record["map_date"]),
        ),
    )


def write_usdm_county_year_output(
    rows: list[UsdmDroughtCountyYear],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "usdm_drought_county_year.csv",
        USDM_COUNTY_YEAR_COLUMNS,
        append=append,
        key=lambda record: (_normalize_fips(record["county_fips"]), int(record["year"])),
        sort_key=lambda record: (
            _normalize_fips(record["county_fips"]),
            int(record["year"]),
        ),
    )


def _write_records(
    rows: list[object],
    output_dir: Path,
    filename: str,
    columns: list[str],
    *,
    append: bool,
    key,
    sort_key,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    records = [_record_from_row(row, columns) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {key(record): record for record in records}
    ordered = sorted(keyed.values(), key=sort_key)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: object, columns: list[str]) -> dict[str, object]:
    raw = asdict(row)
    record = {column: raw.get(column, "") for column in columns}
    record["county_fips"] = _normalize_fips(record["county_fips"])
    return record


def _read_existing_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {**record, "county_fips": _normalize_fips(record["county_fips"])}
            for record in csv.DictReader(handle)
        ]


def _normalize_fips(value: object) -> str:
    return str(value).strip().zfill(5)
