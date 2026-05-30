import csv
from pathlib import Path

from tickbiterisk.modeling.regional_forecast_typicality import (
    build_regional_forecast_typicality,
)
from tickbiterisk.modeling.regional_forecast_typicality_build import (
    write_regional_forecast_typicality_outputs,
)


def test_regional_forecast_typicality_compares_forecast_to_prior_county_history(
    tmp_path: Path,
) -> None:
    incidence_path = _write_incidence_panel(tmp_path / "incidence.csv")
    intervals_path = _write_forecast_intervals(tmp_path / "intervals.csv")

    result = build_regional_forecast_typicality(
        regional_incidence_path=incidence_path,
        regional_annual_forecast_intervals_path=intervals_path,
        model_name="empirical_bayes_spatial_regime_incidence",
    )

    assert result.run.n_forecast_rows == 2
    assert result.run.n_typicality_rows == 1
    assert result.run.baseline_policy == "county history years <= forecast_origin_year"

    row = result.rows[0]
    assert row.county_fips == "24001"
    assert row.forecast_year == 2026
    assert row.forecast_origin_year == 2004
    assert row.comparison_scope == "county_prior_history"
    assert row.comparison_year_start == 2001
    assert row.comparison_year_end == 2004
    assert row.baseline_year_count == 4
    assert row.typical_median_incidence_per_100k == 25.0
    assert row.typical_p25_incidence_per_100k == 17.5
    assert row.typical_p75_incidence_per_100k == 32.5
    assert row.forecast_percentile_of_county_history == 100.0
    assert row.lower_80_percentile_of_county_history == 50.0
    assert row.upper_80_percentile_of_county_history == 100.0
    assert row.lower_95_percentile_of_county_history == 0.0
    assert row.upper_95_percentile_of_county_history == 100.0
    assert row.severity_label == "much higher than typical"
    assert row.interval_severity_label == "typical to much higher than typical"
    assert row.typicality_evidence_level == "very limited"
    assert row.margin_to_typical_band_per_100k == 12.5
    assert row.protocol_policy == "raw_with_surveillance_protocol_caveat"
    assert "forecast_typicality_county_prior_history" in row.assumption_flags
    assert "target_year_observed_rows_excluded" in row.assumption_flags
    assert "not_public_default" in row.assumption_flags


def test_write_regional_forecast_typicality_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_forecast_typicality(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        regional_annual_forecast_intervals_path=_write_forecast_intervals(
            tmp_path / "intervals.csv"
        ),
        model_name="empirical_bayes_spatial_regime_incidence",
    )

    outputs = write_regional_forecast_typicality_outputs(result, tmp_path / "out")

    assert outputs.runs_path.name == "regional_forecast_typicality_runs.csv"
    assert outputs.typicality_path.name == "regional_forecast_typicality.csv"
    with outputs.typicality_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["forecast_percentile_of_county_history"] == "100.0"
    assert rows[0]["severity_label"] == "much higher than typical"
    assert rows[0]["interval_severity_label"] == (
        "typical to much higher than typical"
    )


def test_regional_forecast_typicality_rejects_same_year_forecast_rows(
    tmp_path: Path,
) -> None:
    incidence_path = _write_incidence_panel(tmp_path / "incidence.csv")
    intervals_path = _write_forecast_intervals(
        tmp_path / "intervals.csv",
        forecast_year="2004",
        forecast_origin_year="2004",
    )

    try:
        build_regional_forecast_typicality(
            regional_incidence_path=incidence_path,
            regional_annual_forecast_intervals_path=intervals_path,
            model_name="empirical_bayes_spatial_regime_incidence",
        )
    except ValueError as exc:
        assert "forecast_year must be greater than forecast_origin_year" in str(exc)
    else:
        raise AssertionError("Expected same-year forecast interval rows to fail")


def _write_incidence_panel(path: Path) -> Path:
    columns = [
        "state_fips",
        "state_abbr",
        "state_name",
        "county_fips",
        "county_name",
        "year",
        "total_cases",
        "population",
        "incidence_per_100k",
        "feature_quality_flags",
    ]
    rows = [
        _incidence_row("24001", "Allegany County", 2001, "10.0"),
        _incidence_row("24001", "Allegany County", 2002, "20.0"),
        _incidence_row("24001", "Allegany County", 2003, "30.0"),
        _incidence_row("24001", "Allegany County", 2004, "40.0"),
        _incidence_row("24001", "Allegany County", 2024, "100.0"),
        _incidence_row("24003", "Anne Arundel County", 2004, "18.0"),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_forecast_intervals(
    path: Path,
    *,
    forecast_year: str = "2026",
    forecast_origin_year: str = "2004",
) -> Path:
    columns = [
        "run_id",
        "source_forecast_run_id",
        "model_name",
        "model_family",
        "target_definition",
        "feature_set",
        "feature_profile",
        "evaluation_mode",
        "regional_incidence_sha256",
        "regional_population_sha256",
        "state_fips",
        "state_abbr",
        "state_name",
        "county_fips",
        "county_name",
        "forecast_year",
        "forecast_origin_year",
        "as_of_date",
        "data_cutoff_date",
        "source_vintage",
        "update_mode",
        "forecast_population",
        "predicted_cases",
        "predicted_incidence_per_100k",
        "interval_method",
        "residual_count",
        "residual_test_start_year",
        "residual_test_end_year",
        "lower_80_incidence_per_100k",
        "median_incidence_per_100k",
        "upper_80_incidence_per_100k",
        "lower_95_incidence_per_100k",
        "upper_95_incidence_per_100k",
        "lower_80_cases",
        "median_cases",
        "upper_80_cases",
        "lower_95_cases",
        "upper_95_cases",
        "interval_feature_quality_flags",
        "interval_assumption_flags",
    ]
    rows = [
        _interval_row(
            "24001",
            "Allegany County",
            "45.0",
            "25.0",
            "55.0",
            forecast_year=forecast_year,
            forecast_origin_year=forecast_origin_year,
        ),
        _interval_row(
            "24003",
            "Anne Arundel County",
            "22.0",
            "10.0",
            "35.0",
            forecast_year=forecast_year,
            forecast_origin_year=forecast_origin_year,
        ),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _incidence_row(
    county_fips: str,
    county_name: str,
    year: int,
    incidence: str,
) -> dict[str, str]:
    return {
        "state_fips": county_fips[:2],
        "state_abbr": "MD",
        "state_name": "Maryland",
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "total_cases": "10",
        "population": "100000",
        "incidence_per_100k": incidence,
        "feature_quality_flags": (
            "reported_cases_not_stable_true_incidence,"
            "lyme_case_definition_change"
        ),
    }


def _interval_row(
    county_fips: str,
    county_name: str,
    predicted: str,
    lower_80: str,
    upper_80: str,
    *,
    forecast_year: str = "2026",
    forecast_origin_year: str = "2004",
) -> dict[str, str]:
    return {
        "run_id": (
            "regional_annual_forecast_intervals_"
            f"forecast{forecast_year}_origin{forecast_origin_year}"
        ),
        "source_forecast_run_id": (
            f"regional_annual_forecast_target{forecast_year}_"
            f"origin{forecast_origin_year}"
        ),
        "model_name": "empirical_bayes_spatial_regime_incidence",
        "model_family": "empirical_bayes_spatial_regime",
        "target_definition": "reported_lyme_incidence_per_100k",
        "feature_set": "historical_incidence_forecast_baselines",
        "feature_profile": "localized_spatial_regime_shrinkage",
        "evaluation_mode": "regional_annual_forecast_no_observed_target",
        "regional_incidence_sha256": "a" * 64,
        "regional_population_sha256": "b" * 64,
        "state_fips": county_fips[:2],
        "state_abbr": "MD",
        "state_name": "Maryland",
        "county_fips": county_fips,
        "county_name": county_name,
        "forecast_year": forecast_year,
        "forecast_origin_year": forecast_origin_year,
        "as_of_date": "2026-05-30",
        "data_cutoff_date": "2004-12-31",
        "source_vintage": "unit_test",
        "update_mode": "pre_update",
        "forecast_population": "100000",
        "predicted_cases": predicted,
        "predicted_incidence_per_100k": predicted,
        "interval_method": "empirical_rolling_origin_residual_quantile",
        "residual_count": "30",
        "residual_test_start_year": "2001",
        "residual_test_end_year": "2004",
        "lower_80_incidence_per_100k": lower_80,
        "median_incidence_per_100k": predicted,
        "upper_80_incidence_per_100k": upper_80,
        "lower_95_incidence_per_100k": "5.0",
        "upper_95_incidence_per_100k": "60.0",
        "lower_80_cases": lower_80,
        "median_cases": predicted,
        "upper_80_cases": upper_80,
        "lower_95_cases": "5.0",
        "upper_95_cases": "60.0",
        "interval_feature_quality_flags": "forecast_safe_prior_origin_residuals",
        "interval_assumption_flags": (
            "empirical_rolling_origin_residual_interval,not_public_default"
        ),
    }
