import csv
from pathlib import Path

from tickbiterisk.etl.acquisition_provenance import (
    AcquisitionProvenanceRecord,
    write_acquisition_provenance_manifest,
)
from tickbiterisk.etl.provenance_audit import (
    audit_provenance_manifests,
    discover_provenance_manifests,
)


def test_audit_provenance_manifests_accepts_saved_urls_commands_and_checksums(
    tmp_path: Path,
) -> None:
    root = tmp_path / "build" / "etl"
    acquisition_manifest = _write_good_acquisition_manifest(root / "population")
    source_manifest = _write_good_source_manifest(root / "ecology")

    result = audit_provenance_manifests([acquisition_manifest, source_manifest])

    assert result.manifest_count == 2
    assert result.row_count == 2
    assert result.issue_count == 0
    assert result.issues == []


def test_audit_provenance_manifests_accepts_header_only_and_derived_source_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "build" / "etl"
    derived_manifest = _write_good_acquisition_manifest(
        root / "regional-signals",
        source_url="midatlantic_lyme_county_year.csv",
    )
    header_only_manifest = write_acquisition_provenance_manifest(
        [],
        manifest_path=root / "empty" / "acquisition_provenance.csv",
        retrieved_at="2026-05-28T12:00:00+00:00",
    )

    result = audit_provenance_manifests([derived_manifest, header_only_manifest])

    assert result.manifest_count == 2
    assert result.row_count == 1
    assert result.issue_count == 0


def test_audit_provenance_manifests_flags_missing_evidence_and_secret_like_values(
    tmp_path: Path,
) -> None:
    manifest_path = _write_bad_acquisition_manifest(tmp_path / "bad")

    result = audit_provenance_manifests([manifest_path])

    issue_fields = {(issue.source_id, issue.field) for issue in result.issues}
    assert {
        ("bad_source", "source_url"),
        ("bad_source", "citation_url"),
        ("bad_source", "acquisition_command"),
        ("bad_source", "acquisition_procedure"),
        ("bad_source", "request_method"),
        ("bad_source", "request_description"),
        ("bad_source", "retrieved_at"),
        ("bad_source", "parser_method"),
        ("bad_source", "extraction_quality"),
        ("bad_source", "derived_artifact_sha256s"),
    }.issubset(issue_fields)


def test_discover_provenance_manifests_finds_supported_manifest_names(
    tmp_path: Path,
) -> None:
    root = tmp_path / "build" / "etl"
    acquisition_manifest = _write_good_acquisition_manifest(root / "population")
    source_manifest = _write_good_source_manifest(root / "ecology")
    (root / "other").mkdir()
    (root / "other" / "notes.csv").write_text("not,a,manifest\n", encoding="utf-8")

    discovered = discover_provenance_manifests(root)

    assert discovered == [source_manifest, acquisition_manifest]


def _write_good_acquisition_manifest(
    directory: Path,
    *,
    source_url: str = "https://api.census.gov/data/example?get=POP",
) -> Path:
    artifact_path = directory / "county_population_year.csv"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        "county_fips,year,population\n24003,2023,100\n",
        encoding="utf-8",
    )
    return write_acquisition_provenance_manifest(
        [
            AcquisitionProvenanceRecord(
                source_id="census_population_example",
                source_name="Census Population Example",
                source_url=source_url,
                citation_url="https://www.census.gov/programs-surveys/popest.html",
                acquisition_command=(
                    "tickbiterisk etl census-population --output-dir "
                    "build/etl/population --provenance-manifest-path "
                    "build/etl/population/acquisition_provenance.csv"
                ),
                acquisition_procedure=(
                    "Fetch the official Census API response and normalize county rows."
                ),
                request_method="GET",
                request_description="Census county population request.",
                derived_artifact_paths=[artifact_path],
                derived_artifact_path_labels=[
                    "build/etl/population/county_population_year.csv"
                ],
                row_count=1,
                parser_method="parse_census_population",
                extraction_quality="accepted",
                access_notes="Public API endpoint; no key required.",
                modeling_caveats="Population denominator; not exposure evidence.",
            )
        ],
        manifest_path=directory / "acquisition_provenance.csv",
        retrieved_at="2026-05-28T12:00:00+00:00",
    )


def _write_bad_acquisition_manifest(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "acquisition_provenance.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id",
                "source_name",
                "source_url",
                "citation_url",
                "acquisition_command",
                "acquisition_procedure",
                "request_method",
                "request_description",
                "derived_artifact_paths",
                "derived_artifact_sha256s",
                "row_count",
                "retrieved_at",
                "parser_method",
                "extraction_quality",
                "access_notes",
                "modeling_caveats",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_id": "bad_source",
                "source_name": "Bad Source",
                "source_url": "https://example.test/api?token=SECRET",
                "citation_url": "",
                "acquisition_command": "tickbiterisk etl bad --api-key SECRET",
                "acquisition_procedure": "",
                "request_method": "",
                "request_description": "",
                "derived_artifact_paths": "build/etl/bad/bad.csv",
                "derived_artifact_sha256s": "bad.csv=not-a-sha",
                "row_count": "1",
                "retrieved_at": "",
                "parser_method": "",
                "extraction_quality": "",
                "access_notes": "",
                "modeling_caveats": "",
            }
        )
    return manifest_path


def _write_good_source_manifest(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "source_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id",
                "family",
                "description",
                "url",
                "local_path",
                "expected_format",
                "bytes",
                "sha256",
                "ingested_at",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_id": "maryland_dnr_example",
                "family": "mast",
                "description": "Maryland DNR example PDF",
                "url": "https://dnr.maryland.gov/example.pdf",
                "local_path": "data/raw/ecology/mast/example.pdf",
                "expected_format": "pdf",
                "bytes": "123",
                "sha256": "a" * 64,
                "ingested_at": "2026-05-28T12:00:00+00:00",
            }
        )
    return manifest_path
