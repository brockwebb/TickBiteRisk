from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


_NON_LOCAL_LOCATION_LABELS = {
    "capc maps/data",
    "census api",
    "maryland dnr website",
    "mrlc data portal",
    "power bi dashboard",
}


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source: str
    location: str
    format: str
    geography: str
    time_coverage: str
    role: str
    status: str
    redistribution: str
    notes: str

    @property
    def is_local(self) -> bool:
        location = self.location.strip()
        if not location or location.startswith(("http://", "https://")):
            return False
        if location.casefold() in _NON_LOCAL_LOCATION_LABELS:
            return False
        return (
            Path(location).is_absolute()
            or location.startswith(("./", "../", "~/"))
            or "/" in location
            or "\\" in location
        )


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_cell(value: str) -> str:
    return value.strip().replace("`", "")


def _split_markdown_row(line: str) -> list[str]:
    return [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]


def load_sources_from_markdown(path: Path) -> list[SourceRecord]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[list[str]] = []
    in_catalog = False
    for line in lines:
        if line.startswith("| ID | Source | Local path / URL |"):
            in_catalog = True
            continue
        if in_catalog and re.match(r"^\| [-: ]+ \|", line):
            continue
        if in_catalog and line.startswith("| "):
            cells = _split_markdown_row(line)
            if len(cells) >= 10:
                rows.append(cells[:10])
            continue
        if in_catalog and rows:
            break

    return [
        SourceRecord(
            source_id=row[0],
            source=row[1],
            location=row[2],
            format=row[3],
            geography=row[4],
            time_coverage=row[5],
            role=row[6],
            status=row[7],
            redistribution=row[8],
            notes=row[9],
        )
        for row in rows
    ]
