from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from collections.abc import Sequence
from typing import Any, Callable

from tickbiterisk.etl.noaa import (
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    select_long_coverage_stations,
)
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations
from tickbiterisk.etl.weather_build import (
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
)


class NoaaBackfillError(RuntimeError):
    """Base error for NOAA backfill orchestration failures."""


class NoaaBackfillDateRangeError(NoaaBackfillError):
    """Raised when a NOAA backfill date range is invalid."""


class NoaaBackfillCountyFipsError(NoaaBackfillError):
    """Raised when a Maryland backfill receives a non-Maryland FIPS code."""


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


@dataclass(frozen=True)
class NoaaCountyBackfillFailure:
    county_fips: str
    error: str


@dataclass(frozen=True)
class NoaaMarylandBackfillResult:
    county_results: list[NoaaCountyBackfillResult]
    failures: list[NoaaCountyBackfillFailure]

    @property
    def county_count(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_count(self) -> int:
        return len(self.county_results)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    @property
    def daily_observation_count(self) -> int:
        return sum(row.daily_observation_count for row in self.county_results)


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


def run_noaa_maryland_backfill(
    *,
    start_date: date,
    end_date: date,
    output_dir: Path,
    token: str,
    county_fips_values: Sequence[str] | None = None,
    station_limit: int = 1,
    min_data_coverage: float = 0.5,
    max_end_lag_days: int = 14,
    continue_on_error: bool = True,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> NoaaMarylandBackfillResult:
    county_fips_list = _maryland_county_fips_list(county_fips_values)
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
    )

    county_results: list[NoaaCountyBackfillResult] = []
    failures: list[NoaaCountyBackfillFailure] = []
    for county_fips in county_fips_list:
        try:
            county_results.append(
                run_noaa_county_backfill(
                    county_fips=county_fips,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    token=token,
                    station_limit=station_limit,
                    min_data_coverage=min_data_coverage,
                    max_end_lag_days=max_end_lag_days,
                    json_get=json_get,
                )
            )
        except NoaaBackfillError as exc:
            if not continue_on_error:
                raise
            failures.append(
                NoaaCountyBackfillFailure(
                    county_fips=county_fips,
                    error=str(exc),
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            failures.append(
                NoaaCountyBackfillFailure(
                    county_fips=county_fips,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    return NoaaMarylandBackfillResult(
        county_results=county_results,
        failures=failures,
    )


def resolve_maryland_noaa_county_fips(
    county_fips_values: Sequence[str] | None,
) -> list[str]:
    return _maryland_county_fips_list(county_fips_values)


def validate_noaa_backfill_args(
    *,
    start_date: date,
    end_date: date,
    station_limit: int,
) -> None:
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
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


def _maryland_county_fips_list(
    county_fips_values: Sequence[str] | None,
) -> list[str]:
    known_fips = {row.county_fips for row in load_maryland_weather_locations()}
    if not county_fips_values:
        return sorted(known_fips)

    normalized = [str(value).zfill(5) for value in county_fips_values]
    unknown = sorted(set(normalized) - known_fips)
    if unknown:
        raise NoaaBackfillCountyFipsError(
            f"Unknown Maryland county FIPS: {', '.join(unknown)}"
        )
    return normalized
