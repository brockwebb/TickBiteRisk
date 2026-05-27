from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from tickbiterisk.etl.open_meteo_backfill import (
    OpenMeteoBackfillDateRangeError,
    OpenMeteoBackfillCountyFipsError,
    iter_date_chunks,
    resolve_maryland_open_meteo_county_fips,
    run_open_meteo_county_backfill,
    run_open_meteo_maryland_backfill,
)


def _open_meteo_payload_from_url(url: str) -> dict:
    query = parse_qs(urlparse(url).query)
    start = date.fromisoformat(query["start_date"][0])
    end = date.fromisoformat(query["end_date"][0])
    days = (end - start).days + 1
    times = [date.fromordinal(start.toordinal() + offset).isoformat() for offset in range(days)]
    return {
        "daily": {
            "time": times,
            "temperature_2m_mean": [55.0] * days,
            "temperature_2m_max": [62.0] * days,
            "temperature_2m_min": [45.0] * days,
            "relative_humidity_2m_mean": [82.0] * days,
            "relative_humidity_2m_max": [95.0] * days,
            "relative_humidity_2m_min": [65.0] * days,
            "dew_point_2m_mean": [48.0] * days,
            "precipitation_sum": [0.0] * days,
            "rain_sum": [0.0] * days,
            "snowfall_sum": [0.0] * days,
            "precipitation_hours": [0.0] * days,
            "soil_temperature_0_to_7cm_mean": [48.0] * days,
            "soil_moisture_0_to_7cm_mean": [0.30] * days,
            "et0_fao_evapotranspiration": [1.0] * days,
            "wind_speed_10m_mean": [5.0] * days,
            "wind_speed_10m_max": [10.0] * days,
        }
    }


def _open_meteo_payload_with_year_values(url: str) -> dict:
    query = parse_qs(urlparse(url).query)
    start = date.fromisoformat(query["start_date"][0])
    payload = _open_meteo_payload_from_url(url)
    value = 50.0 if start.year == 2020 else 60.0
    payload["daily"]["temperature_2m_mean"] = [value]
    payload["daily"]["temperature_2m_max"] = [value + 5.0]
    payload["daily"]["temperature_2m_min"] = [value - 5.0]
    return payload


def test_iter_date_chunks_splits_inclusive_ranges() -> None:
    chunks = list(
        iter_date_chunks(
            date(2020, 1, 1),
            date(2020, 1, 5),
            max_chunk_days=2,
        )
    )

    assert chunks == [
        (date(2020, 1, 1), date(2020, 1, 2)),
        (date(2020, 1, 3), date(2020, 1, 4)),
        (date(2020, 1, 5), date(2020, 1, 5)),
    ]


def test_iter_date_chunks_rejects_invalid_ranges() -> None:
    with pytest.raises(OpenMeteoBackfillDateRangeError, match="end_date"):
        list(iter_date_chunks(date(2020, 1, 2), date(2020, 1, 1)))

    with pytest.raises(OpenMeteoBackfillDateRangeError, match="max_chunk_days"):
        list(iter_date_chunks(date(2020, 1, 1), date(2020, 1, 2), max_chunk_days=0))


def test_resolve_maryland_open_meteo_county_fips_validates_subset() -> None:
    assert resolve_maryland_open_meteo_county_fips(["24003", "24005"]) == [
        "24003",
        "24005",
    ]

    with pytest.raises(OpenMeteoBackfillCountyFipsError, match="99999"):
        resolve_maryland_open_meteo_county_fips(["99999"])


def test_run_open_meteo_county_backfill_fetches_chunks_and_writes_features(
    tmp_path,
) -> None:
    calls: list[str] = []

    def fake_json_get(url: str) -> dict:
        calls.append(url)
        return _open_meteo_payload_from_url(url)

    result = run_open_meteo_county_backfill(
        county_fips="24003",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 3),
        output_dir=tmp_path,
        max_chunk_days=2,
        json_get=fake_json_get,
    )

    assert result.county_fips == "24003"
    assert result.chunk_count == 2
    assert result.daily_observation_count == 3
    assert len(calls) == 2
    assert result.daily_output_path == tmp_path / "weather_daily.csv"
    assert result.weekly_output_path == tmp_path / "weather_features_weekly.csv"
    assert result.monthly_output_path == tmp_path / "weather_features_monthly.csv"

    daily = pd.read_csv(tmp_path / "weather_daily.csv", dtype={"county_fips": str})
    assert len(daily) == 3
    assert set(daily["county_fips"]) == {"24003"}
    assert daily.loc[0, "source"] == "open_meteo_archive"

    weekly = pd.read_csv(
        tmp_path / "weather_features_weekly.csv", dtype={"county_fips": str}
    )
    assert weekly.loc[0, "humidity_mean_pct"] == 82.0
    assert weekly.loc[0, "soil_moisture_mean"] == 0.3


def test_run_open_meteo_county_backfill_recomputes_features_from_existing_daily_rows(
    tmp_path,
) -> None:
    run_open_meteo_county_backfill(
        county_fips="24003",
        start_date=date(2021, 1, 1),
        end_date=date(2021, 1, 1),
        output_dir=tmp_path,
        json_get=_open_meteo_payload_with_year_values,
    )

    run_open_meteo_county_backfill(
        county_fips="24003",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 1),
        output_dir=tmp_path,
        json_get=_open_meteo_payload_with_year_values,
    )

    monthly = pd.read_csv(
        tmp_path / "weather_features_monthly.csv", dtype={"county_fips": str}
    )
    jan_2021 = monthly[(monthly["county_fips"] == "24003") & (monthly["year"] == 2021)]

    assert jan_2021.iloc[0]["temp_anomaly_vs_10yr"] == 10.0


def test_run_open_meteo_maryland_backfill_records_failures_when_allowed(
    tmp_path,
) -> None:
    def fake_json_get(url: str) -> dict:
        if "latitude=39.443167" in url:
            raise RuntimeError("archive unavailable")
        return _open_meteo_payload_from_url(url)

    result = run_open_meteo_maryland_backfill(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 1),
        output_dir=tmp_path,
        county_fips_values=["24003", "24005"],
        max_chunk_days=1,
        continue_on_error=True,
        json_get=fake_json_get,
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.daily_observation_count == 1
    assert result.failures[0].county_fips == "24005"
    assert "archive unavailable" in result.failures[0].error


def test_run_open_meteo_maryland_backfill_can_throttle_between_counties(
    tmp_path,
) -> None:
    sleep_calls: list[float] = []

    result = run_open_meteo_maryland_backfill(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 1),
        output_dir=tmp_path,
        county_fips_values=["24003", "24005"],
        max_chunk_days=1,
        inter_county_sleep_seconds=0.5,
        json_get=_open_meteo_payload_from_url,
        sleep=sleep_calls.append,
    )

    assert result.success_count == 2
    assert sleep_calls == [0.5]
