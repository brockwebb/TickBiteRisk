import csv
from pathlib import Path

from tickbiterisk.modeling.regional_forecast_capacity import (
    build_regional_forecast_capacity,
)
from tickbiterisk.modeling.regional_forecast_capacity_build import (
    REGIONAL_FORECAST_CAPACITY_RUN_COLUMNS,
    REGIONAL_FORECAST_CAPACITY_SUMMARY_COLUMNS,
    write_regional_forecast_capacity_outputs,
)


def test_build_regional_forecast_capacity_compares_forecast_to_history(
    tmp_path: Path,
) -> None:
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")

    result = build_regional_forecast_capacity(
        regional_incidence_path=incidence,
        forecast_predictions_path=forecast,
    )

    assert result.run.forecast_year == 2023
    assert result.run.forecast_origin_year == 2021
    assert result.run.history_start_year == 2019
    assert result.run.history_end_year == 2021
    assert result.run.model_names == "analog_year_county_incidence"
    assert result.run.n_capacity_rows == 2

    state = next(
        row
        for row in result.capacity_summary
        if row.geography_level == "state" and row.region_id == "state_24"
    )
    assert state.model_name == "analog_year_county_incidence"
    assert state.model_family == "analog"
    assert state.feature_profile == "forecast_safe_horizon_matched_analog"
    assert state.n_counties == 2
    assert state.history_year_count == 3
    assert state.forecast_total_cases == 80.0
    assert state.forecast_population == 200000
    assert state.forecast_incidence_per_100k == 40.0
    assert state.history_min_cases == 30.0
    assert state.history_mean_cases == 50.0
    assert state.history_max_cases == 70.0
    assert state.history_mean_incidence_per_100k == 25.0
    assert state.forecast_case_percentile_of_history == 1.0
    assert state.forecast_incidence_percentile_of_history == 1.0
    assert state.above_history_max_cases is True
    assert state.below_history_min_cases is False
    assert "forecast_capacity_control_limit" in state.capacity_assumption_flags
    assert "reported_cases_not_stable_true_incidence" in (
        state.capacity_assumption_flags
    )

    regional = next(
        row for row in result.capacity_summary if row.geography_level == "regional"
    )
    assert regional.region_id == "midatlantic"
    assert regional.region_name == "Mid-Atlantic"
    assert regional.forecast_total_cases == 80.0


def test_regional_forecast_capacity_excludes_future_history_rows(
    tmp_path: Path,
) -> None:
    incidence = _write_incidence_panel(tmp_path / "incidence.csv", include_future=True)
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")

    result = build_regional_forecast_capacity(
        regional_incidence_path=incidence,
        forecast_predictions_path=forecast,
    )

    state = next(
        row
        for row in result.capacity_summary
        if row.geography_level == "state" and row.region_id == "state_24"
    )
    assert state.history_end_year == 2021
    assert state.history_max_cases == 70.0
    assert state.forecast_total_cases != 999.0


def test_write_regional_forecast_capacity_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_forecast_capacity(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        forecast_predictions_path=_write_forecast_predictions(tmp_path / "forecast.csv"),
    )

    outputs = write_regional_forecast_capacity_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_FORECAST_CAPACITY_RUN_COLUMNS
    with outputs.capacity_summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_FORECAST_CAPACITY_SUMMARY_COLUMNS


def _write_incidence_panel(path: Path, *, include_future: bool = False) -> Path:
    rows = []
    series = {
        "24001": [10, 20, 30],
        "24003": [20, 30, 40],
    }
    for county_fips, values in series.items():
        for offset, cases in enumerate(values):
            rows.append(
                {
                    "state_fips": "24",
                    "state_abbr": "MD",
                    "state_name": "Maryland",
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(2019 + offset),
                    "total_cases": str(cases),
                    "population": "100000",
                    "incidence_per_100k": str(float(cases)),
                    "feature_quality_flags": (
                        "regional_incidence_diagnostic,"
                        "reported_cases_not_stable_true_incidence"
                    ),
                }
            )
    if include_future:
        for county_fips in series:
            rows.append(
                {
                    "state_fips": "24",
                    "state_abbr": "MD",
                    "state_name": "Maryland",
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": "2022",
                    "total_cases": "999",
                    "population": "100000",
                    "incidence_per_100k": "999.0",
                    "feature_quality_flags": "future_row_should_be_excluded",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_forecast_predictions(path: Path) -> Path:
    rows = []
    for county_fips, cases in [("24001", 35), ("24003", 45)]:
        rows.append(
            {
                "run_id": "regional-forecast-run",
                "model_name": "analog_year_county_incidence",
                "model_family": "analog",
                "target_definition": "reported_lyme_incidence_per_100k",
                "feature_set": "historical_incidence_forecast_baselines",
                "feature_profile": "forecast_safe_horizon_matched_analog",
                "evaluation_mode": "regional_annual_forecast_no_observed_target",
                "regional_incidence_sha256": "inc123",
                "regional_population_sha256": "pop123",
                "state_fips": "24",
                "state_abbr": "MD",
                "state_name": "Maryland",
                "county_fips": county_fips,
                "county_name": f"County {county_fips}",
                "forecast_year": "2023",
                "forecast_origin_year": "2021",
                "as_of_date": "2026-05-29",
                "data_cutoff_date": "2021-12-31",
                "source_vintage": "fixture",
                "update_mode": "pre_update",
                "forecast_horizon_years": "2",
                "train_start_year": "2019",
                "train_end_year": "2021",
                "train_year_count": "3",
                "forecast_population": "100000",
                "population_source_id": "fixture_projection",
                "population_vintage": "2025",
                "population_feature_quality_flags": "forecast_denominator",
                "predicted_cases": str(cases),
                "predicted_incidence_per_100k": str(float(cases)),
                "analog_match_origin_year": "2019",
                "analog_match_observed_year": "2021",
                "analog_match_distance": "0.0",
                "model_feature_quality_flags": "analog_like_year_forecast",
                "forecast_assumption_flags": (
                    "forecast_without_observed_target,"
                    "reported_cases_not_stable_true_incidence"
                ),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
