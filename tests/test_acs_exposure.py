import csv
from pathlib import Path

from tickbiterisk.etl.acs_exposure import (
    build_acs_exposure_source_urls,
    build_midatlantic_acs_exposure,
)
from tickbiterisk.etl.acs_exposure_build import (
    ACS_EXPOSURE_COLUMNS,
    write_acs_exposure_output,
)


def test_build_acs_exposure_source_urls_uses_keyless_table_based_files() -> None:
    urls = build_acs_exposure_source_urls(year=2024)

    assert urls.geography_url == (
        "https://www2.census.gov/programs-surveys/acs/summary_file/2024/"
        "table-based-SF/documentation/Geos20245YR.txt"
    )
    assert urls.table_urls["b01001"].endswith("/acsdt5y2024-b01001.dat")
    assert urls.table_urls["b25024"].endswith("/acsdt5y2024-b25024.dat")
    assert urls.table_urls["b25003"].endswith("/acsdt5y2024-b25003.dat")
    assert urls.gazetteer_url.endswith("/2024_Gazetteer/2024_Gaz_counties_national.zip")


def test_build_midatlantic_acs_exposure_derives_residential_proxy_fields() -> None:
    urls = build_acs_exposure_source_urls(year=2024)

    rows = build_midatlantic_acs_exposure(
        geography_text=_geography_text(
            [
                {
                    "STUSAB": "MD",
                    "STATE": "24",
                    "COUNTY": "003",
                    "GEO_ID": "0500000US24003",
                    "NAME": "Anne Arundel County, Maryland",
                    "TL_GEO_ID": "24003",
                }
            ]
        ),
        b01001_text=_b01001_text(
            "0500000US24003",
            total=100,
            under18_male=[2, 3, 4, 5],
            under18_female=[3, 4, 5, 6],
            age65_male=[1, 1, 2, 2, 3, 3],
            age65_female=[2, 2, 3, 3, 4, 4],
        ),
        b25024_text=_b25024_text(
            "0500000US24003",
            total_housing=50,
            detached=30,
            attached=5,
        ),
        b25003_text=_b25003_text(
            "0500000US24003",
            occupied=40,
            owner=28,
        ),
        gazetteer_text=_gazetteer_text(
            [
                {
                    "USPS": "MD",
                    "GEOID": "24003",
                    "NAME": "Anne Arundel County",
                    "ALAND_SQMI": "10",
                }
            ]
        ),
        source_urls=urls,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24003"
    assert row.year == 2024
    assert row.acs_total_population == 100
    assert row.age_under_18_population == 32
    assert row.age_65_plus_population == 30
    assert row.age_18_64_population == 38
    assert row.age_under_18_share == 0.32
    assert row.single_family_units == 35
    assert row.single_family_share == 0.7
    assert row.owner_occupied_share == 0.7
    assert row.population_per_sqmi == 10.0
    assert row.single_family_units_per_sqmi == 3.5
    assert row.source_id == "census_acs5_2024_residential_exposure"
    assert "acs_5yr_rolling_window" in row.feature_quality_flags
    assert "not_exposure_evidence" in row.feature_quality_flags
    assert "not_tick_bite_counts" in row.feature_quality_flags
    assert "not_lyme_outcome" in row.feature_quality_flags
    assert "not_disease_truth" in row.feature_quality_flags
    assert "not_public_default" in row.feature_quality_flags


def test_build_midatlantic_acs_exposure_flags_missing_values() -> None:
    urls = build_acs_exposure_source_urls(year=2024)

    rows = build_midatlantic_acs_exposure(
        geography_text=_geography_text(
            [
                {
                    "STUSAB": "MD",
                    "STATE": "24",
                    "COUNTY": "011",
                    "GEO_ID": "0500000US24011",
                    "NAME": "Caroline County, Maryland",
                    "TL_GEO_ID": "24011",
                }
            ]
        ),
        b01001_text=_b01001_text("0500000US24011", total=0),
        b25024_text=_b25024_text("0500000US24011", total_housing=0),
        b25003_text=_b25003_text("0500000US24011", occupied=0),
        gazetteer_text=_gazetteer_text([]),
        source_urls=urls,
    )

    row = rows[0]
    assert row.age_under_18_share is None
    assert row.single_family_share is None
    assert row.owner_occupied_share is None
    assert row.land_area_sqmi is None
    assert "zero_or_missing_denominator" in row.feature_quality_flags
    assert "missing_land_area" in row.feature_quality_flags


def test_write_acs_exposure_output_writes_stable_columns(tmp_path: Path) -> None:
    urls = build_acs_exposure_source_urls(year=2024)
    rows = build_midatlantic_acs_exposure(
        geography_text=_geography_text(
            [
                {
                    "STUSAB": "MD",
                    "STATE": "24",
                    "COUNTY": "011",
                    "GEO_ID": "0500000US24011",
                    "NAME": "Caroline County, Maryland",
                    "TL_GEO_ID": "24011",
                }
            ]
        ),
        b01001_text=_b01001_text("0500000US24011", total=100),
        b25024_text=_b25024_text("0500000US24011", total_housing=50),
        b25003_text=_b25003_text("0500000US24011", occupied=40),
        gazetteer_text=_gazetteer_text(
            [{"USPS": "MD", "GEOID": "24011", "NAME": "Caroline", "ALAND_SQMI": "5"}]
        ),
        source_urls=urls,
    )

    output = write_acs_exposure_output(rows, tmp_path / "out")

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == ACS_EXPOSURE_COLUMNS
        first_row = next(reader)
    assert first_row[0:6] == ["24", "MD", "Maryland", "24011", "Caroline County", "2024"]


def _geography_text(rows: list[dict[str, str]]) -> str:
    fieldnames = [
        "FILEID",
        "STUSAB",
        "SUMLEVEL",
        "COMPONENT",
        "STATE",
        "COUNTY",
        "GEO_ID",
        "NAME",
        "TL_GEO_ID",
    ]
    lines = ["|".join(fieldnames)]
    for row in rows:
        record = {fieldname: row.get(fieldname, "") for fieldname in fieldnames}
        record["FILEID"] = record["FILEID"] or "ACSSF"
        record["SUMLEVEL"] = record["SUMLEVEL"] or "050"
        record["COMPONENT"] = record["COMPONENT"] or "00"
        lines.append("|".join(record[fieldname] for fieldname in fieldnames))
    return "\n".join(lines)


def _b01001_text(
    geo_id: str,
    *,
    total: int,
    under18_male: list[int] | None = None,
    under18_female: list[int] | None = None,
    age65_male: list[int] | None = None,
    age65_female: list[int] | None = None,
) -> str:
    values = {f"B01001_E{index:03d}": "0" for index in range(1, 50)}
    values["B01001_E001"] = str(total)
    for start, source_values in [
        (3, under18_male or [0, 0, 0, 0]),
        (27, under18_female or [0, 0, 0, 0]),
        (20, age65_male or [0, 0, 0, 0, 0, 0]),
        (44, age65_female or [0, 0, 0, 0, 0, 0]),
    ]:
        for offset, value in enumerate(source_values):
            values[f"B01001_E{start + offset:03d}"] = str(value)
    fieldnames = ["GEO_ID", *values]
    return "\n".join(
        [
            "|".join(fieldnames),
            "|".join([geo_id, *[values[fieldname] for fieldname in values]]),
        ]
    )


def _b25024_text(
    geo_id: str,
    *,
    total_housing: int,
    detached: int = 0,
    attached: int = 0,
) -> str:
    fieldnames = ["GEO_ID", "B25024_E001", "B25024_E002", "B25024_E003"]
    return "\n".join(
        [
            "|".join(fieldnames),
            "|".join([geo_id, str(total_housing), str(detached), str(attached)]),
        ]
    )


def _b25003_text(
    geo_id: str,
    *,
    occupied: int,
    owner: int = 0,
) -> str:
    fieldnames = ["GEO_ID", "B25003_E001", "B25003_E002"]
    return "\n".join(
        [
            "|".join(fieldnames),
            "|".join([geo_id, str(occupied), str(owner)]),
        ]
    )


def _gazetteer_text(rows: list[dict[str, str]]) -> str:
    fieldnames = ["USPS", "GEOID", "NAME", "ALAND_SQMI"]
    lines = ["\t".join(fieldnames)]
    for row in rows:
        lines.append("\t".join(row.get(fieldname, "") for fieldname in fieldnames))
    return "\n".join(lines)
