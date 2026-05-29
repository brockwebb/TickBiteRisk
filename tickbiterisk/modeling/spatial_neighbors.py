from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any


COUNTY_ADJACENCY_COLUMNS = [
    "county_fips",
    "county_name",
    "neighbor_county_fips",
    "neighbor_county_name",
    "shared_boundary_segment_count",
    "adjacency_method",
    "feature_quality_flags",
]
MARYLAND_COUNTY_ADJACENCY_FLAG = "county_adjacency_from_geojson"
REGIONAL_COUNTY_ADJACENCY_FLAG = "regional_county_adjacency_from_geojson"


@dataclass(frozen=True)
class CountyAdjacency:
    county_fips: str
    county_name: str
    neighbor_county_fips: str
    neighbor_county_name: str
    shared_boundary_segment_count: int
    adjacency_method: str
    feature_quality_flags: str


class CountyAdjacencyInputError(ValueError):
    """Raised when county adjacency inputs are invalid."""


@dataclass(frozen=True)
class NeighborIncidenceSummary:
    mean_incidence_per_100k: float
    max_incidence_per_100k: float
    neighbor_count: int
    start_year: int | None
    end_year: int | None
    year_count: int
    missing_neighbor_incidence: bool


def build_county_adjacency_from_geojson(
    county_geojson_path: Path,
) -> list[CountyAdjacency]:
    geojson = json.loads(county_geojson_path.read_text(encoding="utf-8"))
    features = geojson.get("features", [])
    names_by_fips: dict[str, str] = {}
    segment_counties: dict[
        tuple[tuple[float, float], tuple[float, float]], set[str]
    ] = {}
    for feature in features:
        properties = feature.get("properties", {})
        county_fips = str(properties.get("county_fips", "")).zfill(5)
        county_name = str(properties.get("county_name", ""))
        geometry = feature.get("geometry", {})
        if len(county_fips) != 5 or not geometry:
            continue
        names_by_fips[county_fips] = county_name
        for segment in _geometry_segments(geometry):
            segment_counties.setdefault(segment, set()).add(county_fips)

    shared_segment_counts: dict[tuple[str, str], int] = {}
    for county_fips_set in segment_counties.values():
        if len(county_fips_set) < 2:
            continue
        for left, right in combinations(sorted(county_fips_set), 2):
            shared_segment_counts[(left, right)] = (
                shared_segment_counts.get((left, right), 0) + 1
            )

    rows = []
    for (left, right), segment_count in shared_segment_counts.items():
        rows.extend(
            [
                _adjacency_row(left, right, names_by_fips, segment_count),
                _adjacency_row(right, left, names_by_fips, segment_count),
            ]
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.neighbor_county_fips))


def write_county_adjacency_output(
    rows: list[CountyAdjacency],
    output_dir: Path,
) -> Path:
    return _write_adjacency_output(
        rows,
        output_dir / "md_county_adjacency.csv",
        feature_quality_flags=MARYLAND_COUNTY_ADJACENCY_FLAG,
    )


def write_regional_county_adjacency_output(
    rows: list[CountyAdjacency],
    output_dir: Path,
) -> Path:
    return _write_adjacency_output(
        rows,
        output_dir / "regional_county_adjacency.csv",
        feature_quality_flags=REGIONAL_COUNTY_ADJACENCY_FLAG,
    )


def _write_adjacency_output(
    rows: list[CountyAdjacency],
    output_path: Path,
    *,
    feature_quality_flags: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    keyed = {
        (row.county_fips, row.neighbor_county_fips): row
        for row in rows
    }
    ordered = sorted(
        keyed.values(),
        key=lambda row: (row.county_fips, row.neighbor_county_fips),
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COUNTY_ADJACENCY_COLUMNS)
        writer.writeheader()
        for row in ordered:
            writer.writerow(
                {
                    "county_fips": row.county_fips,
                    "county_name": row.county_name,
                    "neighbor_county_fips": row.neighbor_county_fips,
                    "neighbor_county_name": row.neighbor_county_name,
                    "shared_boundary_segment_count": row.shared_boundary_segment_count,
                    "adjacency_method": row.adjacency_method,
                    "feature_quality_flags": feature_quality_flags,
                }
            )
    return output_path


def read_county_neighbors(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    if not path.exists():
        raise CountyAdjacencyInputError(f"county adjacency file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = {"county_fips", "neighbor_county_fips"} - fieldnames
        if missing_columns:
            raise CountyAdjacencyInputError(
                "missing required county adjacency column(s): "
                f"{', '.join(sorted(missing_columns))}"
            )
        neighbors: dict[str, set[str]] = {}
        for row in reader:
            county_fips = _normalize_county_fips(row["county_fips"], "county_fips")
            neighbor_county_fips = _normalize_county_fips(
                row["neighbor_county_fips"],
                "neighbor_county_fips",
            )
            if county_fips == neighbor_county_fips:
                continue
            neighbors.setdefault(county_fips, set()).add(neighbor_county_fips)
    return {
        county_fips: sorted(county_neighbors)
        for county_fips, county_neighbors in sorted(neighbors.items())
    }


def summarize_neighbor_incidence(
    *,
    county_fips: str,
    years: list[int],
    county_neighbors: dict[str, list[str]],
    incidence_by_county_year: dict[tuple[str, int], float | None],
) -> NeighborIncidenceSummary:
    selected_years = sorted({int(year) for year in years})
    values = []
    years_with_values = set()
    for neighbor_fips in county_neighbors.get(str(county_fips).zfill(5), []):
        for year in selected_years:
            incidence = incidence_by_county_year.get((neighbor_fips, year))
            if incidence is None:
                continue
            values.append(float(incidence))
            years_with_values.add(year)
    if not values:
        return NeighborIncidenceSummary(
            mean_incidence_per_100k=0.0,
            max_incidence_per_100k=0.0,
            neighbor_count=0,
            start_year=None,
            end_year=None,
            year_count=0,
            missing_neighbor_incidence=True,
        )
    return NeighborIncidenceSummary(
        mean_incidence_per_100k=_round(mean(values)),
        max_incidence_per_100k=_round(max(values)),
        neighbor_count=len(values),
        start_year=min(years_with_values),
        end_year=max(years_with_values),
        year_count=len(years_with_values),
        missing_neighbor_incidence=False,
    )


def _adjacency_row(
    county_fips: str,
    neighbor_county_fips: str,
    names_by_fips: dict[str, str],
    segment_count: int,
) -> CountyAdjacency:
    return CountyAdjacency(
        county_fips=county_fips,
        county_name=names_by_fips.get(county_fips, ""),
        neighbor_county_fips=neighbor_county_fips,
        neighbor_county_name=names_by_fips.get(neighbor_county_fips, ""),
        shared_boundary_segment_count=segment_count,
        adjacency_method="shared_boundary_segment",
        feature_quality_flags=MARYLAND_COUNTY_ADJACENCY_FLAG,
    )


def _geometry_segments(
    geometry: dict[str, Any],
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    rings: list[list[list[float]]] = []
    if geometry_type == "Polygon":
        rings.extend(coordinates)
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            rings.extend(polygon)
    segments = []
    for ring in rings:
        points = [_point(point) for point in ring]
        for left, right in zip(points, points[1:], strict=False):
            if left == right:
                continue
            segments.append(tuple(sorted((left, right))))
    return segments


def _point(raw_point: list[float]) -> tuple[float, float]:
    return (round(float(raw_point[0]), 6), round(float(raw_point[1]), 6))


def _normalize_county_fips(value: str, column_name: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value or not raw_value.isdigit() or len(raw_value) > 5:
        raise CountyAdjacencyInputError(
            f"invalid county adjacency {column_name}: {value}"
        )
    return raw_value.zfill(5)


def _round(value: float) -> float:
    return round(float(value), 6)
