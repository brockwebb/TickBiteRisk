from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ACQUISITION_PROVENANCE_COLUMNS = [
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
]


@dataclass(frozen=True)
class AcquisitionProvenanceRecord:
    source_id: str
    source_name: str
    source_url: str
    citation_url: str
    acquisition_command: str
    acquisition_procedure: str
    request_method: str
    request_description: str
    derived_artifact_paths: list[Path] | None = None
    derived_artifact_path_labels: list[str] | None = None
    row_count: int = 0
    parser_method: str = "not_recorded"
    extraction_quality: str = "not_recorded"
    access_notes: str = ""
    modeling_caveats: str = ""


def write_acquisition_provenance_manifest(
    records: list[AcquisitionProvenanceRecord],
    *,
    manifest_path: Path,
    retrieved_at: str | None = None,
    append: bool = False,
) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    rows = [_record_to_row(record, timestamp) for record in records]
    if append and manifest_path.exists():
        rows = [*_read_existing_rows(manifest_path), *rows]
    keyed = {
        (str(row["source_id"]), str(row["source_url"])): row for row in rows
    }
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACQUISITION_PROVENANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            sorted(
                keyed.values(),
                key=lambda row: (str(row["source_id"]), str(row["source_url"])),
            )
        )
    return manifest_path


def _record_to_row(
    record: AcquisitionProvenanceRecord,
    retrieved_at: str,
) -> dict[str, object]:
    artifact_paths = record.derived_artifact_paths or []
    artifact_path_labels = _artifact_path_labels(record, artifact_paths)
    artifact_checksum_labels = _artifact_checksum_labels(record, artifact_paths)
    return {
        "source_id": record.source_id,
        "source_name": record.source_name,
        "source_url": record.source_url,
        "citation_url": record.citation_url,
        "acquisition_command": record.acquisition_command,
        "acquisition_procedure": record.acquisition_procedure,
        "request_method": record.request_method,
        "request_description": record.request_description,
        "derived_artifact_paths": ";".join(artifact_path_labels),
        "derived_artifact_sha256s": ";".join(
            f"{label}={_compute_sha256(path)}"
            for path, label in zip(
                artifact_paths,
                artifact_checksum_labels,
                strict=True,
            )
        ),
        "row_count": record.row_count,
        "retrieved_at": retrieved_at,
        "parser_method": record.parser_method,
        "extraction_quality": record.extraction_quality,
        "access_notes": record.access_notes,
        "modeling_caveats": record.modeling_caveats,
    }


def _artifact_path_labels(
    record: AcquisitionProvenanceRecord,
    artifact_paths: list[Path],
) -> list[str]:
    labels = record.derived_artifact_path_labels
    if labels is None:
        return [str(path) for path in artifact_paths]
    if len(labels) != len(artifact_paths):
        raise ValueError(
            "derived_artifact_path_labels must match derived_artifact_paths length"
        )
    return labels


def _artifact_checksum_labels(
    record: AcquisitionProvenanceRecord,
    artifact_paths: list[Path],
) -> list[str]:
    labels = record.derived_artifact_path_labels
    if labels is not None:
        return labels
    return [path.name for path in artifact_paths]


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_existing_rows(manifest_path: Path) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
