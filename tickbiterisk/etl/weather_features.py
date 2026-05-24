from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import groupby
from statistics import mean

from tickbiterisk.etl.open_meteo import WeatherDailyObservation


@dataclass(frozen=True)
class WeatherWeeklyFeature:
    county_fips: str
    iso_year: int
    iso_week: int
    week_start_date: date
    week_end_date: date
    source: str
    weather_model: str
    days_observed: int
    expected_days: int
    week_complete: bool
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
    soil_moisture_mean: float | None
    soil_temp_above_40f_days: int
    hot_dry_stress_days: int
    evapotranspiration_total_mm: float
    temp_mean_f: float
    precip_mean_mm: float
    humidity_mean_pct: float
    temp_anomaly_vs_10yr: float | None = None
    precip_anomaly_vs_10yr: float | None = None
    humidity_anomaly_vs_10yr: float | None = None


@dataclass(frozen=True)
class WeatherMonthlyFeature:
    county_fips: str
    year: int
    month: int
    source: str
    weather_model: str
    days_observed: int
    expected_days: int
    month_complete: bool
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
    soil_moisture_mean: float | None
    soil_temp_above_40f_days: int
    hot_dry_stress_days: int
    evapotranspiration_total_mm: float
    temp_mean_f: float
    precip_mean_mm: float
    humidity_mean_pct: float
    temp_anomaly_vs_10yr: float | None = None
    precip_anomaly_vs_10yr: float | None = None
    humidity_anomaly_vs_10yr: float | None = None


def compute_weekly_weather_features(
    observations: list[WeatherDailyObservation],
) -> list[WeatherWeeklyFeature]:
    sorted_rows = sorted(
        observations,
        key=lambda row: (row.county_fips, row.source, row.weather_model, row.date),
    )
    features: list[WeatherWeeklyFeature] = []

    def key(row: WeatherDailyObservation) -> tuple[str, str, str, int, int]:
        iso_year, iso_week, _weekday = row.date.isocalendar()
        return (
            row.county_fips,
            row.source,
            row.weather_model,
            iso_year,
            iso_week,
        )

    for (county_fips, source, weather_model, iso_year, iso_week), group in groupby(
        sorted_rows, key=key
    ):
        rows = list(group)
        days_observed = len({row.date for row in rows})
        week_start_date = date.fromisocalendar(iso_year, iso_week, 1)
        metrics = _weather_feature_metrics(rows)
        features.append(
            WeatherWeeklyFeature(
                county_fips=county_fips,
                iso_year=iso_year,
                iso_week=iso_week,
                week_start_date=week_start_date,
                week_end_date=week_start_date + timedelta(days=6),
                source=source,
                weather_model=weather_model,
                days_observed=days_observed,
                expected_days=7,
                week_complete=days_observed == 7,
                **metrics,
            )
        )
    return features


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
        days_observed = len({row.date for row in rows})
        expected_days = monthrange(year, month)[1]
        metrics = _weather_feature_metrics(rows)
        features.append(
            WeatherMonthlyFeature(
                county_fips=county_fips,
                year=year,
                month=month,
                source=source,
                weather_model=weather_model,
                days_observed=days_observed,
                expected_days=expected_days,
                month_complete=days_observed == expected_days,
                **metrics,
            )
        )
    return features


def add_trailing_weekly_anomalies(
    features: list[WeatherWeeklyFeature],
    *,
    baseline_years: int = 10,
) -> list[WeatherWeeklyFeature]:
    sorted_features = sorted(
        features,
        key=lambda row: (
            row.county_fips,
            row.source,
            row.weather_model,
            row.iso_week,
            row.iso_year,
        ),
    )
    output: list[WeatherWeeklyFeature] = []

    def key(row: WeatherWeeklyFeature) -> tuple[str, str, str, int]:
        return (row.county_fips, row.source, row.weather_model, row.iso_week)

    for _, group in groupby(sorted_features, key=key):
        history: list[WeatherWeeklyFeature] = []
        for row in group:
            trailing = [
                prior
                for prior in history
                if row.iso_year - baseline_years <= prior.iso_year < row.iso_year
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

    return sorted(output, key=lambda row: (row.county_fips, row.iso_year, row.iso_week))


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


def _weather_feature_metrics(rows: list[WeatherDailyObservation]) -> dict[str, float | int | None]:
    return {
        "days_above_40f": sum(row.temp_max_f >= 40 for row in rows),
        "days_50_65f": sum(50 <= row.temp_mean_f <= 65 for row in rows),
        "days_70_85f": sum(70 <= row.temp_mean_f <= 85 for row in rows),
        "degree_days_above_40f": round(
            sum(max(row.temp_mean_f - 40, 0) for row in rows), 6
        ),
        "freeze_thaw_days": sum(
            row.temp_min_f < 32 and row.temp_max_f > 32 for row in rows
        ),
        "precip_total_mm": round(sum(row.precipitation_mm for row in rows), 6),
        "rain_total_mm": round(sum(row.rain_mm for row in rows), 6),
        "snowfall_total_mm": round(sum(row.snowfall_mm for row in rows), 6),
        "precip_days": sum(row.precipitation_mm > 0 for row in rows),
        "dry_spell_max_days": _longest_dry_spell(rows),
        "humidity_days_above_85pct": sum(row.humidity_mean_pct >= 85 for row in rows),
        "soil_moisture_mean": _nullable_mean(
            [row.soil_moisture_0_7cm for row in rows]
        ),
        "soil_temp_above_40f_days": sum(row.soil_temp_0_7cm_f >= 40 for row in rows),
        "hot_dry_stress_days": sum(
            row.temp_max_f >= 90 and row.humidity_mean_pct < 55 for row in rows
        ),
        "evapotranspiration_total_mm": round(
            sum(row.evapotranspiration_mm for row in rows), 6
        ),
        "temp_mean_f": round(mean(row.temp_mean_f for row in rows), 6),
        "precip_mean_mm": round(mean(row.precipitation_mm for row in rows), 6),
        "humidity_mean_pct": round(mean(row.humidity_mean_pct for row in rows), 6),
    }


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


def _nullable_mean(values: list[float | None]) -> float | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return round(mean(present_values), 6)
