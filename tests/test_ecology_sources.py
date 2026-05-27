from tickbiterisk.etl.ecology_sources import (
    CENSUS_BPS_COUNTY_INDEX_URL,
    ECOLOGY_SOURCE_FILES,
    MARYLAND_DNR_MAST_REPORT_URLS,
    USDA_MARYLAND_CDL_URL,
    USGS_ANNUAL_NLCD_ACCESS_URL,
    EcologySourceFile,
)


def test_ecology_source_registry_has_primary_source_families() -> None:
    source_ids = {source.source_id for source in ECOLOGY_SOURCE_FILES}

    assert "usgs_annual_nlcd_access" in source_ids
    assert "census_bps_county_index" in source_ids
    assert "usda_nass_maryland_cdl" in source_ids
    assert "maryland_dnr_game_mammals_mast_link" in source_ids


def test_ecology_source_urls_are_official_sources() -> None:
    assert USGS_ANNUAL_NLCD_ACCESS_URL == (
        "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access"
    )
    assert CENSUS_BPS_COUNTY_INDEX_URL == "https://www2.census.gov/econ/bps/County/"
    assert USDA_MARYLAND_CDL_URL == (
        "https://data.nass.usda.gov/Statistics_by_State/Maryland/"
        "Publications/Cropland_Data_Layer/index.php"
    )


def test_mast_report_registry_includes_known_official_reports() -> None:
    assert [source.year for source in MARYLAND_DNR_MAST_REPORT_URLS] == [
        2017,
        2020,
        2021,
    ]
    assert all("dnr.maryland.gov" in source.url for source in MARYLAND_DNR_MAST_REPORT_URLS)


def test_source_default_paths_live_under_ignored_raw_data() -> None:
    source = EcologySourceFile(
        source_id="example",
        family="example",
        url="https://example.test/file.csv",
        raw_relative_path="example/file.csv",
        description="Example source",
        expected_format="csv",
    )

    assert str(source.raw_path()).endswith("data/raw/ecology/example/file.csv")
