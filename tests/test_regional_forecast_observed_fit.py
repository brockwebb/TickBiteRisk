import csv
from pathlib import Path

import pytest

from tickbiterisk.modeling.regional_forecast_observed_fit import (
    RegionalForecastObservedFitInputError,
    build_regional_forecast_observed_fit,
)
from tickbiterisk.modeling.regional_forecast_observed_fit_build import (
    REGIONAL_FORECAST_OBSERVED_FIT_COMPARISON_COLUMNS,
    REGIONAL_FORECAST_OBSERVED_FIT_RUN_COLUMNS,
    REGIONAL_FORECAST_OBSERVED_FIT_SUMMARY_COLUMNS,
    write_regional_forecast_observed_fit_outputs,
)


def test_build_regional_forecast_observed_fit_compares_pa_overlay_to_forecast(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")

    result = build_regional_forecast_observed_fit(
        forecast_predictions_path=forecast,
        regional_incidence_path=incidence,
        forecast_year=2024,
        state_abbr="PA",
        model_name="empirical_bayes_spatial_regime_incidence",
    )

    assert result.run.forecast_year == 2024
    assert result.run.forecast_origin_year == 2023
    assert result.run.state_abbr == "PA"
    assert result.run.model_name == "empirical_bayes_spatial_regime_incidence"
    assert result.run.n_forecast_rows == 2
    assert result.run.n_observed_rows == 2
    assert result.run.n_matched_counties == 2
    assert "partial_state_overlay" in result.run.diagnostic_flags
    assert "post_forecast_diagnostic" in result.run.diagnostic_flags
    assert "not_training_feature" in result.run.diagnostic_flags

    adams = next(row for row in result.comparisons if row.county_fips == "42001")
    assert adams.diagnostic_scope == "pa_2024_partial_state_overlay"
    assert adams.source_forecast_run_id == "regional-forecast-run"
    assert adams.model_family == "empirical_bayes_incidence_shrinkage"
    assert adams.feature_profile == "spatial_regime_shrunken_incidence"
    assert adams.as_of_date == "2026-05-29"
    assert adams.data_cutoff_date == "2023-12-31"
    assert adams.update_mode == "pre_update"
    assert adams.forecast_population == 100000
    assert adams.observed_population == 100000
    assert adams.predicted_cases == 20.0
    assert adams.observed_cases == 30
    assert adams.case_residual == 10.0
    assert adams.absolute_case_error == 10.0
    assert adams.predicted_incidence_per_100k == 20.0
    assert adams.observed_incidence_per_100k == 30.0
    assert adams.incidence_residual_per_100k == 10.0
    assert adams.absolute_incidence_error_per_100k == 10.0
    assert "state_source_not_cdc_public_use" in adams.observed_quality_flags
    assert "pa_doh_official_county_cases" in adams.observed_quality_flags
    assert "not_regional_truth" in adams.diagnostic_flags
    assert "not_public_default" in adams.diagnostic_flags

    summary = result.summary[0]
    assert summary.diagnostic_scope == "pa_2024_partial_state_overlay"
    assert summary.n_counties == 2
    assert summary.predicted_total_cases == 60.0
    assert summary.observed_total_cases == 100.0
    assert summary.case_total_residual == 40.0
    assert summary.mean_case_residual == 20.0
    assert summary.mae_cases == 20.0
    assert summary.rmse_cases == 22.36068
    assert summary.predicted_population == 300000
    assert summary.observed_population == 300000
    assert summary.predicted_incidence_per_100k == 20.0
    assert summary.observed_incidence_per_100k == 33.333333
    assert summary.incidence_residual_per_100k == 13.333333
    assert summary.mae_incidence_per_100k == 12.5
    assert summary.rmse_incidence_per_100k == 12.747549
    assert summary.under_prediction_count == 2
    assert summary.over_prediction_count == 0
    assert summary.exact_prediction_count == 0
    assert "partial_state_overlay" in summary.diagnostic_flags
    assert "not_training_feature" in summary.diagnostic_flags


def test_regional_forecast_observed_fit_rejects_unmatched_observed_county(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")
    incidence = _write_incidence_panel(
        tmp_path / "incidence.csv",
        include_unmatched_observed=True,
    )

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "missing selected forecast rows for observed county FIPS: 42005" in str(
        excinfo.value
    )


def test_regional_forecast_observed_fit_rejects_unmatched_forecast_county(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(
        tmp_path / "forecast.csv",
        include_unmatched_forecast=True,
    )
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "missing selected observed rows for forecast county FIPS: 42005" in str(
        excinfo.value
    )


def test_regional_forecast_observed_fit_requires_state_source_overlay_rows(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")
    incidence = _write_incidence_panel(
        tmp_path / "incidence.csv",
        observed_flags="cdc_dashboard_total_cases,reported_cases_not_stable_true_incidence",
    )

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "selected observed rows must carry state_source_not_cdc_public_use" in str(
        excinfo.value
    )


def test_regional_forecast_observed_fit_requires_pre_update_forecast(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(
        tmp_path / "forecast.csv",
        update_mode="post_observed_outcome",
    )
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "selected forecast rows must have update_mode pre_update" in str(
        excinfo.value
    )


def test_regional_forecast_observed_fit_rejects_target_year_forecast_origin(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(
        tmp_path / "forecast.csv",
        forecast_origin_year=2024,
        data_cutoff_date="2023-12-31",
    )
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "forecast_origin_year must be before forecast_year" in str(excinfo.value)


def test_regional_forecast_observed_fit_rejects_target_year_data_cutoff(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(
        tmp_path / "forecast.csv",
        data_cutoff_date="2024-01-01",
    )
    incidence = _write_incidence_panel(tmp_path / "incidence.csv")

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "data_cutoff_date must be before forecast_year" in str(excinfo.value)


def test_regional_forecast_observed_fit_rejects_nonpositive_population(
    tmp_path: Path,
) -> None:
    forecast = _write_forecast_predictions(tmp_path / "forecast.csv")
    incidence = _write_incidence_panel(
        tmp_path / "incidence.csv",
        observed_population=0,
    )

    with pytest.raises(RegionalForecastObservedFitInputError) as excinfo:
        build_regional_forecast_observed_fit(
            forecast_predictions_path=forecast,
            regional_incidence_path=incidence,
            forecast_year=2024,
            state_abbr="PA",
            model_name="empirical_bayes_spatial_regime_incidence",
        )

    assert "population must be positive" in str(excinfo.value)


def test_write_regional_forecast_observed_fit_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_forecast_observed_fit(
        forecast_predictions_path=_write_forecast_predictions(tmp_path / "forecast.csv"),
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        forecast_year=2024,
        state_abbr="PA",
        model_name="empirical_bayes_spatial_regime_incidence",
    )

    outputs = write_regional_forecast_observed_fit_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_FORECAST_OBSERVED_FIT_RUN_COLUMNS
    with outputs.comparisons_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == (
            REGIONAL_FORECAST_OBSERVED_FIT_COMPARISON_COLUMNS
        )
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_FORECAST_OBSERVED_FIT_SUMMARY_COLUMNS


def _write_forecast_predictions(
    path: Path,
    *,
    include_unmatched_forecast: bool = False,
    forecast_origin_year: int = 2023,
    data_cutoff_date: str = "2023-12-31",
    update_mode: str = "pre_update",
) -> Path:
    rows = [
        _forecast_row(
            "42001",
            "Adams County",
            20,
            20.0,
            forecast_origin_year=forecast_origin_year,
            data_cutoff_date=data_cutoff_date,
            update_mode=update_mode,
        ),
        _forecast_row(
            "42003",
            "Allegheny County",
            40,
            20.0,
            population=200000,
            forecast_origin_year=forecast_origin_year,
            data_cutoff_date=data_cutoff_date,
            update_mode=update_mode,
        ),
        _forecast_row(
            "42001",
            "Adams County",
            999,
            999.0,
            model_name="analog_year_county_incidence",
            model_family="analog",
            feature_profile="forecast_safe_horizon_matched_analog",
        ),
        _forecast_row(
            "51001",
            "Accomack County",
            999,
            999.0,
            state_fips="51",
            state_abbr="VA",
            state_name="Virginia",
        ),
    ]
    if include_unmatched_forecast:
        rows.append(
            _forecast_row(
                "42005",
                "Armstrong County",
                5,
                5.0,
                forecast_origin_year=forecast_origin_year,
                data_cutoff_date=data_cutoff_date,
                update_mode=update_mode,
            )
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_incidence_panel(
    path: Path,
    *,
    include_unmatched_observed: bool = False,
    observed_flags: str = (
        "state_source_not_cdc_public_use,pa_doh_official_county_cases,"
        "reported_cases_not_stable_true_incidence"
    ),
    observed_population: int | None = None,
) -> Path:
    rows = [
        _incidence_row(
            "42001",
            "Adams County",
            2024,
            30,
            30.0,
            population=observed_population if observed_population is not None else 100000,
            feature_quality_flags=observed_flags,
        ),
        _incidence_row(
            "42003",
            "Allegheny County",
            2024,
            70,
            35.0,
            population=observed_population if observed_population is not None else 200000,
            feature_quality_flags=observed_flags,
        ),
        _incidence_row("42001", "Adams County", 2023, 22, 22.0),
        _incidence_row(
            "51001",
            "Accomack County",
            2024,
            1,
            1.0,
            state_fips="51",
            state_abbr="VA",
            state_name="Virginia",
        ),
    ]
    if include_unmatched_observed:
        rows.append(
            _incidence_row(
                "42005",
                "Armstrong County",
                2024,
                5,
                5.0,
                feature_quality_flags=observed_flags,
            )
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _forecast_row(
    county_fips: str,
    county_name: str,
    predicted_cases: float,
    predicted_incidence: float,
    *,
    population: int = 100000,
    state_fips: str = "42",
    state_abbr: str = "PA",
    state_name: str = "Pennsylvania",
    model_name: str = "empirical_bayes_spatial_regime_incidence",
    model_family: str = "empirical_bayes_incidence_shrinkage",
    feature_profile: str = "spatial_regime_shrunken_incidence",
    forecast_origin_year: int = 2023,
    data_cutoff_date: str = "2023-12-31",
    update_mode: str = "pre_update",
) -> dict[str, str]:
    return {
        "run_id": "regional-forecast-run",
        "model_name": model_name,
        "model_family": model_family,
        "target_definition": "reported_lyme_incidence_per_100k",
        "feature_set": "historical_incidence_forecast_baselines",
        "feature_profile": feature_profile,
        "evaluation_mode": "regional_annual_forecast_no_observed_target",
        "regional_incidence_sha256": "inc123",
        "regional_population_sha256": "pop123",
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "forecast_year": "2024",
        "forecast_origin_year": str(forecast_origin_year),
        "as_of_date": "2026-05-29",
        "data_cutoff_date": data_cutoff_date,
        "source_vintage": "cdc_lyme_county_dashboard_2023",
        "update_mode": update_mode,
        "forecast_horizon_years": "1",
        "train_start_year": "2001",
        "train_end_year": "2023",
        "train_year_count": "23",
        "forecast_population": str(population),
        "population_source_id": "census_pep_2025_county_totals",
        "population_vintage": "2025",
        "population_feature_quality_flags": (
            "regional_population_denominator,census_population_estimate"
        ),
        "predicted_cases": str(predicted_cases),
        "predicted_incidence_per_100k": str(predicted_incidence),
        "analog_match_origin_year": "",
        "analog_match_observed_year": "",
        "analog_match_distance": "",
        "model_feature_quality_flags": (
            "localized_spatial_regime_feature,forecast_safe_prior_outcomes_only"
        ),
        "forecast_assumption_flags": (
            "forecast_without_observed_target,reported_cases_not_stable_true_incidence"
        ),
    }


def _incidence_row(
    county_fips: str,
    county_name: str,
    year: int,
    cases: int,
    incidence: float,
    *,
    population: int = 100000,
    state_fips: str = "42",
    state_abbr: str = "PA",
    state_name: str = "Pennsylvania",
    feature_quality_flags: str = (
        "state_source_not_cdc_public_use,pa_doh_official_county_cases,"
        "reported_cases_not_stable_true_incidence"
    ),
) -> dict[str, str]:
    return {
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "total_cases": str(cases),
        "population": str(population),
        "incidence_per_100k": str(incidence),
        "diagnostic_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_percentile": "",
        "diagnostic_midatlantic_incidence_tier": "",
        "diagnostic_prior_year_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_rank_change": "",
        "lyme_panel_sha256": "lyme123",
        "population_panel_sha256": "pop123",
        "feature_quality_flags": feature_quality_flags,
    }
