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
