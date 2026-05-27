from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
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
    source_report_year: int | None = None
    parser_method: str | None = None
    extraction_confidence: str | None = None
    black_oak_acorns_per_branch: float | None = None
    white_oak_acorns_per_branch: float | None = None
    unit_average_acorns_per_branch: float | None = None
    black_oak_mast_rating: str | None = None
    white_oak_mast_rating: str | None = None
    unit_average_mast_rating: str | None = None
    white_oak_subjective_crown_pct: float | None = None
    black_oak_subjective_crown_pct: float | None = None


@dataclass(frozen=True)
class MastAcornExtractionSummary:
    year: int
    source_id: str
    source_path: str
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
    mast_rating: str
    observation_basis: str
    observer_scope: str
    source_id: str
    feature_quality_flags: str
    notes: str


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
                source_report_year=year,
                parser_method="county_block_text",
                extraction_confidence="medium",
            )
        )

    rows.extend(
        _parse_dnr_rolling_tables(
            text,
            source_report_year=year,
            source_id=source_id,
            source_url_hash=source_url_hash,
            jurisdictions_by_key=jurisdictions_by_key,
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
        rows = [
            replace(
                row,
                parser_method=_prefixed_parser_method(parser, row.parser_method),
            )
            for row in rows
        ]
    except Exception as exc:
        summary = MastAcornExtractionSummary(
            year=year,
            source_id=source_id,
            source_path=str(source_path),
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
            source_path=str(source_path),
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
        source_path=str(source_path),
        source_url_hash=source_url_hash,
        parser=parser,
        extraction_status="structured",
        structured_row_count=len(rows),
        extracted_text_excerpt=_excerpt(text),
        feature_quality_flags=_combined_quality_flags(rows),
        notes="Structured mast/acorn rows extracted.",
    )
    return rows, summary


def read_manual_mast_observations(input_path: str | Path) -> list[ManualMastObservation]:
    required_flags = (
        "manual_observation",
        "anecdotal",
        "not_official",
        "not_model_default",
    )
    observations = []
    with Path(input_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            county_fips = str(row.get("county_fips", "")).strip().zfill(5)
            flags = _merge_flags(row.get("feature_quality_flags", ""), required_flags)
            observations.append(
                ManualMastObservation(
                    county_fips=county_fips,
                    county_name=str(row.get("county_name", "")).strip(),
                    year=int(str(row.get("year", "")).strip()),
                    mast_rating=str(row.get("mast_rating", "")).strip(),
                    observation_basis=str(row.get("observation_basis", "")).strip(),
                    observer_scope=str(row.get("observer_scope", "")).strip(),
                    source_id=str(row.get("source_id", "")).strip(),
                    feature_quality_flags=flags,
                    notes=str(row.get("notes", "")).strip(),
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
        blocks.append((match.group("county").strip(), text[match.start() : end]))
    return blocks


def _parse_dnr_rolling_tables(
    text: str,
    *,
    source_report_year: int,
    source_id: str,
    source_url_hash: str,
    jurisdictions_by_key: dict[str, MarylandJurisdiction],
) -> list[MastAcornCountyYear]:
    quantitative = _parse_numeric_oak_table(
        _table_section(text, table_number=1),
        value_rows=("Black Oak", "White Oak", "Unit Average"),
    )
    if not quantitative:
        return []
    ratings = _parse_rating_oak_table(_table_section(text, table_number=2))
    subjective = _parse_subjective_oak_table(_table_section(text, table_number=3))
    excerpt = _excerpt(text)
    rows = []
    for county_name, county_values in quantitative.items():
        jurisdiction = jurisdictions_by_key.get(_county_key(county_name))
        if jurisdiction is None:
            continue
        county_ratings = ratings.get(county_name, {})
        county_subjective = subjective.get(county_name, {})
        for observation_year in sorted(county_values):
            values = county_values[observation_year]
            unit_average = values.get("Unit Average")
            rating = county_ratings.get(observation_year, {})
            unit_rating = rating.get("Unit Average")
            subjective_values = county_subjective.get(observation_year, {})
            rows.append(
                MastAcornCountyYear(
                    county_fips=jurisdiction.county_fips,
                    county_name=jurisdiction.county_name,
                    year=observation_year,
                    region="Western Maryland",
                    mast_category="oak_acorn_abundance",
                    mast_index=unit_average,
                    hard_mast_index=unit_average,
                    soft_mast_index=None,
                    acorn_index=unit_average,
                    mast_rating=_rating_label(unit_rating),
                    plots_observed=None,
                    expected_plots=None,
                    coverage_complete=None,
                    source_id=source_id,
                    source_url_hash=source_url_hash,
                    extracted_text_excerpt=excerpt,
                    feature_quality_flags=(
                        "western_maryland_only,study_plot_not_countywide"
                    ),
                    source_report_year=source_report_year,
                    parser_method="table_text",
                    extraction_confidence="high",
                    black_oak_acorns_per_branch=values.get("Black Oak"),
                    white_oak_acorns_per_branch=values.get("White Oak"),
                    unit_average_acorns_per_branch=unit_average,
                    black_oak_mast_rating=rating.get("Black Oak"),
                    white_oak_mast_rating=rating.get("White Oak"),
                    unit_average_mast_rating=unit_rating,
                    white_oak_subjective_crown_pct=subjective_values.get("White Oak"),
                    black_oak_subjective_crown_pct=subjective_values.get("Black Oak"),
                )
            )
    return rows


def _table_section(text: str, *, table_number: int) -> str:
    marker = f"Table {table_number}:"
    end = text.find(marker)
    if end == -1:
        return ""
    if table_number == 1:
        start = text.rfind("Quantitative Assessment", 0, end)
    elif table_number == 2:
        start = text.rfind("rating system", 0, end)
    else:
        start = text.rfind("Subjective Assessment", 0, end)
    return text[max(start, 0) : end]


def _parse_numeric_oak_table(
    section: str,
    *,
    value_rows: tuple[str, ...],
) -> dict[str, dict[int, dict[str, float]]]:
    years = _extract_table_years(section)
    if not years:
        return {}
    parsed: dict[str, dict[int, dict[str, float]]] = {}
    for county_name, block in _dnr_county_table_blocks(section):
        for row_label in value_rows:
            match = re.search(
                rf"(?im)^\s*{re.escape(row_label)}\s+(?P<values>[0-9.,\s]+)\s*$",
                block,
            )
            if match is None:
                continue
            values = _number_tokens(match.group("values"))
            if len(values) != len(years):
                continue
            for table_year, value in zip(years, values, strict=True):
                parsed.setdefault(county_name, {}).setdefault(table_year, {})[
                    row_label
                ] = value
    return parsed


def _parse_rating_oak_table(section: str) -> dict[str, dict[int, dict[str, str]]]:
    years = _extract_table_years(section)
    if not years:
        return {}
    parsed: dict[str, dict[int, dict[str, str]]] = {}
    for county_name, block in _dnr_county_table_blocks(section):
        for row_label in ("Black Oak", "White Oak", "Unit Average"):
            match = re.search(
                rf"(?im)^\s*{re.escape(row_label)}\s+(?P<values>[IVX\s]+)\s*$",
                block,
            )
            if match is None:
                continue
            values = [value.strip() for value in match.group("values").split()]
            if len(values) != len(years):
                continue
            for table_year, value in zip(years, values, strict=True):
                parsed.setdefault(county_name, {}).setdefault(table_year, {})[
                    row_label
                ] = value
    return parsed


def _parse_subjective_oak_table(
    section: str,
) -> dict[str, dict[int, dict[str, float]]]:
    years = _extract_table_years(section)
    if not years:
        return {}
    parsed: dict[str, dict[int, dict[str, float]]] = {}
    for match in re.finditer(
        r"(?ims)^\s*(?P<county>Garrett|Allegany|Washington|Frederick)\s+"
        r"County\s+(?P<values>(?:[0-9.]+%?\s+){9}[0-9.]+%?)",
        section,
    ):
        county_name = f"{match.group('county')} County"
        values = _number_tokens(match.group("values").replace("%", ""))
        if len(values) != len(years) * 2:
            continue
        for index, table_year in enumerate(years):
            white_value = values[index * 2]
            black_value = values[index * 2 + 1]
            parsed.setdefault(county_name, {})[table_year] = {
                "White Oak": white_value,
                "Black Oak": black_value,
            }
    return parsed


def _dnr_county_table_blocks(section: str) -> list[tuple[str, str]]:
    matches = list(
        re.finditer(
            r"(?im)^\s*(?P<county>GARRETT|ALLEGANY|WASHINGTON|FREDERICK)"
            r"(?:\s+County)?\s*$",
            section,
        )
    )
    blocks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        county_name = f"{match.group('county').title()} County"
        blocks.append((county_name, section[match.end() : end]))
    return blocks


def _extract_table_years(section: str) -> list[int]:
    for line in section.splitlines():
        years = [int(value) for value in re.findall(r"\b20\d{2}\b", line)]
        if len(years) >= 5:
            return years[:5]
    match = re.search(r"\((20\d{2})\s*[-–]\s*(20\d{2})\)", section)
    if match is None:
        return []
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        return []
    return list(range(start, end + 1))


def _number_tokens(value: str) -> list[float]:
    return [
        _parse_float_or_none(token.rstrip("%"))
        for token in re.findall(r"\d+(?:\.\d+)?%?", value)
        if _parse_float_or_none(token.rstrip("%")) is not None
    ]


def _rating_label(value: str | None) -> str | None:
    labels = {
        "I": "mast_failure",
        "II": "poor_and_spotty",
        "III": "average",
        "IV": "abundant",
        "V": "bumper_crop",
    }
    if value is None:
        return None
    return labels.get(value.strip().upper(), value.strip() or None)


def _prefixed_parser_method(parser: str, parser_method: str | None) -> str:
    method = (parser_method or "text").strip()
    if method.startswith(f"{parser}_"):
        return method
    return f"{parser}_{method}"


def _combined_quality_flags(rows: list[MastAcornCountyYear]) -> str:
    flags = [
        flag
        for row in rows
        for flag in _split_flags(row.feature_quality_flags)
    ]
    return ",".join(_dedupe_preserve_order(flags))


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


def _merge_flags(existing_flags: object, required_flags: tuple[str, ...]) -> str:
    flags = [
        flag.strip()
        for flag in str(existing_flags).split(",")
        if flag.strip()
    ]
    seen = set(flags)
    for flag in required_flags:
        if flag not in seen:
            flags.append(flag)
            seen.add(flag)
    return ",".join(flags)


def _split_flags(value: str | None) -> list[str]:
    if value is None:
        return []
    return [flag.strip() for flag in str(value).replace(";", ",").split(",") if flag.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
