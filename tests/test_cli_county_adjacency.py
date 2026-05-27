import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_county_adjacency_command_writes_neighbor_output(tmp_path: Path) -> None:
    geojson = tmp_path / "counties.geojson"
    geojson.write_text(json.dumps(_county_geojson()), encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "county-adjacency",
            "--county-geojson-path",
            str(geojson),
            "--output-dir",
            str(output_dir),
        ],
    )

    output = output_dir / "md_county_adjacency.csv"
    assert result.exit_code == 0
    assert "Wrote 2 county adjacency row(s)" in result.stdout
    assert output.exists()
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24001"
    assert rows[0]["neighbor_county_fips"] == "24003"


def test_county_adjacency_command_fails_cleanly_when_geojson_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "county-adjacency",
            "--county-geojson-path",
            str(tmp_path / "missing.geojson"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "County GeoJSON file not found" in result.output
    assert "Traceback" not in result.output


def _county_geojson() -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            _feature("24001", "Alpha County", [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]),
            _feature("24003", "Beta County", [[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]),
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
