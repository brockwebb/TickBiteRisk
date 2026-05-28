from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from io import StringIO
from typing import Callable
from urllib.request import Request, urlopen

from tickbiterisk.etl.regional_population import (
    MIDATLANTIC_STATE_FIPS,
    MIDATLANTIC_STATES,
)


CENSUS_POP_EST_DATASETS_BASE_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets"
)
CENSUS_PEP_2019_AGE_SEX_DATASET = (
    "2010-2019/counties/asrh/cc-est2019-agesex-{state_fips}.csv"
)
CENSUS_PEP_2024_AGE_SEX_DATASET = (
    "2020-2024/counties/asrh/cc-est2024-agesex-{state_fips}.csv"
)
CENSUS_PEP_AGE_SEX_CITATION_URL = (
    "https://www.census.gov/programs-surveys/popest.html"
)
REGIONAL_AGE_DEMOGRAPHICS_QUALITY_FLAGS = (
    "population_structure_proxy,"
    "human_exposure_context_only,"
    "not_tick_bite_counts,"
    "census_vintage_revision_sensitive"
)


class RegionalDemographicsInputError(ValueError):
    """Raised when regional demographic source data are invalid."""


@dataclass(frozen=True)
class RegionalAgeDemographic:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    population: int
    under5_population: int
    age5_13_population: int
    age14_17_population: int
    age5_17_population: int
    age18_24_population: int
    age25_44_population: int
    age45_64_population: int
    age65plus_population: int
    median_age: float | None
    under5_share: float | None
    age5_17_share: float | None
    age18_24_share: float | None
    age25_44_share: float | None
    age45_64_share: float | None
    age65plus_share: float | None
    source_id: str
    census_dataset: str
    vintage: int
    source_url_hash: str
    feature_quality_flags: str


def build_midatlantic_age_sex_urls(
    *,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
) -> list[str]:
    state_fips_values = [state_fips.zfill(2) for state_fips in state_fips_list]
    return [
        *[
            _build_census_pep_2019_age_sex_url(state_fips)
            for state_fips in state_fips_values
        ],
        *[
            _build_census_pep_2024_age_sex_url(state_fips)
            for state_fips in state_fips_values
        ],
    ]


def fetch_midatlantic_age_sex_demographics(
    *,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
    text_get: Callable[[str], str] | None = None,
) -> list[RegionalAgeDemographic]:
    rows: dict[tuple[str, int], RegionalAgeDemographic] = {}
    for state_fips in [state_fips.zfill(2) for state_fips in state_fips_list]:
        url = _build_census_pep_2019_age_sex_url(state_fips)
        for row in parse_census_pep_2019_age_sex(
            _text_get(url, text_get=text_get),
            source_url=url,
        ):
            rows[(row.county_fips, row.year)] = row

        url = _build_census_pep_2024_age_sex_url(state_fips)
        for row in parse_census_pep_2024_age_sex(
            _text_get(url, text_get=text_get),
            source_url=url,
        ):
            rows[(row.county_fips, row.year)] = row

    return [
        rows[key]
        for key in sorted(
            rows,
            key=lambda item: (item[0], item[1]),
        )
    ]


def parse_census_pep_2019_age_sex(
    csv_text: str,
    *,
    source_url: str,
) -> list[RegionalAgeDemographic]:
    return _parse_age_sex_rows(
        csv_text,
        source_url=source_url,
        vintage=2019,
        source_id_prefix="census_pep_2019_county_age_sex",
        census_dataset_template=CENSUS_PEP_2019_AGE_SEX_DATASET,
        year_from_code=_pep_2019_year,
    )


def parse_census_pep_2024_age_sex(
    csv_text: str,
    *,
    source_url: str,
) -> list[RegionalAgeDemographic]:
    return _parse_age_sex_rows(
        csv_text,
        source_url=source_url,
        vintage=2024,
        source_id_prefix="census_pep_2024_county_age_sex",
        census_dataset_template=CENSUS_PEP_2024_AGE_SEX_DATASET,
        year_from_code=_pep_2024_year,
    )


def _parse_age_sex_rows(
    csv_text: str,
    *,
    source_url: str,
    vintage: int,
    source_id_prefix: str,
    census_dataset_template: str,
    year_from_code: Callable[[str], int | None],
) -> list[RegionalAgeDemographic]:
    reader = csv.DictReader(StringIO(csv_text))
    missing = _required_columns() - set(reader.fieldnames or [])
    if missing:
        raise RegionalDemographicsInputError(
            f"Missing Census age/sex column(s): {sorted(missing)}"
        )
    rows = []
    for source_row in reader:
        if source_row.get("SUMLEV") != "050":
            continue
        year = year_from_code(str(source_row["YEAR"]))
        if year is None:
            continue
        state_fips = str(source_row["STATE"]).zfill(2)
        if state_fips not in MIDATLANTIC_STATES:
            continue
        county_fips = state_fips + str(source_row["COUNTY"]).zfill(3)
        rows.append(
            _demographic_row(
                row=source_row,
                state_fips=state_fips,
                county_fips=county_fips,
                year=year,
                source_id=f"{source_id_prefix}_{state_fips}",
                census_dataset=census_dataset_template.format(
                    state_fips=state_fips
                ),
                vintage=vintage,
                source_url=source_url,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _demographic_row(
    *,
    row: dict[str, str],
    state_fips: str,
    county_fips: str,
    year: int,
    source_id: str,
    census_dataset: str,
    vintage: int,
    source_url: str,
) -> RegionalAgeDemographic:
    population = _parse_int(row["POPESTIMATE"])
    under5 = _parse_int(row["UNDER5_TOT"])
    age5_13 = _parse_int(row["AGE513_TOT"])
    age14_17 = _parse_int(row["AGE1417_TOT"])
    age5_17 = age5_13 + age14_17
    age18_24 = _parse_int(row["AGE1824_TOT"])
    age25_44 = _parse_int(row["AGE2544_TOT"])
    age45_64 = _parse_int(row["AGE4564_TOT"])
    age65plus = _parse_int(row["AGE65PLUS_TOT"])
    state_abbr, state_name = MIDATLANTIC_STATES[state_fips]
    flags = [REGIONAL_AGE_DEMOGRAPHICS_QUALITY_FLAGS]
    if population <= 0:
        flags.append("zero_or_missing_denominator")
    return RegionalAgeDemographic(
        state_fips=state_fips,
        state_abbr=state_abbr,
        state_name=state_name or row["STNAME"],
        county_fips=county_fips,
        county_name=row["CTYNAME"],
        year=year,
        population=population,
        under5_population=under5,
        age5_13_population=age5_13,
        age14_17_population=age14_17,
        age5_17_population=age5_17,
        age18_24_population=age18_24,
        age25_44_population=age25_44,
        age45_64_population=age45_64,
        age65plus_population=age65plus,
        median_age=_parse_float_or_none(row["MEDIAN_AGE_TOT"]),
        under5_share=_share(under5, population),
        age5_17_share=_share(age5_17, population),
        age18_24_share=_share(age18_24, population),
        age25_44_share=_share(age25_44, population),
        age45_64_share=_share(age45_64, population),
        age65plus_share=_share(age65plus, population),
        source_id=source_id,
        census_dataset=census_dataset,
        vintage=vintage,
        source_url_hash=_url_hash(source_url),
        feature_quality_flags=",".join(flags),
    )


def _required_columns() -> set[str]:
    return {
        "SUMLEV",
        "STATE",
        "COUNTY",
        "STNAME",
        "CTYNAME",
        "YEAR",
        "POPESTIMATE",
        "UNDER5_TOT",
        "AGE513_TOT",
        "AGE1417_TOT",
        "AGE1824_TOT",
        "AGE2544_TOT",
        "AGE4564_TOT",
        "AGE65PLUS_TOT",
        "MEDIAN_AGE_TOT",
    }


def _build_census_pep_2019_age_sex_url(state_fips: str) -> str:
    return (
        f"{CENSUS_POP_EST_DATASETS_BASE_URL}/"
        f"{CENSUS_PEP_2019_AGE_SEX_DATASET.format(state_fips=state_fips.zfill(2))}"
    )


def _build_census_pep_2024_age_sex_url(state_fips: str) -> str:
    return (
        f"{CENSUS_POP_EST_DATASETS_BASE_URL}/"
        f"{CENSUS_PEP_2024_AGE_SEX_DATASET.format(state_fips=state_fips.zfill(2))}"
    )


def _pep_2019_year(year_code: str) -> int | None:
    code = int(year_code)
    if 3 <= code <= 12:
        return 2007 + code
    return None


def _pep_2024_year(year_code: str) -> int | None:
    code = int(year_code)
    if 2 <= code <= 6:
        return 2018 + code
    return None


def _text_get(url: str, *, text_get: Callable[[str], str] | None = None) -> str:
    if text_get is not None:
        return text_get(url)
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def _share(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _parse_int(value: str) -> int:
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return 0
    return int(cleaned)


def _parse_float_or_none(value: str) -> float | None:
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return float(cleaned)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()
