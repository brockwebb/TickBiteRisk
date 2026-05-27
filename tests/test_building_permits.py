from dataclasses import replace

from tickbiterisk.etl import building_permits
from tickbiterisk.etl.building_permits import (
    build_census_bps_county_annual_url,
    fetch_census_bps_county_text,
    parse_census_bps_county_text,
)
from tickbiterisk.etl.building_permits_build import write_building_permits_output


BPS_SAMPLE = """Survey,FIPS,FIPS,Region,Division,County,,1-unit,,,2-units,,,3-4 units,,,5+ units,,,1-unit rep,,,2-units rep,,,3-4 units rep,,, 5+units rep
Date,State,County,Code,Code,Name,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value
 
202412,24,003,3,5,Anne Arundel County                                      ,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000
202412,24,005,3,5,Baltimore County                                         ,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000
202412,51,001,3,5,Accomack County                                          ,10,10,1000000,0,0,0,0,0,0,0,0,0,10,10,1000000,0,0,0,0,0,0,0,0,0
"""


class FakeTextResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> "FakeTextResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.content


def test_build_census_bps_county_annual_url_uses_december_ytd_file() -> None:
    assert build_census_bps_county_annual_url(2024) == (
        "https://www2.census.gov/econ/bps/County/co2412y.txt"
    )


def test_fetch_census_bps_county_text_retries_transient_oserror_then_decodes_latin1(
    monkeypatch,
) -> None:
    calls = []

    def flaky_urlopen(request, *, timeout: int):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise OSError("connection reset")
        return FakeTextResponse("Prince George\xeds".encode("latin1"))

    monkeypatch.setattr(building_permits, "urlopen", flaky_urlopen)

    text = fetch_census_bps_county_text(
        "https://www2.census.gov/econ/bps/County/co2412y.txt",
        retry_delay_seconds=0,
    )

    assert text == "Prince George\xeds"
    assert len(calls) == 2
    assert calls[0][0].headers["User-agent"] == "tickbiterisk-etl/0.1"
    assert calls[0][1] == 60


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


def test_write_building_permits_output_appends_and_dedupes(tmp_path) -> None:
    row = parse_census_bps_county_text(
        BPS_SAMPLE,
        source_url="https://www2.census.gov/econ/bps/County/co2412y.txt",
        source_id="census_bps_county_2024",
    )[0]
    replacement = replace(row, total_units_authorized=1600)

    write_building_permits_output([row], tmp_path)
    output = write_building_permits_output([replacement], tmp_path, append=True)

    text = output.read_text(encoding="utf-8")
    assert output.name == "maryland_building_permits_county_year.csv"
    assert "county_fips,county_name,year,month" in text
    assert text.count("24003") == 1
    assert "1600" in text
