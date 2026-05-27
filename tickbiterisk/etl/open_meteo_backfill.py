from __future__ import annotations

import csv
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from tickbiterisk.etl.open_meteo import (
    WeatherDailyObservation,
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
)
from tickbiterisk.etl.weather_build import (
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_features_weekly_output,
)
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    add_trailing_weekly_anomalies,
    compute_monthly_weather_features,
    compute_weekly_weather_features,
)
from tickbiterisk.etl.weather_locations import (
    WeatherLocation,
    load_maryland_weather_locations,
)


class OpenMeteoBackfillError(RuntimeError):
    """Base error for Open-Meteo backfill orchestration failures."""


class OpenMeteoBackfillDateRangeError(OpenMeteoBackfillError):
    """Raised when an Open-Meteo backfill date range is invalid."""


class OpenMeteoBackfillCountyFipsError(OpenMeteoBackfillError):
    """Raised when a Maryland backfill receives a non-Maryland FIPS code."""


@dataclass(frozen=True)
class OpenMeteoArchiveRequestPlan:
    county_fips: str
    county_name: str
    chunk_start_date: date
    chunk_end_date: date
    url: str


@dataclass(frozen=True)
class OpenMeteoCountyBackfillResult:
    county_fips: str
    chunk_count: int
    daily_observation_count: int
    daily_output_path: Path
    weekly_output_path: Path
    monthly_output_path: Path


@dataclass(frozen=True)
class OpenMeteoCountyBackfillFailure:
    county_fips: str
    error: str


@dataclass(frozen=True)
class OpenMeteoMarylandBackfillResult:
    county_results: list[OpenMeteoCountyBackfillResult]
    failures: list[OpenMeteoCountyBackfillFailure]

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
    def chunk_count(self) -> int:
        return sum(row.chunk_count for row in self.county_results)

    @property
    def daily_observation_count(self) -> int:
        return sum(row.daily_observation_count for row in self.county_results)


def iter_date_chunks(
    start_date: date,
    end_date: date,
    *,
    max_chunk_days: int = 366,
) -> Iterator[tuple[date, date]]:
    validate_open_meteo_backfill_args(
        start_date=start_date,
        end_date=end_date,
        max_chunk_days=max_chunk_days,
    )
    current = start_date
    while current <= end_date:
        chunk_end = min(end_date, current + timedelta(days=max_chunk_days - 1))
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def resolve_maryland_open_meteo_county_fips(
    county_fips_values: Sequence[str] | None,
) -> list[str]:
    known_fips = {row.county_fips for row in load_maryland_weather_locations()}
    if not county_fips_values:
        return sorted(known_fips)

    normalized = [str(value).zfill(5) for value in county_fips_values]
    unknown = sorted(set(normalized) - known_fips)
    if unknown:
        raise OpenMeteoBackfillCountyFipsError(
            f"Unknown Maryland county FIPS: {', '.join(unknown)}"
        )
    return normalized


def validate_open_meteo_backfill_args(
    *,
    start_date: date,
    end_date: date,
    max_chunk_days: int = 366,
) -> None:
    if end_date < start_date:
        raise OpenMeteoBackfillDateRangeError("end_date must be on or after start_date")
    if max_chunk_days < 1:
        raise OpenMeteoBackfillDateRangeError("max_chunk_days must be at least 1")


def plan_open_meteo_archive_requests(
    *,
    start_date: date,
    end_date: date,
    county_fips_values: Sequence[str] | None = None,
    max_chunk_days: int = 366,
    weather_model: str = "open_meteo_archive",
) -> list[OpenMeteoArchiveRequestPlan]:
    county_fips_list = resolve_maryland_open_meteo_county_fips(county_fips_values)
    validate_open_meteo_backfill_args(
        start_date=start_date,
        end_date=end_date,
        max_chunk_days=max_chunk_days,
    )
    locations = _maryland_weather_location_by_fips()
    plans: list[OpenMeteoArchiveRequestPlan] = []
    for county_fips in county_fips_list:
        location = locations[county_fips]
        for chunk_start, chunk_end in iter_date_chunks(
            start_date,
            end_date,
            max_chunk_days=max_chunk_days,
        ):
            plans.append(
                OpenMeteoArchiveRequestPlan(
                    county_fips=county_fips,
                    county_name=location.county_name,
                    chunk_start_date=chunk_start,
                    chunk_end_date=chunk_end,
                    url=build_open_meteo_archive_url(
                        location,
                        chunk_start,
                        chunk_end,
                        weather_model=weather_model,
                    ),
                )
            )
    return plans


def run_open_meteo_county_backfill(
    *,
    county_fips: str,
    start_date: date,
    end_date: date,
    output_dir: Path,
    max_chunk_days: int = 366,
    weather_model: str = "open_meteo_archive",
    json_get: Callable[[str], dict[str, Any]] | None = None,
    max_attempts: int = 3,
    sleep_seconds: float = 1.0,
    inter_chunk_sleep_seconds: float = 0.0,
) -> OpenMeteoCountyBackfillResult:
    normalized_county_fips = county_fips.zfill(5)
    county_fips_list = resolve_maryland_open_meteo_county_fips(
        [normalized_county_fips]
    )
    validate_open_meteo_backfill_args(
        start_date=start_date,
        end_date=end_date,
        max_chunk_days=max_chunk_days,
    )
    location = _maryland_weather_location_by_fips()[county_fips_list[0]]

    rows = []
    chunks = list(
        iter_date_chunks(start_date, end_date, max_chunk_days=max_chunk_days)
    )
    for index, (chunk_start, chunk_end) in enumerate(chunks):
        fetch_kwargs: dict[str, Any] = {
            "weather_model": weather_model,
            "max_attempts": max_attempts,
            "sleep_seconds": sleep_seconds,
        }
        if json_get is not None:
            fetch_kwargs["json_get"] = json_get
        rows.extend(
            fetch_open_meteo_archive(
                location,
                chunk_start,
                chunk_end,
                **fetch_kwargs,
            )
        )
        if inter_chunk_sleep_seconds > 0 and index < len(chunks) - 1:
            time.sleep(inter_chunk_sleep_seconds)

    daily_output_path = write_weather_daily_output(rows, output_dir, append=True)
    feature_rows = _read_weather_daily_rows_for_county(
        daily_output_path,
        county_fips=normalized_county_fips,
        weather_model=weather_model,
    )
    weekly_output_path = write_weather_features_weekly_output(
        add_trailing_weekly_anomalies(compute_weekly_weather_features(feature_rows)),
        output_dir,
        append=True,
    )
    monthly_output_path = write_weather_features_monthly_output(
        add_trailing_monthly_anomalies(compute_monthly_weather_features(feature_rows)),
        output_dir,
        append=True,
    )

    return OpenMeteoCountyBackfillResult(
        county_fips=normalized_county_fips,
        chunk_count=len(chunks),
        daily_observation_count=len(rows),
        daily_output_path=daily_output_path,
        weekly_output_path=weekly_output_path,
        monthly_output_path=monthly_output_path,
    )


def run_open_meteo_maryland_backfill(
    *,
    start_date: date,
    end_date: date,
    output_dir: Path,
    county_fips_values: Sequence[str] | None = None,
    max_chunk_days: int = 366,
    weather_model: str = "open_meteo_archive",
    continue_on_error: bool = True,
    json_get: Callable[[str], dict[str, Any]] | None = None,
    max_attempts: int = 3,
    sleep_seconds: float = 1.0,
    inter_chunk_sleep_seconds: float = 0.0,
    inter_county_sleep_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> OpenMeteoMarylandBackfillResult:
    county_fips_list = resolve_maryland_open_meteo_county_fips(county_fips_values)
    validate_open_meteo_backfill_args(
        start_date=start_date,
        end_date=end_date,
        max_chunk_days=max_chunk_days,
    )

    county_results: list[OpenMeteoCountyBackfillResult] = []
    failures: list[OpenMeteoCountyBackfillFailure] = []
    for county_index, county_fips in enumerate(county_fips_list):
        try:
            county_results.append(
                run_open_meteo_county_backfill(
                    county_fips=county_fips,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    max_chunk_days=max_chunk_days,
                    weather_model=weather_model,
                    json_get=json_get,
                    max_attempts=max_attempts,
                    sleep_seconds=sleep_seconds,
                    inter_chunk_sleep_seconds=inter_chunk_sleep_seconds,
                )
            )
        except OpenMeteoBackfillError as exc:
            if not continue_on_error:
                raise
            failures.append(
                OpenMeteoCountyBackfillFailure(
                    county_fips=county_fips,
                    error=str(exc),
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            failures.append(
                OpenMeteoCountyBackfillFailure(
                    county_fips=county_fips,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
        if (
            inter_county_sleep_seconds > 0
            and county_index < len(county_fips_list) - 1
        ):
            sleep(inter_county_sleep_seconds)

    return OpenMeteoMarylandBackfillResult(
        county_results=county_results,
        failures=failures,
    )


def _maryland_weather_location_by_fips() -> dict[str, WeatherLocation]:
    return {location.county_fips: location for location in load_maryland_weather_locations()}


def _read_weather_daily_rows_for_county(
    input_path: Path,
    *,
    county_fips: str,
    weather_model: str,
) -> list[WeatherDailyObservation]:
    return [
        row
        for row in read_open_meteo_weather_daily_rows(input_path)
        if row.county_fips == county_fips and row.weather_model == weather_model
    ]


def read_open_meteo_weather_daily_rows(
    input_path: Path,
) -> list[WeatherDailyObservation]:
    rows = []
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            if record["source"] != "open_meteo_archive":
                continue
            rows.append(_weather_daily_observation_from_record(record))
    return rows


def _weather_daily_observation_from_record(
    record: dict[str, str],
) -> WeatherDailyObservation:
    return WeatherDailyObservation(
        county_fips=str(record["county_fips"]).zfill(5),
        date=date.fromisoformat(record["date"]),
        source=record["source"],
        weather_model=record["weather_model"],
        temp_mean_f=float(record["temp_mean_f"]),
        temp_max_f=float(record["temp_max_f"]),
        temp_min_f=float(record["temp_min_f"]),
        humidity_mean_pct=float(record["humidity_mean_pct"]),
        humidity_max_pct=float(record["humidity_max_pct"]),
        humidity_min_pct=float(record["humidity_min_pct"]),
        dew_point_mean_f=float(record["dew_point_mean_f"]),
        precipitation_mm=float(record["precipitation_mm"]),
        rain_mm=float(record["rain_mm"]),
        snowfall_mm=float(record["snowfall_mm"]),
        precipitation_hours=float(record["precipitation_hours"]),
        soil_temp_0_7cm_f=float(record["soil_temp_0_7cm_f"]),
        soil_moisture_0_7cm=_nullable_float(record["soil_moisture_0_7cm"]),
        evapotranspiration_mm=float(record["evapotranspiration_mm"]),
        wind_mean_mph=float(record["wind_mean_mph"]),
        wind_max_mph=float(record["wind_max_mph"]),
        source_url_hash=record["source_url_hash"],
    )


def _nullable_float(value: str) -> float | None:
    if value == "":
        return None
    return float(value)
