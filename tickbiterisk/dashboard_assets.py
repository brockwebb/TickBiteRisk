from __future__ import annotations

import json
import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.runtime.static_export import (
    MIDATLANTIC_GEOGRAPHY_SCOPE,
    StaticRiskExportPaths,
    export_static_risk_data,
)
from tickbiterisk.runtime.risk_lookup import split_quality_flags


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


@dataclass(frozen=True)
class RegionalResearchDashboardAssetPaths:
    output_dir: Path
    weekly_risk_path: Path
    county_metadata_path: Path
    model_card_path: Path
    source_catalog_path: Path
    export_manifest_path: Path
    county_geojson_path: Path
    state_geojson_path: Path | None
    spatial_regime_overlays_path: Path | None


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
    model_summary_path: Path | None = None,
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
        model_summary_path=model_summary_path,
    )
    raw_geojson = fetch_geojson() if fetch_geojson else fetch_maryland_county_geojson()
    normalized_geojson = normalize_maryland_county_geojson(raw_geojson)
    county_geojson_path = output_dir / "md_counties.geojson"
    county_geojson_path.write_text(
        json.dumps(normalized_geojson, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _augment_manifest_with_county_geojson(
        static_paths.export_manifest_path,
        county_geojson_path=county_geojson_path,
        feature_count=len(normalized_geojson["features"]),
    )
    return _paths_from_static(output_dir, static_paths, county_geojson_path)


def write_regional_research_dashboard_assets(
    *,
    scores_path: Path,
    output_dir: Path,
    regional_counties_geojson_path: Path,
    regional_states_geojson_path: Path | None = None,
    spatial_regime_summary_path: Path | None = None,
    model_name: str = "empirical_bayes_spatial_regime_incidence",
    seasonality_source_id: str = "cdc_seasonality_week_2023",
    benchmark_quantile: float | None = None,
    headroom_multiplier: float | None = None,
    score_denominator: float | None = None,
    source_prediction_run_id: str | None = None,
    source_prediction_sha256: str | None = None,
    source_seasonality_sha256: str | None = None,
) -> RegionalResearchDashboardAssetPaths:
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
        geography_scope=MIDATLANTIC_GEOGRAPHY_SCOPE,
    )
    raw_geojson = json.loads(regional_counties_geojson_path.read_text(encoding="utf-8"))
    normalized_geojson = simplify_regional_geojson_for_web_map(
        normalize_regional_county_geojson(raw_geojson)
    )
    county_geojson_path = output_dir / "regional_counties.geojson"
    county_geojson_path.write_text(
        json.dumps(normalized_geojson, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    state_geojson_path = None
    state_feature_count = 0
    if regional_states_geojson_path is not None:
        raw_state_geojson = json.loads(
            regional_states_geojson_path.read_text(encoding="utf-8")
        )
        normalized_state_geojson = simplify_regional_geojson_for_web_map(
            normalize_regional_state_geojson(raw_state_geojson)
        )
        state_geojson_path = output_dir / "regional_states.geojson"
        state_geojson_path.write_text(
            json.dumps(normalized_state_geojson, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        state_feature_count = len(normalized_state_geojson["features"])
    overlay_path = None
    overlay_count = 0
    overlay_payload = None
    if spatial_regime_summary_path is not None:
        overlay_payload = regional_spatial_regime_overlay_payload(
            spatial_regime_summary_path,
            model_name=model_name,
        )
        overlay_path = output_dir / "regional_spatial_regime_overlays.json"
        overlay_path.write_text(
            json.dumps(overlay_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        overlay_count = int(overlay_payload["record_count"])
        _augment_regional_county_metadata_with_regimes(
            static_paths.county_metadata_path,
            overlay_payload,
        )
    _augment_manifest_with_regional_assets(
        static_paths.export_manifest_path,
        county_geojson_path=county_geojson_path,
        feature_count=len(normalized_geojson["features"]),
        state_geojson_path=state_geojson_path,
        state_feature_count=state_feature_count,
        spatial_regime_overlays_path=overlay_path,
        spatial_regime_overlay_count=overlay_count,
    )
    return _regional_paths_from_static(
        output_dir,
        static_paths,
        county_geojson_path,
        state_geojson_path,
        overlay_path,
    )


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


def normalize_regional_county_geojson(
    payload: dict[str, Any],
) -> dict[str, Any]:
    features = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        county_fips = str(
            properties.get("county_fips")
            or properties.get("GEOID")
            or properties.get("source_geoid")
            or ""
        ).zfill(5)
        state_fips = str(properties.get("state_fips") or county_fips[:2]).zfill(2)
        county_name = str(properties.get("county_name") or properties.get("NAME") or "")
        geometry = feature.get("geometry")
        if len(county_fips) != 5 or len(state_fips) != 2 or not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "state_fips": state_fips,
                    "state_abbr": _state_abbr(state_fips),
                },
                "geometry": geometry,
            }
        )
    features.sort(key=lambda item: item["properties"]["county_fips"])
    if not features:
        raise ValueError("Expected at least one regional county feature")
    return {
        "type": "FeatureCollection",
        "metadata": {
            "scope": "midatlantic_county_equivalent",
            "states": ["DE", "DC", "MD", "PA", "VA", "WV"],
            "feature_count": len(features),
            "research_only": True,
            "not_public_maryland_default": True,
        },
        "features": features,
    }


def normalize_regional_state_geojson(
    payload: dict[str, Any],
) -> dict[str, Any]:
    features = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        state_fips = str(
            properties.get("state_fips")
            or properties.get("STATE")
            or properties.get("GEOID")
            or ""
        ).zfill(2)
        state_abbr = str(properties.get("state_abbr") or properties.get("STUSAB") or "")
        state_name = str(
            properties.get("state_name")
            or properties.get("NAME")
            or properties.get("BASENAME")
            or ""
        )
        geometry = feature.get("geometry")
        if len(state_fips) != 2 or not state_abbr or not state_name or not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                },
                "geometry": geometry,
            }
        )
    features.sort(key=lambda item: item["properties"]["state_fips"])
    if not features:
        raise ValueError("Expected at least one regional state boundary feature")
    return {
        "type": "FeatureCollection",
        "metadata": {
            "scope": "midatlantic_state_boundary",
            "states": [feature["properties"]["state_abbr"] for feature in features],
            "feature_count": len(features),
            "research_only": True,
            "not_public_maryland_default": True,
        },
        "features": features,
    }


def simplify_regional_geojson_for_web_map(
    payload: dict[str, Any],
    *,
    tolerance: float = 0.01,
    coordinate_precision: int = 4,
) -> dict[str, Any]:
    simplified_features = []
    for feature in payload.get("features", []):
        simplified_features.append(
            {
                "type": "Feature",
                "properties": dict(feature.get("properties", {})),
                "geometry": _simplify_geometry_for_web_map(
                    feature.get("geometry", {}),
                    tolerance=tolerance,
                    coordinate_precision=coordinate_precision,
                ),
            }
        )
    metadata = dict(payload.get("metadata", {}))
    metadata["web_map_simplified"] = True
    metadata["geometry_simplification"] = {
        "method": "radial_distance_ring_simplification",
        "tolerance_degrees": tolerance,
        "coordinate_precision": coordinate_precision,
    }
    return {
        "type": payload.get("type", "FeatureCollection"),
        "metadata": metadata,
        "features": simplified_features,
    }


def regional_spatial_regime_overlay_payload(
    summary_path: Path,
    *,
    model_name: str,
) -> dict[str, object]:
    with summary_path.open(encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("model_name") == model_name
        ]
    records = [_spatial_regime_overlay_record(row) for row in rows]
    return {
        "schema_version": "regional-spatial-regime-overlays-v1",
        "export_type": "regional_spatial_regime_overlays",
        "model_name": model_name,
        "record_count": len(records),
        "research_status": {
            "research_only": True,
            "not_public_maryland_default": True,
        },
        "records": records,
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


def _regional_paths_from_static(
    output_dir: Path,
    static_paths: StaticRiskExportPaths,
    county_geojson_path: Path,
    state_geojson_path: Path | None,
    spatial_regime_overlays_path: Path | None,
) -> RegionalResearchDashboardAssetPaths:
    return RegionalResearchDashboardAssetPaths(
        output_dir=output_dir,
        weekly_risk_path=static_paths.weekly_risk_path,
        county_metadata_path=static_paths.county_metadata_path,
        model_card_path=static_paths.model_card_path,
        source_catalog_path=static_paths.source_catalog_path,
        export_manifest_path=static_paths.export_manifest_path,
        county_geojson_path=county_geojson_path,
        state_geojson_path=state_geojson_path,
        spatial_regime_overlays_path=spatial_regime_overlays_path,
    )


def _augment_manifest_with_county_geojson(
    manifest_path: Path,
    *,
    county_geojson_path: Path,
    feature_count: int,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.setdefault("files", [])
    if county_geojson_path.name not in files:
        files.append(county_geojson_path.name)
    record_counts = manifest.setdefault("record_counts", {})
    record_counts["county_geojson_features"] = feature_count
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _augment_manifest_with_regional_assets(
    manifest_path: Path,
    *,
    county_geojson_path: Path,
    feature_count: int,
    state_geojson_path: Path | None,
    state_feature_count: int,
    spatial_regime_overlays_path: Path | None,
    spatial_regime_overlay_count: int,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.setdefault("files", [])
    if county_geojson_path.name not in files:
        files.append(county_geojson_path.name)
    if state_geojson_path is not None and state_geojson_path.name not in files:
        files.append(state_geojson_path.name)
    record_counts = manifest.setdefault("record_counts", {})
    record_counts["regional_county_geojson_features"] = feature_count
    if state_geojson_path is not None:
        record_counts["regional_state_geojson_features"] = state_feature_count
    if spatial_regime_overlays_path is not None:
        if spatial_regime_overlays_path.name not in files:
            files.append(spatial_regime_overlays_path.name)
        record_counts["spatial_regime_overlays"] = spatial_regime_overlay_count
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _augment_regional_county_metadata_with_regimes(
    county_metadata_path: Path,
    overlay_payload: dict[str, object],
) -> None:
    metadata = json.loads(county_metadata_path.read_text(encoding="utf-8"))
    memberships = _county_regime_memberships(overlay_payload)
    for county in metadata.get("counties", []):
        membership = memberships.get(str(county.get("county_fips", "")))
        if membership is not None:
            county["selected_spatial_regime"] = membership
    county_metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _county_regime_memberships(
    overlay_payload: dict[str, object],
) -> dict[str, dict[str, object]]:
    memberships = {}
    for record in overlay_payload.get("records", []):
        if not isinstance(record, dict):
            continue
        membership = {
            "region_id": record["region_id"],
            "region_name": record["region_name"],
            "spatial_regime_rank": record["spatial_regime_rank"],
            "spatial_regime_feature_year": record["spatial_regime_feature_year"],
            "forecast_year": record["forecast_year"],
            "forecast_origin_year": record["forecast_origin_year"],
        }
        for county_fips in record.get("county_fips_list", []):
            memberships[str(county_fips)] = membership
    return memberships


def _spatial_regime_overlay_record(row: dict[str, str]) -> dict[str, object]:
    return {
        "run_id": str(row["run_id"]),
        "region_id": str(row["region_id"]),
        "region_name": str(row["region_name"]),
        "spatial_regime_rank": _int_value(row["spatial_regime_rank"]),
        "spatial_regime_feature_year": _int_value(row["spatial_regime_feature_year"]),
        "forecast_year": _int_value(row["forecast_year"]),
        "forecast_origin_year": _int_value(row["forecast_origin_year"]),
        "n_counties": _int_value(row["n_counties"]),
        "county_fips_list": [
            value.strip()
            for value in str(row["county_fips_list"]).split(",")
            if value.strip()
        ],
        "forecast_population": _int_value(row["forecast_population"]),
        "predicted_total_cases": _float_value(row["predicted_total_cases"]),
        "predicted_incidence_per_100k": _float_value(
            row["predicted_incidence_per_100k"]
        ),
        "predicted_incidence_80_interval": [
            _float_value(row["lower_80_incidence_per_100k"]),
            _float_value(row["upper_80_incidence_per_100k"]),
        ],
        "predicted_incidence_95_interval": [
            _float_value(row["lower_95_incidence_per_100k"]),
            _float_value(row["upper_95_incidence_per_100k"]),
        ],
        "summary_assumption_flags": split_quality_flags(
            row.get("summary_assumption_flags", "")
        ),
    }


def _state_abbr(state_fips: str) -> str:
    return {
        "10": "DE",
        "11": "DC",
        "24": "MD",
        "42": "PA",
        "51": "VA",
        "54": "WV",
    }.get(state_fips, state_fips)


def _simplify_geometry_for_web_map(
    geometry: dict[str, Any],
    *,
    tolerance: float,
    coordinate_precision: int,
) -> dict[str, Any]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        return {
            "type": "Point",
            "coordinates": _round_point(coordinates, coordinate_precision),
        }
    if geometry_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [
                _simplify_ring_for_web_map(
                    ring,
                    tolerance=tolerance,
                    coordinate_precision=coordinate_precision,
                )
                for ring in coordinates or []
            ],
        }
    if geometry_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    _simplify_ring_for_web_map(
                        ring,
                        tolerance=tolerance,
                        coordinate_precision=coordinate_precision,
                    )
                    for ring in polygon
                ]
                for polygon in coordinates or []
            ],
        }
    return geometry


def _simplify_ring_for_web_map(
    ring: list[list[float]],
    *,
    tolerance: float,
    coordinate_precision: int,
) -> list[list[float]]:
    if len(ring) < 4:
        return [_round_point(point, coordinate_precision) for point in ring]

    source_points = list(ring)
    if source_points[0] == source_points[-1]:
        source_points = source_points[:-1]
    if len(source_points) < 3:
        return [_round_point(point, coordinate_precision) for point in ring]

    kept = [source_points[0]]
    last_point = source_points[0]
    tolerance_squared = tolerance * tolerance
    for point in source_points[1:]:
        if _squared_distance(last_point, point) >= tolerance_squared:
            kept.append(point)
            last_point = point
    if len(kept) < 3:
        kept = source_points

    simplified = [_round_point(point, coordinate_precision) for point in kept]
    if simplified[0] != simplified[-1]:
        simplified.append(list(simplified[0]))
    if len(simplified) < 4:
        return [_round_point(point, coordinate_precision) for point in ring]
    return simplified


def _round_point(point: Any, coordinate_precision: int) -> list[float]:
    if not isinstance(point, list | tuple) or len(point) < 2:
        return []
    return [
        round(float(point[0]), coordinate_precision),
        round(float(point[1]), coordinate_precision),
    ]


def _squared_distance(left: list[float], right: list[float]) -> float:
    return (float(left[0]) - float(right[0])) ** 2 + (
        float(left[1]) - float(right[1])
    ) ** 2


def _int_value(value: str) -> int:
    return int(str(value).replace(",", "").strip())


def _float_value(value: str) -> float:
    return float(str(value).replace(",", "").strip())
