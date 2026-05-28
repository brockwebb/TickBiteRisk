from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.enso import (
    MeiV2ModelYearFeatures,
    MeiV2Month,
    ONI_SEASON_ORDER,
    OniModelYearFeatures,
    OniSeason,
)


ONI_SEASON_COLUMNS = [
    "season",
    "year",
    "total_sst_c",
    "oni_anomaly_c",
    "enso_phase",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
]

ONI_MODEL_YEAR_COLUMNS = [
    "model_year",
    "oni_prior_year_season_count",
    "oni_prior_year_mean_anomaly_c",
    "oni_prior_year_max_anomaly_c",
    "oni_prior_year_min_anomaly_c",
    "oni_prior_year_el_nino_season_count",
    "oni_prior_year_la_nina_season_count",
    "source_ids",
    "source_url_hashes",
    "feature_quality_flags",
]

MEI_V2_MONTHLY_COLUMNS = [
    "month_start_date",
    "year",
    "month",
    "mei_v2_value",
    "mei_v2_phase",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
]

MEI_V2_MODEL_YEAR_COLUMNS = [
    "model_year",
    "mei_v2_prior_year_month_count",
    "mei_v2_prior_year_mean",
    "mei_v2_prior_year_max",
    "mei_v2_prior_year_min",
    "mei_v2_prior_year_positive_month_count",
    "mei_v2_prior_year_negative_month_count",
    "source_ids",
    "source_url_hashes",
    "feature_quality_flags",
]


def write_oni_season_output(
    rows: list[OniSeason],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "noaa_cpc_oni_seasons.csv",
        ONI_SEASON_COLUMNS,
        append=append,
        key=lambda record: (int(record["year"]), str(record["season"])),
        sort_key=lambda record: (
            int(record["year"]),
            ONI_SEASON_ORDER[str(record["season"])],
        ),
    )


def write_oni_model_year_output(
    rows: list[OniModelYearFeatures],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "noaa_cpc_oni_model_year_features.csv",
        ONI_MODEL_YEAR_COLUMNS,
        append=append,
        key=lambda record: int(record["model_year"]),
        sort_key=lambda record: int(record["model_year"]),
    )


def write_mei_v2_monthly_output(
    rows: list[MeiV2Month],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "noaa_psl_mei_v2_monthly.csv",
        MEI_V2_MONTHLY_COLUMNS,
        append=append,
        key=lambda record: (int(record["year"]), int(record["month"])),
        sort_key=lambda record: (int(record["year"]), int(record["month"])),
    )


def write_mei_v2_model_year_output(
    rows: list[MeiV2ModelYearFeatures],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_records(
        rows,
        output_dir,
        "noaa_psl_mei_v2_model_year_features.csv",
        MEI_V2_MODEL_YEAR_COLUMNS,
        append=append,
        key=lambda record: int(record["model_year"]),
        sort_key=lambda record: int(record["model_year"]),
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
    return {column: raw.get(column, "") for column in columns}


def _read_existing_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
