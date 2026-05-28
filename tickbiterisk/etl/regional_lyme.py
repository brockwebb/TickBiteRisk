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
