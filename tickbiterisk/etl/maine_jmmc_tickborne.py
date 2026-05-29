from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MaineJmmcTickborneCountyRate:
    state_fips: str
    state_abbr: str
    state_name: str
    year: int
    preliminary_as_of: str
    region_name: str
    county_name: str
    county_fips: str
    geography_type: str
    anaplasmosis_rate_per_100k: float
    babesiosis_rate_per_100k: float
    hard_tick_relapsing_fever_rate_per_100k: float
    lyme_disease_rate_per_100k: float
    powassan_virus_disease_rate_per_100k: float
    source_id: str
    source_url: str
    parser_method: str
    feature_quality_flags: str


def parse_maine_jmmc_tickborne_rates_pdf(
    path: Path,
    *,
    source_id: str,
    source_url: str,
) -> list[MaineJmmcTickborneCountyRate]:
    text = _extract_pypdfium_text(path)
    return parse_maine_jmmc_tickborne_rates_text(
        text,
        source_id=source_id,
        source_url=source_url,
        parser_method="pypdfium_text_table2_rates",
        require_all_regions=True,
    )


def parse_maine_jmmc_tickborne_rates_text(
    text: str,
    *,
    source_id: str,
    source_url: str,
    parser_method: str,
    require_all_regions: bool = False,
) -> list[MaineJmmcTickborneCountyRate]:
    year = _extract_table_year(text)
    preliminary_as_of = _extract_preliminary_as_of(text)
    table_text = _extract_table2_text(text)
    rows: list[MaineJmmcTickborneCountyRate] = []
    for line in table_text.splitlines():
        parsed = _parse_rate_row(line)
        if parsed is None:
            continue
        region_name, rates = parsed
        geography = _region_geography(region_name)
        rows.append(
            MaineJmmcTickborneCountyRate(
                state_fips="23",
                state_abbr="ME",
                state_name="Maine",
                year=year,
                preliminary_as_of=preliminary_as_of,
                region_name=region_name,
                county_name=geography.county_name,
                county_fips=geography.county_fips,
                geography_type=geography.geography_type,
                anaplasmosis_rate_per_100k=rates[0],
                babesiosis_rate_per_100k=rates[1],
                hard_tick_relapsing_fever_rate_per_100k=rates[2],
                lyme_disease_rate_per_100k=rates[3],
                powassan_virus_disease_rate_per_100k=rates[4],
                source_id=source_id,
                source_url=source_url,
                parser_method=parser_method,
                feature_quality_flags=",".join(
                    _quality_flags(preliminary_as_of=preliminary_as_of)
                ),
            )
        )
    if not rows:
        raise ValueError("No Maine JMMC Table 2 tickborne rate rows parsed")
    if require_all_regions:
        _validate_complete_region_set(rows)
    return rows


@dataclass(frozen=True)
class _MaineGeography:
    county_name: str
    county_fips: str
    geography_type: str


_MAINE_COUNTIES: dict[str, _MaineGeography] = {
    "Androscoggin": _MaineGeography("Androscoggin", "23001", "county"),
    "Aroostook": _MaineGeography("Aroostook", "23003", "county"),
    "Cumberland": _MaineGeography("Cumberland", "23005", "county"),
    "Franklin": _MaineGeography("Franklin", "23007", "county"),
    "Hancock": _MaineGeography("Hancock", "23009", "county"),
    "Kennebec": _MaineGeography("Kennebec", "23011", "county"),
    "Knox": _MaineGeography("Knox", "23013", "county"),
    "Lincoln": _MaineGeography("Lincoln", "23015", "county"),
    "Oxford": _MaineGeography("Oxford", "23017", "county"),
    "Penobscot": _MaineGeography("Penobscot", "23019", "county"),
    "Piscataquis": _MaineGeography("Piscataquis", "23021", "county"),
    "Sagadahoc": _MaineGeography("Sagadahoc", "23023", "county"),
    "Somerset": _MaineGeography("Somerset", "23025", "county"),
    "Waldo": _MaineGeography("Waldo", "23027", "county"),
    "Washington": _MaineGeography("Washington", "23029", "county"),
    "York": _MaineGeography("York", "23031", "county"),
}
_STATE_TOTAL = _MaineGeography("", "", "state_total")
_SUPPORTED_REGIONS = {"State", *_MAINE_COUNTIES}


def _extract_pypdfium_text(path: Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ValueError("pypdfium2 is required to parse Maine JMMC PDFs") from exc

    pdf = pdfium.PdfDocument(path)
    text_parts = []
    for page in pdf:
        text_parts.append(page.get_textpage().get_text_range())
    return "\n".join(text_parts)


def _extract_table_year(text: str) -> int:
    match = re.search(
        r"Rates of selected tick-borne diseases per 100\s*000 persons in Maine,"
        r"\s*(20\d{2})",
        text,
    )
    if not match:
        raise ValueError("Maine JMMC Table 2 report year not found")
    return int(match.group(1))


def _extract_preliminary_as_of(text: str) -> str:
    match = re.search(
        r"Data are preliminary as of ([A-Z][a-z]+ \d{1,2}, 20\d{2}), "
        r"and subject to change",
        text,
    )
    if not match:
        raise ValueError("Maine JMMC preliminary-as-of date not found")
    return datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()


def _extract_table2_text(text: str) -> str:
    start_match = re.search(
        r"Table 2\.\s+Rates of selected tick-borne diseases", text
    )
    if not start_match:
        raise ValueError("Maine JMMC Table 2 heading not found")
    end_match = re.search(
        r"[∗*]Data are preliminary as of [A-Z][a-z]+ \d{1,2}, 20\d{2}, "
        r"and subject to change\.",
        text[start_match.start() :],
    )
    if not end_match:
        raise ValueError("Maine JMMC Table 2 preliminary note not found")
    return text[start_match.start() : start_match.start() + end_match.start()]


def _parse_rate_row(line: str) -> tuple[str, tuple[float, float, float, float, float]] | None:
    normalized = re.sub(r"\s+", " ", line).strip()
    if not normalized:
        return None
    match = re.fullmatch(
        r"([A-Za-z]+(?: [A-Za-z]+)?) "
        r"(\d+\.\d) (\d+\.\d) (\d+\.\d) (\d+\.\d) (\d+\.\d)",
        normalized,
    )
    if not match:
        return None
    region_name = match.group(1)
    if region_name not in _SUPPORTED_REGIONS:
        raise ValueError(f"Unsupported Maine JMMC Table 2 region: {region_name}")
    rates = tuple(float(value) for value in match.groups()[1:])
    return region_name, rates  # type: ignore[return-value]


def _region_geography(region_name: str) -> _MaineGeography:
    if region_name == "State":
        return _STATE_TOTAL
    return _MAINE_COUNTIES[region_name]


def _quality_flags(*, preliminary_as_of: str) -> list[str]:
    preliminary_flag = "preliminary_as_of_" + preliminary_as_of.replace("-", "_")
    return [
        "maine_jmmc_review_article",
        "external_comparator_sidecar",
        "maine_tracking_underlying_source",
        "rates_only_no_case_counts",
        preliminary_flag,
        "reported_rates_not_stable_true_incidence",
        "not_confirmed_case_truth",
        "not_public_default",
        "not_model_input",
    ]


def _validate_complete_region_set(rows: list[MaineJmmcTickborneCountyRate]) -> None:
    found = {row.region_name for row in rows}
    expected = _SUPPORTED_REGIONS
    if found != expected:
        missing = ", ".join(sorted(expected - found)) or "none"
        extra = ", ".join(sorted(found - expected)) or "none"
        raise ValueError(
            "Maine JMMC Table 2 region set incomplete: "
            f"missing={missing}; extra={extra}"
        )
