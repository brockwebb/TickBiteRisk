import csv
from dataclasses import replace

from tickbiterisk.etl.mast_acorn import (
    ManualMastObservation,
    MastAcornExtractionSummary,
    build_mast_acorn_from_pdf,
    parse_mast_acorn_text,
    read_manual_mast_observations,
)
from tickbiterisk.etl.mast_acorn_build import (
    MANUAL_MAST_OBSERVATION_COLUMNS,
    MAST_ACORN_COLUMNS,
    MAST_ACORN_SUMMARY_COLUMNS,
    write_manual_mast_observations_output,
    write_mast_acorn_output,
    write_mast_acorn_summary_output,
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
    assert (
        "Western Maryland Mast Survey 2021 Region: Western Maryland"
        in row.extracted_text_excerpt
    )
    assert "\n" not in row.extracted_text_excerpt
    assert len(row.extracted_text_excerpt) <= 500


def test_parse_mast_acorn_text_does_not_attribute_preamble_values() -> None:
    rows = parse_mast_acorn_text(
        """
        Western Maryland Mast Survey 2021
        Hard Mast Index: 99
        Acorn Index: 88
        County: Garrett County
        Mast Rating: sparse
        """,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )

    assert rows == []


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
    assert summary.source_path == str(pdf)


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


def test_read_manual_mast_observations_uses_sidecar_contract(tmp_path) -> None:
    input_path = tmp_path / "manual_mast.csv"
    input_path.write_text(
        "\n".join(
            [
                "county_fips,county_name,year,mast_rating,observation_basis,"
                "observer_scope,source_id,feature_quality_flags,notes",
                "2401,Allegany County,2021,poor,forester note,county,"
                "manual_mast_2021,,Low acorn availability reported.",
            ]
        ),
        encoding="utf-8",
    )

    rows = read_manual_mast_observations(input_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "02401"
    assert row.county_name == "Allegany County"
    assert row.year == 2021
    assert row.mast_rating == "poor"
    assert row.observation_basis == "forester note"
    assert row.observer_scope == "county"
    assert row.source_id == "manual_mast_2021"
    assert row.feature_quality_flags == (
        "manual_observation,anecdotal,not_official,not_model_default"
    )
    assert row.notes == "Low acorn availability reported."


def test_write_mast_acorn_output_and_summary_dedupe(tmp_path) -> None:
    rows = parse_mast_acorn_text(
        MAST_TEXT,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )
    replacement = replace(rows[0], mast_rating="good")
    output = write_mast_acorn_output(rows, tmp_path)
    output = write_mast_acorn_output([replacement], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert list(records[0].keys()) == MAST_ACORN_COLUMNS
    assert len(records) == 1
    assert records[0]["mast_rating"] == "good"

    _, summary = build_mast_acorn_from_pdf(
        tmp_path / "report.pdf",
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
        parser="pypdfium",
        text_extractor=lambda source: MAST_TEXT,
    )
    summary_output = write_mast_acorn_summary_output([summary], tmp_path)
    with summary_output.open("r", encoding="utf-8", newline="") as handle:
        summary_records = list(csv.DictReader(handle))
    assert list(summary_records[0].keys()) == MAST_ACORN_SUMMARY_COLUMNS
    assert summary_records[0]["extraction_status"] == "structured"


def test_manual_mast_observations_are_flagged_and_written(tmp_path) -> None:
    manual = tmp_path / "manual.csv"
    manual.write_text(
        "\n".join(
            [
                "county_fips,county_name,year,mast_rating,observation_basis,"
                "observer_scope,source_id,feature_quality_flags,notes",
                "24003,Anne Arundel County,2025,bumper,local resident "
                "observation of heavy acorn fall,neighborhood,manual_aa_2025,,"
                "Not official",
            ]
        ),
        encoding="utf-8",
    )

    rows = read_manual_mast_observations(manual)
    assert len(rows) == 1
    assert isinstance(rows[0], ManualMastObservation)
    assert rows[0].county_fips == "24003"
    assert rows[0].mast_rating == "bumper"
    assert rows[0].feature_quality_flags == (
        "manual_observation,anecdotal,not_official,not_model_default"
    )

    output = write_manual_mast_observations_output(rows, tmp_path)
    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert list(records[0].keys()) == MANUAL_MAST_OBSERVATION_COLUMNS
    assert records[0]["source_id"] == "manual_aa_2025"
