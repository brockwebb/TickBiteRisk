from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


CENSUS_API_ENDPOINT = "https://api.census.gov/data"
CENSUS_INTERCENSAL_1990_DATASET = "1990/pep/int_charagegroups"
CENSUS_INTERCENSAL_2000_DATASET = "2000/pep/int_population"
CENSUS_PEP_2019_DATASET = "2019/pep/population"
CENSUS_PEP_2023_CHARV_DATASET = "2023/pep/charv"


class CensusApiResponseError(RuntimeError):
    """Raised when the Census API response cannot be parsed safely."""


@dataclass(frozen=True)
class CensusCountyPopulation:
    county_fips: str
    county_name: str
    year: int
    population: int
    source_id: str
    census_dataset: str
    vintage: int
    source_url_hash: str


def get_census_api_key(env: Mapping[str, str] | None = None) -> str | None:
    source = os.environ if env is None else env
    api_key = source.get("CENSUS_API_KEY", "").strip()
    return api_key or None


def build_census_intercensal_1990_population_url(
    *, api_key: str | None = None
) -> str:
    return _build_census_url(
        CENSUS_INTERCENSAL_1990_DATASET,
        get=["POP", "YEAR", "AGEGRP", "RACE_SEX", "HISP", "STATE", "COUNTY"],
        predicates={"for": "county:*", "in": "state:24"},
        api_key=api_key,
    )


def build_census_intercensal_2000_population_url(
    *, api_key: str | None = None
) -> str:
    return _build_census_url(
        CENSUS_INTERCENSAL_2000_DATASET,
        get=["GEONAME", "POP", "DATE_", "DATE_DESC"],
        predicates={"for": "county:*", "in": "state:24"},
        api_key=api_key,
    )


def build_census_pep_2019_population_url(*, api_key: str | None = None) -> str:
    return _build_census_url(
        CENSUS_PEP_2019_DATASET,
        get=["NAME", "POP", "DATE_CODE"],
        predicates={"for": "county:*", "in": "state:24"},
        api_key=api_key,
    )


def build_census_pep_2023_charv_population_url(
    *, year: int, api_key: str | None = None
) -> str:
    return _build_census_url(
        CENSUS_PEP_2023_CHARV_DATASET,
        get=["NAME", "POP", "YEAR", "MONTH", "AGE", "SEX", "HISP", "POPGROUP"],
        predicates={
            "for": "county:*",
            "in": "state:24",
            "YEAR": str(year),
            "MONTH": "7",
            "AGE": "0000",
            "SEX": "0",
            "HISP": "0",
            "POPGROUP": "001",
        },
        api_key=api_key,
    )


def fetch_maryland_county_population_estimates(
    *,
    api_key: str | None = None,
    json_get: Callable[[str], list[list[str]]] | None = None,
) -> list[CensusCountyPopulation]:
    urls_and_parsers = [
        (
            build_census_intercensal_1990_population_url(api_key=api_key),
            lambda payload, url: parse_census_intercensal_1990_population(
                payload, source_url=url, min_year=1992, max_year=1999
            ),
        ),
        (
            build_census_intercensal_2000_population_url(api_key=api_key),
            lambda payload, url: parse_census_intercensal_2000_population(
                payload, source_url=url, min_year=2000, max_year=2009
            ),
        ),
        (
            build_census_pep_2019_population_url(api_key=api_key),
            lambda payload, url: parse_census_pep_2019_population(
                payload, source_url=url
            ),
        ),
    ]
    urls_and_parsers.extend(
        (
            build_census_pep_2023_charv_population_url(year=year, api_key=api_key),
            lambda payload, url: parse_census_pep_2023_charv_population(
                payload, source_url=url
            ),
        )
        for year in range(2020, 2024)
    )

    output: dict[tuple[str, int], CensusCountyPopulation] = {}
    for url, parser in urls_and_parsers:
        payload = _ensure_census_table(_json_get(url, json_get=json_get), url)
        for row in parser(payload, url):
            output[(row.county_fips, row.year)] = row

    return sorted(output.values(), key=lambda row: (row.county_fips, row.year))


def parse_census_intercensal_1990_population(
    payload: list[list[str]],
    *,
    source_url: str,
    min_year: int = 1990,
    max_year: int = 1999,
) -> list[CensusCountyPopulation]:
    aggregates: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in _records(payload):
        year = _intercensal_1990_year(row["YEAR"])
        if not min_year <= year <= max_year:
            continue
        state = str(row.get("state") or row.get("STATE") or "").zfill(2)
        county = str(row.get("county") or row.get("COUNTY") or "").zfill(3)
        key = (state, county, year)
        if key not in aggregates:
            aggregates[key] = {"row": row, "population": 0}
        aggregates[key]["population"] += int(row["POP"])

    records = []
    for (_state, _county, year), aggregate in aggregates.items():
        row = dict(aggregate["row"])
        row["POP"] = str(aggregate["population"])
        records.append(
            _population_row(
                row=row,
                year=year,
                population=aggregate["population"],
                source_id="census_pep_intercensal_1990_2000",
                census_dataset=CENSUS_INTERCENSAL_1990_DATASET,
                vintage=2000,
                source_url=source_url,
            )
        )
    return sorted(records, key=lambda row: (row.county_fips, row.year))


def parse_census_intercensal_2000_population(
    payload: list[list[str]],
    *,
    source_url: str,
    min_year: int = 2000,
    max_year: int = 2010,
) -> list[CensusCountyPopulation]:
    records = []
    for row in _records(payload):
        year = _year_from_date_description(row["DATE_DESC"])
        if year is None or not min_year <= year <= max_year:
            continue
        records.append(
            _population_row(
                row=row,
                year=year,
                population=int(row["POP"]),
                source_id="census_pep_intercensal_2000_2010",
                census_dataset=CENSUS_INTERCENSAL_2000_DATASET,
                vintage=2010,
                source_url=source_url,
            )
        )
    return sorted(records, key=lambda row: (row.county_fips, row.year))


def parse_census_pep_2019_population(
    payload: list[list[str]],
    *,
    source_url: str,
) -> list[CensusCountyPopulation]:
    records = []
    for row in _records(payload):
        date_code = int(row["DATE_CODE"])
        if date_code < 3:
            continue
        year = 2007 + date_code
        if not 2010 <= year <= 2019:
            continue
        records.append(
            _population_row(
                row=row,
                year=year,
                population=int(row["POP"]),
                source_id="census_pep_2019",
                census_dataset=CENSUS_PEP_2019_DATASET,
                vintage=2019,
                source_url=source_url,
            )
        )
    return sorted(records, key=lambda row: (row.county_fips, row.year))


def parse_census_pep_2023_charv_population(
    payload: list[list[str]],
    *,
    source_url: str,
) -> list[CensusCountyPopulation]:
    records = []
    for row in _records(payload):
        if (
            row.get("MONTH") != "7"
            or row.get("AGE") != "0000"
            or row.get("SEX") != "0"
            or row.get("HISP") != "0"
            or row.get("POPGROUP") != "001"
        ):
            continue
        year = int(row["YEAR"])
        records.append(
            _population_row(
                row=row,
                year=year,
                population=int(row["POP"]),
                source_id="census_pep_2023_charv",
                census_dataset=CENSUS_PEP_2023_CHARV_DATASET,
                vintage=2023,
                source_url=source_url,
            )
        )
    return sorted(records, key=lambda row: (row.county_fips, row.year))


def fetch_census_json(url: str) -> list[list[str]]:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        try:
            payload = json.loads(response.read().decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CensusApiResponseError(
                "Census API did not return JSON. Set CENSUS_API_KEY if this "
                f"endpoint requires a key. url={sanitize_census_url(url)}"
            ) from exc
    return _ensure_census_table(payload, url)


def sanitize_census_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        [
            (key, "<redacted>" if key.lower() == "key" else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _build_census_url(
    dataset: str,
    *,
    get: list[str],
    predicates: dict[str, str],
    api_key: str | None,
) -> str:
    query = [("get", ",".join(get)), *predicates.items()]
    if api_key:
        query.append(("key", api_key))
    return f"{CENSUS_API_ENDPOINT}/{dataset}?{urlencode(query)}"


def _json_get(
    url: str,
    *,
    json_get: Callable[[str], list[list[str]]] | None,
) -> list[list[str]]:
    if json_get is None:
        return fetch_census_json(url)
    return json_get(url)


def _ensure_census_table(payload: Any, url: str) -> list[list[str]]:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        raise CensusApiResponseError(
            "Census API response must be a JSON table. "
            f"url={sanitize_census_url(url)}"
        )
    return payload


def _records(payload: list[list[str]]) -> list[dict[str, str]]:
    header = payload[0]
    return [dict(zip(header, row, strict=False)) for row in payload[1:]]


def _population_row(
    *,
    row: dict[str, str],
    year: int,
    population: int,
    source_id: str,
    census_dataset: str,
    vintage: int,
    source_url: str,
) -> CensusCountyPopulation:
    county = str(row.get("county") or row.get("COUNTY") or "").zfill(3)
    state = str(row.get("state") or row.get("STATE") or "").zfill(2)
    county_fips = f"{state}{county}"
    county_name = _county_name(row)
    return CensusCountyPopulation(
        county_fips=county_fips,
        county_name=county_name,
        year=year,
        population=population,
        source_id=source_id,
        census_dataset=census_dataset,
        vintage=vintage,
        source_url_hash=_url_hash(source_url),
    )


def _county_name(row: dict[str, str]) -> str:
    name = row.get("NAME") or row.get("GEONAME") or ""
    if "," in name:
        return name.split(",", maxsplit=1)[0]
    return name


def _year_from_date_description(value: str) -> int | None:
    if "census" in value.lower() or "base" in value.lower():
        return None
    match = re.search(r"(19|20)\d{2}", value)
    if match is None:
        return None
    return int(match.group(0))


def _intercensal_1990_year(value: str) -> int:
    year = int(value)
    if 90 <= year <= 99:
        return 1900 + year
    return year


def _url_hash(source_url: str) -> str:
    return hashlib.sha256(sanitize_census_url(source_url).encode("utf-8")).hexdigest()
