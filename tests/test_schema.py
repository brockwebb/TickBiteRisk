from pathlib import Path


def test_schema_defines_core_tables() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    for table in [
        "source_files",
        "md_jurisdictions",
        "lyme_county_year_source_values",
        "lyme_county_year_reconciled",
        "tick_vector_status",
        "tick_pathogen_status",
        "lone_star_status",
        "county_reference",
        "maryland_dnr_deer_harvest",
        "county_population_year",
        "weather_locations",
        "noaa_ghcnd_stations",
        "noaa_ghcnd_daily_observations",
        "weather_daily",
        "weather_features_weekly",
        "weather_features_monthly",
        "seasonality_observations",
        "seasonality_baseline",
        "county_week_seasonal_risk_baseline",
        "risk_score_scale",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema


def test_reconciled_data_quality_flags_allows_null_copy_values() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "data_quality_flags text DEFAULT ''" in schema
    assert "data_quality_flags text NOT NULL" not in schema


def test_tick_vector_status_preserves_parser_source_columns() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "ixodes_scapularis_source text" in schema
    assert "ixodes_pacificus_source text" in schema


def test_weather_daily_defines_source_provenance_and_primary_key() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "PRIMARY KEY (county_fips, date, source, weather_model)" in schema
    assert "source_url_hash text NOT NULL" in schema


def test_county_population_year_defines_incidence_denominator_key() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS county_population_year" in schema
    assert "population integer NOT NULL CHECK (population > 0)" in schema
    assert "source_url_hash text NOT NULL" in schema
    assert "PRIMARY KEY (county_fips, year)" in schema


def test_county_reference_defines_area_and_internal_point_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS county_reference" in schema
    assert "aland_sqmi double precision NOT NULL CHECK (aland_sqmi > 0)" in schema
    assert "awater_sqmi double precision NOT NULL CHECK (awater_sqmi >= 0)" in schema
    assert "intptlat double precision NOT NULL" in schema
    assert "intptlon double precision NOT NULL" in schema


def test_maryland_dnr_deer_harvest_defines_density_proxy_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS maryland_dnr_deer_harvest" in schema
    assert "season_start_year integer NOT NULL" in schema
    assert "species text NOT NULL" in schema
    assert "harvest_per_sqmi double precision" in schema
    assert "is_derived_total boolean NOT NULL" in schema
    assert (
        "PRIMARY KEY (county_fips, season_start_year, species, source_id)"
        in schema
    )


def test_noaa_ghcnd_daily_observations_defines_raw_station_primary_key() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS noaa_ghcnd_stations" in schema
    assert "PRIMARY KEY (county_fips, station_id)" in schema
    assert "CREATE TABLE IF NOT EXISTS noaa_ghcnd_daily_observations" in schema
    assert "station_id text NOT NULL" in schema
    assert "PRIMARY KEY (county_fips, station_id, date)" in schema


def test_weather_daily_includes_soil_moisture_field() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "soil_moisture_0_7cm double precision" in schema


def test_weather_monthly_features_include_anomaly_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "temp_anomaly_vs_10yr double precision" in schema
    assert "precip_anomaly_vs_10yr double precision" in schema
    assert "humidity_anomaly_vs_10yr double precision" in schema


def test_weather_weekly_features_use_iso_week_and_completeness_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS weather_features_weekly" in schema
    assert "iso_year integer NOT NULL" in schema
    assert "iso_week integer NOT NULL CHECK (iso_week BETWEEN 1 AND 53)" in schema
    assert "week_start_date date NOT NULL" in schema
    assert "week_end_date date NOT NULL" in schema
    assert "week_complete boolean NOT NULL" in schema
    assert "feature_quality_flags text DEFAULT ''" in schema
    assert "PRIMARY KEY (county_fips, iso_year, iso_week, source, weather_model)" in schema


def test_weather_feature_tables_allow_noaa_unavailable_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    feature_schema = schema.split("CREATE TABLE IF NOT EXISTS weather_features_weekly", maxsplit=1)[
        1
    ]

    assert "rain_total_mm double precision NOT NULL" not in feature_schema
    assert "humidity_days_above_85pct integer NOT NULL" not in feature_schema
    assert "soil_temp_above_40f_days integer NOT NULL" not in feature_schema
    assert "hot_dry_stress_days integer NOT NULL" not in feature_schema
    assert "evapotranspiration_total_mm double precision NOT NULL" not in feature_schema
    assert "humidity_mean_pct double precision NOT NULL" not in feature_schema


def test_weather_monthly_features_include_completeness_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "days_observed integer NOT NULL" in schema
    assert "expected_days integer NOT NULL" in schema
    assert "month_complete boolean NOT NULL" in schema


def test_seasonality_tables_define_period_keys_and_share_bands() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS seasonality_observations" in schema
    assert "seasonal_share double precision NOT NULL" in schema
    assert "PRIMARY KEY (source_id, disease, grain, year, period)" in schema
    assert "CREATE TABLE IF NOT EXISTS seasonality_baseline" in schema
    assert "lower_80_share double precision NOT NULL" in schema
    assert "upper_95_share double precision NOT NULL" in schema
    assert "feature_quality_flags text DEFAULT ''" in schema
    assert "PRIMARY KEY (source_id, disease, grain, period)" in schema


def test_county_week_risk_tables_define_score_bounds_and_keys() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS county_week_seasonal_risk_baseline" in schema
    assert "mmwr_week integer NOT NULL CHECK (mmwr_week BETWEEN 1 AND 53)" in schema
    assert "risk_score integer NOT NULL CHECK (risk_score BETWEEN 1 AND 10)" in schema
    assert "risk_category text NOT NULL" in schema
    assert "score_denominator double precision NOT NULL" in schema
    assert "seasonality_source_id text NOT NULL" in schema
    assert (
        "seasonality_source_id,\n"
        "        benchmark_quantile,\n"
        "        headroom_multiplier,\n"
        "        source_prediction_sha256,\n"
        "        source_seasonality_sha256"
    ) in schema
    assert "CREATE TABLE IF NOT EXISTS risk_score_scale" in schema
    assert "benchmark_quantile double precision NOT NULL" in schema
    assert "headroom_multiplier double precision NOT NULL" in schema
    assert (
        "PRIMARY KEY (\n"
        "        model_name,\n"
        "        grain,\n"
        "        seasonality_source_id,\n"
        "        source_prediction_sha256,\n"
        "        source_seasonality_sha256,\n"
        "        benchmark_quantile,\n"
        "        headroom_multiplier\n"
        "    )"
    ) in schema
