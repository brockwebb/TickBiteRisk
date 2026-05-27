from __future__ import annotations

import csv
import hashlib
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from tickbiterisk.etl.ecology_sources import EcologySourceFile


@dataclass(frozen=True)
class RawDownloadResult:
    manifest_path: Path
    row_count: int


def fetch_url_bytes(
    url: str,
    *,
    attempts: int = 3,
    timeout_seconds: int = 60,
    retry_delay_seconds: float = 1,
) -> bytes:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read()
        except OSError:
            if attempt == attempts - 1:
                raise
            if retry_delay_seconds:
                time.sleep(retry_delay_seconds)

    raise RuntimeError("unreachable")


def download_source_files(
    sources: Iterable[EcologySourceFile],
    *,
    raw_dir: Path,
    manifest_path: Path,
    fetcher: Callable[[str], bytes] = fetch_url_bytes,
) -> RawDownloadResult:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    ingested_at = datetime.now(timezone.utc).isoformat()
    for source in sources:
        content = fetcher(source.url)
        output_path = source.raw_path(raw_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        rows.append(
            {
                "source_id": source.source_id,
                "family": source.family,
                "description": source.description,
                "url": source.url,
                "local_path": str(output_path),
                "expected_format": source.expected_format,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "ingested_at": ingested_at,
            }
        )

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
        writer.writerows(sorted(rows, key=lambda row: row["source_id"]))

    return RawDownloadResult(manifest_path=manifest_path, row_count=len(rows))
