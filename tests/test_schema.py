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
