from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.etl.weather_locations import WeatherLocation

OPEN_METEO_ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_DAILY_VARIABLES = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "dew_point_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
]


class OpenMeteoArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class WeatherDailyObservation:
    county_fips: str
    date: date
    source: str
    weather_model: str
    temp_mean_f: float
    temp_max_f: float
    temp_min_f: float
    humidity_mean_pct: float
    humidity_max_pct: float
    humidity_min_pct: float
    dew_point_mean_f: float
    precipitation_mm: float
    rain_mm: float
    snowfall_mm: float
    precipitation_hours: float
    soil_temp_0_7cm_f: float
    soil_moisture_0_7cm: float
    evapotranspiration_mm: float
    wind_mean_mph: float
    wind_max_mph: float
    source_url_hash: str


def build_open_meteo_archive_url(
    location: WeatherLocation,
    start_date: date,
    end_date: date,
    *,
    weather_model: str = "open_meteo_archive",
) -> str:
    if end_date < start_date:
        raise OpenMeteoArchiveError("end_date must be on or after start_date")

    query = {
        "latitude": f"{location.centroid_lat:.6f}",
        "longitude": f"{location.centroid_lon:.6f}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(OPEN_METEO_DAILY_VARIABLES),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "mm",
        "timezone": "America/New_York",
    }
    if weather_model != "open_meteo_archive":
        query["models"] = weather_model
    return f"{OPEN_METEO_ARCHIVE_ENDPOINT}?{urlencode(query)}"


def parse_open_meteo_archive_response(
    payload: dict[str, Any],
    *,
    location: WeatherLocation,
    source_url: str,
    weather_model: str,
) -> list[WeatherDailyObservation]:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise OpenMeteoArchiveError("Open-Meteo response is missing daily data")

    required = ["time", *OPEN_METEO_DAILY_VARIABLES]
    for variable in required:
        if variable not in daily:
            raise OpenMeteoArchiveError(f"Open-Meteo daily data missing {variable}")

    times = daily["time"]
    if not isinstance(times, list):
        raise OpenMeteoArchiveError("Open-Meteo daily time must be a list")

    expected_length = len(times)
    for variable in OPEN_METEO_DAILY_VARIABLES:
        values = daily[variable]
        if not isinstance(values, list) or len(values) != expected_length:
            raise OpenMeteoArchiveError(
                f"Open-Meteo daily variable {variable} has mismatched length"
            )

    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows: list[WeatherDailyObservation] = []
    for index, raw_date in enumerate(times):
        rows.append(
            WeatherDailyObservation(
                county_fips=location.county_fips,
                date=date.fromisoformat(raw_date),
                source="open_meteo_archive",
                weather_model=weather_model,
                temp_mean_f=float(daily["temperature_2m_mean"][index]),
                temp_max_f=float(daily["temperature_2m_max"][index]),
                temp_min_f=float(daily["temperature_2m_min"][index]),
                humidity_mean_pct=float(daily["relative_humidity_2m_mean"][index]),
                humidity_max_pct=float(daily["relative_humidity_2m_max"][index]),
                humidity_min_pct=float(daily["relative_humidity_2m_min"][index]),
                dew_point_mean_f=float(daily["dew_point_2m_mean"][index]),
                precipitation_mm=float(daily["precipitation_sum"][index]),
                rain_mm=float(daily["rain_sum"][index]),
                snowfall_mm=float(daily["snowfall_sum"][index]),
                precipitation_hours=float(daily["precipitation_hours"][index]),
                soil_temp_0_7cm_f=float(
                    daily["soil_temperature_0_to_7cm_mean"][index]
                ),
                soil_moisture_0_7cm=float(
                    daily["soil_moisture_0_to_7cm_mean"][index]
                ),
                evapotranspiration_mm=float(
                    daily["et0_fao_evapotranspiration"][index]
                ),
                wind_mean_mph=float(daily["wind_speed_10m_mean"][index]),
                wind_max_mph=float(daily["wind_speed_10m_max"][index]),
                source_url_hash=source_url_hash,
            )
        )
    return rows


def _default_json_get(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_open_meteo_archive(
    location: WeatherLocation,
    start_date: date,
    end_date: date,
    *,
    weather_model: str = "open_meteo_archive",
    json_get: Callable[[str], dict[str, Any]] = _default_json_get,
    max_attempts: int = 3,
    sleep_seconds: float = 1.0,
) -> list[WeatherDailyObservation]:
    url = build_open_meteo_archive_url(
        location,
        start_date,
        end_date,
        weather_model=weather_model,
    )
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            payload = json_get(url)
            return parse_open_meteo_archive_response(
                payload,
                location=location,
                source_url=url,
                weather_model=weather_model,
            )
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(sleep_seconds * attempt)
    raise OpenMeteoArchiveError(f"Open-Meteo archive fetch failed: {last_error}")
