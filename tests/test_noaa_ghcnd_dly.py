"""Tests for the GHCND .dly fixed-width bulk parser (time-series acquisition path).

The .dly station files give a station's entire period of record in one request.
The parser must emit the same NoaaDailyObservation schema/units as the CDO path
(temperatures in degrees F, precip/snow in inches) so it feeds the existing
weather-feature pipeline unchanged.
"""

from __future__ import annotations

from datetime import date

from tickbiterisk.etl.noaa_ghcnd_dly import (
    build_ghcnd_dly_url,
    parse_ghcnd_dly_text,
)


def _dly_line(station_id: str, year: int, month: int, element: str, day_values):
    """Build one fixed-width .dly line.

    day_values: dict {day_number: (value:int, qflag:str)}. Days not provided are
    encoded as the -9999 missing sentinel with blank flags.
    """
    line = f"{station_id:<11}{year:04d}{month:02d}{element:<4}"
    for day in range(1, 32):
        value, qflag = day_values.get(day, (-9999, " "))
        line += f"{value:5d}" + " " + qflag + " "  # VALUE(5) MFLAG(1) QFLAG(1) SFLAG(1)
    return line


STATION = "USC00180700"


def test_parses_five_elements_into_one_observation_with_unit_conversions():
    text = "\n".join(
        [
            _dly_line(STATION, 2019, 1, "TMAX", {1: (100, " ")}),  # 10.0 C -> 50.0 F
            _dly_line(STATION, 2019, 1, "TMIN", {1: (0, " ")}),    # 0.0 C  -> 32.0 F
            _dly_line(STATION, 2019, 1, "PRCP", {1: (254, " ")}),  # 25.4 mm -> 1.0 in
            _dly_line(STATION, 2019, 1, "SNOW", {1: (254, " ")}),  # 254 mm  -> 10.0 in
            _dly_line(STATION, 2019, 1, "SNWD", {1: (-9999, " ")}),  # missing -> None
        ]
    )
    rows = parse_ghcnd_dly_text(
        text,
        county_fips="24001",
        station_id=f"GHCND:{STATION}",
        source_url=f"https://example/{STATION}.dly",
        start_date=date(2019, 1, 1),
        end_date=date(2019, 1, 31),
    )
    obs = {row.date: row for row in rows}
    jan1 = obs[date(2019, 1, 1)]
    assert jan1.county_fips == "24001"
    assert jan1.station_id == f"GHCND:{STATION}"
    assert jan1.tmax_f == 50.0
    assert jan1.tmin_f == 32.0
    assert jan1.prcp_inches == 1.0
    assert jan1.snow_inches == 10.0
    assert jan1.snwd_inches is None  # -9999 sentinel


def test_failed_quality_flag_is_treated_as_missing():
    # QFLAG non-blank means the value failed a QC check -> must be None, not used.
    text = _dly_line(STATION, 2019, 1, "TMAX", {1: (100, "G")})  # G = failed gap check
    rows = parse_ghcnd_dly_text(
        text,
        county_fips="24001",
        station_id=STATION,
        source_url="u",
        start_date=date(2019, 1, 1),
        end_date=date(2019, 1, 31),
    )
    assert rows[0].tmax_f is None


def test_dates_outside_window_are_excluded():
    text = "\n".join(
        [
            _dly_line(STATION, 2019, 1, "TMAX", {1: (100, " "), 2: (110, " ")}),
        ]
    )
    rows = parse_ghcnd_dly_text(
        text,
        county_fips="24001",
        station_id=STATION,
        source_url="u",
        start_date=date(2019, 1, 2),
        end_date=date(2019, 1, 31),
    )
    assert [r.date for r in rows] == [date(2019, 1, 2)]


def test_invalid_calendar_days_are_skipped_not_crashed():
    # February has 28 days in 2019; day slots 29-31 carry sentinels and must not
    # raise when constructing dates.
    text = _dly_line(STATION, 2019, 2, "TMAX", {1: (100, " "), 31: (120, " ")})
    rows = parse_ghcnd_dly_text(
        text,
        county_fips="24001",
        station_id=STATION,
        source_url="u",
        start_date=date(2019, 1, 1),
        end_date=date(2019, 12, 31),
    )
    assert [r.date for r in rows] == [date(2019, 2, 1)]


def test_build_ghcnd_dly_url_strips_ghcnd_prefix():
    url = build_ghcnd_dly_url("GHCND:USC00180700")
    assert url.endswith("/USC00180700.dly")
    assert "GHCND:" not in url
