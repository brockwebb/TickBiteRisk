from pathlib import Path

from tickbiterisk.etl.lyme import parse_cdc_lyme_public_use


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
