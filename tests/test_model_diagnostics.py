import csv
from pathlib import Path

import pytest

from tickbiterisk.modeling.model_compare_build import (
    MODEL_COMPARISON_INTERVAL_COLUMNS,
    MODEL_COMPARISON_PREDICTION_COLUMNS,
)
from tickbiterisk.modeling.model_diagnostics import (
    ModelDiagnosticsInputError,
    build_model_diagnostics,
)
from tickbiterisk.modeling.model_diagnostics_build import (
    REGIONAL_CAPACITY_INTERVAL_COLUMNS,
    REGIONAL_HOTSPOT_SUMMARY_COLUMNS,
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


def test_model_diagnostics_builds_regional_hotspot_and_capacity_rows(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_intervals(tmp_path / "intervals.csv")

    result = build_model_diagnostics(predictions, intervals_path=intervals)
    outputs = write_model_diagnostics_outputs(result, tmp_path / "out")

    hotspot = next(
        row
        for row in result.regional_hotspot_summary
        if row.model_name == "linear_blend_baseline" and row.test_year == 2024
    )
    assert hotspot.run_id == "run-1"
    assert hotspot.model_family == "ensemble"
    assert hotspot.feature_profile == "linear_blend"
    assert hotspot.evaluation_mode == "rolling_origin_prior_years"
    assert hotspot.source_file_sha256 == "abc123"
    assert hotspot.region_id == "state_24"
    assert hotspot.region_name == "State 24"
    assert hotspot.n_counties == 2
    assert hotspot.actual_total_cases == 50
    assert hotspot.predicted_total_cases == 40.0
    assert hotspot.residual_cases == 10.0
    assert hotspot.absolute_error_cases == 10.0
    assert hotspot.actual_incidence_per_100k_mean == 35.0
    assert hotspot.predicted_incidence_per_100k_mean == 29.0
    assert hotspot.spearman_rank_correlation == 1.0
    assert hotspot.top3_hit_count == 2
    assert hotspot.top5_hit_count == 2
    assert hotspot.county_share_mae == 0.05
    assert hotspot.predicted_case_hhi == 0.505
    assert hotspot.actual_case_hhi == 0.52
    assert hotspot.comparison_assumption_flags == "surveillance_reporting_sensitive"

    capacity = next(
        row
        for row in result.regional_capacity_intervals
        if row.model_name == "analog_year_forecast" and row.test_year == 2024
    )
    assert capacity.run_id == "run-1"
    assert capacity.model_family == "analog"
    assert capacity.feature_profile == "analog_year"
    assert capacity.evaluation_mode == "rolling_origin_prior_years"
    assert capacity.source_file_sha256 == "abc123"
    assert capacity.region_id == "state_24"
    assert capacity.region_name == "State 24"
    assert capacity.interval_method == "summed_county_intervals"
    assert capacity.n_counties == 2
    assert capacity.lower_80_cases == 30.0
    assert capacity.median_cases == 45.0
    assert capacity.upper_80_cases == 60.0
    assert capacity.lower_95_cases == 20.0
    assert capacity.upper_95_cases == 70.0
    assert capacity.actual_cases == 50
    assert capacity.covered_80 is True
    assert capacity.covered_95 is True
    assert capacity.comparison_assumption_flags == "analog_interval_experimental"

    with outputs.regional_hotspot_summary_path.open(
        newline="", encoding="utf-8"
    ) as handle:
        assert next(csv.reader(handle)) == REGIONAL_HOTSPOT_SUMMARY_COLUMNS
    with outputs.regional_capacity_intervals_path.open(
        newline="", encoding="utf-8"
    ) as handle:
        assert next(csv.reader(handle)) == REGIONAL_CAPACITY_INTERVAL_COLUMNS


def test_build_model_diagnostics_keeps_runs_in_separate_summary_groups(
    tmp_path: Path,
) -> None:
    predictions = tmp_path / "predictions.csv"
    row_one = _prediction_row(
        county_fips="24005",
        county_name="County 24005",
        test_year=2022,
        actual_cases=40,
        predicted_cases=20,
        actual_incidence=60.0,
        predicted_incidence=40.0,
        quality_flags="lyme_case_definition_change",
        run_id="run-1",
        source_file_sha256="sha-run-1",
    )
    row_two = {
        **row_one,
        "run_id": "run-2",
        "source_file_sha256": "sha-run-2",
        "predicted_cases": "30",
        "predicted_incidence_per_100k": "50.0",
        "residual_cases": "10",
        "absolute_error_cases": "10",
        "residual_incidence_per_100k": "10.0",
        "absolute_error_incidence_per_100k": "10.0",
    }
    _write_rows(predictions, [row_one, row_two])

    result = build_model_diagnostics(predictions)

    overall_summaries = [
        row
        for row in result.surveillance_summary
        if row.model_name == "linear_blend_baseline"
        and row.surveillance_regime == "case_definition_change_2022_plus"
        and row.test_year is None
    ]
    assert {row.run_id for row in overall_summaries} == {"run-1", "run-2"}
    assert {row.source_file_sha256 for row in overall_summaries} == {
        "sha-run-1",
        "sha-run-2",
    }
    assert all(row.n_predictions == 1 for row in overall_summaries)


def test_build_model_diagnostics_rejects_headerless_csv(tmp_path: Path) -> None:
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("", encoding="utf-8")

    with pytest.raises(
        ModelDiagnosticsInputError,
        match="model comparison predictions CSV has no header",
    ):
        build_model_diagnostics(predictions)


def test_build_model_diagnostics_rejects_blank_required_numeric(
    tmp_path: Path,
) -> None:
    predictions = tmp_path / "predictions.csv"
    row = _prediction_row(
        county_fips="24005",
        county_name="County 24005",
        test_year=2022,
        actual_cases=40,
        predicted_cases=20,
        actual_incidence=60.0,
        predicted_incidence=40.0,
        quality_flags="lyme_case_definition_change",
    )
    row["actual_cases"] = ""
    _write_rows(predictions, [row])

    with pytest.raises(
        ModelDiagnosticsInputError,
        match="missing required numeric value in actual_cases",
    ):
        build_model_diagnostics(predictions)


def test_build_model_diagnostics_rejects_unmatched_interval_rows(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_interval_rows(
        tmp_path / "intervals.csv",
        [
            _interval_row(
                county_fips="24999",
                county_name="County 24999",
                lower_80_incidence=20.0,
                median_incidence=30.0,
                upper_80_incidence=40.0,
                lower_95_incidence=10.0,
                upper_95_incidence=50.0,
                observed_incidence=30.0,
            )
        ],
    )

    with pytest.raises(
        ModelDiagnosticsInputError,
        match="no matching prediction row",
    ):
        build_model_diagnostics(predictions, intervals_path=intervals)


def test_build_model_diagnostics_rejects_mixed_interval_methods(
    tmp_path: Path,
) -> None:
    predictions = _write_predictions(tmp_path / "predictions.csv")
    intervals = _write_interval_rows(
        tmp_path / "intervals.csv",
        [
            _interval_row(
                county_fips="24009",
                county_name="County 24009",
                lower_80_incidence=20.0,
                median_incidence=30.0,
                upper_80_incidence=40.0,
                lower_95_incidence=10.0,
                upper_95_incidence=50.0,
                observed_incidence=30.0,
            ),
            _interval_row(
                county_fips="24011",
                county_name="County 24011",
                lower_80_incidence=20.0,
                median_incidence=30.0,
                upper_80_incidence=40.0,
                lower_95_incidence=20.0,
                upper_95_incidence=40.0,
                observed_incidence=40.0,
                interval_method="alternate_bootstrap",
            ),
        ],
    )

    with pytest.raises(
        ModelDiagnosticsInputError,
        match="mixed interval_method values",
    ):
        build_model_diagnostics(predictions, intervals_path=intervals)


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
        _prediction_row(
            county_fips="24011",
            county_name="County 24011",
            test_year=2024,
            actual_cases=20,
            predicted_cases=18,
            actual_incidence=40.0,
            predicted_incidence=36.0,
            quality_flags=(
                "mdh_probable_only_2024,"
                "state_source_not_cdc_public_use,"
                "lyme_case_definition_change"
            ),
            actual_population=50000,
        ),
        _prediction_row(
            county_fips="24009",
            county_name="County 24009",
            test_year=2024,
            actual_cases=30,
            predicted_cases=25,
            actual_incidence=30.0,
            predicted_incidence=25.0,
            quality_flags=(
                "mdh_probable_only_2024,"
                "state_source_not_cdc_public_use,"
                "lyme_case_definition_change"
            ),
            model_name="analog_year_forecast",
            model_family="analog",
            feature_profile="analog_year",
        ),
        _prediction_row(
            county_fips="24011",
            county_name="County 24011",
            test_year=2024,
            actual_cases=20,
            predicted_cases=20,
            actual_incidence=40.0,
            predicted_incidence=40.0,
            quality_flags=(
                "mdh_probable_only_2024,"
                "state_source_not_cdc_public_use,"
                "lyme_case_definition_change"
            ),
            model_name="analog_year_forecast",
            model_family="analog",
            feature_profile="analog_year",
            actual_population=50000,
        ),
    ]
    return _write_rows(path, rows)


def _write_intervals(path: Path) -> Path:
    rows = [
        _interval_row(
            county_fips="24009",
            county_name="County 24009",
            lower_80_incidence=20.0,
            median_incidence=30.0,
            upper_80_incidence=40.0,
            lower_95_incidence=10.0,
            upper_95_incidence=50.0,
            observed_incidence=30.0,
        ),
        _interval_row(
            county_fips="24011",
            county_name="County 24011",
            lower_80_incidence=20.0,
            median_incidence=30.0,
            upper_80_incidence=40.0,
            lower_95_incidence=20.0,
            upper_95_incidence=40.0,
            observed_incidence=40.0,
        ),
    ]
    return _write_interval_rows(path, rows)


def _write_interval_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MODEL_COMPARISON_INTERVAL_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_rows(path: Path, rows: list[dict[str, str]]) -> Path:
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
    run_id: str = "run-1",
    model_name: str = "linear_blend_baseline",
    model_family: str = "ensemble",
    feature_profile: str = "linear_blend",
    evaluation_mode: str = "rolling_origin_prior_years",
    source_file_sha256: str = "abc123",
    actual_population: int = 100000,
) -> dict[str, str]:
    residual_incidence = actual_incidence - predicted_incidence
    residual_cases = actual_cases - predicted_cases
    return {
        "run_id": run_id,
        "model_name": model_name,
        "model_family": model_family,
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "synthetic",
        "feature_profile": feature_profile,
        "evaluation_mode": evaluation_mode,
        "weather_mode": "mixed_model_specific",
        "source_file_sha256": source_file_sha256,
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": str(test_year),
        "train_start_year": "2018",
        "train_end_year": str(test_year - 1),
        "train_row_count": "10",
        "train_county_count": "2",
        "actual_cases": str(actual_cases),
        "actual_population": str(actual_population),
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


def _interval_row(
    *,
    county_fips: str,
    county_name: str,
    lower_80_incidence: float,
    median_incidence: float,
    upper_80_incidence: float,
    lower_95_incidence: float,
    upper_95_incidence: float,
    observed_incidence: float,
    interval_method: str = "weighted_analog_bootstrap",
) -> dict[str, str]:
    return {
        "run_id": "run-1",
        "model_name": "analog_year_forecast",
        "model_family": "analog",
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "synthetic",
        "feature_profile": "analog_year",
        "evaluation_mode": "rolling_origin_prior_years",
        "weather_mode": "mixed_model_specific",
        "source_file_sha256": "abc123",
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": "2024",
        "train_start_year": "2018",
        "train_end_year": "2023",
        "interval_method": interval_method,
        "bootstrap_seed": "1337",
        "bootstrap_iterations": "200",
        "analog_count": "2",
        "analog_years": "2021;2022",
        "analog_counties": "24009;24011",
        "analog_weights": "0.5;0.5",
        "lower_80_incidence_per_100k": str(lower_80_incidence),
        "median_incidence_per_100k": str(median_incidence),
        "upper_80_incidence_per_100k": str(upper_80_incidence),
        "lower_95_incidence_per_100k": str(lower_95_incidence),
        "upper_95_incidence_per_100k": str(upper_95_incidence),
        "observed_incidence_per_100k": str(observed_incidence),
        "covered_80": "true",
        "covered_95": "true",
        "comparison_assumption_flags": "analog_interval_experimental",
    }
