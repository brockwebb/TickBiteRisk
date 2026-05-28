import csv
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from tickbiterisk.cli import app

runner = CliRunner()


def test_tick_status_command_writes_source_and_feature_outputs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_tick_status_workbooks(raw_dir)

    result = runner.invoke(
        app,
        [
            "etl",
            "tick-status",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 tick status feature row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout
    assert (tmp_path / "out" / "tick_vector_status.csv").exists()
    assert (tmp_path / "out" / "tick_pathogen_status.csv").exists()
    assert (tmp_path / "out" / "lone_star_status.csv").exists()
    assert (tmp_path / "out" / "tick_status_county_features.csv").exists()

    with (tmp_path / "out" / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_ixodes_county_status_2026",
        "cdc_ixodes_pathogen_status_2026",
        "cdc_lone_star_status_2025",
    ]
    provenance_by_source = {row["source_id"]: row for row in provenance_rows}

    ixodes_provenance = provenance_by_source["cdc_ixodes_county_status_2026"]
    assert ixodes_provenance["row_count"] == "1"
    assert ixodes_provenance["parser_method"] == "parse_ixodes_status"
    assert "cdc_ixodes_county_status_2026.xlsx" in ixodes_provenance[
        "derived_artifact_paths"
    ]
    assert (
        ixodes_provenance["source_url"]
        == "https://www.cdc.gov/ticks/media/files/2026/04/Public_Use_Ixodes_County_Table_2026_03252026.xlsx"
    )
    assert (
        ixodes_provenance["citation_url"]
        == "https://www.cdc.gov/ticks/data-research/facts-stats/tick-surveillance-data-sets.html"
    )
    assert "tick_vector_status.csv=" in ixodes_provenance[
        "derived_artifact_sha256s"
    ]
    assert str(tmp_path) not in ixodes_provenance["derived_artifact_paths"]

    pathogen_provenance = provenance_by_source["cdc_ixodes_pathogen_status_2026"]
    assert pathogen_provenance["row_count"] == "1"
    assert pathogen_provenance["parser_method"] == "parse_pathogen_status"
    assert "--provenance-manifest-path" in pathogen_provenance["acquisition_command"]
    assert str(tmp_path) not in pathogen_provenance["acquisition_command"]
    assert "status only, not prevalence" in pathogen_provenance["modeling_caveats"]

    lone_star_provenance = provenance_by_source["cdc_lone_star_status_2025"]
    assert lone_star_provenance["row_count"] == "1"
    assert lone_star_provenance["parser_method"] == "parse_lone_star_status"


def test_tick_status_command_fails_cleanly_when_source_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_ixodes(raw_dir / "cdc_ixodes_county_status_2026.xlsx")

    result = runner.invoke(
        app,
        [
            "etl",
            "tick-status",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "tick status source file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "tick_status_county_features.csv").exists()
    assert not (tmp_path / "out" / "acquisition_provenance.csv").exists()


def test_tick_status_command_accepts_legacy_raw_workbook_filenames(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_ixodes(raw_dir / "cdc_ixodes_county_status_2025.xlsx")
    _write_pathogens(raw_dir / "cdc_ixodes_pathogen_status_2025.xlsx")
    pd.DataFrame(
        [
            {
                "FIPS": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "County Status of A. americanum": "Established",
                "Source": "CDC map",
                "Source Comments": "",
            }
        ]
    ).to_excel(
        raw_dir / "cdc_lone_star_status_2024.xlsx",
        sheet_name="A. americanum Records 2024",
        index=False,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "tick-status",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    with (tmp_path / "out" / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_ixodes_county_status_2025",
        "cdc_ixodes_pathogen_status_2025",
        "cdc_lone_star_status_2024",
    ]


def _write_tick_status_workbooks(raw_dir: Path) -> None:
    _write_ixodes(raw_dir / "cdc_ixodes_county_status_2026.xlsx")
    _write_pathogens(raw_dir / "cdc_ixodes_pathogen_status_2026.xlsx")
    pd.DataFrame(
        [
            {
                "FIPS": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "2025 County Status of A. americanum": "Established",
                "Source": "CDC map",
                "Source Comments": "",
            }
        ]
    ).to_excel(
        raw_dir / "cdc_lone_star_status_2025.xlsx",
        sheet_name="A. americanum Records 2025",
        index=False,
    )


def _write_pathogens(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "FIPS_Code": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Borrelia_burgdorferi_sensu_stricto_County_Status": "Present",
                "Borrelia_mayonii_County_Status": "No records",
                "Borrelia_miyamotoi_County_Status": "No records",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "Present",
                "Ehrlichia_muris_eauclairensis_County_Status": "No records",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ]
    ).to_excel(
        path,
        sheet_name="Ixodes Pathogens 2025",
        index=False,
    )


def _write_ixodes(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "FIPSCode": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_scapularis_data_source": "CDC historical record",
                "Ixodes_pacificus_county_status": "No records",
                "Ixodes_pacificus_data_source": "",
            }
        ]
    ).to_excel(path, sheet_name="Ixodes records 2025", index=False)
