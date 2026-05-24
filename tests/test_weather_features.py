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
    assert may.days_observed == 3
    assert may.expected_days == 31
    assert may.month_complete is False
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


def test_complete_month_is_marked_complete() -> None:
    rows = [obs(date(2020, 2, day)) for day in range(1, 30)]

    features = compute_monthly_weather_features(rows)

    assert features[0].days_observed == 29
    assert features[0].expected_days == 29
    assert features[0].month_complete is True


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
