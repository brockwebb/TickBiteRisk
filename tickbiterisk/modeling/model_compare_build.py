from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from tickbiterisk.modeling.model_compare import ModelComparisonResult


MODEL_COMPARISON_RUN_COLUMNS = [
    "run_id",
    "design_matrix_path",
    "design_matrix_sha256",
    "start_year",
    "end_year",
    "min_train_years",
    "ridge_alpha",
    "shrinkage_strength",
    "model_names",
    "target_definition",
    "evaluation_mode",
    "weather_mode",
    "feature_set",
    "n_design_rows",
    "n_predictions",
    "comparison_assumption_flags",
]

MODEL_COMPARISON_PREDICTION_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
    "evaluation_mode",
    "weather_mode",
    "source_file_sha256",
    "county_fips",
    "county_name",
    "test_year",
    "train_start_year",
    "train_end_year",
    "train_row_count",
    "train_county_count",
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
    "comparison_assumption_flags",
]

MODEL_COMPARISON_METRIC_COLUMNS = [
    "run_id",
    "model_name",
    "model_family",
    "target_definition",
    "feature_set",
    "feature_profile",
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
    "comparison_assumption_flags",
]

MODEL_COMPARISON_SUMMARY_COLUMNS = [
    "run_id",
    "rank_by_mae",
    "model_name",
    "model_family",
    "feature_profile",
    "n_predictions",
    "mae_incidence_per_100k",
    "rmse_incidence_per_100k",
    "pearson_correlation",
    "comparison_assumption_flags",
]


@dataclass(frozen=True)
class ModelComparisonOutputPaths:
    runs_path: Path
    predictions_path: Path
    metrics_path: Path
    summary_path: Path


def write_model_comparison_outputs(
    result: ModelComparisonResult,
    output_dir: Path,
    *,
    append: bool = False,
) -> ModelComparisonOutputPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_path = output_dir / "model_comparison_runs.csv"
    predictions_path = output_dir / "model_comparison_predictions.csv"
    metrics_path = output_dir / "model_comparison_metrics.csv"
    summary_path = output_dir / "model_comparison_summary.csv"
    run_records = [asdict(result.run)]
    prediction_records = [asdict(row) for row in result.predictions]
    metric_records = [asdict(row) for row in result.metrics]
    summary_records = [asdict(row) for row in result.summary]
    if append and runs_path.exists():
        run_records = [*_read_existing_records(runs_path), *run_records]
    if append and predictions_path.exists():
        prediction_records = [
            *_read_existing_records(predictions_path),
            *prediction_records,
        ]
    if append and metrics_path.exists():
        metric_records = [*_read_existing_records(metrics_path), *metric_records]
    if append and summary_path.exists():
        summary_records = [*_read_existing_records(summary_path), *summary_records]
    _write_records(
        runs_path,
        _dedupe_run_records(run_records),
        MODEL_COMPARISON_RUN_COLUMNS,
    )
    _write_records(
        predictions_path,
        _dedupe_prediction_records(prediction_records),
        MODEL_COMPARISON_PREDICTION_COLUMNS,
    )
    _write_records(
        metrics_path,
        _dedupe_metric_records(metric_records),
        MODEL_COMPARISON_METRIC_COLUMNS,
    )
    _write_records(
        summary_path,
        _dedupe_summary_records(summary_records),
        MODEL_COMPARISON_SUMMARY_COLUMNS,
    )
    return ModelComparisonOutputPaths(
        runs_path=runs_path,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
        summary_path=summary_path,
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


def _dedupe_run_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {str(record["run_id"]): record for record in records}
    return [keyed[key] for key in sorted(keyed)]


def _dedupe_prediction_records(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    keyed = {_prediction_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], key[1], int(key[2]), key[3]),
        )
    ]


def _dedupe_metric_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keyed = {_metric_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], key[1], key[2], key[3] or ""),
        )
    ]


def _dedupe_summary_records(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    keyed = {_summary_key(record): record for record in records}
    return [
        keyed[key]
        for key in sorted(
            keyed,
            key=lambda key: (key[0], int(key[1]), key[2]),
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


def _summary_key(record: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(record["run_id"]),
        str(record["rank_by_mae"]),
        str(record["model_name"]),
    )


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
