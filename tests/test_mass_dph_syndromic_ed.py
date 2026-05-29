import csv
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from tickbiterisk.etl.mass_dph_syndromic_ed import (
    parse_mass_dph_syndromic_ed_docx,
)
from tickbiterisk.etl.mass_dph_syndromic_ed_build import (
    write_mass_dph_syndromic_ed_output,
)


def test_mass_dph_docx_parser_extracts_county_table_and_combined_geography(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "mass_dph_tickborne_syndromic_2025_jan_dec.docx"
    _write_docx_table(
        docx_path,
        [
            [
                "County",
                "Total Visits",
                "Number of Tick-borne Disease Visits",
                "Rate (Per 10,000) of Tick-borne Disease Visits",
            ],
            ["Barnstable", "121,588", "177", "14.56"],
            ["Dukes/Nantucket", "24,063", "212", "88.1"],
            ["Missing or out of state", "n=179171", "", ""],
        ],
    )

    rows = parse_mass_dph_syndromic_ed_docx(
        docx_path,
        source_id="mass_dph_tickborne_syndromic_2025_jan_dec_docx",
        source_url=(
            "https://www.mass.gov/doc/"
            "tick-exposure-and-tickborne-disease-syndromic-surveillance-report-"
            "january-december-2025/download"
        ),
        report_year=2025,
        report_period_label="January-December 2025",
        report_period_start="2025-01-01",
        report_period_end="2025-12-31",
        expected_geography_count=2,
    )

    assert len(rows) == 2
    barnstable = rows[0]
    assert barnstable.state_fips == "25"
    assert barnstable.state_abbr == "MA"
    assert barnstable.state_name == "Massachusetts"
    assert barnstable.report_year == 2025
    assert barnstable.report_period_label == "January-December 2025"
    assert barnstable.report_period_start == "2025-01-01"
    assert barnstable.report_period_end == "2025-12-31"
    assert barnstable.county_name == "Barnstable"
    assert barnstable.county_fips == "25001"
    assert barnstable.county_fips_list == "25001"
    assert barnstable.geography_type == "county"
    assert barnstable.total_ed_visits == 121588
    assert barnstable.tickborne_disease_ed_visits == 177
    assert barnstable.tickborne_disease_rate_per_10000 == 14.56
    assert barnstable.missing_or_out_of_state_visits == 179171
    assert "syndromic_ed_signal" in barnstable.feature_quality_flags
    assert "not_reported_case_outcome" in barnstable.feature_quality_flags
    assert "not_tick_bite_count" in barnstable.feature_quality_flags

    combined = rows[1]
    assert combined.county_name == "Dukes/Nantucket"
    assert combined.county_fips == ""
    assert combined.county_fips_list == "25007;25019"
    assert combined.geography_type == "combined_counties"
    assert "dukes_nantucket_combined" in combined.feature_quality_flags


def test_mass_dph_writer_outputs_stable_csv_schema(tmp_path: Path) -> None:
    docx_path = tmp_path / "mass.docx"
    _write_docx_table(
        docx_path,
        [
            [
                "County",
                "Total Visits",
                "Number of Tick-borne Disease Visits",
                "Rate (Per 10,000) of Tick-borne Disease Visits",
            ],
            ["Plymouth", "86,667", "24", "2.77"],
        ],
    )
    rows = parse_mass_dph_syndromic_ed_docx(
        docx_path,
        source_id="mass_dph_tickborne_syndromic_2026_april_docx",
        source_url="https://www.mass.gov/doc/report/download",
        report_year=2026,
        report_period_label="April 2026",
        report_period_start="2026-01-01",
        report_period_end="2026-04-30",
        expected_geography_count=1,
    )

    output_path = write_mass_dph_syndromic_ed_output(rows, tmp_path / "out")

    assert output_path.name == "mass_dph_syndromic_ed_county_summary.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert written == [
        {
            "state_fips": "25",
            "state_abbr": "MA",
            "state_name": "Massachusetts",
            "report_year": "2026",
            "report_period_label": "April 2026",
            "report_period_start": "2026-01-01",
            "report_period_end": "2026-04-30",
            "county_name": "Plymouth",
            "county_fips": "25023",
            "county_fips_list": "25023",
            "geography_type": "county",
            "total_ed_visits": "86667",
            "tickborne_disease_ed_visits": "24",
            "tickborne_disease_rate_per_10000": "2.77",
            "missing_or_out_of_state_visits": "",
            "source_id": "mass_dph_tickborne_syndromic_2026_april_docx",
            "source_url": "https://www.mass.gov/doc/report/download",
            "parser_method": "docx_word_table1",
            "feature_quality_flags": (
                "mass_dph_official_docx,syndromic_ed_signal,ed_visit_proxy,"
                "ytd_snapshot,not_reported_case_outcome,"
                "not_lyme_incidence,not_confirmed_case_truth,not_disease_specific,"
                "not_tick_bite_count,county_residence_available,"
                "icd10_tickborne_disease_definition,not_public_default,"
                "not_model_input"
            ),
        }
    ]


def test_mass_dph_docx_parser_extracts_missing_count_from_report_note(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "mass_dph_tickborne_syndromic_2026_april.docx"
    _write_docx_table(
        docx_path,
        [
            [
                "County",
                "Total Visits",
                "Number of Tick-borne Disease Visits",
                "Rate (Per 10,000) of Tick-borne Disease Visits",
            ],
            ["Suffolk", "122,037", "2", "0.16"],
        ],
        paragraphs=[
            "Visits with missing county or out of state are not shown (n=47465)."
        ],
    )

    rows = parse_mass_dph_syndromic_ed_docx(
        docx_path,
        source_id="mass_dph_tickborne_syndromic_2026_april_docx",
        source_url="https://www.mass.gov/doc/report/download",
        report_year=2026,
        report_period_label="April 2026",
        report_period_start="2026-01-01",
        report_period_end="2026-04-30",
        expected_geography_count=1,
    )

    assert rows[0].missing_or_out_of_state_visits == 47465


def test_mass_dph_docx_parser_rejects_incomplete_table_by_default(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "mass_incomplete.docx"
    _write_docx_table(
        docx_path,
        [
            [
                "County",
                "Total Visits",
                "Number of Tick-borne Disease Visits",
                "Rate (Per 10,000) of Tick-borne Disease Visits",
            ],
            ["Barnstable", "121,588", "177", "14.56"],
            ["Dukes and Nantucket", "24,063", "212", "88.1"],
        ],
    )

    with pytest.raises(ValueError, match="Unrecognized Massachusetts DPH county"):
        parse_mass_dph_syndromic_ed_docx(
            docx_path,
            source_id="mass_dph_tickborne_syndromic_2025_jan_dec_docx",
            source_url="https://www.mass.gov/doc/report/download",
            report_year=2025,
            report_period_label="January-December 2025",
            report_period_start="2025-01-01",
            report_period_end="2025-12-31",
        )


def test_mass_dph_docx_parser_preserves_numbers_split_across_word_runs(
    tmp_path: Path,
) -> None:
    docx_path = tmp_path / "mass_split_runs.docx"
    _write_docx_table(
        docx_path,
        [
            [
                "County",
                "Total Visits",
                "Number of Tick-borne Disease Visits",
                "Rate (Per 10,000) of Tick-borne Disease Visits",
            ],
            ["Barnstable", ["36", ",402"], "8", "2.2"],
        ],
    )

    rows = parse_mass_dph_syndromic_ed_docx(
        docx_path,
        source_id="mass_dph_tickborne_syndromic_2026_april_docx",
        source_url="https://www.mass.gov/doc/report/download",
        report_year=2026,
        report_period_label="April 2026",
        report_period_start="2026-01-01",
        report_period_end="2026-04-30",
        expected_geography_count=1,
    )

    assert rows[0].total_ed_visits == 36402


def _write_docx_table(
    path: Path,
    rows: list[list[str | list[str]]],
    *,
    paragraphs: list[str] | None = None,
) -> None:
    table_rows = []
    for row in rows:
        cells = "".join(
            f"<w:tc><w:p>{_cell_runs(value)}</w:p></w:tc>"
            for value in row
        )
        table_rows.append(f"<w:tr>{cells}</w:tr>")
    paragraph_xml = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs or []
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:tbl>{''.join(table_rows)}</w:tbl>{paragraph_xml}</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def _cell_runs(value: str | list[str]) -> str:
    runs = value if isinstance(value, list) else [value]
    return "".join(f"<w:r><w:t>{escape(run)}</w:t></w:r>" for run in runs)
