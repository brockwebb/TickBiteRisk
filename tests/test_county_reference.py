import pandas as pd

from tickbiterisk.etl.county_reference import (
    CENSUS_GAZETTEER_COUNTIES_2024_URL,
    parse_census_gazetteer_counties,
)
from tickbiterisk.etl.county_reference_build import write_county_reference_output


GAZETTEER_SAMPLE = """USPS\tGEOID\tANSICODE\tNAME\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG   
MD\t24001\t00595728\tAllegany County\t1099438345\t14231703\t424.495\t5.495\t39.612313\t-78.703104
MD\t24003\t01710958\tAnne Arundel County\t1074169609\t448789171\t414.739\t173.278\t38.991617\t-76.560894
VA\t51001\t01480101\tAccomack County\t1164972191\t2229591973\t449.798\t860.850\t37.765944\t-75.757807
MD\t24510\t00596156\tBaltimore city\t209650655\t28760602\t80.946\t11.104\t39.300032\t-76.610476
"""


def test_parse_census_gazetteer_counties_filters_maryland_and_preserves_area() -> None:
    rows = parse_census_gazetteer_counties(
        GAZETTEER_SAMPLE,
        source_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
    )

    assert [row.county_fips for row in rows] == ["24001", "24003", "24510"]
    anne_arundel = rows[1]
    assert anne_arundel.state_fips == "24"
    assert anne_arundel.state == "MD"
    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.aland_sqmi == 414.739
    assert anne_arundel.awater_sqmi == 173.278
    assert anne_arundel.intptlat == 38.991617
    assert anne_arundel.intptlon == -76.560894
    assert anne_arundel.geography_source == "Census Gazetteer 2024 counties"
    assert len(anne_arundel.source_url_hash) == 64


def test_write_county_reference_output_creates_stable_csv(tmp_path) -> None:
    rows = parse_census_gazetteer_counties(
        GAZETTEER_SAMPLE,
        source_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
    )

    output = write_county_reference_output(rows, tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str, "state_fips": str})
    assert output.name == "county_reference.csv"
    assert list(df.columns) == [
        "county_fips",
        "state_fips",
        "state",
        "county_name",
        "aland_sqmi",
        "awater_sqmi",
        "intptlat",
        "intptlon",
        "geography_source",
        "source_url_hash",
    ]
    assert list(df["county_fips"]) == ["24001", "24003", "24510"]
