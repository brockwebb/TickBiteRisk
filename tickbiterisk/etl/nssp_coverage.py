from __future__ import annotations

import csv
import re
import urllib.request
from dataclasses import dataclass
from io import StringIO
from pathlib import Path


CDC_NSSP_COVERAGE_CSV_URL = (
    "https://www.cdc.gov/nssp/documents/Coverage_Map_Tbl_2024Jul01.csv"
)
CDC_NSSP_ABOUT_URL = "https://www.cdc.gov/nssp/php/about/index.html"
NSSP_COVERAGE_SOURCE_ID = "cdc_nssp_coverage_2024_07_01"
NSSP_COVERAGE_AS_OF_DATE = "2024-07-01"


@dataclass(frozen=True)
class NsspCoverageRawRow:
    state_abbr: str
    county_name: str
    coverage_status: str
    coverage_status_slug: str
    recent_data_in_nssp: bool
    nssp_coverage_category: str


@dataclass(frozen=True)
class NsspCoverageCountyStatus:
    county_fips: str
    state_abbr: str
    county_name: str
    nssp_county_name: str
    nssp_coverage_status: str
    nssp_coverage_category: str
    recent_data_in_nssp: bool
    coverage_as_of_date: str
    source_id: str
    source_url: str
    feature_quality_flags: str


class NsspCoverageInputError(ValueError):
    """Raised when NSSP coverage inputs are invalid."""


def fetch_nssp_coverage_csv(
    url: str = CDC_NSSP_COVERAGE_CSV_URL,
) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "tickbiterisk-etl/0.1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def ensure_nssp_coverage_raw(
    raw_path: Path,
    *,
    coverage_url: str = CDC_NSSP_COVERAGE_CSV_URL,
    download_if_missing: bool = True,
) -> bool:
    if raw_path.exists():
        return False
    if not download_if_missing:
        raise NsspCoverageInputError(f"NSSP coverage raw file not found: {raw_path}")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        fetch_nssp_coverage_csv(coverage_url),
        encoding="utf-8",
    )
    return True


def parse_nssp_coverage_csv(csv_text: str) -> list[NsspCoverageRawRow]:
    reader = csv.DictReader(StringIO(csv_text))
    missing = {"State", "County", "Status"} - set(reader.fieldnames or [])
    if missing:
        raise NsspCoverageInputError(
            f"Missing NSSP coverage column(s): {sorted(missing)}"
        )
    rows = []
    for row in reader:
        status = str(row["Status"]).strip()
        rows.append(
            NsspCoverageRawRow(
                state_abbr=str(row["State"]).strip().upper(),
                county_name=str(row["County"]).strip(),
                coverage_status=status,
                coverage_status_slug=_slug_status(status),
                recent_data_in_nssp=status == "Recent Data in NSSP",
                nssp_coverage_category=_coverage_category(status),
            )
        )
    return rows


def build_maryland_nssp_coverage(
    raw_rows: list[NsspCoverageRawRow],
    *,
    county_reference_path: Path,
    source_id: str = NSSP_COVERAGE_SOURCE_ID,
    source_url: str = CDC_NSSP_COVERAGE_CSV_URL,
    coverage_as_of_date: str = NSSP_COVERAGE_AS_OF_DATE,
) -> list[NsspCoverageCountyStatus]:
    county_reference = _read_maryland_county_reference(county_reference_path)
    rows = []
    for row in raw_rows:
        if row.state_abbr != "MD":
            continue
        reference = county_reference.get(_county_key(row.county_name))
        if reference is None:
            raise NsspCoverageInputError(
                f"NSSP coverage county did not match Maryland reference: {row.county_name}"
            )
        rows.append(
            NsspCoverageCountyStatus(
                county_fips=reference["county_fips"],
                state_abbr=row.state_abbr,
                county_name=reference["county_name"],
                nssp_county_name=row.county_name,
                nssp_coverage_status=row.coverage_status,
                nssp_coverage_category=row.nssp_coverage_category,
                recent_data_in_nssp=row.recent_data_in_nssp,
                coverage_as_of_date=coverage_as_of_date,
                source_id=source_id,
                source_url=source_url,
                feature_quality_flags=",".join(_quality_flags(row)),
            )
        )
    return sorted(rows, key=lambda item: item.county_fips)


def _read_maryland_county_reference(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"county_fips", "state", "county_name"} - set(reader.fieldnames or [])
        if missing:
            raise NsspCoverageInputError(
                f"Missing county reference column(s): {sorted(missing)}"
            )
        return {
            _county_key(row["county_name"]): {
                "county_fips": str(row["county_fips"]).zfill(5),
                "county_name": str(row["county_name"]),
            }
            for row in reader
            if str(row["state"]).upper() == "MD"
        }


def _quality_flags(row: NsspCoverageRawRow) -> list[str]:
    flags = [
        "nssp_coverage_only_not_tick_bite_counts",
        "human_exposure_feed_feasibility_only",
    ]
    if row.coverage_status == "Recent Data in NSSP":
        flags.append("recent_ed_data_available")
    elif row.coverage_status == "No Eligible Facilities":
        flags.append("no_eligible_facilities_reported")
    elif row.coverage_status == "No Recent Data in NSSP":
        flags.append("no_recent_ed_data_reported")
    else:
        flags.append("unknown_nssp_coverage_status")
    return flags


def _coverage_category(status: str) -> str:
    if status == "Recent Data in NSSP":
        return "eligible_recent_data"
    if status == "No Recent Data in NSSP":
        return "eligible_no_recent_data"
    if status == "No Eligible Facilities":
        return "no_eligible_facilities"
    return "unknown"


def _slug_status(status: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", status.lower()).strip("_")


def _county_key(value: str) -> str:
    text = value.casefold()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "", text)
    if text.endswith("county"):
        text = text[: -len("county")]
    return text
