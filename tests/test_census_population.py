import pytest

from tickbiterisk.etl.census_population import (
    CENSUS_API_ENDPOINT,
    CensusApiResponseError,
    build_census_intercensal_1990_population_url,
    build_census_intercensal_2000_population_url,
    build_census_pep_2019_population_url,
    build_census_pep_2023_charv_population_url,
    build_census_pep_2025_county_totals_url,
    fetch_maryland_county_population_estimates,
    fetch_maryland_latest_county_population_estimates,
    get_census_api_key,
    parse_census_pep_2025_county_totals_population,
    parse_census_intercensal_1990_population,
    parse_census_intercensal_2000_population,
    parse_census_pep_2019_population,
    parse_census_pep_2023_charv_population,
    sanitize_census_url,
)


def test_get_census_api_key_reads_optional_env_mapping() -> None:
    assert get_census_api_key({"CENSUS_API_KEY": "  census-key  "}) == "census-key"
    assert get_census_api_key({}) is None


def test_build_census_population_urls_append_key_without_leaking_in_sanitized_url() -> None:
    url = build_census_pep_2019_population_url(api_key="secret-census-key")

    assert url.startswith(f"{CENSUS_API_ENDPOINT}/2019/pep/population?")
    assert "for=county%3A%2A" in url
    assert "in=state%3A24" in url
    assert "key=secret-census-key" in url
    assert sanitize_census_url(url).endswith("key=%3Credacted%3E")
    assert "secret-census-key" not in sanitize_census_url(url)


def test_parse_census_intercensal_1990_population_filters_requested_years() -> None:
    rows = parse_census_intercensal_1990_population(
        [
            ["POP", "YEAR", "AGEGRP", "RACE_SEX", "HISP", "STATE", "COUNTY", "state", "county"],
            ["10", "91", "00", "01", "1", "24", "003", "24", "003"],
            ["20", "92", "00", "01", "1", "24", "003", "24", "003"],
            ["30", "92", "00", "02", "1", "24", "003", "24", "003"],
            ["40", "99", "00", "01", "1", "24", "003", "24", "003"],
        ],
        source_url="https://example.test/census?key=secret",
        min_year=1992,
        max_year=1999,
    )

    assert [row.year for row in rows] == [1992, 1999]
    assert rows[0].county_fips == "24003"
    assert rows[0].population == 50
    assert rows[0].source_id == "census_pep_intercensal_1990_2000"
    assert len(rows[0].source_url_hash) == 64


def test_parse_census_intercensal_2000_population_uses_date_description_year() -> None:
    rows = parse_census_intercensal_2000_population(
        [
            ["GEONAME", "POP", "DATE_", "DATE_DESC", "state", "county"],
            [
                "Anne Arundel County, Maryland",
                "493234",
                "4",
                "7/1/2001 population estimate",
                "24",
                "003",
            ],
            [
                "Anne Arundel County, Maryland",
                "538160",
                "13",
                "4/1/2010 Census population",
                "24",
                "003",
            ],
        ],
        source_url="https://example.test/census",
        min_year=2000,
        max_year=2009,
    )

    assert len(rows) == 1
    assert rows[0].year == 2001
    assert rows[0].county_name == "Anne Arundel County"
    assert rows[0].population == 493234


def test_parse_census_pep_2019_population_maps_date_code_to_year() -> None:
    rows = parse_census_pep_2019_population(
        [
            ["NAME", "POP", "DATE_CODE", "state", "county"],
            ["Anne Arundel County, Maryland", "556134", "3", "24", "003"],
            ["Anne Arundel County, Maryland", "579234", "12", "24", "003"],
        ],
        source_url="https://example.test/census",
    )

    assert [row.year for row in rows] == [2010, 2019]
    assert rows[1].source_id == "census_pep_2019"


def test_parse_census_pep_2023_charv_population_keeps_total_july_estimates() -> None:
    rows = parse_census_pep_2023_charv_population(
        [
            ["NAME", "POP", "YEAR", "MONTH", "AGE", "SEX", "HISP", "POPGROUP", "state", "county"],
            ["Anne Arundel County, Maryland", "590336", "2023", "7", "0000", "0", "0", "001", "24", "003"],
            ["Anne Arundel County, Maryland", "42", "2023", "7", "0000", "1", "0", "001", "24", "003"],
        ],
        source_url="https://example.test/census",
    )

    assert len(rows) == 1
    assert rows[0].year == 2023
    assert rows[0].population == 590336
    assert rows[0].source_id == "census_pep_2023_charv"


def test_parse_census_pep_2025_county_totals_population_keeps_maryland_latest_years() -> None:
    csv_text = (
        "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2023,POPESTIMATE2024,POPESTIMATE2025\n"
        "040,24,000,Maryland,Maryland,6177224,6263220,6315000\n"
        "050,24,003,Maryland,Anne Arundel County,590336,594582,598000\n"
        "050,24,510,Maryland,Baltimore city,565239,568271,570100\n"
        "050,51,013,Virginia,Arlington County,238643,240000,241000\n"
    )

    rows = parse_census_pep_2025_county_totals_population(
        csv_text,
        source_url="https://example.test/co-est2025-alldata.csv",
        min_year=2024,
        max_year=2025,
    )

    assert [(row.county_fips, row.year, row.population) for row in rows] == [
        ("24003", 2024, 594582),
        ("24003", 2025, 598000),
        ("24510", 2024, 568271),
        ("24510", 2025, 570100),
    ]
    assert rows[0].county_name == "Anne Arundel County"
    assert rows[0].source_id == "census_pep_2025_county_totals"
    assert rows[0].census_dataset == "2020-2025/counties/totals/co-est2025-alldata.csv"
    assert rows[0].vintage == 2025
    assert len(rows[0].source_url_hash) == 64


def test_fetch_maryland_county_population_estimates_combines_source_eras() -> None:
    calls: list[str] = []

    def fake_json_get(url: str) -> list[list[str]]:
        calls.append(url)
        if "/1990/pep/int_charagegroups" in url:
            return [
                ["POP", "YEAR", "AGEGRP", "RACE_SEX", "HISP", "STATE", "COUNTY"],
                ["40", "92", "00", "01", "1", "24", "003"],
                ["60", "92", "00", "02", "1", "24", "003"],
            ]
        if "/2000/pep/int_population" in url:
            return [
                ["GEONAME", "POP", "DATE_", "DATE_DESC", "state", "county"],
                ["Anne Arundel County, Maryland", "200", "4", "7/1/2001 population estimate", "24", "003"],
            ]
        if "/2019/pep/population" in url:
            return [["NAME", "POP", "DATE_CODE", "state", "county"], ["300", "300", "12", "24", "003"]]
        if "/2023/pep/charv" in url:
            return [
                ["NAME", "POP", "YEAR", "MONTH", "AGE", "SEX", "HISP", "POPGROUP", "state", "county"],
                ["Anne Arundel County, Maryland", "400", "2023", "7", "0000", "0", "0", "001", "24", "003"],
            ]
        raise AssertionError(url)

    def fake_text_get(url: str) -> str:
        calls.append(url)
        if "co-est2025-alldata.csv" in url:
            return (
                "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2024,POPESTIMATE2025\n"
                "050,24,003,Maryland,Anne Arundel County,500,600\n"
            )
        raise AssertionError(url)

    rows = fetch_maryland_county_population_estimates(
        api_key="secret-census-key",
        json_get=fake_json_get,
        text_get=fake_text_get,
    )

    assert [row.year for row in rows] == [1992, 2001, 2019, 2023, 2024, 2025]
    api_calls = [call for call in calls if "api.census.gov" in call]
    static_calls = [call for call in calls if "www2.census.gov" in call]
    assert api_calls
    assert static_calls == [build_census_pep_2025_county_totals_url()]
    assert all("key=secret-census-key" in call for call in api_calls)
    assert all("key=secret-census-key" not in call for call in static_calls)


def test_fetch_maryland_latest_county_population_estimates_uses_static_csv_without_key() -> None:
    calls: list[str] = []

    def fake_text_get(url: str) -> str:
        calls.append(url)
        return (
            "SUMLEV,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2024,POPESTIMATE2025\n"
            "050,24,003,Maryland,Anne Arundel County,500,600\n"
        )

    rows = fetch_maryland_latest_county_population_estimates(text_get=fake_text_get)

    assert build_census_pep_2025_county_totals_url() in calls
    assert [(row.year, row.population) for row in rows] == [(2024, 500), (2025, 600)]


def test_fetch_maryland_county_population_rejects_non_json_without_leaking_key() -> None:
    with pytest.raises(CensusApiResponseError) as exc_info:
        fetch_maryland_county_population_estimates(
            api_key="secret-census-key",
            json_get=lambda url: {"message": "Missing Key"},
        )

    message = str(exc_info.value)
    assert "Census API response must be a JSON table" in message
    assert "secret-census-key" not in message


def test_census_population_url_builders_target_expected_datasets() -> None:
    assert "/1990/pep/int_charagegroups?" in build_census_intercensal_1990_population_url()
    assert "/2000/pep/int_population?" in build_census_intercensal_2000_population_url()
    assert "/2019/pep/population?" in build_census_pep_2019_population_url()
    assert "YEAR=2023" in build_census_pep_2023_charv_population_url(year=2023)
    assert build_census_pep_2025_county_totals_url().endswith(
        "/2020-2025/counties/totals/co-est2025-alldata.csv"
    )
