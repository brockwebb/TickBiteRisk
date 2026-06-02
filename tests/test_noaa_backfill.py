from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tickbiterisk.etl.noaa import NoaaDailyObservation
from tickbiterisk.etl.noaa_backfill import (
    NoaaBackfillCountyFipsError,
    NoaaBackfillDateRangeError,
    NoaaBackfillNoStationError,
    audit_noaa_station_coverage,
    run_noaa_county_backfill,
    run_noaa_maryland_backfill,
    run_noaa_regional_backfill,
)


def _long_coverage_station_json(url: str, token: str) -> dict:
    """Station response with one long-coverage station; daily handled elsewhere."""
    if "stations?" in url:
        return {
            "results": [
                {
                    "id": "GHCND:LONG",
                    "name": "LONG COVERAGE",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "1990-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 1.0,
                }
            ]
        }
    raise AssertionError(f"daily data must not go through json_get: {url}")


def _one_obs(county_fips, station_id, start_date, end_date):
    return [
        NoaaDailyObservation(
            county_fips=county_fips,
            station_id=station_id,
            date=date(2019, 1, 1),
            source="noaa_ghcnd_dly_bulk",
            tmax_f=50.0,
            tmin_f=32.0,
            prcp_inches=1.0,
            snow_inches=0.0,
            snwd_inches=None,
            source_url_hash="hash",
        )
    ]


def test_run_noaa_county_backfill_uses_injected_daily_fetcher(tmp_path: Path) -> None:
    fetched: list[str] = []

    def fake_daily_fetcher(county_fips, station_id, start_date, end_date):
        fetched.append(station_id)
        return _one_obs(county_fips, station_id, start_date, end_date)

    result = run_noaa_county_backfill(
        county_fips="10001",
        start_date=date(2017, 1, 1),
        end_date=date(2021, 12, 31),
        output_dir=tmp_path,
        token="fake-token",
        json_get=_long_coverage_station_json,
        daily_fetcher=fake_daily_fetcher,
    )

    assert fetched == ["GHCND:LONG"]  # injected fetcher used, not CDO /data
    assert result.daily_observation_count == 1
    assert result.daily_output_path.exists()


def test_temp_maxdate_in_window_ignores_non_temp_rows() -> None:
    from tickbiterisk.etl.noaa import NoaaDailyObservation
    from tickbiterisk.etl.noaa_backfill import temp_maxdate

    rows = [
        NoaaDailyObservation("10001", "S", date(2007, 6, 1), "x", 50.0, 32.0,
                             0.0, 0.0, None, "h"),
        # later row but PRCP only (no temp) -> must not count toward temp maxdate
        NoaaDailyObservation("10001", "S", date(2021, 6, 1), "x", None, None,
                             0.1, 0.0, None, "h"),
    ]
    assert temp_maxdate(rows) == date(2007, 6, 1)


def test_select_validated_dly_station_skips_temp_dead_station() -> None:
    # First (nearest) station has TMAX/TMIN ending 2007; must be rejected for a
    # 2021 window in favor of the next candidate with live temp data.
    from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation
    from tickbiterisk.etl.noaa_backfill import select_validated_dly_station

    def mk_station(sid):
        return NoaaStation("10001", sid, sid, 39.0, -75.0,
                           date(1990, 1, 1), date(2026, 1, 1), 0.9)

    dead, live = mk_station("GHCND:DEAD"), mk_station("GHCND:LIVE")

    def fetcher(county_fips, station_id, start_date, end_date):
        end = date(2007, 12, 31) if station_id == "GHCND:DEAD" else date(2021, 12, 31)
        return [
            NoaaDailyObservation(county_fips, station_id, date(2000, 1, 1), "x",
                                 50.0, 32.0, 0.0, 0.0, None, "h"),
            NoaaDailyObservation(county_fips, station_id, end, "x",
                                 50.0, 32.0, 0.0, 0.0, None, "h"),
        ]

    station, rows = select_validated_dly_station(
        [dead, live],
        county_fips="10001",
        daily_fetcher=fetcher,
        acquire_start=date(2017, 1, 1),
        acquire_end=date(2021, 12, 31),
        validate_window_start=date(2017, 1, 1),
        validate_window_end=date(2021, 12, 31),
    )
    assert station is not None and station.station_id == "GHCND:LIVE"
    assert rows


def test_select_validated_dly_station_returns_none_when_all_temp_dead() -> None:
    from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation
    from tickbiterisk.etl.noaa_backfill import select_validated_dly_station

    s = NoaaStation("10001", "GHCND:DEAD", "x", 39.0, -75.0,
                    date(1990, 1, 1), date(2026, 1, 1), 0.9)

    def fetcher(county_fips, station_id, start_date, end_date):
        return [NoaaDailyObservation(county_fips, station_id, date(2007, 1, 1), "x",
                                     50.0, 32.0, 0.0, 0.0, None, "h")]

    station, rows = select_validated_dly_station(
        [s],
        county_fips="10001",
        daily_fetcher=fetcher,
        acquire_start=date(2017, 1, 1),
        acquire_end=date(2021, 12, 31),
        validate_window_start=date(2017, 1, 1),
        validate_window_end=date(2021, 12, 31),
    )
    assert station is None and rows == []


def test_fallback_distance_resolves_non_maryland_county_centroid() -> None:
    # Regression: the nearest-station fallback resolved county centroids from the
    # Maryland-only locations, raising KeyError for DE/DC/PA/VA/WV counties.
    from tickbiterisk.etl.noaa import NoaaStation
    from tickbiterisk.etl.noaa_backfill import _station_distance_to_county_miles

    station = NoaaStation(
        county_fips="51820",
        station_id="GHCND:X",
        name="X",
        latitude=38.07,
        longitude=-78.90,
        mindate=date(1990, 1, 1),
        maxdate=date(2026, 1, 1),
        data_coverage=0.9,
    )
    miles = _station_distance_to_county_miles("51820", station)  # VA city, not MD
    assert miles >= 0.0


def test_run_noaa_county_backfill_validated_skips_temp_dead_internal(tmp_path: Path) -> None:
    # Internal station is temp-dead (ends 2007); a live fallback exists.
    from tickbiterisk.etl.noaa import NoaaStation

    def stations_json(url, token):
        if "stations?" in url:
            return {"results": [{"id": "GHCND:DEAD", "name": "DEAD", "latitude": 39.0,
                                 "longitude": -76.0, "mindate": "1990-01-01",
                                 "maxdate": "2026-01-01", "datacoverage": 1.0}]}
        raise AssertionError(url)

    live_fallback = NoaaStation("99999", "GHCND:LIVE", "LIVE", 39.1, -76.1,
                                date(1990, 1, 1), date(2026, 1, 1), 0.95)

    def fetcher(county_fips, station_id, start_date, end_date):
        end = date(2007, 12, 31) if station_id == "GHCND:DEAD" else date(2021, 12, 31)
        return [NoaaDailyObservation(county_fips, station_id, end, "x",
                                     50.0, 32.0, 0.0, 0.0, None, "h")]

    result = run_noaa_county_backfill(
        county_fips="10001",
        start_date=date(1992, 1, 1),
        end_date=date(2021, 12, 31),
        output_dir=tmp_path,
        token="t",
        json_get=stations_json,
        daily_fetcher=fetcher,
        fallback_stations=[live_fallback],
        validate_temp_window_end=date(2021, 12, 31),
    )
    assert result.selected_station_ids == ["GHCND:LIVE"]  # temp-dead internal rejected


def test_run_noaa_county_backfill_validated_raises_when_all_temp_dead(tmp_path: Path) -> None:
    def stations_json(url, token):
        if "stations?" in url:
            return {"results": [{"id": "GHCND:DEAD", "name": "DEAD", "latitude": 39.0,
                                 "longitude": -76.0, "mindate": "1990-01-01",
                                 "maxdate": "2026-01-01", "datacoverage": 1.0}]}
        raise AssertionError(url)

    def fetcher(county_fips, station_id, start_date, end_date):
        return [NoaaDailyObservation(county_fips, station_id, date(2007, 1, 1), "x",
                                     50.0, 32.0, 0.0, 0.0, None, "h")]

    with pytest.raises(NoaaBackfillNoStationError):
        run_noaa_county_backfill(
            county_fips="10001",
            start_date=date(1992, 1, 1),
            end_date=date(2021, 12, 31),
            output_dir=tmp_path,
            token="t",
            json_get=stations_json,
            daily_fetcher=fetcher,
            validate_temp_window_end=date(2021, 12, 31),
        )


def test_run_noaa_regional_backfill_loops_multiple_counties(tmp_path: Path) -> None:
    result = run_noaa_regional_backfill(
        county_fips_values=["10001", "11001"],
        start_date=date(2017, 1, 1),
        end_date=date(2021, 12, 31),
        output_dir=tmp_path,
        token="fake-token",
        json_get=_long_coverage_station_json,
        daily_fetcher=_one_obs,
    )

    assert result.county_count == 2
    assert result.success_count == 2
    assert result.failure_count == 0
    assert {r.county_fips for r in result.county_results} == {"10001", "11001"}


def test_run_noaa_county_backfill_selects_station_and_writes_outputs(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:SHORT",
                        "name": "SHORT COVERAGE",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "2010-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 1.0,
                    },
                    {
                        "id": "GHCND:BWI",
                        "name": "BWI",
                        "latitude": 39.1733,
                        "longitude": -76.684,
                        "mindate": "1939-07-01",
                        "maxdate": "2026-05-20",
                        "datacoverage": 0.9999,
                    },
                ]
            }
        if "stationid=GHCND%3ABWI" in url:
            return {
                "results": [
                    {
                        "date": "1992-05-01T00:00:00",
                        "datatype": "TMAX",
                        "station": "GHCND:BWI",
                        "value": 72.0,
                    },
                    {
                        "date": "1992-05-01T00:00:00",
                        "datatype": "TMIN",
                        "station": "GHCND:BWI",
                        "value": 44.0,
                    },
                ]
            }
        raise AssertionError(f"unexpected NOAA URL: {url}")

    result = run_noaa_county_backfill(
        county_fips="24003",
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        json_get=fake_json_get,
    )

    assert result.county_fips == "24003"
    assert result.selected_station_ids == ["GHCND:BWI"]
    assert result.daily_observation_count == 1
    assert any("stations?" in call for call in calls)
    assert any("stationid=GHCND%3ABWI" in call for call in calls)
    assert not any("stationid=GHCND%3ASHORT" in call for call in calls)

    stations = pd.read_csv(tmp_path / "noaa_ghcnd_stations.csv", dtype={"county_fips": str})
    daily = pd.read_csv(
        tmp_path / "noaa_ghcnd_daily_observations.csv",
        dtype={"county_fips": str},
    )

    assert list(stations["station_id"]) == ["GHCND:BWI"]
    assert list(daily["station_id"]) == ["GHCND:BWI"]
    assert list(daily["date"]) == ["1992-05-01"]
    assert list(daily["tmax_f"]) == [72.0]


def test_run_noaa_county_backfill_raises_when_no_station_covers_range(
    tmp_path: Path,
) -> None:
    def fake_json_get(url: str, token: str) -> dict:
        return {
            "results": [
                {
                    "id": "GHCND:SHORT",
                    "name": "SHORT COVERAGE",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "2010-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 1.0,
                }
            ]
        }

    with pytest.raises(NoaaBackfillNoStationError) as exc_info:
        run_noaa_county_backfill(
            county_fips="24003",
            start_date=date(1992, 1, 1),
            end_date=date(2026, 5, 24),
            output_dir=tmp_path,
            token="token-value",
            json_get=fake_json_get,
        )

    assert "No NOAA GHCND station covers county_fips=24003" in str(exc_info.value)
    assert not (tmp_path / "noaa_ghcnd_stations.csv").exists()
    assert not (tmp_path / "noaa_ghcnd_daily_observations.csv").exists()


def test_run_noaa_county_backfill_rejects_inverted_date_range(tmp_path: Path) -> None:
    with pytest.raises(NoaaBackfillDateRangeError) as exc_info:
        run_noaa_county_backfill(
            county_fips="24003",
            start_date=date(2026, 5, 24),
            end_date=date(1992, 1, 1),
            output_dir=tmp_path,
            token="token-value",
            json_get=lambda url, token: {"results": []},
        )

    assert "end_date must be on or after start_date" in str(exc_info.value)
    assert not (tmp_path / "noaa_ghcnd_stations.csv").exists()


def test_run_noaa_county_backfill_fetches_multiple_selected_stations(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:FIRST",
                        "name": "FIRST",
                        "latitude": 39.1,
                        "longitude": -76.1,
                        "mindate": "1939-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.95,
                    },
                    {
                        "id": "GHCND:SECOND",
                        "name": "SECOND",
                        "latitude": 39.2,
                        "longitude": -76.2,
                        "mindate": "1940-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.90,
                    },
                ]
            }
        station = "GHCND:FIRST" if "GHCND%3AFIRST" in url else "GHCND:SECOND"
        value = 70.0 if station == "GHCND:FIRST" else 65.0
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": station,
                    "value": value,
                }
            ]
        }

    result = run_noaa_county_backfill(
        county_fips="24003",
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        station_limit=2,
        json_get=fake_json_get,
    )

    assert result.selected_station_ids == ["GHCND:FIRST", "GHCND:SECOND"]
    assert result.daily_observation_count == 2
    assert result.daily_observation_count_by_station == {
        "GHCND:FIRST": 1,
        "GHCND:SECOND": 1,
    }
    assert any("stationid=GHCND%3AFIRST" in call for call in calls)
    assert any("stationid=GHCND%3ASECOND" in call for call in calls)


def test_run_noaa_county_backfill_uses_nearest_fallback_station(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:SHORT",
                        "name": "SHORT",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "2010-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 1.0,
                    }
                ]
            }
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:NEAR",
                    "value": 70.0,
                }
            ]
        }

    fallback_stations = [
        _station("GHCND:FAR", latitude=38.0, longitude=-75.0),
        _station("GHCND:NEAR", latitude=39.17, longitude=-76.68),
    ]

    result = run_noaa_county_backfill(
        county_fips="24003",
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        fallback_stations=fallback_stations,
        json_get=fake_json_get,
    )

    assert result.selection_method == "nearest_maryland"
    assert result.selected_station_ids == ["GHCND:NEAR"]
    assert any("stationid=GHCND%3ANEAR" in call for call in calls)
    assert not any("stationid=GHCND%3AFAR" in call for call in calls)

    stations = pd.read_csv(tmp_path / "noaa_ghcnd_stations.csv", dtype={"county_fips": str})
    assert list(stations["county_fips"]) == ["24003"]
    assert list(stations["station_id"]) == ["GHCND:NEAR"]


def test_run_noaa_maryland_backfill_runs_requested_county_subset(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        county = "24003" if "FIPS%3A24003" in url or "stationid=GHCND%3AMD24003" in url else "24005"
        station_id = f"GHCND:MD{county}"
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": station_id,
                        "name": f"STATION {county}",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "1939-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.99,
                    }
                ]
            }
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": station_id,
                    "value": 72.0,
                }
            ]
        }

    result = run_noaa_maryland_backfill(
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003", "24005"],
        json_get=fake_json_get,
    )

    assert result.county_count == 2
    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.daily_observation_count == 2
    assert [row.county_fips for row in result.county_results] == ["24003", "24005"]
    assert any("FIPS%3A24003" in call for call in calls)
    assert any("FIPS%3A24005" in call for call in calls)

    daily = pd.read_csv(
        tmp_path / "noaa_ghcnd_daily_observations.csv",
        dtype={"county_fips": str},
    )
    assert list(daily["county_fips"]) == ["24003", "24005"]


def test_run_noaa_maryland_backfill_records_county_failures_and_continues(
    tmp_path: Path,
) -> None:
    def fake_json_get(url: str, token: str) -> dict:
        if "FIPS%3A24003" in url:
            return {"results": []}
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:MD24005",
                        "name": "STATION 24005",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "1939-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.99,
                    }
                ]
            }
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:MD24005",
                    "value": 72.0,
                }
            ]
        }

    result = run_noaa_maryland_backfill(
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003", "24005"],
        json_get=fake_json_get,
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.failures[0].county_fips == "24003"
    assert "No NOAA GHCND station covers county_fips=24003" in result.failures[0].error
    assert result.county_results[0].county_fips == "24005"


def test_run_noaa_maryland_backfill_records_unexpected_county_failures(
    tmp_path: Path,
) -> None:
    def fake_json_get(url: str, token: str) -> dict:
        if "FIPS%3A24003" in url:
            raise ValueError("NOAA payload changed shape")
        if "stations?" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:MD24005",
                        "name": "STATION 24005",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "1939-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.99,
                    }
                ]
            }
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:MD24005",
                    "value": 72.0,
                }
            ]
        }

    result = run_noaa_maryland_backfill(
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 1),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003", "24005"],
        json_get=fake_json_get,
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.failures[0].county_fips == "24003"
    assert result.failures[0].error == "ValueError: NOAA payload changed shape"


def test_run_noaa_maryland_backfill_rejects_non_maryland_fips(tmp_path: Path) -> None:
    with pytest.raises(NoaaBackfillCountyFipsError) as exc_info:
        run_noaa_maryland_backfill(
            start_date=date(1992, 5, 1),
            end_date=date(1992, 5, 1),
            output_dir=tmp_path,
            token="token-value",
            county_fips_values=["99999"],
            json_get=lambda url, token: {"results": []},
        )

    assert "Unknown Maryland county FIPS: 99999" in str(exc_info.value)


def test_audit_noaa_station_coverage_writes_county_report(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        county = "24003" if "FIPS%3A24003" in url else "24005"
        return {
            "results": [
                {
                    "id": f"GHCND:BEST{county}",
                    "name": f"BEST {county}",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "1939-01-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 0.99,
                },
                {
                    "id": f"GHCND:SHORT{county}",
                    "name": f"SHORT {county}",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "2010-01-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 1.0,
                },
            ]
        }

    result = audit_noaa_station_coverage(
        start_date=date(1992, 1, 1),
        end_date=date(2026, 5, 24),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003", "24005"],
        json_get=fake_json_get,
    )

    assert result.output_path == tmp_path / "noaa_station_coverage_audit.csv"
    assert result.ok_count == 2
    assert result.needs_fallback_count == 0
    assert result.error_count == 0
    assert any("FIPS%3A24003" in call for call in calls)
    assert any("FIPS%3A24005" in call for call in calls)

    df = pd.read_csv(result.output_path, dtype={"county_fips": str})
    assert list(df["county_fips"]) == ["24003", "24005"]
    assert list(df["status"]) == ["ok", "ok"]
    assert list(df["candidate_station_count"]) == [2, 2]
    assert list(df["selected_station_ids"]) == [
        "GHCND:BEST24003",
        "GHCND:BEST24005",
    ]
    assert list(df["best_station_id"]) == ["GHCND:BEST24003", "GHCND:BEST24005"]


def test_audit_noaa_station_coverage_records_no_selected_station(
    tmp_path: Path,
) -> None:
    def fake_json_get(url: str, token: str) -> dict:
        return {
            "results": [
                {
                    "id": "GHCND:SHORT",
                    "name": "SHORT",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "2010-01-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 1.0,
                }
            ]
        }

    result = audit_noaa_station_coverage(
        start_date=date(1992, 1, 1),
        end_date=date(2026, 5, 24),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003"],
        json_get=fake_json_get,
    )

    df = pd.read_csv(result.output_path, dtype={"county_fips": str})
    assert result.ok_count == 0
    assert result.needs_fallback_count == 1
    assert df.loc[0, "status"] == "needs_fallback"
    assert int(df.loc[0, "candidate_station_count"]) == 1
    assert "No selected station covers requested range" in df.loc[0, "error"]


def test_audit_noaa_station_coverage_can_use_nearest_fallback(tmp_path: Path) -> None:
    def fake_json_get(url: str, token: str) -> dict:
        if "FIPS%3A24003" in url:
            return {
                "results": [
                    {
                        "id": "GHCND:SHORT",
                        "name": "SHORT",
                        "latitude": 39.0,
                        "longitude": -76.0,
                        "mindate": "2010-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 1.0,
                    }
                ]
            }
        return {
            "results": [
                {
                    "id": "GHCND:FALLBACK",
                    "name": "FALLBACK",
                    "latitude": 39.17,
                    "longitude": -76.68,
                    "mindate": "1939-01-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 0.99,
                }
            ]
        }

    result = audit_noaa_station_coverage(
        start_date=date(1992, 1, 1),
        end_date=date(2026, 5, 24),
        output_dir=tmp_path,
        token="token-value",
        county_fips_values=["24003", "24005"],
        nearest_station_fallback=True,
        json_get=fake_json_get,
    )

    df = pd.read_csv(result.output_path, dtype={"county_fips": str})
    anne_arundel = df[df["county_fips"] == "24003"].iloc[0]
    assert result.ok_count == 2
    assert result.needs_fallback_count == 0
    assert anne_arundel["status"] == "ok"
    assert anne_arundel["selection_method"] == "nearest_maryland"
    assert anne_arundel["selected_station_ids"] == "GHCND:FALLBACK"


def _station(station_id: str, *, latitude: float, longitude: float):
    from tickbiterisk.etl.noaa import NoaaStation

    return NoaaStation(
        county_fips="24005",
        station_id=station_id,
        name=station_id,
        latitude=latitude,
        longitude=longitude,
        mindate=date(1939, 1, 1),
        maxdate=date(2026, 5, 20),
        data_coverage=0.99,
    )
