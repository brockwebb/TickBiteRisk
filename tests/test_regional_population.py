import csv
from pathlib import Path

from tickbiterisk.etl.regional_population import (
    MIDATLANTIC_STATE_FIPS,
    RegionalCountyPopulation,
    build_midatlantic_population_urls,
    fetch_midatlantic_county_population_estimates,
    parse_census_pep_2025_county_totals,
    project_regional_county_population,
)
from tickbiterisk.etl.regional_population_build import (
    REGIONAL_COUNTY_POPULATION_COLUMNS,
    write_regional_county_population_output,
)


def test_build_midatlantic_population_urls_cover_each_state_and_year_family() -> None:
    urls = build_midatlantic_population_urls(api_key="secret-key")

    assert len(urls) == len(MIDATLANTIC_STATE_FIPS) + 3
    assert any("co-est00int-alldata-10.csv" in url for url in urls)
    assert any("co-est00int-alldata-11.csv" in url for url in urls)
    assert any("co-est00int-alldata-24.csv" in url for url in urls)
    assert any("co-est00int-alldata-42.csv" in url for url in urls)
    assert any("co-est00int-alldata-51.csv" in url for url in urls)
    assert any("co-est00int-alldata-54.csv" in url for url in urls)
    assert any("co-est2019-alldata.csv" in url for url in urls)
    assert any("co-est2023-alldata.csv" in url for url in urls)
    assert any("co-est2025-alldata.csv" in url for url in urls)
    assert all("secret-key" not in url for url in urls)


def test_parse_census_pep_2025_county_totals_filters_midatlantic_states() -> None:
    csv_text = (
        "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023,POPESTIMATE2024,POPESTIMATE2025\n"
        "040,24,000,Maryland,Maryland,6177224,6200000,6210000,6220000,6263220,6315000\n"
        "050,24,003,Maryland,Anne Arundel County,590000,591000,592000,593000,594582,598000\n"
        "050,42,001,Pennsylvania,Adams County,102000,102500,103000,104000,104500,105000\n"
        "050,36,001,New York,Albany County,311000,312000,313000,314000,315000,316000\n"
    )

    rows = parse_census_pep_2025_county_totals(
        csv_text,
        source_url="https://example.test/co-est2025-alldata.csv",
        state_fips_list=["24", "42"],
    )

    assert [(row.county_fips, row.year, row.population) for row in rows] == [
        ("24003", 2020, 590000),
        ("24003", 2021, 591000),
        ("24003", 2022, 592000),
        ("24003", 2023, 593000),
        ("24003", 2024, 594582),
        ("24003", 2025, 598000),
        ("42001", 2020, 102000),
        ("42001", 2021, 102500),
        ("42001", 2022, 103000),
        ("42001", 2023, 104000),
        ("42001", 2024, 104500),
        ("42001", 2025, 105000),
    ]
    assert rows[0].source_id == "census_pep_2025_county_totals"
    assert rows[0].census_dataset == "2020-2025/counties/totals/co-est2025-alldata.csv"
    assert rows[0].vintage == 2025


def test_fetch_population_projection_uses_full_vintage_2025_trend_when_output_filtered() -> None:
    rows = fetch_midatlantic_county_population_estimates(
        state_fips_list=["24"],
        text_get=lambda url: _fake_population_payload(url),
        min_year=2025,
        max_year=2026,
    )

    assert [
        (row.county_fips, row.year, row.population, row.source_id)
        for row in rows
    ] == [
        ("24003", 2025, 150, "census_pep_2025_county_totals"),
        ("24003", 2026, 160, "regional_population_linear_projection"),
    ]


def test_population_projection_requires_observed_2025_base_year() -> None:
    rows = [
        RegionalCountyPopulation(
            state_fips="51",
            state_abbr="VA",
            state_name="Virginia",
            county_fips="51515",
            county_name="Bedford city",
            year=2023,
            population=1000,
            source_id="census_pep_2023_county_totals",
            census_dataset="2020-2023/counties/totals/co-est2023-alldata.csv",
            vintage=2023,
            source_url_hash="a" * 64,
            feature_quality_flags="regional_population_denominator",
        ),
        RegionalCountyPopulation(
            state_fips="51",
            state_abbr="VA",
            state_name="Virginia",
            county_fips="51001",
            county_name="Accomack County",
            year=2024,
            population=33000,
            source_id="census_pep_2025_county_totals",
            census_dataset="2020-2025/counties/totals/co-est2025-alldata.csv",
            vintage=2025,
            source_url_hash="b" * 64,
            feature_quality_flags="regional_population_denominator",
        ),
        RegionalCountyPopulation(
            state_fips="51",
            state_abbr="VA",
            state_name="Virginia",
            county_fips="51001",
            county_name="Accomack County",
            year=2025,
            population=33100,
            source_id="census_pep_2025_county_totals",
            census_dataset="2020-2025/counties/totals/co-est2025-alldata.csv",
            vintage=2025,
            source_url_hash="b" * 64,
            feature_quality_flags="regional_population_denominator",
        ),
    ]

    projections = project_regional_county_population(
        rows,
        through_year=2026,
        source_url="https://example.test/co-est2025-alldata.csv",
    )

    assert [(row.county_fips, row.year) for row in projections] == [
        ("51001", 2026)
    ]
    assert projections[0].population == 33200


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
        if "co-est2025-alldata" in url:
            return (
                "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023,POPESTIMATE2024,POPESTIMATE2025\n"
                "050,24,003,Maryland,Anne Arundel County,400,401,402,403,404,406\n"
                "050,42,001,Pennsylvania,Adams County,400,401,402,403,404,406\n"
            )
        raise AssertionError(url)

    rows = fetch_midatlantic_county_population_estimates(
        state_fips_list=["24", "42"],
        api_key="secret-key",
        text_get=fake_text_get,
    )

    assert len(calls) == 5
    assert [
        (
            row.state_fips,
            row.county_fips,
            row.year,
            row.population,
            row.source_id,
        )
        for row in rows
    ] == [
        ("24", "24003", 2001, 200, "census_pep_intercensal_2000_2010_static"),
        ("24", "24003", 2010, 2010, "census_pep_2019_county_totals"),
        ("24", "24003", 2011, 2011, "census_pep_2019_county_totals"),
        ("24", "24003", 2012, 2012, "census_pep_2019_county_totals"),
        ("24", "24003", 2013, 2013, "census_pep_2019_county_totals"),
        ("24", "24003", 2014, 2014, "census_pep_2019_county_totals"),
        ("24", "24003", 2015, 2015, "census_pep_2019_county_totals"),
        ("24", "24003", 2016, 2016, "census_pep_2019_county_totals"),
        ("24", "24003", 2017, 2017, "census_pep_2019_county_totals"),
        ("24", "24003", 2018, 2018, "census_pep_2019_county_totals"),
        ("24", "24003", 2019, 300, "census_pep_2019_county_totals"),
        ("24", "24003", 2020, 400, "census_pep_2025_county_totals"),
        ("24", "24003", 2021, 401, "census_pep_2025_county_totals"),
        ("24", "24003", 2022, 402, "census_pep_2025_county_totals"),
        ("24", "24003", 2023, 403, "census_pep_2025_county_totals"),
        ("24", "24003", 2024, 404, "census_pep_2025_county_totals"),
        ("24", "24003", 2025, 406, "census_pep_2025_county_totals"),
        ("24", "24003", 2026, 407, "regional_population_linear_projection"),
        ("42", "42001", 2001, 200, "census_pep_intercensal_2000_2010_static"),
        ("42", "42001", 2010, 2010, "census_pep_2019_county_totals"),
        ("42", "42001", 2011, 2011, "census_pep_2019_county_totals"),
        ("42", "42001", 2012, 2012, "census_pep_2019_county_totals"),
        ("42", "42001", 2013, 2013, "census_pep_2019_county_totals"),
        ("42", "42001", 2014, 2014, "census_pep_2019_county_totals"),
        ("42", "42001", 2015, 2015, "census_pep_2019_county_totals"),
        ("42", "42001", 2016, 2016, "census_pep_2019_county_totals"),
        ("42", "42001", 2017, 2017, "census_pep_2019_county_totals"),
        ("42", "42001", 2018, 2018, "census_pep_2019_county_totals"),
        ("42", "42001", 2019, 300, "census_pep_2019_county_totals"),
        ("42", "42001", 2020, 400, "census_pep_2025_county_totals"),
        ("42", "42001", 2021, 401, "census_pep_2025_county_totals"),
        ("42", "42001", 2022, 402, "census_pep_2025_county_totals"),
        ("42", "42001", 2023, 403, "census_pep_2025_county_totals"),
        ("42", "42001", 2024, 404, "census_pep_2025_county_totals"),
        ("42", "42001", 2025, 406, "census_pep_2025_county_totals"),
        ("42", "42001", 2026, 407, "regional_population_linear_projection"),
    ]
    assert rows[0].state_abbr == "MD"
    assert rows[-1].state_abbr == "PA"
    assert "regional_population_denominator" in rows[0].feature_quality_flags
    assert "simple_linear_population_projection" in rows[-1].feature_quality_flags
    assert "no_official_2026_census_denominator" in rows[-1].feature_quality_flags


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
    if "co-est2023-alldata" in url:
        return (
            "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023\n"
            "050,24,003,Maryland,Anne Arundel County,400,401,402,403\n"
        )
    return (
        "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,POPESTIMATE2023,POPESTIMATE2024,POPESTIMATE2025\n"
        "050,24,003,Maryland,Anne Arundel County,100,110,120,130,140,150\n"
    )
