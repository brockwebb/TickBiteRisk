# Maryland Weather Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Maryland weather ETL backbone: canonical county weather locations, Open-Meteo historical acquisition, daily parsing, monthly feature engineering, NOAA token safety, schema support, and CLI output.

**Architecture:** Keep weather ingestion separate from Lyme/source reconciliation code. Store county centroids as a packaged CSV resource, convert Open-Meteo archive responses into typed daily rows, compute model-ready monthly features with no future-year leakage, and expose a small CLI command that can backfill a bounded date range. The full 2000-2024 backfill remains a repeatable run of the same command across the 24 Maryland jurisdictions.

**Tech Stack:** Python 3.12, Typer CLI, pandas for CSV output, stdlib `urllib`/`json`/`dataclasses`, pytest. No test requires live network access.

---

## File Structure

- Create `tickbiterisk/resources/maryland_weather_locations.csv`: authoritative Maryland county/Baltimore City weather pull points from Census Gazetteer 2024 internal points.
- Create `tickbiterisk/etl/weather_locations.py`: loads and validates the weather location resource.
- Create `tickbiterisk/etl/open_meteo.py`: builds Open-Meteo archive URLs, fetches responses with retry, parses daily JSON into typed rows, and hashes the source URL.
- Create `tickbiterisk/etl/weather_features.py`: computes monthly tick-relevant weather features and trailing 10-year anomalies.
- Create `tickbiterisk/etl/noaa.py`: reads NOAA token from environment without leaking it.
- Create `tickbiterisk/etl/weather_build.py`: writes weather locations, daily weather, and monthly weather feature CSV outputs.
- Modify `tickbiterisk/cli.py`: add weather ETL commands.
- Modify `sql/schema.sql`: add `weather_locations`, `weather_daily`, and `weather_features_monthly`.
- Modify `docs/data-manifest.md`, `docs/software-requirements-spec.md`, and `README.md`: reflect weather ETL support and remaining acquisition work.
- Create tests:
  - `tests/test_weather_locations.py`
  - `tests/test_open_meteo.py`
  - `tests/test_weather_features.py`
  - `tests/test_noaa.py`
  - Extend `tests/test_build_outputs.py`
  - Extend `tests/test_schema.py`

---

### Task 1: Maryland Weather Location Resource

**Files:**
- Create: `tickbiterisk/resources/maryland_weather_locations.csv`
- Create: `tickbiterisk/etl/weather_locations.py`
- Test: `tests/test_weather_locations.py`

- [ ] **Step 1: Write the failing tests**

```python
from tickbiterisk.etl.maryland import maryland_fips_set
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations


def test_weather_locations_include_all_maryland_jurisdictions() -> None:
    locations = load_maryland_weather_locations()

    assert len(locations) == 24
    assert {row.county_fips for row in locations} == maryland_fips_set()


def test_anne_arundel_weather_location_uses_census_internal_point() -> None:
    locations = load_maryland_weather_locations()
    anne_arundel = next(row for row in locations if row.county_fips == "24003")

    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.state == "MD"
    assert anne_arundel.state_fips == "24"
    assert anne_arundel.centroid_lat == 38.991617
    assert anne_arundel.centroid_lon == -76.560894
    assert anne_arundel.geography_source == "Census Gazetteer 2024 county internal point"


def test_baltimore_city_weather_location_is_present() -> None:
    locations = load_maryland_weather_locations()
    baltimore_city = next(row for row in locations if row.county_fips == "24510")

    assert baltimore_city.county_name == "Baltimore City"
    assert baltimore_city.centroid_lat == 39.300032
    assert baltimore_city.centroid_lon == -76.610476
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_weather_locations.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.weather_locations'`.

- [ ] **Step 3: Add the weather location CSV**

Create `tickbiterisk/resources/maryland_weather_locations.csv` with this exact header and rows:

```csv
county_fips,state_fips,state,county_name,centroid_lat,centroid_lon,geography_source
24001,24,MD,Allegany County,39.612313,-78.703104,Census Gazetteer 2024 county internal point
24003,24,MD,Anne Arundel County,38.991617,-76.560894,Census Gazetteer 2024 county internal point
24005,24,MD,Baltimore County,39.443167,-76.616569,Census Gazetteer 2024 county internal point
24009,24,MD,Calvert County,38.522719,-76.529762,Census Gazetteer 2024 county internal point
24011,24,MD,Caroline County,38.871531,-75.831662,Census Gazetteer 2024 county internal point
24013,24,MD,Carroll County,39.563328,-77.015330,Census Gazetteer 2024 county internal point
24015,24,MD,Cecil County,39.562354,-75.941585,Census Gazetteer 2024 county internal point
24017,24,MD,Charles County,38.472853,-77.015427,Census Gazetteer 2024 county internal point
24019,24,MD,Dorchester County,38.429196,-76.047433,Census Gazetteer 2024 county internal point
24021,24,MD,Frederick County,39.470177,-77.397636,Census Gazetteer 2024 county internal point
24023,24,MD,Garrett County,39.547299,-79.274619,Census Gazetteer 2024 county internal point
24025,24,MD,Harford County,39.537429,-76.299789,Census Gazetteer 2024 county internal point
24027,24,MD,Howard County,39.252264,-76.924406,Census Gazetteer 2024 county internal point
24029,24,MD,Kent County,39.241279,-76.125987,Census Gazetteer 2024 county internal point
24031,24,MD,Montgomery County,39.137381,-77.203063,Census Gazetteer 2024 county internal point
24033,24,MD,Prince George's County,38.829278,-76.848188,Census Gazetteer 2024 county internal point
24035,24,MD,Queen Anne's County,39.040693,-76.082405,Census Gazetteer 2024 county internal point
24037,24,MD,St. Mary's County,38.223077,-76.534487,Census Gazetteer 2024 county internal point
24039,24,MD,Somerset County,38.074450,-75.853323,Census Gazetteer 2024 county internal point
24041,24,MD,Talbot County,38.748349,-76.178476,Census Gazetteer 2024 county internal point
24043,24,MD,Washington County,39.603621,-77.814671,Census Gazetteer 2024 county internal point
24045,24,MD,Wicomico County,38.367368,-75.632084,Census Gazetteer 2024 county internal point
24047,24,MD,Worcester County,38.222133,-75.309931,Census Gazetteer 2024 county internal point
24510,24,MD,Baltimore City,39.300032,-76.610476,Census Gazetteer 2024 county internal point
```

- [ ] **Step 4: Implement the loader**

Create `tickbiterisk/etl/weather_locations.py`:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib.resources import files

from tickbiterisk.etl.maryland import maryland_fips_set


@dataclass(frozen=True)
class WeatherLocation:
    county_fips: str
    state_fips: str
    state: str
    county_name: str
    centroid_lat: float
    centroid_lon: float
    geography_source: str


def load_maryland_weather_locations() -> list[WeatherLocation]:
    resource = files("tickbiterisk.resources").joinpath(
        "maryland_weather_locations.csv"
    )
    with resource.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    locations = [
        WeatherLocation(
            county_fips=str(row["county_fips"]).zfill(5),
            state_fips=str(row["state_fips"]).zfill(2),
            state=row["state"],
            county_name=row["county_name"],
            centroid_lat=float(row["centroid_lat"]),
            centroid_lon=float(row["centroid_lon"]),
            geography_source=row["geography_source"],
        )
        for row in rows
    ]

    fips = {row.county_fips for row in locations}
    expected = maryland_fips_set()
    if len(locations) != 24 or fips != expected:
        missing = sorted(expected - fips)
        extra = sorted(fips - expected)
        raise ValueError(
            "Weather location resource must match Maryland jurisdictions; "
            f"missing={missing}, extra={extra}, count={len(locations)}"
        )
    return locations
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_weather_locations.py -q
```

Expected: PASS, 3 tests.

- [ ] **Step 6: Commit**

```bash
git add tickbiterisk/resources/maryland_weather_locations.csv tickbiterisk/etl/weather_locations.py tests/test_weather_locations.py
git commit -m "feat: add Maryland weather locations"
```

---

### Task 2: Open-Meteo URL Builder and Daily Parser

**Files:**
- Create: `tickbiterisk/etl/open_meteo.py`
- Test: `tests/test_open_meteo.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from tickbiterisk.etl.open_meteo import (
    OPEN_METEO_ARCHIVE_ENDPOINT,
    OPEN_METEO_DAILY_VARIABLES,
    OpenMeteoArchiveError,
    build_open_meteo_archive_url,
    parse_open_meteo_archive_response,
)
from tickbiterisk.etl.weather_locations import WeatherLocation


LOCATION = WeatherLocation(
    county_fips="24003",
    state_fips="24",
    state="MD",
    county_name="Anne Arundel County",
    centroid_lat=38.991617,
    centroid_lon=-76.560894,
    geography_source="Census Gazetteer 2024 county internal point",
)


def test_build_open_meteo_archive_url_includes_required_query() -> None:
    url = build_open_meteo_archive_url(
        LOCATION,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    daily_values = query["daily"][0].split(",")

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == OPEN_METEO_ARCHIVE_ENDPOINT
    assert query["latitude"] == ["38.991617"]
    assert query["longitude"] == ["-76.560894"]
    assert query["start_date"] == ["2020-01-01"]
    assert query["end_date"] == ["2020-01-31"]
    assert query["temperature_unit"] == ["fahrenheit"]
    assert query["wind_speed_unit"] == ["mph"]
    assert query["precipitation_unit"] == ["mm"]
    assert query["timezone"] == ["America/New_York"]
    assert set(OPEN_METEO_DAILY_VARIABLES) <= set(daily_values)


def test_parse_open_meteo_archive_response_maps_daily_rows() -> None:
    payload = {
        "daily": {
            "time": ["2020-01-01", "2020-01-02"],
            "temperature_2m_mean": [44.0, 38.0],
            "temperature_2m_max": [51.0, 42.0],
            "temperature_2m_min": [31.0, 28.0],
            "relative_humidity_2m_mean": [88.0, 74.0],
            "relative_humidity_2m_max": [96.0, 85.0],
            "relative_humidity_2m_min": [72.0, 61.0],
            "dew_point_2m_mean": [39.0, 30.0],
            "precipitation_sum": [2.5, 0.0],
            "rain_sum": [2.5, 0.0],
            "snowfall_sum": [0.0, 0.0],
            "precipitation_hours": [4.0, 0.0],
            "soil_temperature_0_to_7cm_mean": [41.0, 36.0],
            "soil_moisture_0_to_7cm_mean": [0.32, 0.28],
            "et0_fao_evapotranspiration": [0.4, 0.6],
            "wind_speed_10m_mean": [5.0, 8.0],
            "wind_speed_10m_max": [12.0, 15.0],
        }
    }
    rows = parse_open_meteo_archive_response(
        payload,
        location=LOCATION,
        source_url="https://example.test/weather",
        weather_model="open_meteo_archive",
    )

    assert len(rows) == 2
    assert rows[0].county_fips == "24003"
    assert rows[0].date.isoformat() == "2020-01-01"
    assert rows[0].source == "open_meteo_archive"
    assert rows[0].weather_model == "open_meteo_archive"
    assert rows[0].temp_mean_f == 44.0
    assert rows[0].humidity_mean_pct == 88.0
    assert rows[0].precipitation_mm == 2.5
    assert len(rows[0].source_url_hash) == 64


def test_parse_open_meteo_archive_response_rejects_missing_required_variable() -> None:
    payload = {"daily": {"time": ["2020-01-01"]}}

    with pytest.raises(OpenMeteoArchiveError, match="temperature_2m_mean"):
        parse_open_meteo_archive_response(
            payload,
            location=LOCATION,
            source_url="https://example.test/weather",
            weather_model="open_meteo_archive",
        )


def test_parse_open_meteo_archive_response_rejects_mismatched_lengths() -> None:
    payload = {
        "daily": {
            variable: [1.0, 2.0]
            for variable in OPEN_METEO_DAILY_VARIABLES
        }
    }
    payload["daily"]["time"] = ["2020-01-01"]

    with pytest.raises(OpenMeteoArchiveError, match="length"):
        parse_open_meteo_archive_response(
            payload,
            location=LOCATION,
            source_url="https://example.test/weather",
            weather_model="open_meteo_archive",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_open_meteo.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.open_meteo'`.

- [ ] **Step 3: Implement URL construction and parsing**

Create `tickbiterisk/etl/open_meteo.py`:

```python
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.etl.weather_locations import WeatherLocation

OPEN_METEO_ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_DAILY_VARIABLES = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "dew_point_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
]


class OpenMeteoArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class WeatherDailyObservation:
    county_fips: str
    date: date
    source: str
    weather_model: str
    temp_mean_f: float
    temp_max_f: float
    temp_min_f: float
    humidity_mean_pct: float
    humidity_max_pct: float
    humidity_min_pct: float
    dew_point_mean_f: float
    precipitation_mm: float
    rain_mm: float
    snowfall_mm: float
    precipitation_hours: float
    soil_temp_0_7cm_f: float
    soil_moisture_0_7cm: float
    evapotranspiration_mm: float
    wind_mean_mph: float
    wind_max_mph: float
    source_url_hash: str


def build_open_meteo_archive_url(
    location: WeatherLocation,
    start_date: date,
    end_date: date,
    *,
    weather_model: str = "open_meteo_archive",
) -> str:
    if end_date < start_date:
        raise OpenMeteoArchiveError("end_date must be on or after start_date")

    query = {
        "latitude": f"{location.centroid_lat:.6f}",
        "longitude": f"{location.centroid_lon:.6f}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(OPEN_METEO_DAILY_VARIABLES),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "mm",
        "timezone": "America/New_York",
    }
    if weather_model != "open_meteo_archive":
        query["models"] = weather_model
    return f"{OPEN_METEO_ARCHIVE_ENDPOINT}?{urlencode(query)}"


def parse_open_meteo_archive_response(
    payload: dict[str, Any],
    *,
    location: WeatherLocation,
    source_url: str,
    weather_model: str,
) -> list[WeatherDailyObservation]:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise OpenMeteoArchiveError("Open-Meteo response is missing daily data")

    required = ["time", *OPEN_METEO_DAILY_VARIABLES]
    for variable in required:
        if variable not in daily:
            raise OpenMeteoArchiveError(f"Open-Meteo daily data missing {variable}")

    times = daily["time"]
    if not isinstance(times, list):
        raise OpenMeteoArchiveError("Open-Meteo daily time must be a list")

    expected_length = len(times)
    for variable in OPEN_METEO_DAILY_VARIABLES:
        values = daily[variable]
        if not isinstance(values, list) or len(values) != expected_length:
            raise OpenMeteoArchiveError(
                f"Open-Meteo daily variable {variable} has mismatched length"
            )

    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows: list[WeatherDailyObservation] = []
    for index, raw_date in enumerate(times):
        rows.append(
            WeatherDailyObservation(
                county_fips=location.county_fips,
                date=date.fromisoformat(raw_date),
                source="open_meteo_archive",
                weather_model=weather_model,
                temp_mean_f=float(daily["temperature_2m_mean"][index]),
                temp_max_f=float(daily["temperature_2m_max"][index]),
                temp_min_f=float(daily["temperature_2m_min"][index]),
                humidity_mean_pct=float(daily["relative_humidity_2m_mean"][index]),
                humidity_max_pct=float(daily["relative_humidity_2m_max"][index]),
                humidity_min_pct=float(daily["relative_humidity_2m_min"][index]),
                dew_point_mean_f=float(daily["dew_point_2m_mean"][index]),
                precipitation_mm=float(daily["precipitation_sum"][index]),
                rain_mm=float(daily["rain_sum"][index]),
                snowfall_mm=float(daily["snowfall_sum"][index]),
                precipitation_hours=float(daily["precipitation_hours"][index]),
                soil_temp_0_7cm_f=float(
                    daily["soil_temperature_0_to_7cm_mean"][index]
                ),
                soil_moisture_0_7cm=float(
                    daily["soil_moisture_0_to_7cm_mean"][index]
                ),
                evapotranspiration_mm=float(
                    daily["et0_fao_evapotranspiration"][index]
                ),
                wind_mean_mph=float(daily["wind_speed_10m_mean"][index]),
                wind_max_mph=float(daily["wind_speed_10m_max"][index]),
                source_url_hash=source_url_hash,
            )
        )
    return rows


def _default_json_get(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_open_meteo_archive(
    location: WeatherLocation,
    start_date: date,
    end_date: date,
    *,
    weather_model: str = "open_meteo_archive",
    json_get: Callable[[str], dict[str, Any]] = _default_json_get,
    max_attempts: int = 3,
    sleep_seconds: float = 1.0,
) -> list[WeatherDailyObservation]:
    url = build_open_meteo_archive_url(
        location,
        start_date,
        end_date,
        weather_model=weather_model,
    )
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            payload = json_get(url)
            return parse_open_meteo_archive_response(
                payload,
                location=location,
                source_url=url,
                weather_model=weather_model,
            )
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(sleep_seconds * attempt)
    raise OpenMeteoArchiveError(f"Open-Meteo archive fetch failed: {last_error}")
```

- [ ] **Step 4: Add fetch test with injected fake JSON getter**

Append to `tests/test_open_meteo.py`:

```python
def test_fetch_open_meteo_archive_uses_injected_json_get() -> None:
    calls: list[str] = []

    def fake_json_get(url: str) -> dict:
        calls.append(url)
        return {
            "daily": {
                "time": ["2020-01-01"],
                "temperature_2m_mean": [44.0],
                "temperature_2m_max": [51.0],
                "temperature_2m_min": [31.0],
                "relative_humidity_2m_mean": [88.0],
                "relative_humidity_2m_max": [96.0],
                "relative_humidity_2m_min": [72.0],
                "dew_point_2m_mean": [39.0],
                "precipitation_sum": [2.5],
                "rain_sum": [2.5],
                "snowfall_sum": [0.0],
                "precipitation_hours": [4.0],
                "soil_temperature_0_to_7cm_mean": [41.0],
                "soil_moisture_0_to_7cm_mean": [0.32],
                "et0_fao_evapotranspiration": [0.4],
                "wind_speed_10m_mean": [5.0],
                "wind_speed_10m_max": [12.0],
            }
        }

    rows = fetch_open_meteo_archive(
        LOCATION,
        date(2020, 1, 1),
        date(2020, 1, 1),
        json_get=fake_json_get,
        sleep_seconds=0,
    )

    assert len(calls) == 1
    assert rows[0].date.isoformat() == "2020-01-01"
```

Import `fetch_open_meteo_archive` in the existing import block.

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_open_meteo.py -q
```

Expected: PASS, 5 tests.

- [ ] **Step 6: Commit**

```bash
git add tickbiterisk/etl/open_meteo.py tests/test_open_meteo.py
git commit -m "feat: add Open-Meteo archive parser"
```

---

### Task 3: Monthly Weather Feature Engineering

**Files:**
- Create: `tickbiterisk/etl/weather_features.py`
- Test: `tests/test_weather_features.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date

from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    compute_monthly_weather_features,
)


def obs(day: date, **overrides: float) -> WeatherDailyObservation:
    values = {
        "temp_mean_f": 55.0,
        "temp_max_f": 62.0,
        "temp_min_f": 45.0,
        "humidity_mean_pct": 82.0,
        "humidity_max_pct": 95.0,
        "humidity_min_pct": 65.0,
        "dew_point_mean_f": 48.0,
        "precipitation_mm": 0.0,
        "rain_mm": 0.0,
        "snowfall_mm": 0.0,
        "precipitation_hours": 0.0,
        "soil_temp_0_7cm_f": 48.0,
        "soil_moisture_0_7cm": 0.30,
        "evapotranspiration_mm": 1.0,
        "wind_mean_mph": 5.0,
        "wind_max_mph": 10.0,
    }
    values.update(overrides)
    return WeatherDailyObservation(
        county_fips="24003",
        date=day,
        source="open_meteo_archive",
        weather_model="open_meteo_archive",
        source_url_hash="a" * 64,
        **values,
    )


def test_compute_monthly_weather_features_matches_hand_calculation() -> None:
    rows = [
        obs(
            date(2020, 5, 1),
            temp_mean_f=45.0,
            temp_max_f=55.0,
            temp_min_f=30.0,
            humidity_mean_pct=90.0,
            precipitation_mm=2.0,
            rain_mm=2.0,
            soil_temp_0_7cm_f=42.0,
            soil_moisture_0_7cm=0.25,
            evapotranspiration_mm=0.5,
        ),
        obs(
            date(2020, 5, 2),
            temp_mean_f=60.0,
            temp_max_f=66.0,
            temp_min_f=52.0,
            precipitation_mm=0.0,
            soil_temp_0_7cm_f=55.0,
            soil_moisture_0_7cm=0.35,
            evapotranspiration_mm=1.5,
        ),
        obs(
            date(2020, 5, 3),
            temp_mean_f=75.0,
            temp_max_f=92.0,
            temp_min_f=66.0,
            humidity_mean_pct=50.0,
            precipitation_mm=0.0,
            soil_temp_0_7cm_f=70.0,
            soil_moisture_0_7cm=0.20,
            evapotranspiration_mm=2.0,
        ),
    ]

    features = compute_monthly_weather_features(rows)

    assert len(features) == 1
    may = features[0]
    assert may.county_fips == "24003"
    assert may.year == 2020
    assert may.month == 5
    assert may.days_above_40f == 3
    assert may.days_50_65f == 1
    assert may.days_70_85f == 1
    assert may.degree_days_above_40f == 60.0
    assert may.freeze_thaw_days == 1
    assert may.precip_total_mm == 2.0
    assert may.rain_total_mm == 2.0
    assert may.snowfall_total_mm == 0.0
    assert may.precip_days == 1
    assert may.dry_spell_max_days == 2
    assert may.humidity_days_above_85pct == 1
    assert may.soil_moisture_mean == 0.266667
    assert may.soil_temp_above_40f_days == 3
    assert may.hot_dry_stress_days == 1
    assert may.evapotranspiration_total_mm == 4.0


def test_dry_spell_is_computed_within_each_month() -> None:
    rows = [
        obs(date(2020, 5, 30), precipitation_mm=0.0),
        obs(date(2020, 5, 31), precipitation_mm=0.0),
        obs(date(2020, 6, 1), precipitation_mm=0.0),
        obs(date(2020, 6, 2), precipitation_mm=1.0),
    ]

    features = compute_monthly_weather_features(rows)
    by_month = {feature.month: feature for feature in features}

    assert by_month[5].dry_spell_max_days == 2
    assert by_month[6].dry_spell_max_days == 1


def test_trailing_monthly_anomalies_do_not_use_current_or_future_years() -> None:
    features = []
    for year, temp, precip, humidity in [
        (2010, 50.0, 10.0, 70.0),
        (2011, 52.0, 12.0, 72.0),
        (2012, 54.0, 14.0, 74.0),
        (2020, 70.0, 25.0, 90.0),
    ]:
        month_rows = [
            obs(
                date(year, 5, 1),
                temp_mean_f=temp,
                precipitation_mm=precip,
                humidity_mean_pct=humidity,
            )
        ]
        features.extend(compute_monthly_weather_features(month_rows))

    with_anomalies = add_trailing_monthly_anomalies(features, baseline_years=10)
    year_2020 = next(feature for feature in with_anomalies if feature.year == 2020)

    assert year_2020.temp_anomaly_vs_10yr == 18.0
    assert year_2020.precip_anomaly_vs_10yr == 13.0
    assert year_2020.humidity_anomaly_vs_10yr == 18.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_weather_features.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.weather_features'`.

- [ ] **Step 3: Implement monthly features and anomalies**

Create `tickbiterisk/etl/weather_features.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import groupby
from statistics import mean

from tickbiterisk.etl.open_meteo import WeatherDailyObservation


@dataclass(frozen=True)
class WeatherMonthlyFeature:
    county_fips: str
    year: int
    month: int
    source: str
    weather_model: str
    days_above_40f: int
    days_50_65f: int
    days_70_85f: int
    degree_days_above_40f: float
    freeze_thaw_days: int
    precip_total_mm: float
    rain_total_mm: float
    snowfall_total_mm: float
    precip_days: int
    dry_spell_max_days: int
    humidity_days_above_85pct: int
    soil_moisture_mean: float
    soil_temp_above_40f_days: int
    hot_dry_stress_days: int
    evapotranspiration_total_mm: float
    temp_mean_f: float
    precip_mean_mm: float
    humidity_mean_pct: float
    temp_anomaly_vs_10yr: float | None = None
    precip_anomaly_vs_10yr: float | None = None
    humidity_anomaly_vs_10yr: float | None = None


def compute_monthly_weather_features(
    observations: list[WeatherDailyObservation],
) -> list[WeatherMonthlyFeature]:
    sorted_rows = sorted(
        observations,
        key=lambda row: (row.county_fips, row.source, row.weather_model, row.date),
    )
    features: list[WeatherMonthlyFeature] = []

    def key(row: WeatherDailyObservation) -> tuple[str, str, str, int, int]:
        return (
            row.county_fips,
            row.source,
            row.weather_model,
            row.date.year,
            row.date.month,
        )

    for (county_fips, source, weather_model, year, month), group in groupby(
        sorted_rows, key=key
    ):
        rows = list(group)
        dry_spell_max = _longest_dry_spell(rows)
        features.append(
            WeatherMonthlyFeature(
                county_fips=county_fips,
                year=year,
                month=month,
                source=source,
                weather_model=weather_model,
                days_above_40f=sum(row.temp_max_f >= 40 for row in rows),
                days_50_65f=sum(50 <= row.temp_mean_f <= 65 for row in rows),
                days_70_85f=sum(70 <= row.temp_mean_f <= 85 for row in rows),
                degree_days_above_40f=round(
                    sum(max(row.temp_mean_f - 40, 0) for row in rows), 6
                ),
                freeze_thaw_days=sum(
                    row.temp_min_f < 32 and row.temp_max_f > 32 for row in rows
                ),
                precip_total_mm=round(sum(row.precipitation_mm for row in rows), 6),
                rain_total_mm=round(sum(row.rain_mm for row in rows), 6),
                snowfall_total_mm=round(sum(row.snowfall_mm for row in rows), 6),
                precip_days=sum(row.precipitation_mm > 0 for row in rows),
                dry_spell_max_days=dry_spell_max,
                humidity_days_above_85pct=sum(
                    row.humidity_mean_pct >= 85 for row in rows
                ),
                soil_moisture_mean=round(
                    mean(row.soil_moisture_0_7cm for row in rows), 6
                ),
                soil_temp_above_40f_days=sum(
                    row.soil_temp_0_7cm_f >= 40 for row in rows
                ),
                hot_dry_stress_days=sum(
                    row.temp_max_f >= 90 and row.humidity_mean_pct < 55 for row in rows
                ),
                evapotranspiration_total_mm=round(
                    sum(row.evapotranspiration_mm for row in rows), 6
                ),
                temp_mean_f=round(mean(row.temp_mean_f for row in rows), 6),
                precip_mean_mm=round(mean(row.precipitation_mm for row in rows), 6),
                humidity_mean_pct=round(mean(row.humidity_mean_pct for row in rows), 6),
            )
        )
    return features


def add_trailing_monthly_anomalies(
    features: list[WeatherMonthlyFeature],
    *,
    baseline_years: int = 10,
) -> list[WeatherMonthlyFeature]:
    sorted_features = sorted(
        features,
        key=lambda row: (
            row.county_fips,
            row.source,
            row.weather_model,
            row.month,
            row.year,
        ),
    )
    output: list[WeatherMonthlyFeature] = []

    def key(row: WeatherMonthlyFeature) -> tuple[str, str, str, int]:
        return (row.county_fips, row.source, row.weather_model, row.month)

    for _, group in groupby(sorted_features, key=key):
        history: list[WeatherMonthlyFeature] = []
        for row in group:
            trailing = [
                prior
                for prior in history
                if row.year - baseline_years <= prior.year < row.year
            ]
            if trailing:
                row = replace(
                    row,
                    temp_anomaly_vs_10yr=round(
                        row.temp_mean_f - mean(prior.temp_mean_f for prior in trailing),
                        6,
                    ),
                    precip_anomaly_vs_10yr=round(
                        row.precip_mean_mm
                        - mean(prior.precip_mean_mm for prior in trailing),
                        6,
                    ),
                    humidity_anomaly_vs_10yr=round(
                        row.humidity_mean_pct
                        - mean(prior.humidity_mean_pct for prior in trailing),
                        6,
                    ),
                )
            output.append(row)
            history.append(row)

    return sorted(output, key=lambda row: (row.county_fips, row.year, row.month))


def _longest_dry_spell(rows: list[WeatherDailyObservation]) -> int:
    longest = 0
    current = 0
    for row in sorted(rows, key=lambda item: item.date):
        if row.precipitation_mm == 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_weather_features.py -q
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add tickbiterisk/etl/weather_features.py tests/test_weather_features.py
git commit -m "feat: compute monthly weather features"
```

---

### Task 4: NOAA Token Safety

**Files:**
- Create: `tickbiterisk/etl/noaa.py`
- Test: `tests/test_noaa.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from tickbiterisk.etl.noaa import NoaaTokenMissingError, get_noaa_token


def test_get_noaa_token_reads_from_environment_mapping() -> None:
    assert get_noaa_token({"NOAA_TOKEN": "secret-value"}) == "secret-value"


def test_get_noaa_token_fails_without_leaking_secret_name_value() -> None:
    with pytest.raises(NoaaTokenMissingError) as exc:
        get_noaa_token({})

    message = str(exc.value)
    assert "NOAA_TOKEN is required for NOAA CDO validation" in message
    assert "secret" not in message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_noaa.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.noaa'`.

- [ ] **Step 3: Implement environment-only NOAA token access**

Create `tickbiterisk/etl/noaa.py`:

```python
from __future__ import annotations

import os
from collections.abc import Mapping


class NoaaTokenMissingError(RuntimeError):
    pass


def get_noaa_token(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    token = source.get("NOAA_TOKEN", "").strip()
    if not token:
        raise NoaaTokenMissingError("NOAA_TOKEN is required for NOAA CDO validation")
    return token
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_noaa.py -q
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add tickbiterisk/etl/noaa.py tests/test_noaa.py
git commit -m "feat: add NOAA token guard"
```

---

### Task 5: Weather Output Writers

**Files:**
- Create: `tickbiterisk/etl/weather_build.py`
- Modify: `tests/test_build_outputs.py`

- [ ] **Step 1: Write failing writer tests**

Append to `tests/test_build_outputs.py`:

```python
from datetime import date

from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.weather_build import (
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_locations_output,
)
from tickbiterisk.etl.weather_features import compute_monthly_weather_features
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations


def sample_weather_daily() -> WeatherDailyObservation:
    return WeatherDailyObservation(
        county_fips="24003",
        date=date(2020, 5, 1),
        source="open_meteo_archive",
        weather_model="open_meteo_archive",
        temp_mean_f=55.0,
        temp_max_f=62.0,
        temp_min_f=45.0,
        humidity_mean_pct=82.0,
        humidity_max_pct=95.0,
        humidity_min_pct=65.0,
        dew_point_mean_f=48.0,
        precipitation_mm=0.0,
        rain_mm=0.0,
        snowfall_mm=0.0,
        precipitation_hours=0.0,
        soil_temp_0_7cm_f=48.0,
        soil_moisture_0_7cm=0.30,
        evapotranspiration_mm=1.0,
        wind_mean_mph=5.0,
        wind_max_mph=10.0,
        source_url_hash="a" * 64,
    )


def test_write_weather_locations_output_creates_csv(tmp_path: Path) -> None:
    output = write_weather_locations_output(
        load_maryland_weather_locations()[:1], tmp_path
    )

    df = pd.read_csv(output, dtype={"county_fips": str, "state_fips": str})

    assert output.name == "weather_locations.csv"
    assert list(df.columns) == [
        "county_fips",
        "state_fips",
        "state",
        "county_name",
        "centroid_lat",
        "centroid_lon",
        "geography_source",
    ]
    assert df.loc[0, "county_fips"] == "24001"


def test_write_weather_daily_output_creates_csv(tmp_path: Path) -> None:
    output = write_weather_daily_output([sample_weather_daily()], tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "weather_daily.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert df.loc[0, "date"] == "2020-05-01"
    assert df.loc[0, "source"] == "open_meteo_archive"
    assert float(df.loc[0, "temp_mean_f"]) == 55.0


def test_write_weather_features_monthly_output_creates_csv(tmp_path: Path) -> None:
    features = compute_monthly_weather_features([sample_weather_daily()])
    output = write_weather_features_monthly_output(features, tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "weather_features_monthly.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "year"]) == 2020
    assert int(df.loc[0, "month"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_build_outputs.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.weather_build'`.

- [ ] **Step 3: Implement output writers**

Create `tickbiterisk/etl/weather_build.py`:

```python
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.weather_features import WeatherMonthlyFeature
from tickbiterisk.etl.weather_locations import WeatherLocation

WEATHER_LOCATION_COLUMNS = [
    "county_fips",
    "state_fips",
    "state",
    "county_name",
    "centroid_lat",
    "centroid_lon",
    "geography_source",
]

WEATHER_DAILY_COLUMNS = [
    "county_fips",
    "date",
    "source",
    "weather_model",
    "temp_mean_f",
    "temp_max_f",
    "temp_min_f",
    "humidity_mean_pct",
    "humidity_max_pct",
    "humidity_min_pct",
    "dew_point_mean_f",
    "precipitation_mm",
    "rain_mm",
    "snowfall_mm",
    "precipitation_hours",
    "soil_temp_0_7cm_f",
    "soil_moisture_0_7cm",
    "evapotranspiration_mm",
    "wind_mean_mph",
    "wind_max_mph",
    "source_url_hash",
]

WEATHER_MONTHLY_COLUMNS = [
    "county_fips",
    "year",
    "month",
    "source",
    "weather_model",
    "days_above_40f",
    "days_50_65f",
    "days_70_85f",
    "degree_days_above_40f",
    "freeze_thaw_days",
    "precip_total_mm",
    "rain_total_mm",
    "snowfall_total_mm",
    "precip_days",
    "dry_spell_max_days",
    "humidity_days_above_85pct",
    "soil_moisture_mean",
    "soil_temp_above_40f_days",
    "hot_dry_stress_days",
    "evapotranspiration_total_mm",
    "temp_mean_f",
    "precip_mean_mm",
    "humidity_mean_pct",
    "temp_anomaly_vs_10yr",
    "precip_anomaly_vs_10yr",
    "humidity_anomaly_vs_10yr",
]


def write_weather_locations_output(
    locations: list[WeatherLocation], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_locations.csv"
    pd.DataFrame(
        [asdict(location) for location in locations], columns=WEATHER_LOCATION_COLUMNS
    ).to_csv(output_path, index=False)
    return output_path


def write_weather_daily_output(
    rows: list[WeatherDailyObservation], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_daily.csv"
    records = []
    for row in rows:
        record = asdict(row)
        record["date"] = row.date.isoformat()
        records.append(record)
    pd.DataFrame(records, columns=WEATHER_DAILY_COLUMNS).to_csv(output_path, index=False)
    return output_path


def write_weather_features_monthly_output(
    rows: list[WeatherMonthlyFeature], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_features_monthly.csv"
    pd.DataFrame([asdict(row) for row in rows], columns=WEATHER_MONTHLY_COLUMNS).to_csv(
        output_path, index=False
    )
    return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_build_outputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tickbiterisk/etl/weather_build.py tests/test_build_outputs.py
git commit -m "feat: write weather ETL outputs"
```

---

### Task 6: Weather CLI Commands

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: create `tests/test_cli_weather.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_weather.py`:

```python
from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_weather_locations_command_writes_locations(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["etl", "weather-locations", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert (tmp_path / "weather_locations.csv").exists()
    assert "weather_locations.csv" in result.stdout


def test_weather_backfill_dry_run_prints_open_meteo_url(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "weather-backfill-open-meteo",
            "--county-fips",
            "24003",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2020-01-02",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "archive-api.open-meteo.com" in result.stdout
    assert "24003" in result.stdout
    assert not (tmp_path / "weather_daily.csv").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_weather.py -q
```

Expected: FAIL because the commands do not exist.

- [ ] **Step 3: Implement weather CLI commands**

Modify `tickbiterisk/cli.py` to include these imports:

```python
from datetime import date
```

Add these imports below the Typer imports:

```python
from tickbiterisk.etl.open_meteo import (
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
)
from tickbiterisk.etl.weather_build import (
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_locations_output,
)
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    compute_monthly_weather_features,
)
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations
```

Add these commands after `etl_check`:

```python
@etl_app.command("weather-locations")
def weather_locations(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    )
) -> None:
    output = write_weather_locations_output(
        load_maryland_weather_locations(), output_dir
    )
    typer.echo(f"Wrote {output}")


@etl_app.command("weather-backfill-open-meteo")
def weather_backfill_open_meteo(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    start_date: date = typer.Option(..., help="Start date for archive pull."),
    end_date: date = typer.Option(..., help="End date for archive pull."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print URL without fetching data."),
) -> None:
    locations = load_maryland_weather_locations()
    location = next(
        (row for row in locations if row.county_fips == county_fips.zfill(5)),
        None,
    )
    if location is None:
        raise typer.BadParameter(f"Unknown Maryland county FIPS: {county_fips}")

    url = build_open_meteo_archive_url(location, start_date, end_date)
    if dry_run:
        typer.echo(f"{location.county_fips} {location.county_name}: {url}")
        return

    rows = fetch_open_meteo_archive(location, start_date, end_date)
    daily_output = write_weather_daily_output(rows, output_dir)
    monthly_features = add_trailing_monthly_anomalies(
        compute_monthly_weather_features(rows)
    )
    monthly_output = write_weather_features_monthly_output(monthly_features, output_dir)
    typer.echo(f"Wrote {daily_output}")
    typer.echo(f"Wrote {monthly_output}")
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_weather.py -q
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Run a live small-range smoke command**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl weather-backfill-open-meteo --county-fips 24003 --start-date 2020-01-01 --end-date 2020-01-03 --output-dir build/etl/weather-smoke
```

Expected: writes `build/etl/weather-smoke/weather_daily.csv` and `build/etl/weather-smoke/weather_features_monthly.csv`. If Open-Meteo is temporarily unavailable, rerun once; if still unavailable, record the HTTP error in the final status and keep tests as the verified acceptance path.

- [ ] **Step 6: Commit**

```bash
git add tickbiterisk/cli.py tests/test_cli_weather.py
git commit -m "feat: add weather ETL CLI commands"
```

---

### Task 7: Weather SQL Schema

**Files:**
- Modify: `sql/schema.sql`
- Modify: `tests/test_schema.py`

- [ ] **Step 1: Extend schema tests**

Modify `tests/test_schema.py` so `test_schema_defines_core_tables` includes:

```python
        "weather_locations",
        "weather_daily",
        "weather_features_monthly",
```

Append:

```python
def test_weather_daily_schema_has_model_ready_keys() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "PRIMARY KEY (county_fips, date, source, weather_model)" in schema
    assert "source_url_hash text NOT NULL" in schema
    assert "soil_moisture_0_7cm double precision" in schema


def test_weather_features_monthly_schema_has_anomaly_columns() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "temp_anomaly_vs_10yr double precision" in schema
    assert "precip_anomaly_vs_10yr double precision" in schema
    assert "humidity_anomaly_vs_10yr double precision" in schema
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_schema.py -q
```

Expected: FAIL because the weather tables do not exist.

- [ ] **Step 3: Add schema tables**

Append to `sql/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS weather_locations (
    county_fips char(5) PRIMARY KEY REFERENCES md_jurisdictions(county_fips),
    state_fips char(2) NOT NULL DEFAULT '24',
    state char(2) NOT NULL DEFAULT 'MD',
    county_name text NOT NULL,
    centroid_lat double precision NOT NULL,
    centroid_lon double precision NOT NULL,
    geography_source text NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS weather_daily (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    date date NOT NULL,
    source text NOT NULL,
    weather_model text NOT NULL,
    temp_mean_f double precision NOT NULL,
    temp_max_f double precision NOT NULL,
    temp_min_f double precision NOT NULL,
    humidity_mean_pct double precision NOT NULL,
    humidity_max_pct double precision NOT NULL,
    humidity_min_pct double precision NOT NULL,
    dew_point_mean_f double precision NOT NULL,
    precipitation_mm double precision NOT NULL,
    rain_mm double precision NOT NULL,
    snowfall_mm double precision NOT NULL,
    precipitation_hours double precision NOT NULL,
    soil_temp_0_7cm_f double precision NOT NULL,
    soil_moisture_0_7cm double precision,
    evapotranspiration_mm double precision NOT NULL,
    wind_mean_mph double precision NOT NULL,
    wind_max_mph double precision NOT NULL,
    source_url_hash text NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, date, source, weather_model)
);

CREATE TABLE IF NOT EXISTS weather_features_monthly (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    month integer NOT NULL CHECK (month BETWEEN 1 AND 12),
    source text NOT NULL,
    weather_model text NOT NULL,
    days_above_40f integer NOT NULL,
    days_50_65f integer NOT NULL,
    days_70_85f integer NOT NULL,
    degree_days_above_40f double precision NOT NULL,
    freeze_thaw_days integer NOT NULL,
    precip_total_mm double precision NOT NULL,
    rain_total_mm double precision NOT NULL,
    snowfall_total_mm double precision NOT NULL,
    precip_days integer NOT NULL,
    dry_spell_max_days integer NOT NULL,
    humidity_days_above_85pct integer NOT NULL,
    soil_moisture_mean double precision,
    soil_temp_above_40f_days integer NOT NULL,
    hot_dry_stress_days integer NOT NULL,
    evapotranspiration_total_mm double precision NOT NULL,
    temp_mean_f double precision NOT NULL,
    precip_mean_mm double precision NOT NULL,
    humidity_mean_pct double precision NOT NULL,
    temp_anomaly_vs_10yr double precision,
    precip_anomaly_vs_10yr double precision,
    humidity_anomaly_vs_10yr double precision,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year, month, source, weather_model)
);
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_schema.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sql/schema.sql tests/test_schema.py
git commit -m "feat: add weather schema tables"
```

---

### Task 8: Documentation and Full-Run Notes

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/software-requirements-spec.md`

- [ ] **Step 1: Add documentation checks**

Run:

```bash
rg -n "Open-Meteo|weather_daily|weather_features_monthly|NOAA_TOKEN|2000-01-01" README.md docs/data-manifest.md docs/software-requirements-spec.md
```

Expected before edits: some terms are missing from one or more files.

- [ ] **Step 2: Update README command examples**

Add a short weather ETL section to `README.md`:

```markdown
### Maryland Weather ETL

The weather slice uses Open-Meteo historical archive data at Census Gazetteer county internal points for Maryland's 23 counties plus Baltimore City.

```bash
tickbiterisk etl weather-locations --output-dir build/etl
tickbiterisk etl weather-backfill-open-meteo \
  --county-fips 24003 \
  --start-date 2020-01-01 \
  --end-date 2020-01-03 \
  --output-dir build/etl/weather-smoke
```

The full Maryland weather backfill is the same command run for each `weather_locations.csv` row over `2000-01-01` through `2024-12-31`. NOAA CDO validation reads `NOAA_TOKEN` from the local environment only.
```

- [ ] **Step 3: Update data manifest**

In `docs/data-manifest.md`, ensure the Open-Meteo source row or section contains:

```markdown
| `open_meteo_archive_md_county_daily` | Open-Meteo Historical Weather API | `https://archive-api.open-meteo.com/v1/archive` | Daily county-centroid weather for Maryland jurisdictions | 2000-01-01 to 2024-12-31 planned | API JSON -> `weather_daily` / `weather_features_monthly` | No key required | `etl_supported`, `backfill_pending` |
```

Also ensure NOAA CDO is represented as validation-only:

```markdown
| `noaa_cdo_station_validation` | NOAA CDO API | `https://www.ncdc.noaa.gov/cdo-web/webservices/v2` | Station observations for spot-checking Open-Meteo | Validation subset only | API JSON | Requires local `NOAA_TOKEN`; token must not be committed or logged | `validation_branch`, `not_primary_backfill` |
```

- [ ] **Step 4: Update SRS**

In `docs/software-requirements-spec.md`, add or update weather requirements so they state:

```markdown
- The system shall load one weather pull location for each Maryland county and Baltimore City using Census Gazetteer county internal points.
- The system shall backfill Open-Meteo daily weather for bounded county/date ranges and write `weather_daily.csv`.
- The system shall derive monthly tick-activity features and trailing 10-year anomaly fields without using current or future years in a historical backtest baseline.
- NOAA CDO validation shall read `NOAA_TOKEN` only from the local process environment.
```

- [ ] **Step 5: Verify documentation terms**

Run:

```bash
rg -n "Open-Meteo|weather_daily|weather_features_monthly|NOAA_TOKEN|2000-01-01" README.md docs/data-manifest.md docs/software-requirements-spec.md
```

Expected: all five terms appear.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/data-manifest.md docs/software-requirements-spec.md
git commit -m "docs: document Maryland weather ETL"
```

---

### Task 9: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run all tests**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run style check**

Run:

```bash
.venv/bin/python -m ruff check .
```

Expected: no lint violations.

- [ ] **Step 3: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Check weather smoke outputs**

If Task 6 live smoke succeeded, run:

```bash
head -n 5 build/etl/weather-smoke/weather_daily.csv
head -n 5 build/etl/weather-smoke/weather_features_monthly.csv
```

Expected: CSV headers include `county_fips,date,source,weather_model` for daily data and `county_fips,year,month,source,weather_model` for monthly features.

- [ ] **Step 5: Final commit only if verification required file changes**

If verification required fixes, commit those fixes:

```bash
git add <changed-files>
git commit -m "fix: verify Maryland weather ETL"
```

If no files changed, do not create an empty commit.

---

## Full Backfill Run Plan

After this implementation lands, the production-size Maryland Open-Meteo pull is:

```bash
tickbiterisk etl weather-locations --output-dir build/etl/weather-2000-2024
```

Then run `weather-backfill-open-meteo` once for each county FIPS in `weather_locations.csv`:

```bash
tickbiterisk etl weather-backfill-open-meteo \
  --county-fips 24003 \
  --start-date 2000-01-01 \
  --end-date 2024-12-31 \
  --output-dir build/etl/weather-2000-2024/24003
```

There are 24 jurisdictions. That is 24 Open-Meteo calls for the initial daily archive if each call requests the full 2000-2024 date range. If Open-Meteo rejects a full-range request for payload size, split by year and keep the same output columns.

---

## Self-Review Checklist

- Spec coverage: county weather locations, Open-Meteo URL construction, response parsing, monthly features, anomaly leakage prevention, NOAA token safety, CLI, schema, docs, and final verification are covered.
- Type consistency: `WeatherLocation`, `WeatherDailyObservation`, and `WeatherMonthlyFeature` are introduced before dependent tasks use them.
- Modeling boundary: this plan prepares data and features only; it does not fit Bayesian, random forest, PCA, or ensemble models.
- Network boundary: tests use injected data; only the explicit smoke command performs a live Open-Meteo request.
