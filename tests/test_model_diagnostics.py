import csv
from pathlib import Path

from tickbiterisk.modeling.model_compare_build import (
    MODEL_COMPARISON_PREDICTION_COLUMNS,
)
from tickbiterisk.modeling.model_diagnostics import build_model_diagnostics
from tickbiterisk.modeling.model_diagnostics_build import (
    SURVEILLANCE_REGIME_RESIDUAL_COLUMNS,
    SURVEILLANCE_REGIME_SUMMARY_COLUMNS,
    write_model_diagnostics_outputs,
)


def test_build_model_diagnostics_labels_surveillance_regimes(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")

    result = build_model_diagnostics(predictions)

    regimes = {row.surveillance_regime for row in result.surveillance_residuals}
    assert regimes == {
        "pre_2020_baseline",
        "covid_reporting_disruption",
        "case_definition_change_2022_plus",
        "mdh_probable_only_2024",
    }
    overall_2022_regime = next(
        row
        for row in result.surveillance_summary
        if row.model_name == "linear_blend_baseline"
        and row.surveillance_regime == "case_definition_change_2022_plus"
        and row.test_year is None
    )
    assert overall_2022_regime.n_predictions == 1
    assert overall_2022_regime.mean_residual_incidence_per_100k == 20.0
    assert overall_2022_regime.mae_incidence_per_100k == 20.0


def test_write_model_diagnostics_outputs_writes_expected_columns(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    result = build_model_diagnostics(predictions)

    outputs = write_model_diagnostics_outputs(result, tmp_path / "out")

    with outputs.surveillance_residuals_path.open(
        newline="", encoding="utf-8"
    ) as handle:
        assert next(csv.reader(handle)) == SURVEILLANCE_REGIME_RESIDUAL_COLUMNS
    with outputs.surveillance_summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == SURVEILLANCE_REGIME_SUMMARY_COLUMNS
    assert outputs.regional_hotspot_summary_path.exists()
    assert outputs.regional_capacity_intervals_path.exists()


def _write_predictions(path: Path) -> Path:
    rows = [
        _prediction_row(
            county_fips="24001",
            county_name="County 24001",
            test_year=2019,
            actual_cases=10,
            predicted_cases=8,
            actual_incidence=10.0,
            predicted_incidence=8.0,
            quality_flags="",
        ),
        _prediction_row(
            county_fips="24003",
            county_name="County 24003",
            test_year=2020,
            actual_cases=12,
            predicted_cases=15,
            actual_incidence=12.0,
            predicted_incidence=15.0,
            quality_flags="covid_reporting_disruption",
        ),
        _prediction_row(
            county_fips="24005",
            county_name="County 24005",
            test_year=2022,
            actual_cases=40,
            predicted_cases=20,
            actual_incidence=60.0,
            predicted_incidence=40.0,
            quality_flags="lyme_case_definition_change",
        ),
        _prediction_row(
            county_fips="24009",
            county_name="County 24009",
            test_year=2024,
            actual_cases=30,
            predicted_cases=22,
            actual_incidence=30.0,
            predicted_incidence=22.0,
            quality_flags=(
                "mdh_probable_only_2024,"
                "state_source_not_cdc_public_use,"
                "lyme_case_definition_change"
            ),
        ),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MODEL_COMPARISON_PREDICTION_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _prediction_row(
    *,
    county_fips: str,
    county_name: str,
    test_year: int,
    actual_cases: int,
    predicted_cases: float,
    actual_incidence: float,
    predicted_incidence: float,
    quality_flags: str,
) -> dict[str, str]:
    residual_incidence = actual_incidence - predicted_incidence
    residual_cases = actual_cases - predicted_cases
    return {
        "run_id": "run-1",
        "model_name": "linear_blend_baseline",
        "model_family": "ensemble",
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "synthetic",
        "feature_profile": "linear_blend",
        "evaluation_mode": "rolling_origin_prior_years",
        "weather_mode": "mixed_model_specific",
        "source_file_sha256": "abc123",
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": str(test_year),
        "train_start_year": "2018",
        "train_end_year": str(test_year - 1),
        "train_row_count": "10",
        "train_county_count": "2",
        "actual_cases": str(actual_cases),
        "actual_population": "100000",
        "actual_incidence_per_100k": str(actual_incidence),
        "predicted_cases": str(predicted_cases),
        "predicted_incidence_per_100k": str(predicted_incidence),
        "residual_incidence_per_100k": str(residual_incidence),
        "absolute_error_incidence_per_100k": str(abs(residual_incidence)),
        "residual_cases": str(residual_cases),
        "absolute_error_cases": str(abs(residual_cases)),
        "model_feature_quality_flags": quality_flags,
        "comparison_assumption_flags": "surveillance_reporting_sensitive",
    }
