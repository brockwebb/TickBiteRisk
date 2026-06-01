"""Tests for the config-file-driven weather acquisition parameters.

Replaces hardcoded weather parameters (target states, GHCND variables, date
range, baseline window, station-selection knobs) with a TOML config read via
stdlib tomllib, validated fail-loud.
"""

from __future__ import annotations

from datetime import date

import pytest

from tickbiterisk.etl.weather_config import (
    WeatherConfigError,
    load_weather_config,
)

VALID = """
[weather]
states = ["DE", "DC", "MD", "PA", "VA", "WV"]
ghcnd_datatypes = ["TMAX", "TMIN", "PRCP", "SNOW", "SNWD"]
start_date = "1992-01-01"
end_date = "2021-12-31"
baseline_years = 30

[weather.station_selection]
station_limit = 1
min_data_coverage = 0.5
max_end_lag_days = 14
nearest_station_fallback = true
"""


def _write(tmp_path, body):
    path = tmp_path / "weather.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_loads_all_parameters(tmp_path):
    config = load_weather_config(_write(tmp_path, VALID))
    assert config.states == ["DE", "DC", "MD", "PA", "VA", "WV"]
    assert config.ghcnd_datatypes == ["TMAX", "TMIN", "PRCP", "SNOW", "SNWD"]
    assert config.start_date == date(1992, 1, 1)
    assert config.end_date == date(2021, 12, 31)
    assert config.baseline_years == 30
    assert config.station_limit == 1
    assert config.min_data_coverage == 0.5
    assert config.max_end_lag_days == 14
    assert config.nearest_station_fallback is True


def test_rejects_unknown_state(tmp_path):
    body = VALID.replace('"WV"]', '"WV", "NY"]')
    with pytest.raises(WeatherConfigError, match="NY"):
        load_weather_config(_write(tmp_path, body))


def test_rejects_start_after_end(tmp_path):
    body = VALID.replace('start_date = "1992-01-01"', 'start_date = "2025-01-01"')
    with pytest.raises(WeatherConfigError, match="start_date"):
        load_weather_config(_write(tmp_path, body))


def test_rejects_nonpositive_baseline_years(tmp_path):
    body = VALID.replace("baseline_years = 30", "baseline_years = 0")
    with pytest.raises(WeatherConfigError, match="baseline_years"):
        load_weather_config(_write(tmp_path, body))


def test_missing_file_fails_loud(tmp_path):
    with pytest.raises(WeatherConfigError, match="not found"):
        load_weather_config(tmp_path / "absent.toml")
