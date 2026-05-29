import csv
import hashlib
from pathlib import Path

import pytest

from tickbiterisk.modeling.regional_annual_forecast import (
    RegionalAnnualForecastInputError,
    build_regional_annual_forecast,
)
from tickbiterisk.modeling.regional_annual_forecast_build import (
    REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS,
    REGIONAL_ANNUAL_FORECAST_RUN_COLUMNS,
    write_regional_annual_forecast_outputs,
)


def test_build_regional_annual_forecast_emits_target_year_rows_without_actuals(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    population = _write_population(tmp_path / "population.csv")

    result = build_regional_annual_forecast(
        regional_incidence_path=panel,
        population_path=population,
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
        shrinkage_strength=2.0,
        as_of_date="2026-05-28",
        data_cutoff_date="2023-12-31",
        source_vintage="cdc_2023_dashboard_v1",
        update_mode="pre_update",
    )

    assert result.run.target_year == 2023
    assert result.run.forecast_origin_year == 2021
    assert result.run.as_of_date == "2026-05-28"
    assert result.run.data_cutoff_date == "2023-12-31"
    assert result.run.source_vintage == "cdc_2023_dashboard_v1"
    assert result.run.update_mode == "pre_update"
    assert result.run.n_training_rows == 8
    assert result.run.n_forecast_counties == 4
    assert result.run.n_forecast_rows == 20
    assert {row.model_name for row in result.predictions} == {
        "analog_year_county_incidence",
        "empirical_bayes_midatlantic_incidence",
        "empirical_bayes_state_incidence",
        "latest_observed_county_incidence",
        "trailing_mean_county_incidence",
    }

    latest = next(
        row
        for row in result.predictions
        if row.model_name == "latest_observed_county_incidence"
        and row.county_fips == "24001"
    )
    assert latest.forecast_year == 2023
    assert latest.forecast_origin_year == 2021
    assert latest.as_of_date == "2026-05-28"
    assert latest.data_cutoff_date == "2023-12-31"
    assert latest.source_vintage == "cdc_2023_dashboard_v1"
    assert latest.update_mode == "pre_update"
    assert latest.forecast_horizon_years == 2
    assert latest.feature_profile == "latest_observed_origin_incidence"
    assert latest.forecast_population == 110000
    assert latest.predicted_incidence_per_100k == 40.0
    assert latest.predicted_cases == 44.0
    assert latest.train_start_year == 2020
    assert latest.train_end_year == 2021
    assert latest.train_year_count == 2
    assert "forecast_without_observed_target" in latest.forecast_assumption_flags
    assert "regional_population_denominator" in latest.forecast_assumption_flags
    assert "no_official_2023_census_denominator" in latest.forecast_assumption_flags
    assert "diagnostic_same_year_not_forecast_feature" not in (
        latest.forecast_assumption_flags
    )
    assert "actual_incidence_per_100k" not in REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS
    assert "residual_incidence_per_100k" not in (
        REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS
    )

    eb_state = next(
        row
        for row in result.predictions
        if row.model_name == "empirical_bayes_state_incidence"
        and row.county_fips == "24001"
    )
    assert eb_state.predicted_incidence_per_100k == 27.5
    assert eb_state.model_family == "empirical_bayes_incidence_shrinkage"
    assert eb_state.feature_profile == "state_shrunken_incidence"

    analog = next(
        row
        for row in result.predictions
        if row.model_name == "analog_year_county_incidence"
        and row.county_fips == "24001"
    )
    assert analog.model_family == "analog"
    assert analog.feature_profile == "forecast_safe_horizon_matched_analog"
    assert analog.predicted_incidence_per_100k == 40.0
    assert analog.analog_match_origin_year == 2019
    assert analog.analog_match_observed_year == 2021
    assert analog.analog_match_distance == 40.0
    assert analog.train_start_year == 2018
    assert analog.train_end_year == 2021
    assert analog.train_year_count == 4
    assert "analog_like_year_forecast" in analog.model_feature_quality_flags
    assert "analog_horizon_matched_outcome" in analog.model_feature_quality_flags


def test_build_regional_annual_forecast_defaults_origin_to_latest_complete_year(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        min_train_years=2,
        lookback_years=2,
    )

    assert result.run.forecast_origin_year == 2021
    assert {row.forecast_origin_year for row in result.predictions} == {2021}


def test_default_regional_forecast_origin_ignores_obsolete_extra_geographies(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(
            tmp_path / "incidence.csv",
            obsolete_extra_county=True,
        ),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        min_train_years=2,
        lookback_years=2,
    )

    assert result.run.forecast_origin_year == 2021


def test_regional_annual_forecast_analog_excludes_future_outcomes(
    tmp_path: Path,
) -> None:
    panel = _write_single_county_incidence_panel(
        tmp_path / "incidence.csv",
        [5, 15, 50, 60, 999, 1],
    )

    result = build_regional_annual_forecast(
        regional_incidence_path=panel,
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    analog = next(
        row
        for row in result.predictions
        if row.model_name == "analog_year_county_incidence"
    )
    assert analog.predicted_incidence_per_100k == 60.0
    assert analog.analog_match_origin_year == 2019
    assert analog.analog_match_observed_year == 2021
    assert analog.analog_match_observed_year <= analog.forecast_origin_year
    assert analog.predicted_incidence_per_100k != 999.0
    assert "analog_outcome_observed_by_forecast_origin" in (
        analog.model_feature_quality_flags
    )


def test_build_regional_annual_forecast_ignores_partial_overlay_year_by_default(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(
            tmp_path / "incidence.csv",
            partial_overlay_year=True,
        ),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        min_train_years=2,
        lookback_years=2,
    )

    assert result.run.forecast_origin_year == 2021
    assert result.run.n_forecast_counties == 4
    assert {row.forecast_origin_year for row in result.predictions} == {2021}


def test_build_regional_annual_forecast_ignores_high_coverage_partial_year(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(
            tmp_path / "incidence.csv",
            extra_full_county=True,
            high_coverage_partial_overlay_year=True,
        ),
        population_path=_write_population(
            tmp_path / "population.csv",
            extra_counties=["24005"],
        ),
        target_year=2023,
        min_train_years=2,
        lookback_years=2,
    )

    assert result.run.forecast_origin_year == 2021
    assert result.run.n_forecast_counties == 5
    assert {row.forecast_origin_year for row in result.predictions} == {2021}


def test_build_regional_annual_forecast_can_explicitly_use_partial_origin(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(
            tmp_path / "incidence.csv",
            partial_overlay_year=True,
        ),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        forecast_origin_year=2022,
        min_train_years=2,
        lookback_years=2,
    )

    assert result.run.forecast_origin_year == 2022
    assert result.run.n_forecast_counties == 1
    assert {row.county_fips for row in result.predictions} == {"42001"}


def test_regional_annual_forecast_uses_spatial_regime_prior_not_diagnostic_actual(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    regimes = _write_spatial_regimes(
        tmp_path / "regional_spatial_regimes.csv",
        source_file_sha256=_sha256_file(panel),
        feature_year=2022,
    )

    result = build_regional_annual_forecast(
        regional_incidence_path=panel,
        population_path=_write_population(tmp_path / "population.csv"),
        regional_spatial_regimes_path=regimes,
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
        shrinkage_strength=2.0,
    )

    spatial_regime = next(
        row
        for row in result.predictions
        if row.model_name == "empirical_bayes_spatial_regime_incidence"
        and row.county_fips == "24001"
    )
    assert spatial_regime.predicted_incidence_per_100k == 67.5
    assert spatial_regime.predicted_incidence_per_100k != 999.0
    assert spatial_regime.model_family == "empirical_bayes_spatial_regime"
    assert spatial_regime.feature_profile == "localized_spatial_regime_shrinkage"
    assert "localized_spatial_regime_feature" in (
        spatial_regime.model_feature_quality_flags
    )
    assert "forecast_safe_prior_history_spatial_regime" in (
        spatial_regime.model_feature_quality_flags
    )
    assert "not_public_default" in spatial_regime.model_feature_quality_flags
    assert result.run.regional_spatial_regimes_path == str(regimes)
    assert len(result.run.regional_spatial_regimes_sha256 or "") == 64
    assert result.run.regional_spatial_regime_feature_year == 2022
    assert "empirical_bayes_spatial_regime_incidence" in result.run.model_names


def test_regional_annual_forecast_rejects_spatial_regime_source_mismatch(
    tmp_path: Path,
) -> None:
    regimes = _write_spatial_regimes(
        tmp_path / "regional_spatial_regimes.csv",
        source_file_sha256="not_the_incidence_panel_hash",
    )

    with pytest.raises(RegionalAnnualForecastInputError, match="source_file_sha256"):
        build_regional_annual_forecast(
            regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
            population_path=_write_population(tmp_path / "population.csv"),
            regional_spatial_regimes_path=regimes,
            target_year=2023,
            forecast_origin_year=2021,
            min_train_years=2,
            lookback_years=2,
        )


def test_regional_annual_forecast_rejects_future_spatial_regime_feature_year(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    regimes = _write_spatial_regimes(
        tmp_path / "regional_spatial_regimes.csv",
        source_file_sha256=_sha256_file(panel),
        feature_year=2023,
    )

    with pytest.raises(
        RegionalAnnualForecastInputError,
        match="regional_spatial_regime_feature_year",
    ):
        build_regional_annual_forecast(
            regional_incidence_path=panel,
            population_path=_write_population(tmp_path / "population.csv"),
            regional_spatial_regimes_path=regimes,
            regional_spatial_regime_feature_year=2023,
            target_year=2023,
            forecast_origin_year=2021,
            min_train_years=2,
            lookback_years=2,
        )


def test_regional_annual_forecast_rejects_empty_spatial_regime_feature_year(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    regimes = _write_spatial_regimes(
        tmp_path / "regional_spatial_regimes.csv",
        source_file_sha256=_sha256_file(panel),
        feature_year=2020,
    )

    with pytest.raises(
        RegionalAnnualForecastInputError,
        match="no regional spatial regime rows for feature year 2022",
    ):
        build_regional_annual_forecast(
            regional_incidence_path=panel,
            population_path=_write_population(tmp_path / "population.csv"),
            regional_spatial_regimes_path=regimes,
            target_year=2023,
            forecast_origin_year=2021,
            min_train_years=2,
            lookback_years=2,
        )


def test_build_regional_annual_forecast_requires_county_depth_and_origin_row(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        sparse_county=True,
        stale_county=True,
    )
    population = _write_population(
        tmp_path / "population.csv",
        extra_counties=["24005", "24009"],
    )

    result = build_regional_annual_forecast(
        regional_incidence_path=panel,
        population_path=population,
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    assert {row.county_fips for row in result.predictions} == {
        "24001",
        "24003",
        "42001",
        "42003",
    }
    assert result.run.n_forecast_counties == 4


def test_build_regional_annual_forecast_requires_future_target_year(
    tmp_path: Path,
) -> None:
    with pytest.raises(RegionalAnnualForecastInputError, match="target-year"):
        build_regional_annual_forecast(
            regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2021,
            forecast_origin_year=2021,
        )


def test_build_regional_annual_forecast_rejects_unknown_update_mode(
    tmp_path: Path,
) -> None:
    with pytest.raises(RegionalAnnualForecastInputError, match="update_mode"):
        build_regional_annual_forecast(
            regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2023,
            forecast_origin_year=2021,
            min_train_years=2,
            lookback_years=2,
            update_mode="post_update",
        )


def test_build_regional_annual_forecast_rejects_nonfinite_incidence(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        override_incidence="NaN",
    )

    with pytest.raises(
        RegionalAnnualForecastInputError,
        match="incidence_per_100k must be finite",
    ):
        build_regional_annual_forecast(
            regional_incidence_path=panel,
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2023,
        )


def test_build_regional_annual_forecast_rejects_blank_target_population(
    tmp_path: Path,
) -> None:
    population = _write_population(
        tmp_path / "population.csv",
        override_population="",
    )

    with pytest.raises(
        RegionalAnnualForecastInputError,
        match="population must be an integer",
    ):
        build_regional_annual_forecast(
            regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
            population_path=population,
            target_year=2023,
        )


def test_build_regional_annual_forecast_rejects_fractional_required_integer(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        override_total_cases="1.5",
    )

    with pytest.raises(
        RegionalAnnualForecastInputError,
        match="total_cases must be an integer",
    ):
        build_regional_annual_forecast(
            regional_incidence_path=panel,
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2023,
        )


def test_build_regional_annual_forecast_preserves_2026_denominator_projection_flags(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        population_path=_write_population(
            tmp_path / "population.csv",
            target_year="2026",
            projection_flags=True,
        ),
        target_year=2026,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    flags = result.predictions[0].forecast_assumption_flags
    assert "forecast_denominator" in flags
    assert "no_official_2026_census_denominator" in flags


def test_build_regional_annual_forecast_rejects_no_usable_origin_incidence(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv", all_incidence_missing=True)

    with pytest.raises(RegionalAnnualForecastInputError, match="no usable incidence"):
        build_regional_annual_forecast(
            regional_incidence_path=panel,
            population_path=_write_population(tmp_path / "population.csv"),
            target_year=2023,
        )


def test_build_regional_annual_forecast_rejects_zero_forecast_rows(
    tmp_path: Path,
) -> None:
    population = _write_population(
        tmp_path / "population.csv",
        target_year="2024",
        unmatched_counties=True,
    )

    with pytest.raises(RegionalAnnualForecastInputError, match="no forecast rows"):
        build_regional_annual_forecast(
            regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
            population_path=population,
            target_year=2024,
            forecast_origin_year=2021,
            min_train_years=2,
            lookback_years=2,
        )


def test_write_regional_annual_forecast_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_annual_forecast(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        population_path=_write_population(tmp_path / "population.csv"),
        target_year=2023,
        forecast_origin_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    outputs = write_regional_annual_forecast_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_ANNUAL_FORECAST_RUN_COLUMNS
    with outputs.predictions_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_ANNUAL_FORECAST_PREDICTION_COLUMNS
    assert outputs.runs_path.name == "regional_annual_forecast_runs.csv"
    assert outputs.predictions_path.name == "regional_annual_forecast_predictions.csv"


def _write_single_county_incidence_panel(path: Path, values: list[int]) -> Path:
    rows = []
    for offset, incidence in enumerate(values):
        rows.append(
            _incidence_row(
                "24",
                "MD",
                "Maryland",
                "24001",
                "Allegany County",
                str(2018 + offset),
                str(incidence),
                str(float(incidence)),
                (
                    "regional_incidence_diagnostic,"
                    "reported_cases_not_stable_true_incidence"
                ),
            )
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_spatial_regimes(
    path: Path,
    *,
    source_file_sha256: str,
    feature_year: int = 2022,
) -> Path:
    rows = []
    for county_fips, regime_mean in {
        "24001": 100,
        "24003": 10,
        "42001": 20,
        "42003": 15,
    }.items():
        rows.append(
            {
                "source_file_sha256": source_file_sha256,
                "regional_adjacency_sha256": "adjacency123",
                "county_fips": county_fips,
                "year": str(feature_year),
                "spatial_regime_id": f"{feature_year}_regime_{county_fips}",
                "feature_regime_trailing_mean_incidence_per_100k": str(regime_mean),
                "diagnostic_actual_regime_incidence_per_100k": "999",
                "model_feature_quality_flags": (
                    "localized_spatial_regime_feature,"
                    "forecast_safe_prior_history_spatial_regime,"
                    "not_public_default"
                ),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_incidence_panel(
    path: Path,
    *,
    sparse_county: bool = False,
    stale_county: bool = False,
    all_incidence_missing: bool = False,
    override_incidence: str | None = None,
    override_total_cases: str | None = None,
    partial_overlay_year: bool = False,
    high_coverage_partial_overlay_year: bool = False,
    extra_full_county: bool = False,
    obsolete_extra_county: bool = False,
) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [10, 20, 30, 40],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [30, 20, 10, 0],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [5, 10, 20, 30],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [15, 10, 0, 10],
    }
    if extra_full_county:
        series[("24", "MD", "Maryland", "24005", "County 24005")] = [6, 7, 8, 9]
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, incidence in enumerate(values):
            year = 2018 + offset
            rows.append(
                _incidence_row(
                    state_fips,
                    state_abbr,
                    state_name,
                    county_fips,
                    county_name,
                    str(year),
                    override_total_cases
                    if override_total_cases is not None and not rows
                    else str(incidence),
                    override_incidence
                    if override_incidence is not None and not rows
                    else "" if all_incidence_missing else str(float(incidence)),
                    (
                        "regional_incidence_diagnostic,"
                        "reported_cases_not_stable_true_incidence"
                    ),
                )
            )
    if sparse_county:
        rows.append(
            _incidence_row(
                "24",
                "MD",
                "Maryland",
                "24005",
                "County 24005",
                "2021",
                "12",
                "12.0",
                "regional_incidence_diagnostic",
            )
        )
    if obsolete_extra_county:
        rows.append(
            _incidence_row(
                "51",
                "VA",
                "Virginia",
                "51515",
                "Obsolete city",
                "2019",
                "1",
                "1.0",
                "regional_incidence_diagnostic",
            )
        )
    if stale_county:
        for year, incidence in [(2019, 7), (2020, 9)]:
            rows.append(
                _incidence_row(
                    "24",
                    "MD",
                    "Maryland",
                    "24009",
                    "County 24009",
                    str(year),
                    str(incidence),
                    str(float(incidence)),
                    "regional_incidence_diagnostic",
                )
            )
    if partial_overlay_year:
        rows.append(
            _incidence_row(
                "42",
                "PA",
                "Pennsylvania",
                "42001",
                "Adams County",
                "2022",
                "128",
                "119.9",
                (
                    "regional_incidence_diagnostic,"
                    "state_source_not_cdc_public_use"
                ),
            )
        )
    if high_coverage_partial_overlay_year:
        for county_fips, incidence in [
            ("24001", 41),
            ("24003", 8),
            ("42001", 128),
            ("42003", 12),
        ]:
            state_fips = "42" if county_fips.startswith("42") else "24"
            state_abbr = "PA" if state_fips == "42" else "MD"
            state_name = "Pennsylvania" if state_fips == "42" else "Maryland"
            county_name = (
                "Adams County"
                if county_fips == "42001"
                else "Allegheny County"
                if county_fips == "42003"
                else f"County {county_fips}"
            )
            rows.append(
                _incidence_row(
                    state_fips,
                    state_abbr,
                    state_name,
                    county_fips,
                    county_name,
                    "2022",
                    str(incidence),
                    str(float(incidence)),
                    (
                        "regional_incidence_diagnostic,"
                        "state_source_not_cdc_public_use"
                    ),
                )
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _incidence_row(
    state_fips: str,
    state_abbr: str,
    state_name: str,
    county_fips: str,
    county_name: str,
    year: str,
    total_cases: str,
    incidence: str,
    feature_quality_flags: str,
) -> dict[str, str]:
    return {
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "year": year,
        "total_cases": total_cases,
        "population": "100000",
        "incidence_per_100k": incidence,
        "diagnostic_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_percentile": "",
        "diagnostic_midatlantic_incidence_tier": "",
        "diagnostic_prior_year_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_rank_change": "",
        "lyme_panel_sha256": "lyme123",
        "population_panel_sha256": "pop123",
        "feature_quality_flags": feature_quality_flags,
    }


def _write_population(
    path: Path,
    *,
    extra_counties: list[str] | None = None,
    target_year: str = "2023",
    unmatched_counties: bool = False,
    override_population: str | None = None,
    projection_flags: bool = False,
) -> Path:
    population_counties = (
        [("24", "MD", "Maryland", "24999", "Unmatched County", "110000")]
        if unmatched_counties
        else [
            ("24", "MD", "Maryland", "24001", "Allegany County", "110000"),
            ("24", "MD", "Maryland", "24003", "Anne Arundel County", "90000"),
            ("42", "PA", "Pennsylvania", "42001", "Adams County", "100000"),
            ("42", "PA", "Pennsylvania", "42003", "Allegheny County", "120000"),
        ]
    )
    rows = [
        _population_row(
            *values[:5],
            override_population if override_population is not None and index == 0 else values[5],
            target_year=target_year,
            projection_flags=projection_flags,
        )
        for index, values in enumerate(population_counties)
    ]
    for county_fips in extra_counties or []:
        rows.append(
            _population_row(
                "24",
                "MD",
                "Maryland",
                county_fips,
                f"County {county_fips}",
                "50000",
                target_year=target_year,
                projection_flags=projection_flags,
            )
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _population_row(
    state_fips: str,
    state_abbr: str,
    state_name: str,
    county_fips: str,
    county_name: str,
    population: str,
    *,
    target_year: str = "2023",
    projection_flags: bool = False,
) -> dict[str, str]:
    flags = [
        "regional_population_denominator",
        "simple_linear_population_projection",
        f"no_official_{target_year}_census_denominator",
    ]
    if projection_flags:
        flags.append("forecast_denominator")
    return {
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "year": target_year,
        "population": population,
        "source_id": "regional_population_linear_projection",
        "census_dataset": "projection",
        "vintage": "2022",
        "source_url_hash": "hash",
        "feature_quality_flags": ",".join(flags),
    }
