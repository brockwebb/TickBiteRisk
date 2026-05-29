import csv

from tickbiterisk.etl.maine_jmmc_tickborne import (
    parse_maine_jmmc_tickborne_rates_text,
)
from tickbiterisk.etl.maine_jmmc_tickborne_build import (
    write_maine_jmmc_tickborne_rates_output,
)


def test_maine_jmmc_tickborne_rates_text_extracts_table2_rows() -> None:
    text = """
    Table 2. Rates of selected tick-borne diseases per 100 000 persons in Maine, 2024.*
    Hard tick Lyme Powassan virus
    Region Anaplasmosis Babesiosis relapsing fever disease disease
    County
    Androscoggin 36.9 15.8 0.9 133.6 0.0
    Knox 302.6 97.6 2.4 710.2 2.4
    Lincoln 438.3 79.4 0.0 698.5 2.7
    State 92.8 22.3 1.6 231.1 0.5
    *Data are preliminary as of January 20, 2025, and subject to change.
    Fig. 1. Select tick-borne disease density by county in Maine, 2010 and 2024.
    """

    rows = parse_maine_jmmc_tickborne_rates_text(
        text,
        source_id="maine_jmmc_2024_county_rates_pdf",
        source_url="https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi?article=1219&context=jmmc",
        parser_method="pypdfium_text_table2_rates",
    )

    assert [(row.region_name, row.lyme_disease_rate_per_100k) for row in rows] == [
        ("Androscoggin", 133.6),
        ("Knox", 710.2),
        ("Lincoln", 698.5),
        ("State", 231.1),
    ]
    knox = rows[1]
    assert knox.state_fips == "23"
    assert knox.state_abbr == "ME"
    assert knox.state_name == "Maine"
    assert knox.year == 2024
    assert knox.preliminary_as_of == "2025-01-20"
    assert knox.geography_type == "county"
    assert knox.county_name == "Knox"
    assert knox.county_fips == "23013"
    assert knox.anaplasmosis_rate_per_100k == 302.6
    assert knox.babesiosis_rate_per_100k == 97.6
    assert knox.hard_tick_relapsing_fever_rate_per_100k == 2.4
    assert knox.powassan_virus_disease_rate_per_100k == 2.4
    assert "external_comparator_sidecar" in knox.feature_quality_flags
    assert "maine_jmmc_review_article" in knox.feature_quality_flags
    assert "rates_only_no_case_counts" in knox.feature_quality_flags
    assert "preliminary_as_of_2025_01_20" in knox.feature_quality_flags
    assert "not_confirmed_case_truth" in knox.feature_quality_flags
    assert "not_model_input" in knox.feature_quality_flags

    state = rows[-1]
    assert state.geography_type == "state_total"
    assert state.county_name == ""
    assert state.county_fips == ""


def test_maine_jmmc_tickborne_rates_parser_requires_supported_regions() -> None:
    text = """
    Table 2. Rates of selected tick-borne diseases per 100 000 persons in Maine, 2024.*
    County
    Atlantis 1.0 2.0 3.0 4.0 5.0
    *Data are preliminary as of January 20, 2025, and subject to change.
    """

    try:
        parse_maine_jmmc_tickborne_rates_text(
            text,
            source_id="maine_jmmc_2024_county_rates_pdf",
            source_url="https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi?article=1219&context=jmmc",
            parser_method="pypdfium_text_table2_rates",
        )
    except ValueError as exc:
        assert "Unsupported Maine JMMC Table 2 region" in str(exc)
    else:
        raise AssertionError("Expected unsupported region failure")


def test_maine_jmmc_tickborne_rates_writer_outputs_stable_csv_schema(
    tmp_path,
) -> None:
    rows = parse_maine_jmmc_tickborne_rates_text(
        """
        Table 2. Rates of selected tick-borne diseases per 100 000 persons in Maine, 2024.*
        County
        Lincoln 438.3 79.4 0.0 698.5 2.7
        State 92.8 22.3 1.6 231.1 0.5
        *Data are preliminary as of January 20, 2025, and subject to change.
        """,
        source_id="maine_jmmc_2024_county_rates_pdf",
        source_url="https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi?article=1219&context=jmmc",
        parser_method="pypdfium_text_table2_rates",
    )

    output_path = write_maine_jmmc_tickborne_rates_output(rows, tmp_path / "out")

    assert output_path.name == "maine_jmmc_tickborne_county_rates_2024.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert written[0] == {
        "state_fips": "23",
        "state_abbr": "ME",
        "state_name": "Maine",
        "year": "2024",
        "preliminary_as_of": "2025-01-20",
        "region_name": "Lincoln",
        "county_name": "Lincoln",
        "county_fips": "23015",
        "geography_type": "county",
        "anaplasmosis_rate_per_100k": "438.3",
        "babesiosis_rate_per_100k": "79.4",
        "hard_tick_relapsing_fever_rate_per_100k": "0.0",
        "lyme_disease_rate_per_100k": "698.5",
        "powassan_virus_disease_rate_per_100k": "2.7",
        "source_id": "maine_jmmc_2024_county_rates_pdf",
        "source_url": "https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi?article=1219&context=jmmc",
        "parser_method": "pypdfium_text_table2_rates",
        "feature_quality_flags": (
            "maine_jmmc_review_article,external_comparator_sidecar,"
            "maine_tracking_underlying_source,rates_only_no_case_counts,"
            "preliminary_as_of_2025_01_20,"
            "reported_rates_not_stable_true_incidence,not_confirmed_case_truth,"
            "not_public_default,not_model_input"
        ),
    }
