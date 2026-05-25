from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from tickbiterisk.etl.county_reference import CountyReference
from tickbiterisk.etl.maryland import MarylandJurisdiction, load_maryland_jurisdictions


MARYLAND_DNR_DEER_HARVEST_URLS = [
    "https://news.maryland.gov/dnr/2021/02/16/"
    "maryland-hunters-harvest-81000-deer-during-2020-2021-season/",
    "https://news.maryland.gov/dnr/2022/02/10/"
    "maryland-hunters-report-taking-70845-deer-in-2021-2022-season/",
    "https://news.maryland.gov/dnr/2023/02/16/"
    "maryland-hunters-harvest-76687-deer-for-2022-2023-season/",
    "https://news.maryland.gov/dnr/2024/02/13/"
    "maryland-hunters-harvest-72642-deer-for-2023-2024-season/",
    "https://news.maryland.gov/dnr/2025/02/14/"
    "maryland-hunters-harvest-84201-deer-for-2024-2025-season/",
    "https://news.maryland.gov/dnr/2026/02/12/"
    "maryland-hunters-harvest-71649-deer-for-2025-2026-season/",
]


@dataclass(frozen=True)
class MarylandDeerHarvest:
    county_fips: str
    county_name: str
    season_start_year: int
    season_label: str
    species: str
    antlered_harvest: int
    antlerless_harvest: int
    total_harvest: int
    land_area_sqmi: float | None
    harvest_per_sqmi: float | None
    is_derived_total: bool
    source_id: str
    source_url_hash: str


def fetch_maryland_dnr_deer_harvest_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def source_id_from_deer_harvest_url(url: str) -> str:
    match = re.search(r"/(20\d{2})/", url)
    if match:
        return f"md_dnr_deer_harvest_{match.group(1)}"
    return "md_dnr_deer_harvest"


def parse_maryland_dnr_deer_harvest_html(
    html: str,
    *,
    source_url: str,
    source_id: str,
) -> list[MarylandDeerHarvest]:
    tables = _HarvestTableParser.parse(html)
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    jurisdictions_by_key = _jurisdictions_by_county_key()

    for table in tables:
        header_index = _find_harvest_header_index(table)
        if header_index is None:
            continue
        rows = _parse_harvest_rows(
            table[header_index:],
            jurisdictions_by_key=jurisdictions_by_key,
            source_id=source_id,
            source_url_hash=source_url_hash,
        )
        return _with_derived_all_deer_totals(rows)

    raise ValueError("Maryland DNR deer harvest table was not found")


def attach_deer_harvest_density(
    rows: list[MarylandDeerHarvest],
    county_references: list[CountyReference],
) -> list[MarylandDeerHarvest]:
    land_area_by_fips = {
        row.county_fips: row.aland_sqmi
        for row in county_references
        if row.aland_sqmi is not None and row.aland_sqmi > 0
    }
    with_density = []
    for row in rows:
        land_area_sqmi = land_area_by_fips.get(row.county_fips)
        if land_area_sqmi is None:
            with_density.append(row)
            continue
        with_density.append(
            replace(
                row,
                land_area_sqmi=land_area_sqmi,
                harvest_per_sqmi=round(row.total_harvest / land_area_sqmi, 6),
            )
        )
    return sorted(with_density, key=_deer_harvest_sort_key)


class _HarvestTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell_parts: list[str] | None = None

    @classmethod
    def parse(cls, html: str) -> list[list[list[str]]]:
        parser = cls()
        parser.feed(html)
        return parser.tables

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "table":
            if self._table_depth == 0:
                self._current_table = []
            self._table_depth += 1
            return
        if self._table_depth == 0:
            return
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"}:
            self._current_cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_cell_parts is not None:
            self._current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table_depth == 0:
            return
        if tag in {"td", "th"} and self._current_cell_parts is not None:
            if self._current_row is not None:
                self._current_row.append(_normalize_cell("".join(self._current_cell_parts)))
            self._current_cell_parts = None
        elif tag == "tr":
            if (
                self._current_table is not None
                and self._current_row is not None
                and any(cell for cell in self._current_row)
            ):
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table":
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None


def _find_harvest_header_index(table: list[list[str]]) -> int | None:
    title_index = None
    for index, row in enumerate(table):
        if any(
            "Maryland Reported Antlered and Antlerless Deer Harvest" in cell
            for cell in row
        ):
            title_index = index
            break
    if title_index is None:
        return None

    for index in range(title_index + 1, len(table)):
        if table[index] and table[index][0].lower() == "county":
            return index
    return None


def _parse_harvest_rows(
    table_rows: list[list[str]],
    *,
    jurisdictions_by_key: dict[str, MarylandJurisdiction],
    source_id: str,
    source_url_hash: str,
) -> list[MarylandDeerHarvest]:
    if not table_rows:
        return []
    header = table_rows[0]
    if len(header) < 9:
        raise ValueError("Maryland DNR deer harvest header has too few columns")

    rows: list[MarylandDeerHarvest] = []
    current_county: MarylandJurisdiction | None = None
    for cells in table_rows[1:]:
        if not cells:
            continue
        label = _normalize_cell(cells[0])
        if not label or label.lower().startswith("total") or label.startswith("*"):
            continue

        jurisdiction = jurisdictions_by_key.get(_county_key(label))
        if jurisdiction is not None:
            current_county = jurisdiction
            if _has_harvest_values(cells):
                rows.extend(
                    _row_to_harvest_records(
                        cells,
                        header=header,
                        jurisdiction=jurisdiction,
                        species="all_deer",
                        is_derived_total=False,
                        source_id=source_id,
                        source_url_hash=source_url_hash,
                    )
                )
            continue

        species = _species_from_label(label)
        if species is not None and current_county is not None:
            rows.extend(
                _row_to_harvest_records(
                    cells,
                    header=header,
                    jurisdiction=current_county,
                    species=species,
                    is_derived_total=False,
                    source_id=source_id,
                    source_url_hash=source_url_hash,
                )
            )

    return sorted(rows, key=_deer_harvest_sort_key)


def _row_to_harvest_records(
    cells: list[str],
    *,
    header: list[str],
    jurisdiction: MarylandJurisdiction,
    species: str,
    is_derived_total: bool,
    source_id: str,
    source_url_hash: str,
) -> list[MarylandDeerHarvest]:
    records = []
    for season_index in (1, 2):
        season_label = header[season_index]
        antlered = _parse_harvest_int(_cell_at(cells, season_index))
        antlerless = _parse_harvest_int(_cell_at(cells, season_index + 3))
        total = _parse_harvest_int(_cell_at(cells, season_index + 6))
        if antlered is None or antlerless is None or total is None:
            continue
        records.append(
            MarylandDeerHarvest(
                county_fips=jurisdiction.county_fips,
                county_name=jurisdiction.county_name,
                season_start_year=_season_start_year(season_label),
                season_label=season_label,
                species=species,
                antlered_harvest=antlered,
                antlerless_harvest=antlerless,
                total_harvest=total,
                land_area_sqmi=None,
                harvest_per_sqmi=None,
                is_derived_total=is_derived_total,
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
        )
    return records


def _with_derived_all_deer_totals(
    rows: list[MarylandDeerHarvest],
) -> list[MarylandDeerHarvest]:
    existing_all_deer = {
        (row.county_fips, row.season_start_year, row.source_id)
        for row in rows
        if row.species == "all_deer"
    }
    species_groups: dict[
        tuple[str, str, int, str, str, str], list[MarylandDeerHarvest]
    ] = {}
    for row in rows:
        if row.species == "all_deer":
            continue
        key = (
            row.county_fips,
            row.county_name,
            row.season_start_year,
            row.season_label,
            row.source_id,
            row.source_url_hash,
        )
        species_groups.setdefault(key, []).append(row)

    derived_rows = []
    for (
        county_fips,
        county_name,
        season_start_year,
        season_label,
        source_id,
        source_url_hash,
    ), members in species_groups.items():
        if (county_fips, season_start_year, source_id) in existing_all_deer:
            continue
        derived_rows.append(
            MarylandDeerHarvest(
                county_fips=county_fips,
                county_name=county_name,
                season_start_year=season_start_year,
                season_label=season_label,
                species="all_deer",
                antlered_harvest=sum(row.antlered_harvest for row in members),
                antlerless_harvest=sum(row.antlerless_harvest for row in members),
                total_harvest=sum(row.total_harvest for row in members),
                land_area_sqmi=None,
                harvest_per_sqmi=None,
                is_derived_total=True,
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
        )

    return sorted([*rows, *derived_rows], key=_deer_harvest_sort_key)


def _jurisdictions_by_county_key() -> dict[str, MarylandJurisdiction]:
    jurisdictions = load_maryland_jurisdictions()
    keyed = {}
    for jurisdiction in jurisdictions:
        keyed[_county_key(jurisdiction.county_name)] = jurisdiction
        keyed[_county_key(jurisdiction.county_name.removesuffix(" County"))] = (
            jurisdiction
        )
    return keyed


def _county_key(value: str) -> str:
    normalized = _normalize_cell(value).lower()
    normalized = normalized.replace(".", "")
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"\bcounty\b", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _species_from_label(label: str) -> str | None:
    key = _normalize_cell(label).lower().replace("-", " ")
    if key in {"whitetail", "white tail", "white tailed", "white tailed deer"}:
        return "white_tailed_deer"
    if key in {"sika", "sika deer"}:
        return "sika_deer"
    return None


def _normalize_cell(value: str) -> str:
    normalized = value.replace("\xa0", " ")
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", normalized).strip()


def _has_harvest_values(cells: list[str]) -> bool:
    return any(
        _parse_harvest_int(_cell_at(cells, index)) is not None
        for index in (1, 2, 4, 5, 7, 8)
    )


def _parse_harvest_int(value: str) -> int | None:
    cleaned = _normalize_cell(value).replace(",", "")
    if not cleaned or cleaned in {"-", "*"}:
        return None
    if not re.fullmatch(r"\d+", cleaned):
        return None
    return int(cleaned)


def _cell_at(cells: list[str], index: int) -> str:
    if index >= len(cells):
        return ""
    return cells[index]


def _season_start_year(season_label: str) -> int:
    first_part = season_label.split("-", maxsplit=1)[0]
    if len(first_part) == 2:
        return 2000 + int(first_part)
    return int(first_part)


def _deer_harvest_sort_key(row: MarylandDeerHarvest) -> tuple[str, int, int, str]:
    species_order = {
        "all_deer": 0,
        "white_tailed_deer": 1,
        "sika_deer": 2,
    }
    return (
        row.county_fips,
        row.season_start_year,
        species_order.get(row.species, 99),
        row.species,
    )
