from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.mast_acorn import (
    MastAcornCountyYear,
    MastAcornExtractionSummary,
)


runner = CliRunner()


def test_mast_acorn_command_writes_structured_and_summary_outputs(
    tmp_path, monkeypatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for year in [2017, 2020, 2021]:
        (raw_dir / f"maryland_dnr_wmd_mast_survey_{year}.pdf").write_bytes(b"%PDF")

    def fake_build(source_path, *, year, source_id, source_url, parser):
        return (
            [
                MastAcornCountyYear(
                    county_fips="24023",
                    county_name="Garrett County",
                    year=year,
                    region="Western Maryland",
                    mast_category="overall",
                    mast_index=82.5,
                    mast_rating="bumper",
                    acorn_index=77.0,
                    hard_mast_index=82.5,
                    soft_mast_index=41.0,
                    plots_observed=20,
                    expected_plots=20,
                    coverage_complete=True,
                    source_id=source_id,
                    source_url_hash="hash",
                    feature_quality_flags="western_maryland_only",
                    extracted_text_excerpt="excerpt",
                )
            ],
            MastAcornExtractionSummary(
                source_id=source_id,
                source_url_hash="hash",
                year=year,
                parser=parser,
                source_path=str(source_path),
                extraction_status="structured",
                structured_row_count=1,
                feature_quality_flags="",
                notes="ok",
                extracted_text_excerpt="excerpt",
            ),
        )

    monkeypatch.setattr("tickbiterisk.cli.build_mast_acorn_from_pdf", fake_build)

    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 3 mast/acorn row(s)" in result.stdout
    assert (tmp_path / "out" / "maryland_dnr_mast_acorn_county_year.csv").exists()
    assert (
        tmp_path / "out" / "maryland_dnr_mast_acorn_extraction_summary.csv"
    ).exists()


def test_mast_acorn_command_writes_manual_observations_when_provided(
    tmp_path, monkeypatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for year in [2017, 2020, 2021]:
        (raw_dir / f"maryland_dnr_wmd_mast_survey_{year}.pdf").write_bytes(b"%PDF")
    manual = tmp_path / "manual.csv"
    manual.write_text(
        "\n".join(
            [
                "county_fips,county_name,year,mast_rating,observation_basis,observer_scope,source_id,feature_quality_flags,notes",
                "24003,Anne Arundel County,2025,bumper,heavy acorn fall,neighborhood,manual_aa_2025,,Not official",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tickbiterisk.cli.build_mast_acorn_from_pdf",
        lambda source_path, *, year, source_id, source_url, parser: (
            [],
            MastAcornExtractionSummary(
                source_id=source_id,
                source_url_hash="hash",
                year=year,
                parser=parser,
                source_path=str(source_path),
                extraction_status="no_supported_values",
                structured_row_count=0,
                feature_quality_flags="ocr_pending",
                notes="none",
                extracted_text_excerpt="",
            ),
        ),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
            "--manual-observations-path",
            str(manual),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 manual mast observation row(s)" in result.stdout
    assert (tmp_path / "out" / "manual_mast_observations_county_year.csv").exists()


def test_mast_acorn_command_validates_manual_observations_path_before_writing(
    tmp_path, monkeypatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for year in [2017, 2020, 2021]:
        (raw_dir / f"maryland_dnr_wmd_mast_survey_{year}.pdf").write_bytes(b"%PDF")

    def fake_build(source_path, *, year, source_id, source_url, parser):
        return (
            [
                MastAcornCountyYear(
                    county_fips="24023",
                    county_name="Garrett County",
                    year=year,
                    region="Western Maryland",
                    mast_category="overall",
                    mast_index=82.5,
                    mast_rating="bumper",
                    acorn_index=77.0,
                    hard_mast_index=82.5,
                    soft_mast_index=41.0,
                    plots_observed=20,
                    expected_plots=20,
                    coverage_complete=True,
                    source_id=source_id,
                    source_url_hash="hash",
                    feature_quality_flags="western_maryland_only",
                    extracted_text_excerpt="excerpt",
                )
            ],
            MastAcornExtractionSummary(
                source_id=source_id,
                source_url_hash="hash",
                year=year,
                parser=parser,
                source_path=str(source_path),
                extraction_status="structured",
                structured_row_count=1,
                feature_quality_flags="",
                notes="ok",
                extracted_text_excerpt="excerpt",
            ),
        )

    monkeypatch.setattr("tickbiterisk.cli.build_mast_acorn_from_pdf", fake_build)

    output_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
            "--manual-observations-path",
            str(tmp_path / "missing.csv"),
        ],
    )

    assert result.exit_code != 0
    assert "manual mast observation file not found" in result.output
    assert "Traceback" not in result.output
    assert not (output_dir / "maryland_dnr_mast_acorn_county_year.csv").exists()
    assert not (
        output_dir / "maryland_dnr_mast_acorn_extraction_summary.csv"
    ).exists()


def test_mast_acorn_command_rejects_invalid_parser_cleanly(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(tmp_path),
            "--parser",
            "pdfplumber",
        ],
    )

    assert result.exit_code != 0
    assert "parser must be pypdfium or docling" in result.output
    assert "Traceback" not in result.output


def test_mast_acorn_command_rejects_missing_raw_pdf_cleanly(tmp_path) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "mast source file not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()
