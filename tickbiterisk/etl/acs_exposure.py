from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from tickbiterisk.etl.county_reference import (
    CENSUS_GAZETTEER_COUNTIES_2024_URL,
)
from tickbiterisk.etl.regional_population import (
    MIDATLANTIC_STATE_FIPS,
    MIDATLANTIC_STATES,
)


ACS_TABLE_BASED_SUMMARY_FILE_CITATION_URL = (
    "https://www.census.gov/programs-surveys/acs/data/summary-file.html"
)
ACS_TABLE_BASED_BASE_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file"
)
ACS_EXPOSURE_TABLES = ("b01001", "b25024", "b25003")
ACS_EXPOSURE_QUALITY_FLAGS = (
    "acs_5yr_rolling_window,"
    "exposure_proxy_only,"
    "not_exposure_evidence,"
    "not_tick_bite_counts,"
    "not_lyme_outcome,"
    "not_disease_truth,"
    "not_public_default,"
    "density_proxy_from_static_land_area"
)


class AcsExposureInputError(ValueError):
    """Raised when ACS exposure source data are invalid."""


@dataclass(frozen=True)
class AcsExposureSourceUrls:
    year: int
    geography_url: str
    table_urls: dict[str, str]
    gazetteer_url: str

    @property
    def all_urls(self) -> list[str]:
        return [
            self.geography_url,
            *[self.table_urls[table] for table in ACS_EXPOSURE_TABLES],
            self.gazetteer_url,
        ]


@dataclass(frozen=True)
class AcsExposureCountyYear:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    acs_total_population: int | None
    age_under_18_population: int | None
    age_18_64_population: int | None
    age_65_plus_population: int | None
    age_under_18_share: float | None
    age_18_64_share: float | None
    age_65_plus_share: float | None
    total_housing_units: int | None
    single_family_detached_units: int | None
    single_family_attached_units: int | None
    single_family_units: int | None
    single_family_detached_share: float | None
    single_family_share: float | None
    occupied_housing_units: int | None
    owner_occupied_units: int | None
    owner_occupied_share: float | None
    land_area_sqmi: float | None
    population_per_sqmi: float | None
    housing_units_per_sqmi: float | None
    single_family_units_per_sqmi: float | None
    source_id: str
    census_dataset: str
    vintage: int
    acs_source_url_hash: str
    geography_source_url_hash: str
    feature_quality_flags: str


@dataclass(frozen=True)
class _AcsGeography:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    geo_id: str


def build_acs_exposure_source_urls(year: int = 2024) -> AcsExposureSourceUrls:
    if year < 2023 or year > 2024:
        raise AcsExposureInputError("ACS table-based source URLs support 2023-2024")
    return AcsExposureSourceUrls(
        year=year,
        geography_url=(
            f"{ACS_TABLE_BASED_BASE_URL}/{year}/table-based-SF/"
            f"documentation/Geos{year}5YR.txt"
        ),
        table_urls={
            table: (
                f"{ACS_TABLE_BASED_BASE_URL}/{year}/table-based-SF/"
                f"data/5YRData/acsdt5y{year}-{table}.dat"
            )
            for table in ACS_EXPOSURE_TABLES
        },
        gazetteer_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
    )


def materialize_acs_exposure_sources(
    raw_dir: Path,
    *,
    year: int = 2024,
    download_if_missing: bool = True,
) -> dict[str, Path]:
    urls = build_acs_exposure_source_urls(year=year)
    output_dir = raw_dir / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "geography": output_dir / Path(urls.geography_url).name,
        **{
            table: output_dir / Path(url).name
            for table, url in urls.table_urls.items()
        },
        "gazetteer": output_dir / "2024_Gaz_counties_national.txt",
    }
    for key, url in [
        ("geography", urls.geography_url),
        *[(table, urls.table_urls[table]) for table in ACS_EXPOSURE_TABLES],
    ]:
        _download_if_needed(paths[key], url, download_if_missing=download_if_missing)
    if not paths["gazetteer"].exists():
        if not download_if_missing:
            raise AcsExposureInputError(f"ACS source file not found: {paths['gazetteer']}")
        _download_gazetteer_text(paths["gazetteer"], urls.gazetteer_url)
    return paths


def build_midatlantic_acs_exposure_from_paths(
    paths: dict[str, Path],
    *,
    source_urls: AcsExposureSourceUrls,
) -> list[AcsExposureCountyYear]:
    return build_midatlantic_acs_exposure(
        geography_text=paths["geography"].read_text(encoding="utf-8-sig"),
        b01001_text=paths["b01001"].read_text(encoding="utf-8-sig"),
        b25024_text=paths["b25024"].read_text(encoding="utf-8-sig"),
        b25003_text=paths["b25003"].read_text(encoding="utf-8-sig"),
        gazetteer_text=paths["gazetteer"].read_text(encoding="utf-8-sig"),
        source_urls=source_urls,
    )


def build_midatlantic_acs_exposure(
    *,
    geography_text: str,
    b01001_text: str,
    b25024_text: str,
    b25003_text: str,
    gazetteer_text: str,
    source_urls: AcsExposureSourceUrls,
    state_fips_list: list[str] | tuple[str, ...] = MIDATLANTIC_STATE_FIPS,
) -> list[AcsExposureCountyYear]:
    state_filter = {state_fips.zfill(2) for state_fips in state_fips_list}
    geography = _parse_acs_geography(geography_text, state_filter=state_filter)
    b01001 = _parse_acs_table(
        b01001_text,
        required_columns=_b01001_columns(),
        state_filter=state_filter,
    )
    b25024 = _parse_acs_table(
        b25024_text,
        required_columns={"B25024_E001", "B25024_E002", "B25024_E003"},
        state_filter=state_filter,
    )
    b25003 = _parse_acs_table(
        b25003_text,
        required_columns={"B25003_E001", "B25003_E002"},
        state_filter=state_filter,
    )
    land_area = _parse_gazetteer_land_area(
        gazetteer_text,
        state_filter=state_filter,
    )
    rows = []
    for geo_id, geo in geography.items():
        if geo_id not in b01001 or geo_id not in b25024 or geo_id not in b25003:
            raise AcsExposureInputError(
                f"ACS exposure source table missing geography {geo_id}"
            )
        rows.append(
            _acs_exposure_row(
                geography=geo,
                b01001=b01001[geo_id],
                b25024=b25024[geo_id],
                b25003=b25003[geo_id],
                land_area_sqmi=land_area.get(geo.county_fips),
                source_urls=source_urls,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _acs_exposure_row(
    *,
    geography: _AcsGeography,
    b01001: dict[str, str],
    b25024: dict[str, str],
    b25003: dict[str, str],
    land_area_sqmi: float | None,
    source_urls: AcsExposureSourceUrls,
) -> AcsExposureCountyYear:
    flags = [ACS_EXPOSURE_QUALITY_FLAGS]
    population = _parse_acs_int(b01001["B01001_E001"], flags)
    under18 = _sum_optional(
        [_parse_acs_int(b01001[column], flags) for column in _under18_columns()]
    )
    age65plus = _sum_optional(
        [_parse_acs_int(b01001[column], flags) for column in _age65plus_columns()]
    )
    age18_64 = None
    if population is not None and under18 is not None and age65plus is not None:
        age18_64 = population - under18 - age65plus

    total_housing = _parse_acs_int(b25024["B25024_E001"], flags)
    single_family_detached = _parse_acs_int(b25024["B25024_E002"], flags)
    single_family_attached = _parse_acs_int(b25024["B25024_E003"], flags)
    single_family = _sum_optional([single_family_detached, single_family_attached])

    occupied_housing = _parse_acs_int(b25003["B25003_E001"], flags)
    owner_occupied = _parse_acs_int(b25003["B25003_E002"], flags)

    if land_area_sqmi is None or land_area_sqmi <= 0:
        flags.append("missing_land_area")
        land_area_sqmi = None
    return AcsExposureCountyYear(
        state_fips=geography.state_fips,
        state_abbr=geography.state_abbr,
        state_name=geography.state_name,
        county_fips=geography.county_fips,
        county_name=geography.county_name,
        year=source_urls.year,
        acs_total_population=population,
        age_under_18_population=under18,
        age_18_64_population=age18_64,
        age_65_plus_population=age65plus,
        age_under_18_share=_share(under18, population, flags),
        age_18_64_share=_share(age18_64, population, flags),
        age_65_plus_share=_share(age65plus, population, flags),
        total_housing_units=total_housing,
        single_family_detached_units=single_family_detached,
        single_family_attached_units=single_family_attached,
        single_family_units=single_family,
        single_family_detached_share=_share(
            single_family_detached,
            total_housing,
            flags,
        ),
        single_family_share=_share(single_family, total_housing, flags),
        occupied_housing_units=occupied_housing,
        owner_occupied_units=owner_occupied,
        owner_occupied_share=_share(owner_occupied, occupied_housing, flags),
        land_area_sqmi=land_area_sqmi,
        population_per_sqmi=_density(population, land_area_sqmi),
        housing_units_per_sqmi=_density(total_housing, land_area_sqmi),
        single_family_units_per_sqmi=_density(single_family, land_area_sqmi),
        source_id=f"census_acs5_{source_urls.year}_residential_exposure",
        census_dataset=f"{source_urls.year}/acs/acs5/table_based_summary_file",
        vintage=source_urls.year,
        acs_source_url_hash=_url_hash(";".join(source_urls.all_urls[:-1])),
        geography_source_url_hash=_url_hash(source_urls.gazetteer_url),
        feature_quality_flags=",".join(dict.fromkeys(flags)),
    )


def _parse_acs_geography(
    text: str,
    *,
    state_filter: set[str],
) -> dict[str, _AcsGeography]:
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    missing = {"SUMLEVEL", "STATE", "COUNTY", "STUSAB", "GEO_ID", "NAME"} - set(
        reader.fieldnames or []
    )
    if missing:
        raise AcsExposureInputError(f"Missing ACS geography column(s): {sorted(missing)}")
    rows = {}
    for row in reader:
        state_fips = str(row["STATE"]).zfill(2)
        if row["SUMLEVEL"] != "050" or state_fips not in state_filter:
            continue
        state_abbr, state_name = MIDATLANTIC_STATES[state_fips]
        county_fips = state_fips + str(row["COUNTY"]).zfill(3)
        rows[row["GEO_ID"]] = _AcsGeography(
            state_fips=state_fips,
            state_abbr=state_abbr or row["STUSAB"],
            state_name=state_name,
            county_fips=county_fips,
            county_name=row["NAME"].split(",", maxsplit=1)[0],
            geo_id=row["GEO_ID"],
        )
    return rows


def _parse_acs_table(
    text: str,
    *,
    required_columns: set[str],
    state_filter: set[str],
) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    missing = {"GEO_ID", *required_columns} - set(reader.fieldnames or [])
    if missing:
        raise AcsExposureInputError(f"Missing ACS table column(s): {sorted(missing)}")
    rows = {}
    for row in reader:
        geo_id = row["GEO_ID"]
        if not geo_id.startswith("0500000US"):
            continue
        county_fips = geo_id.removeprefix("0500000US")
        if county_fips[:2] not in state_filter:
            continue
        rows[geo_id] = row
    return rows


def _parse_gazetteer_land_area(
    text: str,
    *,
    state_filter: set[str],
) -> dict[str, float]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if reader.fieldnames is not None:
        reader.fieldnames = [field.strip() for field in reader.fieldnames]
    missing = {"GEOID", "ALAND_SQMI"} - set(reader.fieldnames or [])
    if missing:
        raise AcsExposureInputError(
            f"Missing Census Gazetteer column(s): {sorted(missing)}"
        )
    rows = {}
    for row in reader:
        county_fips = str(row["GEOID"]).zfill(5)
        if county_fips[:2] in state_filter:
            rows[county_fips] = float(row["ALAND_SQMI"])
    return rows


def _download_if_needed(path: Path, url: str, *, download_if_missing: bool) -> None:
    if path.exists():
        return
    if not download_if_missing:
        raise AcsExposureInputError(f"ACS source file not found: {path}")
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=120) as response:
        with path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def _download_gazetteer_text(path: Path, url: str) -> None:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        zipped_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(zipped_bytes)) as archive:
        text_names = [name for name in archive.namelist() if name.endswith(".txt")]
        if not text_names:
            raise AcsExposureInputError("Census Gazetteer zip did not contain a .txt")
        with archive.open(text_names[0]) as handle:
            path.write_text(handle.read().decode("utf-8"), encoding="utf-8")


def _b01001_columns() -> set[str]:
    return {"B01001_E001", *_under18_columns(), *_age65plus_columns()}


def _under18_columns() -> list[str]:
    return [
        *[f"B01001_E{index:03d}" for index in range(3, 7)],
        *[f"B01001_E{index:03d}" for index in range(27, 31)],
    ]


def _age65plus_columns() -> list[str]:
    return [
        *[f"B01001_E{index:03d}" for index in range(20, 26)],
        *[f"B01001_E{index:03d}" for index in range(44, 50)],
    ]


def _parse_acs_int(value: str, flags: list[str]) -> int | None:
    cleaned = str(value).strip()
    if not cleaned:
        flags.append("missing_or_suppressed_acs_value")
        return None
    parsed = int(cleaned)
    if parsed <= -100000000:
        flags.append("missing_or_suppressed_acs_value")
        return None
    return parsed


def _sum_optional(values: list[int | None]) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _share(
    numerator: int | None,
    denominator: int | None,
    flags: list[str],
) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        flags.append("zero_or_missing_denominator")
        return None
    return round(numerator / denominator, 6)


def _density(value: int | None, land_area_sqmi: float | None) -> float | None:
    if value is None or land_area_sqmi is None or land_area_sqmi <= 0:
        return None
    return round(value / land_area_sqmi, 6)


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()
