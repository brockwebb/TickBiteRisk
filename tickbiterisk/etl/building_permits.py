from __future__ import annotations

import csv
import hashlib
import time
from dataclasses import dataclass
from urllib.request import Request, urlopen


CENSUS_BPS_COUNTY_BASE_URL = "https://www2.census.gov/econ/bps/County"
MARYLAND_STATE_FIPS = "24"


@dataclass(frozen=True)
class CensusBuildingPermitCountyYear:
    county_fips: str
    county_name: str
    year: int
    month: int
    one_unit_units: int
    two_unit_units: int
    three_four_unit_units: int
    five_plus_unit_units: int
    total_units_authorized: int
    total_value_dollars: int
    source_id: str
    source_url_hash: str


def build_census_bps_county_annual_url(year: int) -> str:
    if year < 2000 or year > 2025:
        raise ValueError(
            "Census BPS county annual ASCII files are supported for 2000-2025"
        )
    return f"{CENSUS_BPS_COUNTY_BASE_URL}/co{year % 100:02d}12y.txt"


def source_id_from_census_bps_year(year: int) -> str:
    return f"census_bps_county_{year}"


def fetch_census_bps_county_text(
    url: str,
    *,
    attempts: int = 3,
    timeout_seconds: int = 60,
    retry_delay_seconds: float = 1,
) -> str:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("latin1")
        except OSError:
            if attempt == attempts - 1:
                raise
            if retry_delay_seconds:
                time.sleep(retry_delay_seconds)

    raise RuntimeError("unreachable")


def parse_census_bps_county_text(
    text: str,
    *,
    source_url: str,
    source_id: str,
) -> list[CensusBuildingPermitCountyYear]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows = []
    for record in csv.reader(text.splitlines()):
        if not record or not record[0].isdigit():
            continue
        if len(record) < 18:
            continue
        state_fips = record[1].zfill(2)
        if state_fips != MARYLAND_STATE_FIPS:
            continue
        survey_date = record[0]
        year = int(survey_date[:4])
        month = int(survey_date[4:6])
        one_unit_units = _parse_int(record[7])
        two_unit_units = _parse_int(record[10])
        three_four_unit_units = _parse_int(record[13])
        five_plus_unit_units = _parse_int(record[16])
        rows.append(
            CensusBuildingPermitCountyYear(
                county_fips=f"{state_fips}{record[2].zfill(3)}",
                county_name=record[5].strip(),
                year=year,
                month=month,
                one_unit_units=one_unit_units,
                two_unit_units=two_unit_units,
                three_four_unit_units=three_four_unit_units,
                five_plus_unit_units=five_plus_unit_units,
                total_units_authorized=(
                    one_unit_units
                    + two_unit_units
                    + three_four_unit_units
                    + five_plus_unit_units
                ),
                total_value_dollars=(
                    _parse_int(record[8])
                    + _parse_int(record[11])
                    + _parse_int(record[14])
                    + _parse_int(record[17])
                ),
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _parse_int(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return 0
    return int(cleaned)
