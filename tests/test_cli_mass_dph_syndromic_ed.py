import csv
import zipfile
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()

_MASSACHUSETTS_TABLE_ROWS = [
    ["Barnstable", "121,588", "177", "14.56"],
    ["Berkshire", "79,919", "119", "14.89"],
    ["Bristol", "342,998", "274", "7.99"],
    ["Dukes/Nantucket", "24,063", "212", "88.1"],
    ["Essex", "386,360", "107", "2.77"],
    ["Franklin", "37,948", "40", "10.54"],
    ["Hampden", "278,330", "78", "2.8"],
    ["Hampshire", "58,172", "58", "9.97"],
    ["Middlesex", "569,858", "187", "3.28"],
    ["Norfolk", "271,685", "114", "4.2"],
    ["Plymouth", "283,689", "301", "10.61"],
    ["Suffolk", "398,759", "56", "1.4"],
    ["Worcester", "385,350", "143", "3.71"],
]


def test_mass_dph_syndromic_ed_command_writes_output_and_provenance(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    for filename in [
        "mass_dph_tickborne_syndromic_2024_jan_dec.docx",
        "mass_dph_tickborne_syndromic_2025_jan_dec.docx",
        "mass_dph_tickborne_syndromic_2026_april.docx",
    ]:
        _write_docx_table(
            raw_dir / filename,
            [
                [
                    "County",
                    "Total Visits",
                    "Number of Tick-borne Disease Visits",
                    "Rate (Per 10,000) of Tick-borne Disease Visits",
                ],
                *_MASSACHUSETTS_TABLE_ROWS,
            ],
        )

    result = runner.invoke(
        app,
        [
            "etl",
            "mass-dph-syndromic-ed",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 39 Massachusetts DPH syndromic ED county summary row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "mass_dph_syndromic_ed_county_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 39
    assert Counter(row["source_id"] for row in rows) == {
        "mass_dph_tickborne_syndromic_2024_jan_dec_docx": 13,
        "mass_dph_tickborne_syndromic_2025_jan_dec_docx": 13,
        "mass_dph_tickborne_syndromic_2026_april_docx": 13,
    }
    assert {row["state_abbr"] for row in rows} == {"MA"}
    assert all("syndromic_ed_signal" in row["feature_quality_flags"] for row in rows)
    assert all("not_lyme_incidence" in row["feature_quality_flags"] for row in rows)
    assert all("not_reported_case_outcome" in row["feature_quality_flags"] for row in rows)

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "mass_dph_tickborne_syndromic_2024_jan_dec_docx",
        "mass_dph_tickborne_syndromic_2025_jan_dec_docx",
        "mass_dph_tickborne_syndromic_2026_april_docx",
    ]
    assert all(
        "mass-dph-syndromic-ed" in row["acquisition_command"]
        for row in provenance_rows
    )
    assert all(
        "not Lyme incidence" in row["modeling_caveats"]
        for row in provenance_rows
    )
    assert {row["row_count"] for row in provenance_rows} == {"13"}
    assert all("DOCX" in row["parser_method"] for row in provenance_rows)


def test_mass_dph_syndromic_ed_command_fails_cleanly_when_report_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "etl",
            "mass-dph-syndromic-ed",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Massachusetts DPH syndromic ED source file not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()


def _write_docx_table(path: Path, rows: list[list[str]]) -> None:
    table_rows = []
    for row in rows:
        cells = "".join(
            f"<w:tc><w:p><w:r><w:t>{escape(value)}</w:t></w:r></w:p></w:tc>"
            for value in row
        )
        table_rows.append(f"<w:tr>{cells}</w:tr>")
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:tbl>{''.join(table_rows)}</w:tbl></w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
