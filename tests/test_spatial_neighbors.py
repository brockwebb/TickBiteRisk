import csv
import json
from pathlib import Path

import pytest

from tickbiterisk.modeling.spatial_neighbors import (
    build_county_adjacency_from_geojson,
    CountyAdjacencyInputError,
    read_county_neighbors,
    summarize_neighbor_incidence,
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


def test_read_county_neighbors_orders_dedupes_and_skips_self_edges(
    tmp_path: Path,
) -> None:
    adjacency = tmp_path / "regional_county_adjacency.csv"
    _write_adjacency_csv(
        adjacency,
        [
            ("24001", "42001"),
            ("24001", "42001"),
            ("24001", "24001"),
            ("42001", "24001"),
            ("42001", "54001"),
        ],
    )

    neighbors = read_county_neighbors(adjacency)

    assert neighbors == {
        "24001": ["42001"],
        "42001": ["24001", "54001"],
    }


@pytest.mark.parametrize(
    ("county_fips", "neighbor_county_fips"),
    [
        ("", "42001"),
        ("24001", "bad"),
    ],
)
def test_read_county_neighbors_rejects_malformed_fips_values(
    tmp_path: Path,
    county_fips: str,
    neighbor_county_fips: str,
) -> None:
    adjacency = tmp_path / "regional_county_adjacency.csv"
    _write_adjacency_csv(adjacency, [(county_fips, neighbor_county_fips)])

    with pytest.raises(CountyAdjacencyInputError, match="invalid county adjacency"):
        read_county_neighbors(adjacency)


def test_summarize_neighbor_incidence_uses_only_requested_years(
    tmp_path: Path,
) -> None:
    adjacency = tmp_path / "regional_county_adjacency.csv"
    _write_adjacency_csv(adjacency, [("24001", "42001")])
    neighbors = read_county_neighbors(adjacency)

    summary = summarize_neighbor_incidence(
        county_fips="24001",
        years=[2020],
        county_neighbors=neighbors,
        incidence_by_county_year={
            ("42001", 2020): 50.0,
            ("42001", 2021): 999.0,
        },
    )

    assert summary.mean_incidence_per_100k == 50.0
    assert summary.max_incidence_per_100k == 50.0
    assert summary.neighbor_count == 1
    assert summary.start_year == 2020
    assert summary.end_year == 2020
    assert summary.year_count == 1
    assert summary.missing_neighbor_incidence is False


def test_summarize_neighbor_incidence_marks_missing_without_neighbor_history(
    tmp_path: Path,
) -> None:
    adjacency = tmp_path / "regional_county_adjacency.csv"
    _write_adjacency_csv(adjacency, [("24001", "42001")])
    neighbors = read_county_neighbors(adjacency)

    summary = summarize_neighbor_incidence(
        county_fips="24001",
        years=[2020],
        county_neighbors=neighbors,
        incidence_by_county_year={("42001", 2021): 999.0},
    )

    assert summary.mean_incidence_per_100k == 0.0
    assert summary.max_incidence_per_100k == 0.0
    assert summary.neighbor_count == 0
    assert summary.start_year is None
    assert summary.end_year is None
    assert summary.year_count == 0
    assert summary.missing_neighbor_incidence is True


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


def _write_adjacency_csv(path: Path, pairs: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "county_fips",
                "neighbor_county_fips",
            ],
        )
        writer.writeheader()
        for county_fips, neighbor_county_fips in pairs:
            writer.writerow(
                {
                    "county_fips": county_fips,
                    "neighbor_county_fips": neighbor_county_fips,
                }
            )
