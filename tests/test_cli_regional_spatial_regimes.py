from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_spatial_regimes import (
    _write_adjacency,
    _write_incidence_panel,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_spatial_regimes_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-spatial-regimes",
            "--regional-incidence-path",
            str(panel),
            "--regional-adjacency-path",
            str(adjacency),
            "--start-year",
            "2021",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_spatial_regime_county_year.csv" in result.stdout
    assert (output_dir / "regional_spatial_regime_runs.csv").exists()
    assert (output_dir / "regional_spatial_regime_county_year.csv").exists()
    assert (output_dir / "regional_spatial_regime_summary.csv").exists()


def test_regional_spatial_regimes_command_fails_cleanly_when_incidence_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-spatial-regimes",
            "--regional-incidence-path",
            str(missing_path),
            "--regional-adjacency-path",
            str(adjacency),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional incidence panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output


def test_regional_spatial_regimes_command_fails_cleanly_when_adjacency_missing(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    missing_path = tmp_path / "missing_adjacency.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-spatial-regimes",
            "--regional-incidence-path",
            str(panel),
            "--regional-adjacency-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional adjacency file not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
