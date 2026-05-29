from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class MassDphSyndromicEdCountySummary:
    state_fips: str
    state_abbr: str
    state_name: str
    report_year: int
    report_period_label: str
    report_period_start: str
    report_period_end: str
    county_name: str
    county_fips: str
    county_fips_list: str
    geography_type: str
    total_ed_visits: int
    tickborne_disease_ed_visits: int
    tickborne_disease_rate_per_10000: float
    missing_or_out_of_state_visits: int | None
    source_id: str
    source_url: str
    parser_method: str
    feature_quality_flags: str


def parse_mass_dph_syndromic_ed_docx(
    path: Path,
    *,
    source_id: str,
    source_url: str,
    report_year: int,
    report_period_label: str,
    report_period_start: str,
    report_period_end: str,
    expected_geography_count: int | None = 13,
) -> list[MassDphSyndromicEdCountySummary]:
    tables, document_text = _extract_docx_content(path)
    table = _find_table1(tables)
    parsed_rows: list[tuple[_MassCountyGeography, int, int, float]] = []
    missing_or_out_of_state_visits: int | None = None

    for row in table:
        if not row:
            continue
        county_cell = row[0].strip()
        if not county_cell:
            continue
        if _is_missing_or_out_of_state_row(row):
            missing_or_out_of_state_visits = _parse_missing_or_out_of_state(row)
            continue
        geography = _county_geography(county_cell)
        if geography is None:
            if _is_table1_data_row(row):
                raise ValueError(
                    "Unrecognized Massachusetts DPH county or combined geography "
                    f"in Table 1: {county_cell!r}"
                )
            continue
        if len(row) < 4:
            raise ValueError(f"Massachusetts DPH Table 1 row has too few cells: {row}")
        parsed_rows.append(
            (
                geography,
                _parse_int(row[1]),
                _parse_int(row[2]),
                _parse_float(row[3]),
            )
        )

    if missing_or_out_of_state_visits is None:
        missing_or_out_of_state_visits = _parse_missing_or_out_of_state_text(
            document_text
        )

    if not parsed_rows:
        raise ValueError("No Massachusetts DPH syndromic ED county rows parsed")
    _validate_expected_geographies(
        parsed_rows,
        expected_geography_count=expected_geography_count,
    )

    return [
        MassDphSyndromicEdCountySummary(
            state_fips="25",
            state_abbr="MA",
            state_name="Massachusetts",
            report_year=report_year,
            report_period_label=report_period_label,
            report_period_start=report_period_start,
            report_period_end=report_period_end,
            county_name=geography.name,
            county_fips=geography.county_fips,
            county_fips_list=geography.county_fips_list,
            geography_type=geography.geography_type,
            total_ed_visits=total_ed_visits,
            tickborne_disease_ed_visits=tickborne_disease_ed_visits,
            tickborne_disease_rate_per_10000=rate_per_10000,
            missing_or_out_of_state_visits=missing_or_out_of_state_visits,
            source_id=source_id,
            source_url=source_url,
            parser_method="docx_word_table1",
            feature_quality_flags=",".join(
                _quality_flags(geography_type=geography.geography_type)
            ),
        )
        for (
            geography,
            total_ed_visits,
            tickborne_disease_ed_visits,
            rate_per_10000,
        ) in parsed_rows
    ]


@dataclass(frozen=True)
class _MassCountyGeography:
    name: str
    county_fips: str
    county_fips_list: str
    geography_type: str


_MA_COUNTIES: dict[str, _MassCountyGeography] = {
    "barnstable": _MassCountyGeography("Barnstable", "25001", "25001", "county"),
    "berkshire": _MassCountyGeography("Berkshire", "25003", "25003", "county"),
    "bristol": _MassCountyGeography("Bristol", "25005", "25005", "county"),
    "dukes/nantucket": _MassCountyGeography(
        "Dukes/Nantucket",
        "",
        "25007;25019",
        "combined_counties",
    ),
    "dukes / nantucket": _MassCountyGeography(
        "Dukes/Nantucket",
        "",
        "25007;25019",
        "combined_counties",
    ),
    "essex": _MassCountyGeography("Essex", "25009", "25009", "county"),
    "franklin": _MassCountyGeography("Franklin", "25011", "25011", "county"),
    "hampden": _MassCountyGeography("Hampden", "25013", "25013", "county"),
    "hampshire": _MassCountyGeography("Hampshire", "25015", "25015", "county"),
    "middlesex": _MassCountyGeography("Middlesex", "25017", "25017", "county"),
    "norfolk": _MassCountyGeography("Norfolk", "25021", "25021", "county"),
    "plymouth": _MassCountyGeography("Plymouth", "25023", "25023", "county"),
    "suffolk": _MassCountyGeography("Suffolk", "25025", "25025", "county"),
    "worcester": _MassCountyGeography("Worcester", "25027", "25027", "county"),
}
_EXPECTED_GEOGRAPHY_NAMES = {geography.name for geography in _MA_COUNTIES.values()}


_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_WORD_TEXT = f"{{{_WORD_NS['w']}}}t"
_WORD_TAB = f"{{{_WORD_NS['w']}}}tab"
_WORD_BREAK = f"{{{_WORD_NS['w']}}}br"


def _extract_docx_content(path: Path) -> tuple[list[list[list[str]]], str]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    tables = []
    for table in root.findall(".//w:tbl", _WORD_NS):
        rows = []
        for table_row in table.findall("./w:tr", _WORD_NS):
            cells = [
                _extract_cell_text(cell)
                for cell in table_row.findall("./w:tc", _WORD_NS)
            ]
            rows.append(cells)
        tables.append(rows)
    return tables, _extract_element_text(root)


def _extract_cell_text(cell: ET.Element) -> str:
    return _extract_element_text(cell)


def _extract_element_text(element: ET.Element) -> str:
    paragraph_texts = [
        _extract_paragraph_text(paragraph)
        for paragraph in element.findall(".//w:p", _WORD_NS)
    ]
    if paragraph_texts:
        return _normalize_space(" ".join(text for text in paragraph_texts if text))

    return _normalize_space(_extract_paragraph_text(element))


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    parts = []
    for node in paragraph.iter():
        if node.tag == _WORD_TEXT and node.text:
            parts.append(node.text)
        elif node.tag in {_WORD_TAB, _WORD_BREAK}:
            parts.append(" ")
    return "".join(parts)


def _find_table1(tables: list[list[list[str]]]) -> list[list[str]]:
    for table in tables:
        for index, row in enumerate(table):
            normalized_cells = [_normalize_header(cell) for cell in row]
            if (
                any(cell == "county" for cell in normalized_cells)
                and any("total visits" in cell for cell in normalized_cells)
                and any("tick borne disease visits" in cell for cell in normalized_cells)
                and any("rate" in cell and "10 000" in cell for cell in normalized_cells)
            ):
                return table[index + 1 :]
    raise ValueError("Massachusetts DPH Table 1 county ED visit table not found")


def _county_geography(value: str) -> _MassCountyGeography | None:
    return _MA_COUNTIES.get(_normalize_county(value))


def _normalize_county(value: str) -> str:
    normalized = _normalize_space(value).casefold()
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    return normalized


def _normalize_header(value: str) -> str:
    normalized = _normalize_space(value).casefold()
    normalized = normalized.replace("-", " ").replace("/", " ")
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _is_missing_or_out_of_state_row(row: list[str]) -> bool:
    return "missing" in row[0].casefold() and "out of state" in row[0].casefold()


def _is_table1_data_row(row: list[str]) -> bool:
    return len(row) >= 4 and all(re.search(r"\d", cell) for cell in row[1:4])


def _validate_expected_geographies(
    parsed_rows: list[tuple[_MassCountyGeography, int, int, float]],
    *,
    expected_geography_count: int | None,
) -> None:
    if expected_geography_count is None:
        return
    observed_names = {geography.name for geography, *_ in parsed_rows}
    if len(parsed_rows) != expected_geography_count:
        raise ValueError(
            "Massachusetts DPH Table 1 parsed "
            f"{len(parsed_rows)} geography row(s), expected {expected_geography_count}"
        )
    if expected_geography_count == len(_EXPECTED_GEOGRAPHY_NAMES):
        missing_names = sorted(_EXPECTED_GEOGRAPHY_NAMES - observed_names)
        extra_names = sorted(observed_names - _EXPECTED_GEOGRAPHY_NAMES)
        if missing_names or extra_names:
            raise ValueError(
                "Massachusetts DPH Table 1 geography coverage mismatch: "
                f"missing={missing_names}, extra={extra_names}"
            )


def _parse_missing_or_out_of_state(row: list[str]) -> int | None:
    text = " ".join(row)
    parsed = _parse_missing_or_out_of_state_text(text)
    if parsed is not None:
        return parsed
    for cell in row[1:]:
        if re.search(r"\d", cell):
            return _parse_int(cell)
    return None


def _parse_missing_or_out_of_state_text(text: str) -> int | None:
    match = re.search(
        r"(?:missing|out of state).{0,160}\bn\s*=\s*([\d,]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return _parse_int(match.group(1))
    return None


def _parse_int(value: str) -> int:
    match = re.search(r"[\d,]+", value)
    if not match:
        raise ValueError(f"Expected integer value, got {value!r}")
    return int(match.group(0).replace(",", ""))


def _parse_float(value: str) -> float:
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        raise ValueError(f"Expected numeric rate value, got {value!r}")
    return float(match.group(0))


def _quality_flags(*, geography_type: str) -> list[str]:
    flags = [
        "mass_dph_official_docx",
        "syndromic_ed_signal",
        "ed_visit_proxy",
        "ytd_snapshot",
        "not_reported_case_outcome",
        "not_lyme_incidence",
        "not_confirmed_case_truth",
        "not_disease_specific",
        "not_tick_bite_count",
        "county_residence_available",
        "icd10_tickborne_disease_definition",
        "not_public_default",
        "not_model_input",
    ]
    if geography_type == "combined_counties":
        flags.append("dukes_nantucket_combined")
    return flags
