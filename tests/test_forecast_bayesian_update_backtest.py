import csv
from pathlib import Path

import pytest

from tests.test_forecast_calibration_backtest import (
    _replace_first_csv_value,
    _write_calibration_predictions,
)

from tickbiterisk.modeling.forecast_bayesian_update_backtest import (
    ForecastBayesianUpdateBacktestInputError,
    build_forecast_bayesian_update_backtest,
)
from tickbiterisk.modeling.forecast_bayesian_update_backtest_build import (
    FORECAST_BAYESIAN_UPDATE_BACKTEST_METRIC_COLUMNS,
    FORECAST_BAYESIAN_UPDATE_BACKTEST_PREDICTION_COLUMNS,
    FORECAST_BAYESIAN_UPDATE_BACKTEST_RUN_COLUMNS,
    write_forecast_bayesian_update_backtest_outputs,
)


def test_build_forecast_bayesian_update_backtest_applies_gamma_poisson_posterior(
    tmp_path: Path,
) -> None:
    result = build_forecast_bayesian_update_backtest(
        predictions_path=_write_calibration_predictions(tmp_path / "predictions.csv"),
        start_year=2019,
        min_prior_updates=2,
        prior_strength_cases=10.0,
    )

    row = next(
        row
        for row in result.predictions
        if row.county_fips == "24001" and row.forecast_year == 2019
    )
    assert row.update_scope == "same_regime_prior_years"
    assert row.n_prior_updates == 4
    assert row.prior_actual_cases == 120
    assert row.prior_predicted_cases == 60.0
    assert row.posterior_alpha == 130.0
    assert row.posterior_beta == 70.0
    assert row.posterior_case_multiplier_mean == 1.857143
    assert row.original_predicted_cases == 30.0
    assert row.updated_predicted_cases == 55.714286
    assert row.actual_cases == 60
    assert row.original_absolute_error_cases == 30.0
    assert row.updated_absolute_error_cases == 4.285714
    assert row.lower_80_updated_cases < row.updated_predicted_cases
    assert row.upper_80_updated_cases > row.updated_predicted_cases
    assert row.covered_80 is True
    assert row.covered_95 is True
    assert "gamma_poisson_bayesian_update_backtest" in row.comparison_assumption_flags
    assert "not_public_default" in row.comparison_assumption_flags

    overall = next(
        row
        for row in result.metrics
        if row.aggregation == "overall"
        and row.model_name == "linear_blend_baseline"
        and row.forecast_year is None
    )
    assert overall.n_predictions == 2
    assert overall.original_mae_cases == 30.0
    assert overall.updated_mae_cases == 4.285714
    assert overall.mae_improvement_cases == 25.714286
    assert overall.coverage_80_count == 2
    assert overall.update_gate_decision == "candidate_review_required"
    assert result.run.bayes_update_method == "gamma_poisson_case_multiplier"


def test_build_forecast_bayesian_update_backtest_leaves_rows_at_prior_without_history(
    tmp_path: Path,
) -> None:
    result = build_forecast_bayesian_update_backtest(
        predictions_path=_write_calibration_predictions(tmp_path / "predictions.csv"),
        start_year=2017,
        end_year=2017,
        min_prior_updates=2,
        prior_strength_cases=10.0,
    )

    assert {row.update_scope for row in result.predictions} == {
        "prior_only_insufficient_updates"
    }
    assert all(row.posterior_case_multiplier_mean == 1.0 for row in result.predictions)
    assert all(
        row.original_predicted_cases == row.updated_predicted_cases
        for row in result.predictions
    )


def test_build_forecast_bayesian_update_backtest_rejects_bad_prior_strength(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ForecastBayesianUpdateBacktestInputError,
        match="prior_strength_cases",
    ):
        build_forecast_bayesian_update_backtest(
            predictions_path=_write_calibration_predictions(
                tmp_path / "predictions.csv"
            ),
            prior_strength_cases=0,
        )


def test_build_forecast_bayesian_update_backtest_rejects_negative_case_exposure(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")
    _replace_first_csv_value(predictions, "predicted_cases", "-1")

    with pytest.raises(
        ForecastBayesianUpdateBacktestInputError,
        match="predicted_cases must be non-negative",
    ):
        build_forecast_bayesian_update_backtest(
            predictions_path=predictions,
            start_year=2017,
        )


def test_write_forecast_bayesian_update_backtest_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_forecast_bayesian_update_backtest(
        predictions_path=_write_calibration_predictions(tmp_path / "predictions.csv"),
        start_year=2019,
        min_prior_updates=2,
    )

    outputs = write_forecast_bayesian_update_backtest_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == FORECAST_BAYESIAN_UPDATE_BACKTEST_RUN_COLUMNS
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        assert (
            next(csv.reader(handle))
            == FORECAST_BAYESIAN_UPDATE_BACKTEST_PREDICTION_COLUMNS
        )
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == FORECAST_BAYESIAN_UPDATE_BACKTEST_METRIC_COLUMNS
