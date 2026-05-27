import csv
from pathlib import Path

from tickbiterisk.etl.usdm_drought import (
    build_usdm_county_year_features,
    build_usdm_drought_urls,
    parse_usdm_dsci_csv,
)
from tickbiterisk.etl.usdm_drought_build import (
    USDM_COUNTY_YEAR_COLUMNS,
    USDM_WEEKLY_COLUMNS,
    write_usdm_county_year_output,
    write_usdm_weekly_output,
)


DSCI_CSV = """State,County,FIPS,MapDate,DSCI
MD,Allegany County,24001,2020-03-31,0
MD,Allegany County,24001,2020-04-07,100
MD,Allegany County,24001,2020-07-14,250
MD,Anne Arundel County,24003,2020-04-07,50
"""

SEVERITY_CSV = """MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4
2020-03-31,24001,Allegany County,MD,100,0,0,0,0,0
2020-04-07,24001,Allegany County,MD,0,100,0,0,0,0
2020-07-14,24001,Allegany County,MD,0,10,40,50,0,0
2020-04-07,24003,Anne Arundel County,MD,50,50,0,0,0,0
"""


def test_parse_usdm_csv_rows_merges_dsci_and_severity() -> None:
    rows = parse_usdm_dsci_csv(
        DSCI_CSV,
        severity_csv=SEVERITY_CSV,
        source_url="https://example.test/usdm",
    )

    assert len(rows) == 4
    row = rows[1]
    assert row.county_fips == "24001"
    assert row.county_name == "Allegany County"
    assert row.state == "MD"
    assert row.map_date.isoformat() == "2020-04-07"
    assert row.dsci == 100
    assert row.pct_none == 0
    assert row.pct_d0 == 100
    assert row.pct_d1 == 0
    assert row.pct_d2 == 0
    assert row.source_id == "usdm_county_statistics"
    assert len(row.source_url_hash) == 64
    assert row.feature_quality_flags == "drought_monitor_retro_observed"


def test_build_usdm_county_year_features_aggregates_drought_weeks() -> None:
    weekly_rows = parse_usdm_dsci_csv(
        DSCI_CSV,
        severity_csv=SEVERITY_CSV,
        source_url="https://example.test/usdm",
    )

    features = build_usdm_county_year_features(weekly_rows)

    allegany = next(row for row in features if row.county_fips == "24001")
    assert allegany.year == 2020
    assert allegany.usdm_week_count == 3
    assert allegany.usdm_dsci_mean == round((0 + 100 + 250) / 3, 6)
    assert allegany.usdm_dsci_max == 250
    assert allegany.usdm_weeks_d0_or_worse == 2
    assert allegany.usdm_weeks_d1_or_worse == 1
    assert allegany.usdm_weeks_d2_or_worse == 1
    assert allegany.usdm_tick_season_week_count == 2
    assert allegany.usdm_tick_season_dsci_mean == 175
    assert allegany.usdm_tick_season_weeks_d1_or_worse == 1
    assert allegany.feature_quality_flags == "drought_monitor_retro_observed"


def test_build_usdm_county_year_features_dedupes_overlapping_api_weeks() -> None:
    weekly_rows = parse_usdm_dsci_csv(
        DSCI_CSV,
        severity_csv=SEVERITY_CSV,
        source_url="https://example.test/usdm",
    )

    features = build_usdm_county_year_features([*weekly_rows, weekly_rows[1]])

    allegany = next(row for row in features if row.county_fips == "24001")
    assert allegany.usdm_week_count == 3
    assert allegany.usdm_dsci_mean == round((0 + 100 + 250) / 3, 6)
    assert allegany.usdm_weeks_d0_or_worse == 2


def test_build_usdm_drought_urls_use_county_statistics_api() -> None:
    urls = build_usdm_drought_urls(aoi="MD", year=2020)

    assert "GetDSCI" in urls.dsci_url
    assert "GetDroughtSeverityStatisticsByAreaPercent" in urls.severity_url
    assert "aoi=MD" in urls.dsci_url
    assert "startdate=1%2F1%2F2020" in urls.dsci_url
    assert "enddate=12%2F31%2F2020" in urls.severity_url
    assert "statisticsType=1" in urls.severity_url


def test_write_usdm_outputs_order_and_dedupe(tmp_path: Path) -> None:
    weekly_rows = parse_usdm_dsci_csv(
        DSCI_CSV,
        severity_csv=SEVERITY_CSV,
        source_url="https://example.test/usdm",
    )
    features = build_usdm_county_year_features(weekly_rows)

    weekly_path = write_usdm_weekly_output(weekly_rows, tmp_path)
    yearly_path = write_usdm_county_year_output(features, tmp_path)
    yearly_path = write_usdm_county_year_output(features, tmp_path, append=True)

    with weekly_path.open("r", encoding="utf-8", newline="") as handle:
        weekly_records = list(csv.DictReader(handle))
    assert list(weekly_records[0].keys()) == USDM_WEEKLY_COLUMNS
    assert weekly_records[0]["county_fips"] == "24001"

    with yearly_path.open("r", encoding="utf-8", newline="") as handle:
        yearly_records = list(csv.DictReader(handle))
    assert list(yearly_records[0].keys()) == USDM_COUNTY_YEAR_COLUMNS
    assert len(yearly_records) == 2
    assert yearly_records[0]["county_fips"] == "24001"
