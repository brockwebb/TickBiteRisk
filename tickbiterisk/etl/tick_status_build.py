from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.etl.tick_status import TickStatusCountyFeature

TICK_VECTOR_STATUS_COLUMNS = [
    "source_id",
    "county_fips",
    "county_name",
    "ixodes_scapularis_status",
    "ixodes_scapularis_source",
    "ixodes_pacificus_status",
    "ixodes_pacificus_source",
]

TICK_PATHOGEN_STATUS_COLUMNS = [
    "source_id",
    "county_fips",
    "county_name",
    "borrelia_burgdorferi_status",
    "borrelia_miyamotoi_status",
    "anaplasma_phagocytophilum_status",
    "babesia_microti_status",
    "powassan_virus_status",
]

LONE_STAR_STATUS_COLUMNS = [
    "source_id",
    "county_fips",
    "county_name",
    "amblyomma_americanum_status",
    "status_source",
    "source_comments",
]

TICK_STATUS_FEATURE_COLUMNS = [
    "county_fips",
    "county_name",
    "ixodes_scapularis_status",
    "ixodes_pacificus_status",
    "borrelia_burgdorferi_status",
    "borrelia_miyamotoi_status",
    "anaplasma_phagocytophilum_status",
    "babesia_microti_status",
    "powassan_virus_status",
    "amblyomma_americanum_status",
    "tick_status_source_ids",
    "tick_status_feature_quality_flags",
]


@dataclass(frozen=True)
class TickStatusOutputPaths:
    vector_path: Path
    pathogen_path: Path
    lone_star_path: Path
    features_path: Path


def write_tick_status_outputs(
    *,
    ixodes_rows: list[dict[str, object]],
    pathogen_rows: list[dict[str, object]],
    lone_star_rows: list[dict[str, object]],
    feature_rows: list[TickStatusCountyFeature],
    output_dir: Path,
) -> TickStatusOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    vector_path = output_dir / "tick_vector_status.csv"
    pathogen_path = output_dir / "tick_pathogen_status.csv"
    lone_star_path = output_dir / "lone_star_status.csv"
    features_path = output_dir / "tick_status_county_features.csv"

    _write_records(vector_path, ixodes_rows, TICK_VECTOR_STATUS_COLUMNS)
    _write_records(pathogen_path, pathogen_rows, TICK_PATHOGEN_STATUS_COLUMNS)
    _write_records(lone_star_path, lone_star_rows, LONE_STAR_STATUS_COLUMNS)
    _write_records(
        features_path,
        [asdict(row) for row in feature_rows],
        TICK_STATUS_FEATURE_COLUMNS,
    )
    return TickStatusOutputPaths(
        vector_path=vector_path,
        pathogen_path=pathogen_path,
        lone_star_path=lone_star_path,
        features_path=features_path,
    )


def _write_records(
    output_path: Path,
    rows: list[dict[str, object]],
    columns: list[str],
) -> None:
    keyed = {
        _record_key(record): {
            column: _format_value(record.get(column))
            for column in columns
        }
        for record in rows
    }
    ordered = sorted(keyed.values(), key=lambda row: _record_key(row))
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(ordered)


def _record_key(record: dict[str, object]) -> tuple[str, str]:
    return (
        str(record.get("county_fips", "")).zfill(5),
        str(record.get("source_id", "")),
    )


def _format_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value.strip().lower() in {"nan", "none"}:
        return ""
    return value
