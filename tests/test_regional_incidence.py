import csv
from pathlib import Path

from tickbiterisk.etl.regional_incidence import build_midatlantic_incidence_panel
from tickbiterisk.etl.regional_incidence_build import (
    REGIONAL_INCIDENCE_COLUMNS,
    REGIONAL_INCIDENCE_SUMMARY_COLUMNS,
    write_regional_incidence_outputs,
)


def test_build_midatlantic_incidence_panel_adds_rates_and_rank_tiers(
    tmp_path: Path,
) -> None:
    lyme_path = _write_regional_lyme(tmp_path / "lyme.csv")
    population_path = _write_regional_population(tmp_path / "population.csv")

    result = build_midatlantic_incidence_panel(
        regional_lyme_path=lyme_path,
        regional_population_path=population_path,
        lyme_panel_sha256="lyme123",
        population_panel_sha256="pop123",
    )

    c_2022 = next(
        row
        for row in result.county_year_rows
        if row.county_fips == "42001" and row.year == 2022
    )
    assert c_2022.population == 100000
    assert c_2022.incidence_per_100k == 130.0
    assert c_2022.diagnostic_midatlantic_incidence_rank == 1
    assert c_2022.diagnostic_midatlantic_incidence_percentile == 1.0
    assert c_2022.diagnostic_midatlantic_incidence_tier == "top_decile"
    assert c_2022.diagnostic_prior_year_midatlantic_incidence_rank == 3
    assert c_2022.diagnostic_midatlantic_incidence_rank_change == 2
    assert c_2022.lyme_panel_sha256 == "lyme123"
    assert c_2022.population_panel_sha256 == "pop123"

    missing = next(
        row
        for row in result.county_year_rows
        if row.county_fips == "51515" and row.year == 2022
    )
    assert missing.population is None
    assert missing.incidence_per_100k is None
    assert missing.diagnostic_midatlantic_incidence_rank is None
    assert missing.diagnostic_midatlantic_incidence_tier == "population_missing"
    assert "missing_population_denominator" in missing.feature_quality_flags

    summary_2022 = next(row for row in result.summary_rows if row.year == 2022)
    assert summary_2022.n_county_years == 5
    assert summary_2022.n_with_population == 4
    assert summary_2022.n_missing_population == 1
    assert summary_2022.diagnostic_top_quintile_incidence_count == 1
    assert summary_2022.diagnostic_new_top_quintile_incidence_count == 1
    assert summary_2022.diagnostic_exited_top_quintile_incidence_count == 1


def test_write_regional_incidence_outputs_uses_stable_schemas(tmp_path: Path) -> None:
    result = build_midatlantic_incidence_panel(
        regional_lyme_path=_write_regional_lyme(tmp_path / "lyme.csv"),
        regional_population_path=_write_regional_population(tmp_path / "population.csv"),
        lyme_panel_sha256="lyme123",
        population_panel_sha256="pop123",
    )

    outputs = write_regional_incidence_outputs(result, tmp_path / "out")

    with outputs.county_year_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_COLUMNS
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_INCIDENCE_SUMMARY_COLUMNS


def _write_regional_lyme(path: Path) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [100, 80, 70],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [50, 120, 60],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [20, 30, 130],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [0, 10, 20],
        ("51", "VA", "Virginia", "51515", "Bedford city"): [5, 5, 5],
    }
    for key, values in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for offset, cases in enumerate(values):
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(2020 + offset),
                    "total_cases": str(cases),
                    "source_id": "fixture",
                    "feature_quality_flags": "regional_expansion_stress_test",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_regional_population(path: Path) -> Path:
    rows = []
    populations = {
        "24001": 100000,
        "24003": 100000,
        "42001": 100000,
        "42003": 100000,
        "51515": 100000,
    }
    for county_fips, population in populations.items():
        state_fips = county_fips[:2]
        for year in [2020, 2021, 2022]:
            if county_fips == "51515" and year == 2022:
                continue
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": {"24": "MD", "42": "PA", "51": "VA"}[state_fips],
                    "state_name": {
                        "24": "Maryland",
                        "42": "Pennsylvania",
                        "51": "Virginia",
                    }[state_fips],
                    "county_fips": county_fips,
                    "county_name": "fixture",
                    "year": str(year),
                    "population": str(population),
                    "source_id": "fixture",
                    "census_dataset": "fixture",
                    "vintage": "2023",
                    "source_url_hash": "a" * 64,
                    "feature_quality_flags": "regional_population_denominator",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
