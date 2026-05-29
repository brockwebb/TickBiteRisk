import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_nj_reportable_tickborne_command_writes_output_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    stats_pdf = raw_dir / "new_jersey_doh_reportable_disease_statistics_2024.pdf"
    notes_pdf = raw_dir / "new_jersey_doh_reportable_disease_technical_notes_2024.pdf"
    stats_pdf.write_bytes(b"%PDF stats")
    notes_pdf.write_bytes(b"%PDF notes")

    def fake_parse_pdf(path: Path, *, source_id: str, source_url: str):
        from tickbiterisk.etl.nj_reportable_tickborne import (
            parse_nj_doh_reportable_tickborne_text,
        )

        assert path == stats_pdf
        return parse_nj_doh_reportable_tickborne_text(
            """
            2024 New Jersey Reportable Communicable Disease Report
            10:56 Friday, August 22, 2025 1
            ( December 31, 2023 to December 28, 2024)
            STATE TOTAL LYME DISEASE 6256
            ATLANTIC LYME DISEASE 152
            BERGEN LYME DISEASE 414
            """,
            source_id=source_id,
            source_url=source_url,
            parser_method="pypdfium_text_reportable_rows",
        )

    monkeypatch.setattr(
        "tickbiterisk.cli.parse_nj_doh_reportable_tickborne_pdf",
        fake_parse_pdf,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "nj-doh-reportable-tickborne",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 3 New Jersey DOH reportable tickborne row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "nj_doh_reportable_tickborne_county_year.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["county_fips"] for row in rows] == ["", "34001", "34003"]
    assert {row["source_id"] for row in rows} == {
        "nj_doh_reportable_tickborne_2024_pdf"
    }
    assert all("not_confirmed_case_truth" in row["feature_quality_flags"] for row in rows)
    assert all("not_model_input" in row["feature_quality_flags"] for row in rows)

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "nj_doh_reportable_tickborne_2024_pdf"
    ]
    provenance = provenance_rows[0]
    assert provenance["row_count"] == "3"
    assert "nj-doh-reportable-tickborne" in provenance["acquisition_command"]
    assert "technical_notes_2024.pdf=" in provenance["derived_artifact_sha256s"]
    assert "2022 Lyme laboratory-based surveillance" in provenance["modeling_caveats"]


def test_nj_reportable_tickborne_command_fails_cleanly_when_report_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "etl",
            "nj-doh-reportable-tickborne",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "New Jersey DOH reportable disease statistics PDF not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()
