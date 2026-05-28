import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_lyme_aggregate_validation_command_writes_capacity_anchor_outputs(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    _write_required_sources(raw_dir)

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-aggregate-validation",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 4 CDC Lyme state aggregate row(s)" in result.stdout
    assert "Wrote 2 CDC Lyme regional aggregate row(s)" in result.stdout
    assert "Wrote 2 CDC Lyme national aggregate row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "cdc_lyme_state_year.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        state_rows = list(csv.DictReader(handle))
    maryland_2022 = next(
        row
        for row in state_rows
        if row["geography_id"] == "24" and row["year"] == "2022"
    )
    assert maryland_2022["geography_name"] == "Maryland"
    assert maryland_2022["cases"] == "2400"
    assert maryland_2022["incidence_per_100k"] == "40.1"
    assert "lyme_case_definition_change" in maryland_2022["feature_quality_flags"]

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_caseincid_cases_region_2023",
        "cdc_caseincid_cases_state_2023",
        "cdc_caseincid_overall_cases_2023",
        "cdc_caseincid_overall_rate_2023",
        "cdc_caseincid_rates_region_2023",
        "cdc_caseincid_rates_state_2023",
    ]
    state_cases = next(
        row
        for row in provenance_rows
        if row["source_id"] == "cdc_caseincid_cases_state_2023"
    )
    assert state_cases["row_count"] == "4"
    assert "state_caseincid_cases.csv=" in state_cases["derived_artifact_sha256s"]
    assert "cdc_lyme_state_year.csv=" in state_cases["derived_artifact_sha256s"]
    assert str(tmp_path) not in state_cases["derived_artifact_paths"]


def test_lyme_aggregate_validation_command_fails_before_writing_when_missing_source(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    _write_required_sources(raw_dir)
    (raw_dir / "state_caseincid_rates.csv").unlink()

    result = runner.invoke(
        app,
        [
            "etl",
            "lyme-aggregate-validation",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Lyme aggregate source file not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()


def _write_required_sources(raw_dir: Path) -> None:
    (raw_dir / "state_caseincid_cases.csv").write_text(
        "\n".join(
            [
                "State,2008,2022",
                "Maryland\u2020,\"1,200\",2400",
                "Pennsylvania\u2020,5000,6200",
                "U.S. Total,10000,30000",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "state_caseincid_rates.csv").write_text(
        "\n".join(
            [
                "State,Year,Rates",
                "Maryland\u2020,2022,40.1",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "region_caseincid_cases.csv").write_text(
        "\n".join(
            [
                "Year,Region,Cases",
                "2020,South Atlantic,100",
                "2022,South Atlantic,150",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "region_caseincid_rates.csv").write_text(
        "\n".join(
            [
                "Year,Region,Rate",
                "2020,South Atlantic,1.0",
                "2022,South Atlantic,1.5",
            ]
        ),
        encoding="utf-8",
    )
    (raw_dir / "national_caseincid_cases.csv").write_text(
        "\n".join(["Year,Cases", "2020,5000", "2022,8000"]),
        encoding="utf-8",
    )
    (raw_dir / "national_caseincid_rates.csv").write_text(
        "\n".join(["Year,Incidence", "2020,1.5", "2022,2.4"]),
        encoding="utf-8",
    )
