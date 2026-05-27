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

DNR_ROLLING_TABLE_TEXT = """
Western Maryland Mast Survey Summary 2021
Results
Quantitative Assessment
2017 2018 2019 2020 2021
GARRETT
Black Oak 11.48 0.00 0.00 0.00 17.02
White Oak 4.45 2.78 0.00 4.60 6.80
Unit Average 7.90 1.39 0.00 0.57 11.91
ALLEGANY
Black Oak 16.40 7.35 22.33 0.75 1.97
White Oak 8.90 8.45 1.43 14.77 1.90
Unit Average 12.65 7.90 11.88 7.76 1.92
WASHINGTON
Black Oak 10.20 7.28 12.93 71.80 5.75
White Oak 9.40 2.05 1.38 0.00 4.30
Unit Average 9.80 4.66 7.15 8.98 5.04
FREDERICK
Black Oak 7.25 1.25 4.28 3.25 2.65
White Oak 4.80 0.00 0.00 0.00 0.00
Unit Average 6.04 0.63 2.13 1.63 1.31
Table 1: Quantitative assessment of acorn abundance expressed as an average number of
acorns per branch (2017 - 2021).
To more easily see the range of annual variations, annual mast yields are classified according
to the following rating system.
I - Mast Failure
II - Poor and Spotty
III - Average
IV - Abundant
V - Bumper Crop
2017 2018 2019 2020 2021
GARRETT
Black Oak II I I I II
White Oak I I I I II
Unit Average II I I I II
ALLEGANY
Black Oak II I III I I
White Oak II II I III I
Unit Average III II II II I
WASHINGTON
Black Oak II I II V I
White Oak II I I I I
Unit Average II I I II I
FREDERICK
Black Oak I I I I I
White Oak I I I I I
Unit Average I I I I I
Table 2: Mast Abundance Ratings (2017 - 2021).
Subjective Assessment
2017 2018 2019 2020 2021
White Oak Group Black Oak Group White Oak Group Black Oak Group White Oak Group
Black Oak Group White Oak Group Black Oak Group White Oak Group Black Oak Group
Garrett
County 3.38% 12.13% 1.88% 0.00% 0.00% 0.00% 1.00% 0.00% 22.87% 34.87%
Allegany
County 34.75% 36.00% 32.13% 25.75% 4.00% 54.50% 1.75% 34.00% 3.75% 1.45%
Washington
County 6.75% 8.25% 1.50% 2.38% 0.50% 5.13% 0.00% 13.62% 1.62% 2.62%
Frederick
County 15.25% 21.00% 0.00% 3.25% 0.00% 8.88% 0.00% 7.75% 0.00% 5.75%
Table 3: Subjective Assessment (2017-2021).
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


def test_parse_mast_acorn_text_extracts_dnr_rolling_county_tables() -> None:
    rows = parse_mast_acorn_text(
        DNR_ROLLING_TABLE_TEXT,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )

    assert len(rows) == 20
    garrett_2021 = next(
        row
        for row in rows
        if row.county_fips == "24023" and row.year == 2021
    )
    assert garrett_2021.county_name == "Garrett County"
    assert garrett_2021.source_report_year == 2021
    assert garrett_2021.mast_category == "oak_acorn_abundance"
    assert garrett_2021.mast_index == 11.91
    assert garrett_2021.acorn_index == 11.91
    assert garrett_2021.hard_mast_index == 11.91
    assert garrett_2021.black_oak_acorns_per_branch == 17.02
    assert garrett_2021.white_oak_acorns_per_branch == 6.80
    assert garrett_2021.unit_average_acorns_per_branch == 11.91
    assert garrett_2021.black_oak_mast_rating == "II"
    assert garrett_2021.white_oak_mast_rating == "II"
    assert garrett_2021.unit_average_mast_rating == "II"
    assert garrett_2021.mast_rating == "poor_and_spotty"
    assert garrett_2021.white_oak_subjective_crown_pct == 22.87
    assert garrett_2021.black_oak_subjective_crown_pct == 34.87
    assert garrett_2021.parser_method == "table_text"
    assert garrett_2021.extraction_confidence == "high"
    assert garrett_2021.feature_quality_flags == (
        "western_maryland_only,study_plot_not_countywide"
    )

    frederick_2017 = next(
        row
        for row in rows
        if row.county_fips == "24021" and row.year == 2017
    )
    assert frederick_2017.black_oak_acorns_per_branch == 7.25
    assert frederick_2017.white_oak_subjective_crown_pct == 15.25


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
    assert rows[0].source_report_year == 2021
    assert rows[0].parser_method == "pypdfium_county_block_text"


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


def test_build_mast_acorn_from_pdf_annotates_table_parser_outputs(tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    rows, summary = build_mast_acorn_from_pdf(
        pdf,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
        parser="pypdfium",
        text_extractor=lambda source: DNR_ROLLING_TABLE_TEXT,
    )

    assert len(rows) == 20
    assert {row.parser_method for row in rows} == {"pypdfium_table_text"}
    assert {row.extraction_confidence for row in rows} == {"high"}
    assert summary.extraction_status == "structured"
    assert summary.structured_row_count == 20
    assert summary.feature_quality_flags == (
        "western_maryland_only,study_plot_not_countywide"
    )


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
