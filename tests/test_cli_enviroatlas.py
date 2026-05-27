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
