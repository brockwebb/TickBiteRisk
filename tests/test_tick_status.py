from pathlib import Path

import pandas as pd

from tickbiterisk.etl.tick_status import (
    parse_ixodes_status,
    parse_lone_star_status,
    parse_pathogen_status,
)


def _write_excel(path: Path, sheet_name: str, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_excel(path, sheet_name=sheet_name, index=False)


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
                "Borrelia_miyamotoi_County_Status": "Present",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "No records",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ],
    )
    rows = parse_pathogen_status(path, source_id="cdc_ixodes_pathogen_status_2025")
    assert rows[0]["borrelia_burgdorferi_status"] == "no_records"
    assert rows[0]["borrelia_miyamotoi_status"] == "present"


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
