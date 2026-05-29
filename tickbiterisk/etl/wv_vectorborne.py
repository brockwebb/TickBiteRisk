from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class WestVirginiaVectorborneStateSummary:
    state_fips: str
    state_abbr: str
    state_name: str
    report_year: int
    as_of_date: str
    disease: str
    confirmed_probable_cases: int
    counties_reported: int | None
    source_id: str
    source_url: str
    parser_method: str
    feature_quality_flags: str


def parse_wv_vectorborne_report_pdf(
    path: Path,
    *,
    source_id: str,
    source_url: str,
) -> list[WestVirginiaVectorborneStateSummary]:
    text = _extract_pypdfium_text(path)
    return parse_wv_vectorborne_report_text(
        text,
        source_id=source_id,
        source_url=source_url,
        parser_method="pypdfium_text_table3",
    )


def parse_wv_vectorborne_report_text(
    text: str,
    *,
    source_id: str,
    source_url: str,
    parser_method: str,
) -> list[WestVirginiaVectorborneStateSummary]:
    normalized = _normalize_text(text)
    report_year, as_of_date = _extract_report_date(normalized)
    table_text = _extract_table3_text(normalized)
    rows = []
    for disease, cases_text, counties_text in _TABLE_ROW_RE.findall(table_text):
        disease_name = _clean_disease_name(disease)
        rows.append(
            WestVirginiaVectorborneStateSummary(
                state_fips="54",
                state_abbr="WV",
                state_name="West Virginia",
                report_year=report_year,
                as_of_date=as_of_date,
                disease=disease_name,
                confirmed_probable_cases=int(cases_text),
                counties_reported=_parse_counties_reported(counties_text),
                source_id=source_id,
                source_url=source_url,
                parser_method=parser_method,
                feature_quality_flags=",".join(
                    _quality_flags(report_year=report_year, disease=disease_name)
                ),
            )
        )
    if not rows:
        raise ValueError("No West Virginia vectorborne Table 3 rows parsed")
    return rows


_TABLE_ROW_RE = re.compile(
    r"(?P<disease>Alpha-Gal Syndrome|Anaplasmosis|Babesiosis|Ehrlichiosis|"
    r"Lyme disease|Spotted fever group rickettsiosis[a-z]?|Total)\s+"
    r"(?P<cases>\d+)\s+"
    r"(?P<counties>\d+|--)"
)


def _extract_pypdfium_text(path: Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ValueError("pypdfium2 is required to parse WV vectorborne PDFs") from exc

    pdf = pdfium.PdfDocument(path)
    text_parts = []
    for page in pdf:
        text_parts.append(page.get_textpage().get_text_range())
    return "\n".join(text_parts)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u2013", "-").replace("\u2014", "-"))


def _extract_report_date(text: str) -> tuple[int, str]:
    match = re.search(
        r"JANUARY\s+1\s*-\s*([A-Z]+)\s+(\d{1,2}),\s*(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"through\s+([A-Z][a-z]+|[A-Z]+)\s+(\d{1,2}),\s*(\d{4})",
            text,
            flags=re.IGNORECASE,
        )
    if not match:
        raise ValueError("West Virginia vectorborne report date not found")
    month, day, year = match.groups()
    parsed = datetime.strptime(f"{month.title()} {int(day)} {year}", "%B %d %Y")
    return parsed.year, parsed.date().isoformat()


def _extract_table3_text(text: str) -> str:
    start = text.find("Table 3.")
    if start < 0:
        raise ValueError("West Virginia vectorborne Table 3 not found")
    end_candidates = [
        index
        for marker in ("Figure 1.", "TICK SURVEILLANCE", "aTable includes")
        if (index := text.find(marker, start + 1)) > start
    ]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


def _clean_disease_name(value: str) -> str:
    return value.removesuffix("b").strip()


def _parse_counties_reported(value: str) -> int | None:
    if value == "--":
        return None
    return int(value)


def _quality_flags(*, report_year: int, disease: str) -> list[str]:
    flags = [
        "wv_oeps_vectorborne_report",
        "state_aggregate_validation",
        "provisional_ytd_report",
        "no_county_detail",
        "confirmed_and_probable_cases",
        "reported_cases_not_stable_true_incidence",
    ]
    if report_year >= 2022:
        flags.append("lyme_case_definition_change")
    if disease == "Total":
        flags.append("all_tickborne_diseases_total")
    return flags
