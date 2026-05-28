from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Callable
from urllib.request import Request, urlopen

from tickbiterisk.etl.census_population import _url_hash


MIDATLANTIC_STATES = {
    "10": ("DE", "Delaware"),
    "11": ("DC", "District of Columbia"),
    "24": ("MD", "Maryland"),
    "42": ("PA", "Pennsylvania"),
    "51": ("VA", "Virginia"),
    "54": ("WV", "West Virginia"),
}
MIDATLANTIC_STATE_FIPS = tuple(MIDATLANTIC_STATES)
CENSUS_INTERCENSAL_2000_COUNTY_DATASET = (
    "2000-2010/intercensal/county/co-est00int-alldata-{state_fips}.csv"
)
CENSUS_PEP_2019_COUNTY_TOTALS_DATASET = (
    "2010-2019/counties/totals/co-est2019-alldata.csv"
)
CENSUS_PEP_2023_COUNTY_TOTALS_DATASET = (
    "2020-2023/counties/totals/co-est2023-alldata.csv"
)
CENSUS_POP_EST_DATASETS_BASE_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets"
)
REGIONAL_POPULATION_QUALITY_FLAGS = (
    "regional_population_denominator,"
    "census_population_estimate,"
    "vintage_revision_sensitive,"
    "not_exposure_evidence"
)


@dataclass(frozen=True)
class RegionalCountyPopulation:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    population: int
    source_id: str
    census_dataset: str
    vintage: int
    source_url_hash: str
    feature_quality_flags: str


def build_midatlantic_population_urls(
    *,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
    api_key: str | None = None,
) -> list[str]:
    _ = api_key
    return [
        *[
            build_census_intercensal_2000_county_totals_url(state_fips)
            for state_fips in state_fips_list
        ],
        build_census_pep_2019_county_totals_url(),
        build_census_pep_2023_county_totals_url(),
    ]


def build_census_intercensal_2000_county_totals_url(state_fips: str) -> str:
    dataset = CENSUS_INTERCENSAL_2000_COUNTY_DATASET.format(
        state_fips=state_fips.zfill(2)
    )
    return f"{CENSUS_POP_EST_DATASETS_BASE_URL}/{dataset}"


def build_census_pep_2019_county_totals_url() -> str:
    return f"{CENSUS_POP_EST_DATASETS_BASE_URL}/{CENSUS_PEP_2019_COUNTY_TOTALS_DATASET}"


def build_census_pep_2023_county_totals_url() -> str:
    return f"{CENSUS_POP_EST_DATASETS_BASE_URL}/{CENSUS_PEP_2023_COUNTY_TOTALS_DATASET}"


def fetch_midatlantic_county_population_estimates(
    *,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
    api_key: str | None = None,
    text_get: Callable[[str], str] | None = None,
    min_year: int = 2001,
    max_year: int = 2023,
) -> list[RegionalCountyPopulation]:
    _ = api_key
    output: dict[tuple[str, int], RegionalCountyPopulation] = {}
    for state_fips in state_fips_list:
        url = build_census_intercensal_2000_county_totals_url(state_fips)
        for row in parse_census_intercensal_2000_county_totals(
            _text_get(url, text_get=text_get),
            source_url=url,
        ):
            if min_year <= row.year <= max_year:
                output[(row.county_fips, row.year)] = row

    url = build_census_pep_2019_county_totals_url()
    for row in parse_census_pep_2019_county_totals(
        _text_get(url, text_get=text_get),
        source_url=url,
        state_fips_list=state_fips_list,
    ):
        if min_year <= row.year <= max_year:
            output[(row.county_fips, row.year)] = row

    url = build_census_pep_2023_county_totals_url()
    for row in parse_census_pep_2023_county_totals(
        _text_get(url, text_get=text_get),
        source_url=url,
        state_fips_list=state_fips_list,
    ):
        if min_year <= row.year <= max_year:
            output[(row.county_fips, row.year)] = row

    return [
        output[key]
        for key in sorted(
            output,
            key=lambda key: (key[0], key[1]),
        )
    ]


def parse_census_intercensal_2000_county_totals(
    csv_text: str,
    *,
    source_url: str,
) -> list[RegionalCountyPopulation]:
    rows = []
    for row in csv.DictReader(StringIO(csv_text)):
        if row.get("SUMLEV") != "050" or row.get("AGEGRP") != "99":
            continue
        year = _intercensal_2000_static_year(row["YEAR"])
        if year is None:
            continue
        rows.append(
            _population_row(
                state_fips=row["STATE"],
                state_name=row["STNAME"],
                county_fips=row["STATE"].zfill(2) + row["COUNTY"].zfill(3),
                county_name=row["CTYNAME"],
                year=year,
                population=int(row["TOT_POP"]),
                source_id="census_pep_intercensal_2000_2010_static",
                census_dataset=CENSUS_INTERCENSAL_2000_COUNTY_DATASET.format(
                    state_fips=row["STATE"].zfill(2)
                ),
                vintage=2010,
                source_url=source_url,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def parse_census_pep_2019_county_totals(
    csv_text: str,
    *,
    source_url: str,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
) -> list[RegionalCountyPopulation]:
    state_filter = {state_fips.zfill(2) for state_fips in state_fips_list}
    rows = []
    for row in csv.DictReader(StringIO(csv_text)):
        if row.get("SUMLEV") != "050" or row.get("STATE", "").zfill(2) not in state_filter:
            continue
        for year in range(2010, 2020):
            rows.append(
                _population_row(
                    state_fips=row["STATE"],
                    state_name=row["STNAME"],
                    county_fips=row["STATE"].zfill(2) + row["COUNTY"].zfill(3),
                    county_name=row["CTYNAME"],
                    year=year,
                    population=int(row[f"POPESTIMATE{year}"]),
                    source_id="census_pep_2019_county_totals",
                    census_dataset=CENSUS_PEP_2019_COUNTY_TOTALS_DATASET,
                    vintage=2019,
                    source_url=source_url,
                )
            )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def parse_census_pep_2023_county_totals(
    csv_text: str,
    *,
    source_url: str,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
) -> list[RegionalCountyPopulation]:
    state_filter = {state_fips.zfill(2) for state_fips in state_fips_list}
    rows = []
    for row in csv.DictReader(StringIO(csv_text)):
        if row.get("SUMLEV") != "050" or row.get("STATE", "").zfill(2) not in state_filter:
            continue
        for year in range(2020, 2024):
            rows.append(
                _population_row(
                    state_fips=row["STATE"],
                    state_name=row["STNAME"],
                    county_fips=row["STATE"].zfill(2) + row["COUNTY"].zfill(3),
                    county_name=row["CTYNAME"],
                    year=year,
                    population=int(row[f"POPESTIMATE{year}"]),
                    source_id="census_pep_2023_county_totals",
                    census_dataset=CENSUS_PEP_2023_COUNTY_TOTALS_DATASET,
                    vintage=2023,
                    source_url=source_url,
                )
            )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _population_row(
    *,
    state_fips: str,
    state_name: str,
    county_fips: str,
    county_name: str,
    year: int,
    population: int,
    source_id: str,
    census_dataset: str,
    vintage: int,
    source_url: str,
) -> RegionalCountyPopulation:
    state_fips = state_fips.zfill(2)
    state_abbr = MIDATLANTIC_STATES[state_fips][0]
    return RegionalCountyPopulation(
        state_fips=state_fips,
        state_abbr=state_abbr,
        state_name=state_name,
        county_fips=county_fips,
        county_name=county_name,
        year=year,
        population=population,
        source_id=source_id,
        census_dataset=census_dataset,
        vintage=vintage,
        source_url_hash=_url_hash(source_url),
        feature_quality_flags=REGIONAL_POPULATION_QUALITY_FLAGS,
    )


def _intercensal_2000_static_year(year_code: str) -> int | None:
    code = int(year_code)
    if 3 <= code <= 11:
        return 1998 + code
    return None


def _text_get(
    url: str,
    *,
    text_get: Callable[[str], str] | None,
) -> str:
    if text_get is not None:
        return text_get(url)
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("latin-1")
