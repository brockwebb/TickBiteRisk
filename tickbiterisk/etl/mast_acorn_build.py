from __future__ import annotations

import csv
from collections.abc import Callable, Iterable
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.mast_acorn import (
    ManualMastObservation,
    MastAcornCountyYear,
    MastAcornExtractionSummary,
)


MAST_ACORN_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "region",
    "mast_category",
    "mast_index",
    "mast_rating",
    "acorn_index",
    "hard_mast_index",
    "soft_mast_index",
    "plots_observed",
    "expected_plots",
    "coverage_complete",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
    "extracted_text_excerpt",
]

MAST_ACORN_SUMMARY_COLUMNS = [
    "source_id",
    "source_url_hash",
    "year",
    "parser",
    "source_path",
    "extraction_status",
    "structured_row_count",
    "feature_quality_flags",
    "notes",
    "extracted_text_excerpt",
]

MANUAL_MAST_OBSERVATION_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "mast_rating",
    "observation_basis",
    "observer_scope",
    "source_id",
    "feature_quality_flags",
    "notes",
]


def write_mast_acorn_output(
    rows: list[MastAcornCountyYear],
    output_dir: str | Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "maryland_dnr_mast_acorn_county_year.csv",
        MAST_ACORN_COLUMNS,
        append=append,
        key=_mast_acorn_key,
        sort_key=_mast_acorn_key,
    )


def write_mast_acorn_summary_output(
    rows: list[MastAcornExtractionSummary],
    output_dir: str | Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "maryland_dnr_mast_acorn_extraction_summary.csv",
        MAST_ACORN_SUMMARY_COLUMNS,
        append=append,
        key=_summary_key,
        sort_key=_summary_key,
    )


def write_manual_mast_observations_output(
    rows: list[ManualMastObservation],
    output_dir: str | Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "manual_mast_observations_county_year.csv",
        MANUAL_MAST_OBSERVATION_COLUMNS,
        append=append,
        key=_manual_observation_key,
        sort_key=_manual_observation_key,
    )


def _write_records(
    rows: Iterable[object],
    output_dir: str | Path,
    filename: str,
    fieldnames: list[str],
    *,
    append: bool,
    key: Callable[[dict[str, object]], tuple[object, ...]],
    sort_key: Callable[[dict[str, object]], tuple[object, ...]],
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    records = [_record_from_row(row, fieldnames) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {key(record): record for record in records}
    ordered = sorted(keyed.values(), key=sort_key)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: object, fieldnames: list[str]) -> dict[str, object]:
    raw_record = asdict(row)
    record = {fieldname: raw_record.get(fieldname, "") for fieldname in fieldnames}
    if "county_fips" in record:
        record["county_fips"] = _normalize_county_fips(record["county_fips"])
    return record


def _read_existing_records(output_path: Path) -> list[dict[str, object]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records: list[dict[str, object]] = []
        for record in reader:
            if "county_fips" in record:
                record["county_fips"] = _normalize_county_fips(record["county_fips"])
            records.append(record)
        return records


def _mast_acorn_key(record: dict[str, object]) -> tuple[str, int, str, str]:
    return (
        _normalize_county_fips(record["county_fips"]),
        int(record["year"]),
        str(record["mast_category"] or ""),
        str(record["source_id"]),
    )


def _summary_key(record: dict[str, object]) -> tuple[str, str]:
    return (str(record["source_id"]), str(record["parser"]))


def _manual_observation_key(record: dict[str, object]) -> tuple[str, int, str]:
    return (
        _normalize_county_fips(record["county_fips"]),
        int(record["year"]),
        str(record["source_id"]),
    )


def _normalize_county_fips(value: object) -> str:
    return str(value).strip().zfill(5)
