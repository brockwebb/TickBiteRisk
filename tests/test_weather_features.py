from datetime import date

from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.noaa import NoaaDailyObservation
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    add_trailing_weekly_anomalies,
    compute_noaa_monthly_weather_features,
    compute_noaa_weekly_weather_features,
    compute_monthly_weather_features,
    compute_weekly_weather_features,
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


def noaa_obs(day: date, **overrides: float | None) -> NoaaDailyObservation:
    values = {
        "tmax_f": 62.0,
        "tmin_f": 42.0,
        "prcp_inches": 0.0,
        "snow_inches": 0.0,
        "snwd_inches": None,
    }
    values.update(overrides)
    return NoaaDailyObservation(
        county_fips="24003",
        station_id="GHCND:USW00093721",
        date=day,
        source="noaa_cdo_ghcnd_daily",
        source_url_hash="b" * 64,
        **values,
    )


def test_compute_noaa_weekly_weather_features_preserves_missing_derived_fields() -> None:
    rows = [
        noaa_obs(
            date(2020, 5, 4),
            tmax_f=70.0,
            tmin_f=50.0,
            prcp_inches=0.10,
            snow_inches=0.0,
        ),
        noaa_obs(
            date(2020, 5, 5),
            tmax_f=92.0,
            tmin_f=72.0,
            prcp_inches=0.0,
            snow_inches=0.0,
        ),
        noaa_obs(
            date(2020, 5, 6),
            tmax_f=None,
            tmin_f=45.0,
            prcp_inches=None,
            snow_inches=None,
        ),
    ]

    features = compute_noaa_weekly_weather_features(rows)

    assert len(features) == 1
    week = features[0]
    assert week.iso_year == 2020
    assert week.iso_week == 19
    assert week.days_observed == 3
    assert week.expected_days == 7
    assert week.week_complete is False
    assert week.days_above_40f == 2
    assert week.days_50_65f == 1
    assert week.days_70_85f == 1
    assert week.degree_days_above_40f == 62.0
    assert week.freeze_thaw_days == 0
    assert week.precip_total_mm == 2.54
    assert week.rain_total_mm is None
    assert week.snowfall_total_mm == 0.0
    assert week.precip_days == 1
    assert week.dry_spell_max_days == 1
    assert week.humidity_days_above_85pct is None
    assert week.humidity_mean_pct is None
    assert week.soil_moisture_mean is None
    assert week.soil_temp_above_40f_days is None
    assert week.hot_dry_stress_days is None
    assert week.evapotranspiration_total_mm is None
    assert week.temp_mean_f == 71.0
    assert week.precip_mean_mm == 1.27
    assert week.feature_quality_flags == (
        "no_humidity,no_soil_data,no_evapotranspiration,no_rain_split,"
        "partial_temp,partial_precip,partial_snow"
    )


def test_compute_noaa_monthly_weather_features_converts_inches_to_mm() -> None:
    rows = [
        noaa_obs(date(2020, 5, 1), prcp_inches=1.0, snow_inches=0.5),
        noaa_obs(date(2020, 5, 2), prcp_inches=0.0, snow_inches=0.0),
    ]

    features = compute_noaa_monthly_weather_features(rows)

    assert len(features) == 1
    may = features[0]
    assert may.year == 2020
    assert may.month == 5
    assert may.precip_total_mm == 25.4
    assert may.snowfall_total_mm == 12.7
    assert may.precip_mean_mm == 12.7
    assert may.feature_quality_flags == (
        "no_humidity,no_soil_data,no_evapotranspiration,no_rain_split"
    )


def test_noaa_trailing_anomalies_skip_unavailable_humidity() -> None:
    features = []
    for year, tmax, prcp in [(2010, 60.0, 0.1), (2011, 62.0, 0.2), (2020, 80.0, 1.0)]:
        features.extend(
            compute_noaa_weekly_weather_features(
                [
                    noaa_obs(
                        date.fromisocalendar(year, 20, 1),
                        tmax_f=tmax,
                        tmin_f=40.0,
                        prcp_inches=prcp,
                    )
                ]
            )
        )

    with_anomalies = add_trailing_weekly_anomalies(features, baseline_years=10)
    year_2020 = next(feature for feature in with_anomalies if feature.iso_year == 2020)

    assert year_2020.temp_anomaly_vs_10yr == 9.5
    assert year_2020.precip_anomaly_vs_10yr == 21.59
    assert year_2020.humidity_anomaly_vs_10yr is None


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


def test_compute_weekly_weather_features_uses_iso_week() -> None:
    rows = [
        obs(
            date(2020, 12, 28),
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
            date(2021, 1, 3),
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

    features = compute_weekly_weather_features(rows)

    assert len(features) == 1
    week = features[0]
    assert week.iso_year == 2020
    assert week.iso_week == 53
    assert week.week_start_date == date(2020, 12, 28)
    assert week.week_end_date == date(2021, 1, 3)
    assert week.days_observed == 2
    assert week.expected_days == 7
    assert week.week_complete is False
    assert week.days_above_40f == 2
    assert week.days_70_85f == 1
    assert week.degree_days_above_40f == 40.0
    assert week.freeze_thaw_days == 1
    assert week.precip_total_mm == 2.0
    assert week.precip_days == 1
    assert week.dry_spell_max_days == 1
    assert week.humidity_days_above_85pct == 1
    assert week.soil_moisture_mean == 0.225
    assert week.soil_temp_above_40f_days == 2
    assert week.hot_dry_stress_days == 1
    assert week.evapotranspiration_total_mm == 2.5


def test_complete_week_is_marked_complete() -> None:
    rows = [obs(date.fromisocalendar(2020, 20, weekday)) for weekday in range(1, 8)]

    features = compute_weekly_weather_features(rows)

    assert features[0].days_observed == 7
    assert features[0].expected_days == 7
    assert features[0].week_complete is True


def test_weekly_dry_spell_is_computed_within_each_iso_week() -> None:
    rows = [
        obs(date(2020, 5, 3), precipitation_mm=0.0),
        obs(date(2020, 5, 4), precipitation_mm=0.0),
        obs(date(2020, 5, 5), precipitation_mm=1.0),
    ]

    features = compute_weekly_weather_features(rows)
    by_week = {feature.iso_week: feature for feature in features}

    assert by_week[18].dry_spell_max_days == 1
    assert by_week[19].dry_spell_max_days == 1


def test_trailing_weekly_anomalies_do_not_use_current_or_future_years() -> None:
    features = []
    for year, temp, precip, humidity in [
        (2010, 50.0, 10.0, 70.0),
        (2011, 52.0, 12.0, 72.0),
        (2012, 54.0, 14.0, 74.0),
        (2020, 70.0, 25.0, 90.0),
    ]:
        week_rows = [
            obs(
                date.fromisocalendar(year, 20, 1),
                temp_mean_f=temp,
                precipitation_mm=precip,
                humidity_mean_pct=humidity,
            )
        ]
        features.extend(compute_weekly_weather_features(week_rows))

    with_anomalies = add_trailing_weekly_anomalies(features, baseline_years=10)
    year_2020 = next(feature for feature in with_anomalies if feature.iso_year == 2020)

    assert year_2020.temp_anomaly_vs_10yr == 18.0
    assert year_2020.precip_anomaly_vs_10yr == 13.0
    assert year_2020.humidity_anomaly_vs_10yr == 18.0
