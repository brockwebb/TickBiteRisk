import csv
import math
from pathlib import Path

from tickbiterisk.modeling import model_compare
from tickbiterisk.modeling.model_compare import run_model_comparison
from tickbiterisk.modeling.model_compare_build import (
    MODEL_COMPARISON_METRIC_COLUMNS,
    MODEL_COMPARISON_PREDICTION_COLUMNS,
    MODEL_COMPARISON_RUN_COLUMNS,
    MODEL_COMPARISON_SUMMARY_COLUMNS,
    write_model_comparison_outputs,
)


def test_run_model_comparison_uses_prior_year_training_windows(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")

    result = run_model_comparison(
        design_matrix_path=matrix,
        start_year=2021,
        min_train_years=1,
        ridge_alpha=1.0,
        shrinkage_strength=3.0,
    )

    model_names = {row.model_name for row in result.predictions}
    assert model_names == {
        "empirical_bayes_shrinkage",
        "linear_blend_baseline",
        "prior_year_incidence",
        "ridge_forecast_ecology",
        "ridge_forecast_safe",
        "ridge_lag_weather_ecology",
        "trailing_mean_incidence",
    }
    prior = next(
        row
        for row in result.predictions
        if row.model_name == "prior_year_incidence"
        and row.county_fips == "24001"
        and row.test_year == 2021
    )
    assert prior.predicted_incidence_per_100k == 20.0
    assert prior.actual_incidence_per_100k == 30.0
    assert prior.train_start_year == 2019
    assert prior.train_end_year == 2020
    assert prior.train_row_count == 4
    assert prior.train_county_count == 2
    assert prior.evaluation_mode == "rolling_origin_prior_years"
    assert prior.weather_mode == "not_used_by_lagged_model"
    assert len(prior.source_file_sha256) == 64
    assert "observational_not_causal" in prior.comparison_assumption_flags
    assert result.run.weather_mode == "mixed_model_specific"


def test_run_model_comparison_includes_empirical_bayes_and_metrics(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")

    result = run_model_comparison(
        design_matrix_path=matrix,
        start_year=2021,
        min_train_years=1,
        shrinkage_strength=3.0,
    )

    bayes = next(
        row
        for row in result.predictions
        if row.model_name == "empirical_bayes_shrinkage"
        and row.county_fips == "24001"
        and row.test_year == 2021
    )
    assert bayes.model_family == "empirical_bayes"
    assert bayes.predicted_incidence_per_100k == 37.5
    assert bayes.feature_profile == "lagged_outcome_with_shrinkage"
    blend = next(
        row
        for row in result.predictions
        if row.model_name == "linear_blend_baseline"
        and row.county_fips == "24001"
        and row.test_year == 2021
    )
    assert blend.predicted_incidence_per_100k == 17.5
    assert blend.model_family == "ensemble"

    ridge = next(
        row for row in result.predictions if row.model_name == "ridge_lag_weather_ecology"
    )
    assert ridge.model_family == "regularized_linear"
    assert ridge.feature_profile == "retrospective_weather_ecology"
    assert ridge.predicted_incidence_per_100k >= 0
    forecast_ridge = next(
        row for row in result.predictions if row.model_name == "ridge_forecast_safe"
    )
    assert forecast_ridge.model_family == "regularized_linear"
    assert forecast_ridge.feature_profile == "forecast_safe_lagged"
    assert forecast_ridge.weather_mode == "not_used_by_forecast_safe_model"
    ecology_ridge = next(
        row for row in result.predictions if row.model_name == "ridge_forecast_ecology"
    )
    assert ecology_ridge.model_family == "regularized_linear"
    assert ecology_ridge.feature_profile == "forecast_safe_lagged_ecology"
    assert ecology_ridge.weather_mode == "not_used_by_forecast_safe_model"

    overall = next(
        row
        for row in result.metrics
        if row.model_name == "prior_year_incidence"
        and row.aggregation == "overall"
    )
    assert overall.n_predictions == 4
    assert overall.mae_incidence_per_100k == 15.0
    assert overall.rmse_incidence_per_100k == round(math.sqrt(250), 6)
    assert overall.pearson_correlation == 0.889824
    assert result.summary[0].rank_by_mae == 1
    assert result.run.n_predictions == len(result.predictions)


def test_forecast_profile_feature_selectors_avoid_same_year_leakage() -> None:
    assert model_compare._is_forecast_safe_feature_column(
        "feature_trailing_3yr_mean_lyme_incidence_per_100k"
    )
    assert model_compare._is_forecast_safe_feature_column(
        "feature_trailing_10yr_mean_lyme_incidence_per_100k"
    )
    assert not model_compare._is_forecast_safe_feature_column(
        "feature_weather_temp_mean_f"
    )
    assert not model_compare._is_forecast_ecology_feature_column(
        "feature_units_authorized_per_sqmi"
    )
    assert not model_compare._is_forecast_ecology_feature_column(
        "feature_contact_pressure_total_value_dollars"
    )
    assert model_compare._is_forecast_ecology_feature_column(
        "feature_deer_harvest_per_sqmi_prior_season"
    )
    assert model_compare._is_forecast_ecology_feature_column(
        "feature_missing_deer_harvest_prior_season"
    )
    assert not model_compare._is_forecast_safe_feature_column(
        "feature_mast_index_prior_year"
    )
    assert model_compare._is_forecast_ecology_feature_column(
        "feature_mast_index_prior_year"
    )
    assert model_compare._is_forecast_ecology_feature_column(
        "feature_black_oak_acorns_per_branch_prior_year"
    )
    assert model_compare._is_forecast_ecology_feature_column(
        "feature_missing_mast_index_prior_year"
    )
    assert not model_compare._is_safe_feature_column(
        "feature_flag_western_maryland_only"
    )
    assert not model_compare._is_safe_feature_column(
        "feature_flag_study_plot_not_countywide"
    )


def test_write_model_comparison_outputs_orders_and_dedupes(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    result = run_model_comparison(
        design_matrix_path=matrix,
        start_year=2021,
        min_train_years=1,
    )

    outputs = write_model_comparison_outputs(result, tmp_path / "out")
    second_outputs = write_model_comparison_outputs(result, tmp_path / "out", append=True)

    assert second_outputs == outputs
    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        runs = list(csv.DictReader(handle))
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        predictions = list(csv.DictReader(handle))
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        metrics = list(csv.DictReader(handle))
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))

    assert list(runs[0]) == MODEL_COMPARISON_RUN_COLUMNS
    assert list(predictions[0]) == MODEL_COMPARISON_PREDICTION_COLUMNS
    assert list(metrics[0]) == MODEL_COMPARISON_METRIC_COLUMNS
    assert list(summary[0]) == MODEL_COMPARISON_SUMMARY_COLUMNS
    assert len(runs) == 1
    assert len(predictions) == len(result.predictions)
    assert len(metrics) == len(result.metrics)
    assert len(summary) == len(result.summary)
    assert summary[0]["rank_by_mae"] == "1"


def _write_design_matrix(path: Path) -> Path:
    rows = []
    values = {
        "24001": [10, 20, 30, 40],
        "24003": [100, 80, 60, 40],
    }
    for county_fips, cases_by_year in values.items():
        county_name = f"County {county_fips}"
        for offset, cases in enumerate(cases_by_year):
            year = 2019 + offset
            prior_cases = cases_by_year[offset - 1] if offset else 0
            history = cases_by_year[:offset]
            trailing = sum(history[-2:]) / len(history[-2:]) if history else 0
            state_prior = _state_prior(values, offset)
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "target_total_cases": str(cases),
                    "target_lyme_incidence_per_100k": str(float(cases)),
                    "target_population": "100000",
                    "feature_year": str(year),
                    "feature_prior_year_lyme_incidence_per_100k": str(float(prior_cases)),
                    "feature_trailing_2yr_mean_lyme_incidence_per_100k": str(float(trailing)),
                    "feature_trailing_history_years": str(offset),
                    "feature_missing_prior_year_lyme_incidence": "1" if offset == 0 else "0",
                    "feature_state_prior_year_lyme_incidence_per_100k": str(float(state_prior)),
                    "feature_missing_state_prior_year_lyme_incidence": "1" if offset == 0 else "0",
                    "feature_weather_temp_mean_f": str(50 + cases / 10),
                    "feature_weather_precip_total_mm": str(900 + cases),
                    "feature_deer_harvest_per_sqmi_prior_season": str(cases / 20),
                    "feature_missing_deer_harvest_prior_season": "0",
                    "feature_flag_current_status_retrospective_proxy": "1",
                    "model_feature_quality_flags": "current_status_retrospective_proxy",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _state_prior(values: dict[str, list[int]], offset: int) -> float:
    if offset == 0:
        return 0.0
    return sum(series[offset - 1] for series in values.values()) / len(values)
