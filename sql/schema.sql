CREATE TABLE IF NOT EXISTS source_files (
    source_id text PRIMARY KEY,
    source_name text NOT NULL,
    source_location text NOT NULL,
    file_format text NOT NULL,
    geography text NOT NULL,
    time_coverage text NOT NULL,
    role text NOT NULL,
    status text NOT NULL,
    redistribution text NOT NULL,
    sha256 text,
    notes text,
    ingested_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS md_jurisdictions (
    county_fips char(5) PRIMARY KEY,
    state_fips char(2) NOT NULL DEFAULT '24',
    state char(2) NOT NULL DEFAULT 'MD',
    county_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS lyme_county_year_source_values (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    confirmed_cases integer,
    probable_cases integer,
    total_cases integer NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips, year)
);

CREATE TABLE IF NOT EXISTS lyme_county_year_reconciled (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    confirmed_cases integer,
    probable_cases integer,
    total_cases integer NOT NULL,
    canonical_source_id text NOT NULL,
    source_values_summary text NOT NULL,
    reconciliation_status text NOT NULL,
    data_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year)
);

CREATE TABLE IF NOT EXISTS midatlantic_lyme_county_year (
    state_fips char(2) NOT NULL,
    state_abbr char(2) NOT NULL,
    state_name text NOT NULL,
    county_fips char(5) NOT NULL,
    county_name text NOT NULL,
    year integer NOT NULL,
    total_cases integer NOT NULL CHECK (total_cases >= 0),
    source_id text NOT NULL,
    feature_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year, source_id)
);

CREATE TABLE IF NOT EXISTS tick_vector_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    ixodes_scapularis_status text,
    ixodes_scapularis_source text,
    ixodes_pacificus_status text,
    ixodes_pacificus_source text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);

CREATE TABLE IF NOT EXISTS tick_pathogen_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    borrelia_burgdorferi_status text,
    borrelia_miyamotoi_status text,
    anaplasma_phagocytophilum_status text,
    babesia_microti_status text,
    powassan_virus_status text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);

CREATE TABLE IF NOT EXISTS lone_star_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    amblyomma_americanum_status text,
    status_source text,
    source_comments text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);

CREATE TABLE IF NOT EXISTS county_reference (
    county_fips char(5) PRIMARY KEY REFERENCES md_jurisdictions(county_fips),
    state_fips char(2) NOT NULL DEFAULT '24',
    state char(2) NOT NULL DEFAULT 'MD',
    county_name text NOT NULL,
    aland_sqmi double precision NOT NULL CHECK (aland_sqmi > 0),
    awater_sqmi double precision NOT NULL CHECK (awater_sqmi >= 0),
    intptlat double precision NOT NULL,
    intptlon double precision NOT NULL,
    geography_source text NOT NULL,
    source_url_hash text NOT NULL,
    ingested_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS maryland_dnr_deer_harvest (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    county_name text NOT NULL,
    season_start_year integer NOT NULL,
    season_label text NOT NULL,
    species text NOT NULL,
    antlered_harvest integer NOT NULL CHECK (antlered_harvest >= 0),
    antlerless_harvest integer NOT NULL CHECK (antlerless_harvest >= 0),
    total_harvest integer NOT NULL CHECK (total_harvest >= 0),
    land_area_sqmi double precision,
    harvest_per_sqmi double precision,
    is_derived_total boolean NOT NULL,
    source_id text NOT NULL,
    source_url_hash text NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, season_start_year, species, source_id)
);

CREATE TABLE IF NOT EXISTS county_population_year (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    county_name text NOT NULL,
    year integer NOT NULL,
    population integer NOT NULL CHECK (population > 0),
    source_id text NOT NULL,
    census_dataset text NOT NULL,
    vintage integer NOT NULL,
    source_url_hash text NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year)
);

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

CREATE TABLE IF NOT EXISTS noaa_ghcnd_stations (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    station_id text NOT NULL,
    name text NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    mindate date NOT NULL,
    maxdate date NOT NULL,
    data_coverage double precision NOT NULL,
    elevation double precision,
    elevation_unit text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, station_id)
);

CREATE TABLE IF NOT EXISTS noaa_ghcnd_daily_observations (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    station_id text NOT NULL,
    date date NOT NULL,
    source text NOT NULL,
    tmax_f double precision,
    tmin_f double precision,
    prcp_inches double precision,
    snow_inches double precision,
    snwd_inches double precision,
    source_url_hash text NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, station_id, date)
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

CREATE TABLE IF NOT EXISTS weather_features_weekly (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    iso_year integer NOT NULL,
    iso_week integer NOT NULL CHECK (iso_week BETWEEN 1 AND 53),
    week_start_date date NOT NULL,
    week_end_date date NOT NULL,
    source text NOT NULL,
    weather_model text NOT NULL,
    days_observed integer NOT NULL,
    expected_days integer NOT NULL,
    week_complete boolean NOT NULL,
    days_above_40f integer NOT NULL,
    days_50_65f integer NOT NULL,
    days_70_85f integer NOT NULL,
    degree_days_above_40f double precision NOT NULL,
    freeze_thaw_days integer NOT NULL,
    precip_total_mm double precision NOT NULL,
    rain_total_mm double precision,
    snowfall_total_mm double precision,
    precip_days integer,
    dry_spell_max_days integer,
    humidity_days_above_85pct integer,
    soil_moisture_mean double precision,
    soil_temp_above_40f_days integer,
    hot_dry_stress_days integer,
    evapotranspiration_total_mm double precision,
    temp_mean_f double precision,
    precip_mean_mm double precision,
    humidity_mean_pct double precision,
    temp_anomaly_vs_10yr double precision,
    precip_anomaly_vs_10yr double precision,
    humidity_anomaly_vs_10yr double precision,
    feature_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, iso_year, iso_week, source, weather_model)
);

CREATE TABLE IF NOT EXISTS weather_features_monthly (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    month integer NOT NULL CHECK (month BETWEEN 1 AND 12),
    source text NOT NULL,
    weather_model text NOT NULL,
    days_observed integer NOT NULL,
    expected_days integer NOT NULL,
    month_complete boolean NOT NULL,
    days_above_40f integer NOT NULL,
    days_50_65f integer NOT NULL,
    days_70_85f integer NOT NULL,
    degree_days_above_40f double precision NOT NULL,
    freeze_thaw_days integer NOT NULL,
    precip_total_mm double precision NOT NULL,
    rain_total_mm double precision,
    snowfall_total_mm double precision,
    precip_days integer,
    dry_spell_max_days integer,
    humidity_days_above_85pct integer,
    soil_moisture_mean double precision,
    soil_temp_above_40f_days integer,
    hot_dry_stress_days integer,
    evapotranspiration_total_mm double precision,
    temp_mean_f double precision,
    precip_mean_mm double precision,
    humidity_mean_pct double precision,
    temp_anomaly_vs_10yr double precision,
    precip_anomaly_vs_10yr double precision,
    humidity_anomaly_vs_10yr double precision,
    feature_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year, month, source, weather_model)
);

CREATE TABLE IF NOT EXISTS seasonality_observations (
    source_id text NOT NULL,
    disease text NOT NULL,
    grain text NOT NULL CHECK (grain IN ('month', 'mmwr_week')),
    year integer NOT NULL CHECK (year >= 0),
    period integer NOT NULL CHECK (period >= 1),
    period_label text NOT NULL,
    cases integer NOT NULL CHECK (cases >= 0),
    annual_cases integer NOT NULL CHECK (annual_cases >= 0),
    seasonal_share double precision NOT NULL CHECK (
        seasonal_share >= 0 AND seasonal_share <= 1
    ),
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, disease, grain, year, period)
);

CREATE TABLE IF NOT EXISTS seasonality_baseline (
    source_id text NOT NULL,
    disease text NOT NULL,
    grain text NOT NULL CHECK (grain IN ('month', 'mmwr_week')),
    period integer NOT NULL CHECK (period >= 1),
    period_label text NOT NULL,
    years_observed integer NOT NULL CHECK (years_observed > 0),
    mean_cases double precision NOT NULL CHECK (mean_cases >= 0),
    median_cases double precision NOT NULL CHECK (median_cases >= 0),
    min_cases integer NOT NULL CHECK (min_cases >= 0),
    max_cases integer NOT NULL CHECK (max_cases >= 0),
    mean_share double precision NOT NULL CHECK (mean_share >= 0 AND mean_share <= 1),
    median_share double precision NOT NULL CHECK (
        median_share >= 0 AND median_share <= 1
    ),
    lower_80_share double precision NOT NULL CHECK (
        lower_80_share >= 0 AND lower_80_share <= 1
    ),
    upper_80_share double precision NOT NULL CHECK (
        upper_80_share >= 0 AND upper_80_share <= 1
    ),
    lower_95_share double precision NOT NULL CHECK (
        lower_95_share >= 0 AND lower_95_share <= 1
    ),
    upper_95_share double precision NOT NULL CHECK (
        upper_95_share >= 0 AND upper_95_share <= 1
    ),
    peak_rank integer NOT NULL CHECK (peak_rank >= 1),
    cumulative_mean_share double precision NOT NULL CHECK (
        cumulative_mean_share >= 0 AND cumulative_mean_share <= 1
    ),
    feature_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, disease, grain, period)
);

CREATE TABLE IF NOT EXISTS county_week_seasonal_risk_baseline (
    source_prediction_run_id text NOT NULL,
    source_prediction_sha256 text NOT NULL,
    source_seasonality_sha256 text NOT NULL,
    model_name text NOT NULL,
    model_family text NOT NULL,
    target_definition text NOT NULL,
    feature_set text NOT NULL,
    evaluation_mode text NOT NULL,
    weather_mode text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    county_name text NOT NULL,
    year integer NOT NULL,
    mmwr_week integer NOT NULL CHECK (mmwr_week BETWEEN 1 AND 53),
    period_label text NOT NULL,
    predicted_annual_incidence_per_100k double precision NOT NULL CHECK (
        predicted_annual_incidence_per_100k >= 0
    ),
    predicted_annual_cases double precision NOT NULL CHECK (
        predicted_annual_cases >= 0
    ),
    seasonal_mean_share double precision NOT NULL CHECK (
        seasonal_mean_share >= 0 AND seasonal_mean_share <= 1
    ),
    seasonal_lower_80_share double precision NOT NULL CHECK (
        seasonal_lower_80_share >= 0 AND seasonal_lower_80_share <= 1
    ),
    seasonal_upper_80_share double precision NOT NULL CHECK (
        seasonal_upper_80_share >= 0 AND seasonal_upper_80_share <= 1
    ),
    seasonal_lower_95_share double precision NOT NULL CHECK (
        seasonal_lower_95_share >= 0 AND seasonal_lower_95_share <= 1
    ),
    seasonal_upper_95_share double precision NOT NULL CHECK (
        seasonal_upper_95_share >= 0 AND seasonal_upper_95_share <= 1
    ),
    predicted_weekly_incidence_per_100k double precision NOT NULL CHECK (
        predicted_weekly_incidence_per_100k >= 0
    ),
    lower_80_weekly_incidence_per_100k double precision NOT NULL CHECK (
        lower_80_weekly_incidence_per_100k >= 0
    ),
    upper_80_weekly_incidence_per_100k double precision NOT NULL CHECK (
        upper_80_weekly_incidence_per_100k >= 0
    ),
    lower_95_weekly_incidence_per_100k double precision NOT NULL CHECK (
        lower_95_weekly_incidence_per_100k >= 0
    ),
    upper_95_weekly_incidence_per_100k double precision NOT NULL CHECK (
        upper_95_weekly_incidence_per_100k >= 0
    ),
    predicted_weekly_cases double precision NOT NULL CHECK (
        predicted_weekly_cases >= 0
    ),
    benchmark_quantile double precision NOT NULL CHECK (
        benchmark_quantile > 0 AND benchmark_quantile <= 1
    ),
    headroom_multiplier double precision NOT NULL CHECK (headroom_multiplier > 0),
    score_denominator double precision NOT NULL CHECK (score_denominator >= 0),
    risk_score_raw double precision NOT NULL CHECK (risk_score_raw >= 0),
    risk_score integer NOT NULL CHECK (risk_score BETWEEN 1 AND 10),
    risk_category text NOT NULL,
    seasonality_source_id text NOT NULL,
    model_feature_quality_flags text DEFAULT '',
    seasonality_feature_quality_flags text DEFAULT '',
    feature_quality_flags text DEFAULT '',
    backtest_assumption_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (
        county_fips,
        year,
        mmwr_week,
        source_prediction_run_id,
        model_name,
        seasonality_source_id,
        benchmark_quantile,
        headroom_multiplier,
        source_prediction_sha256,
        source_seasonality_sha256
    )
);

CREATE TABLE IF NOT EXISTS risk_score_scale (
    model_name text NOT NULL,
    grain text NOT NULL,
    target_definition text NOT NULL,
    seasonality_source_id text NOT NULL,
    benchmark_quantile double precision NOT NULL CHECK (
        benchmark_quantile > 0 AND benchmark_quantile <= 1
    ),
    headroom_multiplier double precision NOT NULL CHECK (headroom_multiplier > 0),
    benchmark_weekly_incidence_per_100k double precision NOT NULL CHECK (
        benchmark_weekly_incidence_per_100k >= 0
    ),
    score_denominator double precision NOT NULL CHECK (score_denominator >= 0),
    n_score_rows integer NOT NULL CHECK (n_score_rows >= 0),
    source_prediction_sha256 text NOT NULL,
    source_seasonality_sha256 text NOT NULL,
    scale_quality_flags text DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (
        model_name,
        grain,
        seasonality_source_id,
        source_prediction_sha256,
        source_seasonality_sha256,
        benchmark_quantile,
        headroom_multiplier
    )
);
