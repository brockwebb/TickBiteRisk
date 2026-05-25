from tickbiterisk.etl.mast_acorn import (
    MastAcornExtractionSummary,
    build_mast_acorn_from_pdf,
    parse_mast_acorn_text,
)


MAST_TEXT = """
Western Maryland Mast Survey 2021
Region: Western Maryland
County: Garrett County
Mast Category: overall
Hard Mast Index: 82.5
Soft Mast Index: 41
Acorn Index: 77
Mast Rating: bumper
Plots Observed: 20
Expected Plots: 20
"""


def test_parse_mast_acorn_text_extracts_supported_county_values() -> None:
    rows = parse_mast_acorn_text(
        MAST_TEXT,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24023"
    assert row.county_name == "Garrett County"
    assert row.year == 2021
    assert row.region == "Western Maryland"
    assert row.mast_category == "overall"
    assert row.mast_index == 82.5
    assert row.hard_mast_index == 82.5
    assert row.soft_mast_index == 41.0
    assert row.acorn_index == 77.0
    assert row.mast_rating == "bumper"
    assert row.plots_observed == 20
    assert row.expected_plots == 20
    assert row.coverage_complete is True
    assert "western_maryland_only" in row.feature_quality_flags


def test_build_mast_acorn_from_pdf_uses_injected_text_extractor(tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    rows, summary = build_mast_acorn_from_pdf(
        pdf,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
        parser="pypdfium",
        text_extractor=lambda source: MAST_TEXT,
    )

    assert len(rows) == 1
    assert summary.extraction_status == "structured"
    assert summary.structured_row_count == 1
    assert summary.parser == "pypdfium"


def test_build_mast_acorn_from_pdf_records_no_supported_values(tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    rows, summary = build_mast_acorn_from_pdf(
        pdf,
        year=2020,
        source_id="maryland_dnr_wmd_mast_survey_2020",
        source_url="https://example.test/mast2020.pdf",
        parser="pypdfium",
        text_extractor=lambda source: "Western Maryland Mast Survey 2020",
    )

    assert rows == []
    assert isinstance(summary, MastAcornExtractionSummary)
    assert summary.extraction_status == "no_supported_values"
    assert summary.structured_row_count == 0
    assert "ocr_pending" in summary.feature_quality_flags
