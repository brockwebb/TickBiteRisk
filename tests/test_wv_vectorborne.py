import csv
from pathlib import Path

from tickbiterisk.etl.wv_vectorborne import (
    parse_wv_vectorborne_report_text,
)
from tickbiterisk.etl.wv_vectorborne_build import (
    write_wv_vectorborne_state_summary,
)


def test_wv_vectorborne_report_text_extracts_table3_state_counts() -> None:
    text = """
    West Virginia Vectorborne Disease Surveillance Report
    JANUARY 1 - NOVEMBER 14, 2025

    HUMAN SURVEILLANCE - TICKBORNE DISEASE
    Through November 14, 2025, 4215 confirmed and probable cases of tickborne
    diseases (TBDs) were reported in West Virginia (Table 3).

    Table 3. Summary of human cases of tickborne diseases through November 14, 2025
                                                                  # Confirmed and Probable
                   Tickborne Disease                                                                              # of Counties Where Disease Reported
                                                              Cases through November 14, 2025
                Alpha-Gal Syndrome                                                 102                                                 18
                    Anaplasmosis                                                    51                                                 22
                     Babesiosis                                                      3                                                  3
                     Ehrlichiosis                                                   28                                                 15
                    Lyme disease                                                  4019                                                 55
          Spotted fever group rickettsiosisb                                        12                                                 10
                        Total                                                     4215                                                 --
    aTable includes only confirmed or probable cases that have been reviewed and closed by the Vectorborne Disease Epidemiologist.
    bIncludes Rocky Mountain spotted fever.
    """

    rows = parse_wv_vectorborne_report_text(
        text,
        source_id="west_virginia_oeps_vectorborne_2025_pdf",
        source_url="https://oeps.wv.gov/media/21/download?inline",
        parser_method="pypdfium_text_table3",
    )

    assert [(row.disease, row.confirmed_probable_cases, row.counties_reported) for row in rows] == [
        ("Alpha-Gal Syndrome", 102, 18),
        ("Anaplasmosis", 51, 22),
        ("Babesiosis", 3, 3),
        ("Ehrlichiosis", 28, 15),
        ("Lyme disease", 4019, 55),
        ("Spotted fever group rickettsiosis", 12, 10),
        ("Total", 4215, None),
    ]
    lyme = next(row for row in rows if row.disease == "Lyme disease")
    assert lyme.state_fips == "54"
    assert lyme.state_abbr == "WV"
    assert lyme.state_name == "West Virginia"
    assert lyme.report_year == 2025
    assert lyme.as_of_date == "2025-11-14"
    assert "wv_oeps_vectorborne_report" in lyme.feature_quality_flags
    assert "state_aggregate_validation" in lyme.feature_quality_flags
    assert "provisional_ytd_report" in lyme.feature_quality_flags
    assert "no_county_detail" in lyme.feature_quality_flags
    assert "confirmed_and_probable_cases" in lyme.feature_quality_flags
    assert "lyme_case_definition_change" in lyme.feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in lyme.feature_quality_flags


def test_wv_vectorborne_writer_outputs_stable_csv_schema(tmp_path: Path) -> None:
    rows = parse_wv_vectorborne_report_text(
        """
        West Virginia Vectorborne Disease Surveillance Report
        JANUARY 1 - OCTOBER 25, 2024
        Table 3. Summary of human cases of tickborne diseases through October 25, 2024
        Tickborne Disease # Confirmed and Probable Cases through October 25, 2024 # of Counties Where Disease Reported
        Lyme disease 2867 55
        Total 2902 --
        aTable includes only confirmed or probable cases that have been reviewed and closed by the Vectorborne Disease Epidemiologist.
        """,
        source_id="west_virginia_oeps_vectorborne_2024_pdf",
        source_url="https://oeps.wv.gov/media/20/download?inline",
        parser_method="pypdfium_text_table3",
    )

    output_path = write_wv_vectorborne_state_summary(rows, tmp_path / "out")

    assert output_path.name == "wv_vectorborne_state_summary.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert [row["disease"] for row in written] == ["Lyme disease", "Total"]
    assert written[0]["state_fips"] == "54"
    assert written[0]["confirmed_probable_cases"] == "2867"
    assert written[1]["counties_reported"] == ""
