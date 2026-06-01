#!/usr/bin/env python3
"""Generate the six-state weather locations resource for the parameterized loader.

Deterministic, reproducible build of
``tickbiterisk/resources/weather_locations.csv`` (the DE/DC/MD/PA/VA/WV county
universe with representative centroids used by the weather loader's optional
nearest-station fallback).

Provenance:
  - County FIPS / name / state from the committed regional county GeoJSON
    (build/etl/regional-county-adjacency/regional_counties.geojson).
  - Centroids: Maryland rows preserve the existing Census Gazetteer internal
    points from tickbiterisk/resources/maryland_weather_locations.csv; the other
    five states use the bounding-box center of the (web-simplified) county
    polygon. Centroids are used only for nearest-station fallback ranking, so a
    bbox center is adequate; the primary NOAA station discovery is FIPS-based.

Re-run after the regional county set changes:
    python scripts/build_weather_locations_resource.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEOJSON = REPO / "build/etl/regional-county-adjacency/regional_counties.geojson"
MD_RESOURCE = REPO / "tickbiterisk/resources/maryland_weather_locations.csv"
OUTPUT = REPO / "tickbiterisk/resources/weather_locations.csv"

STATE_FIPS_TO_ABBR = {"10": "DE", "11": "DC", "24": "MD", "42": "PA", "51": "VA", "54": "WV"}
COLUMNS = [
    "county_fips",
    "state_fips",
    "state",
    "county_name",
    "centroid_lat",
    "centroid_lon",
    "geography_source",
]


def _iter_coords(geometry: dict):
    gtype = geometry["type"]
    coords = geometry["coordinates"]
    if gtype == "Polygon":
        rings = coords
    elif gtype == "MultiPolygon":
        rings = [ring for polygon in coords for ring in polygon]
    else:
        raise ValueError(f"unsupported geometry type: {gtype}")
    for ring in rings:
        for lon, lat in ring:
            yield float(lon), float(lat)


def _bbox_center(geometry: dict) -> tuple[float, float]:
    lons, lats = [], []
    for lon, lat in _iter_coords(geometry):
        lons.append(lon)
        lats.append(lat)
    lat = round((min(lats) + max(lats)) / 2.0, 6)
    lon = round((min(lons) + max(lons)) / 2.0, 6)
    return lat, lon


def main() -> None:
    md_centroids: dict[str, dict[str, str]] = {}
    with MD_RESOURCE.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            md_centroids[str(row["county_fips"]).zfill(5)] = row

    geojson = json.loads(GEOJSON.read_text(encoding="utf-8"))
    rows = []
    for feature in geojson["features"]:
        props = feature["properties"]
        county_fips = str(props["county_fips"]).zfill(5)
        state_fips = str(props["state_fips"]).zfill(2)
        state = STATE_FIPS_TO_ABBR[state_fips]
        county_name = props["county_name"]
        if county_fips in md_centroids:
            md = md_centroids[county_fips]
            lat, lon = md["centroid_lat"], md["centroid_lon"]
            source = md["geography_source"]
        else:
            lat, lon = _bbox_center(feature["geometry"])
            source = "regional_counties.geojson bbox center (web-simplified)"
        rows.append(
            {
                "county_fips": county_fips,
                "state_fips": state_fips,
                "state": state,
                "county_name": county_name,
                "centroid_lat": lat,
                "centroid_lon": lon,
                "geography_source": source,
            }
        )
    rows.sort(key=lambda r: r["county_fips"])

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} weather location rows to {OUTPUT}")


if __name__ == "__main__":
    main()
