from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from urllib.request import Request, urlopen


CENSUS_GAZETTEER_COUNTIES_2024_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_counties_national.zip"
)


@dataclass(frozen=True)
class CountyReference:
    county_fips: str
    state_fips: str
    state: str
    county_name: str
    aland_sqmi: float
    awater_sqmi: float
    intptlat: float
    intptlon: float
    geography_source: str
    source_url_hash: str


def fetch_census_gazetteer_counties_text(
    url: str = CENSUS_GAZETTEER_COUNTIES_2024_URL,
) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        zipped_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(zipped_bytes)) as archive:
        text_names = [name for name in archive.namelist() if name.endswith(".txt")]
        if not text_names:
            raise ValueError("Census Gazetteer zip did not contain a .txt file")
        with archive.open(text_names[0]) as handle:
            return handle.read().decode("utf-8")


def parse_census_gazetteer_counties(
    text: str,
    *,
    source_url: str,
) -> list[CountyReference]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if reader.fieldnames is not None:
        reader.fieldnames = [field.strip() for field in reader.fieldnames]
    rows = []
    for row in reader:
        if row["USPS"] != "MD":
            continue
        rows.append(
            CountyReference(
                county_fips=str(row["GEOID"]).zfill(5),
                state_fips=str(row["GEOID"])[:2].zfill(2),
                state=row["USPS"],
                county_name=row["NAME"],
                aland_sqmi=float(row["ALAND_SQMI"]),
                awater_sqmi=float(row["AWATER_SQMI"]),
                intptlat=float(row["INTPTLAT"]),
                intptlon=float(row["INTPTLONG"]),
                geography_source="Census Gazetteer 2024 counties",
                source_url_hash=source_url_hash,
            )
        )
    return sorted(rows, key=lambda item: item.county_fips)
