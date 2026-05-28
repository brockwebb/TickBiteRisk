import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_seasonality_baseline_command_writes_monthly_and_weekly_outputs(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "cdc_lyme_monthly_onset_2010_2023.csv",
        [
            {"Year": "2010", "Onset Month": "January", "Cases": "20"},
            {"Year": "2010", "Onset Month": "February", "Cases": "80"},
            {"Year": "2011", "Onset Month": "January", "Cases": "40"},
            {"Year": "2011", "Onset Month": "February", "Cases": "60"},
        ],
    )
    _write_csv(
        raw_dir / "cdc_lyme_weekly_onset_2010_2023.csv",
        [
            {"Year": "2010", "MMWR Week": "1", "Cases": "70"},
            {"Year": "2010", "MMWR Week": "2", "Cases": "30"},
            {"Year": "2011", "MMWR Week": "1", "Cases": "50"},
            {"Year": "2011", "MMWR Week": "2", "Cases": "50"},
        ],
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "seasonality-baseline",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 8 seasonality observation row(s)" in result.stdout
    assert "Wrote 4 seasonality baseline row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout
    assert (output_dir / "seasonality_observations.csv").exists()
    assert (output_dir / "seasonality_baseline.csv").exists()

    with (output_dir / "seasonality_baseline.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["grain"] for row in rows} == {"month", "mmwr_week"}
    assert rows[0]["feature_quality_flags"] == (
        "national_curve_not_county_specific,shares_normalized_by_annual_total,"
        "empirical_prediction_band"
    )

    with (output_dir / "acquisition_provenance.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert [row["source_id"] for row in provenance_rows] == [
        "cdc_seasonality_month_2023",
        "cdc_seasonality_week_2023",
    ]
    provenance_by_source = {row["source_id"]: row for row in provenance_rows}

    month_provenance = provenance_by_source["cdc_seasonality_month_2023"]
    assert month_provenance["row_count"] == "4"
    assert month_provenance["parser_method"] == "parse_cdc_lyme_monthly_onset"
    assert month_provenance["source_url"].startswith("https://www.cdc.gov/lyme/")
    assert "cdc_lyme_monthly_onset_2010_2023.csv" in month_provenance[
        "derived_artifact_paths"
    ]
    assert "seasonality_observations.csv=" in month_provenance[
        "derived_artifact_sha256s"
    ]
    assert str(tmp_path) not in month_provenance["derived_artifact_paths"]

    week_provenance = provenance_by_source["cdc_seasonality_week_2023"]
    assert week_provenance["row_count"] == "4"
    assert week_provenance["parser_method"] == "parse_cdc_lyme_weekly_onset"
    assert "--provenance-manifest-path" in week_provenance["acquisition_command"]
    assert str(tmp_path) not in week_provenance["acquisition_command"]
    assert "national curve" in week_provenance["modeling_caveats"]


def test_seasonality_baseline_command_fails_cleanly_when_source_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "cdc_lyme_monthly_onset_2010_2023.csv",
        [{"Year": "2010", "Onset Month": "January", "Cases": "20"}],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "seasonality-baseline",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "seasonality source file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "seasonality_baseline.csv").exists()
    assert not (tmp_path / "out" / "acquisition_provenance.csv").exists()


def test_seasonality_baseline_command_fails_cleanly_when_columns_missing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "cdc_lyme_monthly_onset_2010_2023.csv",
        [{"Year": "2010", "Onset Month": "January"}],
    )
    _write_csv(
        raw_dir / "cdc_lyme_weekly_onset_2010_2023.csv",
        [{"Year": "2010", "MMWR Week": "1", "Cases": "70"}],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "seasonality-baseline",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "missing required seasonality column(s): Cases" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "seasonality_baseline.csv").exists()
    assert not (tmp_path / "out" / "acquisition_provenance.csv").exists()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
