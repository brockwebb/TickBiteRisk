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
