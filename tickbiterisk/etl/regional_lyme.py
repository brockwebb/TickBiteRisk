from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.lyme import _frequency_to_int
from tickbiterisk.etl.lyme_aggregate import STATE_FIPS


MIDATLANTIC_STATE_NAMES = (
    "Delaware",
    "District of Columbia",
    "Maryland",
    "Pennsylvania",
    "Virginia",
    "West Virginia",
)
MIDATLANTIC_STATE_FIPS = {
    STATE_FIPS[state_name][0] for state_name in MIDATLANTIC_STATE_NAMES
}
PENNSYLVANIA_COUNTY_FIPS = {
    "Adams": "42001",
    "Allegheny": "42003",
    "Armstrong": "42005",
    "Beaver": "42007",
    "Bedford": "42009",
    "Berks": "42011",
    "Blair": "42013",
    "Bradford": "42015",
    "Bucks": "42017",
    "Butler": "42019",
    "Cambria": "42021",
    "Cameron": "42023",
    "Carbon": "42025",
    "Centre": "42027",
    "Chester": "42029",
    "Clarion": "42031",
    "Clearfield": "42033",
    "Clinton": "42035",
    "Columbia": "42037",
    "Crawford": "42039",
    "Cumberland": "42041",
    "Dauphin": "42043",
    "Delaware": "42045",
    "Elk": "42047",
    "Erie": "42049",
    "Fayette": "42051",
    "Forest": "42053",
    "Franklin": "42055",
    "Fulton": "42057",
    "Greene": "42059",
    "Huntingdon": "42061",
    "Indiana": "42063",
    "Jefferson": "42065",
    "Juniata": "42067",
    "Lackawanna": "42069",
    "Lancaster": "42071",
    "Lawrence": "42073",
    "Lebanon": "42075",
    "Lehigh": "42077",
    "Luzerne": "42079",
    "Lycoming": "42081",
    "McKean": "42083",
    "Mercer": "42085",
    "Mifflin": "42087",
    "Monroe": "42089",
    "Montgomery": "42091",
    "Montour": "42093",
    "Northampton": "42095",
    "Northumberland": "42097",
    "Perry": "42099",
    "Philadelphia": "42101",
    "Pike": "42103",
    "Potter": "42105",
    "Schuylkill": "42107",
    "Snyder": "42109",
    "Somerset": "42111",
    "Sullivan": "42113",
    "Susquehanna": "42115",
    "Tioga": "42117",
    "Union": "42119",
    "Venango": "42121",
    "Warren": "42123",
    "Washington": "42125",
    "Wayne": "42127",
    "Westmoreland": "42129",
    "Wyoming": "42131",
    "York": "42133",
}
DELAWARE_COUNTY_FIPS = {
    "KENT COUNTY": ("10001", "Kent County"),
    "NEW CASTLE COUNTY": ("10003", "New Castle County"),
    "SUSSEX COUNTY": ("10005", "Sussex County"),
}


@dataclass(frozen=True)
class RegionalLymeCountyYear:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    source_id: str
    feature_quality_flags: str


def parse_cdc_midatlantic_county_dashboard(
    path: Path,
    *,
    source_id: str,
) -> list[RegionalLymeCountyYear]:
    df = pd.read_csv(path, dtype=str, encoding="latin1")
    required = {"Ctyname", "stname", "stcode", "ctycode"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CDC county dashboard columns: {sorted(missing)}")

    year_columns = _case_year_columns(df.columns)
    if not year_columns:
        raise ValueError("No CDC county dashboard case-year columns found")

    rows: list[RegionalLymeCountyYear] = []
    for record in df.to_dict(orient="records"):
        state_name = str(record["stname"]).strip()
        if state_name not in MIDATLANTIC_STATE_NAMES:
            continue
        state_fips = f"{int(record['stcode']):02d}"
        county_fips = f"{state_fips}{int(record['ctycode']):03d}"
        _, state_abbr = STATE_FIPS[state_name]
        for column in year_columns:
            year = int(column.lower().replace("cases", ""))
            case_value = record[column]
            rows.append(
                RegionalLymeCountyYear(
                    state_fips=state_fips,
                    state_abbr=state_abbr,
                    state_name=state_name,
                    county_fips=county_fips,
                    county_name=str(record["Ctyname"]).strip(),
                    year=year,
                    total_cases=_frequency_to_int(case_value),
                    source_id=source_id,
                    feature_quality_flags=",".join(
                        _regional_quality_flags(
                            state_fips=state_fips,
                            year=year,
                            case_value=case_value,
                        )
                    ),
                )
            )
    return sorted(rows, key=lambda row: (row.state_fips, row.county_fips, row.year))


def parse_pa_doh_lyme_county_workbook(
    path: Path,
    *,
    source_id: str,
    target_year: int = 2024,
) -> list[RegionalLymeCountyYear]:
    raw = pd.read_excel(
        path,
        sheet_name="RedactedCountyCaseCounts",
        dtype=str,
        header=None,
    )
    year_column = str(target_year)
    header_index = _find_pa_header_row(raw, year_column=year_column)
    df = raw.iloc[header_index + 1 :].copy()
    df.columns = [str(column).strip() for column in raw.iloc[header_index]]
    df.columns = [str(column).strip() for column in df.columns]
    required = {"Jurisdiction", year_column}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing PA DOH Lyme workbook columns: {sorted(missing)}")

    rows: list[RegionalLymeCountyYear] = []
    for record in df.to_dict(orient="records"):
        jurisdiction = str(record.get("Jurisdiction", "")).strip()
        if not jurisdiction or jurisdiction.lower() == "nan":
            continue
        county_name = jurisdiction.removesuffix(" County")
        county_fips = PENNSYLVANIA_COUNTY_FIPS.get(county_name)
        if county_fips is None:
            continue
        case_value = record.get(year_column)
        rows.append(
            RegionalLymeCountyYear(
                state_fips="42",
                state_abbr="PA",
                state_name="Pennsylvania",
                county_fips=county_fips,
                county_name=f"{county_name} County",
                year=target_year,
                total_cases=_pa_case_value_to_int(case_value),
                source_id=source_id,
                feature_quality_flags=",".join(
                    _pa_quality_flags(year=target_year, case_value=case_value)
                ),
            )
        )
    if not rows:
        raise ValueError("No PA DOH Lyme county rows parsed from workbook")
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def parse_de_dhss_lyme_county_html(
    path: Path,
    *,
    source_id: str,
) -> list[RegionalLymeCountyYear]:
    tables = pd.read_html(path)
    table = _find_de_dhss_lyme_table(tables)
    header_index = _find_de_dhss_header_row(table)
    headers = [_normalize_de_header_cell(value) for value in table.iloc[header_index]]
    county_columns = {
        index: DELAWARE_COUNTY_FIPS[header]
        for index, header in enumerate(headers)
        if header in DELAWARE_COUNTY_FIPS
    }
    missing_counties = set(DELAWARE_COUNTY_FIPS) - {
        header for header in headers if header in DELAWARE_COUNTY_FIPS
    }
    if missing_counties:
        raise ValueError(
            "Missing Delaware DHSS Lyme county columns: "
            f"{sorted(missing_counties)}"
        )

    rows: list[RegionalLymeCountyYear] = []
    for _, record in table.iloc[header_index + 1 :].iterrows():
        year = _de_table_year(record.iloc[0])
        if year is None:
            continue
        for column_index, (county_fips, county_name) in county_columns.items():
            case_value = record.iloc[column_index]
            rows.append(
                RegionalLymeCountyYear(
                    state_fips="10",
                    state_abbr="DE",
                    state_name="Delaware",
                    county_fips=county_fips,
                    county_name=county_name,
                    year=year,
                    total_cases=_frequency_to_int(case_value),
                    source_id=source_id,
                    feature_quality_flags=",".join(
                        _de_dhss_quality_flags(year=year, case_value=case_value)
                    ),
                )
            )
    if not rows:
        raise ValueError("No Delaware DHSS Lyme county rows parsed from HTML")
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _find_de_dhss_lyme_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for table in tables:
        text = " ".join(
            _normalize_de_header_cell(value)
            for value in table.to_numpy().ravel().tolist()
        )
        if all(county in text for county in DELAWARE_COUNTY_FIPS):
            return table
    raise ValueError("Delaware DHSS Lyme county table not found")


def _find_de_dhss_header_row(df: pd.DataFrame) -> int:
    for index, row in df.iterrows():
        values = {_normalize_de_header_cell(value) for value in row}
        if "YEAR" in values and set(DELAWARE_COUNTY_FIPS).issubset(values):
            return int(index)
    raise ValueError("Delaware DHSS Lyme table header row not found")


def _normalize_de_header_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().upper().split())


def _de_table_year(value: object) -> int | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    try:
        year = int(float(text))
    except ValueError:
        return None
    if 1900 <= year <= 2100:
        return year
    return None


def _find_pa_header_row(df: pd.DataFrame, *, year_column: str) -> int:
    for index, row in df.iterrows():
        values = {str(value).strip() for value in row if not pd.isna(value)}
        if "Jurisdiction" in values and year_column in values:
            return int(index)
    raise ValueError(
        "PA DOH Lyme workbook does not contain a RedactedCountyCaseCounts "
        f"header row for {year_column}"
    )


def _case_year_columns(columns: object) -> list[str]:
    return sorted(
        [
            column
            for column in columns
            if str(column).lower().startswith("cases")
            and str(column).lower().replace("cases", "").isdigit()
        ],
        key=lambda column: int(str(column).lower().replace("cases", "")),
    )


def _regional_quality_flags(
    *,
    state_fips: str,
    year: int,
    case_value: object,
) -> list[str]:
    flags = [
        "regional_expansion_stress_test",
        "cdc_dashboard_total_cases",
        "not_public_maryland_default",
        "reported_cases_not_stable_true_incidence",
    ]
    if year == 2020:
        flags.append("covid_reporting_disruption")
    if year >= 2022:
        flags.append("lyme_case_definition_change")
    if state_fips == "11":
        flags.append("district_county_equivalent")
    if _case_value_is_suppressed_or_unknown(case_value):
        flags.append("case_value_suppressed_or_unknown")
    return flags


def _case_value_is_suppressed_or_unknown(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    return text in {"", "-", "n", "nan", "suppressed", "u"}


def _pa_quality_flags(*, year: int, case_value: object) -> list[str]:
    flags = [
        "regional_expansion_stress_test",
        "pa_doh_official_county_cases",
        "state_source_not_cdc_public_use",
        "not_public_maryland_default",
        "reported_cases_not_stable_true_incidence",
    ]
    if year >= 2022:
        flags.append("lyme_case_definition_change")
    if _pa_case_value_is_suppressed_or_unknown(case_value):
        flags.append("case_value_suppressed_or_unknown")
    return flags


def _de_dhss_quality_flags(*, year: int, case_value: object) -> list[str]:
    flags = [
        "regional_expansion_stress_test",
        "de_dhss_official_county_cases",
        "state_source_not_cdc_public_use",
        "state_source_validation_only",
        "not_public_maryland_default",
        "reported_cases_not_stable_true_incidence",
        "confirmed_and_probable_cases",
    ]
    if year == 2020:
        flags.append("covid_reporting_disruption")
    if year >= 2022:
        flags.append("lyme_case_definition_change")
    if _case_value_is_suppressed_or_unknown(case_value):
        flags.append("case_value_suppressed_or_unknown")
    return flags


def _pa_case_value_to_int(value: object) -> int:
    if _pa_case_value_is_suppressed_or_unknown(value):
        return 0
    return _frequency_to_int(value)


def _pa_case_value_is_suppressed_or_unknown(value: object) -> bool:
    if _case_value_is_suppressed_or_unknown(value):
        return True
    return str(value).strip() == "*"
