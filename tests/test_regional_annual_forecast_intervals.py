import csv
from pathlib import Path

import pytest

from tests.test_regional_annual_forecast import (
    _sha256_file,
    _write_incidence_panel,
    _write_population,
)
from tickbiterisk.modeling.regional_annual_forecast import (
    build_regional_annual_forecast,
)
from tickbiterisk.modeling.regional_annual_forecast_build import (
    write_regional_annual_forecast_outputs,
)
from tickbiterisk.modeling.regional_annual_forecast_intervals import (
    REGIONAL_ANNUAL_FORECAST_INTERVAL_COLUMNS,
    REGIONAL_ANNUAL_FORECAST_INTERVAL_RUN_COLUMNS,
    RegionalAnnualForecastIntervalInputError,
    build_regional_annual_forecast_intervals,
    write_regional_annual_forecast_interval_outputs,
)


def test_regional_annual_forecast_intervals_use_prior_origin_residuals(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
        include_future_leakage_row=True,
    )

    result = build_regional_annual_forecast_intervals(
        forecast_predictions_path=forecast_predictions,
        regional_incidence_stress_predictions_path=stress_predictions,
        min_residual_count=2,
    )

    latest = next(
        row
        for row in result.intervals
        if row.model_name == "latest_observed_county_incidence"
        and row.county_fips == "24001"
    )
    assert latest.residual_model_name == "prior_year_county_incidence"
    assert latest.residual_count == 2
    assert latest.residual_test_start_year == 2020
    assert latest.residual_test_end_year == 2021
    assert latest.predicted_incidence_per_100k == 40.0
    assert latest.lower_80_incidence_per_100k == 32.0
    assert latest.median_incidence_per_100k == 40.0
    assert latest.upper_80_incidence_per_100k == 48.0
    assert latest.lower_95_incidence_per_100k == 30.5
    assert latest.upper_95_incidence_per_100k == 49.5
    assert latest.lower_80_cases == 35.2
    assert latest.upper_95_cases == 54.45
    assert "empirical_rolling_origin_residual_interval" in (
        latest.interval_assumption_flags
    )
    assert "forecast_without_observed_target" in latest.interval_assumption_flags
    assert "not_public_default" in latest.interval_assumption_flags
    assert "residual_model_alias_prior_year_county_incidence" in (
        latest.interval_feature_quality_flags
    )
    assert result.run.n_forecast_rows == 20
    assert result.run.n_interval_rows == 20
    assert result.run.residual_test_start_year == 2020
    assert result.run.residual_test_end_year == 2021


def test_regional_annual_forecast_intervals_reject_source_hash_mismatch(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256="not_the_forecast_incidence_hash",
    )

    with pytest.raises(
        RegionalAnnualForecastIntervalInputError,
        match="source_file_sha256",
    ):
        build_regional_annual_forecast_intervals(
            forecast_predictions_path=forecast_predictions,
            regional_incidence_stress_predictions_path=stress_predictions,
            min_residual_count=2,
        )


def test_regional_annual_forecast_intervals_reject_missing_model_residuals(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
        omitted_model_name="trailing_mean_county_incidence",
    )

    with pytest.raises(
        RegionalAnnualForecastIntervalInputError,
        match="trailing_mean_county_incidence",
    ):
        build_regional_annual_forecast_intervals(
            forecast_predictions_path=forecast_predictions,
            regional_incidence_stress_predictions_path=stress_predictions,
            min_residual_count=2,
        )


def test_regional_annual_forecast_intervals_reject_mixed_stress_branch_metadata(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
        mixed_metadata_model_name="trailing_mean_county_incidence",
    )

    with pytest.raises(
        RegionalAnnualForecastIntervalInputError,
        match="mixed residual metadata",
    ):
        build_regional_annual_forecast_intervals(
            forecast_predictions_path=forecast_predictions,
            regional_incidence_stress_predictions_path=stress_predictions,
            min_residual_count=2,
        )


def test_write_regional_annual_forecast_interval_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    forecast_predictions = _write_forecast_predictions(tmp_path)
    incidence_sha = _sha256_file(tmp_path / "incidence.csv")
    stress_predictions = _write_stress_predictions(
        tmp_path / "stress_predictions.csv",
        source_file_sha256=incidence_sha,
    )
    result = build_regional_annual_forecast_intervals(
        forecast_predictions_path=forecast_predictions,
        regional_incidence_stress_predictions_path=stress_predictions,
        min_residual_count=2,
    )

    outputs = write_regional_annual_forecast_interval_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_ANNUAL_FORECAST_INTERVAL_RUN_COLUMNS
    with outputs.intervals_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_ANNUAL_FORECAST_INTERVAL_COLUMNS
    assert outputs.runs_path.name == "regional_annual_forecast_interval_runs.csv"
    assert outputs.intervals_path.name == "regional_annual_forecast_intervals.csv"


def _write_forecast_predictions(tmp_path: Path) -> Path:
    incidence_path = _write_incidence_panel(tmp_path / "incidence.csv")
    population_path = _write_population(tmp_path / "population.csv")
    result = build_regional_annual_forecast(
        regional_incidence_path=incidence_path,
        population_path=population_path,
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
        shrinkage_strength=2.0,
        as_of_date="2026-05-29",
        data_cutoff_date="2021-12-31",
        source_vintage="fixture_v1",
        update_mode="pre_update",
    )
    outputs = write_regional_annual_forecast_outputs(result, tmp_path / "forecast")
    return outputs.predictions_path


def _write_stress_predictions(
    path: Path,
    *,
    source_file_sha256: str,
    include_future_leakage_row: bool = False,
    omitted_model_name: str | None = None,
    mixed_metadata_model_name: str | None = None,
) -> Path:
    model_names = [
        "prior_year_county_incidence",
        "trailing_mean_county_incidence",
        "analog_year_county_incidence",
        "empirical_bayes_state_incidence",
        "empirical_bayes_midatlantic_incidence",
    ]
    rows = []
    for model_name in model_names:
        if model_name == omitted_model_name:
            continue
        rows.extend(
            [
                _stress_row(
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    test_year="2020",
                    residual="-10.0",
                ),
                _stress_row(
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    test_year="2021",
                    residual="10.0",
                ),
            ]
        )
        if include_future_leakage_row:
            rows.append(
                _stress_row(
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    test_year="2022",
                    residual="999.0",
                )
            )
        if model_name == mixed_metadata_model_name:
            rows.append(
                {
                    **_stress_row(
                        model_name=model_name,
                        source_file_sha256=source_file_sha256,
                        test_year="2021",
                        residual="5.0",
                    ),
                    "evaluation_mode": "same_year_diagnostic_leak",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _stress_row(
    *,
    model_name: str,
    source_file_sha256: str,
    test_year: str,
    residual: str,
) -> dict[str, str]:
    return {
        "run_id": "stress-run-1",
        "model_name": model_name,
        "model_family": _stress_model_family(model_name),
        "target_definition": "reported_lyme_incidence_per_100k",
        "feature_set": "historical_incidence_shrinkage_analog_random_forest_baselines",
        "evaluation_mode": "rolling_origin_prior_years",
        "source_file_sha256": source_file_sha256,
        "state_fips": "24",
        "state_abbr": "MD",
        "state_name": "Maryland",
        "county_fips": "24001",
        "county_name": "Allegany County",
        "test_year": test_year,
        "train_start_year": "2018",
        "train_end_year": str(int(test_year) - 1),
        "train_year_count": "2",
        "actual_incidence_per_100k": "50.0",
        "predicted_incidence_per_100k": str(50.0 - float(residual)),
        "residual_incidence_per_100k": residual,
        "absolute_error_incidence_per_100k": str(abs(float(residual))),
        "actual_cases": "50",
        "actual_population": "100000",
        "predicted_cases": "50.0",
        "analog_match_origin_year": "",
        "analog_match_observed_year": "",
        "analog_match_distance": "",
        "model_feature_quality_flags": "forecast_safe_prior_outcomes_only",
        "comparison_assumption_flags": (
            "reported_cases_not_stable_true_incidence,not_public_maryland_default"
        ),
    }


def _stress_model_family(model_name: str) -> str:
    if model_name == "analog_year_county_incidence":
        return "analog"
    if model_name.startswith("empirical_bayes_spatial_regime"):
        return "empirical_bayes_spatial_regime"
    if model_name.startswith("empirical_bayes_"):
        return "empirical_bayes_incidence_shrinkage"
    return "county_incidence_baseline"
