import csv
from pathlib import Path

from tickbiterisk.etl.regional_hotspots import build_midatlantic_hotspot_diagnostics
from tickbiterisk.etl.regional_hotspots_build import (
    REGIONAL_HOTSPOT_COUNTY_YEAR_COLUMNS,
    REGIONAL_HOTSPOT_SUMMARY_COLUMNS,
    write_regional_hotspot_outputs,
)


def test_build_midatlantic_hotspot_diagnostics_tracks_rank_tiers_and_transitions(
    tmp_path: Path,
) -> None:
    panel = _write_hotspot_panel(tmp_path / "regional.csv")

    result = build_midatlantic_hotspot_diagnostics(
        panel,
        source_panel_sha256="abc123",
    )

    c_2022 = next(
        row
        for row in result.county_year_rows
        if row.county_fips == "42001" and row.year == 2022
    )
    assert c_2022.diagnostic_midatlantic_total_cases == 280
    assert c_2022.diagnostic_state_total_cases == 150
    assert c_2022.diagnostic_midatlantic_case_share == 0.464286
    assert c_2022.diagnostic_state_case_share == 0.866667
    assert c_2022.diagnostic_midatlantic_rank_cases == 1
    assert c_2022.diagnostic_state_rank_cases == 1
    assert c_2022.diagnostic_midatlantic_hotspot_percentile == 1.0
    assert c_2022.diagnostic_midatlantic_hotspot_tier == "top_decile"
    assert c_2022.diagnostic_prior_year_midatlantic_rank_cases == 3
    assert c_2022.diagnostic_midatlantic_rank_change == 2
    assert c_2022.diagnostic_prior_year_midatlantic_hotspot_tier == "lower_half"
    assert c_2022.diagnostic_year_over_year_case_change == 100
    assert c_2022.diagnostic_prior_3yr_top_quintile_count == 0
    assert "diagnostic_same_year_not_forecast_feature" in c_2022.feature_quality_flags

    summary_2022 = next(row for row in result.summary_rows if row.year == 2022)
    assert summary_2022.diagnostic_top_decile_count == 1
    assert summary_2022.diagnostic_top_quintile_count == 1
    assert summary_2022.diagnostic_persistent_top_quintile_count == 0
    assert summary_2022.diagnostic_new_top_quintile_count == 1
    assert summary_2022.diagnostic_exited_top_quintile_count == 1


def test_build_midatlantic_hotspot_diagnostics_does_not_count_first_year_as_new(
    tmp_path: Path,
) -> None:
    result = build_midatlantic_hotspot_diagnostics(
        _write_hotspot_panel(tmp_path / "regional.csv"),
        source_panel_sha256="abc123",
    )

    summary_2020 = next(row for row in result.summary_rows if row.year == 2020)
    assert summary_2020.diagnostic_top_quintile_count == 1
    assert summary_2020.diagnostic_persistent_top_quintile_count is None
    assert summary_2020.diagnostic_new_top_quintile_count is None
    assert summary_2020.diagnostic_exited_top_quintile_count is None


def test_write_regional_hotspot_outputs_uses_stable_schemas(tmp_path: Path) -> None:
    result = build_midatlantic_hotspot_diagnostics(
        _write_hotspot_panel(tmp_path / "regional.csv"),
        source_panel_sha256="abc123",
    )

    outputs = write_regional_hotspot_outputs(result, tmp_path / "out")

    with outputs.county_year_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_HOTSPOT_COUNTY_YEAR_COLUMNS
    with outputs.summary_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REGIONAL_HOTSPOT_SUMMARY_COLUMNS


def _write_hotspot_panel(path: Path) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): [100, 80, 70],
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): [50, 120, 60],
        ("42", "PA", "Pennsylvania", "42001", "Adams County"): [20, 30, 130],
        ("42", "PA", "Pennsylvania", "42003", "Allegheny County"): [0, 10, 20],
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
