import csv
from pathlib import Path

from tickbiterisk.etl.regional_signals import build_midatlantic_regional_signals
from tickbiterisk.etl.regional_signals_build import write_regional_signals_output


def test_build_midatlantic_regional_signals_adds_capacity_and_lagged_shares(
    tmp_path: Path,
) -> None:
    panel_path = tmp_path / "midatlantic_lyme_county_year.csv"
    _write_panel(panel_path)

    rows = build_midatlantic_regional_signals(
        panel_path,
        source_panel_sha256="abc123",
    )

    anne_2002 = next(row for row in rows if row.county_fips == "24003" and row.year == 2002)
    assert anne_2002.diagnostic_state_total_cases == 20
    assert anne_2002.diagnostic_midatlantic_total_cases == 30
    assert anne_2002.diagnostic_county_share_of_state_cases == 1.0
    assert anne_2002.diagnostic_county_share_of_midatlantic_cases == 0.666667
    assert anne_2002.feature_prior_year_total_cases == 10
    assert anne_2002.feature_prior_year_county_share_of_state_cases == 0.666667
    assert anne_2002.feature_prior_year_county_share_of_midatlantic_cases == 0.5
    assert anne_2002.feature_prior_year_state_total_cases == 15
    assert anne_2002.feature_prior_year_midatlantic_total_cases == 20
    assert anne_2002.feature_trailing_5yr_midatlantic_total_min == 20
    assert anne_2002.feature_trailing_5yr_midatlantic_total_mean == 20.0
    assert anne_2002.feature_trailing_5yr_midatlantic_total_max == 20
    assert anne_2002.diagnostic_midatlantic_total_within_trailing_5yr_band is False
    assert anne_2002.source_panel_sha256 == "abc123"
    assert anne_2002.feature_quality_flags == (
        "regional_signal_candidate,reported_cases_not_stable_true_incidence,"
        "case_count_not_population_rate,same_year_diagnostics_not_forecast_features,"
        "partial_trailing_regional_history,regional_expansion_stress_test"
    )

    anne_2001 = next(row for row in rows if row.county_fips == "24003" and row.year == 2001)
    assert anne_2001.feature_prior_year_total_cases is None
    assert anne_2001.feature_prior_year_midatlantic_total_cases is None
    assert anne_2001.feature_trailing_5yr_midatlantic_total_min is None
    assert anne_2001.diagnostic_midatlantic_total_within_trailing_5yr_band is None
    assert "insufficient_prior_year_history" in anne_2001.feature_quality_flags
    assert "insufficient_trailing_regional_history" in anne_2001.feature_quality_flags


def test_write_regional_signals_output_uses_stable_schema(tmp_path: Path) -> None:
    panel_path = tmp_path / "midatlantic_lyme_county_year.csv"
    _write_panel(panel_path)
    rows = build_midatlantic_regional_signals(
        panel_path,
        source_panel_sha256="abc123",
    )

    output_path = write_regional_signals_output(rows, tmp_path / "out")

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert reader.fieldnames[:7] == [
            "state_fips",
            "state_abbr",
            "state_name",
            "county_fips",
            "county_name",
            "year",
            "total_cases",
        ]
        first = next(reader)
    assert output_path.name == "midatlantic_regional_signals.csv"
    assert first["county_fips"] == "24003"
    assert first["feature_prior_year_total_cases"] == ""
    assert first["source_panel_sha256"] == "abc123"


def _write_panel(path: Path) -> None:
    rows = [
        ["24", "MD", "Maryland", "24003", "Anne Arundel County", "2001", "10"],
        ["24", "MD", "Maryland", "24005", "Baltimore County", "2001", "5"],
        ["42", "PA", "Pennsylvania", "42001", "Adams County", "2001", "5"],
        ["24", "MD", "Maryland", "24003", "Anne Arundel County", "2002", "20"],
        ["24", "MD", "Maryland", "24005", "Baltimore County", "2002", "0"],
        ["42", "PA", "Pennsylvania", "42001", "Adams County", "2002", "10"],
        ["24", "MD", "Maryland", "24003", "Anne Arundel County", "2003", "12"],
        ["24", "MD", "Maryland", "24005", "Baltimore County", "2003", "8"],
        ["42", "PA", "Pennsylvania", "42001", "Adams County", "2003", "10"],
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "state_fips",
                "state_abbr",
                "state_name",
                "county_fips",
                "county_name",
                "year",
                "total_cases",
                "source_id",
                "feature_quality_flags",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    *row,
                    "cdc_lyme_county_dashboard_2023",
                    "regional_expansion_stress_test",
                ]
            )
