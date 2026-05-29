import csv
from pathlib import Path
from statistics import mean

import pytest

from tickbiterisk.modeling import annual_forecast
from tickbiterisk.modeling.annual_forecast import (
    AnnualForecastInputError,
    build_annual_forecast,
)
from tickbiterisk.modeling.annual_forecast_build import (
    ANNUAL_FORECAST_PREDICTION_COLUMNS,
    ANNUAL_FORECAST_RUN_COLUMNS,
    write_annual_forecast_outputs,
)


def test_build_annual_forecast_emits_target_year_rows_without_actuals(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")

    result = build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
        shrinkage_strength=3.0,
        as_of_date="2026-05-28",
        data_cutoff_date="2024-12-31",
        source_vintage="mdh_2024_reviewed_v1",
        update_mode="pre_update",
    )

    assert result.run.target_year == 2026
    assert result.run.forecast_origin_year == 2024
    assert result.run.as_of_date == "2026-05-28"
    assert result.run.data_cutoff_date == "2024-12-31"
    assert result.run.source_vintage == "mdh_2024_reviewed_v1"
    assert result.run.update_mode == "pre_update"
    assert result.run.ridge_alpha == 1.0
    assert result.run.n_forecast_rows == 12
    assert "forecast_without_observed_target" in result.run.forecast_assumption_flags
    assert {row.model_name for row in result.predictions} == {
        "empirical_bayes_shrinkage",
        "analog_year_forecast",
        "latest_observed_incidence",
        "linear_blend_baseline",
        "ridge_forecast_safe",
        "trailing_mean_incidence",
    }

    latest = next(
        row
        for row in result.predictions
        if row.model_name == "latest_observed_incidence"
        and row.county_fips == "24001"
    )
    assert latest.forecast_year == 2026
    assert latest.forecast_origin_year == 2024
    assert latest.as_of_date == "2026-05-28"
    assert latest.data_cutoff_date == "2024-12-31"
    assert latest.source_vintage == "mdh_2024_reviewed_v1"
    assert latest.update_mode == "pre_update"
    assert latest.forecast_horizon_years == 2
    assert latest.forecast_population == 110000
    assert latest.population_source_id == "regional_population_linear_projection"
    assert latest.predicted_incidence_per_100k == 40.0
    assert latest.predicted_cases == 44.0
    assert latest.train_start_year == 2021
    assert latest.train_end_year == 2024
    assert latest.train_county_count == 2
    assert "no_official_2026_census_denominator" in latest.forecast_assumption_flags
    assert "retrospective_weather_reconstruction" not in latest.forecast_assumption_flags
    assert "drought_monitor_retro_observed" not in latest.forecast_assumption_flags
    assert "mdh_probable_only_2024" in latest.forecast_assumption_flags
    assert "drought_monitor_retro_observed" in latest.model_feature_quality_flags
    assert "not_weather_adjusted" in latest.forecast_assumption_flags
    assert "actual_cases" not in ANNUAL_FORECAST_PREDICTION_COLUMNS
    assert "residual_cases" not in ANNUAL_FORECAST_PREDICTION_COLUMNS

    blend = next(
        row
        for row in result.predictions
        if row.model_name == "linear_blend_baseline"
        and row.county_fips == "24001"
    )
    assert blend.predicted_incidence_per_100k == 32.5
    assert blend.feature_profile == "latest_observed_trailing_blend"

    analog = next(
        row
        for row in result.predictions
        if row.model_name == "analog_year_forecast"
        and row.county_fips == "24001"
    )
    assert analog.model_family == "analog"
    assert analog.feature_profile == "forecast_safe_analog_years"
    assert analog.weather_mode == "not_used_by_forecast_safe_model"
    assert analog.predicted_incidence_per_100k >= 0.0

    ridge = next(
        row
        for row in result.predictions
        if row.model_name == "ridge_forecast_safe"
        and row.county_fips == "24001"
    )
    assert ridge.model_family == "regularized_linear"
    assert ridge.feature_profile == "forecast_safe_lagged"
    assert ridge.weather_mode == "not_used_by_forecast_safe_model"


def test_build_annual_forecast_requires_future_target_year(tmp_path: Path) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")

    with pytest.raises(AnnualForecastInputError, match="target-year must be greater"):
        build_annual_forecast(
            design_matrix_path=matrix,
            population_path=population,
            target_year=2024,
            forecast_origin_year=2024,
        )


def test_build_annual_forecast_rejects_unknown_update_mode(tmp_path: Path) -> None:
    with pytest.raises(AnnualForecastInputError, match="update_mode"):
        build_annual_forecast(
            design_matrix_path=_write_design_matrix(tmp_path / "design_matrix.csv"),
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2026,
            forecast_origin_year=2024,
            min_train_years=2,
            update_mode="post_update",
        )


def test_build_annual_forecast_requires_county_depth_and_origin_row(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(
        tmp_path / "design_matrix.csv",
        sparse_county=True,
        stale_county=True,
    )
    population = _write_population(
        tmp_path / "population.csv",
        extra_counties=["24005", "24009"],
    )

    result = build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    assert {row.county_fips for row in result.predictions} == {"24001", "24003"}
    assert result.run.n_forecast_counties == 2
    assert result.run.n_forecast_rows == 12


def test_build_annual_forecast_uses_target_year_safe_ridge_features(
    tmp_path: Path,
    monkeypatch,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")
    captured_rows = []

    def capturing_ridge_prediction(
        *,
        row,
        train_rows,
        feature_columns,
        ridge_alpha,
        ridge_cache,
    ):
        captured_rows.append((row.county_fips, dict(row.features), tuple(feature_columns)))
        return 12.345678

    monkeypatch.setattr(
        annual_forecast,
        "_ridge_prediction",
        capturing_ridge_prediction,
    )

    result = build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
        ridge_alpha=2.5,
    )

    ridge = next(
        row
        for row in result.predictions
        if row.model_name == "ridge_forecast_safe"
        and row.county_fips == "24001"
    )
    county_fips, features, columns = next(
        capture for capture in captured_rows if capture[0] == "24001"
    )

    assert county_fips == "24001"
    assert ridge.predicted_incidence_per_100k == 12.345678
    assert result.run.ridge_alpha == 2.5
    assert "feature_year" in columns
    assert features["feature_year"] == 2026.0
    assert features["feature_prior_year_lyme_incidence_per_100k"] == 40.0
    assert features["feature_trailing_history_years"] == 4.0
    assert features["feature_trailing_5yr_mean_lyme_incidence_per_100k"] == 25.0
    assert features["feature_state_prior_year_lyme_incidence_per_100k"] == 30.0
    assert features["feature_log_population_offset"] == 11.608236


def test_build_annual_forecast_caps_target_year_history_depth_to_design_window(
    tmp_path: Path,
    monkeypatch,
) -> None:
    matrix = _write_design_matrix(
        tmp_path / "design_matrix.csv",
        county_values={
            "24001": [10, 20, 30, 40, 50, 60, 70, 80],
            "24003": [15, 25, 35, 45, 55, 65, 75, 85],
        },
        start_year=2017,
    )
    population = _write_population(tmp_path / "population.csv")
    captured_rows = []

    def capturing_ridge_prediction(
        *,
        row,
        train_rows,
        feature_columns,
        ridge_alpha,
        ridge_cache,
    ):
        captured_rows.append((row.county_fips, dict(row.features)))
        return 12.345678

    monkeypatch.setattr(
        annual_forecast,
        "_ridge_prediction",
        capturing_ridge_prediction,
    )

    build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    features = next(features for fips, features in captured_rows if fips == "24001")
    assert features["feature_trailing_history_years"] == 5.0
    assert features["feature_trailing_5yr_mean_lyme_incidence_per_100k"] == 60.0


def test_build_annual_forecast_uses_population_weighted_state_prior_incidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    matrix = _write_design_matrix(
        tmp_path / "design_matrix.csv",
        county_populations={
            "24001": 100000,
            "24003": 300000,
        },
    )
    population = _write_population(tmp_path / "population.csv")
    captured_rows = []

    def capturing_ridge_prediction(
        *,
        row,
        train_rows,
        feature_columns,
        ridge_alpha,
        ridge_cache,
    ):
        captured_rows.append((row.county_fips, dict(row.features)))
        return 12.345678

    monkeypatch.setattr(
        annual_forecast,
        "_ridge_prediction",
        capturing_ridge_prediction,
    )

    build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    features = next(features for fips, features in captured_rows if fips == "24001")
    assert features["feature_state_prior_year_lyme_incidence_per_100k"] == 25.0
    assert features["feature_missing_state_prior_year_lyme_incidence"] == 0.0


def test_build_annual_forecast_adds_spatial_ridge_and_top4_with_adjacency(
    tmp_path: Path,
    monkeypatch,
) -> None:
    matrix = _write_design_matrix(
        tmp_path / "design_matrix.csv",
        include_spatial_features=True,
    )
    population = _write_population(tmp_path / "population.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")
    captured_spatial_features = {}

    def capturing_ridge_prediction(
        *,
        row,
        train_rows,
        feature_columns,
        ridge_alpha,
        ridge_cache,
    ):
        if "feature_neighbor_prior_year_lyme_incidence_mean" in feature_columns:
            captured_spatial_features[row.county_fips] = dict(row.features)
            return 22.0
        return 11.0

    monkeypatch.setattr(
        annual_forecast,
        "_ridge_prediction",
        capturing_ridge_prediction,
    )

    result = build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        county_adjacency_path=adjacency,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    model_names = {row.model_name for row in result.predictions}
    assert "ridge_forecast_spatial" in model_names
    assert "forecast_safe_top4_ensemble" in model_names
    assert result.run.n_forecast_rows == 16
    assert result.run.county_adjacency_path == str(adjacency)
    assert len(result.run.county_adjacency_sha256 or "") == 64

    spatial = next(
        row
        for row in result.predictions
        if row.model_name == "ridge_forecast_spatial"
        and row.county_fips == "24001"
    )
    top4 = next(
        row
        for row in result.predictions
        if row.model_name == "forecast_safe_top4_ensemble"
        and row.county_fips == "24001"
    )
    features = captured_spatial_features["24001"]

    assert spatial.feature_profile == "forecast_safe_lagged_spatial"
    assert spatial.weather_mode == "not_used_by_forecast_safe_model"
    assert spatial.predicted_incidence_per_100k == 22.0
    assert top4.feature_profile == "forecast_safe_top4_blend"
    assert top4.predicted_incidence_per_100k == 26.375
    assert features["feature_neighbor_prior_year_lyme_incidence_mean"] == 20.0
    assert features["feature_neighbor_prior_year_lyme_incidence_max"] == 20.0
    assert features["feature_neighbor_prior_year_count"] == 1.0
    assert features["feature_missing_neighbor_prior_year_lyme_incidence"] == 0.0


def test_build_annual_forecast_limits_analog_to_lagged_history_features(
    tmp_path: Path,
    monkeypatch,
) -> None:
    matrix = _write_design_matrix(
        tmp_path / "design_matrix.csv",
        include_extra_analog_candidates=True,
    )
    population = _write_population(tmp_path / "population.csv")
    captured_columns = []
    original_analog_prediction = annual_forecast._analog_prediction

    def capturing_analog_prediction(row, train_rows, feature_columns):
        captured_columns.append(tuple(feature_columns))
        return original_analog_prediction(row, train_rows, feature_columns)

    monkeypatch.setattr(
        annual_forecast,
        "_analog_prediction",
        capturing_analog_prediction,
    )

    build_annual_forecast(
        design_matrix_path=matrix,
        population_path=population,
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    assert captured_columns
    assert all(
        "feature_prior_year_lyme_incidence_per_100k" in columns
        for columns in captured_columns
    )
    assert all("feature_trailing_history_years" in columns for columns in captured_columns)
    assert all("feature_year" not in columns for columns in captured_columns)
    assert all("feature_forest_pct" not in columns for columns in captured_columns)
    assert all(
        "feature_regional_prior_year_midatlantic_total_cases" not in columns
        for columns in captured_columns
    )
    assert all(
        "feature_neighbor_prior_year_lyme_incidence_mean" not in columns
        for columns in captured_columns
    )


def test_write_annual_forecast_outputs_uses_stable_schemas(tmp_path: Path) -> None:
    result = build_annual_forecast(
        design_matrix_path=_write_design_matrix(tmp_path / "design_matrix.csv"),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2026,
        forecast_origin_year=2024,
        min_train_years=2,
    )

    outputs = write_annual_forecast_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        run_rows = list(csv.reader(handle))
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        prediction_rows = list(csv.reader(handle))

    assert run_rows[0] == ANNUAL_FORECAST_RUN_COLUMNS
    assert prediction_rows[0] == ANNUAL_FORECAST_PREDICTION_COLUMNS
    assert outputs.runs_path.name == "annual_forecast_runs.csv"
    assert outputs.predictions_path.name == "annual_forecast_predictions.csv"
    assert len(prediction_rows) == len(result.predictions) + 1


def _write_design_matrix(
    path: Path,
    *,
    sparse_county: bool = False,
    stale_county: bool = False,
    include_extra_analog_candidates: bool = False,
    include_spatial_features: bool = False,
    county_values: dict[str, list[int]] | None = None,
    county_populations: dict[str, int] | None = None,
    start_year: int = 2021,
) -> Path:
    rows = []
    county_values = county_values or {
        "24001": [10, 20, 30, 40],
        "24003": [80, 60, 40, 20],
    }
    county_populations = county_populations or {}
    for county_fips, values in county_values.items():
        population = county_populations.get(county_fips, 100000)
        for offset, incidence in enumerate(values):
            year = start_year + offset
            row = {
                "county_fips": county_fips,
                "county_name": f"County {county_fips}",
                "year": str(year),
                "target_total_cases": str(round(incidence / 100000 * population)),
                "target_lyme_incidence_per_100k": str(float(incidence)),
                "target_population": str(population),
                "feature_year": str(float(year)),
                "feature_prior_year_lyme_incidence_per_100k": str(
                    float(values[offset - 1] if offset else 0)
                ),
                "feature_trailing_5yr_mean_lyme_incidence_per_100k": str(
                    mean(float(value) for value in values[: offset + 1])
                ),
                "feature_trailing_history_years": str(offset),
                "model_feature_quality_flags": (
                    "mdh_probable_only_2024,drought_monitor_retro_observed"
                    if year == 2024
                    else ""
                ),
                "feature_state_prior_year_lyme_incidence_per_100k": str(
                    float(values[offset - 1] if offset else 0)
                ),
                "feature_missing_state_prior_year_lyme_incidence": (
                    "0" if offset else "1"
                ),
                "feature_log_population_offset": "11.512925",
            }
            if include_extra_analog_candidates:
                row.update(
                    {
                        "feature_forest_pct": str(float(40 + offset)),
                        "feature_neighbor_prior_year_lyme_incidence_mean": str(
                            float(incidence / 2)
                        ),
                        "feature_regional_prior_year_midatlantic_total_cases": str(
                            float(1000 + incidence)
                        ),
                    }
                )
            if include_spatial_features:
                row.update(
                    {
                        "feature_neighbor_prior_year_lyme_incidence_mean": "999.0",
                        "feature_neighbor_prior_year_lyme_incidence_max": "999.0",
                        "feature_neighbor_prior_year_count": "9",
                        "feature_missing_neighbor_prior_year_lyme_incidence": "0",
                    }
                )
            rows.append(row)
    if sparse_county:
        rows.append(
            {
                "county_fips": "24005",
                "county_name": "County 24005",
                "year": "2024",
                "target_total_cases": "12",
                "target_lyme_incidence_per_100k": "12.0",
                "target_population": "100000",
                "feature_prior_year_lyme_incidence_per_100k": "11.0",
                "feature_trailing_5yr_mean_lyme_incidence_per_100k": "11.0",
                "feature_trailing_history_years": "1",
                "feature_state_prior_year_lyme_incidence_per_100k": "30.0",
                "feature_missing_state_prior_year_lyme_incidence": "0",
                "feature_log_population_offset": "11.512925",
                "model_feature_quality_flags": "",
            }
        )
    if stale_county:
        for year, incidence in [(2021, 7), (2022, 9)]:
            rows.append(
                {
                    "county_fips": "24009",
                    "county_name": "County 24009",
                    "year": str(year),
                    "target_total_cases": str(incidence),
                    "target_lyme_incidence_per_100k": str(float(incidence)),
                    "target_population": "100000",
                    "feature_prior_year_lyme_incidence_per_100k": "0.0",
                    "feature_trailing_5yr_mean_lyme_incidence_per_100k": str(
                        float(incidence)
                    ),
                    "feature_trailing_history_years": "1",
                    "feature_state_prior_year_lyme_incidence_per_100k": "0.0",
                    "feature_missing_state_prior_year_lyme_incidence": "1",
                    "feature_log_population_offset": "11.512925",
                    "model_feature_quality_flags": "",
                }
            )
    _write_rows(path, rows)
    return path


def _write_adjacency(path: Path) -> Path:
    rows = [
        {
            "county_fips": "24001",
            "county_name": "County 24001",
            "neighbor_county_fips": "24003",
            "neighbor_county_name": "County 24003",
            "shared_boundary_segment_count": "1",
            "adjacency_method": "fixture",
            "feature_quality_flags": "county_adjacency_from_fixture",
        },
        {
            "county_fips": "24003",
            "county_name": "County 24003",
            "neighbor_county_fips": "24001",
            "neighbor_county_name": "County 24001",
            "shared_boundary_segment_count": "1",
            "adjacency_method": "fixture",
            "feature_quality_flags": "county_adjacency_from_fixture",
        },
    ]
    _write_rows(path, rows)
    return path


def _write_population(path: Path, *, extra_counties: list[str] | None = None) -> Path:
    rows = [
        {
            "county_fips": "24001",
            "county_name": "County 24001",
            "year": "2026",
            "population": "110000",
            "source_id": "regional_population_linear_projection",
            "vintage": "2025",
            "feature_quality_flags": (
                "regional_population_denominator,"
                "simple_linear_population_projection,"
                "no_official_2026_census_denominator"
            ),
        },
        {
            "county_fips": "24003",
            "county_name": "County 24003",
            "year": "2026",
            "population": "90000",
            "source_id": "regional_population_linear_projection",
            "vintage": "2025",
            "feature_quality_flags": (
                "regional_population_denominator,"
                "simple_linear_population_projection,"
                "no_official_2026_census_denominator"
            ),
        },
    ]
    for county_fips in extra_counties or []:
        rows.append(
            {
                "county_fips": county_fips,
                "county_name": f"County {county_fips}",
                "year": "2026",
                "population": "50000",
                "source_id": "regional_population_linear_projection",
                "vintage": "2025",
                "feature_quality_flags": (
                    "regional_population_denominator,"
                    "simple_linear_population_projection,"
                    "no_official_2026_census_denominator"
                ),
            }
        )
    _write_rows(
        path,
        rows,
    )
    return path


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
