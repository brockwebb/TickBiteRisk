from pathlib import Path

from tickbiterisk.etl.sources import compute_sha256, load_sources_from_markdown


def _write_manifest(path: Path, rows: list[str]) -> None:
    path.write_text(
        "\n".join(
            [
                "# Test Manifest",
                "",
                "| ID | Source | Local path / URL | Format | Geography | Time coverage | Role | Status | Redistribution | SHA-256 / Notes |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                *rows,
            ]
        ),
        encoding="utf-8",
    )


def test_load_sources_from_markdown_table() -> None:
    sources = load_sources_from_markdown(Path("tests/fixtures/manifest-mini.md"))
    assert [source.source_id for source in sources] == ["fixture_csv", "remote_candidate"]
    assert sources[0].format == "CSV"
    assert sources[0].is_local is True
    assert sources[1].is_local is False


def test_placeholder_locations_are_not_local_files(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.md"
    _write_manifest(
        manifest_path,
        [
            "| `census_api` | Census | Census API | CSV | County | 2022 | Covariate | candidate | Public | No local file |",
            "| `fixture_csv` | Fixture CSV | `tests/fixtures/lyme_public_use_2022_2023_mini.csv` | CSV | County | 2022 | Outcome | acquired | Test fixture | local fixture |",
        ],
    )

    sources = load_sources_from_markdown(manifest_path)

    assert sources[0].is_local is False
    assert sources[1].is_local is True


def test_inline_code_spans_are_removed_from_cells_with_trailing_notes(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.md"
    _write_manifest(
        manifest_path,
        [
            "| `latin1_csv` | Latin1 CSV | `tests/fixtures/latin1.csv` | CSV | County | 2022 | Outcome | acquired | Restricted | `abc123`; requires latin1 |",
        ],
    )

    sources = load_sources_from_markdown(manifest_path)

    assert sources[0].notes == "abc123; requires latin1"


def test_compute_sha256_for_local_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("tick risk\n", encoding="utf-8")
    assert compute_sha256(file_path) == "952085cb1f514d1814cab4821b26563f88fa4a65a1a57a240afb7e69a89b2762"


def test_project_manifest_tracks_remaining_candidate_sources() -> None:
    sources = load_sources_from_markdown(Path("docs/data-manifest.md"))
    source_ids = {source.source_id for source in sources}

    for source_id in [
        "noaa_cpc_enso_index",
        "noaa_psl_mei_v2",
        "cdc_tick_bite_tracker",
        "nssp_tick_bite_ed",
        "poison_center_tick_bite_inquiries",
        "inaturalist_tick_observations",
        "gbif_tick_occurrences",
        "park_attendance_county_year",
        "dog_license_pet_ownership_proxy",
        "parcel_low_density_residential_proxy",
        "surveillance_regime_calibration",
        "ecological_pressure_index",
    ]:
        assert source_id in source_ids


def test_project_docs_define_acquisition_provenance_contract() -> None:
    docs_text = "\n".join(
        [
            Path("docs/etl-pipeline.md").read_text(encoding="utf-8"),
            Path("docs/data-sources.md").read_text(encoding="utf-8"),
        ]
    )

    for token in [
        "Acquisition provenance contract",
        "direct API ETL run manifests",
        "acquisition_provenance.csv",
        "ENSO, EnviroAtlas, USDM drought, Census population, and building permits",
        "source URL or API endpoint",
        "rerunnable command",
        "citation URL",
        "secret-free",
        "checksum",
        "retrieval timestamp",
        "parser method",
        "extraction quality",
    ]:
        assert token in docs_text
