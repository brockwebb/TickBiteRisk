from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation
from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.weather_features import WeatherMonthlyFeature, WeatherWeeklyFeature
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

NOAA_STATION_COLUMNS = [
    "county_fips",
    "station_id",
    "name",
    "latitude",
    "longitude",
    "mindate",
    "maxdate",
    "data_coverage",
    "elevation",
    "elevation_unit",
]

NOAA_DAILY_COLUMNS = [
    "county_fips",
    "station_id",
    "date",
    "source",
    "tmax_f",
    "tmin_f",
    "prcp_inches",
    "snow_inches",
    "snwd_inches",
    "source_url_hash",
]

WEATHER_WEEKLY_COLUMNS = [
    "county_fips",
    "iso_year",
    "iso_week",
    "week_start_date",
    "week_end_date",
    "source",
    "weather_model",
    "days_observed",
    "expected_days",
    "week_complete",
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
    "feature_quality_flags",
]

WEATHER_MONTHLY_COLUMNS = [
    "county_fips",
    "year",
    "month",
    "source",
    "weather_model",
    "days_observed",
    "expected_days",
    "month_complete",
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
    "feature_quality_flags",
]


def read_noaa_daily_observations_input(input_path: Path) -> list[NoaaDailyObservation]:
    df = pd.read_csv(input_path, dtype={"county_fips": str, "station_id": str})
    rows: list[NoaaDailyObservation] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            NoaaDailyObservation(
                county_fips=str(record["county_fips"]).zfill(5),
                station_id=str(record["station_id"]),
                date=date.fromisoformat(str(record["date"])),
                source=str(record["source"]),
                tmax_f=_nullable_float(record.get("tmax_f")),
                tmin_f=_nullable_float(record.get("tmin_f")),
                prcp_inches=_nullable_float(record.get("prcp_inches")),
                snow_inches=_nullable_float(record.get("snow_inches")),
                snwd_inches=_nullable_float(record.get("snwd_inches")),
                source_url_hash=str(record["source_url_hash"]),
            )
        )
    return rows


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
    rows: list[WeatherDailyObservation], output_dir: Path, *, append: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_daily.csv"
    records = []
    for row in rows:
        record = asdict(row)
        record["date"] = row.date.isoformat()
        records.append(record)
    _write_output(
        records,
        WEATHER_DAILY_COLUMNS,
        output_path,
        append=append,
        key_columns=["county_fips", "date", "source", "weather_model"],
    )
    return output_path


def write_noaa_stations_output(
    rows: list[NoaaStation], output_dir: Path, *, append: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "noaa_ghcnd_stations.csv"
    records = []
    for row in rows:
        record = asdict(row)
        record["mindate"] = row.mindate.isoformat()
        record["maxdate"] = row.maxdate.isoformat()
        records.append(record)
    _write_output(
        records,
        NOAA_STATION_COLUMNS,
        output_path,
        append=append,
        key_columns=["county_fips", "station_id"],
    )
    return output_path


def write_noaa_daily_observations_output(
    rows: list[NoaaDailyObservation], output_dir: Path, *, append: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "noaa_ghcnd_daily_observations.csv"
    records = []
    for row in rows:
        record = asdict(row)
        record["date"] = row.date.isoformat()
        records.append(record)
    _write_output(
        records,
        NOAA_DAILY_COLUMNS,
        output_path,
        append=append,
        key_columns=["county_fips", "station_id", "date"],
    )
    return output_path


def write_weather_features_monthly_output(
    rows: list[WeatherMonthlyFeature], output_dir: Path, *, append: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_features_monthly.csv"
    _write_output(
        [asdict(row) for row in rows],
        WEATHER_MONTHLY_COLUMNS,
        output_path,
        append=append,
        key_columns=["county_fips", "year", "month", "source", "weather_model"],
    )
    return output_path


def write_weather_features_weekly_output(
    rows: list[WeatherWeeklyFeature], output_dir: Path, *, append: bool = False
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_features_weekly.csv"
    records = []
    for row in rows:
        record = asdict(row)
        record["week_start_date"] = row.week_start_date.isoformat()
        record["week_end_date"] = row.week_end_date.isoformat()
        records.append(record)
    _write_output(
        records,
        WEATHER_WEEKLY_COLUMNS,
        output_path,
        append=append,
        key_columns=["county_fips", "iso_year", "iso_week", "source", "weather_model"],
    )
    return output_path


def _write_output(
    records: list[dict],
    columns: list[str],
    output_path: Path,
    *,
    append: bool,
    key_columns: list[str],
) -> None:
    df = pd.DataFrame(records, columns=columns)
    if append and output_path.exists():
        existing = pd.read_csv(output_path, dtype={"county_fips": str})
        df = pd.concat([existing, df], ignore_index=True)
    if not df.empty:
        df = df.drop_duplicates(subset=key_columns, keep="last")
        df = df.sort_values(key_columns).reset_index(drop=True)
    df.to_csv(output_path, index=False)


def _nullable_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
