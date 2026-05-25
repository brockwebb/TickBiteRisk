from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tickbiterisk.etl.deer_harvest import (
    extract_docling_markdown,
    extract_pypdfium_text,
)
from tickbiterisk.etl.maryland import MarylandJurisdiction, load_maryland_jurisdictions


@dataclass(frozen=True)
class MastAcornCountyYear:
    county_fips: str
    county_name: str
    year: int
    region: str | None
    mast_category: str | None
    mast_index: float | None
    hard_mast_index: float | None
    soft_mast_index: float | None
    acorn_index: float | None
    mast_rating: str | None
    plots_observed: int | None
    expected_plots: int | None
    coverage_complete: bool | None
    source_id: str
    source_url_hash: str
    extracted_text_excerpt: str
    feature_quality_flags: str


@dataclass(frozen=True)
class MastAcornExtractionSummary:
    year: int
    source_id: str
    source_url_hash: str
    parser: str
    extraction_status: str
    structured_row_count: int
    extracted_text_excerpt: str
    feature_quality_flags: str
    notes: str


@dataclass(frozen=True)
class ManualMastObservation:
    county_fips: str
    county_name: str
    year: int
    region: str | None
    mast_category: str | None
    mast_index: float | None
    hard_mast_index: float | None
    soft_mast_index: float | None
    acorn_index: float | None
    mast_rating: str | None
    observation_notes: str | None
    source_id: str
    source_url_hash: str
    feature_quality_flags: str


def parse_mast_acorn_text(
    text: str,
    *,
    year: int,
    source_id: str,
    source_url: str,
) -> list[MastAcornCountyYear]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    jurisdictions_by_key = _jurisdictions_by_county_key()

    rows = []
    for county_name, block in _county_blocks(text):
        jurisdiction = jurisdictions_by_key.get(_county_key(county_name))
        if jurisdiction is None:
            continue

        hard_mast_index = _extract_float(block, "Hard Mast Index")
        soft_mast_index = _extract_float(block, "Soft Mast Index")
        acorn_index = _extract_float(block, "Acorn Index")
        mast_index = _extract_float(block, "Mast Index")
        if mast_index is None:
            mast_index = hard_mast_index
        if not any(
            value is not None
            for value in (mast_index, hard_mast_index, soft_mast_index, acorn_index)
        ):
            continue

        plots_observed = _extract_int(block, "Plots Observed")
        expected_plots = _extract_int(block, "Expected Plots")
        coverage_complete = None
        if plots_observed is not None and expected_plots is not None:
            coverage_complete = plots_observed >= expected_plots

        rows.append(
            MastAcornCountyYear(
                county_fips=jurisdiction.county_fips,
                county_name=jurisdiction.county_name,
                year=year,
                region=_extract_label(block, "Region") or _extract_label(text, "Region"),
                mast_category=_extract_label(block, "Mast Category"),
                mast_index=mast_index,
                hard_mast_index=hard_mast_index,
                soft_mast_index=soft_mast_index,
                acorn_index=acorn_index,
                mast_rating=_extract_label(block, "Mast Rating"),
                plots_observed=plots_observed,
                expected_plots=expected_plots,
                coverage_complete=coverage_complete,
                source_id=source_id,
                source_url_hash=source_url_hash,
                extracted_text_excerpt=_excerpt(text),
                feature_quality_flags="western_maryland_only",
            )
        )

    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))


def build_mast_acorn_from_pdf(
    source_path: str | Path,
    *,
    year: int,
    source_id: str,
    source_url: str,
    parser: str,
    text_extractor: Callable[[str | Path], str] = extract_pypdfium_text,
    converter_factory: Callable[[], object] | None = None,
) -> tuple[list[MastAcornCountyYear], MastAcornExtractionSummary]:
    if parser not in {"pypdfium", "docling"}:
        raise ValueError("PDF parser must be 'pypdfium' or 'docling'")

    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    try:
        if parser == "docling" or converter_factory is not None:
            text = extract_docling_markdown(
                source_path,
                converter_factory=converter_factory,
            )
        else:
            text = text_extractor(source_path)
        rows = parse_mast_acorn_text(
            text,
            year=year,
            source_id=source_id,
            source_url=source_url,
        )
    except Exception as exc:
        summary = MastAcornExtractionSummary(
            year=year,
            source_id=source_id,
            source_url_hash=source_url_hash,
            parser=parser,
            extraction_status="parser_failed",
            structured_row_count=0,
            extracted_text_excerpt="",
            feature_quality_flags="parser_low_confidence",
            notes=str(exc),
        )
        return [], summary

    if not rows:
        summary = MastAcornExtractionSummary(
            year=year,
            source_id=source_id,
            source_url_hash=source_url_hash,
            parser=parser,
            extraction_status="no_supported_values",
            structured_row_count=0,
            extracted_text_excerpt=_excerpt(text),
            feature_quality_flags="ocr_pending,parser_low_confidence",
            notes="No supported mast/acorn county table values were found.",
        )
        return [], summary

    summary = MastAcornExtractionSummary(
        year=year,
        source_id=source_id,
        source_url_hash=source_url_hash,
        parser=parser,
        extraction_status="structured",
        structured_row_count=len(rows),
        extracted_text_excerpt=_excerpt(text),
        feature_quality_flags="",
        notes="Structured mast/acorn rows extracted.",
    )
    return rows, summary


def read_manual_mast_observations(input_path: str | Path) -> list[ManualMastObservation]:
    required_flags = {
        "manual_observation",
        "anecdotal",
        "not_official",
        "not_model_default",
    }
    observations = []
    with Path(input_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            county_fips = str(row.get("county_fips", "")).strip().zfill(5)
            source_url_hash = str(row.get("source_url_hash", "")).strip()
            source_url = str(row.get("source_url", "")).strip()
            if not source_url_hash and source_url:
                source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
            flags = _merge_flags(row.get("feature_quality_flags", ""), required_flags)
            observations.append(
                ManualMastObservation(
                    county_fips=county_fips,
                    county_name=str(row.get("county_name", "")).strip(),
                    year=int(str(row.get("year", "")).strip()),
                    region=_optional_text(row.get("region", "")),
                    mast_category=_optional_text(row.get("mast_category", "")),
                    mast_index=_parse_float_or_none(row.get("mast_index", "")),
                    hard_mast_index=_parse_float_or_none(row.get("hard_mast_index", "")),
                    soft_mast_index=_parse_float_or_none(row.get("soft_mast_index", "")),
                    acorn_index=_parse_float_or_none(row.get("acorn_index", "")),
                    mast_rating=_optional_text(row.get("mast_rating", "")),
                    observation_notes=_optional_text(row.get("observation_notes", "")),
                    source_id=str(row.get("source_id", "")).strip(),
                    source_url_hash=source_url_hash,
                    feature_quality_flags=flags,
                )
            )
    return sorted(
        observations,
        key=lambda row: (row.county_fips, row.year, row.source_id),
    )


def _county_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(
        re.finditer(
            r"(?im)^\s*County\s*:\s*(?P<county>[^\n\r]+)\s*$",
            text,
        )
    )
    blocks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block_start = 0 if index == 0 else match.start()
        blocks.append((match.group("county").strip(), text[block_start:end]))
    return blocks


def _extract_label(text: str, label: str) -> str | None:
    match = re.search(
        rf"(?im)^\s*{re.escape(label)}\s*:\s*(?P<value>[^\n\r]+?)\s*$",
        text,
    )
    if match is None:
        return None
    value = match.group("value").strip()
    return value or None


def _extract_float(text: str, label: str) -> float | None:
    value = _extract_label(text, label)
    if value is None:
        return None
    return _parse_float_or_none(value)


def _extract_int(text: str, label: str) -> int | None:
    value = _extract_label(text, label)
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    return int(cleaned)


def _parse_float_or_none(value: object) -> float | None:
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    return float(cleaned)


def _optional_text(value: object) -> str | None:
    cleaned = str(value).strip()
    return cleaned or None


def _jurisdictions_by_county_key() -> dict[str, MarylandJurisdiction]:
    return {
        _county_key(jurisdiction.county_name): jurisdiction
        for jurisdiction in load_maryland_jurisdictions()
    }


def _county_key(value: str) -> str:
    cleaned = value.lower().replace("’", "'")
    cleaned = re.sub(r"\bcounty\b", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned


def _excerpt(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:500]


def _merge_flags(existing_flags: object, required_flags: set[str]) -> str:
    flags = [
        flag.strip()
        for flag in str(existing_flags).split(",")
        if flag.strip()
    ]
    seen = set(flags)
    for flag in sorted(required_flags):
        if flag not in seen:
            flags.append(flag)
            seen.add(flag)
    return ",".join(flags)
