import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_model_backtest_command_writes_predictions_and_metrics(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(feature_matrix),
            "--start-year",
            "2020",
            "--min-train-years",
            "2",
            "--lookback-years",
            "2",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 24 backtest prediction row(s)" in result.stdout
    assert "Wrote 16 backtest metric row(s)" in result.stdout
    assert "Wrote 1 backtest run row(s)" in result.stdout
    assert (output_dir / "model_backtest_runs.csv").exists()
    assert (output_dir / "model_backtest_predictions.csv").exists()
    assert (output_dir / "model_backtest_metrics.csv").exists()

    with (output_dir / "model_backtest_predictions.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["model_name"] == "county_trailing_mean_incidence"
    assert rows[0]["evaluation_mode"] == "forecast_prior_year"


def test_model_backtest_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Model features file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_backtest_predictions.csv").exists()


def test_model_backtest_command_validates_training_options(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(feature_matrix),
            "--min-train-years",
            "0",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "min-train-years must be at least 1" in result.output
    assert "Traceback" not in result.output


def test_model_backtest_command_validates_year_bounds(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(feature_matrix),
            "--start-year",
            "2022",
            "--end-year",
            "2020",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "start-year must be less than or equal to end-year" in result.output
    assert "Traceback" not in result.output


def test_model_backtest_command_fails_cleanly_when_years_outside_input(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "features.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(feature_matrix),
            "--start-year",
            "2030",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "start-year must be between input years 2018 and 2022" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_backtest_runs.csv").exists()

    result = runner.invoke(
        app,
        [
            "etl",
            "model-backtest",
            "--model-features-path",
            str(feature_matrix),
            "--start-year",
            "2020",
            "--end-year",
            "2030",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "end-year must be between input years 2018 and 2022" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_backtest_runs.csv").exists()


def _write_feature_matrix(path: Path) -> Path:
    rows = []
    values = {
        "24001": [10, 20, 30, 40, 50],
        "24003": [100, 80, 60, 40, 20],
    }
    for county_fips, cases_by_year in values.items():
        for offset, cases in enumerate(cases_by_year):
            year = 2018 + offset
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(year),
                    "total_cases": str(cases),
                    "population": "100000",
                    "lyme_incidence_per_100k": str(cases),
                    "model_feature_quality_flags": "",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
