import csv
from pathlib import Path

from tickbiterisk.etl.nssp_coverage import (
    build_maryland_nssp_coverage,
    parse_nssp_coverage_csv,
)
from tickbiterisk.etl.nssp_coverage_build import (
    NSSP_COVERAGE_COLUMNS,
    write_nssp_coverage_output,
)


def test_parse_nssp_coverage_csv_normalizes_statuses() -> None:
    rows = parse_nssp_coverage_csv(
        "\n".join(
            [
                "State,County,Status",
                "MD,Anne Arundel,Recent Data in NSSP",
                "MD,Caroline,No Eligible Facilities",
                "MD,Example,No Recent Data in NSSP",
            ]
        )
    )

    assert [row.state_abbr for row in rows] == ["MD", "MD", "MD"]
    assert [row.coverage_status_slug for row in rows] == [
        "recent_data_in_nssp",
        "no_eligible_facilities",
        "no_recent_data_in_nssp",
    ]
    assert rows[0].recent_data_in_nssp is True
    assert rows[1].recent_data_in_nssp is False


def test_build_maryland_nssp_coverage_joins_county_reference_names(
    tmp_path: Path,
) -> None:
    raw_rows = parse_nssp_coverage_csv(
        "\n".join(
            [
                "State,County,Status",
                "MD,Prince Georges,Recent Data in NSSP",
                "MD,Queen Annes,Recent Data in NSSP",
                "MD,St. Marys,Recent Data in NSSP",
                "MD,Baltimore City,Recent Data in NSSP",
                "MD,Caroline,No Eligible Facilities",
            ]
        )
    )
    county_reference = _write_county_reference(tmp_path / "county_reference.csv")

    rows = build_maryland_nssp_coverage(
        raw_rows,
        county_reference_path=county_reference,
        source_id="cdc_nssp_coverage_2024_07_01",
        source_url="https://www.cdc.gov/nssp/documents/Coverage_Map_Tbl_2024Jul01.csv",
        coverage_as_of_date="2024-07-01",
    )

    by_fips = {row.county_fips: row for row in rows}
    assert set(by_fips) == {"24011", "24033", "24035", "24037", "24510"}
    assert by_fips["24033"].county_name == "Prince George's County"
    assert by_fips["24035"].nssp_county_name == "Queen Annes"
    assert by_fips["24037"].nssp_county_name == "St. Marys"
    assert by_fips["24510"].county_name == "Baltimore city"
    assert by_fips["24011"].nssp_coverage_status == "No Eligible Facilities"
    assert by_fips["24011"].recent_data_in_nssp is False
    assert by_fips["24011"].nssp_coverage_category == "no_eligible_facilities"
    assert "nssp_coverage_only_not_tick_bite_counts" in (
        by_fips["24011"].feature_quality_flags
    )
    assert "no_eligible_facilities_reported" in by_fips["24011"].feature_quality_flags


def test_write_nssp_coverage_output_writes_stable_columns(tmp_path: Path) -> None:
    raw_rows = parse_nssp_coverage_csv(
        "State,County,Status\nMD,Caroline,No Eligible Facilities\n"
    )
    rows = build_maryland_nssp_coverage(
        raw_rows,
        county_reference_path=_write_county_reference(tmp_path / "county_reference.csv"),
        source_id="cdc_nssp_coverage_2024_07_01",
        source_url="https://www.cdc.gov/nssp/documents/Coverage_Map_Tbl_2024Jul01.csv",
        coverage_as_of_date="2024-07-01",
    )

    output = write_nssp_coverage_output(rows, tmp_path / "out")

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == NSSP_COVERAGE_COLUMNS
        first_row = next(reader)
    assert first_row[0] == "24011"


def _write_county_reference(path: Path) -> Path:
    rows = [
        ("24003", "Anne Arundel County"),
        ("24005", "Baltimore County"),
        ("24011", "Caroline County"),
        ("24033", "Prince George's County"),
        ("24035", "Queen Anne's County"),
        ("24037", "St. Mary's County"),
        ("24510", "Baltimore city"),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        for county_fips, county_name in rows:
            writer.writerow(
                {
                    "county_fips": county_fips,
                    "state_fips": "24",
                    "state": "MD",
                    "county_name": county_name,
                    "aland_sqmi": "1",
                    "awater_sqmi": "0",
                    "intptlat": "0",
                    "intptlon": "0",
                    "geography_source": "fixture",
                    "source_url_hash": "fixture",
                }
            )
    return path
