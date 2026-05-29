from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.etl.acquisition_provenance import AcquisitionProvenanceRecord


MIDATLANTIC_STATE_FIPS = ("10", "11", "24", "42", "51", "54")
MIDATLANTIC_STATE_LABELS = {
    "10": "DE",
    "11": "DC",
    "24": "MD",
    "42": "PA",
    "51": "VA",
    "54": "WV",
}
EXPECTED_MIDATLANTIC_COUNTY_COUNTS = {
    "10": 3,
    "11": 1,
    "24": 24,
    "42": 67,
    "51": 133,
    "54": 55,
}
CENSUS_TIGERWEB_COUNTY_QUERY_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/State_County/MapServer/49/query"
)
CENSUS_TIGERWEB_COUNTY_CITATION_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/State_County/MapServer"
)
CENSUS_TIGERWEB_SOURCE_ID = "census_tigerweb_midatlantic_county_geojson"


def build_tigerweb_county_query_url(
    state_fips: tuple[str, ...] | list[str] = MIDATLANTIC_STATE_FIPS,
) -> str:
    quoted_states = ",".join(f"'{str(value).zfill(2)}'" for value in state_fips)
    params = {
        "where": f"STATE IN ({quoted_states})",
        "outFields": "GEOID,STATE,COUNTY,NAME,BASENAME",
        "returnGeometry": "true",
        "geometryPrecision": "6",
        "outSR": "4326",
        "f": "geojson",
    }
    return f"{CENSUS_TIGERWEB_COUNTY_QUERY_URL}?{urlencode(params)}"


def fetch_regional_county_geojson_text(
    url: str | None = None,
) -> str:
    source_url = url or build_tigerweb_county_query_url()
    request = Request(source_url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8")


def normalize_tigerweb_county_geojson(
    source_geojson: dict[str, Any],
    *,
    state_fips: tuple[str, ...] | list[str] = MIDATLANTIC_STATE_FIPS,
    source_url: str | None = None,
) -> dict[str, Any]:
    allowed_states = {str(value).zfill(2) for value in state_fips}
    source_url_hash = _source_url_hash(
        source_url or build_tigerweb_county_query_url(tuple(sorted(allowed_states)))
    )
    features = []
    for feature in source_geojson.get("features", []):
        properties = feature.get("properties", {})
        county_fips = str(
            properties.get("GEOID")
            or properties.get("county_fips")
            or ""
        ).zfill(5)
        state_fips_value = str(
            properties.get("STATE")
            or properties.get("state_fips")
            or county_fips[:2]
        ).zfill(2)
        county_name = str(
            properties.get("county_name")
            or properties.get("NAME")
            or properties.get("NAMELSAD")
            or properties.get("BASENAME")
            or ""
        )
        if len(county_fips) != 5 or state_fips_value not in allowed_states:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "county_fips": county_fips,
                    "state_fips": state_fips_value,
                    "county_name": county_name,
                    "source_geoid": county_fips,
                    "source_url_hash": source_url_hash,
                },
                "geometry": feature.get("geometry", {}),
            }
        )
    return {
        "type": "FeatureCollection",
        "features": sorted(
            features,
            key=lambda item: str(item["properties"]["county_fips"]),
        ),
    }


def normalize_tigerweb_county_geojson_text(
    text: str,
    *,
    source_url: str | None = None,
) -> dict[str, Any]:
    return normalize_tigerweb_county_geojson(
        json.loads(text),
        source_url=source_url,
    )


def validate_regional_county_geojson_footprint(
    normalized_geojson: dict[str, Any],
    *,
    expected_state_counts: dict[str, int] | None = EXPECTED_MIDATLANTIC_COUNTY_COUNTS,
) -> None:
    features = normalized_geojson.get("features", [])
    if not features:
        raise ValueError(
            "Regional county GeoJSON footprint incomplete: no county features found."
        )
    state_counts = Counter(
        str(feature.get("properties", {}).get("state_fips", "")).zfill(2)
        for feature in features
    )
    expected_states = set(MIDATLANTIC_STATE_FIPS)
    observed_states = {state for state, count in state_counts.items() if count > 0}
    missing_states = sorted(expected_states - observed_states)
    unexpected_states = sorted(observed_states - expected_states)
    if missing_states:
        raise ValueError(
            "Regional county GeoJSON footprint incomplete: missing state FIPS "
            f"{', '.join(_state_label(state) for state in missing_states)}."
        )
    if unexpected_states:
        raise ValueError(
            "Regional county GeoJSON footprint includes unsupported state FIPS "
            f"{', '.join(_state_label(state) for state in unexpected_states)}."
        )
    if expected_state_counts is None:
        return
    mismatches = [
        f"{_state_label(state)} expected {expected_count} found {state_counts[state]}"
        for state, expected_count in sorted(expected_state_counts.items())
        if state_counts[state] != expected_count
    ]
    if mismatches:
        expected_total = sum(expected_state_counts.values())
        observed_total = len(features)
        raise ValueError(
            "Regional county GeoJSON footprint incomplete: expected "
            f"{expected_total} county-equivalent features across DE/DC/MD/PA/VA/WV, "
            f"found {observed_total}; " + "; ".join(mismatches) + "."
        )


def build_regional_county_geojson_provenance(
    *,
    source_url: str,
    artifact_paths: list[Path],
    row_count: int,
    output_dir: Path,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id=CENSUS_TIGERWEB_SOURCE_ID,
        source_name="U.S. Census TIGERweb county geometry",
        source_url=source_url,
        citation_url=CENSUS_TIGERWEB_COUNTY_CITATION_URL,
        acquisition_command=(
            "tickbiterisk etl regional-county-adjacency "
            f"--fetch-census-geojson --output-dir {output_dir}"
        ),
        acquisition_procedure=(
            "Query the official Census TIGERweb State_County county layer as "
            "GeoJSON for DE/DC/MD/PA/VA/WV, normalize county properties, and "
            "derive shared-boundary county adjacency."
        ),
        request_method="GET",
        request_description=(
            "Census TIGERweb county GeoJSON request for DE/DC/MD/PA/VA/WV "
            "county-equivalent geometry."
        ),
        derived_artifact_paths=artifact_paths,
        row_count=row_count,
        parser_method="normalize_tigerweb_county_geojson",
        extraction_quality="accepted",
        access_notes="Public Census TIGERweb GeoJSON endpoint; no API key required.",
        modeling_caveats=(
            "County geometry and adjacency support only; not disease, exposure, "
            "or latent-risk truth."
        ),
    )


def _source_url_hash(source_url: str) -> str:
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def _state_label(state_fips: str) -> str:
    label = MIDATLANTIC_STATE_LABELS.get(state_fips)
    if label is None:
        return state_fips
    return f"{state_fips} ({label})"
