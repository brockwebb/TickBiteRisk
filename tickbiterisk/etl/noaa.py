from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class NoaaTokenMissingError(RuntimeError):
    """Raised when the NOAA CDO API token is unavailable."""


NOAA_CDO_ENDPOINT = "https://www.ncei.noaa.gov/cdo-web/api/v2"
NOAA_GHCND_DAILY_TYPES = ["TMAX", "TMIN", "PRCP", "SNOW", "SNWD"]
NOAA_GHCND_DAILY_SOURCE = "noaa_cdo_ghcnd_daily"


@dataclass(frozen=True)
class NoaaStation:
    county_fips: str
    station_id: str
    name: str
    latitude: float
    longitude: float
    mindate: date
    maxdate: date
    data_coverage: float
    elevation: float | None = None
    elevation_unit: str | None = None


@dataclass(frozen=True)
class NoaaDailyObservation:
    county_fips: str
    station_id: str
    date: date
    source: str
    tmax_f: float | None
    tmin_f: float | None
    prcp_inches: float | None
    snow_inches: float | None
    snwd_inches: float | None
    source_url_hash: str


def get_noaa_token(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    token = source.get("NOAA_TOKEN", "").strip()
    if not token:
        raise NoaaTokenMissingError("NOAA_TOKEN is required for NOAA CDO validation")
    return token


def build_noaa_station_url(
    county_fips: str,
    start_date: date,
    end_date: date,
    *,
    limit: int = 1000,
    offset: int | None = None,
) -> str:
    query = {
        "datasetid": "GHCND",
        "locationid": f"FIPS:{county_fips.zfill(5)}",
        "startdate": start_date.isoformat(),
        "enddate": end_date.isoformat(),
        "limit": str(limit),
    }
    if offset is not None:
        query["offset"] = str(offset)
    return f"{NOAA_CDO_ENDPOINT}/stations?{urlencode(query)}"


def build_noaa_daily_data_url(
    station_id: str,
    start_date: date,
    end_date: date,
    *,
    datatypes: list[str] | None = None,
    limit: int = 1000,
    offset: int | None = None,
) -> str:
    query_items = [
        ("datasetid", "GHCND"),
        ("stationid", station_id),
        ("startdate", start_date.isoformat()),
        ("enddate", end_date.isoformat()),
        ("units", "standard"),
        ("limit", str(limit)),
    ]
    if offset is not None:
        query_items.append(("offset", str(offset)))
    for datatype in datatypes or NOAA_GHCND_DAILY_TYPES:
        query_items.append(("datatypeid", datatype))
    return f"{NOAA_CDO_ENDPOINT}/data?{urlencode(query_items)}"


def parse_noaa_station_response(
    payload: dict[str, Any], *, county_fips: str
) -> list[NoaaStation]:
    stations: list[NoaaStation] = []
    for row in payload.get("results", []):
        stations.append(
            NoaaStation(
                county_fips=county_fips.zfill(5),
                station_id=row["id"],
                name=row["name"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                mindate=date.fromisoformat(row["mindate"]),
                maxdate=date.fromisoformat(row["maxdate"]),
                data_coverage=float(row.get("datacoverage", 0.0)),
                elevation=_nullable_float(row.get("elevation")),
                elevation_unit=row.get("elevationUnit"),
            )
        )
    return stations


def select_long_coverage_stations(
    stations: list[NoaaStation],
    *,
    start_date: date,
    end_date: date,
    min_data_coverage: float = 0.5,
    max_end_lag_days: int = 0,
) -> list[NoaaStation]:
    latest_allowed_date = end_date - timedelta(days=max_end_lag_days)
    eligible = [
        station
        for station in stations
        if station.mindate <= start_date
        and station.maxdate >= latest_allowed_date
        and station.data_coverage >= min_data_coverage
    ]
    return sorted(
        eligible,
        key=lambda station: (
            -station.data_coverage,
            station.mindate,
            -_coverage_days(station),
            station.station_id,
        ),
    )


def parse_noaa_daily_data_response(
    payload: dict[str, Any], *, county_fips: str, source_url: str
) -> list[NoaaDailyObservation]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    grouped: dict[tuple[str, date], dict[str, float | None]] = {}
    for row in payload.get("results", []):
        observed_date = date.fromisoformat(row["date"][:10])
        key = (row["station"], observed_date)
        grouped.setdefault(key, {})
        grouped[key][row["datatype"]] = _nullable_float(row.get("value"))

    output: list[NoaaDailyObservation] = []
    for (station_id, observed_date), values in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        output.append(
            NoaaDailyObservation(
                county_fips=county_fips.zfill(5),
                station_id=station_id,
                date=observed_date,
                source=NOAA_GHCND_DAILY_SOURCE,
                tmax_f=values.get("TMAX"),
                tmin_f=values.get("TMIN"),
                prcp_inches=values.get("PRCP"),
                snow_inches=values.get("SNOW"),
                snwd_inches=values.get("SNWD"),
                source_url_hash=source_url_hash,
            )
        )
    return output


def fetch_noaa_json(url: str, *, token: str) -> dict[str, Any]:
    request = Request(url, headers={"token": token, "User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_noaa_stations(
    county_fips: str,
    start_date: date,
    end_date: date,
    *,
    token: str,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> list[NoaaStation]:
    pages = _fetch_noaa_pages(
        lambda offset: build_noaa_station_url(
            county_fips,
            start_date,
            end_date,
            offset=offset,
        ),
        token=token,
        json_get=json_get,
    )
    combined_payload = {
        "results": [
            result
            for payload, _url in pages
            for result in payload.get("results", [])
        ]
    }
    return parse_noaa_station_response(combined_payload, county_fips=county_fips)


def fetch_noaa_daily_observations(
    county_fips: str,
    station_id: str,
    start_date: date,
    end_date: date,
    *,
    token: str,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> list[NoaaDailyObservation]:
    source_url = build_noaa_daily_data_url(station_id, start_date, end_date)
    pages: list[tuple[dict[str, Any], str]] = []
    for window_start, window_end in _calendar_year_windows(start_date, end_date):
        pages.extend(
            _fetch_noaa_pages(
                lambda offset, window_start=window_start, window_end=window_end: (
                    build_noaa_daily_data_url(
                        station_id,
                        window_start,
                        window_end,
                        offset=offset,
                    )
                ),
                token=token,
                json_get=json_get,
            )
        )
    combined_payload = {
        "results": [
            result
            for payload, _url in pages
            for result in payload.get("results", [])
        ]
    }
    return parse_noaa_daily_data_response(
        combined_payload,
        county_fips=county_fips,
        source_url=source_url,
    )


def _coverage_days(station: NoaaStation) -> int:
    return (station.maxdate - station.mindate).days


def _calendar_year_windows(start_date: date, end_date: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    window_start = start_date
    while window_start <= end_date:
        window_end = min(date(window_start.year, 12, 31), end_date)
        windows.append((window_start, window_end))
        window_start = date(window_start.year + 1, 1, 1)
    return windows


def _fetch_with_getter(
    url: str,
    *,
    token: str,
    json_get: Callable[[str, str], dict[str, Any]] | None,
) -> dict[str, Any]:
    if json_get is not None:
        return json_get(url, token)
    return fetch_noaa_json(url, token=token)


def _fetch_noaa_pages(
    build_url: Callable[[int], str],
    *,
    token: str,
    json_get: Callable[[str, str], dict[str, Any]] | None,
) -> list[tuple[dict[str, Any], str]]:
    pages: list[tuple[dict[str, Any], str]] = []
    offset = 1
    while True:
        url = build_url(offset)
        payload = _fetch_with_getter(url, token=token, json_get=json_get)
        pages.append((payload, url))

        resultset = payload.get("metadata", {}).get("resultset")
        if not resultset:
            break

        current_offset = int(resultset.get("offset", offset))
        count = int(resultset.get("count", 0))
        limit = int(resultset.get("limit", 1000))
        if current_offset + limit > count:
            break
        offset = current_offset + limit
    return pages


def _nullable_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
