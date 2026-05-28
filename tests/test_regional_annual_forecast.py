import csv
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
    )

    assert result.run.target_year == 2023
    assert result.run.forecast_origin_year == 2021
    assert result.run.n_training_rows == 8
    assert result.run.n_forecast_counties == 4
    assert result.run.n_forecast_rows == 16
    assert {row.model_name for row in result.predictions} == {
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


def test_build_regional_annual_forecast_defaults_origin_to_latest_input_year(
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


def _write_incidence_panel(
    path: Path,
    *,
    sparse_county: bool = False,
    stale_county: bool = False,
    all_incidence_missing: bool = False,
    override_incidence: str | None = None,
    override_total_cases: str | None = None,
) -> Path:
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
