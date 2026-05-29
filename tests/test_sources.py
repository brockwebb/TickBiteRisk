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


def test_project_manifest_tracks_2024_plus_source_watchlist() -> None:
    sources = load_sources_from_markdown(Path("docs/data-manifest.md"))
    sources_by_id = {source.source_id: source for source in sources}

    expected = {
        "delaware_dhss_lyme_table": "https://dhss.delaware.gov/",
        "virginia_vdh_reportable_disease_dashboard": "https://www.vdh.virginia.gov/",
        "west_virginia_oeps_vectorborne_reports": "https://oeps.wv.gov/",
        "dc_health_tickborne_report": "https://dchealth.dc.gov/",
        "mass_dph_monthly_tickborne_reports": "https://www.mass.gov/lists/monthly-tick-borne-disease-reports",
        "maine_jmmc_2024_county_rates": "https://knowledgeconnection.mainehealth.org/",
        "ohio_odh_lyme_dashboard": "https://odh.ohio.gov/",
        "nj_doh_tickborne_page": "https://www.nj.gov/health/",
        "cdc_surveillance_based_lyme_disease_network": "https://www.cdc.gov/lyme/data-research/facts-stats/",
        "foia_nndss_preliminary_county": "https://www.cdc.gov/nndss/",
        "state_essence_tick_bite_proxy": "https://www.cdc.gov/nssp/",
    }

    for source_id, url_prefix in expected.items():
        assert source_id in sources_by_id
        source = sources_by_id[source_id]
        assert source.location.startswith(url_prefix)
        if source_id == "delaware_dhss_lyme_table":
            assert "etl_supported" in source.status
            assert "not_model_input" in source.status
        elif source_id == "virginia_vdh_reportable_disease_dashboard":
            assert "etl_supported" in source.status
            assert "state_overlay" in source.status
        elif source_id == "west_virginia_oeps_vectorborne_reports":
            assert "etl_supported" in source.status
            assert "state_aggregate" in source.status
        elif source_id == "mass_dph_monthly_tickborne_reports":
            assert "etl_supported" in source.status
            assert "syndromic_ed_signal" in source.status
        else:
            assert "candidate" in source.status
        assert "not a confirmed disease truth label" in source.notes


def test_project_docs_define_acquisition_provenance_contract() -> None:
    docs_text = "\n".join(
        [
            Path("docs/etl-pipeline.md").read_text(encoding="utf-8"),
            Path("docs/data-sources.md").read_text(encoding="utf-8"),
        ]
    )

    for token in [
        "Acquisition provenance contract",
        "Direct API and raw-source ETL run manifests",
        "acquisition_provenance.csv",
        "ENSO, EnviroAtlas, USDM drought, Census population, regional population, regional demographics, ACS exposure, building permits, county reference, deer harvest, Open-Meteo weather backfill, NOAA weather primitives, NOAA weather backfill, Lyme outcomes, aggregate Lyme validation, regional Lyme outcomes, regional signals, Massachusetts DPH syndromic ED, NSSP coverage, seasonality baseline, tick status, and mast/acorn",
        "source URL or API endpoint",
        "rerunnable command",
        "citation URL",
        "secret-free",
        "checksum",
        "retrieval timestamp",
        "parser method",
        "extraction quality",
        "tickbiterisk etl provenance-audit",
    ]:
        assert token in docs_text
