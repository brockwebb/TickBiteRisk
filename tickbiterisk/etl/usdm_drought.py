from __future__ import annotations

import csv
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from io import StringIO
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USDM_COUNTY_STATISTICS_BASE_URL = "https://usdmdataservices.unl.edu/api/CountyStatistics"
USDM_FEATURE_FLAGS = "drought_monitor_retro_observed"


@dataclass(frozen=True)
class UsdmDroughtUrls:
    dsci_url: str
    severity_url: str


@dataclass(frozen=True)
class UsdmDroughtWeekly:
    county_fips: str
    county_name: str
    state: str
    map_date: date
    dsci: float
    pct_none: float | None
    pct_d0: float | None
    pct_d1: float | None
    pct_d2: float | None
    pct_d3: float | None
    pct_d4: float | None
    source_id: str
    source_url_hash: str
    feature_quality_flags: str


@dataclass(frozen=True)
class UsdmDroughtCountyYear:
    county_fips: str
    county_name: str
    year: int
    usdm_week_count: int
    usdm_dsci_mean: float | None
    usdm_dsci_max: float | None
    usdm_weeks_d0_or_worse: int
    usdm_weeks_d1_or_worse: int
    usdm_weeks_d2_or_worse: int
    usdm_tick_season_week_count: int
    usdm_tick_season_dsci_mean: float | None
    usdm_tick_season_weeks_d1_or_worse: int
    source_ids: str
    feature_quality_flags: str


def build_usdm_drought_urls(*, aoi: str, year: int) -> UsdmDroughtUrls:
    params = {
        "aoi": aoi,
        "startdate": f"1/1/{year}",
        "enddate": f"12/31/{year}",
        "statisticsType": "1",
    }
    query = urlencode(params)
    return UsdmDroughtUrls(
        dsci_url=f"{USDM_COUNTY_STATISTICS_BASE_URL}/GetDSCI?{query}",
        severity_url=(
            f"{USDM_COUNTY_STATISTICS_BASE_URL}/"
            f"GetDroughtSeverityStatisticsByAreaPercent?{query}"
        ),
    )


def fetch_usdm_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def fetch_usdm_drought_year(
    *,
    aoi: str,
    year: int,
    fetcher: Callable[[str], str] = fetch_usdm_text,
) -> list[UsdmDroughtWeekly]:
    urls = build_usdm_drought_urls(aoi=aoi, year=year)
    dsci_csv = fetcher(urls.dsci_url)
    severity_csv = fetcher(urls.severity_url)
    return parse_usdm_dsci_csv(
        dsci_csv,
        severity_csv=severity_csv,
        source_url=f"{urls.dsci_url} {urls.severity_url}",
    )


def parse_usdm_dsci_csv(
    text: str,
    *,
    severity_csv: str | None = None,
    source_url: str,
) -> list[UsdmDroughtWeekly]:
    severity_by_key = parse_usdm_severity_csv(severity_csv or "")
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows = []
    for row in _read_csv_text(text):
        county_fips = str(row["FIPS"]).strip().zfill(5)
        map_date = _parse_date(row["MapDate"])
        severity = severity_by_key.get((county_fips, map_date), {})
        rows.append(
            UsdmDroughtWeekly(
                county_fips=county_fips,
                county_name=str(row["County"]).strip(),
                state=str(row["State"]).strip(),
                map_date=map_date,
                dsci=_parse_float(row["DSCI"]),
                pct_none=_severity_float(severity, "None"),
                pct_d0=_severity_float(severity, "D0"),
                pct_d1=_severity_float(severity, "D1"),
                pct_d2=_severity_float(severity, "D2"),
                pct_d3=_severity_float(severity, "D3"),
                pct_d4=_severity_float(severity, "D4"),
                source_id="usdm_county_statistics",
                source_url_hash=source_url_hash,
                feature_quality_flags=USDM_FEATURE_FLAGS,
            )
        )
    return sorted(rows, key=lambda item: (item.county_fips, item.map_date))


def parse_usdm_severity_csv(text: str) -> dict[tuple[str, date], dict[str, str]]:
    return {
        (str(row["FIPS"]).strip().zfill(5), _parse_date(row["MapDate"])): row
        for row in _read_csv_text(text)
    }


def build_usdm_county_year_features(
    rows: list[UsdmDroughtWeekly],
) -> list[UsdmDroughtCountyYear]:
    grouped: dict[tuple[str, int], list[UsdmDroughtWeekly]] = {}
    for row in _dedupe_weekly_rows(rows):
        grouped.setdefault((row.county_fips, row.map_date.year), []).append(row)
    features = []
    for (county_fips, year), county_rows in grouped.items():
        ordered = sorted(county_rows, key=lambda row: row.map_date)
        tick_season = [row for row in ordered if 4 <= row.map_date.month <= 9]
        features.append(
            UsdmDroughtCountyYear(
                county_fips=county_fips,
                county_name=ordered[0].county_name,
                year=year,
                usdm_week_count=len(ordered),
                usdm_dsci_mean=_mean([row.dsci for row in ordered]),
                usdm_dsci_max=max(row.dsci for row in ordered) if ordered else None,
                usdm_weeks_d0_or_worse=sum(
                    1 for row in ordered if _category_or_worse(row, "d0")
                ),
                usdm_weeks_d1_or_worse=sum(
                    1 for row in ordered if _category_or_worse(row, "d1")
                ),
                usdm_weeks_d2_or_worse=sum(
                    1 for row in ordered if _category_or_worse(row, "d2")
                ),
                usdm_tick_season_week_count=len(tick_season),
                usdm_tick_season_dsci_mean=_mean([row.dsci for row in tick_season]),
                usdm_tick_season_weeks_d1_or_worse=sum(
                    1 for row in tick_season if _category_or_worse(row, "d1")
                ),
                source_ids=",".join(sorted({row.source_id for row in ordered})),
                feature_quality_flags=USDM_FEATURE_FLAGS,
            )
        )
    return sorted(features, key=lambda item: (item.county_fips, item.year))


def _dedupe_weekly_rows(rows: list[UsdmDroughtWeekly]) -> list[UsdmDroughtWeekly]:
    keyed = {(row.county_fips, row.map_date): row for row in rows}
    return sorted(keyed.values(), key=lambda item: (item.county_fips, item.map_date))


def _read_csv_text(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []
    return list(csv.DictReader(StringIO(text.lstrip("\ufeff"))))


def _parse_date(value: str) -> date:
    cleaned = str(value).strip()
    if "/" in cleaned:
        month, day, year = cleaned.split("/")
        return date(int(year), int(month), int(day))
    return date.fromisoformat(cleaned)


def _parse_float(value: str) -> float:
    return float(str(value).strip())


def _severity_float(row: dict[str, str], column: str) -> float | None:
    value = row.get(column)
    if value is None or str(value).strip() == "":
        return None
    return _parse_float(value)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _category_or_worse(row: UsdmDroughtWeekly, category: str) -> bool:
    columns_by_category = {
        "d0": ("pct_d0", "pct_d1", "pct_d2", "pct_d3", "pct_d4"),
        "d1": ("pct_d1", "pct_d2", "pct_d3", "pct_d4"),
        "d2": ("pct_d2", "pct_d3", "pct_d4"),
    }
    return any(
        (getattr(row, column) or 0) > 0
        for column in columns_by_category[category]
    )
