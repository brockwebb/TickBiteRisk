"""Config-file-driven weather acquisition parameters.

Externalizes the previously-hardcoded weather parameters (target jurisdictions,
GHCND variable selection, acquisition date range, climatological-baseline
window, station-selection knobs) into a TOML config read with stdlib ``tomllib``
(no new dependency). Validation is fail-loud: a malformed or out-of-range config
raises rather than silently producing a wrong acquisition.

The NOAA API token is intentionally NOT a config value — it is a secret read
from the ``NOAA_TOKEN`` environment variable via ``noaa.get_noaa_token``.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# The six-jurisdiction regional product (settled scope). A configured state must
# be one of these; the loader resolves its counties from the regional universe.
REGIONAL_STATES = ("DE", "DC", "MD", "PA", "VA", "WV")


class WeatherConfigError(ValueError):
    """Raised when the weather config file is missing or invalid."""


@dataclass(frozen=True)
class WeatherConfig:
    states: list[str]
    ghcnd_datatypes: list[str]
    start_date: date
    end_date: date
    baseline_years: int
    station_limit: int
    min_data_coverage: float
    max_end_lag_days: int
    nearest_station_fallback: bool


def _require(mapping: dict, key: str, context: str):
    if key not in mapping:
        raise WeatherConfigError(f"weather config missing required key: {context}{key}")
    return mapping[key]


def _parse_date(value: object, key: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise WeatherConfigError(f"{key} must be an ISO date (YYYY-MM-DD): {value!r}") from exc


def load_weather_config(path: Path) -> WeatherConfig:
    path = Path(path)
    if not path.is_file():
        raise WeatherConfigError(f"weather config file not found: {path}")
    try:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise WeatherConfigError(f"weather config is not valid TOML: {exc}") from exc

    weather = _require(document, "weather", "")
    if not isinstance(weather, dict):
        raise WeatherConfigError("[weather] table is required")

    states = list(_require(weather, "states", "weather."))
    if not states:
        raise WeatherConfigError("weather.states must list at least one jurisdiction")
    unknown = [s for s in states if s not in REGIONAL_STATES]
    if unknown:
        raise WeatherConfigError(
            f"weather.states contains non-regional jurisdiction(s): {unknown}; "
            f"allowed: {list(REGIONAL_STATES)}"
        )

    datatypes = list(_require(weather, "ghcnd_datatypes", "weather."))
    if not datatypes:
        raise WeatherConfigError("weather.ghcnd_datatypes must list at least one element")

    start_date = _parse_date(_require(weather, "start_date", "weather."), "weather.start_date")
    end_date = _parse_date(_require(weather, "end_date", "weather."), "weather.end_date")
    if start_date > end_date:
        raise WeatherConfigError(
            f"weather.start_date ({start_date}) must not be after weather.end_date ({end_date})"
        )

    baseline_years = int(_require(weather, "baseline_years", "weather."))
    if baseline_years <= 0:
        raise WeatherConfigError("weather.baseline_years must be a positive integer")

    selection = weather.get("station_selection", {})
    if not isinstance(selection, dict):
        raise WeatherConfigError("[weather.station_selection] must be a table")
    station_limit = int(selection.get("station_limit", 1))
    if station_limit < 1:
        raise WeatherConfigError("weather.station_selection.station_limit must be >= 1")
    min_data_coverage = float(selection.get("min_data_coverage", 0.5))
    if not 0.0 < min_data_coverage <= 1.0:
        raise WeatherConfigError(
            "weather.station_selection.min_data_coverage must be in (0, 1]"
        )
    max_end_lag_days = int(selection.get("max_end_lag_days", 14))
    if max_end_lag_days < 0:
        raise WeatherConfigError(
            "weather.station_selection.max_end_lag_days must be >= 0"
        )
    nearest_station_fallback = bool(selection.get("nearest_station_fallback", False))

    return WeatherConfig(
        states=states,
        ghcnd_datatypes=datatypes,
        start_date=start_date,
        end_date=end_date,
        baseline_years=baseline_years,
        station_limit=station_limit,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
        nearest_station_fallback=nearest_station_fallback,
    )
