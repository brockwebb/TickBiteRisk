import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_county_adjacency_command_writes_cross_border_output(
    tmp_path: Path,
) -> None:
    geojson = tmp_path / "regional_counties.geojson"
    geojson.write_text(json.dumps(_regional_county_geojson()), encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-county-adjacency",
            "--county-geojson-path",
            str(geojson),
            "--output-dir",
            str(output_dir),
        ],
    )

    output = output_dir / "regional_county_adjacency.csv"
    assert result.exit_code == 0
    assert "Wrote 2 regional county adjacency row(s)" in result.stdout
    assert output.exists()
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24001"
    assert rows[0]["neighbor_county_fips"] == "42001"
    assert rows[0]["feature_quality_flags"] == "regional_county_adjacency_from_geojson"


def test_regional_county_adjacency_command_fails_cleanly_when_geojson_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "regional-county-adjacency",
            "--county-geojson-path",
            str(tmp_path / "missing.geojson"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Regional county GeoJSON file not found" in result.output
    assert "Traceback" not in result.output


def test_regional_county_adjacency_fetch_mode_writes_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_regional_county_geojson_text",
        lambda source_url: json.dumps(_tigerweb_county_geojson()),
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-county-adjacency",
            "--fetch-census-geojson",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote acquisition provenance manifest" in result.stdout
    assert (output_dir / "regional_counties.geojson").exists()
    assert (output_dir / "regional_county_adjacency.csv").exists()
    provenance = output_dir / "acquisition_provenance.csv"
    assert provenance.exists()
    with provenance.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_id"] == "census_tigerweb_midatlantic_county_geojson"
    assert "regional_counties.geojson" in rows[0]["derived_artifact_paths"]
    assert "regional_county_adjacency.csv" in rows[0]["derived_artifact_paths"]


def test_regional_county_adjacency_fetch_mode_rejects_partial_footprint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_regional_county_geojson_text",
        lambda source_url: json.dumps(_partial_tigerweb_county_geojson()),
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-county-adjacency",
            "--fetch-census-geojson",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Regional county GeoJSON footprint incomplete" in result.output
    assert not (output_dir / "regional_counties.geojson").exists()
    assert not (output_dir / "acquisition_provenance.csv").exists()


def _regional_county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _feature(county_fips, county_name, _ring(county_fips, index))
            for index, (county_fips, county_name) in enumerate(_regional_counties())
        ],
    }


def _tigerweb_county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _tigerweb_feature(
                county_fips,
                county_fips[:2],
                county_name,
                _ring(county_fips, index),
            )
            for index, (county_fips, county_name) in enumerate(_regional_counties())
        ],
    }


def _partial_tigerweb_county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _tigerweb_feature(
                county_fips,
                county_fips[:2],
                county_name,
                _ring(county_fips, index),
            )
            for index, (county_fips, county_name) in enumerate(
                [("24001", "Maryland Edge County"), ("42001", "Pennsylvania Edge County")]
            )
        ],
    }


def _regional_counties() -> list[tuple[str, str]]:
    state_counts = {
        "10": 3,
        "11": 1,
        "24": 24,
        "42": 67,
        "51": 133,
        "54": 55,
    }
    counties = []
    for state_fips, count in state_counts.items():
        for index in range(1, count + 1):
            county_fips = f"{state_fips}{index:03d}"
            counties.append((county_fips, f"State {state_fips} County {index}"))
    return counties


def _ring(county_fips: str, index: int) -> list[list[float]]:
    if county_fips == "24001":
        return [[0, 0], [1, 0], [1, 1], [0, 0]]
    if county_fips == "42001":
        return [[1, 0], [2, 0], [1, 1], [1, 0]]
    offset = 1000 + (index * 10)
    return [[offset, 0], [offset + 1, 0], [offset, 1], [offset, 0]]


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


def _tigerweb_feature(
    county_fips: str,
    state_fips: str,
    county_name: str,
    ring: list[list[float]],
) -> dict[str, object]:
    return {
        "type": "Feature",
        "properties": {
            "GEOID": county_fips,
            "STATE": state_fips,
            "COUNTY": county_fips[2:],
            "NAME": county_name,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    }
