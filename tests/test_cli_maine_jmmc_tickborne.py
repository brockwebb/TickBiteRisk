import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_maine_jmmc_tickborne_command_writes_output_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    pdf = raw_dir / "jmmc_maine_tickborne_trends_2001_2024.pdf"
    pdf.write_bytes(b"%PDF maine")

    def fake_parse_pdf(path: Path, *, source_id: str, source_url: str):
        from tickbiterisk.etl.maine_jmmc_tickborne import (
            parse_maine_jmmc_tickborne_rates_text,
        )

        assert path == pdf
        return parse_maine_jmmc_tickborne_rates_text(
            """
            Table 2. Rates of selected tick-borne diseases per 100 000 persons in Maine, 2024.*
            County
            Lincoln 438.3 79.4 0.0 698.5 2.7
            State 92.8 22.3 1.6 231.1 0.5
            *Data are preliminary as of January 20, 2025, and subject to change.
            """,
            source_id=source_id,
            source_url=source_url,
            parser_method="pypdfium_text_table2_rates",
        )

    monkeypatch.setattr(
        "tickbiterisk.cli.parse_maine_jmmc_tickborne_rates_pdf",
        fake_parse_pdf,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "maine-jmmc-tickborne-rates",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 Maine JMMC tickborne county-rate row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "maine_jmmc_tickborne_county_rates_2024.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["county_fips"] for row in rows] == ["23015", ""]
    assert all("rates_only_no_case_counts" in row["feature_quality_flags"] for row in rows)
    assert all("not_model_input" in row["feature_quality_flags"] for row in rows)

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "maine_jmmc_2024_county_rates_pdf"
    ]
    provenance = provenance_rows[0]
    assert provenance["row_count"] == "2"
    assert "maine-jmmc-tickborne-rates" in provenance["acquisition_command"]
    assert "jmmc_maine_tickborne_trends_2001_2024.pdf=" in provenance[
        "derived_artifact_sha256s"
    ]
    assert "preliminary rates only" in provenance["modeling_caveats"]
    assert "not stable true incidence" in provenance["modeling_caveats"]


def test_maine_jmmc_tickborne_command_fails_cleanly_when_pdf_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "etl",
            "maine-jmmc-tickborne-rates",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Maine JMMC tickborne trends PDF not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()
