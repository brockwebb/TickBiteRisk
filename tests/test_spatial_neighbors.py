import csv
import json
from pathlib import Path

from tickbiterisk.modeling.spatial_neighbors import (
    build_county_adjacency_from_geojson,
    write_county_adjacency_output,
    write_regional_county_adjacency_output,
)


def test_build_county_adjacency_from_geojson_uses_shared_edges_only(
    tmp_path: Path,
) -> None:
    geojson = tmp_path / "counties.geojson"
    geojson.write_text(json.dumps(_county_geojson()), encoding="utf-8")

    rows = build_county_adjacency_from_geojson(geojson)

    pairs = {(row.county_fips, row.neighbor_county_fips) for row in rows}
    assert pairs == {
        ("24001", "24003"),
        ("24003", "24001"),
        ("24003", "24005"),
        ("24005", "24003"),
    }
    assert all(row.adjacency_method == "shared_boundary_segment" for row in rows)
    assert all(row.shared_boundary_segment_count == 1 for row in rows)
    assert all("county_adjacency_from_geojson" in row.feature_quality_flags for row in rows)


def test_write_county_adjacency_output_orders_and_dedupes(tmp_path: Path) -> None:
    geojson = tmp_path / "counties.geojson"
    geojson.write_text(json.dumps(_county_geojson()), encoding="utf-8")
    rows = build_county_adjacency_from_geojson(geojson)

    output = write_county_adjacency_output([*rows, rows[0]], tmp_path / "out")

    with output.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    assert output.name == "md_county_adjacency.csv"
    assert [(row["county_fips"], row["neighbor_county_fips"]) for row in records] == [
        ("24001", "24003"),
        ("24003", "24001"),
        ("24003", "24005"),
        ("24005", "24003"),
    ]


def test_write_regional_county_adjacency_output_preserves_cross_state_edges(
    tmp_path: Path,
) -> None:
    geojson = tmp_path / "counties.geojson"
    geojson.write_text(json.dumps(_regional_county_geojson()), encoding="utf-8")
    rows = build_county_adjacency_from_geojson(geojson)

    output = write_regional_county_adjacency_output([*rows, rows[0]], tmp_path / "out")

    with output.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    assert output.name == "regional_county_adjacency.csv"
    assert [
        (row["county_fips"], row["neighbor_county_fips"])
        for row in records
    ] == [
        ("24001", "42001"),
        ("42001", "24001"),
    ]
    assert {
        row["feature_quality_flags"]
        for row in records
    } == {"regional_county_adjacency_from_geojson"}


def _county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _feature("24001", "Alpha County", [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]),
            _feature("24003", "Beta County", [[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]),
            _feature("24005", "Gamma County", [[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]),
            _feature("24007", "Point County", [[3, 1], [4, 1], [4, 2], [3, 2], [3, 1]]),
        ],
    }


def _regional_county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _feature("24001", "Maryland Edge County", [[0, 0], [1, 0], [1, 1], [0, 0]]),
            _feature("42001", "Pennsylvania Edge County", [[1, 0], [2, 0], [1, 1], [1, 0]]),
        ],
    }


def _feature(county_fips: str, county_name: str, ring: list[list[float]]) -> dict[str, object]:
    return {
        "type": "Feature",
        "properties": {
            "county_fips": county_fips,
            "county_name": county_name,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    }
