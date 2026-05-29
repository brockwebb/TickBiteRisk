import csv
from pathlib import Path

from tickbiterisk.etl.nj_reportable_tickborne import (
    parse_nj_doh_reportable_tickborne_text,
)
from tickbiterisk.etl.nj_reportable_tickborne_build import (
    write_nj_doh_reportable_tickborne_output,
)


def test_nj_reportable_tickborne_text_extracts_allowed_disease_rows() -> None:
    text = """
    2024 New Jersey Reportable Communicable Disease Report
    10:56 Friday, August 22, 2025 1
    ( December 31, 2023 to December 28, 2024)
    Jurisdiction Disease
    Case
    Counts
    STATE TOTAL LYME DISEASE 6256
    STATE TOTAL BABESIOSIS 278
    STATE TOTAL EHRLICHIOSIS/ANAPLASMOSIS - ANAPLASMA PHAGOCYTOPHILUM (PREVIOUSLY HGE) 174
    STATE TOTAL POWASSAN 2
    ATLANTIC LYME DISEASE 152
    ATLANTIC BABESIOSIS 4
    ATLANTIC SPOTTED FEVER GROUP RICKETTSIOSIS 1
    BERGEN LYME DISEASE 414
    CAPE MAY ALPHA-GAL SYNDROME 18
    UNKNOWN LYME DISEASE 99
    ATLANTIC CAMPYLOBACTERIOSIS 36
    """

    rows = parse_nj_doh_reportable_tickborne_text(
        text,
        source_id="nj_doh_reportable_tickborne_2024_pdf",
        source_url="https://www.nj.gov/health/cd/documents/reportable_disease/web_statistics_2024.pdf",
        parser_method="pypdfium_text_reportable_rows",
    )

    assert [(row.jurisdiction, row.disease, row.case_count) for row in rows] == [
        ("STATE TOTAL", "Lyme disease", 6256),
        ("STATE TOTAL", "Babesiosis", 278),
        (
            "STATE TOTAL",
            "Ehrlichiosis/Anaplasmosis - Anaplasma phagocytophilum (previously HGE)",
            174,
        ),
        ("STATE TOTAL", "Powassan", 2),
        ("ATLANTIC", "Lyme disease", 152),
        ("ATLANTIC", "Babesiosis", 4),
        ("ATLANTIC", "Spotted fever group rickettsiosis", 1),
        ("BERGEN", "Lyme disease", 414),
        ("CAPE MAY", "Alpha-gal syndrome", 18),
    ]

    lyme = next(row for row in rows if row.jurisdiction == "ATLANTIC")
    assert lyme.state_fips == "34"
    assert lyme.state_abbr == "NJ"
    assert lyme.state_name == "New Jersey"
    assert lyme.report_year == 2024
    assert lyme.report_period_start == "2023-12-31"
    assert lyme.report_period_end == "2024-12-28"
    assert lyme.prepared_at == "2025-08-22"
    assert lyme.county_name == "Atlantic"
    assert lyme.county_fips == "34001"
    assert lyme.geography_type == "county"
    assert "nj_doh_reportable_disease_statistics" in lyme.feature_quality_flags
    assert "northeast_extension_sidecar" in lyme.feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in lyme.feature_quality_flags
    assert "not_confirmed_case_truth" in lyme.feature_quality_flags
    assert "lyme_case_definition_change" in lyme.feature_quality_flags
    assert "lyme_2022_laboratory_based_surveillance" in lyme.feature_quality_flags
    assert "not_public_default" in lyme.feature_quality_flags
    assert "not_model_input" in lyme.feature_quality_flags

    state_total = rows[0]
    assert state_total.geography_type == "state_total"
    assert state_total.county_name == ""
    assert state_total.county_fips == ""


def test_nj_reportable_tickborne_writer_outputs_stable_csv_schema(
    tmp_path: Path,
) -> None:
    rows = parse_nj_doh_reportable_tickborne_text(
        """
        2024 New Jersey Reportable Communicable Disease Report
        10:56 Friday, August 22, 2025 1
        ( December 31, 2023 to December 28, 2024)
        STATE TOTAL TULAREMIA 2
        MERCER TULAREMIA 1
        """,
        source_id="nj_doh_reportable_tickborne_2024_pdf",
        source_url="https://www.nj.gov/health/cd/documents/reportable_disease/web_statistics_2024.pdf",
        parser_method="pypdfium_text_reportable_rows",
    )

    output_path = write_nj_doh_reportable_tickborne_output(rows, tmp_path / "out")

    assert output_path.name == "nj_doh_reportable_tickborne_county_year.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert written == [
        {
            "state_fips": "34",
            "state_abbr": "NJ",
            "state_name": "New Jersey",
            "report_year": "2024",
            "report_period_start": "2023-12-31",
            "report_period_end": "2024-12-28",
            "prepared_at": "2025-08-22",
            "jurisdiction": "STATE TOTAL",
            "county_name": "",
            "county_fips": "",
            "geography_type": "state_total",
            "disease": "Tularemia",
            "case_count": "2",
            "source_id": "nj_doh_reportable_tickborne_2024_pdf",
            "source_url": "https://www.nj.gov/health/cd/documents/reportable_disease/web_statistics_2024.pdf",
            "parser_method": "pypdfium_text_reportable_rows",
            "feature_quality_flags": (
                "nj_doh_reportable_disease_statistics,northeast_extension_sidecar,"
                "state_source_not_cdc_public_use,confirmed_and_probable_cases,"
                "reported_cases_not_stable_true_incidence,not_confirmed_case_truth,"
                "not_public_default,not_model_input,"
                "low_count_public_interpretation_caution"
            ),
        },
        {
            "state_fips": "34",
            "state_abbr": "NJ",
            "state_name": "New Jersey",
            "report_year": "2024",
            "report_period_start": "2023-12-31",
            "report_period_end": "2024-12-28",
            "prepared_at": "2025-08-22",
            "jurisdiction": "MERCER",
            "county_name": "Mercer",
            "county_fips": "34021",
            "geography_type": "county",
            "disease": "Tularemia",
            "case_count": "1",
            "source_id": "nj_doh_reportable_tickborne_2024_pdf",
            "source_url": "https://www.nj.gov/health/cd/documents/reportable_disease/web_statistics_2024.pdf",
            "parser_method": "pypdfium_text_reportable_rows",
            "feature_quality_flags": (
                "nj_doh_reportable_disease_statistics,northeast_extension_sidecar,"
                "state_source_not_cdc_public_use,confirmed_and_probable_cases,"
                "reported_cases_not_stable_true_incidence,not_confirmed_case_truth,"
                "not_public_default,not_model_input,"
                "low_count_public_interpretation_caution"
            ),
        },
    ]
