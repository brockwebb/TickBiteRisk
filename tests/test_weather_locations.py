from tickbiterisk.etl.maryland import maryland_fips_set
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations


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
