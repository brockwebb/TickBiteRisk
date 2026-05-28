import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_acs_exposure_dry_run_prints_keyless_urls(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "acs-exposure",
            "--year",
            "2024",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Planned ACS exposure source URL(s): 5" in result.stdout
    assert "acsdt5y2024-b01001.dat" in result.stdout
    assert "Geos20245YR.txt" in result.stdout


def test_acs_exposure_command_writes_output_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"

    def fake_materialize(raw_dir: Path, *, year: int, download_if_missing: bool):
        source_dir = raw_dir / str(year)
        source_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "geography": source_dir / "Geos20245YR.txt",
            "b01001": source_dir / "acsdt5y2024-b01001.dat",
            "b25024": source_dir / "acsdt5y2024-b25024.dat",
            "b25003": source_dir / "acsdt5y2024-b25003.dat",
            "gazetteer": source_dir / "2024_Gaz_counties_national.txt",
        }
        paths["geography"].write_text(
            "\n".join(
                [
                    "FILEID|STUSAB|SUMLEVEL|COMPONENT|STATE|COUNTY|GEO_ID|NAME|TL_GEO_ID",
                    "ACSSF|MD|050|00|24|011|0500000US24011|Caroline County, Maryland|24011",
                ]
            ),
            encoding="utf-8",
        )
        b01001_values = {f"B01001_E{index:03d}": "0" for index in range(1, 50)}
        b01001_values["B01001_E001"] = "100"
        b01001_values["B01001_E003"] = "5"
        b01001_values["B01001_E027"] = "5"
        paths["b01001"].write_text(
            "GEO_ID|" + "|".join(b01001_values) + "\n"
            "0500000US24011|"
            + "|".join(b01001_values[column] for column in b01001_values)
            + "\n",
            encoding="utf-8",
        )
        paths["b25024"].write_text(
            "GEO_ID|B25024_E001|B25024_E002|B25024_E003\n"
            "0500000US24011|50|30|5\n",
            encoding="utf-8",
        )
        paths["b25003"].write_text(
            "GEO_ID|B25003_E001|B25003_E002\n0500000US24011|40|28\n",
            encoding="utf-8",
        )
        paths["gazetteer"].write_text(
            "USPS\tGEOID\tNAME\tALAND_SQMI\nMD\t24011\tCaroline County\t5\n",
            encoding="utf-8",
        )
        return paths

    monkeypatch.setattr(
        "tickbiterisk.cli.materialize_acs_exposure_sources",
        fake_materialize,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "acs-exposure",
            "--year",
            "2024",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 ACS exposure row(s)" in result.stdout
    output_path = output_dir / "midatlantic_acs_exposure_county_year.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24011"
    assert rows[0]["single_family_share"] == "0.7"
    assert rows[0]["source_id"] == "census_acs5_2024_residential_exposure"

    with (output_dir / "acquisition_provenance.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert len(provenance_rows) == 5
    assert {row["source_id"] for row in provenance_rows} >= {
        "census_acs5_2024_b01001",
        "census_acs5_2024_b25024",
        "census_acs5_2024_b25003",
        "census_acs5_2024_geography",
        "census_gazetteer_2024_counties_national",
    }
    assert "midatlantic_acs_exposure_county_year.csv=" in provenance_rows[0][
        "derived_artifact_sha256s"
    ]
    assert all("not public-default" in row["modeling_caveats"] for row in provenance_rows)


def test_acs_exposure_command_appends_multiple_vintages_and_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"

    def fake_materialize(raw_dir: Path, *, year: int, download_if_missing: bool):
        source_dir = raw_dir / str(year)
        source_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "geography": source_dir / f"Geos{year}5YR.txt",
            "b01001": source_dir / f"acsdt5y{year}-b01001.dat",
            "b25024": source_dir / f"acsdt5y{year}-b25024.dat",
            "b25003": source_dir / f"acsdt5y{year}-b25003.dat",
            "gazetteer": source_dir / "2024_Gaz_counties_national.txt",
        }
        paths["geography"].write_text(
            "\n".join(
                [
                    "FILEID|STUSAB|SUMLEVEL|COMPONENT|STATE|COUNTY|GEO_ID|NAME|TL_GEO_ID",
                    "ACSSF|MD|050|00|24|011|0500000US24011|Caroline County, Maryland|24011",
                ]
            ),
            encoding="utf-8",
        )
        b01001_values = {f"B01001_E{index:03d}": "0" for index in range(1, 50)}
        b01001_values["B01001_E001"] = str(year)
        paths["b01001"].write_text(
            "GEO_ID|" + "|".join(b01001_values) + "\n"
            "0500000US24011|"
            + "|".join(b01001_values[column] for column in b01001_values)
            + "\n",
            encoding="utf-8",
        )
        paths["b25024"].write_text(
            "GEO_ID|B25024_E001|B25024_E002|B25024_E003\n"
            "0500000US24011|50|30|5\n",
            encoding="utf-8",
        )
        paths["b25003"].write_text(
            "GEO_ID|B25003_E001|B25003_E002\n0500000US24011|40|28\n",
            encoding="utf-8",
        )
        paths["gazetteer"].write_text(
            "USPS\tGEOID\tNAME\tALAND_SQMI\nMD\t24011\tCaroline County\t5\n",
            encoding="utf-8",
        )
        return paths

    monkeypatch.setattr(
        "tickbiterisk.cli.materialize_acs_exposure_sources",
        fake_materialize,
    )

    first = runner.invoke(
        app,
        [
            "etl",
            "acs-exposure",
            "--year",
            "2023",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ],
    )
    second = runner.invoke(
        app,
        [
            "etl",
            "acs-exposure",
            "--year",
            "2024",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
            "--append",
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    output_path = output_dir / "midatlantic_acs_exposure_county_year.csv"
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["county_fips"], row["year"]) for row in rows] == [
        ("24011", "2023"),
        ("24011", "2024"),
    ]

    with (output_dir / "acquisition_provenance.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))
    assert len(provenance_rows) == 9
    assert {
        "census_acs5_2023_b01001",
        "census_acs5_2024_b01001",
    } <= {row["source_id"] for row in provenance_rows}
    assert any("--append" in row["acquisition_command"] for row in provenance_rows)
