from datetime import date
from dataclasses import replace
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.build import write_reconciled_lyme_outputs
from tickbiterisk.etl.census_population import CensusCountyPopulation
from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation
from tickbiterisk.etl.open_meteo import WeatherDailyObservation
from tickbiterisk.etl.population_build import write_county_population_output
from tickbiterisk.etl.weather_build import (
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_features_weekly_output,
    write_weather_locations_output,
)
from tickbiterisk.etl.weather_features import (
    compute_noaa_weekly_weather_features,
    compute_monthly_weather_features,
    compute_weekly_weather_features,
)
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations

EXPECTED_RECONCILED_LYME_COLUMNS = [
    "county_fips",
    "year",
    "confirmed_cases",
    "probable_cases",
    "total_cases",
    "canonical_source_id",
    "source_values_summary",
    "reconciliation_status",
    "data_quality_flags",
]


def test_write_reconciled_lyme_outputs_creates_csv(tmp_path: Path) -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue(
            "cdc_lyme_county_dashboard_2023", "24003", 2022, None, None, 127
        ),
    ]
    output = write_reconciled_lyme_outputs(rows, tmp_path)
    assert output.name == "lyme_county_year_reconciled.csv"
    df = pd.read_csv(output, dtype={"county_fips": str})
    assert list(df.columns) == EXPECTED_RECONCILED_LYME_COLUMNS
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "total_cases"]) == 127
    assert df.loc[0, "reconciliation_status"] == "matched"


def test_write_reconciled_lyme_outputs_creates_empty_csv_with_header(
    tmp_path: Path,
) -> None:
    output = write_reconciled_lyme_outputs([], tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})
    assert df.empty
    assert list(df.columns) == EXPECTED_RECONCILED_LYME_COLUMNS


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


def sample_noaa_station() -> NoaaStation:
    return NoaaStation(
        county_fips="24003",
        station_id="GHCND:USW00093721",
        name="BALTIMORE WASHINGTON INTERNATIONAL AIRPORT, MD US",
        latitude=39.1733,
        longitude=-76.684,
        elevation=47.5,
        elevation_unit="METERS",
        mindate=date(1939, 7, 1),
        maxdate=date(2026, 5, 20),
        data_coverage=0.9999,
    )


def sample_noaa_daily() -> NoaaDailyObservation:
    return NoaaDailyObservation(
        county_fips="24003",
        station_id="GHCND:USW00093721",
        date=date(1992, 5, 1),
        source="noaa_cdo_ghcnd_daily",
        tmax_f=72.0,
        tmin_f=44.0,
        prcp_inches=0.01,
        snow_inches=0.0,
        snwd_inches=None,
        source_url_hash="b" * 64,
    )


def sample_population() -> CensusCountyPopulation:
    return CensusCountyPopulation(
        county_fips="24003",
        county_name="Anne Arundel County",
        year=2023,
        population=590336,
        source_id="census_pep_2023_charv",
        census_dataset="2023/pep/charv",
        vintage=2023,
        source_url_hash="c" * 64,
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


def test_write_noaa_stations_output_creates_csv(tmp_path: Path) -> None:
    output = write_noaa_stations_output([sample_noaa_station()], tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "noaa_ghcnd_stations.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert df.loc[0, "station_id"] == "GHCND:USW00093721"
    assert df.loc[0, "mindate"] == "1939-07-01"


def test_write_noaa_daily_observations_output_appends_by_station_date(
    tmp_path: Path,
) -> None:
    first = sample_noaa_daily()
    second = replace(first, date=date(1992, 5, 2), tmax_f=80.0)

    write_noaa_daily_observations_output([first], tmp_path)
    output = write_noaa_daily_observations_output([second], tmp_path, append=True)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "noaa_ghcnd_daily_observations.csv"
    assert list(df["date"]) == ["1992-05-01", "1992-05-02"]
    assert list(df["tmax_f"]) == [72.0, 80.0]


def test_write_weather_daily_output_creates_csv(tmp_path: Path) -> None:
    output = write_weather_daily_output([sample_weather_daily()], tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "weather_daily.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert df.loc[0, "date"] == "2020-05-01"
    assert df.loc[0, "source"] == "open_meteo_archive"
    assert float(df.loc[0, "temp_mean_f"]) == 55.0


def test_write_weather_daily_output_appends_without_losing_prior_counties(
    tmp_path: Path,
) -> None:
    first = sample_weather_daily()
    second = replace(first, county_fips="24005", temp_mean_f=50.0)

    write_weather_daily_output([first], tmp_path)
    write_weather_daily_output([second], tmp_path, append=True)

    df = pd.read_csv(tmp_path / "weather_daily.csv", dtype={"county_fips": str})
    assert list(df["county_fips"]) == ["24003", "24005"]
    assert list(df["temp_mean_f"]) == [55.0, 50.0]


def test_write_county_population_output_creates_csv(tmp_path: Path) -> None:
    output = write_county_population_output([sample_population()], tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "county_population_year.csv"
    assert list(df.columns) == [
        "county_fips",
        "county_name",
        "year",
        "population",
        "source_id",
        "census_dataset",
        "vintage",
        "source_url_hash",
    ]
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "population"]) == 590336


def test_write_county_population_output_appends_and_dedupes_by_county_year(
    tmp_path: Path,
) -> None:
    first = sample_population()
    replacement = replace(first, population=590337)

    write_county_population_output([first], tmp_path)
    write_county_population_output([replacement], tmp_path, append=True)

    df = pd.read_csv(tmp_path / "county_population_year.csv", dtype={"county_fips": str})
    assert len(df) == 1
    assert int(df.loc[0, "population"]) == 590337


def test_write_weather_features_weekly_output_creates_csv(tmp_path: Path) -> None:
    features = compute_weekly_weather_features([sample_weather_daily()])
    output = write_weather_features_weekly_output(features, tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "weather_features_weekly.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "iso_year"]) == 2020
    assert int(df.loc[0, "iso_week"]) == 18
    assert df.loc[0, "week_start_date"] == "2020-04-27"
    assert df.loc[0, "week_end_date"] == "2020-05-03"
    assert int(df.loc[0, "days_observed"]) == 1
    assert bool(df.loc[0, "week_complete"]) is False
    assert "feature_quality_flags" in df.columns


def test_write_weather_features_weekly_output_appends_without_losing_prior_counties(
    tmp_path: Path,
) -> None:
    first = compute_weekly_weather_features([sample_weather_daily()])[0]
    second = replace(first, county_fips="24005", temp_mean_f=50.0)

    write_weather_features_weekly_output([first], tmp_path)
    write_weather_features_weekly_output([second], tmp_path, append=True)

    df = pd.read_csv(
        tmp_path / "weather_features_weekly.csv", dtype={"county_fips": str}
    )
    assert list(df["county_fips"]) == ["24003", "24005"]
    assert list(df["temp_mean_f"]) == [55.0, 50.0]


def test_write_noaa_weather_features_weekly_output_preserves_nullable_fields(
    tmp_path: Path,
) -> None:
    features = compute_noaa_weekly_weather_features([sample_noaa_daily()])

    output = write_weather_features_weekly_output(features, tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})
    assert df.loc[0, "source"] == "noaa_cdo_ghcnd_daily"
    assert pd.isna(df.loc[0, "humidity_mean_pct"])
    assert pd.isna(df.loc[0, "rain_total_mm"])
    assert "no_humidity" in df.loc[0, "feature_quality_flags"]


def test_write_weather_features_monthly_output_creates_csv(tmp_path: Path) -> None:
    features = compute_monthly_weather_features([sample_weather_daily()])
    output = write_weather_features_monthly_output(features, tmp_path)

    df = pd.read_csv(output, dtype={"county_fips": str})

    assert output.name == "weather_features_monthly.csv"
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "year"]) == 2020
    assert int(df.loc[0, "month"]) == 5
    assert int(df.loc[0, "days_observed"]) == 1
    assert bool(df.loc[0, "month_complete"]) is False


def test_write_weather_features_monthly_output_appends_without_losing_prior_counties(
    tmp_path: Path,
) -> None:
    first = compute_monthly_weather_features([sample_weather_daily()])[0]
    second = replace(first, county_fips="24005", temp_mean_f=50.0)

    write_weather_features_monthly_output([first], tmp_path)
    write_weather_features_monthly_output([second], tmp_path, append=True)

    df = pd.read_csv(
        tmp_path / "weather_features_monthly.csv", dtype={"county_fips": str}
    )
    assert list(df["county_fips"]) == ["24003", "24005"]
    assert list(df["temp_mean_f"]) == [55.0, 50.0]
