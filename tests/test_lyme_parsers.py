from pathlib import Path

import pytest

from tickbiterisk.etl.lyme import (
    _frequency_to_int,
    parse_cdc_county_dashboard,
    parse_cdc_lyme_geodata,
    parse_cdc_lyme_public_use,
    parse_mdh_lyme_pdf_text,
)

_GEODATA_HEADER = (
    "STATEFP,COUNTYFP,GEOID,NAME,STUSPS,STATE_NAME,fips,year,"
    "Lyme_Confirmed_Cases,Lyme_Probable_Cases,Lyme_Confirmed_Probable_Cases"
)


def _write_geodata_csv(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "lyme_geodata_edge.csv"
    path.write_text("\n".join([_GEODATA_HEADER, *rows]) + "\n")
    return path


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


def test_parse_cdc_lyme_geodata_dedupes_swapped_components_by_total(
    tmp_path: Path,
) -> None:
    path = _write_geodata_csv(
        tmp_path,
        [
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2020,53,18,71",
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2020,18,53,71",
        ],
    )
    rows = parse_cdc_lyme_geodata(
        path,
        source_id="cdc_lyme_county_geodata_2000_2021",
    )
    anne_2020 = [
        row for row in rows if row.county_fips == "24003" and row.year == 2020
    ]
    assert len(anne_2020) == 1
    assert anne_2020[0].total_cases == 71
    assert anne_2020[0].confirmed_cases is None
    assert anne_2020[0].probable_cases is None


def test_parse_cdc_lyme_geodata_filters_to_2000_2021_source_scope(
    tmp_path: Path,
) -> None:
    path = _write_geodata_csv(
        tmp_path,
        [
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2021,60,21,81",
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2022,61,22,83",
        ],
    )
    rows = parse_cdc_lyme_geodata(
        path,
        source_id="cdc_lyme_county_geodata_2000_2021",
    )
    assert all(row.year <= 2021 for row in rows)


def test_parse_cdc_lyme_geodata_rejects_duplicate_total_disagreement(
    tmp_path: Path,
) -> None:
    path = _write_geodata_csv(
        tmp_path,
        [
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2020,53,18,71",
            "24,003,24003,Anne Arundel,MD,Maryland,24003,2020,53,19,72",
        ],
    )

    with pytest.raises(ValueError, match="24003.*2020"):
        parse_cdc_lyme_geodata(
            path,
            source_id="cdc_lyme_county_geodata_2000_2021",
        )


def test_parse_mdh_lyme_pdf_text_reads_2024_probable_only_table() -> None:
    text = """Lyme Disease in Maryland by Jurisdiction 2013-2024
2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024
JURISDICTION *Confirmed and Probable ^Probable only 2024 Incidence
Allegany 33 51 80 86 87 85 71 51 84 108 153 143 213.1
Anne Arundel 95 117 107 178 127 90 110 70 153 126 161 203 33.7
Baltimore City 17 30 43 39 33 29 41 11 24 99 54 127 22.4
Baltimore 144 199 218 191 212 176 138 52 81 279 413 443 52.0
Prince George's 8 2 47 59 130 16 22 0 0 49 80 152 15.7
Statewide total 1198 1373 1727 1867 1887 1384 1420 838 918 2036 2463 3093
^ Change in case definition where Confirmed classification eliminated, and only Probable are reported.
"""

    rows = parse_mdh_lyme_pdf_text(text, source_id="mdh_lyme_2013_2024_pdf")

    assert len(rows) == 5 * 12
    anne_2024 = next(
        row for row in rows if row.county_fips == "24003" and row.year == 2024
    )
    assert anne_2024.total_cases == 203
    assert anne_2024.confirmed_cases is None
    assert anne_2024.probable_cases == 203
    baltimore_county = next(
        row for row in rows if row.county_fips == "24005" and row.year == 2024
    )
    assert baltimore_county.total_cases == 443
    baltimore_city = next(
        row for row in rows if row.county_fips == "24510" and row.year == 2024
    )
    assert baltimore_city.total_cases == 127
    prince_georges = next(
        row for row in rows if row.county_fips == "24033" and row.year == 2024
    )
    assert prince_georges.total_cases == 152
    assert all(row.source_id == "mdh_lyme_2013_2024_pdf" for row in rows)
