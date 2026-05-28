import csv
from pathlib import Path

from tickbiterisk.etl.regional_lyme import (
    MIDATLANTIC_STATE_FIPS,
    parse_cdc_midatlantic_county_dashboard,
)
from tickbiterisk.etl.regional_lyme_build import write_regional_lyme_output


def test_midatlantic_dashboard_parser_expands_county_year_rows_with_flags(
    tmp_path: Path,
) -> None:
    path = tmp_path / "county_dashboard.csv"
    path.write_text(
        "\n".join(
            [
                "Ctyname,stname,ststatus,stcode,ctycode,Cases2001,cases2020,cases2022,cases2023",
                "Anne Arundel County,Maryland,High Incidence,24,3,69,103,127,162",
                "Adams County,Pennsylvania,High Incidence,42,1,17,2,143,145",
                "Arlington County,Virginia,Low Incidence,51,13,2,20,38,27",
                "Berkeley County,West Virginia,Low Incidence,54,3,5,64,93,108",
                "New Castle County,Delaware,High Incidence,10,3,102,93,184,203",
                "District of Columbia,District of Columbia,Low Incidence,11,1,17,51,73,108",
                "Autauga County,Alabama,Low Incidence,1,1,0,0,0,1",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_cdc_midatlantic_county_dashboard(
        path,
        source_id="cdc_lyme_county_dashboard_2023",
    )

    assert len(rows) == len(MIDATLANTIC_STATE_FIPS) * 4
    assert (rows[0].state_abbr, rows[0].county_fips, rows[0].year) == (
        "DE",
        "10003",
        2001,
    )
    anne_arundel_2022 = next(
        row
        for row in rows
        if row.county_fips == "24003" and row.year == 2022
    )
    assert anne_arundel_2022.total_cases == 127
    assert anne_arundel_2022.county_name == "Anne Arundel County"
    assert "regional_expansion_stress_test" in anne_arundel_2022.feature_quality_flags
    assert "not_public_maryland_default" in anne_arundel_2022.feature_quality_flags
    assert "lyme_case_definition_change" in anne_arundel_2022.feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in anne_arundel_2022.feature_quality_flags

    dc_2020 = next(
        row
        for row in rows
        if row.county_fips == "11001" and row.year == 2020
    )
    assert dc_2020.state_abbr == "DC"
    assert dc_2020.county_name == "District of Columbia"
    assert "district_county_equivalent" in dc_2020.feature_quality_flags
    assert "covid_reporting_disruption" in dc_2020.feature_quality_flags


def test_midatlantic_dashboard_parser_rejects_missing_case_year_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "county_dashboard.csv"
    path.write_text(
        "\n".join(
            [
                "Ctyname,stname,ststatus,stcode,ctycode",
                "Kent County,Delaware,High Incidence,10,1",
            ]
        ),
        encoding="utf-8",
    )

    try:
        parse_cdc_midatlantic_county_dashboard(
            path,
            source_id="cdc_lyme_county_dashboard_2023",
        )
    except ValueError as exc:
        assert "No CDC county dashboard case-year columns found" in str(exc)
    else:
        raise AssertionError("Expected missing case-year columns to fail")


def test_midatlantic_dashboard_parser_flags_suppressed_or_unknown_case_values(
    tmp_path: Path,
) -> None:
    path = tmp_path / "county_dashboard.csv"
    path.write_text(
        "\n".join(
            [
                "Ctyname,stname,ststatus,stcode,ctycode,Cases2001,cases2002",
                "Kent County,Delaware,High Incidence,10,1,suppressed,u",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_cdc_midatlantic_county_dashboard(
        path,
        source_id="cdc_lyme_county_dashboard_2023",
    )

    assert [(row.year, row.total_cases) for row in rows] == [(2001, 0), (2002, 0)]
    assert all(
        "case_value_suppressed_or_unknown" in row.feature_quality_flags
        for row in rows
    )


def test_regional_lyme_writer_outputs_stable_csv_schema(tmp_path: Path) -> None:
    source_path = tmp_path / "county_dashboard.csv"
    source_path.write_text(
        "\n".join(
            [
                "Ctyname,stname,ststatus,stcode,ctycode,Cases2001",
                "Kent County,Delaware,High Incidence,10,1,22",
            ]
        ),
        encoding="utf-8",
    )
    rows = parse_cdc_midatlantic_county_dashboard(
        source_path,
        source_id="cdc_lyme_county_dashboard_2023",
    )

    output_path = write_regional_lyme_output(rows, tmp_path / "out")

    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert output_path.name == "midatlantic_lyme_county_year.csv"
    assert written == [
        {
            "state_fips": "10",
            "state_abbr": "DE",
            "state_name": "Delaware",
            "county_fips": "10001",
            "county_name": "Kent County",
            "year": "2001",
            "total_cases": "22",
            "source_id": "cdc_lyme_county_dashboard_2023",
            "feature_quality_flags": (
                "regional_expansion_stress_test,cdc_dashboard_total_cases,"
                "not_public_maryland_default,"
                "reported_cases_not_stable_true_incidence"
            ),
        }
    ]
