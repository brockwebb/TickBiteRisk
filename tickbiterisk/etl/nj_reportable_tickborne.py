from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class NewJerseyReportableTickborneCountyYear:
    state_fips: str
    state_abbr: str
    state_name: str
    report_year: int
    report_period_start: str
    report_period_end: str
    prepared_at: str
    jurisdiction: str
    county_name: str
    county_fips: str
    geography_type: str
    disease: str
    case_count: int
    source_id: str
    source_url: str
    parser_method: str
    feature_quality_flags: str


def parse_nj_doh_reportable_tickborne_pdf(
    path: Path,
    *,
    source_id: str,
    source_url: str,
) -> list[NewJerseyReportableTickborneCountyYear]:
    text = _extract_pypdfium_text(path)
    return parse_nj_doh_reportable_tickborne_text(
        text,
        source_id=source_id,
        source_url=source_url,
        parser_method="pypdfium_text_reportable_rows",
    )


def parse_nj_doh_reportable_tickborne_text(
    text: str,
    *,
    source_id: str,
    source_url: str,
    parser_method: str,
) -> list[NewJerseyReportableTickborneCountyYear]:
    report_year = _extract_report_year(text)
    prepared_at = _extract_prepared_at(text)
    report_period_start, report_period_end = _extract_report_period(text)

    rows: list[NewJerseyReportableTickborneCountyYear] = []
    for line in text.splitlines():
        parsed = _parse_reportable_row(line)
        if parsed is None:
            continue
        jurisdiction, disease, case_count = parsed
        geography = _jurisdiction_geography(jurisdiction)
        rows.append(
            NewJerseyReportableTickborneCountyYear(
                state_fips="34",
                state_abbr="NJ",
                state_name="New Jersey",
                report_year=report_year,
                report_period_start=report_period_start,
                report_period_end=report_period_end,
                prepared_at=prepared_at,
                jurisdiction=jurisdiction,
                county_name=geography.county_name,
                county_fips=geography.county_fips,
                geography_type=geography.geography_type,
                disease=disease,
                case_count=case_count,
                source_id=source_id,
                source_url=source_url,
                parser_method=parser_method,
                feature_quality_flags=",".join(
                    _quality_flags(disease=disease, case_count=case_count)
                ),
            )
        )
    if not rows:
        raise ValueError("No New Jersey DOH reportable tickborne rows parsed")
    return rows


@dataclass(frozen=True)
class _NjGeography:
    county_name: str
    county_fips: str
    geography_type: str


_NJ_COUNTIES: dict[str, _NjGeography] = {
    "ATLANTIC": _NjGeography("Atlantic", "34001", "county"),
    "BERGEN": _NjGeography("Bergen", "34003", "county"),
    "BURLINGTON": _NjGeography("Burlington", "34005", "county"),
    "CAMDEN": _NjGeography("Camden", "34007", "county"),
    "CAPE MAY": _NjGeography("Cape May", "34009", "county"),
    "CUMBERLAND": _NjGeography("Cumberland", "34011", "county"),
    "ESSEX": _NjGeography("Essex", "34013", "county"),
    "GLOUCESTER": _NjGeography("Gloucester", "34015", "county"),
    "HUDSON": _NjGeography("Hudson", "34017", "county"),
    "HUNTERDON": _NjGeography("Hunterdon", "34019", "county"),
    "MERCER": _NjGeography("Mercer", "34021", "county"),
    "MIDDLESEX": _NjGeography("Middlesex", "34023", "county"),
    "MONMOUTH": _NjGeography("Monmouth", "34025", "county"),
    "MORRIS": _NjGeography("Morris", "34027", "county"),
    "OCEAN": _NjGeography("Ocean", "34029", "county"),
    "PASSAIC": _NjGeography("Passaic", "34031", "county"),
    "SALEM": _NjGeography("Salem", "34033", "county"),
    "SOMERSET": _NjGeography("Somerset", "34035", "county"),
    "SUSSEX": _NjGeography("Sussex", "34037", "county"),
    "UNION": _NjGeography("Union", "34039", "county"),
    "WARREN": _NjGeography("Warren", "34041", "county"),
}
_STATE_TOTAL = _NjGeography("", "", "state_total")
_JURISDICTIONS = ["STATE TOTAL", *_NJ_COUNTIES.keys()]
_JURISDICTIONS_BY_LENGTH = sorted(_JURISDICTIONS, key=len, reverse=True)


_TICKBORNE_DISEASES = {
    "ALPHA-GAL SYNDROME": "Alpha-gal syndrome",
    "BABESIOSIS": "Babesiosis",
    "EHRLICHIOSIS/ANAPLASMOSIS - ANAPLASMA PHAGOCYTOPHILUM (PREVIOUSLY HGE)": (
        "Ehrlichiosis/Anaplasmosis - Anaplasma phagocytophilum (previously HGE)"
    ),
    "EHRLICHIOSIS/ANAPLASMOSIS - EHRLICHIA CHAFFEENSIS (PREVIOUSLY HME)": (
        "Ehrlichiosis/Anaplasmosis - Ehrlichia chaffeensis (previously HME)"
    ),
    "EHRLICHIOSIS/ANAPLASMOSIS - EHRLICHIA EWINGII": (
        "Ehrlichiosis/Anaplasmosis - Ehrlichia ewingii"
    ),
    "EHRLICHIOSIS/ANAPLASMOSIS - UNDETERMINED": (
        "Ehrlichiosis/Anaplasmosis - undetermined"
    ),
    "LYME DISEASE": "Lyme disease",
    "POWASSAN": "Powassan",
    "SPOTTED FEVER GROUP RICKETTSIOSIS": "Spotted fever group rickettsiosis",
    "TULAREMIA": "Tularemia",
}


def _extract_pypdfium_text(path: Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ValueError("pypdfium2 is required to parse NJ DOH PDFs") from exc

    pdf = pdfium.PdfDocument(path)
    text_parts = []
    for page in pdf:
        text_parts.append(page.get_textpage().get_text_range())
    return "\n".join(text_parts)


def _extract_report_year(text: str) -> int:
    match = re.search(
        r"\b(20\d{2})\s+New Jersey Reportable Communicable Disease Report",
        text,
    )
    if not match:
        raise ValueError("New Jersey DOH report year not found")
    return int(match.group(1))


def _extract_prepared_at(text: str) -> str:
    match = re.search(
        r"\b\d{1,2}:\d{2}\s+\w+,\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
        text,
    )
    if not match:
        raise ValueError("New Jersey DOH prepared date not found")
    return datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()


def _extract_report_period(text: str) -> tuple[str, str]:
    match = re.search(
        r"\(\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s+to\s+"
        r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s*\)",
        text,
    )
    if not match:
        raise ValueError("New Jersey DOH report period not found")
    start, end = match.groups()
    return (
        datetime.strptime(start, "%B %d, %Y").date().isoformat(),
        datetime.strptime(end, "%B %d, %Y").date().isoformat(),
    )


def _parse_reportable_row(line: str) -> tuple[str, str, int] | None:
    normalized = re.sub(r"\s+", " ", line.replace("\u2013", "-")).strip()
    if not normalized:
        return None
    for jurisdiction in _JURISDICTIONS_BY_LENGTH:
        prefix = f"{jurisdiction} "
        if not normalized.startswith(prefix):
            continue
        rest = normalized.removeprefix(prefix)
        match = re.fullmatch(r"(.+)\s+(\d+)", rest)
        if not match:
            return None
        disease_key, case_count = match.groups()
        disease = _TICKBORNE_DISEASES.get(disease_key)
        if disease is None:
            return None
        return jurisdiction, disease, int(case_count)
    return None


def _jurisdiction_geography(jurisdiction: str) -> _NjGeography:
    if jurisdiction == "STATE TOTAL":
        return _STATE_TOTAL
    return _NJ_COUNTIES[jurisdiction]


def _quality_flags(*, disease: str, case_count: int) -> list[str]:
    flags = [
        "nj_doh_reportable_disease_statistics",
        "northeast_extension_sidecar",
        "state_source_not_cdc_public_use",
        "confirmed_and_probable_cases",
        "reported_cases_not_stable_true_incidence",
        "not_confirmed_case_truth",
        "not_public_default",
        "not_model_input",
    ]
    if disease == "Lyme disease":
        flags.append("lyme_case_definition_change")
        flags.append("lyme_2022_laboratory_based_surveillance")
    if disease.startswith("Ehrlichiosis/Anaplasmosis"):
        flags.append("ehrlichiosis_anaplasmosis_reporting_change_2024")
    if disease == "Alpha-gal syndrome":
        flags.append("alpha_gal_voluntary_reporting_underestimate")
    if case_count < 5:
        flags.append("low_count_public_interpretation_caution")
    return flags
