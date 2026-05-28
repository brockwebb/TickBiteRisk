from pathlib import Path

import pandas as pd

from tickbiterisk.etl.tick_status import (
    build_tick_status_county_features,
    parse_ixodes_status,
    parse_lone_star_status,
    parse_pathogen_status,
)
from tickbiterisk.etl.tick_status_build import (
    TICK_STATUS_FEATURE_COLUMNS,
    write_tick_status_outputs,
)


def _write_excel(path: Path, sheet_name: str, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_excel(path, sheet_name=sheet_name, index=False)


def _write_excel_with_header_on_second_row(
    path: Path, sheet_name: str, rows: list[dict[str, object]]
) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(
            writer, sheet_name=sheet_name, index=False, startrow=1
        )
        worksheet = writer.sheets[sheet_name]
        worksheet.cell(row=1, column=1, value="Generated report metadata")


def test_parse_ixodes_status_normalizes_maryland_rows(tmp_path: Path) -> None:
    path = tmp_path / "ixodes.xlsx"
    _write_excel(
        path,
        "Ixodes records 2025",
        [
            {
                "FIPSCode": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_scapularis_data_source": "CDC historic",
                "Ixodes_pacificus_county_status": "No records",
                "Ixodes_pacificus_data_source": "CDC historic",
            }
        ],
    )
    rows = parse_ixodes_status(path, source_id="cdc_ixodes_county_status_2025")
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["ixodes_scapularis_status"] == "established"


def test_parse_ixodes_status_filters_non_maryland_and_sorts_by_fips(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ixodes.xlsx"
    _write_excel(
        path,
        "Ixodes records 2025",
        [
            {
                "FIPSCode": "24005",
                "State": "MD",
                "County": "Baltimore County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_pacificus_county_status": "No records",
            },
            {
                "FIPSCode": "51013",
                "State": "VA",
                "County": "Arlington County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_pacificus_county_status": "No records",
            },
            {
                "FIPSCode": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_pacificus_county_status": "No records",
            },
        ],
    )
    rows = parse_ixodes_status(path, source_id="cdc_ixodes_county_status_2025")
    assert [row["county_fips"] for row in rows] == ["24003", "24005"]
    assert rows[0]["ixodes_scapularis_source"] == ""


def test_parse_pathogen_status_preserves_no_records_language(tmp_path: Path) -> None:
    path = tmp_path / "pathogens.xlsx"
    _write_excel(
        path,
        "Ixodes Pathogens 2025",
        [
            {
                "FIPS_Code": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Borrelia_burgdorferi_sensu_stricto_County_Status": "No records",
                "Borrelia_mayonii_County_Status": "Present",
                "Borrelia_miyamotoi_County_Status": "Present",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "No records",
                "Ehrlichia_muris_eauclairensis_County_Status": "No records",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ],
    )
    rows = parse_pathogen_status(path, source_id="cdc_ixodes_pathogen_status_2025")
    assert rows[0]["borrelia_burgdorferi_status"] == "no_records"
    assert rows[0]["borrelia_mayonii_status"] == "present"
    assert rows[0]["borrelia_miyamotoi_status"] == "present"
    assert rows[0]["ehrlichia_muris_eauclairensis_status"] == "no_records"


def test_parse_pathogen_status_supports_header_on_second_row(tmp_path: Path) -> None:
    path = tmp_path / "pathogens.xlsx"
    _write_excel_with_header_on_second_row(
        path,
        "Ixodes Pathogens 2025",
        [
            {
                "FIPS_Code": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Borrelia_burgdorferi_sensu_stricto_County_Status": "No records",
                "Borrelia_miyamotoi_County_Status": "Present",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "No records",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ],
    )
    rows = parse_pathogen_status(path, source_id="cdc_ixodes_pathogen_status_2025")
    assert rows[0]["county_fips"] == "24003"


def test_parse_lone_star_status(tmp_path: Path) -> None:
    path = tmp_path / "lone-star.xlsx"
    _write_excel(
        path,
        "A. americanum Records 2024",
        [
            {
                "FIPS": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "County Status of A. americanum": "Established",
                "Source": "Springer et al. 2014",
                "Source Comments": "",
            }
        ],
    )
    rows = parse_lone_star_status(path, source_id="cdc_lone_star_status_2024")
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["amblyomma_americanum_status"] == "established"
    assert rows[0]["source_comments"] == ""


def test_parse_lone_star_status_supports_2025_workbook_shape(tmp_path: Path) -> None:
    path = tmp_path / "lone-star-2025.xlsx"
    _write_excel(
        path,
        "A. americanum Records 2025",
        [
            {
                "FIPS": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "2025 County Status of A. americanum": "Established",
                "Source": "CDC map",
                "Source Comments": "",
            }
        ],
    )
    rows = parse_lone_star_status(path, source_id="cdc_lone_star_status_2025")
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["amblyomma_americanum_status"] == "established"


def test_build_tick_status_county_features_combines_sources_and_flags_limits() -> None:
    rows = build_tick_status_county_features(
        ixodes_rows=[
            {
                "source_id": "cdc_ixodes_county_status_2025",
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "ixodes_scapularis_status": "established",
                "ixodes_scapularis_source": "CDC historical record",
                "ixodes_pacificus_status": "no_records",
                "ixodes_pacificus_source": "",
            }
        ],
        pathogen_rows=[
            {
                "source_id": "cdc_ixodes_pathogen_status_2025",
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "borrelia_burgdorferi_status": "present",
                "borrelia_mayonii_status": "no_records",
                "borrelia_miyamotoi_status": "no_records",
                "anaplasma_phagocytophilum_status": "present",
                "ehrlichia_muris_eauclairensis_status": "no_records",
                "babesia_microti_status": "no_records",
                "powassan_virus_status": "no_records",
            }
        ],
        lone_star_rows=[
            {
                "source_id": "cdc_lone_star_status_2024",
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "amblyomma_americanum_status": "established",
                "status_source": "CDC map",
                "source_comments": "",
            }
        ],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24003"
    assert row.ixodes_scapularis_status == "established"
    assert row.borrelia_burgdorferi_status == "present"
    assert row.borrelia_mayonii_status == "no_records"
    assert row.ehrlichia_muris_eauclairensis_status == "no_records"
    assert row.amblyomma_americanum_status == "established"
    assert row.tick_status_source_ids == (
        "cdc_ixodes_county_status_2025,"
        "cdc_ixodes_pathogen_status_2025,"
        "cdc_lone_star_status_2024"
    )
    assert set(row.tick_status_feature_quality_flags.split(",")) == {
        "current_status_retrospective_proxy",
        "no_records_not_absence",
        "status_only_not_prevalence",
    }


def test_write_tick_status_outputs_writes_source_tables_and_feature_table(
    tmp_path: Path,
) -> None:
    ixodes_rows = [
        {
            "source_id": "cdc_ixodes_county_status_2025",
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "ixodes_scapularis_status": "established",
            "ixodes_scapularis_source": "CDC historical record",
            "ixodes_pacificus_status": "no_records",
            "ixodes_pacificus_source": "",
        }
    ]
    pathogen_rows = [
        {
            "source_id": "cdc_ixodes_pathogen_status_2025",
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "borrelia_burgdorferi_status": "present",
            "borrelia_mayonii_status": "no_records",
            "borrelia_miyamotoi_status": "no_records",
            "anaplasma_phagocytophilum_status": "present",
            "ehrlichia_muris_eauclairensis_status": "no_records",
            "babesia_microti_status": "no_records",
            "powassan_virus_status": "no_records",
        }
    ]
    lone_star_rows = [
        {
            "source_id": "cdc_lone_star_status_2024",
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "amblyomma_americanum_status": "established",
            "status_source": "CDC map",
            "source_comments": "",
        }
    ]
    feature_rows = build_tick_status_county_features(
        ixodes_rows=ixodes_rows,
        pathogen_rows=pathogen_rows,
        lone_star_rows=lone_star_rows,
    )

    outputs = write_tick_status_outputs(
        ixodes_rows=ixodes_rows,
        pathogen_rows=pathogen_rows,
        lone_star_rows=lone_star_rows,
        feature_rows=feature_rows,
        output_dir=tmp_path,
    )

    assert outputs.vector_path.name == "tick_vector_status.csv"
    assert outputs.pathogen_path.name == "tick_pathogen_status.csv"
    assert outputs.lone_star_path.name == "lone_star_status.csv"
    assert outputs.features_path.name == "tick_status_county_features.csv"

    feature_df = pd.read_csv(outputs.features_path, dtype=str)
    assert list(feature_df.columns) == TICK_STATUS_FEATURE_COLUMNS
    assert feature_df.loc[0, "county_fips"] == "24003"
    assert feature_df.loc[0, "borrelia_burgdorferi_status"] == "present"
