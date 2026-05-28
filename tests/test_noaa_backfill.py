from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tickbiterisk.etl.noaa_backfill import (
    NoaaBackfillCountyFipsError,
    NoaaBackfillDateRangeError,
    NoaaBackfillNoStationError,
    audit_noaa_station_coverage,
    run_noaa_county_backfill,
    run_noaa_maryland_backfill,
)


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
