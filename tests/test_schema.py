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
        "weather_locations",
        "weather_daily",
        "weather_features_monthly",
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


def test_weather_daily_includes_soil_moisture_field() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "soil_moisture_0_7cm double precision" in schema


def test_weather_monthly_features_include_anomaly_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "temp_anomaly_vs_10yr double precision" in schema
    assert "precip_anomaly_vs_10yr double precision" in schema
    assert "humidity_anomaly_vs_10yr double precision" in schema


def test_weather_monthly_features_include_completeness_fields() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")

    assert "days_observed integer NOT NULL" in schema
    assert "expected_days integer NOT NULL" in schema
    assert "month_complete boolean NOT NULL" in schema
