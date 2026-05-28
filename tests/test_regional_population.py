import csv
from pathlib import Path

from tickbiterisk.etl.regional_population import (
    MIDATLANTIC_STATE_FIPS,
    build_midatlantic_population_urls,
    fetch_midatlantic_county_population_estimates,
)
from tickbiterisk.etl.regional_population_build import (
    REGIONAL_COUNTY_POPULATION_COLUMNS,
    write_regional_county_population_output,
)


def test_build_midatlantic_population_urls_cover_each_state_and_year_family() -> None:
    urls = build_midatlantic_population_urls(api_key="secret-key")

    assert len(urls) == len(MIDATLANTIC_STATE_FIPS) + 2
    assert any("co-est00int-alldata-10.csv" in url for url in urls)
    assert any("co-est00int-alldata-11.csv" in url for url in urls)
    assert any("co-est00int-alldata-24.csv" in url for url in urls)
    assert any("co-est00int-alldata-42.csv" in url for url in urls)
    assert any("co-est00int-alldata-51.csv" in url for url in urls)
    assert any("co-est00int-alldata-54.csv" in url for url in urls)
    assert any("co-est2019-alldata.csv" in url for url in urls)
    assert any("co-est2023-alldata.csv" in url for url in urls)
    assert all("secret-key" not in url for url in urls)


def test_fetch_midatlantic_county_population_estimates_combines_state_panels() -> None:
    calls: list[str] = []

    def fake_text_get(url: str) -> str:
        calls.append(url)
        state = "24" if "24" in url else "42"
        county = "003" if state == "24" else "001"
        name = (
            "Anne Arundel County, Maryland"
            if state == "24"
            else "Adams County, Pennsylvania"
        )
        if "co-est00int-alldata" in url:
            return (
                "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,YEAR,AGEGRP,TOT_POP\n"
                f"050,{state},{county},{'Maryland' if state == '24' else 'Pennsylvania'},{name.split(',')[0]},3,99,200\n"
            )
        if "co-est2019-alldata" in url:
            return (
                "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2010,POPESTIMATE2011,POPESTIMATE2012,POPESTIMATE2013,POPESTIMATE2014,POPESTIMATE2015,POPESTIMATE2016,POPESTIMATE2017,POPESTIMATE2018,POPESTIMATE2019\n"
                "050,24,003,Maryland,Anne Arundel County,2010,2011,2012,2013,2014,2015,2016,2017,2018,300\n"
                "050,42,001,Pennsylvania,Adams County,2010,2011,2012,2013,2014,2015,2016,2017,2018,300\n"
            )
        if "co-est2023-alldata" in url:
            return (
                "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023\n"
                "050,24,003,Maryland,Anne Arundel County,400,401,402,403\n"
                "050,42,001,Pennsylvania,Adams County,400,401,402,403\n"
            )
        raise AssertionError(url)

    rows = fetch_midatlantic_county_population_estimates(
        state_fips_list=["24", "42"],
        api_key="secret-key",
        text_get=fake_text_get,
    )

    assert len(calls) == 4
    assert [
        (row.state_fips, row.county_fips, row.year, row.population)
        for row in rows
    ] == [
        ("24", "24003", 2001, 200),
        ("24", "24003", 2010, 2010),
        ("24", "24003", 2011, 2011),
        ("24", "24003", 2012, 2012),
        ("24", "24003", 2013, 2013),
        ("24", "24003", 2014, 2014),
        ("24", "24003", 2015, 2015),
        ("24", "24003", 2016, 2016),
        ("24", "24003", 2017, 2017),
        ("24", "24003", 2018, 2018),
        ("24", "24003", 2019, 300),
        ("24", "24003", 2020, 400),
        ("24", "24003", 2021, 401),
        ("24", "24003", 2022, 402),
        ("24", "24003", 2023, 403),
        ("42", "42001", 2001, 200),
        ("42", "42001", 2010, 2010),
        ("42", "42001", 2011, 2011),
        ("42", "42001", 2012, 2012),
        ("42", "42001", 2013, 2013),
        ("42", "42001", 2014, 2014),
        ("42", "42001", 2015, 2015),
        ("42", "42001", 2016, 2016),
        ("42", "42001", 2017, 2017),
        ("42", "42001", 2018, 2018),
        ("42", "42001", 2019, 300),
        ("42", "42001", 2020, 400),
        ("42", "42001", 2021, 401),
        ("42", "42001", 2022, 402),
        ("42", "42001", 2023, 403),
    ]
    assert rows[0].state_abbr == "MD"
    assert rows[-1].state_abbr == "PA"
    assert "regional_population_denominator" in rows[0].feature_quality_flags


def test_write_regional_county_population_output_uses_stable_schema(tmp_path: Path) -> None:
    rows = fetch_midatlantic_county_population_estimates(
        state_fips_list=["24"],
        text_get=lambda url: _fake_population_payload(url),
    )

    output_path = write_regional_county_population_output(rows, tmp_path)

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == REGIONAL_COUNTY_POPULATION_COLUMNS
        first = next(reader)
    assert output_path.name == "midatlantic_county_population_year.csv"
    assert first[:4] == ["24", "MD", "Maryland", "24003"]


def _fake_population_payload(url: str) -> str:
    if "co-est00int-alldata" in url:
        return (
            "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,YEAR,AGEGRP,TOT_POP\n"
            "050,24,003,Maryland,Anne Arundel County,3,99,200\n"
        )
    if "co-est2019-alldata" in url:
        return (
            "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2010,POPESTIMATE2011,POPESTIMATE2012,POPESTIMATE2013,POPESTIMATE2014,POPESTIMATE2015,POPESTIMATE2016,POPESTIMATE2017,POPESTIMATE2018,POPESTIMATE2019\n"
            "050,24,003,Maryland,Anne Arundel County,2010,2011,2012,2013,2014,2015,2016,2017,2018,300\n"
        )
    return (
        "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023\n"
        "050,24,003,Maryland,Anne Arundel County,400,401,402,403\n"
    )
