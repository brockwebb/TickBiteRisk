from tickbiterisk.etl.building_permits import (
    build_census_bps_county_annual_url,
    parse_census_bps_county_text,
)


BPS_SAMPLE = """Survey,FIPS,FIPS,Region,Division,County,,1-unit,,,2-units,,,3-4 units,,,5+ units,,,1-unit rep,,,2-units rep,,,3-4 units rep,,, 5+units rep
Date,State,County,Code,Code,Name,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value
 
202412,24,003,3,5,Anne Arundel County                                      ,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000
202412,24,005,3,5,Baltimore County                                         ,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000
202412,51,001,3,5,Accomack County                                          ,10,10,1000000,0,0,0,0,0,0,0,0,0,10,10,1000000,0,0,0,0,0,0,0,0,0
"""


def test_build_census_bps_county_annual_url_uses_december_ytd_file() -> None:
    assert build_census_bps_county_annual_url(2024) == (
        "https://www2.census.gov/econ/bps/County/co2412y.txt"
    )


def test_parse_census_bps_county_text_filters_maryland_and_totals_units() -> None:
    rows = parse_census_bps_county_text(
        BPS_SAMPLE,
        source_url="https://www2.census.gov/econ/bps/County/co2412y.txt",
        source_id="census_bps_county_2024",
    )

    assert len(rows) == 2
    anne_arundel = rows[0]
    assert anne_arundel.county_fips == "24003"
    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.year == 2024
    assert anne_arundel.month == 12
    assert anne_arundel.one_unit_units == 1150
    assert anne_arundel.two_unit_units == 8
    assert anne_arundel.three_four_unit_units == 9
    assert anne_arundel.five_plus_unit_units == 360
    assert anne_arundel.total_units_authorized == 1527
    assert anne_arundel.total_value_dollars == 500900000
    assert len(anne_arundel.source_url_hash) == 64
