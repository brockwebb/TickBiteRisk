from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.runtime.static_export import (
    StaticRiskExportPaths,
    export_static_risk_data,
)


TIGERWEB_COUNTIES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/tigerWMS_Current/MapServer/82/query"
)


@dataclass(frozen=True)
class DashboardAssetPaths:
    output_dir: Path
    weekly_risk_path: Path
    county_metadata_path: Path
    model_card_path: Path
    source_catalog_path: Path
    export_manifest_path: Path
    county_geojson_path: Path


def write_dashboard_assets(
    *,
    scores_path: Path,
    output_dir: Path,
    model_name: str = "linear_blend_baseline",
    seasonality_source_id: str = "cdc_seasonality_week_2023",
    benchmark_quantile: float | None = None,
    headroom_multiplier: float | None = None,
    score_denominator: float | None = None,
    source_prediction_run_id: str | None = None,
    source_prediction_sha256: str | None = None,
    source_seasonality_sha256: str | None = None,
    fetch_geojson: Callable[[], dict[str, Any]] | None = None,
) -> DashboardAssetPaths:
    static_paths = export_static_risk_data(
        scores_path=scores_path,
        output_dir=output_dir,
        model_name=model_name,
        seasonality_source_id=seasonality_source_id,
        benchmark_quantile=benchmark_quantile,
        headroom_multiplier=headroom_multiplier,
        score_denominator=score_denominator,
        source_prediction_run_id=source_prediction_run_id,
        source_prediction_sha256=source_prediction_sha256,
        source_seasonality_sha256=source_seasonality_sha256,
    )
    raw_geojson = fetch_geojson() if fetch_geojson else fetch_maryland_county_geojson()
    normalized_geojson = normalize_maryland_county_geojson(raw_geojson)
    county_geojson_path = output_dir / "md_counties.geojson"
    county_geojson_path.write_text(
        json.dumps(normalized_geojson, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _paths_from_static(output_dir, static_paths, county_geojson_path)


def fetch_maryland_county_geojson() -> dict[str, Any]:
    params = urlencode(
        {
            "where": "STATE='24'",
            "outFields": "GEOID,NAME,STATE,COUNTY",
            "returnGeometry": "true",
            "outSR": "4326",
            "geometryPrecision": "5",
            "maxAllowableOffset": "0.001",
            "f": "geojson",
        }
    )
    request = Request(
        f"{TIGERWEB_COUNTIES_URL}?{params}",
        headers={"User-Agent": "TickBiteRisk/0.1"},
    )
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Census TIGERweb response was not a GeoJSON FeatureCollection")
    return payload


def normalize_maryland_county_geojson(
    payload: dict[str, Any],
) -> dict[str, Any]:
    features = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        county_fips = str(properties.get("GEOID", ""))
        state_fips = str(properties.get("STATE") or county_fips[:2])
        county_name = str(properties.get("NAME", ""))
        geometry = feature.get("geometry")
        if state_fips != "24" or len(county_fips) != 5 or not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "county_fips": county_fips,
                    "county_name": county_name,
                },
                "geometry": geometry,
            }
        )
    features.sort(key=lambda item: item["properties"]["county_fips"])
    if len(features) != 24:
        raise ValueError(f"Expected 24 Maryland county features, found {len(features)}")
    return {
        "type": "FeatureCollection",
        "metadata": {
            "source": "US Census TIGERweb Counties",
            "source_url": TIGERWEB_COUNTIES_URL,
            "state_fips": "24",
            "feature_count": len(features),
        },
        "features": features,
    }


def _paths_from_static(
    output_dir: Path,
    static_paths: StaticRiskExportPaths,
    county_geojson_path: Path,
) -> DashboardAssetPaths:
    return DashboardAssetPaths(
        output_dir=output_dir,
        weekly_risk_path=static_paths.weekly_risk_path,
        county_metadata_path=static_paths.county_metadata_path,
        model_card_path=static_paths.model_card_path,
        source_catalog_path=static_paths.source_catalog_path,
        export_manifest_path=static_paths.export_manifest_path,
        county_geojson_path=county_geojson_path,
    )
