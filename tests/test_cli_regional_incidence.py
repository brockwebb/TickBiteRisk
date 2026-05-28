from pathlib import Path

from typer.testing import CliRunner

from tests.test_regional_incidence import _write_regional_lyme, _write_regional_population
from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_incidence_command_writes_outputs(tmp_path: Path) -> None:
    lyme_path = _write_regional_lyme(tmp_path / "lyme.csv")
    population_path = _write_regional_population(tmp_path / "population.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence",
            "--regional-lyme-path",
            str(lyme_path),
            "--regional-population-path",
            str(population_path),
            "--output-dir",
            str(output_dir),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code == 0
    assert "midatlantic_lyme_incidence_county_year.csv" in result.stdout
    assert (output_dir / "midatlantic_lyme_incidence_county_year.csv").exists()
    assert (output_dir / "midatlantic_lyme_incidence_summary.csv").exists()


def test_regional_incidence_command_fails_cleanly_when_population_missing(
    tmp_path: Path,
) -> None:
    lyme_path = _write_regional_lyme(tmp_path / "lyme.csv")
    missing_path = tmp_path / "missing.csv"

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-incidence",
            "--regional-lyme-path",
            str(lyme_path),
            "--regional-population-path",
            str(missing_path),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        env={"COLUMNS": "200"},
    )

    assert result.exit_code != 0
    assert f"Regional population panel not found: {missing_path}" in result.output
    assert "Traceback" not in result.output
