import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_wv_vectorborne_summary_command_writes_output_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    for year in (2024, 2025):
        (raw_dir / f"west_virginia_oeps_vectorborne_{year}.pdf").write_bytes(
            b"%PDF fixture"
        )

    def fake_parse_pdf(path: Path, *, source_id: str, source_url: str):
        from tickbiterisk.etl.wv_vectorborne import parse_wv_vectorborne_report_text

        year = 2024 if "2024" in path.name else 2025
        cases = 2867 if year == 2024 else 4019
        as_of = "OCTOBER 25, 2024" if year == 2024 else "NOVEMBER 14, 2025"
        return parse_wv_vectorborne_report_text(
            f"""
            West Virginia Vectorborne Disease Surveillance Report
            JANUARY 1 - {as_of}
            Table 3. Summary of human cases of tickborne diseases through {as_of.title()}
            Tickborne Disease # Confirmed and Probable Cases through {as_of.title()} # of Counties Where Disease Reported
            Lyme disease {cases} 55
            Total {cases} --
            aTable includes only confirmed or probable cases that have been reviewed and closed by the Vectorborne Disease Epidemiologist.
            """,
            source_id=source_id,
            source_url=source_url,
            parser_method="pypdfium_text_table3",
        )

    monkeypatch.setattr("tickbiterisk.cli.parse_wv_vectorborne_report_pdf", fake_parse_pdf)

    result = runner.invoke(
        app,
        [
            "etl",
            "wv-vectorborne-summary",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 4 West Virginia vectorborne state summary row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "wv_vectorborne_state_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["source_id"] for row in rows} == {
        "west_virginia_oeps_vectorborne_2024_pdf",
        "west_virginia_oeps_vectorborne_2025_pdf",
    }
    assert [row["confirmed_probable_cases"] for row in rows if row["disease"] == "Lyme disease"] == [
        "2867",
        "4019",
    ]

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "west_virginia_oeps_vectorborne_2024_pdf",
        "west_virginia_oeps_vectorborne_2025_pdf",
    ]
    assert all(
        "wv-vectorborne-summary" in row["acquisition_command"]
        for row in provenance_rows
    )
    assert all(
        "state aggregate validation" in row["modeling_caveats"]
        for row in provenance_rows
    )


def test_wv_vectorborne_summary_command_fails_cleanly_when_report_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "etl",
            "wv-vectorborne-summary",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "WV vectorborne report source file not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()
