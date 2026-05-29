import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_annual_forecast_command_writes_run_and_predictions(tmp_path: Path) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(matrix),
            "--population-path",
            str(population),
            "--target-year",
            "2026",
            "--forecast-origin-year",
            "2024",
            "--min-train-years",
            "2",
            "--as-of-date",
            "2026-05-28",
            "--data-cutoff-date",
            "2024-12-31",
            "--source-vintage",
            "mdh_2024_reviewed_v1",
            "--update-mode",
            "pre_update",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 annual forecast run row(s)" in result.stdout
    assert "annual_forecast_predictions.csv" in result.stdout
    assert (output_dir / "annual_forecast_runs.csv").exists()
    assert (output_dir / "annual_forecast_predictions.csv").exists()

    with (output_dir / "annual_forecast_predictions.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["forecast_year"] for row in rows} == {"2026"}
    assert {row["forecast_origin_year"] for row in rows} == {"2024"}
    assert {row["as_of_date"] for row in rows} == {"2026-05-28"}
    assert {row["data_cutoff_date"] for row in rows} == {"2024-12-31"}
    assert {row["source_vintage"] for row in rows} == {"mdh_2024_reviewed_v1"}
    assert {row["update_mode"] for row in rows} == {"pre_update"}
    assert "analog_year_forecast" in {row["model_name"] for row in rows}
    analog = next(row for row in rows if row["model_name"] == "analog_year_forecast")
    assert analog["model_family"] == "analog"
    assert analog["feature_profile"] == "forecast_safe_analog_years"
    assert analog["weather_mode"] == "not_used_by_forecast_safe_model"
    assert "actual_cases" not in rows[0]
    assert "residual_cases" not in rows[0]
    assert any(
        "no_official_2026_census_denominator" in row["forecast_assumption_flags"]
        for row in rows
    )


def test_annual_forecast_command_fails_cleanly_when_population_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(tmp_path / "missing-matrix.csv"),
            "--population-path",
            str(tmp_path / "missing-population.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Model design matrix file not found" in result.output
    assert "Traceback" not in result.output


def test_annual_forecast_command_rejects_non_future_target_year(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(matrix),
            "--population-path",
            str(population),
            "--target-year",
            "2024",
            "--forecast-origin-year",
            "2024",
            "--min-train-years",
            "2",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "target-year must be greater than forecast-origin-year" in result.output
    assert "Traceback" not in result.output


def test_annual_forecast_command_rejects_unknown_update_mode(tmp_path: Path) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(matrix),
            "--population-path",
            str(population),
            "--target-year",
            "2026",
            "--forecast-origin-year",
            "2024",
            "--min-train-years",
            "2",
            "--update-mode",
            "post_update",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "update-mode must be one of" in result.output
    assert "Traceback" not in result.output


def test_annual_forecast_command_fails_cleanly_for_malformed_matrix(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")
    rows = list(csv.DictReader(matrix.open(encoding="utf-8", newline="")))
    rows[0]["target_total_cases"] = "not-a-number"
    _write_rows(matrix, rows)

    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(matrix),
            "--population-path",
            str(population),
            "--target-year",
            "2026",
            "--forecast-origin-year",
            "2024",
            "--min-train-years",
            "2",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "invalid annual forecast design matrix" in result.output
    assert "Traceback" not in result.output


def test_annual_forecast_command_fails_cleanly_for_malformed_population(
    tmp_path: Path,
) -> None:
    matrix = _write_design_matrix(tmp_path / "design_matrix.csv")
    population = _write_population(tmp_path / "population.csv")
    rows = list(csv.DictReader(population.open(encoding="utf-8", newline="")))
    rows[0]["population"] = "not-a-number"
    _write_rows(population, rows)

    result = runner.invoke(
        app,
        [
            "etl",
            "annual-forecast",
            "--design-matrix-path",
            str(matrix),
            "--population-path",
            str(population),
            "--target-year",
            "2026",
            "--forecast-origin-year",
            "2024",
            "--min-train-years",
            "2",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "population must be an integer" in result.output
    assert "Traceback" not in result.output


def _write_design_matrix(path: Path) -> Path:
    rows = []
    for county_fips, values in {
        "24001": [10, 20, 30, 40],
        "24003": [80, 60, 40, 20],
    }.items():
        for offset, incidence in enumerate(values):
            year = 2021 + offset
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": f"County {county_fips}",
                    "year": str(year),
                    "target_total_cases": str(incidence),
                    "target_lyme_incidence_per_100k": str(float(incidence)),
                    "target_population": "100000",
                    "feature_prior_year_lyme_incidence_per_100k": str(
                        float(values[offset - 1] if offset else 0)
                    ),
                    "feature_trailing_history_years": str(offset),
                    "model_feature_quality_flags": "",
                }
            )
    _write_rows(path, rows)
    return path


def _write_population(path: Path) -> Path:
    _write_rows(
        path,
        [
            {
                "county_fips": "24001",
                "county_name": "County 24001",
                "year": "2026",
                "population": "110000",
                "source_id": "regional_population_linear_projection",
                "vintage": "2025",
                "feature_quality_flags": (
                    "simple_linear_population_projection,"
                    "no_official_2026_census_denominator"
                ),
            },
            {
                "county_fips": "24003",
                "county_name": "County 24003",
                "year": "2026",
                "population": "90000",
                "source_id": "regional_population_linear_projection",
                "vintage": "2025",
                "feature_quality_flags": (
                    "simple_linear_population_projection,"
                    "no_official_2026_census_denominator"
                ),
            },
        ],
    )
    return path


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
