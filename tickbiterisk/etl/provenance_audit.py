from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from tickbiterisk.etl.acquisition_provenance import ACQUISITION_PROVENANCE_COLUMNS


SUPPORTED_PROVENANCE_MANIFEST_NAMES = {
    "acquisition_provenance.csv",
    "source_manifest.csv",
}

SOURCE_MANIFEST_COLUMNS = [
    "source_id",
    "family",
    "description",
    "url",
    "local_path",
    "expected_format",
    "bytes",
    "sha256",
    "ingested_at",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_PARAM_NAMES = {
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "password",
    "secret",
}
_SECRET_COMMAND_RE = re.compile(
    r"(?i)(--?(?:api[-_]?key|token|access[-_]?token|password|secret)\b|"
    r"(?:api[-_]?key|token|access[-_]?token|password|secret)=)"
)


@dataclass(frozen=True)
class ProvenanceAuditIssue:
    manifest_path: Path
    row_number: int
    source_id: str
    field: str
    message: str

    def format(self) -> str:
        return (
            f"{self.manifest_path}:{self.row_number}: "
            f"{self.source_id} {self.field}: {self.message}"
        )


@dataclass(frozen=True)
class ProvenanceAuditResult:
    manifest_count: int
    row_count: int
    issues: list[ProvenanceAuditIssue]

    @property
    def issue_count(self) -> int:
        return len(self.issues)


@dataclass(frozen=True)
class _CsvManifest:
    columns: set[str]
    rows: list[dict[str, str]]


def discover_provenance_manifests(root_dir: Path) -> list[Path]:
    if not root_dir.exists():
        return []
    return sorted(
        path
        for path in root_dir.rglob("*.csv")
        if path.name in SUPPORTED_PROVENANCE_MANIFEST_NAMES
    )


def audit_provenance_manifests(manifest_paths: list[Path]) -> ProvenanceAuditResult:
    issues: list[ProvenanceAuditIssue] = []
    row_count = 0
    for manifest_path in manifest_paths:
        manifest = _read_csv_manifest(manifest_path)
        row_count += len(manifest.rows)
        if manifest_path.name == "acquisition_provenance.csv":
            issues.extend(_audit_acquisition_manifest(manifest_path, manifest))
        elif manifest_path.name == "source_manifest.csv":
            issues.extend(_audit_source_manifest(manifest_path, manifest))
        else:
            issues.append(
                ProvenanceAuditIssue(
                    manifest_path=manifest_path,
                    row_number=0,
                    source_id="manifest",
                    field="filename",
                    message="Unsupported provenance manifest filename.",
                )
            )
    return ProvenanceAuditResult(
        manifest_count=len(manifest_paths),
        row_count=row_count,
        issues=issues,
    )


def _read_csv_manifest(path: Path) -> _CsvManifest:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return _CsvManifest(
            columns=set(reader.fieldnames or []),
            rows=list(reader),
        )


def _audit_acquisition_manifest(
    manifest_path: Path,
    manifest: _CsvManifest,
) -> list[ProvenanceAuditIssue]:
    issues = _missing_column_issues(
        manifest_path,
        actual_columns=manifest.columns,
        required_columns=ACQUISITION_PROVENANCE_COLUMNS,
    )
    for row_index, row in enumerate(manifest.rows, start=2):
        source_id = _source_id(row)
        for field in [
            "source_id",
            "source_name",
            "source_url",
            "citation_url",
            "acquisition_command",
            "acquisition_procedure",
            "request_method",
            "request_description",
            "retrieved_at",
            "parser_method",
            "extraction_quality",
        ]:
            issues.extend(_require_value(manifest_path, row_index, source_id, row, field))
        issues.extend(
            _require_source_locator(
                manifest_path,
                row_index,
                source_id,
                "source_url",
                row.get("source_url", ""),
            )
        )
        issues.extend(
            _require_http_url(
                manifest_path,
                row_index,
                source_id,
                "citation_url",
                row.get("citation_url", ""),
            )
        )
        issues.extend(
            _require_tickbiterisk_command(
                manifest_path,
                row_index,
                source_id,
                row.get("acquisition_command", ""),
            )
        )
        issues.extend(
            _require_secret_free(
                manifest_path,
                row_index,
                source_id,
                "source_url",
                row.get("source_url", ""),
            )
        )
        issues.extend(
            _require_secret_free(
                manifest_path,
                row_index,
                source_id,
                "citation_url",
                row.get("citation_url", ""),
            )
        )
        issues.extend(
            _require_secret_free(
                manifest_path,
                row_index,
                source_id,
                "acquisition_command",
                row.get("acquisition_command", ""),
            )
        )
        issues.extend(
            _require_artifact_sha256s(
                manifest_path,
                row_index,
                source_id,
                row.get("derived_artifact_sha256s", ""),
            )
        )
    return issues


def _audit_source_manifest(
    manifest_path: Path,
    manifest: _CsvManifest,
) -> list[ProvenanceAuditIssue]:
    issues = _missing_column_issues(
        manifest_path,
        actual_columns=manifest.columns,
        required_columns=SOURCE_MANIFEST_COLUMNS,
    )
    for row_index, row in enumerate(manifest.rows, start=2):
        source_id = _source_id(row)
        for field in SOURCE_MANIFEST_COLUMNS:
            issues.extend(_require_value(manifest_path, row_index, source_id, row, field))
        issues.extend(
            _require_http_url(
                manifest_path,
                row_index,
                source_id,
                "url",
                row.get("url", ""),
            )
        )
        issues.extend(
            _require_sha256(
                manifest_path,
                row_index,
                source_id,
                "sha256",
                row.get("sha256", ""),
            )
        )
        issues.extend(
            _require_nonnegative_integer(
                manifest_path,
                row_index,
                source_id,
                "bytes",
                row.get("bytes", ""),
            )
        )
    return issues


def _missing_column_issues(
    manifest_path: Path,
    *,
    actual_columns: set[str],
    required_columns: list[str],
) -> list[ProvenanceAuditIssue]:
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=1,
            source_id="manifest",
            field="header",
            message=f"Missing required column: {column}",
        )
        for column in required_columns
        if column not in actual_columns
    ]


def _source_id(row: dict[str, str]) -> str:
    return (row.get("source_id") or "unknown_source").strip()


def _require_value(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    row: dict[str, str],
    field: str,
) -> list[ProvenanceAuditIssue]:
    if (row.get(field) or "").strip():
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Required provenance evidence is blank.",
        )
    ]


def _require_source_locator(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    field: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip() or _is_http_url(value) or _is_local_artifact_locator(value):
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Expected an http(s) URL or local derived artifact path.",
        )
    ]


def _require_http_url(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    field: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip() or _is_http_url(value):
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Expected an http(s) URL.",
        )
    ]


def _require_tickbiterisk_command(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip() or "tickbiterisk" in value:
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field="acquisition_command",
            message="Expected a rerunnable tickbiterisk command.",
        )
    ]


def _require_secret_free(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    field: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip() or not _contains_secret_like_value(value):
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Secret-like token or key value should not be recorded.",
        )
    ]


def _require_artifact_sha256s(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip():
        return []
    bad_entries = [
        entry
        for entry in value.split(";")
        if entry and not _artifact_sha_entry_is_valid(entry)
    ]
    if not bad_entries:
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field="derived_artifact_sha256s",
            message="Expected artifact checksum entries shaped as label=64hex.",
        )
    ]


def _require_sha256(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    field: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip() or _SHA256_RE.match(value.strip()):
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Expected a 64-character lowercase SHA-256 checksum.",
        )
    ]


def _require_nonnegative_integer(
    manifest_path: Path,
    row_number: int,
    source_id: str,
    field: str,
    value: str,
) -> list[ProvenanceAuditIssue]:
    if not value.strip():
        return []
    try:
        parsed = int(value)
    except ValueError:
        parsed = -1
    if parsed >= 0:
        return []
    return [
        ProvenanceAuditIssue(
            manifest_path=manifest_path,
            row_number=row_number,
            source_id=source_id,
            field=field,
            message="Expected a non-negative integer.",
        )
    ]


def _is_http_url(value: str) -> bool:
    parsed = urlsplit(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_local_artifact_locator(value: str) -> bool:
    stripped = value.strip()
    if "://" in stripped or stripped.startswith(("/", "~")):
        return False
    return bool(Path(stripped).suffix)


def _contains_secret_like_value(value: str) -> bool:
    parsed = urlsplit(value.strip())
    query_params = {
        name.casefold().replace("-", "_")
        for name, _ in parse_qsl(parsed.query, keep_blank_values=True)
    }
    if query_params & _SECRET_PARAM_NAMES:
        return True
    return bool(_SECRET_COMMAND_RE.search(value))


def _artifact_sha_entry_is_valid(entry: str) -> bool:
    if "=" not in entry:
        return False
    _, checksum = entry.rsplit("=", maxsplit=1)
    return bool(_SHA256_RE.match(checksum.strip()))
