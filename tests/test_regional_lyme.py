import csv
from pathlib import Path

from tickbiterisk.etl.regional_lyme import (
    MIDATLANTIC_STATE_FIPS,
    parse_cdc_midatlantic_county_dashboard,
    parse_de_dhss_lyme_county_html,
    parse_pa_doh_lyme_county_workbook,
    parse_va_vdh_reportable_disease_locality_csv,
)
from tickbiterisk.etl.regional_lyme_build import (
    write_regional_lyme_output,
    write_regional_lyme_state_validation_output,
)


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


def test_pa_doh_workbook_parser_adds_2024_county_rows_with_state_source_flags(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pa_lyme.xlsx"
    _write_pa_workbook(
        path,
        [
            {"Jurisdiction": "Adams", "2024": "128", "2023": "145"},
            {"Jurisdiction": "Montour", "2024": "*", "2023": "7"},
        ],
    )

    rows = parse_pa_doh_lyme_county_workbook(
        path,
        source_id="pa_doh_lyme_1980_2024_xlsx",
        target_year=2024,
    )

    assert [(row.county_fips, row.year, row.total_cases) for row in rows] == [
        ("42001", 2024, 128),
        ("42093", 2024, 0),
    ]
    assert rows[0].state_abbr == "PA"
    assert rows[0].state_name == "Pennsylvania"
    assert rows[0].county_name == "Adams County"
    assert "pa_doh_official_county_cases" in rows[0].feature_quality_flags
    assert "state_source_not_cdc_public_use" in rows[0].feature_quality_flags
    assert "lyme_case_definition_change" in rows[0].feature_quality_flags
    assert "case_value_suppressed_or_unknown" in rows[1].feature_quality_flags


def test_de_dhss_html_parser_extracts_county_rows_as_validation_only(
    tmp_path: Path,
) -> None:
    path = tmp_path / "de_lyme.html"
    path.write_text(
        """
        <html><body>
        <h3>Lyme Disease Case Counts and Incidence Rates by Year and County, Delaware, 2019-2023</h3>
        <table>
          <tr><td></td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>INCIDENT RATE PER 100,000 POPULATION</td></tr>
          <tr><td>YEAR</td><td>NEW CASTLE COUNTY</td><td>KENT COUNTY</td><td>SUSSEX COUNTY</td><td>DELAWARE</td><td>DELAWARE</td></tr>
          <tr><td>2023</td><td>213</td><td>53</td><td>83</td><td>349</td><td>33.8</td></tr>
          <tr><td>2022</td><td>192</td><td>54</td><td>52</td><td>298</td><td>29.3</td></tr>
          <tr><td>2021</td><td>97</td><td>18</td><td>25</td><td>140</td><td>14.0</td></tr>
          <tr><td>* These data include confirmed and probable cases according to national surveillance case definitions.</td><td></td><td></td><td></td><td></td><td></td></tr>
        </table>
        </body></html>
        """,
        encoding="utf-8",
    )

    rows = parse_de_dhss_lyme_county_html(
        path,
        source_id="delaware_dhss_lyme_table",
    )

    assert len(rows) == 9
    assert [(row.county_fips, row.year, row.total_cases) for row in rows[:3]] == [
        ("10001", 2021, 18),
        ("10001", 2022, 54),
        ("10001", 2023, 53),
    ]
    new_castle_2023 = next(
        row
        for row in rows
        if row.county_fips == "10003" and row.year == 2023
    )
    assert new_castle_2023.state_abbr == "DE"
    assert new_castle_2023.state_name == "Delaware"
    assert new_castle_2023.county_name == "New Castle County"
    assert "de_dhss_official_county_cases" in new_castle_2023.feature_quality_flags
    assert "state_source_not_cdc_public_use" in new_castle_2023.feature_quality_flags
    assert "state_source_validation_only" in new_castle_2023.feature_quality_flags
    assert "confirmed_and_probable_cases" in new_castle_2023.feature_quality_flags
    assert "lyme_case_definition_change" in new_castle_2023.feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in (
        new_castle_2023.feature_quality_flags
    )


def test_va_vdh_csv_parser_adds_2024_locality_rows_with_state_source_flags(
    tmp_path: Path,
) -> None:
    path = tmp_path / "va_vdh_geography.csv"
    path.write_text(
        "\n".join(
            [
                "_id,Year,Condition,Geography Level,Geography Value,FIPS,Annual Case Count,Incidence Rate",
                "492,2024,Lyme disease,State,Virginia,NA,1420,16.2",
                "493,2024,Lyme disease,Locality,Accomack,51001,4,12",
                "493,2024,Lyme disease,Locality,Accomack,51001,4,12",
                "494,2024,Lyme disease,Locality,Accomack,51001,4,12.1",
                "495,2024,Amebiasis,Locality,Accomack,51001,0,0",
                "496,2024,Lyme disease,Locality,Alexandria,51510,8,5.2",
                "497,2023,Lyme disease,Locality,Alexandria,51510,6,3.9",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_va_vdh_reportable_disease_locality_csv(
        path,
        source_id="virginia_vdh_reportable_disease_locality_2024_csv",
        target_year=2024,
    )

    assert [(row.county_fips, row.county_name, row.total_cases) for row in rows] == [
        ("51001", "Accomack", 4),
        ("51001", "Accomack", 4),
        ("51510", "Alexandria", 8),
    ]
    alexandria = rows[2]
    assert alexandria.state_fips == "51"
    assert alexandria.state_abbr == "VA"
    assert alexandria.state_name == "Virginia"
    assert alexandria.year == 2024
    assert "va_vdh_official_locality_cases" in alexandria.feature_quality_flags
    assert "state_source_not_cdc_public_use" in alexandria.feature_quality_flags
    assert "virginia_county_or_independent_city_locality" in (
        alexandria.feature_quality_flags
    )
    assert "not_public_maryland_default" in alexandria.feature_quality_flags
    assert "lyme_case_definition_change" in alexandria.feature_quality_flags
    assert "reported_cases_not_stable_true_incidence" in (
        alexandria.feature_quality_flags
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


def test_regional_lyme_state_validation_writer_outputs_sidecar_csv(
    tmp_path: Path,
) -> None:
    path = tmp_path / "de_lyme.html"
    path.write_text(
        """
        <table>
          <tr><td></td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>CASE COUNTS</td><td>INCIDENT RATE PER 100,000 POPULATION</td></tr>
          <tr><td>YEAR</td><td>NEW CASTLE COUNTY</td><td>KENT COUNTY</td><td>SUSSEX COUNTY</td><td>DELAWARE</td><td>DELAWARE</td></tr>
          <tr><td>2023</td><td>213</td><td>53</td><td>83</td><td>349</td><td>33.8</td></tr>
        </table>
        """,
        encoding="utf-8",
    )
    rows = parse_de_dhss_lyme_county_html(
        path,
        source_id="delaware_dhss_lyme_table",
    )

    output_path = write_regional_lyme_state_validation_output(rows, tmp_path / "out")

    with output_path.open(newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    assert output_path.name == "regional_lyme_state_source_validation.csv"
    assert len(written) == 3
    assert {row["source_id"] for row in written} == {"delaware_dhss_lyme_table"}
    assert all(
        "state_source_validation_only" in row["feature_quality_flags"]
        for row in written
    )


def _write_pa_workbook(path: Path, rows: list[dict[str, str]]) -> None:
    import pandas as pd

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(
            writer,
            sheet_name="RedactedCountyCaseCounts",
            startrow=2,
            index=False,
        )
