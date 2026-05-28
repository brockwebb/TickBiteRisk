from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.etl.lyme_aggregate import LymeAggregateObservation


LYME_AGGREGATE_COLUMNS = [
    "geography_type",
    "geography_id",
    "geography_name",
    "year",
    "cases",
    "incidence_per_100k",
    "cases_source_id",
    "rate_source_id",
    "feature_quality_flags",
]


@dataclass(frozen=True)
class LymeAggregateOutputPaths:
    state_path: Path
    region_path: Path
    national_path: Path


def write_lyme_aggregate_outputs(
    *,
    state_rows: list[LymeAggregateObservation],
    region_rows: list[LymeAggregateObservation],
    national_rows: list[LymeAggregateObservation],
    output_dir: Path,
) -> LymeAggregateOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "cdc_lyme_state_year.csv"
    region_path = output_dir / "cdc_lyme_region_year.csv"
    national_path = output_dir / "cdc_lyme_national_year.csv"
    _write_rows(state_path, state_rows)
    _write_rows(region_path, region_rows)
    _write_rows(national_path, national_rows)
    return LymeAggregateOutputPaths(
        state_path=state_path,
        region_path=region_path,
        national_path=national_path,
    )


def _write_rows(path: Path, rows: list[LymeAggregateObservation]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LYME_AGGREGATE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record.get(column))
                for column in LYME_AGGREGATE_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
