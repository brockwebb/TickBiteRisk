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
