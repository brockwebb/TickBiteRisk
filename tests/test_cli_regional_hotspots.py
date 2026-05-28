from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_hotspots import _write_hotspot_panel
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_hotspots_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_hotspot_panel(tmp_path / "regional.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-hotspots",
            "--regional-lyme-path",
            str(panel),
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "midatlantic_hotspot_county_year.csv" in result.stdout
    assert (output_dir / "midatlantic_hotspot_county_year.csv").exists()
    assert (output_dir / "midatlantic_hotspot_summary.csv").exists()


def test_regional_hotspots_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-hotspots",
            "--regional-lyme-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional Lyme panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
