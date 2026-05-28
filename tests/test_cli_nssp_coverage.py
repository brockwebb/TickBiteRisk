import csv
from pathlib import Path

from typer.testing import CliRunner

from tests.test_nssp_coverage import _write_county_reference
from tickbiterisk.cli import app


runner = CliRunner()


def test_nssp_coverage_command_writes_output_and_provenance(tmp_path: Path) -> None:
    raw_path = tmp_path / "Coverage_Map_Tbl_2024Jul01.csv"
    raw_path.write_text(
        "\n".join(
            [
                "State,County,Status",
                "MD,Caroline,No Eligible Facilities",
                "MD,Anne Arundel,Recent Data in NSSP",
            ]
        ),
        encoding="utf-8",
    )
    county_reference = _write_county_reference(tmp_path / "county_reference.csv")

    result = runner.invoke(
        app,
        [
            "etl",
            "nssp-coverage",
            "--raw-path",
            str(raw_path),
            "--county-reference-path",
            str(county_reference),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 NSSP coverage row(s)" in result.stdout
    output_path = tmp_path / "out" / "nssp_coverage_county_status.csv"
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_id"] == "cdc_nssp_coverage_2024_07_01"
    caroline = next(row for row in rows if row["county_fips"] == "24011")
    assert caroline["feature_quality_flags"] == (
        "nssp_coverage_only_not_tick_bite_counts,"
        "human_exposure_feed_feasibility_only,no_eligible_facilities_reported"
    )

    with (tmp_path / "out" / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert provenance_rows[0]["source_id"] == "cdc_nssp_coverage_2024_07_01"
    assert (
        provenance_rows[0]["source_url"]
        == "https://www.cdc.gov/nssp/documents/Coverage_Map_Tbl_2024Jul01.csv"
    )
    assert "nssp_coverage_county_status.csv=" in provenance_rows[0][
        "derived_artifact_sha256s"
    ]
