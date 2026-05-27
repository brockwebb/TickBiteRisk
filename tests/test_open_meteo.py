from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from tickbiterisk.etl.open_meteo import (
    OPEN_METEO_ARCHIVE_ENDPOINT,
    OPEN_METEO_DAILY_VARIABLES,
    OpenMeteoArchiveError,
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
    parse_open_meteo_archive_response,
)
from tickbiterisk.etl.weather_locations import WeatherLocation


LOCATION = WeatherLocation(
    county_fips="24003",
    state_fips="24",
    state="MD",
    county_name="Anne Arundel County",
    centroid_lat=38.991617,
    centroid_lon=-76.560894,
    geography_source="Census Gazetteer 2024 county internal point",
)


def open_meteo_payload() -> dict:
    return {
        "daily": {
            "time": ["2020-01-01", "2020-01-02"],
            "temperature_2m_mean": [44.0, 38.0],
            "temperature_2m_max": [51.0, 42.0],
            "temperature_2m_min": [31.0, 28.0],
            "relative_humidity_2m_mean": [88.0, 74.0],
            "relative_humidity_2m_max": [96.0, 85.0],
            "relative_humidity_2m_min": [72.0, 61.0],
            "dew_point_2m_mean": [39.0, 30.0],
            "precipitation_sum": [2.5, 0.0],
            "rain_sum": [2.5, 0.0],
            "snowfall_sum": [0.0, 0.0],
            "precipitation_hours": [4.0, 0.0],
            "soil_temperature_0_to_7cm_mean": [41.0, 36.0],
            "soil_moisture_0_to_7cm_mean": [0.32, 0.28],
            "et0_fao_evapotranspiration": [0.4, 0.6],
            "wind_speed_10m_mean": [5.0, 8.0],
            "wind_speed_10m_max": [12.0, 15.0],
        }
    }


def test_build_open_meteo_archive_url_includes_required_query() -> None:
    url = build_open_meteo_archive_url(
        LOCATION,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    daily_values = query["daily"][0].split(",")

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == OPEN_METEO_ARCHIVE_ENDPOINT
    assert query["latitude"] == ["38.991617"]
    assert query["longitude"] == ["-76.560894"]
    assert query["start_date"] == ["2020-01-01"]
    assert query["end_date"] == ["2020-01-31"]
    assert query["temperature_unit"] == ["fahrenheit"]
    assert query["wind_speed_unit"] == ["mph"]
    assert query["precipitation_unit"] == ["mm"]
    assert query["timezone"] == ["America/New_York"]
    assert set(OPEN_METEO_DAILY_VARIABLES) <= set(daily_values)


def test_parse_open_meteo_archive_response_maps_daily_rows() -> None:
    rows = parse_open_meteo_archive_response(
        open_meteo_payload(),
        location=LOCATION,
        source_url="https://example.test/weather",
        weather_model="open_meteo_archive",
    )

    assert len(rows) == 2
    assert rows[0].county_fips == "24003"
    assert rows[0].date.isoformat() == "2020-01-01"
    assert rows[0].source == "open_meteo_archive"
    assert rows[0].weather_model == "open_meteo_archive"
    assert rows[0].temp_mean_f == 44.0
    assert rows[0].humidity_mean_pct == 88.0
    assert rows[0].precipitation_mm == 2.5
    assert len(rows[0].source_url_hash) == 64


def test_parse_open_meteo_archive_response_converts_snowfall_cm_to_mm() -> None:
    payload = open_meteo_payload()
    payload["daily"]["snowfall_sum"] = [1.2, 0.0]

    rows = parse_open_meteo_archive_response(
        payload,
        location=LOCATION,
        source_url="https://example.test/weather",
        weather_model="open_meteo_archive",
    )

    assert rows[0].snowfall_mm == 12.0


def test_parse_open_meteo_archive_response_preserves_nullable_soil_moisture() -> None:
    payload = open_meteo_payload()
    payload["daily"]["soil_moisture_0_to_7cm_mean"] = [None, 0.28]

    rows = parse_open_meteo_archive_response(
        payload,
        location=LOCATION,
        source_url="https://example.test/weather",
        weather_model="open_meteo_archive",
    )

    assert rows[0].soil_moisture_0_7cm is None
    assert rows[1].soil_moisture_0_7cm == 0.28


def test_parse_open_meteo_archive_response_rejects_null_required_value() -> None:
    payload = open_meteo_payload()
    payload["daily"]["precipitation_sum"] = [None, 0.0]

    with pytest.raises(OpenMeteoArchiveError, match="precipitation_sum.*2020-01-01"):
        parse_open_meteo_archive_response(
            payload,
            location=LOCATION,
            source_url="https://example.test/weather",
            weather_model="open_meteo_archive",
        )


def test_parse_open_meteo_archive_response_rejects_missing_required_variable() -> None:
    payload = {"daily": {"time": ["2020-01-01"]}}

    with pytest.raises(OpenMeteoArchiveError, match="temperature_2m_mean"):
        parse_open_meteo_archive_response(
            payload,
            location=LOCATION,
            source_url="https://example.test/weather",
            weather_model="open_meteo_archive",
        )


def test_parse_open_meteo_archive_response_rejects_mismatched_lengths() -> None:
    payload = {
        "daily": {variable: [1.0, 2.0] for variable in OPEN_METEO_DAILY_VARIABLES}
    }
    payload["daily"]["time"] = ["2020-01-01"]

    with pytest.raises(OpenMeteoArchiveError, match="length"):
        parse_open_meteo_archive_response(
            payload,
            location=LOCATION,
            source_url="https://example.test/weather",
            weather_model="open_meteo_archive",
        )


def test_fetch_open_meteo_archive_uses_injected_json_get() -> None:
    calls: list[str] = []

    def fake_json_get(url: str) -> dict:
        calls.append(url)
        payload = open_meteo_payload()
        payload["daily"] = {
            variable: values[:1] for variable, values in payload["daily"].items()
        }
        return payload

    rows = fetch_open_meteo_archive(
        LOCATION,
        date(2020, 1, 1),
        date(2020, 1, 1),
        json_get=fake_json_get,
        sleep_seconds=0,
    )

    assert len(calls) == 1
    assert rows[0].date.isoformat() == "2020-01-01"
