from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENVIROATLAS_HABITAT_QUERY_BASE_URL = (
    "https://enviroatlas.epa.gov/arcgis/rest/services/"
    "Other/CMA_Landscape/MapServer/1"
)
EPA_ENVIROATLAS_DATA_DOWNLOAD_URL = "https://www.epa.gov/enviroatlas/data-download"
ENVIROATLAS_HABITAT_FIELDS = [
    "GEOID",
    "NAMELSAD",
    "pfor",
    "pfor90",
    "pwetl",
    "pwetl95",
    "pdev",
    "Pimprv",
    "pagr",
    "pagrp",
    "pagrc",
    "rNI45",
    "rfor45",
    "rfor9045",
    "NINDEX",
]
ENVIROATLAS_HABITAT_FEATURE_QUALITY_FLAGS = "static_enviroatlas_2011"
MARYLAND_STATE_FIPS = "24"


@dataclass(frozen=True)
class EnviroAtlasCountyHabitat:
    county_fips: str
    county_name: str
    forest_pct: float
    forest_woody_wetland_pct: float
    wetland_pct: float
    emergent_wetland_pct: float
    developed_pct: float
    impervious_pct: float
    agriculture_pct: float
    pasture_hay_pct: float
    cultivated_crop_pct: float
    riparian_natural_45m_pct: float
    riparian_forest_45m_pct: float
    riparian_forest_woody_wetland_45m_pct: float
    natural_land_cover_index: float
    source_url_hash: str
    feature_quality_flags: str


def build_enviroatlas_maryland_habitat_query_url() -> str:
    params = {
        "where": "GEOID LIKE '24%'",
        "outFields": ",".join(ENVIROATLAS_HABITAT_FIELDS),
        "returnGeometry": "false",
        "f": "json",
    }
    return f"{ENVIROATLAS_HABITAT_QUERY_BASE_URL}/query?{urlencode(params)}"


def fetch_enviroatlas_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_enviroatlas_county_habitat(
    response_json: dict[str, object],
    *,
    source_url: str,
) -> list[EnviroAtlasCountyHabitat]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows = []
    for feature in response_json.get("features", []):
        if not isinstance(feature, dict):
            continue
        attributes = feature.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        county_fips = _normalize_fips(attributes.get("GEOID"))
        if not county_fips.startswith(MARYLAND_STATE_FIPS):
            continue
        rows.append(
            EnviroAtlasCountyHabitat(
                county_fips=county_fips,
                county_name=_county_name(attributes),
                forest_pct=_parse_float(attributes.get("pfor")),
                forest_woody_wetland_pct=_parse_float(attributes.get("pfor90")),
                wetland_pct=_parse_float(attributes.get("pwetl")),
                emergent_wetland_pct=_parse_float(attributes.get("pwetl95")),
                developed_pct=_parse_float(attributes.get("pdev")),
                impervious_pct=_parse_float(attributes.get("Pimprv")),
                agriculture_pct=_parse_float(attributes.get("pagr")),
                pasture_hay_pct=_parse_float(attributes.get("pagrp")),
                cultivated_crop_pct=_parse_float(attributes.get("pagrc")),
                riparian_natural_45m_pct=_parse_float(attributes.get("rNI45")),
                riparian_forest_45m_pct=_parse_float(attributes.get("rfor45")),
                riparian_forest_woody_wetland_45m_pct=_parse_float(
                    attributes.get("rfor9045")
                ),
                natural_land_cover_index=_parse_float(attributes.get("NINDEX")),
                source_url_hash=source_url_hash,
                feature_quality_flags=ENVIROATLAS_HABITAT_FEATURE_QUALITY_FLAGS,
            )
        )
    return sorted(rows, key=lambda row: row.county_fips)


def _normalize_fips(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().zfill(5)


def _county_name(attributes: dict[str, object]) -> str:
    for field in ["NAMELSAD", "NAME", "County", "COUNTY", "county_name"]:
        value = attributes.get(field)
        if value is not None:
            return str(value).strip()
    return ""


def _parse_float(value: object) -> float:
    if value is None:
        return 0.0
    cleaned = str(value).strip()
    if not cleaned:
        return 0.0
    return float(cleaned)
