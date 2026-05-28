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


def test_model_design_matrix_command_accepts_county_adjacency_path(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_two_county_feature_matrix(tmp_path / "model_features.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--county-adjacency-path",
            str(adjacency),
            "--lookback-years",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "model_design_matrix_county_year.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    anne_2020 = next(row for row in rows if row["county_fips"] == "24003")
    assert anne_2020["feature_neighbor_prior_year_lyme_incidence_mean"] == "30.0"

    schema = json.loads(
        (output_dir / "model_design_matrix_schema.json").read_text(encoding="utf-8")
    )
    assert schema["spatial_neighbor_source_path"] == str(adjacency)


def test_model_design_matrix_command_accepts_regional_signals_path(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_two_county_feature_matrix(tmp_path / "model_features.csv")
    regional_signals = _write_regional_signals(tmp_path / "regional_signals.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--regional-signals-path",
            str(regional_signals),
            "--lookback-years",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "model_design_matrix_county_year.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    anne_2020 = next(row for row in rows if row["county_fips"] == "24003")
    assert anne_2020["feature_regional_prior_year_midatlantic_total_cases"] == "80.0"
    assert anne_2020["feature_flag_regional_signal_candidate"] == "1"

    schema = json.loads(
        (output_dir / "model_design_matrix_schema.json").read_text(encoding="utf-8")
    )
    assert schema["regional_signal_source_path"] == str(regional_signals)


def test_model_design_matrix_command_accepts_regional_incidence_clusters_path(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_two_county_feature_matrix(tmp_path / "model_features.csv")
    regional_clusters = _write_regional_incidence_clusters(
        tmp_path / "regional_incidence_clusters.csv"
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--regional-incidence-clusters-path",
            str(regional_clusters),
            "--lookback-years",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "model_design_matrix_county_year.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    anne_2020 = next(row for row in rows if row["county_fips"] == "24003")
    assert anne_2020["feature_regional_incidence_cluster_rank"] == "2.0"
    assert anne_2020["feature_regional_incidence_cluster_band_moderate"] == "1"
    assert anne_2020["feature_missing_regional_incidence_cluster"] == "0"

    schema = json.loads(
        (output_dir / "model_design_matrix_schema.json").read_text(encoding="utf-8")
    )
    assert schema["regional_incidence_cluster_source_path"] == str(regional_clusters)


def test_model_design_matrix_command_fails_cleanly_when_regional_signals_missing(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--regional-signals-path",
            str(tmp_path / "missing-regional-signals.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Regional signals file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_design_matrix_county_year.csv").exists()


def test_model_design_matrix_command_fails_cleanly_when_regional_clusters_missing(
    tmp_path: Path,
) -> None:
    feature_matrix = _write_feature_matrix(tmp_path / "model_features.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "model-design-matrix",
            "--model-features-path",
            str(feature_matrix),
            "--regional-incidence-clusters-path",
            str(tmp_path / "missing-regional-clusters.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Regional incidence clusters file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "model_design_matrix_county_year.csv").exists()


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


def _write_two_county_feature_matrix(path: Path) -> Path:
    rows = []
    for county_fips, county_name, cases_by_year in [
        ("24003", "Anne Arundel County", {2019: 10, 2020: 20}),
        ("24005", "Baltimore County", {2019: 30, 2020: 40}),
    ]:
        for year, cases in cases_by_year.items():
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": county_name,
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


def _write_adjacency(path: Path) -> Path:
    rows = [
        {
            "county_fips": "24003",
            "neighbor_county_fips": "24005",
        },
        {
            "county_fips": "24005",
            "neighbor_county_fips": "24003",
        },
    ]
    return _write_rows(path, rows)


def _write_regional_signals(path: Path) -> Path:
    rows = []
    for county_fips, county_name in [
        ("24003", "Anne Arundel County"),
        ("24005", "Baltimore County"),
    ]:
        for year in [2019, 2020]:
            rows.append(
                {
                    "state_fips": "24",
                    "state_abbr": "MD",
                    "state_name": "Maryland",
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": "20",
                    "diagnostic_state_total_cases": "60",
                    "diagnostic_midatlantic_total_cases": "100",
                    "diagnostic_county_share_of_state_cases": "0.25",
                    "diagnostic_county_share_of_midatlantic_cases": "0.2",
                    "feature_prior_year_total_cases": "20",
                    "feature_prior_year_county_share_of_state_cases": "0.333333",
                    "feature_prior_year_county_share_of_midatlantic_cases": "0.25",
                    "feature_prior_year_state_total_cases": "60",
                    "feature_prior_year_midatlantic_total_cases": "80",
                    "feature_trailing_5yr_midatlantic_total_min": "70",
                    "feature_trailing_5yr_midatlantic_total_mean": "75",
                    "feature_trailing_5yr_midatlantic_total_max": "80",
                    "diagnostic_midatlantic_total_within_trailing_5yr_band": "False",
                    "source_panel_sha256": "abc123",
                    "feature_quality_flags": "regional_signal_candidate",
                }
            )
    return _write_rows(path, rows)


def _write_regional_incidence_clusters(path: Path) -> Path:
    rows = []
    for year in [2019, 2020]:
        rows.append(
            {
                "county_fips": "24003",
                "year": str(year),
                "cluster_rank": "2",
                "cluster_label": "moderate",
                "cluster_centroid_prior_mean_incidence_per_100k": "12.5",
                "feature_prior_mean_incidence_per_100k": "10.0",
                "feature_prior_min_incidence_per_100k": "5.0",
                "feature_prior_max_incidence_per_100k": "20.0",
                "feature_prior_sd_incidence_per_100k": "4.5",
                "feature_prior_year_incidence_per_100k": "10.0",
                "train_start_year": "2015",
                "train_end_year": "2019",
                "train_year_count": "5",
                "actual_incidence_per_100k": "999.0",
                "actual_cases": "999",
                "actual_population": "100000",
                "model_feature_quality_flags": (
                    "regional_incidence_cluster_candidate,"
                    "diagnostic_same_year_not_forecast_feature"
                ),
            }
        )
    return _write_rows(path, rows)


def _write_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
