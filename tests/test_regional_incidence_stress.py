import csv
from pathlib import Path

from tickbiterisk.modeling.regional_incidence_stress import (
    build_regional_incidence_stress,
)
from tickbiterisk.modeling.regional_incidence_stress_build import (
    REGIONAL_INCIDENCE_STRESS_METRIC_COLUMNS,
    REGIONAL_INCIDENCE_STRESS_PREDICTION_COLUMNS,
    REGIONAL_INCIDENCE_STRESS_RUN_COLUMNS,
    write_regional_incidence_stress_outputs,
)


def test_build_regional_incidence_stress_compares_shrinkage_baselines(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")

    result = build_regional_incidence_stress(
        regional_incidence_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
        shrinkage_strength=2.0,
        random_forest_n_estimators=5,
    )

    model_names = {row.model_name for row in result.predictions}
    assert model_names == {
        "analog_year_county_incidence",
        "empirical_bayes_midatlantic_incidence",
        "empirical_bayes_state_incidence",
        "prior_year_county_incidence",
        "random_forest_regional_incidence",
        "trailing_mean_county_incidence",
    }
    eb_state = next(
        row
        for row in result.predictions
        if row.model_name == "empirical_bayes_state_incidence"
        and row.county_fips == "24001"
    )
    assert eb_state.actual_incidence_per_100k == 40.0
    assert eb_state.predicted_incidence_per_100k == 22.5
    assert eb_state.residual_incidence_per_100k == 17.5
    assert eb_state.train_start_year == 2019
    assert eb_state.train_end_year == 2020
    assert eb_state.train_year_count == 2
    assert eb_state.evaluation_mode == "rolling_origin_prior_years"
    assert "reported_cases_not_stable_true_incidence" in (
        eb_state.comparison_assumption_flags
    )
    assert result.run.shrinkage_strength == 2.0
    assert result.run.random_forest_n_estimators == 5
    assert result.run.random_forest_min_samples_leaf == 3
    assert result.run.random_forest_max_features == "sqrt"
    assert result.run.random_forest_random_state == 1337

    random_forest = next(
        row
        for row in result.predictions
        if row.model_name == "random_forest_regional_incidence"
        and row.county_fips == "24001"
    )
    assert random_forest.model_family == "random_forest_incidence"
    assert random_forest.predicted_incidence_per_100k >= 0
    assert random_forest.train_start_year == 2020
    assert random_forest.train_end_year == 2020
    assert random_forest.train_end_year < random_forest.test_year
    assert "random_forest_regional_research" in (
        random_forest.model_feature_quality_flags
    )
    assert "forecast_safe_prior_outcomes_only" in (
        random_forest.model_feature_quality_flags
    )

    overall_prior = next(
        row
        for row in result.metrics
        if row.model_name == "prior_year_county_incidence"
        and row.aggregation == "overall"
        and row.test_year is None
    )
    assert overall_prior.n_predictions == 4
    assert overall_prior.mae_incidence_per_100k == 10.0
    assert overall_prior.rmse_incidence_per_100k == 10.0
    assert result.run.n_predictions == len(result.predictions)


def test_regional_incidence_stress_analog_uses_only_prior_known_outcomes(
    tmp_path: Path,
) -> None:
    panel = _write_single_county_incidence_panel(
        tmp_path / "incidence.csv",
        [5, 15, 50, 999],
    )

    result = build_regional_incidence_stress(
        regional_incidence_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    analog = next(
        row
        for row in result.predictions
        if row.model_name == "analog_year_county_incidence"
    )
    assert analog.model_family == "analog"
    assert analog.actual_incidence_per_100k == 999.0
    assert analog.predicted_incidence_per_100k == 50.0
    assert analog.analog_match_origin_year == 2019
    assert analog.analog_match_observed_year == 2020
    assert analog.analog_match_observed_year < analog.test_year
    assert "analog_like_year_hindcast" in analog.model_feature_quality_flags
    assert "forecast_safe_prior_outcomes_only" in (
        analog.model_feature_quality_flags
    )


def test_build_regional_incidence_stress_skips_missing_target_incidence(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv", missing_target=True)

    result = build_regional_incidence_stress(
        regional_incidence_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    assert all(row.county_fips != "42003" for row in result.predictions)


def test_write_regional_incidence_stress_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_incidence_stress(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    outputs = write_regional_incidence_stress_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_STRESS_RUN_COLUMNS
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_STRESS_PREDICTION_COLUMNS
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_STRESS_METRIC_COLUMNS


def _write_single_county_incidence_panel(path: Path, values: list[int]) -> Path:
    rows = []
    for offset, incidence in enumerate(values):
        year = 2018 + offset
        rows.append(
            {
                "state_fips": "24",
                "state_abbr": "MD",
                "state_name": "Maryland",
                "county_fips": "24001",
                "county_name": "Allegany County",
                "year": str(year),
                "total_cases": str(incidence),
                "population": "100000",
                "incidence_per_100k": str(incidence),
                "diagnostic_midatlantic_incidence_rank": "",
                "diagnostic_midatlantic_incidence_percentile": "",
                "diagnostic_midatlantic_incidence_tier": "",
                "diagnostic_prior_year_midatlantic_incidence_rank": "",
                "diagnostic_midatlantic_incidence_rank_change": "",
                "lyme_panel_sha256": "lyme123",
                "population_panel_sha256": "pop123",
                "feature_quality_flags": (
                    "regional_incidence_diagnostic,"
                    "reported_cases_not_stable_true_incidence"
                ),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_incidence_panel(path: Path, *, missing_target: bool = False) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [10, 20, 30, 40],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [30, 20, 10, 0],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [5, 10, 20, 30],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [15, 10, 0, 10],
    }
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, incidence in enumerate(values):
            year = 2018 + offset
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(incidence),
                    "population": "100000",
                    "incidence_per_100k": (
                        ""
                        if missing_target and county_fips == "42003" and year == 2021
                        else str(incidence)
                    ),
                    "diagnostic_midatlantic_incidence_rank": "",
                    "diagnostic_midatlantic_incidence_percentile": "",
                    "diagnostic_midatlantic_incidence_tier": "",
                    "diagnostic_prior_year_midatlantic_incidence_rank": "",
                    "diagnostic_midatlantic_incidence_rank_change": "",
                    "lyme_panel_sha256": "lyme123",
                    "population_panel_sha256": "pop123",
                    "feature_quality_flags": (
                        "regional_incidence_diagnostic,"
                        "reported_cases_not_stable_true_incidence"
                    ),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
