from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_incidence_clusters import _write_incidence_panel
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_incidence_clusters_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-clusters",
            "--regional-incidence-path",
            str(panel),
            "--start-year",
            "2021",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--n-clusters",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_incidence_cluster_county_year.csv" in result.stdout
    assert (output_dir / "regional_incidence_cluster_runs.csv").exists()
    assert (output_dir / "regional_incidence_cluster_county_year.csv").exists()
    assert (output_dir / "regional_incidence_cluster_summary.csv").exists()


def test_regional_incidence_clusters_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-clusters",
            "--regional-incidence-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional incidence panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
