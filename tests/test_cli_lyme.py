import csv
import shutil
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.lyme import LymeCountyYearValue


runner = CliRunner()

PUBLIC_USE_HEADER = "Year,State,FIPS,Case_status,Sex,Age_cat_yrs,Frequency\n"


def _copy_lyme_fixture(raw_dir: Path, fixture_name: str, output_name: str) -> None:
    shutil.copyfile(Path("tests/fixtures") / fixture_name, raw_dir / output_name)


def _create_required_lyme_sources(raw_dir: Path) -> None:
    raw_dir.mkdir()
    (raw_dir / "cdc_lyme_public_1992_2007.csv").write_text(
        PUBLIC_USE_HEADER,
        encoding="utf-8",
    )
    (raw_dir / "cdc_lyme_public_2008_2021.csv").write_text(
        PUBLIC_USE_HEADER,
        encoding="utf-8",
    )
    _copy_lyme_fixture(
        raw_dir,
        "lyme_public_use_2022_2023_mini.csv",
        "cdc_lyme_public_2022_2023.csv",
    )
    _copy_lyme_fixture(
        raw_dir,
        "ld_case_counts_by_county_mini.csv",
        "cdc_lyme_county_dashboard_2023.csv",
    )
    _copy_lyme_fixture(
        raw_dir,
        "lyme_geodata_mini.csv",
        "cdc_lyme_county_geodata_2000_2021.csv",
    )


def test_lyme_outcomes_command_writes_reconciled_county_years(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    _create_required_lyme_sources(raw_dir)

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    output_path = output_dir / "lyme_county_year_reconciled.csv"
    assert result.exit_code == 0
    assert output_path.exists()
    assert "Wrote 8 reconciled Lyme county-year outcome row(s)" in result.stdout
    assert str(output_path) in result.stdout

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    anne_2022 = next(
        row
        for row in rows
        if row["county_fips"] == "24003" and row["year"] == "2022"
    )
    assert anne_2022["total_cases"] == "127"
    assert anne_2022["canonical_source_id"] == "cdc_lyme_public_2022_2023"


def test_lyme_outcomes_command_includes_mdh_2024_when_pdf_is_present(
    tmp_path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    _create_required_lyme_sources(raw_dir)
    (raw_dir / "mdh_lyme_2013_2024.pdf").write_bytes(b"%PDF fixture")

    def fake_parse_mdh(path, source_id):
        return [
            LymeCountyYearValue(
                source_id=source_id,
                county_fips="24003",
                year=2023,
                confirmed_cases=161,
                probable_cases=0,
                total_cases=161,
            ),
            LymeCountyYearValue(
                source_id=source_id,
                county_fips="24003",
                year=2024,
                confirmed_cases=None,
                probable_cases=203,
                total_cases=203,
            ),
        ]

    monkeypatch.setattr("tickbiterisk.cli.parse_mdh_lyme_pdf", fake_parse_mdh)

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 9 reconciled Lyme county-year outcome row(s)" in result.stdout

    with (output_dir / "lyme_county_year_reconciled.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    anne_2024 = next(
        row
        for row in rows
        if row["county_fips"] == "24003" and row["year"] == "2024"
    )
    assert anne_2024["total_cases"] == "203"
    assert anne_2024["canonical_source_id"] == "mdh_lyme_2013_2024_pdf"
    assert anne_2024["data_quality_flags"] == (
        "lyme_case_definition_change;mdh_probable_only_2024;"
        "state_source_not_cdc_public_use"
    )

    anne_2023 = next(
        row
        for row in rows
        if row["county_fips"] == "24003" and row["year"] == "2023"
    )
    assert anne_2023["canonical_source_id"] == "cdc_lyme_public_2022_2023"


def test_lyme_outcomes_command_fails_cleanly_when_source_file_missing(
    tmp_path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    _create_required_lyme_sources(raw_dir)
    (raw_dir / "cdc_lyme_county_geodata_2000_2021.csv").unlink()

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Lyme source file not found" in result.output
    assert "Traceback" not in result.output
    assert not (output_dir / "lyme_county_year_reconciled.csv").exists()


def test_lyme_outcomes_command_validates_all_sources_before_parsing(
    tmp_path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    _create_required_lyme_sources(raw_dir)
    (raw_dir / "cdc_lyme_public_1992_2007.csv").write_text(
        "not,a,valid,public,use,file\n",
        encoding="utf-8",
    )
    (raw_dir / "cdc_lyme_county_geodata_2000_2021.csv").unlink()

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Lyme source file not found" in result.output
    assert "Missing CDC Lyme public-use columns" not in result.output
    assert not (output_dir / "lyme_county_year_reconciled.csv").exists()
