from pathlib import Path

from tickbiterisk.etl.lyme import (
    _frequency_to_int,
    parse_cdc_county_dashboard,
    parse_cdc_lyme_geodata,
    parse_cdc_lyme_public_use,
)


def test_frequency_to_int_maps_nan_token_to_zero() -> None:
    assert _frequency_to_int("NaN") == 0


def test_parse_cdc_lyme_public_use_filters_maryland_counties() -> None:
    rows = parse_cdc_lyme_public_use(
        Path("tests/fixtures/lyme_public_use_2022_2023_mini.csv"),
        source_id="cdc_lyme_public_2022_2023",
    )
    assert {(row.county_fips, row.year) for row in rows} == {
        ("24003", 2022),
        ("24005", 2022),
        ("24003", 2023),
    }


def test_parse_cdc_lyme_public_use_sums_case_statuses() -> None:
    rows = parse_cdc_lyme_public_use(
        Path("tests/fixtures/lyme_public_use_2022_2023_mini.csv"),
        source_id="cdc_lyme_public_2022_2023",
    )
    anne_2022 = next(row for row in rows if row.county_fips == "24003" and row.year == 2022)
    assert anne_2022.confirmed_cases is None
    assert anne_2022.probable_cases == 127
    assert anne_2022.total_cases == 127
    assert anne_2022.source_id == "cdc_lyme_public_2022_2023"


def test_parse_cdc_county_dashboard_handles_latin1_style_columns() -> None:
    rows = parse_cdc_county_dashboard(
        Path("tests/fixtures/ld_case_counts_by_county_mini.csv"),
        source_id="cdc_lyme_county_dashboard_2023",
    )
    anne = next(row for row in rows if row.county_fips == "24003" and row.year == 2022)
    assert anne.total_cases == 127
    assert anne.confirmed_cases is None
    assert anne.probable_cases is None


def test_parse_cdc_lyme_geodata_reads_confirmed_probable_components() -> None:
    rows = parse_cdc_lyme_geodata(
        Path("tests/fixtures/lyme_geodata_mini.csv"),
        source_id="cdc_lyme_county_geodata_2000_2021",
    )
    anne = next(row for row in rows if row.county_fips == "24003" and row.year == 2020)
    assert anne.confirmed_cases == 53
    assert anne.probable_cases == 18
    assert anne.total_cases == 71
