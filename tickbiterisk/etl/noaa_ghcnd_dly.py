"""GHCND .dly bulk-file acquisition: one request per station, full period of record.

The NOAA CDO Web API caps responses at 1000 records and a one-year date window,
so a multi-decade county pull costs tens of requests per station. The GHCND
``.dly`` station files instead return a station's entire history in a single,
un-rate-limited HTTP GET. This module parses that fixed-width format into the
same :class:`NoaaDailyObservation` schema/units the CDO path emits, so it feeds
the existing weather-feature pipeline unchanged.

Format reference: ``ncei.noaa.gov/pub/data/ghcn/daily/readme.txt``. Each line is
one station/year/month/element. Layout (1-indexed): ID 1-11, YEAR 12-15,
MONTH 16-17, ELEMENT 18-21, then 31 day fields of VALUE(5) MFLAG(1) QFLAG(1)
SFLAG(1). VALUE -9999 is the missing sentinel; a non-blank QFLAG means the value
failed a quality check and is treated as missing.

Units in .dly are metric (tenths of degrees C for TMAX/TMIN; tenths of mm for
PRCP; mm for SNOW/SNWD); we convert to the degrees-F / inches the pipeline uses.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date
from urllib.request import Request, urlopen

from tickbiterisk.etl.noaa import NoaaDailyObservation

# Bulk daily station files live under the GHCN-Daily "all" directory.
GHCND_DLY_BASE_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all"
GHCND_DLY_SOURCE = "noaa_ghcnd_dly_bulk"

_MISSING_VALUE = -9999
_TENTHS_C_ELEMENTS = {"TMAX", "TMIN"}
_TENTHS_MM_ELEMENTS = {"PRCP"}
_MM_ELEMENTS = {"SNOW", "SNWD"}
_SUPPORTED_ELEMENTS = _TENTHS_C_ELEMENTS | _TENTHS_MM_ELEMENTS | _MM_ELEMENTS

# Map GHCND element code -> NoaaDailyObservation attribute.
_ELEMENT_FIELD = {
    "TMAX": "tmax_f",
    "TMIN": "tmin_f",
    "PRCP": "prcp_inches",
    "SNOW": "snow_inches",
    "SNWD": "snwd_inches",
}


def _bare_station_id(station_id: str) -> str:
    """Strip the CDO ``GHCND:`` prefix to get the bare GHCND station id."""
    return station_id.split(":", 1)[1] if ":" in station_id else station_id


def build_ghcnd_dly_url(station_id: str) -> str:
    return f"{GHCND_DLY_BASE_URL}/{_bare_station_id(station_id)}.dly"


def _convert(element: str, raw_value: int) -> float | None:
    if raw_value == _MISSING_VALUE:
        return None
    if element in _TENTHS_C_ELEMENTS:
        celsius = raw_value / 10.0
        return round(celsius * 9.0 / 5.0 + 32.0, 1)
    if element in _TENTHS_MM_ELEMENTS:
        millimeters = raw_value / 10.0
        return round(millimeters / 25.4, 2)
    if element in _MM_ELEMENTS:
        return round(raw_value / 25.4, 2)
    return None


def parse_ghcnd_dly_text(
    text: str,
    *,
    county_fips: str,
    station_id: str,
    source_url: str,
    start_date: date,
    end_date: date,
    datatypes: list[str] | None = None,
) -> list[NoaaDailyObservation]:
    """Parse a station ``.dly`` file into daily observations within a date window."""
    wanted = set(datatypes) if datatypes else set(_SUPPORTED_ELEMENTS)
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    normalized_fips = county_fips.zfill(5)

    # date -> {field_name: value}
    grouped: dict[date, dict[str, float | None]] = {}
    for line in text.splitlines():
        if len(line) < 21:
            continue
        element = line[17:21].strip()
        if element not in wanted or element not in _ELEMENT_FIELD:
            continue
        year = int(line[11:15])
        month = int(line[15:17])
        for day_index in range(31):
            offset = 21 + day_index * 8
            field = line[offset : offset + 8]
            if len(field) < 8:
                break
            raw = field[0:5].strip()
            if not raw:
                continue
            qflag = field[6]
            try:
                observed = date(year, month, day_index + 1)
            except ValueError:
                continue  # e.g. Feb 30 / Apr 31 slots
            if observed < start_date or observed > end_date:
                continue
            try:
                raw_value = int(raw)
            except ValueError:
                continue
            if raw_value == _MISSING_VALUE:
                continue  # no measurement reported for this day/element
            # A real measurement exists; a non-blank QFLAG means it failed QC and
            # is unusable, so the day is recorded but the value is None.
            value = None if qflag != " " else _convert(element, raw_value)
            grouped.setdefault(observed, {})[_ELEMENT_FIELD[element]] = value

    observations: list[NoaaDailyObservation] = []
    for observed in sorted(grouped):
        values = grouped[observed]
        observations.append(
            NoaaDailyObservation(
                county_fips=normalized_fips,
                station_id=station_id,
                date=observed,
                source=GHCND_DLY_SOURCE,
                tmax_f=values.get("tmax_f"),
                tmin_f=values.get("tmin_f"),
                prcp_inches=values.get("prcp_inches"),
                snow_inches=values.get("snow_inches"),
                snwd_inches=values.get("snwd_inches"),
                source_url_hash=source_url_hash,
            )
        )
    return observations


def fetch_ghcnd_dly_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=120) as response:  # noqa: S310 (trusted NCEI host)
        return response.read().decode("utf-8")


def fetch_ghcnd_dly_observations(
    county_fips: str,
    station_id: str,
    start_date: date,
    end_date: date,
    *,
    datatypes: list[str] | None = None,
    http_get: Callable[[str], str] | None = None,
) -> list[NoaaDailyObservation]:
    """Fetch and parse one station's full ``.dly`` history within a window."""
    url = build_ghcnd_dly_url(station_id)
    getter = http_get or fetch_ghcnd_dly_text
    text = getter(url)
    return parse_ghcnd_dly_text(
        text,
        county_fips=county_fips,
        station_id=station_id,
        source_url=url,
        start_date=start_date,
        end_date=end_date,
        datatypes=datatypes,
    )
