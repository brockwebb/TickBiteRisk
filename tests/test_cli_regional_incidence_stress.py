import csv
from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_incidence_stress import (
    _sha256_file,
    _write_incidence_panel,
    _write_regional_adjacency,
    _write_spatial_regimes,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_incidence_stress_command_writes_outputs(tmp_path: Path) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
            "--regional-incidence-path",
            str(panel),
            "--start-year",
            "2021",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--random-forest-n-estimators",
            "5",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "regional_incidence_stress_predictions.csv" in result.stdout
    assert (output_dir / "regional_incidence_stress_runs.csv").exists()
    assert (output_dir / "regional_incidence_stress_predictions.csv").exists()
    assert (output_dir / "regional_incidence_stress_metrics.csv").exists()

    run_header = (output_dir / "regional_incidence_stress_runs.csv").read_text(
        encoding="utf-8"
    ).splitlines()[0]
    assert "random_forest_n_estimators" in run_header


def test_regional_incidence_stress_command_accepts_regional_adjacency(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    adjacency = _write_regional_adjacency(tmp_path / "regional_adjacency.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
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
            "--random-forest-n-estimators",
            "5",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    with (output_dir / "regional_incidence_stress_predictions.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert "spatial_prior_year_neighbor_incidence" in {
        row["model_name"] for row in rows
    }

    with (output_dir / "regional_incidence_stress_runs.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        run = next(csv.DictReader(handle))
    assert run["regional_adjacency_path"] == str(adjacency)
    assert len(run["regional_adjacency_sha256"]) == 64


def test_regional_incidence_stress_command_accepts_spatial_regimes(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    regimes = _write_spatial_regimes(
        tmp_path / "regional_spatial_regimes.csv",
        source_file_sha256=_sha256_file(panel),
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
            "--regional-incidence-path",
            str(panel),
            "--regional-spatial-regimes-path",
            str(regimes),
            "--start-year",
            "2021",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--random-forest-n-estimators",
            "5",
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    with (output_dir / "regional_incidence_stress_predictions.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert "empirical_bayes_spatial_regime_incidence" in {
        row["model_name"] for row in rows
    }

    with (output_dir / "regional_incidence_stress_runs.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        run = next(csv.DictReader(handle))
    assert run["regional_spatial_regimes_path"] == str(regimes)
    assert len(run["regional_spatial_regimes_sha256"]) == 64


def test_regional_incidence_stress_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
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


def test_regional_incidence_stress_command_fails_cleanly_when_adjacency_missing(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    missing_adjacency = tmp_path / "missing_adjacency.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
            "--regional-incidence-path",
            str(panel),
            "--regional-adjacency-path",
            str(missing_adjacency),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional adjacency file not found: {missing_adjacency}" in result.output
    assert "Traceback" not in result.output


def test_regional_incidence_stress_command_fails_cleanly_when_regimes_missing(
    tmp_path: Path,
) -> None:
    panel = _write_incidence_panel(tmp_path / "incidence.csv")
    missing_regimes = tmp_path / "missing_regimes.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence-stress",
            "--regional-incidence-path",
            str(panel),
            "--regional-spatial-regimes-path",
            str(missing_regimes),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional spatial regimes file not found: {missing_regimes}" in (
        result.output
    )
    assert "Traceback" not in result.output
