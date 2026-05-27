import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_model_design_matrix_command_writes_matrix_and_schema(tmp_path: Path) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--lookback-years",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    matrix_path = output_dir / "model_design_matrix_county_year.csv"
    schema_path = output_dir / "model_design_matrix_schema.json"
    assert result.exit_code == 0
    assert "Wrote 1 model design matrix row(s)" in result.stdout
    assert matrix_path.exists()
    assert schema_path.exists()

    with matrix_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["feature_prior_year_lyme_incidence_per_100k"] == "10.0"
    assert rows[0]["feature_weather_temp_mean_f"] == "51.0"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["lookback_years"] == 1
    assert "feature_prior_year_lyme_incidence_per_100k" in schema["feature_columns"]


def test_model_design_matrix_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Model features file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_design_matrix_county_year.csv").exists()


def test_model_design_matrix_command_fails_cleanly_for_malformed_input(
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
            "model-design-matrix",
            "--model-features-path",
            str(malformed),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "missing required model feature column(s):" in result.output
    assert "lyme_incidence_per_100k" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_design_matrix_county_year.csv").exists()


def _write_feature_matrix(path: Path) -> Path:
    rows = []
    for year, cases in [(2019, 10), (2020, 20)]:
        rows.append(
            {
                "county_fips": "24003",
                "county_name": "Anne Arundel County",
                "year": str(year),
                "total_cases": str(cases),
                "population": "100000",
                "lyme_incidence_per_100k": str(float(cases)),
                "weather_temp_mean_f": str(50 + (year - 2019)),
                "weather_precip_total_mm": "1000",
                "deer_harvest_per_sqmi_prior_season": "",
                "ixodes_scapularis_status": "established",
                "borrelia_burgdorferi_status": "present",
                "model_feature_quality_flags": "missing_deer_harvest_prior_season",
            }
        )
    return _write_rows(path, rows)


def _write_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
