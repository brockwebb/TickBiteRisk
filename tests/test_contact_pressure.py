import csv
from dataclasses import replace

from tickbiterisk.etl.contact_pressure import (
    ContactPressureFeature,
    build_contact_pressure_features,
)
from tickbiterisk.etl.contact_pressure_build import (
    CONTACT_PRESSURE_COLUMNS,
    write_contact_pressure_output,
)


def _write(path, header, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _sample_inputs(tmp_path):
    bps = tmp_path / "building_permits.csv"
    county_reference = tmp_path / "county_reference.csv"
    population = tmp_path / "county_population_year.csv"
    _write(
        bps,
        [
            "county_fips",
            "county_name",
            "year",
            "month",
            "one_unit_units",
            "two_unit_units",
            "three_four_unit_units",
            "five_plus_unit_units",
            "total_units_authorized",
            "total_value_dollars",
            "source_id",
            "source_url_hash",
        ],
        [
            [
                "24003",
                "Anne Arundel County",
                "2023",
                "12",
                "100",
                "2",
                "4",
                "10",
                "116",
                "42000000",
                "census_bps_county_2023",
                "hash2023",
            ],
            [
                "24003",
                "Anne Arundel County",
                "2024",
                "12",
                "120",
                "0",
                "0",
                "0",
                "120",
                "43000000",
                "census_bps_county_2024",
                "hash2024",
            ],
            [
                "24005",
                "Baltimore County",
                "2023",
                "12",
                "50",
                "0",
                "0",
                "0",
                "50",
                "10000000",
                "census_bps_county_2023",
                "hash2023",
            ],
        ],
    )
    _write(
        county_reference,
        [
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
        [
            [
                "24003",
                "24",
                "MD",
                "Anne Arundel County",
                "414.806",
                "172.995",
                "38.99",
                "-76.56",
                "Census Gazetteer",
                "geo",
            ],
            [
                "24005",
                "24",
                "MD",
                "Baltimore County",
                "598.358",
                "83.382",
                "39.44",
                "-76.61",
                "Census Gazetteer",
                "geo",
            ],
        ],
    )
    _write(
        population,
        [
            "county_fips",
            "county_name",
            "year",
            "population",
            "source_id",
            "census_dataset",
            "vintage",
            "source_url_hash",
        ],
        [
            [
                "24003",
                "Anne Arundel County",
                "2023",
                "590000",
                "census_population_2023",
                "pep",
                "2023",
                "pop",
            ],
            [
                "24005",
                "Baltimore County",
                "2023",
                "850000",
                "census_population_2023",
                "pep",
                "2023",
                "pop",
            ],
        ],
    )
    return bps, county_reference, population


def test_build_contact_pressure_features_calculates_denominator_rates(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2023 = next(row for row in rows if row.county_fips == "24003" and row.year == 2023)
    assert anne_2023.residential_units_authorized == 116
    assert anne_2023.units_authorized_per_sqmi == round(116 / 414.806, 6)
    assert anne_2023.units_authorized_per_100k == round(116 / 590000 * 100000, 6)
    assert anne_2023.total_value_dollars == 42000000
    assert anne_2023.population == 590000
    assert anne_2023.land_area_sqmi == 414.806
    assert anne_2023.feature_quality_flags == (
        "construction_proxy_only,historical_partial_jurisdiction_coverage"
    )


def test_build_contact_pressure_features_flags_missing_population(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2024 = next(row for row in rows if row.county_fips == "24003" and row.year == 2024)
    assert anne_2024.units_authorized_per_100k is None
    assert anne_2024.population is None
    assert "missing_population" in anne_2024.feature_quality_flags
    assert "construction_proxy_only" in anne_2024.feature_quality_flags


def test_build_contact_pressure_features_treats_blank_population_as_missing(
    tmp_path,
) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)
    _write(
        population,
        [
            "county_fips",
            "county_name",
            "year",
            "population",
            "source_id",
            "census_dataset",
            "vintage",
            "source_url_hash",
        ],
        [
            [
                "24003",
                "Anne Arundel County",
                "2023",
                "",
                "census_population_2023",
                "pep",
                "2023",
                "pop",
            ],
        ],
    )

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2023 = next(row for row in rows if row.county_fips == "24003" and row.year == 2023)
    assert anne_2023.population is None
    assert anne_2023.units_authorized_per_100k is None
    assert "missing_population" in anne_2023.feature_quality_flags


def test_build_contact_pressure_features_flags_blank_land_area(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)
    _write(
        county_reference,
        [
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
        [
            [
                "24003",
                "24",
                "MD",
                "Anne Arundel County",
                "",
                "172.995",
                "38.99",
                "-76.56",
                "Census Gazetteer",
                "geo",
            ],
        ],
    )

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2023 = next(row for row in rows if row.county_fips == "24003" and row.year == 2023)
    assert anne_2023.land_area_sqmi is None
    assert anne_2023.units_authorized_per_sqmi is None
    assert "missing_land_area" in anne_2023.feature_quality_flags


def test_build_contact_pressure_features_flags_missing_land_area(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)
    _write(
        county_reference,
        [
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
        [],
    )

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2023 = next(row for row in rows if row.county_fips == "24003" and row.year == 2023)
    assert anne_2023.land_area_sqmi is None
    assert anne_2023.units_authorized_per_sqmi is None
    assert "missing_land_area" in anne_2023.feature_quality_flags


def test_write_contact_pressure_output_appends_and_dedupes(tmp_path) -> None:
    row = ContactPressureFeature(
        county_fips="24003",
        county_name="Anne Arundel County",
        year=2024,
        residential_units_authorized=120,
        units_authorized_per_sqmi=0.289292,
        units_authorized_per_100k=None,
        total_value_dollars=43000000,
        land_area_sqmi=414.806,
        population=None,
        source_id="census_bps_county_2024",
        source_url_hash="hash2024",
        feature_quality_flags="construction_proxy_only,missing_population",
    )
    replacement = replace(row, residential_units_authorized=121)

    write_contact_pressure_output([row], tmp_path)
    output = write_contact_pressure_output([replacement], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert output.name == "contact_pressure_features_county_year.csv"
    assert list(records[0].keys()) == CONTACT_PRESSURE_COLUMNS
    assert len(records) == 1
    assert records[0]["county_fips"] == "24003"
    assert records[0]["residential_units_authorized"] == "121"


def test_write_contact_pressure_output_normalizes_existing_county_fips(tmp_path) -> None:
    output = tmp_path / "contact_pressure_features_county_year.csv"
    _write(
        output,
        CONTACT_PRESSURE_COLUMNS,
        [
            [
                "2403",
                "Anne Arundel County",
                "2024",
                "120",
                "0.289292",
                "",
                "43000000",
                "414.806",
                "",
                "census_bps_county_2024",
                "hash2024",
                "construction_proxy_only,missing_population",
            ],
        ],
    )

    write_contact_pressure_output([], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert records[0]["county_fips"] == "02403"
