import csv

from tickbiterisk.etl.acquisition_provenance import (
    AcquisitionProvenanceRecord,
    write_acquisition_provenance_manifest,
)


def test_write_acquisition_provenance_manifest_records_api_run_evidence(tmp_path) -> None:
    first_output = tmp_path / "out" / "first.csv"
    second_output = tmp_path / "out" / "second.csv"
    first_output.parent.mkdir()
    first_output.write_text("a,b\n1,2\n", encoding="utf-8")
    second_output.write_text("c,d\n3,4\n", encoding="utf-8")

    manifest_path = write_acquisition_provenance_manifest(
        [
            AcquisitionProvenanceRecord(
                source_id="example_api",
                source_name="Example API",
                source_url="https://example.test/api?format=csv",
                citation_url="https://example.test/docs",
                acquisition_command=(
                    "tickbiterisk etl example --output-dir "
                    f"{tmp_path / 'out'}"
                ),
                acquisition_procedure="Fetch the official API response.",
                request_method="GET",
                request_description="Example public API request.",
                derived_artifact_paths=[first_output, second_output],
                row_count=12,
                parser_method="example_parser_v1",
                extraction_quality="accepted",
                access_notes="No key required.",
                modeling_caveats="Research lane only.",
            )
        ],
        manifest_path=tmp_path / "out" / "acquisition_provenance.csv",
        retrieved_at="2026-05-28T12:00:00+00:00",
    )

    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "source_id": "example_api",
            "source_name": "Example API",
            "source_url": "https://example.test/api?format=csv",
            "citation_url": "https://example.test/docs",
            "acquisition_command": (
                "tickbiterisk etl example --output-dir "
                f"{tmp_path / 'out'}"
            ),
            "acquisition_procedure": "Fetch the official API response.",
            "request_method": "GET",
            "request_description": "Example public API request.",
            "derived_artifact_paths": f"{first_output};{second_output}",
            "derived_artifact_sha256s": (
                "first.csv=492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470;"
                "second.csv=e7f1cdc787bef2e5f844bd6ac61f688d8afde3e9cbff61c9ab2b9e3b7d104650"
            ),
            "row_count": "12",
            "retrieved_at": "2026-05-28T12:00:00+00:00",
            "parser_method": "example_parser_v1",
            "extraction_quality": "accepted",
            "access_notes": "No key required.",
            "modeling_caveats": "Research lane only.",
        }
    ]


def test_write_acquisition_provenance_manifest_sorts_by_source_id_and_url(
    tmp_path,
) -> None:
    manifest_path = write_acquisition_provenance_manifest(
        [
            AcquisitionProvenanceRecord(
                source_id="b_source",
                source_name="B source",
                source_url="https://example.test/b",
                citation_url="https://example.test/b",
                acquisition_command="tickbiterisk etl b",
                acquisition_procedure="Fetch B.",
                request_method="GET",
                request_description="B request.",
            ),
            AcquisitionProvenanceRecord(
                source_id="a_source",
                source_name="A source",
                source_url="https://example.test/a",
                citation_url="https://example.test/a",
                acquisition_command="tickbiterisk etl a",
                acquisition_procedure="Fetch A.",
                request_method="GET",
                request_description="A request.",
            ),
        ],
        manifest_path=tmp_path / "manifest.csv",
        retrieved_at="2026-05-28T12:00:00+00:00",
    )

    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["source_id"] for row in rows] == ["a_source", "b_source"]
