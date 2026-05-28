import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_model_compare_command_writes_runs_predictions_metrics_and_summary(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-compare",
            "--design-matrix-path",
            str(matrix),
            "--start-year",
            "2021",
            "--min-train-years",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 model comparison run row(s)" in result.stdout
    assert "model_comparison_predictions.csv" in result.stdout
    assert "model_comparison_intervals.csv" in result.stdout
    assert (output_dir / "model_comparison_runs.csv").exists()
    assert (output_dir / "model_comparison_predictions.csv").exists()
    assert (output_dir / "model_comparison_intervals.csv").exists()
    assert (output_dir / "model_comparison_metrics.csv").exists()
    assert (output_dir / "model_comparison_summary.csv").exists()

    with (output_dir / "model_comparison_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        summary = list(csv.DictReader(handle))
    assert {row["model_name"] for row in summary} == {
        "analog_year_forecast",
        "empirical_bayes_shrinkage",
        "linear_blend_baseline",
        "prior_year_incidence",
        "ridge_forecast_ecology",
        "ridge_forecast_safe",
        "ridge_lag_weather_ecology",
        "trailing_mean_incidence",
    }


def test_model_compare_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "model-compare",
            "--design-matrix-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Model design matrix file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_comparison_predictions.csv").exists()


def test_model_compare_command_fails_cleanly_for_malformed_input(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.csv"
    _write_rows(
        malformed,
        [
            {"county_fips": "24003", "year": "2020"},
            {"county_fips": "24003", "year": "2021"},
        ],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "model-compare",
            "--design-matrix-path",
            str(malformed),
            "--start-year",
            "2021",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "missing required model comparison column(s):" in result.output
    assert "target_lyme_incidence_per_100k" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_comparison_predictions.csv").exists()


def _write_design_matrix(path: Path) -> Path:
    rows = []
    for county_fips, values in {
        "24001": [10, 20, 30],
        "24003": [100, 80, 60],
    }.items():
        for offset, cases in enumerate(values):
            year = 2019 + offset
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(year),
                    "target_total_cases": str(cases),
                    "target_lyme_incidence_per_100k": str(float(cases)),
                    "target_population": "100000",
                    "feature_prior_year_lyme_incidence_per_100k": str(
                        float(values[offset - 1] if offset else 0)
                    ),
                    "feature_trailing_2yr_mean_lyme_incidence_per_100k": str(
                        float(sum(values[:offset]) / offset if offset else 0)
                    ),
                    "feature_trailing_history_years": str(offset),
                    "feature_state_prior_year_lyme_incidence_per_100k": "50",
                    "feature_weather_temp_mean_f": str(45 + offset),
                    "model_feature_quality_flags": "",
                }
            )
    return _write_rows(path, rows)


def _write_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
