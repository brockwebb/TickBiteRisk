import csv

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_enviroatlas_habitat_command_writes_county_habitat_output(
    tmp_path,
    monkeypatch,
) -> None:
    response_json = {
        "features": [
            {
                "attributes": {
                    "GEOID": "24001",
                    "NAMELSAD": "Allegany County",
                    "pfor": 70,
                    "pfor90": 72,
                    "pwetl": 2,
                    "pwetl95": 0.5,
                    "pdev": 9,
                    "Pimprv": 3,
                    "pagr": 15,
                    "pagrp": 12,
                    "pagrc": 3,
                    "rNI45": 81,
                    "rfor45": 76,
                    "rfor9045": 78,
                    "NINDEX": 84,
                }
            }
        ]
    }

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_enviroatlas_json",
        lambda url: response_json,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "enviroatlas-habitat",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 EnviroAtlas county habitat row(s)" in result.stdout
    assert (tmp_path / "out" / "enviroatlas_county_habitat.csv").exists()
    manifest_path = tmp_path / "out" / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_id"] == "epa_enviroatlas_habitat"
    assert rows[0]["source_url"].startswith(
        "https://enviroatlas.epa.gov/arcgis/rest/services/"
    )
    assert rows[0]["citation_url"] == "https://www.epa.gov/enviroatlas/data-download"
    assert rows[0]["request_method"] == "GET"
    assert rows[0]["parser_method"] == "parse_enviroatlas_county_habitat"
    assert rows[0]["extraction_quality"] == "accepted"
    assert rows[0]["row_count"] == "1"
    assert "tickbiterisk etl enviroatlas-habitat" in rows[0]["acquisition_command"]
    assert "enviroatlas_county_habitat.csv=" in rows[0]["derived_artifact_sha256s"]
