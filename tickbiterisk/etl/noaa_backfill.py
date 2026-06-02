from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from tickbiterisk.etl.noaa import (
    NoaaDailyObservation,
    NoaaStation,
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    select_long_coverage_stations,
)
from tickbiterisk.etl.weather_build import (
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
)
from tickbiterisk.etl.weather_locations import (
    WeatherLocation,
    load_maryland_weather_locations,
    load_weather_locations,
)

# A daily-observation fetcher: (county_fips, station_id, start_date, end_date)
# -> observations. Defaults to the CDO /data path; the GHCND .dly bulk path is
# injected for the regional time-series acquisition.
DailyFetcher = Callable[[str, str, date, date], list[NoaaDailyObservation]]

# Length (years) of the temperature-density validation window ending at the
# configured validation date (e.g. 2021 -> 2017-2021).
_VALIDATION_WINDOW_YEARS = 5


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
    daily_observation_count_by_station: dict[str, int] = field(default_factory=dict)
    selection_method: str = "internal"


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

    # NOTE: structurally a generic multi-county backfill result; see the
    # NoaaMultiCountyBackfillResult alias below used by the regional path.

    @property
    def success_count(self) -> int:
        return len(self.county_results)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    @property
    def daily_observation_count(self) -> int:
        return sum(row.daily_observation_count for row in self.county_results)


@dataclass(frozen=True)
class NoaaStationCoverageAuditRow:
    county_fips: str
    county_name: str
    status: str
    selection_method: str
    fallback_distance_miles: float | None
    candidate_station_count: int
    selected_station_count: int
    selected_station_ids: str
    best_station_id: str
    best_station_name: str
    best_station_mindate: str
    best_station_maxdate: str
    best_station_data_coverage: float | None
    error: str


@dataclass(frozen=True)
class NoaaStationCoverageAuditResult:
    output_path: Path
    county_count: int
    ok_count: int
    needs_fallback_count: int
    error_count: int


NOAA_STATION_COVERAGE_AUDIT_COLUMNS = [
    "county_fips",
    "county_name",
    "status",
    "selection_method",
    "fallback_distance_miles",
    "candidate_station_count",
    "selected_station_count",
    "selected_station_ids",
    "best_station_id",
    "best_station_name",
    "best_station_mindate",
    "best_station_maxdate",
    "best_station_data_coverage",
    "error",
]


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
    fallback_stations: Sequence[NoaaStation] | None = None,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
    daily_fetcher: DailyFetcher | None = None,
    validate_temp_window_end: date | None = None,
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
    # Station eligibility is decided by the validation window (where we need
    # temperature), NOT the acquisition end_date — the .dly pull may extend years
    # past it for covariates, and station metadata maxdate lags by months.
    eligibility_end = (
        validate_temp_window_end if validate_temp_window_end is not None else end_date
    )
    internal = select_long_coverage_stations(
        stations,
        start_date=start_date,
        end_date=eligibility_end,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
    )

    # Validated .dly path: try candidates in rank order and accept the first whose
    # ACTUAL in-window TMAX/TMIN reaches the window — rejecting stations whose
    # temperature record died early (CDO all-element maxdate overstates temp).
    if validate_temp_window_end is not None and daily_fetcher is not None:
        candidate_ids = {station.station_id for station in internal}
        candidates = list(internal)
        if fallback_stations:
            nearest = _nearest_eligible_fallback_stations(
                county_fips=normalized_county_fips,
                stations=fallback_stations,
                start_date=start_date,
                end_date=eligibility_end,
                station_limit=len(fallback_stations),
                min_data_coverage=min_data_coverage,
                max_end_lag_days=max_end_lag_days,
            )
            candidates += [s for s in nearest if s.station_id not in candidate_ids]
        # Validate temperature density over a fit window ending at the validation
        # date (5-year window), so a station must actually report temp IN the
        # window, not merely reach it.
        validate_window_start = date(
            validate_temp_window_end.year - (_VALIDATION_WINDOW_YEARS - 1), 1, 1
        )
        station, validated_rows = select_validated_dly_station(
            candidates,
            county_fips=normalized_county_fips,
            daily_fetcher=daily_fetcher,
            acquire_start=start_date,
            acquire_end=end_date,
            validate_window_start=validate_window_start,
            validate_window_end=validate_temp_window_end,
        )
        if station is None:
            raise NoaaBackfillNoStationError(
                "No NOAA GHCND station with TMAX/TMIN through "
                f"{validate_temp_window_end.isoformat()} covers "
                f"county_fips={normalized_county_fips} (checked "
                f"{len(candidates)} candidate station(s))"
            )
        selected = [station]
        selection_method = (
            "internal" if station.station_id in candidate_ids else "nearest_validated"
        )
        daily_rows = list(validated_rows)
        daily_observation_count_by_station = {station.station_id: len(validated_rows)}
        stations_output_path = write_noaa_stations_output(
            selected, output_dir, append=True
        )
        daily_output_path = write_noaa_daily_observations_output(
            daily_rows, output_dir, append=True
        )
        return NoaaCountyBackfillResult(
            county_fips=normalized_county_fips,
            selected_station_ids=[station.station_id],
            station_count=1,
            daily_observation_count=len(daily_rows),
            stations_output_path=stations_output_path,
            daily_output_path=daily_output_path,
            daily_observation_count_by_station=daily_observation_count_by_station,
            selection_method=selection_method,
        )

    selected = internal[:station_limit]
    selection_method = "internal"
    if not selected and fallback_stations:
        selected = _nearest_eligible_fallback_stations(
            county_fips=normalized_county_fips,
            stations=fallback_stations,
            start_date=start_date,
            end_date=end_date,
            station_limit=station_limit,
            min_data_coverage=min_data_coverage,
            max_end_lag_days=max_end_lag_days,
        )
        if selected:
            selection_method = "nearest_maryland"
    if not selected:
        raise NoaaBackfillNoStationError(
            "No NOAA GHCND station covers "
            f"county_fips={normalized_county_fips}, "
            f"start_date={start_date.isoformat()}, "
            f"end_date={end_date.isoformat()} "
            f"with min_data_coverage={min_data_coverage}"
        )

    daily_rows = []
    daily_observation_count_by_station = {}
    for station in selected:
        if daily_fetcher is not None:
            station_daily_rows = daily_fetcher(
                normalized_county_fips,
                station.station_id,
                start_date,
                end_date,
            )
        else:
            station_daily_rows = fetch_noaa_daily_observations(
                normalized_county_fips,
                station.station_id,
                start_date,
                end_date,
                token=token,
                json_get=json_get,
            )
        daily_observation_count_by_station[station.station_id] = len(
            station_daily_rows
        )
        daily_rows.extend(station_daily_rows)

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
        daily_observation_count_by_station=daily_observation_count_by_station,
        selection_method=selection_method,
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
    nearest_station_fallback: bool = False,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> NoaaMarylandBackfillResult:
    county_fips_list = _maryland_county_fips_list(county_fips_values)
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
    )

    fallback_stations = (
        _fetch_noaa_station_pool(
            county_fips_list=county_fips_list,
            start_date=start_date,
            end_date=end_date,
            token=token,
            json_get=json_get,
        )
        if nearest_station_fallback
        else None
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
                    fallback_stations=fallback_stations,
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


# The regional multi-county result shares the structure of the Maryland one.
NoaaMultiCountyBackfillResult = NoaaMarylandBackfillResult


def run_noaa_regional_backfill(
    *,
    county_fips_values: Sequence[str],
    start_date: date,
    end_date: date,
    output_dir: Path,
    token: str,
    station_limit: int = 1,
    min_data_coverage: float = 0.5,
    max_end_lag_days: int = 14,
    continue_on_error: bool = True,
    nearest_station_fallback: bool = False,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
    daily_fetcher: DailyFetcher | None = None,
    validate_temp_window_end: date | None = None,
    station_pool_county_fips: Sequence[str] | None = None,
) -> NoaaMultiCountyBackfillResult:
    """State-agnostic multi-county NOAA backfill for the six-state product.

    Generalizes the Maryland backfill: the caller supplies the county FIPS set
    (resolved from config via the weather locations loader) and, for the bulk
    time-series path, a ``daily_fetcher`` (GHCND .dly). Station discovery stays
    FIPS-based. A county with no qualifying station is recorded as a failure
    (fail-loud per county) rather than silently dropped.

    ``validate_temp_window_end`` enables validated selection (reject stations
    whose actual TMAX/TMIN died before the window). ``station_pool_county_fips``
    sources the nearest-station fallback pool from the FULL six-state universe
    (not just the processed subset), so a re-pull of a few counties still draws
    on every region station — this is what stops a temp-dead far station from
    being assigned to dozens of counties.
    """
    if not county_fips_values:
        raise NoaaBackfillCountyFipsError(
            "run_noaa_regional_backfill requires at least one county FIPS"
        )
    county_fips_list = [str(value).zfill(5) for value in county_fips_values]
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
    )

    pool_fips = (
        [str(v).zfill(5) for v in station_pool_county_fips]
        if station_pool_county_fips is not None
        else county_fips_list
    )
    fallback_stations = (
        _fetch_noaa_station_pool(
            county_fips_list=pool_fips,
            start_date=start_date,
            end_date=end_date,
            token=token,
            json_get=json_get,
        )
        if nearest_station_fallback
        else None
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
                    fallback_stations=fallback_stations,
                    json_get=json_get,
                    daily_fetcher=daily_fetcher,
                    validate_temp_window_end=validate_temp_window_end,
                )
            )
        except NoaaBackfillError as exc:
            if not continue_on_error:
                raise
            failures.append(
                NoaaCountyBackfillFailure(county_fips=county_fips, error=str(exc))
            )
        except Exception as exc:  # noqa: BLE001 - recorded per-county, not swallowed
            if not continue_on_error:
                raise
            failures.append(
                NoaaCountyBackfillFailure(
                    county_fips=county_fips,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    return NoaaMultiCountyBackfillResult(
        county_results=county_results,
        failures=failures,
    )


def audit_noaa_station_coverage(
    *,
    start_date: date,
    end_date: date,
    output_dir: Path,
    token: str,
    county_fips_values: Sequence[str] | None = None,
    station_limit: int = 1,
    min_data_coverage: float = 0.5,
    max_end_lag_days: int = 14,
    nearest_station_fallback: bool = False,
    json_get: Callable[[str, str], dict[str, Any]] | None = None,
) -> NoaaStationCoverageAuditResult:
    county_fips_list = _maryland_county_fips_list(county_fips_values)
    _validate_backfill_args(
        start_date=start_date,
        end_date=end_date,
        station_limit=station_limit,
    )
    county_names = _maryland_county_name_by_fips()

    stations_by_county: dict[str, list[NoaaStation]] = {}
    fetch_errors: dict[str, Exception] = {}
    for county_fips in county_fips_list:
        try:
            stations_by_county[county_fips] = fetch_noaa_stations(
                county_fips,
                start_date,
                end_date,
                token=token,
                json_get=json_get,
            )
        except Exception as exc:
            fetch_errors[county_fips] = exc

    fallback_stations = (
        _dedupe_stations_by_id(
            [
                station
                for station_list in stations_by_county.values()
                for station in station_list
            ]
        )
        if nearest_station_fallback
        else []
    )

    rows: list[NoaaStationCoverageAuditRow] = []
    for county_fips in county_fips_list:
        try:
            if county_fips in fetch_errors:
                raise fetch_errors[county_fips]

            stations = stations_by_county[county_fips]
            selected = select_long_coverage_stations(
                stations,
                start_date=start_date,
                end_date=end_date,
                min_data_coverage=min_data_coverage,
                max_end_lag_days=max_end_lag_days,
            )[:station_limit]
            selection_method = "internal"
            fallback_distance_miles = None
            if not selected and nearest_station_fallback:
                selected = _nearest_eligible_fallback_stations(
                    county_fips=county_fips,
                    stations=fallback_stations,
                    start_date=start_date,
                    end_date=end_date,
                    station_limit=station_limit,
                    min_data_coverage=min_data_coverage,
                    max_end_lag_days=max_end_lag_days,
                )
                if selected:
                    selection_method = "nearest_maryland"
                    fallback_distance_miles = _station_distance_to_county_miles(
                        county_fips,
                        selected[0],
                    )
            rows.append(
                _station_coverage_audit_row(
                    county_fips=county_fips,
                    county_name=county_names[county_fips],
                    stations=stations,
                    selected=selected,
                    selection_method=selection_method,
                    fallback_distance_miles=fallback_distance_miles,
                )
            )
        except Exception as exc:
            rows.append(
                NoaaStationCoverageAuditRow(
                    county_fips=county_fips,
                    county_name=county_names[county_fips],
                    status="error",
                    selection_method="",
                    fallback_distance_miles=None,
                    candidate_station_count=0,
                    selected_station_count=0,
                    selected_station_ids="",
                    best_station_id="",
                    best_station_name="",
                    best_station_mindate="",
                    best_station_maxdate="",
                    best_station_data_coverage=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    output_path = write_noaa_station_coverage_audit_output(rows, output_dir)
    return NoaaStationCoverageAuditResult(
        output_path=output_path,
        county_count=len(rows),
        ok_count=sum(1 for row in rows if row.status == "ok"),
        needs_fallback_count=sum(1 for row in rows if row.status == "needs_fallback"),
        error_count=sum(1 for row in rows if row.status == "error"),
    )


def write_noaa_station_coverage_audit_output(
    rows: list[NoaaStationCoverageAuditRow],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "noaa_station_coverage_audit.csv"
    df = pd.DataFrame(
        [asdict(row) for row in rows],
        columns=NOAA_STATION_COVERAGE_AUDIT_COLUMNS,
    )
    if not df.empty:
        df = df.sort_values(["county_fips"]).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    return output_path


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


def _maryland_county_name_by_fips() -> dict[str, str]:
    return {
        location.county_fips: location.county_name
        for location in load_maryland_weather_locations()
    }


def _maryland_weather_location_by_fips() -> dict[str, WeatherLocation]:
    return {location.county_fips: location for location in load_maryland_weather_locations()}


def _weather_location_by_fips() -> dict[str, WeatherLocation]:
    """County centroid lookup across all six regional jurisdictions.

    The nearest-station fallback needs centroids for any of DE/DC/MD/PA/VA/WV, not
    only Maryland; resolving from the Maryland-only resource raised KeyError for
    every out-of-MD county that fell through to the fallback.
    """
    return {location.county_fips: location for location in load_weather_locations()}


def _station_coverage_audit_row(
    *,
    county_fips: str,
    county_name: str,
    stations: list[NoaaStation],
    selected: list[NoaaStation],
    selection_method: str,
    fallback_distance_miles: float | None,
) -> NoaaStationCoverageAuditRow:
    best_station = selected[0] if selected else None
    if best_station is None:
        return NoaaStationCoverageAuditRow(
            county_fips=county_fips,
            county_name=county_name,
            status="needs_fallback",
            selection_method="",
            fallback_distance_miles=None,
            candidate_station_count=len(stations),
            selected_station_count=0,
            selected_station_ids="",
            best_station_id="",
            best_station_name="",
            best_station_mindate="",
            best_station_maxdate="",
            best_station_data_coverage=None,
            error="No selected station covers requested range",
        )

    return NoaaStationCoverageAuditRow(
        county_fips=county_fips,
        county_name=county_name,
        status="ok",
        selection_method=selection_method,
        fallback_distance_miles=fallback_distance_miles,
        candidate_station_count=len(stations),
        selected_station_count=len(selected),
        selected_station_ids=";".join(station.station_id for station in selected),
        best_station_id=best_station.station_id,
        best_station_name=best_station.name,
        best_station_mindate=best_station.mindate.isoformat(),
        best_station_maxdate=best_station.maxdate.isoformat(),
        best_station_data_coverage=best_station.data_coverage,
        error="",
    )


def _fetch_noaa_station_pool(
    *,
    county_fips_list: Sequence[str],
    start_date: date,
    end_date: date,
    token: str,
    json_get: Callable[[str, str], dict[str, Any]] | None,
) -> list[NoaaStation]:
    stations: list[NoaaStation] = []
    for county_fips in county_fips_list:
        try:
            stations.extend(
                fetch_noaa_stations(
                    county_fips,
                    start_date,
                    end_date,
                    token=token,
                    json_get=json_get,
                )
            )
        except Exception:
            continue
    return _dedupe_stations_by_id(stations)


def _nearest_eligible_fallback_stations(
    *,
    county_fips: str,
    stations: Sequence[NoaaStation],
    start_date: date,
    end_date: date,
    station_limit: int,
    min_data_coverage: float,
    max_end_lag_days: int,
) -> list[NoaaStation]:
    eligible = select_long_coverage_stations(
        list(_dedupe_stations_by_id(stations)),
        start_date=start_date,
        end_date=end_date,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
    )
    sorted_by_distance = sorted(
        eligible,
        key=lambda station: (
            _station_distance_to_county_miles(county_fips, station),
            -station.data_coverage,
            station.mindate,
            -_station_coverage_days(station),
            station.station_id,
        ),
    )
    return [
        replace(station, county_fips=county_fips)
        for station in sorted_by_distance[:station_limit]
    ]


def temp_maxdate(daily_rows: Sequence[NoaaDailyObservation]) -> date | None:
    """Latest date with an actual TMAX or TMIN observation.

    Distinct from a station's CDO all-element ``maxdate``: a station can still
    report precipitation long after its temperature record ended, so the CDO
    maxdate overstates temperature availability. Station selection must use this.
    """
    temp_dates = [
        row.date
        for row in daily_rows
        if row.tmax_f is not None or row.tmin_f is not None
    ]
    return max(temp_dates) if temp_dates else None


def inwindow_temp_days(
    daily_rows: Sequence[NoaaDailyObservation],
    window_start: date,
    window_end: date,
) -> int:
    """Distinct dates inside the window with an actual TMAX or TMIN observation."""
    return len(
        {
            row.date
            for row in daily_rows
            if window_start <= row.date <= window_end
            and (row.tmax_f is not None or row.tmin_f is not None)
        }
    )


# Max candidate stations to fetch+test per county before settling for the best.
_MAX_VALIDATION_CANDIDATES = 8


def select_validated_dly_station(
    candidates: Sequence[NoaaStation],
    *,
    county_fips: str,
    daily_fetcher: DailyFetcher,
    acquire_start: date,
    acquire_end: date,
    validate_window_start: date,
    validate_window_end: date,
    good_density: float = 0.90,
) -> tuple[NoaaStation | None, list[NoaaDailyObservation]]:
    """Pick the candidate with the best ACTUAL in-window temperature density.

    Fetches each candidate's full ``.dly`` over ``[acquire_start, acquire_end]``
    (so accepted stations keep their entire covariate series) and measures real
    TMAX/TMIN coverage WITHIN ``[validate_window_start, validate_window_end]`` —
    not merely the latest temp date, which a station that only began reporting
    temperature after the window would satisfy while contributing nothing in it.
    Early-accepts the first candidate at or above ``good_density``; otherwise
    keeps the best with any in-window temperature. Returns ``(None, [])`` only
    when no candidate has a single in-window temperature day (→ interpolation).
    """
    normalized_fips = county_fips.zfill(5)
    expected = (validate_window_end - validate_window_start).days + 1
    best: tuple[int, NoaaStation, list[NoaaDailyObservation]] | None = None
    for station in candidates[:_MAX_VALIDATION_CANDIDATES]:
        rows = daily_fetcher(
            normalized_fips, station.station_id, acquire_start, acquire_end
        )
        days = inwindow_temp_days(rows, validate_window_start, validate_window_end)
        if best is None or days > best[0]:
            best = (days, station, rows)
        if expected and days / expected >= good_density:
            return replace(station, county_fips=normalized_fips), rows
    if best is not None and best[0] > 0:
        return replace(best[1], county_fips=normalized_fips), best[2]
    return None, []


def _dedupe_stations_by_id(stations: Sequence[NoaaStation]) -> list[NoaaStation]:
    by_id: dict[str, NoaaStation] = {}
    for station in stations:
        current = by_id.get(station.station_id)
        if current is None or _station_quality_key(station) < _station_quality_key(
            current
        ):
            by_id[station.station_id] = station
    return list(by_id.values())


def _station_quality_key(station: NoaaStation) -> tuple[float, date, int, str]:
    return (
        -station.data_coverage,
        station.mindate,
        -_station_coverage_days(station),
        station.station_id,
    )


def _station_coverage_days(station: NoaaStation) -> int:
    return (station.maxdate - station.mindate).days


def _station_distance_to_county_miles(
    county_fips: str,
    station: NoaaStation,
) -> float:
    location = _weather_location_by_fips()[county_fips]
    return _distance_miles(
        location.centroid_lat,
        location.centroid_lon,
        station.latitude,
        station.longitude,
    )


def _distance_miles(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> float:
    earth_radius_miles = 3958.8
    dlat = radians(lat_b - lat_a)
    dlon = radians(lon_b - lon_a)
    start_lat = radians(lat_a)
    end_lat = radians(lat_b)
    haversine = sin(dlat / 2) ** 2 + cos(start_lat) * cos(end_lat) * sin(dlon / 2) ** 2
    return 2 * earth_radius_miles * asin(sqrt(min(1.0, haversine)))
