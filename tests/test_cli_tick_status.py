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
    assert (tmp_path / "out" / "tick_vector_status.csv").exists()
    assert (tmp_path / "out" / "tick_pathogen_status.csv").exists()
    assert (tmp_path / "out" / "lone_star_status.csv").exists()
    assert (tmp_path / "out" / "tick_status_county_features.csv").exists()


def test_tick_status_command_fails_cleanly_when_source_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_ixodes(raw_dir / "cdc_ixodes_county_status_2025.xlsx")

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


def _write_tick_status_workbooks(raw_dir: Path) -> None:
    _write_ixodes(raw_dir / "cdc_ixodes_county_status_2025.xlsx")
    pd.DataFrame(
        [
            {
                "FIPS_Code": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Borrelia_burgdorferi_sensu_stricto_County_Status": "Present",
                "Borrelia_miyamotoi_County_Status": "No records",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "Present",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ]
    ).to_excel(
        raw_dir / "cdc_ixodes_pathogen_status_2025.xlsx",
        sheet_name="Ixodes Pathogens 2025",
        index=False,
    )
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
