from pathlib import Path

from tickbiterisk.etl.lyme_aggregate import (
    build_aggregate_observations,
    parse_cdc_lyme_aggregate_cases,
    parse_cdc_lyme_aggregate_rates,
)


def test_state_caseincid_parser_cleans_footnotes_and_skips_us_total(tmp_path: Path):
    path = tmp_path / "state_cases.csv"
    path.write_text(
        "\n".join(
            [
                "State,2008,2009,2022",
                "Maryland\u2020,\"1,200\",1300,2400",
                "Pennsylvania\u2020,5000,5100,6200",
                "U.S. Total,10000,12000,30000",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_cdc_lyme_aggregate_cases(
        path,
        source_id="cdc_caseincid_cases_state_2023",
        geography_type="state",
    )

    assert [(row.geography_id, row.geography_name, row.year, row.value) for row in rows] == [
        ("24", "Maryland", 2008, 1200),
        ("24", "Maryland", 2009, 1300),
        ("24", "Maryland", 2022, 2400),
        ("42", "Pennsylvania", 2008, 5000),
        ("42", "Pennsylvania", 2009, 5100),
        ("42", "Pennsylvania", 2022, 6200),
    ]


def test_aggregate_builder_merges_cases_and_rates_with_flags(tmp_path: Path):
    cases_path = tmp_path / "region_cases.csv"
    rates_path = tmp_path / "region_rates.csv"
    cases_path.write_text(
        "\n".join(
            [
                "Year,Region,Cases",
                "2020,South Atlantic,100",
                "2022,South Atlantic,150",
            ]
        ),
        encoding="utf-8",
    )
    rates_path.write_text(
        "\n".join(
            [
                "Year,Region,Rate",
                "2022,South Atlantic,1.5",
            ]
        ),
        encoding="utf-8",
    )

    rows = build_aggregate_observations(
        case_rows=parse_cdc_lyme_aggregate_cases(
            cases_path,
            source_id="cdc_caseincid_cases_region_2023",
            geography_type="region",
        ),
        rate_rows=parse_cdc_lyme_aggregate_rates(
            rates_path,
            source_id="cdc_caseincid_rates_region_2023",
            geography_type="region",
        ),
    )

    assert [(row.year, row.cases, row.incidence_per_100k) for row in rows] == [
        (2020, 100, None),
        (2022, 150, 1.5),
    ]
    assert rows[0].feature_quality_flags == (
        "aggregate_validation_anchor,no_county_detail,"
        "reported_cases_not_stable_true_incidence,"
        "covid_reporting_disruption,missing_rate,regional_capacity_anchor"
    )
    assert rows[1].feature_quality_flags == (
        "aggregate_validation_anchor,no_county_detail,"
        "reported_cases_not_stable_true_incidence,"
        "lyme_case_definition_change,regional_capacity_anchor"
    )


def test_national_aggregate_parser_labels_united_states(tmp_path: Path):
    path = tmp_path / "national_cases.csv"
    path.write_text("\n".join(["Year,Cases", "2022,8000"]), encoding="utf-8")

    rows = parse_cdc_lyme_aggregate_cases(
        path,
        source_id="cdc_caseincid_overall_cases_2023",
        geography_type="national",
    )

    assert rows[0].geography_id == "US"
    assert rows[0].geography_name == "United States"
