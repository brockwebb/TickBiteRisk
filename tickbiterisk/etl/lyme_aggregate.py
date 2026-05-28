from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


STATE_FIPS = {
    "Alabama": ("01", "AL"),
    "Alaska": ("02", "AK"),
    "Arizona": ("04", "AZ"),
    "Arkansas": ("05", "AR"),
    "California": ("06", "CA"),
    "Colorado": ("08", "CO"),
    "Connecticut": ("09", "CT"),
    "Delaware": ("10", "DE"),
    "District of Columbia": ("11", "DC"),
    "Florida": ("12", "FL"),
    "Georgia": ("13", "GA"),
    "Idaho": ("16", "ID"),
    "Illinois": ("17", "IL"),
    "Indiana": ("18", "IN"),
    "Iowa": ("19", "IA"),
    "Kansas": ("20", "KS"),
    "Kentucky": ("21", "KY"),
    "Louisiana": ("22", "LA"),
    "Maine": ("23", "ME"),
    "Maryland": ("24", "MD"),
    "Massachusetts": ("25", "MA"),
    "Michigan": ("26", "MI"),
    "Minnesota": ("27", "MN"),
    "Mississippi": ("28", "MS"),
    "Missouri": ("29", "MO"),
    "Montana": ("30", "MT"),
    "Nebraska": ("31", "NE"),
    "Nevada": ("32", "NV"),
    "New Hampshire": ("33", "NH"),
    "New Jersey": ("34", "NJ"),
    "New Mexico": ("35", "NM"),
    "New York": ("36", "NY"),
    "North Carolina": ("37", "NC"),
    "North Dakota": ("38", "ND"),
    "Ohio": ("39", "OH"),
    "Oklahoma": ("40", "OK"),
    "Oregon": ("41", "OR"),
    "Pennsylvania": ("42", "PA"),
    "Rhode Island": ("44", "RI"),
    "South Carolina": ("45", "SC"),
    "South Dakota": ("46", "SD"),
    "Tennessee": ("47", "TN"),
    "Texas": ("48", "TX"),
    "Utah": ("49", "UT"),
    "Vermont": ("50", "VT"),
    "Virginia": ("51", "VA"),
    "Washington": ("53", "WA"),
    "West Virginia": ("54", "WV"),
    "Wisconsin": ("55", "WI"),
    "Wyoming": ("56", "WY"),
}


@dataclass(frozen=True)
class LymeAggregateValue:
    geography_type: str
    geography_id: str
    geography_name: str
    year: int
    value: float | int
    source_id: str


@dataclass(frozen=True)
class LymeAggregateObservation:
    geography_type: str
    geography_id: str
    geography_name: str
    year: int
    cases: int | None
    incidence_per_100k: float | None
    cases_source_id: str
    rate_source_id: str
    feature_quality_flags: str


def parse_cdc_lyme_aggregate_cases(
    path: Path,
    *,
    source_id: str,
    geography_type: str,
) -> list[LymeAggregateValue]:
    rows = _read_csv(path)
    if geography_type == "state":
        return _parse_state_case_rows(rows, source_id)
    geography_column = _geography_column(geography_type)
    return [
        LymeAggregateValue(
            geography_type=geography_type,
            geography_id=_geography_id(geography_type, row[geography_column]),
            geography_name=_geography_name(geography_type, row[geography_column]),
            year=_parse_int(row["Year"]),
            value=_parse_int(row["Cases"]),
            source_id=source_id,
        )
        for row in rows
    ]


def parse_cdc_lyme_aggregate_rates(
    path: Path,
    *,
    source_id: str,
    geography_type: str,
) -> list[LymeAggregateValue]:
    rows = _read_csv(path)
    geography_column = _geography_column(geography_type)
    value_column = _rate_column(rows)
    return [
        LymeAggregateValue(
            geography_type=geography_type,
            geography_id=_geography_id(geography_type, row[geography_column]),
            geography_name=_geography_name(geography_type, row[geography_column]),
            year=_parse_int(row["Year"]),
            value=_parse_float(row[value_column]),
            source_id=source_id,
        )
        for row in rows
        if _include_geography(geography_type, row[geography_column])
    ]


def build_aggregate_observations(
    *,
    case_rows: list[LymeAggregateValue],
    rate_rows: list[LymeAggregateValue],
) -> list[LymeAggregateObservation]:
    cases_by_key = {_aggregate_key(row): row for row in case_rows}
    rates_by_key = {_aggregate_key(row): row for row in rate_rows}
    keys = sorted(cases_by_key.keys() | rates_by_key.keys())
    output = []
    for key in keys:
        case_row = cases_by_key.get(key)
        rate_row = rates_by_key.get(key)
        row = case_row or rate_row
        if row is None:
            continue
        cases = int(case_row.value) if case_row is not None else None
        rate = float(rate_row.value) if rate_row is not None else None
        output.append(
            LymeAggregateObservation(
                geography_type=row.geography_type,
                geography_id=row.geography_id,
                geography_name=row.geography_name,
                year=row.year,
                cases=cases,
                incidence_per_100k=rate,
                cases_source_id=case_row.source_id if case_row is not None else "",
                rate_source_id=rate_row.source_id if rate_row is not None else "",
                feature_quality_flags=",".join(
                    _aggregate_quality_flags(row, cases=cases, rate=rate)
                ),
            )
        )
    return output


def _parse_state_case_rows(
    rows: list[dict[str, str]],
    source_id: str,
) -> list[LymeAggregateValue]:
    output = []
    for row in rows:
        state_name = _clean_geography_name(row["State"])
        if not _include_geography("state", state_name):
            continue
        state_fips, _ = STATE_FIPS[state_name]
        for column, value in row.items():
            if not column.isdigit() or not str(value).strip():
                continue
            output.append(
                LymeAggregateValue(
                    geography_type="state",
                    geography_id=state_fips,
                    geography_name=state_name,
                    year=int(column),
                    value=_parse_int(value),
                    source_id=source_id,
                )
            )
    return sorted(output, key=lambda row: (row.geography_id, row.year))


def _aggregate_quality_flags(
    row: LymeAggregateValue,
    *,
    cases: int | None,
    rate: float | None,
) -> list[str]:
    flags = [
        "aggregate_validation_anchor",
        "no_county_detail",
        "reported_cases_not_stable_true_incidence",
    ]
    if row.year == 2020:
        flags.append("covid_reporting_disruption")
    if row.year >= 2022:
        flags.append("lyme_case_definition_change")
    if cases is None:
        flags.append("missing_cases")
    if rate is None:
        flags.append("missing_rate")
    if row.geography_type == "region":
        flags.append("regional_capacity_anchor")
    elif row.geography_type == "national":
        flags.append("national_context_anchor")
    else:
        flags.append("state_capacity_anchor")
    return flags


def _aggregate_key(row: LymeAggregateValue) -> tuple[str, str, int]:
    return (row.geography_type, row.geography_id, row.year)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding=_csv_encoding(path), newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_encoding(path: Path) -> str:
    try:
        path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return "latin1"
    return "utf-8-sig"


def _geography_column(geography_type: str) -> str:
    if geography_type == "state":
        return "State"
    if geography_type == "region":
        return "Region"
    if geography_type == "national":
        return "Year"
    raise ValueError(f"Unsupported aggregate geography type: {geography_type}")


def _geography_id(geography_type: str, value: str) -> str:
    if geography_type == "state":
        return STATE_FIPS[_clean_geography_name(value)][0]
    if geography_type == "national":
        return "US"
    return _slug(_clean_geography_name(value))


def _geography_name(geography_type: str, value: str) -> str:
    if geography_type == "national":
        return "United States"
    return _clean_geography_name(value)


def _include_geography(geography_type: str, value: str) -> bool:
    if geography_type != "state":
        return True
    return _clean_geography_name(value) in STATE_FIPS


def _rate_column(rows: list[dict[str, str]]) -> str:
    fieldnames = rows[0].keys() if rows else []
    for column in ("Rates", "Rate", "Incidence"):
        if column in fieldnames:
            return column
    raise ValueError("CDC Lyme aggregate rate column not found")


def _clean_geography_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z .'-]", "", str(value)).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _parse_int(value: str) -> int:
    return int(str(value).replace(",", "").strip())


def _parse_float(value: str) -> float:
    return float(str(value).replace(",", "").strip())
