import csv
import math
from pathlib import Path

from tickbiterisk.modeling.backtest import (
    run_baseline_backtests,
)
from tickbiterisk.modeling.backtest_build import (
    MODEL_BACKTEST_METRIC_COLUMNS,
    MODEL_BACKTEST_PREDICTION_COLUMNS,
    MODEL_BACKTEST_RUN_COLUMNS,
    write_model_backtest_outputs,
)


def test_run_baseline_backtests_uses_only_prior_years_for_predictions(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        min_train_years=2,
        lookback_years=2,
    )

    predictions = [
        row
        for row in result.predictions
        if row.model_name == "prior_year_incidence" and row.test_year == 2020
    ]
    assert [(row.county_fips, row.predicted_incidence_per_100k) for row in predictions] == [
        ("24001", 20.0),
        ("24003", 80.0),
    ]
    assert all(row.train_start_year == 2018 for row in predictions)
    assert all(row.train_end_year == 2019 for row in predictions)
    assert all(row.train_year_count == 2 for row in predictions)
    assert all(row.evaluation_mode == "forecast_prior_year" for row in predictions)
    assert all(row.weather_mode == "not_used_by_baseline" for row in predictions)
    assert all(len(row.source_file_sha256) == 64 for row in predictions)
    assert all(row.actual_population == 100000 for row in predictions)
    assert all("intervention_history_unmodeled" in row.backtest_assumption_flags for row in predictions)
    assert result.run.start_year == 2020
    assert result.run.end_year == 2022
    assert result.run.n_feature_rows == 10
    assert result.run.n_predictions == 24


def test_run_baseline_backtests_reports_model_metrics(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        min_train_years=2,
        lookback_years=2,
    )

    metric = next(
        row
        for row in result.metrics
        if row.model_name == "prior_year_incidence"
        and row.aggregation == "test_year"
        and row.test_year == 2020
    )
    assert metric.n_predictions == 2
    assert metric.mae_incidence_per_100k == 15.0
    assert metric.rmse_incidence_per_100k == round(math.sqrt(250), 6)
    assert metric.mean_bias_incidence_per_100k == -5.0
    assert metric.pearson_correlation == 1.0

    overall = next(
        row
        for row in result.metrics
        if row.model_name == "county_trailing_mean_incidence"
        and row.aggregation == "overall"
    )
    assert overall.test_year is None
    assert overall.n_predictions == 6
    assert overall.feature_set == "historical_outcome_baselines"


def test_run_baseline_backtests_includes_state_trend_and_blend_models(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        min_train_years=2,
        lookback_years=2,
    )

    model_names = {row.model_name for row in result.predictions}
    assert model_names == {
        "prior_year_incidence",
        "county_trailing_mean_incidence",
        "state_trend_adjusted_county_mean",
        "linear_blend_baseline",
    }
    adjusted = next(
        row
        for row in result.predictions
        if row.model_name == "state_trend_adjusted_county_mean"
        and row.county_fips == "24001"
        and row.test_year == 2020
    )
    assert adjusted.predicted_incidence_per_100k == 14.285714


def test_run_baseline_backtests_bounds_end_year(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    assert {row.test_year for row in result.predictions} == {2020, 2021}
    assert result.run.end_year == 2021


def test_prior_year_baseline_requires_exact_prior_year(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix_with_gap(tmp_path / "features.csv")

    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        min_train_years=2,
        lookback_years=3,
    )

    model_names = {
        row.model_name
        for row in result.predictions
        if row.county_fips == "24001" and row.test_year == 2020
    }
    assert model_names == {
        "county_trailing_mean_incidence",
        "state_trend_adjusted_county_mean",
    }


def test_write_model_backtest_outputs_orders_and_dedupes(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")
    result = run_baseline_backtests(
        model_features_path=feature_matrix,
        start_year=2020,
        min_train_years=2,
        lookback_years=2,
    )

    outputs = write_model_backtest_outputs(result, tmp_path / "out")
    second_outputs = write_model_backtest_outputs(result, tmp_path / "out", append=True)

    assert second_outputs == outputs
    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        runs = list(csv.DictReader(handle))
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        predictions = list(csv.DictReader(handle))
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        metrics = list(csv.DictReader(handle))

    assert list(runs[0]) == MODEL_BACKTEST_RUN_COLUMNS
    assert list(predictions[0]) == MODEL_BACKTEST_PREDICTION_COLUMNS
    assert list(metrics[0]) == MODEL_BACKTEST_METRIC_COLUMNS
    assert len(runs) == 1
    assert len(predictions) == len(result.predictions)
    assert len(metrics) == len(result.metrics)
    assert predictions[0]["county_fips"] == "24001"


def _write_feature_matrix(path: Path) -> Path:
    rows = []
    values = {
        "24001": {
            2018: (10, 100000),
            2019: (20, 100000),
            2020: (30, 100000),
            2021: (40, 100000),
            2022: (50, 100000),
        },
        "24003": {
            2018: (100, 100000),
            2019: (80, 100000),
            2020: (60, 100000),
            2021: (40, 100000),
            2022: (20, 100000),
        },
    }
    for county_fips, yearly in values.items():
        for year, (cases, population) in yearly.items():
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(year),
                    "total_cases": str(cases),
                    "population": str(population),
                    "lyme_incidence_per_100k": str(cases / population * 100000),
                    "model_feature_quality_flags": "",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_feature_matrix_with_gap(path: Path) -> Path:
    rows = []
    values = {
        "24001": {
            2017: (10, 100000),
            2018: (20, 100000),
            2020: (30, 100000),
        },
        "24003": {
            2017: (100, 100000),
            2018: (80, 100000),
            2019: (60, 100000),
            2020: (40, 100000),
        },
    }
    for county_fips, yearly in values.items():
        for year, (cases, population) in yearly.items():
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(year),
                    "total_cases": str(cases),
                    "population": str(population),
                    "lyme_incidence_per_100k": str(cases / population * 100000),
                    "model_feature_quality_flags": "",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
