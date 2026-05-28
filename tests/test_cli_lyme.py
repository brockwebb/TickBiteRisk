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
    assert "Wrote acquisition provenance manifest" in result.stdout

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    anne_2022 = next(
        row
        for row in rows
        if row["county_fips"] == "24003" and row["year"] == "2022"
    )
    assert anne_2022["total_cases"] == "127"
    assert anne_2022["canonical_source_id"] == "cdc_lyme_public_2022_2023"

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))

    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_lyme_county_dashboard_2023",
        "cdc_lyme_county_geodata_2000_2021",
        "cdc_lyme_public_1992_2007",
        "cdc_lyme_public_2008_2021",
        "cdc_lyme_public_2022_2023",
    ]
    provenance_by_source = {row["source_id"]: row for row in provenance_rows}
    public_1992 = provenance_by_source["cdc_lyme_public_1992_2007"]
    assert public_1992["row_count"] == "0"
    assert public_1992["source_url"].endswith("84rx-ksgd/about_data")
    assert "cdc_lyme_public_1992_2007.csv=" in public_1992[
        "derived_artifact_sha256s"
    ]
    assert "lyme_county_year_reconciled.csv=" in public_1992[
        "derived_artifact_sha256s"
    ]
    assert public_1992["derived_artifact_paths"] == (
        "cdc_lyme_public_1992_2007.csv;lyme_county_year_reconciled.csv"
    )
    assert str(tmp_path) not in public_1992["derived_artifact_paths"]

    public_2022 = provenance_by_source["cdc_lyme_public_2022_2023"]
    assert public_2022["row_count"] == "3"
    assert public_2022["parser_method"] == "parse_cdc_lyme_public_use"
    assert "--provenance-manifest-path" in public_2022["acquisition_command"]
    assert str(tmp_path) not in public_2022["acquisition_command"]
    assert public_2022["extraction_quality"] == "accepted"
    assert "case definition" in public_2022["modeling_caveats"]


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
    assert "Wrote acquisition provenance manifest" in result.stdout

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

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    provenance_by_source = {row["source_id"]: row for row in provenance_rows}

    mdh_provenance = provenance_by_source["mdh_lyme_2013_2024_pdf"]
    assert mdh_provenance["row_count"] == "1"
    assert mdh_provenance["parser_method"] == "parse_mdh_lyme_pdf"
    assert mdh_provenance["citation_url"] == (
        "https://health.maryland.gov/phpa/OIDEOR/CZVBD/Shared%20Documents/"
        "Lyme%20Disease%20Data%202013%20to%202024.pdf"
    )
    assert "2024 rows selected" in mdh_provenance["request_description"]
    assert "mdh_lyme_2013_2024.pdf=" in mdh_provenance["derived_artifact_sha256s"]
    assert str(tmp_path) not in mdh_provenance["derived_artifact_paths"]
    assert str(tmp_path) not in mdh_provenance["acquisition_command"]
    assert "state/probable-only" in mdh_provenance["modeling_caveats"]


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
    assert not (output_dir / "acquisition_provenance.csv").exists()


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
    assert not (output_dir / "acquisition_provenance.csv").exists()
