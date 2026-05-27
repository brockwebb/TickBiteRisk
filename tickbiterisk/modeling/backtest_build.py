from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.backtest import ModelBacktestResult


MODEL_BACKTEST_RUN_COLUMNS = [
    "run_id",
    "model_features_path",
    "model_features_sha256",
    "start_year",
    "end_year",
    "min_train_years",
    "lookback_years",
    "model_names",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "weather_mode",
    "n_feature_rows",
    "n_predictions",
    "backtest_assumption_flags",
]

MODEL_BACKTEST_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "weather_mode",
    "source_file_sha256",
    "county_fips",
    "county_name",
    "test_year",
    "train_start_year",
    "train_end_year",
    "train_year_count",
    "actual_cases",
    "actual_population",
    "actual_incidence_per_100k",
    "predicted_cases",
    "predicted_incidence_per_100k",
    "residual_incidence_per_100k",
    "absolute_error_incidence_per_100k",
    "residual_cases",
    "absolute_error_cases",
    "model_feature_quality_flags",
    "backtest_assumption_flags",
]

MODEL_BACKTEST_METRIC_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "evaluation_mode",
    "weather_mode",
    "source_file_sha256",
    "aggregation",
    "test_year",
    "n_predictions",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "mean_bias_incidence_per_100k",
    "mae_cases",
    "rmse_cases",
    "pearson_correlation",
    "backtest_assumption_flags",
]


@dataclass(frozen=True)
class ModelBacktestOutputPaths:
    runs_path: Path
    predictions_path: Path
    metrics_path: Path


def write_model_backtest_outputs(
    result: ModelBacktestResult,
    output_dir: Path,
    *,
    append: bool = False,
) -> ModelBacktestOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "model_backtest_runs.csv"
    predictions_path = output_dir / "model_backtest_predictions.csv"
    metrics_path = output_dir / "model_backtest_metrics.csv"
    run_records = [asdict(result.run)]
    prediction_records = [asdict(row) for row in result.predictions]
    metric_records = [asdict(row) for row in result.metrics]
    if append and runs_path.exists():
        run_records = [*_read_existing_records(runs_path), *run_records]
    if append and predictions_path.exists():
        prediction_records = [
            *_read_existing_records(predictions_path),
            *prediction_records,
        ]
    if append and metrics_path.exists():
        metric_records = [*_read_existing_records(metrics_path), *metric_records]
    _write_records(
        runs_path,
        _dedupe_run_records(run_records),
        MODEL_BACKTEST_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        _dedupe_prediction_records(prediction_records),
        MODEL_BACKTEST_PREDICTION_COLUMNS,
    )
    _write_records(
        metrics_path,
        _dedupe_metric_records(metric_records),
        MODEL_BACKTEST_METRIC_COLUMNS,
    )
    return ModelBacktestOutputPaths(
        runs_path=runs_path,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
    )


def _write_records(
    output_path: Path,
    records: list[dict[str, object]],
    columns: list[str],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
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


def _dedupe_prediction_records(
    records: list[dict[str, object]]
) -> list[dict[str, object]]:
    keyed = {_prediction_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], key[1], int(key[2]), key[3]),
        )
    ]


def _dedupe_run_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {str(record["run_id"]): record for record in records}
    return [keyed[key] for key in sorted(keyed)]


def _dedupe_metric_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {_metric_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], key[1], key[2], key[3] or ""),
        )
    ]


def _prediction_key(record: dict[str, object]) -> tuple[str, str, str, str]:
    return (
        str(record["run_id"]),
        str(record["model_name"]),
        str(record["test_year"]),
        str(record["county_fips"]).zfill(5),
    )


def _metric_key(record: dict[str, object]) -> tuple[str, str, str, str]:
    return (
        str(record["run_id"]),
        str(record["model_name"]),
        str(record["aggregation"]),
        _format_value(record.get("test_year")),
    )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
