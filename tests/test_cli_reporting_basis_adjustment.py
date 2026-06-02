import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_reporting_basis_adjustment_command_writes_artifacts(
    tmp_path: Path,
) -> None:
    incidence = _write_regional_incidence(tmp_path / "regional_incidence.csv")
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")
    control_panel = _write_did_control_panel(tmp_path / "did_control_candidates.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "reporting-basis-adjustment",
            "--regional-incidence-path",
            str(incidence),
            "--county-adjacency-path",
            str(adjacency),
            "--did-control-panel-path",
            str(control_panel),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "reporting_basis_adjustment.csv" in result.stdout
    adjustment_path = output_dir / "reporting_basis_adjustment.csv"
    classification_path = output_dir / "high_incidence_classification.csv"
    control_path = output_dir / "did_control_panel.csv"
    run_path = output_dir / "reporting_basis_adjustment_runs.csv"
    assert adjustment_path.exists()
    assert classification_path.exists()
    assert control_path.exists()
    assert run_path.exists()

    with adjustment_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_scope_regime = {
        (row["jurisdiction_scope"], row["source_regime"]): row
        for row in rows
    }
    assert by_scope_regime[
        ("county_24001", "pre_2020_baseline")
    ]["multiplicative_factor"] == "1.818182"
    assert by_scope_regime[
        ("county_54001", "pre_2020_baseline")
    ]["multiplicative_factor"] == "1.818182"
    assert by_scope_regime[
        ("county_24001", "case_definition_change_2022_plus")
    ]["multiplicative_factor"] == "1.0"
    with control_path.open(newline="", encoding="utf-8") as handle:
        control_rows = list(csv.DictReader(handle))
    assert {row["candidate_state_fips"] for row in control_rows} == {"13", "40"}


def test_reporting_basis_adjustment_command_fails_cleanly_when_input_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "reporting-basis-adjustment",
            "--regional-incidence-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Regional incidence file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "reporting_basis_adjustment.csv").exists()


def _write_regional_incidence(path: Path) -> Path:
    rows = []
    series = {
        ("24", "24001"): [20, 20, 20, 40],
        ("24", "24003"): [20, 20, 20, 40],
        ("54", "54001"): [12, 12, 12, 24],
        ("54", "54003"): [12, 12, 12, 24],
    }
    for (state_fips, county_fips), incidences in series.items():
        for year, incidence in zip([2017, 2018, 2019, 2022], incidences):
            rows.append(
                {
                    "state_fips": state_fips,
                    "county_fips": county_fips,
                    "year": str(year),
                    "total_cases": str(int(float(incidence))),
                    "population": "100000",
                    "incidence_per_100k": str(float(incidence)),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_adjacency(path: Path) -> Path:
    rows = [
        {"county_fips": "24001", "neighbor_county_fips": "54001"},
        {"county_fips": "54001", "neighbor_county_fips": "24001"},
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_did_control_panel(path: Path) -> Path:
    rows = []
    series = {
        ("13", "GA", "Georgia", "13001", "Appling County"): [5, 5, 5, 5.5],
        ("13", "GA", "Georgia", "13003", "Atkinson County"): [5, 5, 5, 5.5],
        ("40", "OK", "Oklahoma", "40001", "Adair County"): [1, 5, 9, 9.9],
        ("40", "OK", "Oklahoma", "40003", "Alfalfa County"): [1, 5, 9, 9.9],
    }
    for key, incidences in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for year, incidence in zip([2017, 2018, 2019, 2022], incidences):
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(int(float(incidence))),
                    "population": "100000",
                    "incidence_per_100k": str(float(incidence)),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
