import csv
from pathlib import Path

from tickbiterisk.modeling.regional_incidence_clusters import (
    build_regional_incidence_clusters,
)
from tickbiterisk.modeling.regional_incidence_clusters_build import (
    REGIONAL_INCIDENCE_CLUSTER_COUNTY_YEAR_COLUMNS,
    REGIONAL_INCIDENCE_CLUSTER_RUN_COLUMNS,
    REGIONAL_INCIDENCE_CLUSTER_SUMMARY_COLUMNS,
    write_regional_incidence_cluster_outputs,
)


def test_build_regional_incidence_clusters_assigns_prior_history_bands(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")

    result = build_regional_incidence_clusters(
        regional_incidence_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
        n_clusters=2,
    )

    assignments = {row.county_fips: row for row in result.county_year_rows}
    assert assignments["24001"].cluster_rank == 1
    assert assignments["24001"].cluster_label == "low"
    assert assignments["24001"].feature_prior_mean_incidence_per_100k == 6.5
    assert assignments["24001"].train_start_year == 2019
    assert assignments["24001"].train_end_year == 2020
    assert assignments["42003"].cluster_rank == 2
    assert assignments["42003"].cluster_label == "high"
    assert assignments["42003"].feature_prior_mean_incidence_per_100k == 55.0
    assert "reported_cases_not_stable_true_incidence" in (
        assignments["42003"].comparison_assumption_flags
    )

    low_summary = next(
        row
        for row in result.summary_rows
        if row.year == 2021 and row.cluster_rank == 1
    )
    assert low_summary.n_counties == 2
    assert low_summary.feature_prior_cluster_min_incidence_per_100k == 5.5
    assert low_summary.feature_prior_cluster_mean_incidence_per_100k == 6.0
    assert low_summary.feature_prior_cluster_max_incidence_per_100k == 6.5
    assert low_summary.diagnostic_actual_cluster_incidence_per_100k == 7.5
    assert low_summary.diagnostic_actual_cluster_cases == 15
    assert result.run.n_county_years == 4
    assert result.run.n_summary_rows == 2
    assert result.run.clustering_method == "prior_mean_1d_kmeans"


def test_build_regional_incidence_clusters_skips_missing_target_incidence(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv", missing_target=True)

    result = build_regional_incidence_clusters(
        regional_incidence_path=panel,
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
        n_clusters=2,
    )

    assert all(row.county_fips != "42003" for row in result.county_year_rows)
    assert sum(row.n_counties for row in result.summary_rows) == 3


def test_build_regional_incidence_clusters_ignores_future_outliers(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv", future_outlier=True)

    result = build_regional_incidence_clusters(
        regional_incidence_path=panel,
        start_year=2021,
        end_year=2021,
        min_train_years=2,
        lookback_years=2,
        n_clusters=2,
    )

    allegany = next(row for row in result.county_year_rows if row.county_fips == "24001")
    assert allegany.cluster_rank == 1
    assert allegany.feature_prior_mean_incidence_per_100k == 6.5
    assert allegany.feature_prior_max_incidence_per_100k == 7.0
    assert allegany.train_end_year == 2020


def test_write_regional_incidence_cluster_outputs_uses_stable_schemas(
    tmp_path: Path,
) -> None:
    result = build_regional_incidence_clusters(
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        start_year=2021,
        min_train_years=2,
        lookback_years=2,
        n_clusters=2,
    )

    outputs = write_regional_incidence_cluster_outputs(result, tmp_path / "out")

    with outputs.runs_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_CLUSTER_RUN_COLUMNS
    with outputs.county_year_path.open(newline="", encoding="utf-8") as handle:
        assert (
            next(csv.reader(handle))
            == REGIONAL_INCIDENCE_CLUSTER_COUNTY_YEAR_COLUMNS
        )
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_CLUSTER_SUMMARY_COLUMNS


def _write_incidence_panel(
    path: Path,
    *,
    missing_target: bool = False,
    future_outlier: bool = False,
) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [5, 6, 7, 8],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [6, 5, 6, 7],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [50, 55, 60, 65],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [55, 52, 58, 70],
    }
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, incidence in enumerate(values):
            year = 2018 + offset
            rows.append(
                _incidence_row(
                    state_fips=state_fips,
                    state_abbr=state_abbr,
                    state_name=state_name,
                    county_fips=county_fips,
                    county_name=county_name,
                    year=year,
                    incidence=incidence,
                    missing_incidence=(
                        missing_target and county_fips == "42003" and year == 2021
                    ),
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
    missing_incidence: bool = False,
) -> dict[str, str]:
    return {
        "state_fips": state_fips,
        "state_abbr": state_abbr,
        "state_name": state_name,
        "county_fips": county_fips,
        "county_name": county_name,
        "year": str(year),
        "total_cases": str(incidence),
        "population": "100000",
        "incidence_per_100k": "" if missing_incidence else str(incidence),
        "diagnostic_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_percentile": "",
        "diagnostic_midatlantic_incidence_tier": "",
        "diagnostic_prior_year_midatlantic_incidence_rank": "",
        "diagnostic_midatlantic_incidence_rank_change": "",
        "lyme_panel_sha256": "lyme123",
        "population_panel_sha256": "pop123",
        "feature_quality_flags": (
            "regional_incidence_diagnostic,"
            "reported_cases_not_stable_true_incidence"
        ),
    }
