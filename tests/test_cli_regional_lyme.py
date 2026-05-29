import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_regional_lyme_outcomes_command_writes_panel_and_provenance(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()
    (raw_dir / "cdc_lyme_county_dashboard_2023.csv").write_text(
        "\n".join(
            [
                "Ctyname,stname,ststatus,stcode,ctycode,Cases2001,cases2022",
                "Kent County,Delaware,High Incidence,10,1,22,45",
                "District of Columbia,District of Columbia,Low Incidence,11,1,17,73",
                "Anne Arundel County,Maryland,High Incidence,24,3,69,127",
                "Adams County,Pennsylvania,High Incidence,42,1,17,143",
                "Arlington County,Virginia,Low Incidence,51,13,2,38",
                "Berkeley County,West Virginia,Low Incidence,54,3,5,93",
                "Autauga County,Alabama,Low Incidence,1,1,0,0",
            ]
        ),
        encoding="utf-8",
    )
    pa_path = raw_dir / "pennsylvania_doh_official_lyme_by_report_2024_with_map.xlsx"
    _write_pa_workbook(
        pa_path,
        [
            {"Jurisdiction": "Adams", "2024": "128", "2023": "145"},
            {"Jurisdiction": "Montour", "2024": "*", "2023": "7"},
        ],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
            "--pa-2024-workbook-path",
            str(pa_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 14 Mid-Atlantic Lyme county-year outcome row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (output_dir / "midatlantic_lyme_county_year.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 14
    dc_2022 = next(
        row
        for row in rows
        if row["county_fips"] == "11001" and row["year"] == "2022"
    )
    assert dc_2022["state_abbr"] == "DC"
    assert "district_county_equivalent" in dc_2022["feature_quality_flags"]
    assert "lyme_case_definition_change" in dc_2022["feature_quality_flags"]
    pa_2024 = next(
        row
        for row in rows
        if row["county_fips"] == "42001" and row["year"] == "2024"
    )
    assert pa_2024["source_id"] == "pa_doh_lyme_1980_2024_xlsx"
    assert "pa_doh_official_county_cases" in pa_2024["feature_quality_flags"]

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_lyme_county_dashboard_2023",
        "pa_doh_lyme_1980_2024_xlsx",
    ]
    provenance = provenance_rows[0]
    assert provenance["row_count"] == "12"
    assert "cdc_lyme_county_dashboard_2023.csv=" in provenance[
        "derived_artifact_sha256s"
    ]
    assert "midatlantic_lyme_county_year.csv=" in provenance[
        "derived_artifact_sha256s"
    ]
    assert str(tmp_path) not in provenance["derived_artifact_paths"]
    assert "regional expansion/stress-test panel" in provenance["modeling_caveats"]
    pa_provenance = provenance_rows[1]
    assert pa_provenance["row_count"] == "2"
    assert "OfficialLymeByReport2024withMap.xlsx" in pa_provenance["source_url"]
    assert "state 2024 overlay" in pa_provenance["modeling_caveats"]


def test_regional_lyme_outcomes_command_fails_before_writing_when_missing_dashboard(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "etl",
            "regional-lyme-outcomes",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Regional Lyme source file not found" in result.output
    assert "Traceback" not in result.output
    assert not output_dir.exists()


def _write_pa_workbook(path: Path, rows: list[dict[str, str]]) -> None:
    import pandas as pd

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(
            writer,
            sheet_name="RedactedCountyCaseCounts",
            startrow=2,
            index=False,
        )
