from __future__ import annotations

import hashlib
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from pathlib import Path
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

MARYLAND_DNR_DEER_ANNUAL_REPORT_ARCHIVE_URL = (
    "https://dnr.maryland.gov/wildlife/Pages/hunt_trap/Deer_AnnualReports.aspx"
)


@dataclass(frozen=True)
class MarylandDnrDeerAnnualReportSource:
    season_start_year: int
    season_label: str
    url: str

    @property
    def source_id(self) -> str:
        return (
            "md_dnr_deer_annual_report_"
            f"{self.season_start_year}_{self.season_start_year + 1}"
        )


MARYLAND_DNR_DEER_ANNUAL_REPORT_OCR_PENDING_URLS = [
    MarylandDnrDeerAnnualReportSource(
        2007,
        "2007-08",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report07-08.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2008,
        "2008-09",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report08-09.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2009,
        "2009-10",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report09-10.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2010,
        "2010-11",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report10-11.pdf",
    ),
]


MARYLAND_DNR_DEER_ANNUAL_REPORT_URLS = [
    MarylandDnrDeerAnnualReportSource(
        2011,
        "2011-12",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report11-12.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2012,
        "2012-13",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report12-13.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2013,
        "2013-14",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report13-14.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2014,
        "2014-15",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report14-15.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2015,
        "2015-16",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report15-16.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2016,
        "2016-17",
        "https://dnr.maryland.gov/wildlife/Documents/md_annual_deer_report16-17.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2017,
        "2017-18",
        "https://dnr.maryland.gov/wildlife/Documents/MD-Annual-Deer-Report-2017-2018.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2018,
        "2018-19",
        "https://dnr.maryland.gov/wildlife/Documents/MD-Annual-Deer-Report-2018-2019.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2019,
        "2019-20",
        "https://dnr.maryland.gov/wildlife/Documents/MD-Annual-Deer-Report-2019-2020.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2020,
        "2020-21",
        "https://dnr.maryland.gov/wildlife/Documents/Maryland-Annual-Deer-Report-2020-2021.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2021,
        "2021-22",
        "https://dnr.maryland.gov/wildlife/Documents/Maryland-Big-Game-Report-2021-22.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2022,
        "2022-23",
        "https://dnr.maryland.gov/wildlife/Documents/Maryland-Big-Game-Report-2022-2023.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2023,
        "2023-24",
        "https://dnr.maryland.gov/wildlife/Documents/maryland-Big-Game-Report_2023-24.pdf",
    ),
    MarylandDnrDeerAnnualReportSource(
        2024,
        "2024-25",
        "https://dnr.maryland.gov/wildlife/Documents/maryland-Big-Game-Report_2024-25.pdf",
    ),
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


def parse_maryland_dnr_deer_harvest_text(
    text: str,
    *,
    source_url: str,
    source_id: str,
) -> list[MarylandDeerHarvest]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    season_label = _season_label_from_annual_report_text(text)
    jurisdictions_by_key = _jurisdictions_by_county_key()
    raw_rows = _parse_annual_report_total_table(
        _annual_report_rows_from_text(text),
        season_label=season_label,
        jurisdictions_by_key=jurisdictions_by_key,
        source_id=source_id,
        source_url_hash=source_url_hash,
    )
    if raw_rows:
        return _with_derived_all_deer_totals(raw_rows)

    tables = _markdown_tables(text)
    for table in tables:
        rows = _parse_annual_report_total_table(
            table,
            season_label=season_label,
            jurisdictions_by_key=jurisdictions_by_key,
            source_id=source_id,
            source_url_hash=source_url_hash,
        )
        if rows:
            return _with_derived_all_deer_totals(rows)
    raise ValueError("Maryland DNR annual report harvest table was not found")


def extract_docling_markdown(
    source: str | Path,
    *,
    converter_factory: Callable[[], object] | None = None,
) -> str:
    if converter_factory is None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Docling is required for PDF deer harvest extraction. "
                "Install the development dependencies with docling enabled."
            ) from exc
        converter_factory = DocumentConverter
    converter = converter_factory()
    result = converter.convert(source)
    return result.document.export_to_markdown()


def extract_pypdfium_text(source: str | Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "pypdfium2 is required for lightweight PDF deer harvest extraction."
        ) from exc

    source_value = str(source)
    temp_path: Path | None = None
    if source_value.startswith(("http://", "https://")):
        request = Request(source_value, headers={"User-Agent": "tickbiterisk-etl/0.1"})
        with urlopen(request, timeout=60) as response:
            pdf_bytes = response.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(pdf_bytes)
            temp_path = Path(handle.name)
        pdf_source = str(temp_path)
    else:
        pdf_source = source_value

    try:
        document = pdfium.PdfDocument(pdf_source)
        pages = []
        for page_index in range(len(document)):
            page = document[page_index]
            pages.append(page.get_textpage().get_text_range())
        return "\n".join(pages)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def parse_maryland_dnr_deer_harvest_pdf(
    source: str | Path,
    *,
    source_url: str,
    source_id: str,
    parser: str = "pypdfium",
    text_extractor: Callable[[str | Path], str] = extract_pypdfium_text,
    converter_factory: Callable[[], object] | None = None,
) -> list[MarylandDeerHarvest]:
    if parser not in {"pypdfium", "docling"}:
        raise ValueError("PDF parser must be 'pypdfium' or 'docling'")
    if parser == "docling" or converter_factory is not None:
        markdown = extract_docling_markdown(
            source,
            converter_factory=converter_factory,
        )
    else:
        markdown = text_extractor(source)
    return parse_maryland_dnr_deer_harvest_text(
        markdown,
        source_url=source_url,
        source_id=source_id,
    )


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


def _parse_annual_report_total_table(
    table: list[list[str]],
    *,
    season_label: str,
    jurisdictions_by_key: dict[str, MarylandJurisdiction],
    source_id: str,
    source_url_hash: str,
) -> list[MarylandDeerHarvest]:
    rows: list[MarylandDeerHarvest] = []
    current_county: MarylandJurisdiction | None = None
    for cells in table:
        if not cells:
            continue
        label = _normalize_cell(cells[0])
        if not label or label.lower() == "county" or label.lower().startswith("total"):
            continue
        if label.startswith("---"):
            continue

        jurisdiction = jurisdictions_by_key.get(_county_key(label))
        if jurisdiction is not None:
            current_county = jurisdiction
            harvest_record = _annual_report_row_to_harvest_record(
                cells,
                season_label=season_label,
                jurisdiction=jurisdiction,
                species="all_deer",
                is_derived_total=False,
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
            if harvest_record is not None:
                rows.append(harvest_record)
            continue

        species = _species_from_label(label)
        if species is not None and current_county is not None:
            harvest_record = _annual_report_row_to_harvest_record(
                cells,
                season_label=season_label,
                jurisdiction=current_county,
                species=species,
                is_derived_total=False,
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
            if harvest_record is not None:
                rows.append(harvest_record)

    return sorted(rows, key=_deer_harvest_sort_key)


def _annual_report_row_to_harvest_record(
    cells: list[str],
    *,
    season_label: str,
    jurisdiction: MarylandJurisdiction,
    species: str,
    is_derived_total: bool,
    source_id: str,
    source_url_hash: str,
) -> MarylandDeerHarvest | None:
    numeric_values = [_parse_harvest_int(cell) for cell in cells[1:]]
    numeric_values = [value for value in numeric_values if value is not None]
    if len(numeric_values) < 3:
        return None
    antlered, antlerless, total = numeric_values[-3:]
    return MarylandDeerHarvest(
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


def _markdown_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current_table: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [_normalize_cell(cell) for cell in stripped.strip("|").split("|")]
            current_table.append(cells)
            continue
        if current_table:
            tables.append(current_table)
            current_table = []
    if current_table:
        tables.append(current_table)
    return tables


def _annual_report_rows_from_text(text: str) -> list[list[str]]:
    title_match = re.search(
        r"Maryland Reported Antlered and Antlerless(?: Deer)? Harvest.*?"
        r"Hunting\s+Seasons by County,\s*20\d{2}[-\u2013\u2014]\d{2,4}",
        text,
        flags=re.DOTALL,
    )
    if title_match is not None:
        before_title = text[: title_match.start()]
        allegany_index = before_title.rfind("\nAllegany ")
        if allegany_index != -1:
            before_rows = _annual_report_rows_from_text_block(
                before_title[allegany_index:]
            )
            if before_rows:
                return before_rows

    rows = []
    pending_labels: list[str] = []
    split_label_items: list[tuple[str, bool]] = []
    split_labels_prepared = False
    in_table = False
    for line in text.splitlines():
        line = _normalize_cell(line)
        if not line:
            continue
        if line.startswith("by County,") or "Hunting Seasons by County," in line:
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("Table 2"):
            break
        lower_line = line.lower()
        if lower_line in {"county", "archery firearm muzzleloader total"}:
            continue
        if lower_line.startswith("antlered antlerless"):
            continue
        numeric_only_values = _annual_report_numeric_values_from_line(line)
        if numeric_only_values and pending_labels:
            if not split_labels_prepared:
                split_label_items = _annual_report_split_label_items(pending_labels)
                split_labels_prepared = True
            while split_label_items and not split_label_items[0][1]:
                label, _expects_numeric = split_label_items.pop(0)
                rows.append([label])
            if not split_label_items:
                continue
            label, _expects_numeric = split_label_items.pop(0)
            rows.append([label, *numeric_only_values])
            if label.lower().startswith("total"):
                break
            continue
        label = _annual_report_label_from_text_line(line)
        if label is not None:
            pending_labels.append(label)
            continue
        row = _annual_report_row_from_text_line(line)
        if row is None:
            continue
        if pending_labels:
            rows.extend([label] for label in pending_labels)
            pending_labels = []
            split_label_items = []
            split_labels_prepared = False
        rows.append(row)
        if row[0].lower().startswith("total"):
            break
    return rows


def _annual_report_rows_from_text_block(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = _normalize_cell(line)
        if not line:
            continue
        row = _annual_report_row_from_text_line(line)
        if row is None:
            continue
        rows.append(row)
        if row[0].lower().startswith("total"):
            break
    if rows and rows[-1][0].lower().startswith("total"):
        return rows
    return []


def _annual_report_row_from_text_line(line: str) -> list[str] | None:
    first_digit = re.search(r"\d", line)
    if first_digit is None:
        label = _annual_report_label_from_text_line(line)
        if label is not None:
            return [label]
        return None
    label = _normalize_cell(line[: first_digit.start()])
    values = re.findall(r"\d[\d,]*", line[first_digit.start() :])
    if not label or not values:
        return None
    return [label, *values]


def _annual_report_numeric_values_from_line(line: str) -> list[str]:
    if not re.fullmatch(r"[\d,\s]+", line):
        return []
    return re.findall(r"\d[\d,]*", line)


def _annual_report_split_label_items(labels: list[str]) -> list[tuple[str, bool]]:
    items: list[tuple[str, bool]] = []
    index = 0
    while index < len(labels):
        label = labels[index]
        if label.lower().startswith("total"):
            items.append((label, True))
            index += 1
            continue
        if not _is_annual_report_county_label(label):
            items.append((label, True))
            index += 1
            continue

        species_labels = []
        next_index = index + 1
        while next_index < len(labels) and _species_from_label(labels[next_index]):
            species_labels.append(labels[next_index])
            next_index += 1
        if species_labels:
            items.append((label, False))
            items.extend((species_label, True) for species_label in species_labels)
            index = next_index
            continue

        items.append((label, True))
        index += 1

    return items


def _is_annual_report_county_label(line: str) -> bool:
    return _county_key(line) in _jurisdictions_by_county_key()


def _annual_report_label_from_text_line(line: str) -> str | None:
    if _is_annual_report_county_label(line):
        return line
    if _species_from_label(line) is not None:
        return line
    if line.lower().startswith("total"):
        return line
    return None


def _season_label_from_annual_report_text(text: str) -> str:
    match = re.search(r"by County,\s*(20\d{2})[-\u2013\u2014](\d{2,4})", text)
    if not match:
        match = re.search(r"(20\d{2})[-\u2013\u2014](\d{2,4})", text)
    if not match:
        raise ValueError("Could not determine deer harvest season from annual report")
    start_year = int(match.group(1))
    end_part = match.group(2)
    if len(end_part) == 4:
        end_part = end_part[-2:]
    return f"{start_year}-{end_part}"


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
