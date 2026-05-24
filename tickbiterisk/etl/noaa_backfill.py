from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from tickbiterisk.etl.noaa import (
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    select_long_coverage_stations,
)
from tickbiterisk.etl.weather_build import (
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
)


class NoaaBackfillError(RuntimeError):
    """Base error for NOAA backfill orchestration failures."""


class NoaaBackfillDateRangeError(NoaaBackfillError):
    """Raised when a NOAA backfill date range is invalid."""


class NoaaBackfillNoStationError(NoaaBackfillError):
    """Raised when no NOAA station can cover the requested county/date range."""


@dataclass(frozen=True)
class NoaaCountyBackfillResult:
    county_fips: str
    selected_station_ids: list[str]
    station_count: int
    daily_observation_count: int
    stations_output_path: Path
    daily_output_path: Path


def run_noaa_county_backfill(
    *,
    county_fips: str,
    start_date: date,
    end_date: date,
    output_dir: Path,
    token: str,
    station_limit: int = 1,
    min_data_coverage: float = 0.5,
    max_end_lag_days: int = 14,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> NoaaCountyBackfillResult:
    normalized_county_fips = county_fips.zfill(5)
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
    )

    stations = fetch_noaa_stations(
        normalized_county_fips,
        start_date,
        end_date,
        token=token,
        json_get=json_get,
    )
    selected = select_long_coverage_stations(
        stations,
        start_date=start_date,
        end_date=end_date,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
    )[:station_limit]
    if not selected:
        raise NoaaBackfillNoStationError(
            "No NOAA GHCND station covers "
            f"county_fips={normalized_county_fips}, "
            f"start_date={start_date.isoformat()}, "
            f"end_date={end_date.isoformat()} "
            f"with min_data_coverage={min_data_coverage}"
        )

    daily_rows = []
    for station in selected:
        daily_rows.extend(
            fetch_noaa_daily_observations(
                normalized_county_fips,
                station.station_id,
                start_date,
                end_date,
                token=token,
                json_get=json_get,
            )
        )

    stations_output_path = write_noaa_stations_output(
        selected,
        output_dir,
        append=True,
    )
    daily_output_path = write_noaa_daily_observations_output(
        daily_rows,
        output_dir,
        append=True,
    )

    return NoaaCountyBackfillResult(
        county_fips=normalized_county_fips,
        selected_station_ids=[station.station_id for station in selected],
        station_count=len(selected),
        daily_observation_count=len(daily_rows),
        stations_output_path=stations_output_path,
        daily_output_path=daily_output_path,
    )


def _validate_backfill_args(
    *,
    start_date: date,
    end_date: date,
    station_limit: int,
) -> None:
    if end_date < start_date:
        raise NoaaBackfillDateRangeError("end_date must be on or after start_date")
    if station_limit < 1:
        raise NoaaBackfillDateRangeError("station_limit must be at least 1")
