import csv
from pathlib import Path

from tests.test_model_diagnostics import _prediction_row, _write_rows
import pytest

from tickbiterisk.modeling.forecast_calibration_backtest import (
    ForecastCalibrationBacktestInputError,
    build_forecast_calibration_backtest,
)
from tickbiterisk.modeling.forecast_calibration_backtest_build import (
    FORECAST_CALIBRATION_BACKTEST_METRIC_COLUMNS,
    FORECAST_CALIBRATION_BACKTEST_PREDICTION_COLUMNS,
    FORECAST_CALIBRATION_BACKTEST_RUN_COLUMNS,
    write_forecast_calibration_backtest_outputs,
)


def test_build_forecast_calibration_backtest_applies_prior_shrunken_ratio(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")

    result = build_forecast_calibration_backtest(
        predictions_path=predictions,
        start_year=2019,
        min_calibration_updates=2,
        calibration_prior_strength=2.0,
    )

    row = next(
        row
        for row in result.predictions
        if row.county_fips == "24001" and row.forecast_year == 2019
    )
    assert row.calibration_scope == "same_regime_prior_years"
    assert row.n_calibration_updates == 4
    assert row.raw_actual_to_predicted_case_ratio == 2.0
    assert row.shrunken_case_multiplier == 1.666667
    assert row.original_predicted_cases == 30.0
    assert row.calibrated_predicted_cases == 50.0
    assert row.actual_cases == 60
    assert row.original_absolute_error_cases == 30.0
    assert row.calibrated_absolute_error_cases == 10.0
    assert row.original_predicted_incidence_per_100k == 30.0
    assert row.calibrated_predicted_incidence_per_100k == 50.0
    assert row.actual_incidence_per_100k == 60.0
    assert row.calibrated_absolute_error_incidence_per_100k == 10.0

    overall = next(
        row
        for row in result.metrics
        if row.aggregation == "overall"
        and row.model_name == "linear_blend_baseline"
        and row.forecast_year is None
    )
    assert overall.n_predictions == 2
    assert overall.original_mae_incidence_per_100k == 30.0
    assert overall.calibrated_mae_incidence_per_100k == 10.0
    assert overall.mae_improvement_incidence_per_100k == 20.0
    assert overall.calibration_gate_decision == "candidate_review_required"
    assert overall.calibration_gate_reason == (
        "calibration improved overall held-out incidence and case MAE"
    )
    assert result.run.n_predictions == 2


def test_build_forecast_calibration_backtest_leaves_rows_uncalibrated_without_prior(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")

    result = build_forecast_calibration_backtest(
        predictions_path=predictions,
        start_year=2017,
        end_year=2017,
        min_calibration_updates=2,
    )

    assert {row.calibration_scope for row in result.predictions} == {
        "uncalibrated_insufficient_prior"
    }
    assert all(row.shrunken_case_multiplier == 1.0 for row in result.predictions)
    assert all(
        row.original_predicted_cases == row.calibrated_predicted_cases
        for row in result.predictions
    )


def test_build_forecast_calibration_backtest_rejects_worsening_overall_gate(
    tmp_path: Path,
) -> None:
    predictions = tmp_path / "predictions.csv"
    rows = []
    for year in (2017, 2018):
        rows.extend(
            [
                _prediction_row(
                    county_fips="24001",
                    county_name="County 24001",
                    test_year=year,
                    actual_cases=20,
                    predicted_cases=10,
                    actual_incidence=20.0,
                    predicted_incidence=10.0,
                    quality_flags="",
                ),
                _prediction_row(
                    county_fips="24003",
                    county_name="County 24003",
                    test_year=year,
                    actual_cases=40,
                    predicted_cases=20,
                    actual_incidence=40.0,
                    predicted_incidence=20.0,
                    quality_flags="",
                ),
            ]
        )
    rows.extend(
        [
            _prediction_row(
                county_fips="24001",
                county_name="County 24001",
                test_year=2019,
                actual_cases=30,
                predicted_cases=30,
                actual_incidence=30.0,
                predicted_incidence=30.0,
                quality_flags="",
            ),
            _prediction_row(
                county_fips="24003",
                county_name="County 24003",
                test_year=2019,
                actual_cases=30,
                predicted_cases=30,
                actual_incidence=30.0,
                predicted_incidence=30.0,
                quality_flags="",
            ),
        ]
    )
    _write_rows(predictions, rows)

    result = build_forecast_calibration_backtest(
        predictions_path=predictions,
        start_year=2019,
        min_calibration_updates=2,
        calibration_prior_strength=2.0,
    )

    overall = next(
        row
        for row in result.metrics
        if row.aggregation == "overall"
        and row.model_name == "linear_blend_baseline"
        and row.forecast_year is None
    )
    assert overall.original_mae_incidence_per_100k == 0.0
    assert overall.calibrated_mae_incidence_per_100k == 20.0
    assert overall.mae_improvement_incidence_per_100k == -20.0
    assert overall.calibration_gate_decision == "do_not_apply_to_public_forecast"
    assert overall.calibration_gate_reason == (
        "calibration did not improve overall held-out incidence and case MAE"
    )


def test_build_forecast_calibration_backtest_falls_back_when_same_regime_zero_prediction(
    tmp_path: Path,
) -> None:
    predictions = tmp_path / "predictions.csv"
    rows = [
        _prediction_row(
            county_fips="24001",
            county_name="County 24001",
            test_year=2017,
            actual_cases=10,
            predicted_cases=0,
            actual_incidence=10.0,
            predicted_incidence=0.0,
            quality_flags="lyme_case_definition_change",
        ),
        _prediction_row(
            county_fips="24003",
            county_name="County 24003",
            test_year=2018,
            actual_cases=10,
            predicted_cases=0,
            actual_incidence=10.0,
            predicted_incidence=0.0,
            quality_flags="lyme_case_definition_change",
        ),
        _prediction_row(
            county_fips="24001",
            county_name="County 24001",
            test_year=2017,
            actual_cases=20,
            predicted_cases=10,
            actual_incidence=20.0,
            predicted_incidence=10.0,
            quality_flags="",
        ),
        _prediction_row(
            county_fips="24003",
            county_name="County 24003",
            test_year=2018,
            actual_cases=40,
            predicted_cases=20,
            actual_incidence=40.0,
            predicted_incidence=20.0,
            quality_flags="",
        ),
        _prediction_row(
            county_fips="24005",
            county_name="County 24005",
            test_year=2022,
            actual_cases=60,
            predicted_cases=30,
            actual_incidence=60.0,
            predicted_incidence=30.0,
            quality_flags="lyme_case_definition_change",
        ),
    ]
    _write_rows(predictions, rows)

    result = build_forecast_calibration_backtest(
        predictions_path=predictions,
        start_year=2022,
        min_calibration_updates=2,
        calibration_prior_strength=2.0,
    )

    row = result.predictions[0]
    assert row.calibration_scope == "all_regime_prior_years"
    assert row.n_calibration_updates == 4
    assert row.raw_actual_to_predicted_case_ratio == 2.666667
    assert row.shrunken_case_multiplier == 2.111111

    subgroup = next(
        row
        for row in result.metrics
        if row.aggregation == "surveillance_regime"
        and row.surveillance_regime == "case_definition_change_2022_plus"
    )
    assert subgroup.calibration_gate_decision == "diagnostic_subgroup_only"
    assert subgroup.calibration_gate_reason == (
        "subgroup result is diagnostic evidence, not a standalone public update gate"
    )


def test_build_forecast_calibration_backtest_rejects_non_numeric_inputs(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")
    _replace_first_csv_value(predictions, "actual_incidence_per_100k", "abc")

    with pytest.raises(
        ForecastCalibrationBacktestInputError,
        match="invalid numeric value in actual_incidence_per_100k",
    ):
        build_forecast_calibration_backtest(predictions_path=predictions)


def test_build_forecast_calibration_backtest_rejects_non_finite_inputs(
    tmp_path: Path,
) -> None:
    predictions = _write_calibration_predictions(tmp_path / "predictions.csv")
    _replace_first_csv_value(predictions, "actual_incidence_per_100k", "nan")

    with pytest.raises(
        ForecastCalibrationBacktestInputError,
        match="non-finite numeric value in actual_incidence_per_100k",
    ):
        build_forecast_calibration_backtest(predictions_path=predictions)


def test_write_forecast_calibration_backtest_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_forecast_calibration_backtest(
        predictions_path=_write_calibration_predictions(tmp_path / "predictions.csv"),
        start_year=2019,
        min_calibration_updates=2,
    )

    outputs = write_forecast_calibration_backtest_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == FORECAST_CALIBRATION_BACKTEST_RUN_COLUMNS
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        assert (
            next(csv.reader(handle))
            == FORECAST_CALIBRATION_BACKTEST_PREDICTION_COLUMNS
        )
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == FORECAST_CALIBRATION_BACKTEST_METRIC_COLUMNS


def _write_calibration_predictions(path: Path) -> Path:
    rows = []
    for year in (2017, 2018):
        rows.extend(
            [
                _prediction_row(
                    county_fips="24001",
                    county_name="County 24001",
                    test_year=year,
                    actual_cases=20,
                    predicted_cases=10,
                    actual_incidence=20.0,
                    predicted_incidence=10.0,
                    quality_flags="",
                ),
                _prediction_row(
                    county_fips="24003",
                    county_name="County 24003",
                    test_year=year,
                    actual_cases=40,
                    predicted_cases=20,
                    actual_incidence=40.0,
                    predicted_incidence=20.0,
                    quality_flags="",
                ),
            ]
        )
    rows.extend(
        [
            _prediction_row(
                county_fips="24001",
                county_name="County 24001",
                test_year=2019,
                actual_cases=60,
                predicted_cases=30,
                actual_incidence=60.0,
                predicted_incidence=30.0,
                quality_flags="",
            ),
            _prediction_row(
                county_fips="24003",
                county_name="County 24003",
                test_year=2019,
                actual_cases=60,
                predicted_cases=30,
                actual_incidence=60.0,
                predicted_incidence=30.0,
                quality_flags="",
            ),
        ]
    )
    return _write_rows(path, rows)


def _replace_first_csv_value(path: Path, column: str, value: str) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][column] = value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
