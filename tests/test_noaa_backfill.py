from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tickbiterisk.etl.noaa_backfill import (
    NoaaBackfillDateRangeError,
    NoaaBackfillNoStationError,
    run_noaa_county_backfill,
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
    assert any("stationid=GHCND%3AFIRST" in call for call in calls)
    assert any("stationid=GHCND%3ASECOND" in call for call in calls)
