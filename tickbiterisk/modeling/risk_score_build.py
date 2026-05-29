from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.risk_score import SeasonalRiskScoreResult


SEASONAL_RISK_SCORE_COLUMNS = [
    "source_prediction_run_id",
    "source_prediction_sha256",
    "source_seasonality_sha256",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "weather_mode",
    "county_fips",
    "county_name",
    "year",
    "forecast_origin_year",
    "as_of_date",
    "data_cutoff_date",
    "source_vintage",
    "update_mode",
    "mmwr_week",
    "period_label",
    "predicted_annual_incidence_per_100k",
    "predicted_annual_cases",
    "seasonal_mean_share",
    "seasonal_lower_80_share",
    "seasonal_upper_80_share",
    "seasonal_lower_95_share",
    "seasonal_upper_95_share",
    "predicted_weekly_incidence_per_100k",
    "lower_80_weekly_incidence_per_100k",
    "upper_80_weekly_incidence_per_100k",
    "lower_95_weekly_incidence_per_100k",
    "upper_95_weekly_incidence_per_100k",
    "predicted_weekly_cases",
    "benchmark_quantile",
    "headroom_multiplier",
    "score_denominator",
    "risk_score_raw",
    "risk_score",
    "risk_category",
    "seasonality_source_id",
    "model_feature_quality_flags",
    "seasonality_feature_quality_flags",
    "feature_quality_flags",
    "backtest_assumption_flags",
]

RISK_SCORE_SCALE_COLUMNS = [
    "model_name",
    "grain",
    "target_definition",
    "seasonality_source_id",
    "benchmark_quantile",
    "headroom_multiplier",
    "benchmark_weekly_incidence_per_100k",
    "score_denominator",
    "n_score_rows",
    "source_prediction_sha256",
    "source_seasonality_sha256",
    "scale_quality_flags",
]


@dataclass(frozen=True)
class SeasonalRiskScoreOutputPaths:
    scores_path: Path
    scale_path: Path


def write_seasonal_risk_score_outputs(
    result: SeasonalRiskScoreResult,
    output_dir: Path,
    *,
    append: bool = False,
) -> SeasonalRiskScoreOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    scores_path = output_dir / "county_week_seasonal_risk_baseline.csv"
    scale_path = output_dir / "risk_score_scale.csv"
    score_records = [asdict(row) for row in result.rows]
    scale_records = [asdict(result.scale)]
    if append and scores_path.exists():
        score_records = [
            *_read_existing_records(
                scores_path,
                required_columns=SEASONAL_RISK_SCORE_COLUMNS,
            ),
            *score_records,
        ]
    if append and scale_path.exists():
        scale_records = [
            *_read_existing_records(
                scale_path,
                required_columns=RISK_SCORE_SCALE_COLUMNS,
            ),
            *scale_records,
        ]
    _write_records(
        scores_path,
        _dedupe_score_records(score_records),
        SEASONAL_RISK_SCORE_COLUMNS,
    )
    _write_records(
        scale_path,
        _dedupe_scale_records(scale_records),
        RISK_SCORE_SCALE_COLUMNS,
    )
    return SeasonalRiskScoreOutputPaths(scores_path=scores_path, scale_path=scale_path)


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


def _read_existing_records(
    path: Path,
    *,
    required_columns: list[str],
) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if any(column not in fieldnames for column in required_columns):
            return []
        return list(reader)


def _dedupe_score_records(
    records: list[dict[str, object]]
) -> list[dict[str, object]]:
    keyed = {_score_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (
                key[0],
                key[1],
                int(key[2]),
                int(key[3]),
                key[4],
                key[5],
                float(key[6]),
                float(key[7]),
            ),
        )
    ]


def _dedupe_scale_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {_scale_key(record): record for record in records}
    return [keyed[key] for key in sorted(keyed)]


def _score_key(
    record: dict[str, object]
) -> tuple[str, str, str, str, str, str, str, str, str, str]:
    return (
        str(record["county_fips"]).zfill(5),
        str(record["model_name"]),
        str(record["year"]),
        str(record["mmwr_week"]),
        str(record["source_prediction_run_id"]),
        str(record["seasonality_source_id"]),
        str(record["benchmark_quantile"]),
        str(record["headroom_multiplier"]),
        str(record["source_prediction_sha256"]),
        str(record["source_seasonality_sha256"]),
    )


def _scale_key(record: dict[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(record["model_name"]),
        str(record["grain"]),
        str(record["seasonality_source_id"]),
        str(record["source_prediction_sha256"]),
        str(record["source_seasonality_sha256"]),
        str(record["benchmark_quantile"]),
        str(record["headroom_multiplier"]),
    )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
