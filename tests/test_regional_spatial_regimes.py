import csv
from pathlib import Path

from tickbiterisk.modeling.regional_spatial_regimes import (
    build_regional_spatial_regimes,
)
from tickbiterisk.modeling.regional_spatial_regimes_build import (
    REGIONAL_SPATIAL_REGIME_COUNTY_YEAR_COLUMNS,
    REGIONAL_SPATIAL_REGIME_RUN_COLUMNS,
    REGIONAL_SPATIAL_REGIME_SUMMARY_COLUMNS,
    write_regional_spatial_regime_outputs,
)


def test_build_regional_spatial_regimes_groups_adjacent_similar_counties(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = build_regional_spatial_regimes(
        regional_incidence_path=panel,
        regional_adjacency_path=adjacency,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
        max_prior_mean_difference=25.0,
        max_prior_year_difference=25.0,
        max_trend_difference=10.0,
    )

    assignments = {row.county_fips: row for row in result.county_year_rows}
    assert assignments["24001"].spatial_regime_id == (
        assignments["42001"].spatial_regime_id
    )
    assert assignments["24001"].spatial_regime_id != (
        assignments["24003"].spatial_regime_id
    )
    assert assignments["24003"].spatial_regime_id == (
        assignments["51810"].spatial_regime_id
    )
    assert assignments["24001"].spatial_regime_member_count == 2
    assert assignments["24001"].spatial_regime_neighbor_count == 1
    assert assignments["24001"].feature_county_prior_mean_incidence_per_100k == 115.0
    assert assignments["24001"].feature_county_prior_year_incidence_per_100k == 120.0
    assert assignments["24001"].feature_county_prior_trend_incidence_per_100k == 10.0
    assert assignments["24001"].feature_regime_trailing_mean_incidence_per_100k == 117.5
    assert assignments["24001"].feature_regime_prior_year_mean_incidence_per_100k == 122.5
    assert assignments["24001"].train_start_year == 2019
    assert assignments["24001"].train_end_year == 2020
    assert assignments["24001"].train_year_count == 2
    assert "localized_spatial_regime_feature" in (
        assignments["24001"].model_feature_quality_flags
    )
    assert "forecast_safe_prior_history_spatial_regime" in (
        assignments["24001"].model_feature_quality_flags
    )
    assert "not_public_default" in assignments["24001"].model_feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in (
        assignments["24001"].comparison_assumption_flags
    )

    high_summary = next(
        row
        for row in result.summary_rows
        if row.spatial_regime_id == assignments["24001"].spatial_regime_id
    )
    assert high_summary.n_counties == 2
    assert high_summary.county_fips_list == "24001;42001"
    assert high_summary.feature_regime_prior_year_mean_incidence_per_100k == 122.5
    assert high_summary.diagnostic_actual_regime_incidence_per_100k == 132.5
    assert result.run.n_county_years == 4
    assert result.run.n_summary_rows == 2
    assert result.run.regime_method == "adjacency_prior_history_similarity"


def test_regional_spatial_regime_diagnostics_use_population_weighted_incidence(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        population_by_county={"24001": 100000, "42001": 300000},
    )
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = build_regional_spatial_regimes(
        regional_incidence_path=panel,
        regional_adjacency_path=adjacency,
        start_year=2021,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    high_summary = next(
        row
        for row in result.summary_rows
        if row.county_fips_list == "24001;42001"
    )
    assert high_summary.diagnostic_actual_regime_cases == 535
    assert high_summary.diagnostic_actual_regime_population == 400000
    assert high_summary.diagnostic_actual_regime_incidence_per_100k == 133.75


def test_regional_spatial_regime_neighbor_count_uses_direct_regime_edges(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        extra_county=("42003", "Allegheny County", [106, 116, 126, 136]),
    )
    adjacency = _write_adjacency(
        tmp_path / "adjacency.csv",
        extra_edges=[("42001", "42003"), ("42003", "42001")],
    )

    result = build_regional_spatial_regimes(
        regional_incidence_path=panel,
        regional_adjacency_path=adjacency,
        start_year=2021,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    assignments = {row.county_fips: row for row in result.county_year_rows}
    assert assignments["24001"].spatial_regime_member_count == 3
    assert assignments["24001"].spatial_regime_neighbor_count == 1
    assert assignments["42001"].spatial_regime_neighbor_count == 2
    assert assignments["42003"].spatial_regime_neighbor_count == 1


def test_regional_spatial_regime_features_include_neighbors_without_target_year(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(
        tmp_path / "incidence.csv",
        skip_target_counties={"42001"},
    )
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = build_regional_spatial_regimes(
        regional_incidence_path=panel,
        regional_adjacency_path=adjacency,
        start_year=2021,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    assignments = {row.county_fips: row for row in result.county_year_rows}
    assert assignments["24001"].spatial_regime_id == (
        assignments["42001"].spatial_regime_id
    )
    assert assignments["24001"].spatial_regime_member_count == 2
    assert assignments["24001"].feature_regime_trailing_mean_incidence_per_100k == 117.5
    assert assignments["42001"].diagnostic_actual_incidence_per_100k is None
    assert assignments["42001"].diagnostic_actual_cases is None

    high_summary = next(
        row
        for row in result.summary_rows
        if row.spatial_regime_id == assignments["24001"].spatial_regime_id
    )
    assert high_summary.county_fips_list == "24001;42001"
    assert high_summary.diagnostic_actual_regime_incidence_per_100k is None
    assert high_summary.diagnostic_actual_regime_cases is None


def test_build_regional_spatial_regimes_ignores_future_outliers(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv", future_outlier=True)
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = build_regional_spatial_regimes(
        regional_incidence_path=panel,
        regional_adjacency_path=adjacency,
        start_year=2021,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    allegany = next(row for row in result.county_year_rows if row.county_fips == "24001")
    assert allegany.feature_county_prior_mean_incidence_per_100k == 115.0
    assert allegany.feature_county_prior_year_incidence_per_100k == 120.0
    assert allegany.train_end_year == 2020


def test_write_regional_spatial_regime_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_spatial_regimes(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        regional_adjacency_path=_write_adjacency(tmp_path / "adjacency.csv"),
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
    )

    outputs = write_regional_spatial_regime_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_SPATIAL_REGIME_RUN_COLUMNS
    with outputs.county_year_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_SPATIAL_REGIME_COUNTY_YEAR_COLUMNS
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_SPATIAL_REGIME_SUMMARY_COLUMNS


def _write_incidence_panel(
    path: Path,
    *,
    future_outlier: bool = False,
    population_by_county: dict[str, int] | None = None,
    extra_county: tuple[str, str, list[int]] | None = None,
    skip_target_counties: set[str] | None = None,
) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [100, 110, 120, 130],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [105, 115, 125, 135],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [10, 12, 11, 12],
        ("51", "VA", "Virginia", "51810", "Virginia Beach city"): [8, 9, 10, 11],
    }
    if extra_county is not None:
        county_fips, county_name, values = extra_county
        series[("42", "PA", "Pennsylvania", county_fips, county_name)] = values
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, incidence in enumerate(values):
            year = 2018 + offset
            if skip_target_counties is not None and (
                county_fips in skip_target_counties and year == 2021
            ):
                continue
            population = (
                100000
                if population_by_county is None
                else population_by_county.get(county_fips, 100000)
            )
            rows.append(
                _incidence_row(
                    state_fips=state_fips,
                    state_abbr=state_abbr,
                    state_name=state_name,
                    county_fips=county_fips,
                    county_name=county_name,
                    year=year,
                    incidence=incidence,
                    population=population,
                )
            )
    if future_outlier:
        rows.append(
            _incidence_row(
                state_fips="24",
                state_abbr="MD",
                state_name="Maryland",
                county_fips="24001",
                county_name="Allegany County",
                year=2022,
                incidence=9999,
                population=100000,
            )
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _incidence_row(
    *,
    state_fips: str,
    state_abbr: str,
    state_name: str,
    county_fips: str,
    county_name: str,
    year: int,
    incidence: int,
    population: int,
) -> dict[str, str]:
    total_cases = round(incidence * population / 100000)
    return {
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "total_cases": str(total_cases),
        "population": str(population),
        "incidence_per_100k": str(incidence),
        "feature_quality_flags": (
            "regional_incidence_diagnostic,"
            "reported_cases_not_stable_true_incidence"
        ),
    }


def _write_adjacency(
    path: Path,
    *,
    extra_edges: list[tuple[str, str]] | None = None,
) -> Path:
    rows = [
        ("24001", "42001"),
        ("42001", "24001"),
        ("24001", "24003"),
        ("24003", "24001"),
        ("24003", "51810"),
        ("51810", "24003"),
    ]
    if extra_edges is not None:
        rows.extend(extra_edges)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "county_fips",
                "neighbor_county_fips",
            ],
        )
        writer.writeheader()
        for county_fips, neighbor_county_fips in rows:
            writer.writerow(
                {
                    "county_fips": county_fips,
                    "neighbor_county_fips": neighbor_county_fips,
                }
            )
    return path
