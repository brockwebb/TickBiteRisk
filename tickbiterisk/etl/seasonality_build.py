from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.etl.seasonality import (
    SeasonalityBaseline,
    SeasonalityObservation,
)


SEASONALITY_OBSERVATION_COLUMNS = [
    "source_id",
    "disease",
    "grain",
    "year",
    "period",
    "period_label",
    "cases",
    "annual_cases",
    "seasonal_share",
]

SEASONALITY_BASELINE_COLUMNS = [
    "source_id",
    "disease",
    "grain",
    "period",
    "period_label",
    "years_observed",
    "mean_cases",
    "median_cases",
    "min_cases",
    "max_cases",
    "mean_share",
    "median_share",
    "lower_80_share",
    "upper_80_share",
    "lower_95_share",
    "upper_95_share",
    "peak_rank",
    "cumulative_mean_share",
    "feature_quality_flags",
]


@dataclass(frozen=True)
class SeasonalityOutputPaths:
    observations_path: Path
    baseline_path: Path


def write_seasonality_outputs(
    *,
    observations: list[SeasonalityObservation],
    baseline_rows: list[SeasonalityBaseline],
    output_dir: Path,
    append: bool = False,
) -> SeasonalityOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    observations_path = output_dir / "seasonality_observations.csv"
    baseline_path = output_dir / "seasonality_baseline.csv"
    observation_records = [asdict(row) for row in observations]
    baseline_records = [asdict(row) for row in baseline_rows]
    if append and observations_path.exists():
        observation_records = [
            *_read_existing_records(observations_path),
            *observation_records,
        ]
    if append and baseline_path.exists():
        baseline_records = [*_read_existing_records(baseline_path), *baseline_records]
    _write_records(
        observations_path,
        _dedupe_observations(observation_records),
        SEASONALITY_OBSERVATION_COLUMNS,
    )
    _write_records(
        baseline_path,
        _dedupe_baseline(baseline_records),
        SEASONALITY_BASELINE_COLUMNS,
    )
    return SeasonalityOutputPaths(
        observations_path=observations_path,
        baseline_path=baseline_path,
    )


def _write_records(
    path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record.get(column))
                for column in columns
            }
            for record in records
        )


def _read_existing_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _dedupe_observations(
    records: list[dict[str, object]]
) -> list[dict[str, object]]:
    keyed = {_observation_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], key[1], key[2], int(key[3]), int(key[4])),
        )
    ]


def _dedupe_baseline(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {_baseline_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(keyed, key=lambda key: (key[0], key[1], key[2], int(key[3])))
    ]


def _observation_key(record: dict[str, object]) -> tuple[str, str, str, str, str]:
    return (
        str(record["source_id"]),
        str(record["disease"]),
        str(record["grain"]),
        str(record["year"]),
        str(record["period"]),
    )


def _baseline_key(record: dict[str, object]) -> tuple[str, str, str, str]:
    return (
        str(record["source_id"]),
        str(record["disease"]),
        str(record["grain"]),
        str(record["period"]),
    )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
