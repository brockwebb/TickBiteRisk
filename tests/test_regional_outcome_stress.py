import csv
from pathlib import Path

from tickbiterisk.modeling.regional_outcome_stress import (
    build_regional_outcome_stress,
)
from tickbiterisk.modeling.regional_outcome_stress_build import (
    REGIONAL_OUTCOME_STRESS_METRIC_COLUMNS,
    REGIONAL_OUTCOME_STRESS_PREDICTION_COLUMNS,
    REGIONAL_OUTCOME_STRESS_RUN_COLUMNS,
    write_regional_outcome_stress_outputs,
)


def test_build_regional_outcome_stress_compares_capacity_share_baselines(
    tmp_path: Path,
) -> None:
    panel = _write_regional_panel(tmp_path / "regional.csv")

    result = build_regional_outcome_stress(
        regional_lyme_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    model_names = {row.model_name for row in result.predictions}
    assert model_names == {
        "midatlantic_capacity_share_cases",
        "prior_year_county_cases",
        "state_capacity_share_cases",
        "trailing_mean_county_cases",
    }
    state_capacity = next(
        row
        for row in result.predictions
        if row.model_name == "state_capacity_share_cases"
        and row.county_fips == "24001"
    )
    assert state_capacity.actual_cases == 40
    assert state_capacity.predicted_cases == 25.0
    assert state_capacity.residual_cases == 15.0
    assert state_capacity.train_start_year == 2019
    assert state_capacity.train_end_year == 2020
    assert state_capacity.evaluation_mode == "rolling_origin_prior_years"
    assert "reported_cases_not_stable_true_incidence" in (
        state_capacity.comparison_assumption_flags
    )

    overall_prior = next(
        row
        for row in result.metrics
        if row.model_name == "prior_year_county_cases"
        and row.aggregation == "overall"
        and row.test_year is None
    )
    assert overall_prior.n_predictions == 4
    assert overall_prior.mae_cases == 10.0
    assert overall_prior.rmse_cases == 10.0
    assert result.run.n_predictions == len(result.predictions)


def test_write_regional_outcome_stress_outputs_writes_expected_columns(
    tmp_path: Path,
) -> None:
    result = build_regional_outcome_stress(
        regional_lyme_path=_write_regional_panel(tmp_path / "regional.csv"),
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    outputs = write_regional_outcome_stress_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_OUTCOME_STRESS_RUN_COLUMNS
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_OUTCOME_STRESS_PREDICTION_COLUMNS
    with outputs.metrics_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_OUTCOME_STRESS_METRIC_COLUMNS


def _write_regional_panel(path: Path) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [10, 20, 30, 40],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [30, 20, 10, 0],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [5, 10, 20, 30],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [15, 10, 0, 10],
    }
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, cases in enumerate(values):
            year = 2018 + offset
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(cases),
                    "source_id": "fixture",
                    "feature_quality_flags": (
                        "regional_expansion_stress_test,"
                        "reported_cases_not_stable_true_incidence"
                    ),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
