import pytest

from tickbiterisk.etl.maryland import maryland_fips_set
from tickbiterisk.etl.weather_locations import (
    WeatherLocationError,
    load_maryland_weather_locations,
    load_weather_locations,
)


def test_weather_locations_include_all_maryland_jurisdictions() -> None:
    locations = load_maryland_weather_locations()

    assert len(locations) == 24
    assert {row.county_fips for row in locations} == maryland_fips_set()


def test_anne_arundel_weather_location_uses_census_internal_point() -> None:
    locations = load_maryland_weather_locations()
    anne_arundel = next(row for row in locations if row.county_fips == "24003")

    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.state == "MD"
    assert anne_arundel.state_fips == "24"
    assert anne_arundel.centroid_lat == 38.991617
    assert anne_arundel.centroid_lon == -76.560894
    assert anne_arundel.geography_source == "Census Gazetteer 2024 county internal point"


def test_baltimore_city_weather_location_is_present() -> None:
    locations = load_maryland_weather_locations()
    baltimore_city = next(row for row in locations if row.county_fips == "24510")

    assert baltimore_city.county_name == "Baltimore City"
    assert baltimore_city.centroid_lat == 39.300032
    assert baltimore_city.centroid_lon == -76.610476


# --- generalized six-state loader (parameterized, config-driven) -------------

EXPECTED_PER_STATE = {"DE": 3, "DC": 1, "MD": 24, "PA": 67, "VA": 133, "WV": 55}


def test_load_weather_locations_returns_full_six_state_universe() -> None:
    locations = load_weather_locations()
    assert len(locations) == 283
    counts: dict[str, int] = {}
    for row in locations:
        counts[row.state] = counts.get(row.state, 0) + 1
    assert counts == EXPECTED_PER_STATE


def test_load_weather_locations_filters_to_requested_states() -> None:
    # Proves the MD-only rejection is gone: a non-MD state loads on its own.
    pa = load_weather_locations(states=["PA"])
    assert len(pa) == 67
    assert {row.state for row in pa} == {"PA"}
    assert all(row.county_fips.startswith("42") for row in pa)


def test_load_weather_locations_handles_dc_single_district() -> None:
    dc = load_weather_locations(states=["DC"])
    assert len(dc) == 1
    assert dc[0].county_fips == "11001"
    assert dc[0].state == "DC"


def test_load_weather_locations_rejects_state_outside_region() -> None:
    with pytest.raises(WeatherLocationError, match="NY"):
        load_weather_locations(states=["NY"])

