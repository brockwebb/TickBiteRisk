# Ecology Land-Use Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Acquire and catalog Maryland ecology, habitat, construction, mast, and agricultural source data needed for later host/habitat/contact-pressure feature generation.

**Architecture:** Add a small ecology acquisition layer that follows existing ETL patterns: source registries live in focused modules, raw downloads write to ignored `data/raw/`, normalized CSV outputs write to `build/etl/`, and every row carries source provenance. Census Building Permits gets full parser/output support now because it is small county-year data; NLCD, CDL, and mast reports get reproducible source acquisition and manifesting now, with raster/table feature extraction deferred unless the source offers easy summaries.

**Tech Stack:** Python 3.12 stdlib (`csv`, `dataclasses`, `hashlib`, `urllib.request`, `html.parser`, `pathlib`), Typer CLI, pytest, ruff. No pandas. Raw downloaded files stay ignored by git.

---

## File Structure

- Create `tickbiterisk/etl/ecology_sources.py`
  - Stable source registry for NLCD/MRLC, Census BPS, Maryland DNR mast reports, and USDA CDL.
  - Owns source IDs, URLs, default raw paths, and source-family metadata.
- Create `tickbiterisk/etl/raw_download.py`
  - Small reusable URL downloader and raw manifest writer.
  - Does not know ecology domain semantics.
- Create `tickbiterisk/etl/building_permits.py`
  - Census BPS URL builder, parser, and Maryland row normalization.
- Create `tickbiterisk/etl/building_permits_build.py`
  - CSV writer with append/dedupe semantics for normalized BPS rows.
- Modify `tickbiterisk/cli.py`
  - Add `etl ecology-sources` to download/catalog raw source files.
  - Add `etl building-permits` to normalize Maryland county-year BPS rows.
- Modify docs:
  - `docs/data-manifest.md`
  - `docs/etl-pipeline.md`
  - `README.md`
- Add tests:
  - `tests/test_ecology_sources.py`
  - `tests/test_raw_download.py`
  - `tests/test_building_permits.py`
  - `tests/test_cli_ecology.py`
  - `tests/test_cli_building_permits.py`

---

### Task 1: Ecology Source Registry

**Files:**
- Create: `tickbiterisk/etl/ecology_sources.py`
- Test: `tests/test_ecology_sources.py`

- [ ] **Step 1: Write the failing source registry tests**

Create `tests/test_ecology_sources.py`:

```python
from tickbiterisk.etl.ecology_sources import (
    CENSUS_BPS_COUNTY_INDEX_URL,
    ECOLOGY_SOURCE_FILES,
    MARYLAND_DNR_MAST_REPORT_URLS,
    USDA_MARYLAND_CDL_URL,
    USGS_ANNUAL_NLCD_ACCESS_URL,
    EcologySourceFile,
)


def test_ecology_source_registry_has_primary_source_families() -> None:
    source_ids = {source.source_id for source in ECOLOGY_SOURCE_FILES}

    assert "usgs_annual_nlcd_access" in source_ids
    assert "census_bps_county_index" in source_ids
    assert "usda_nass_maryland_cdl" in source_ids
    assert "maryland_dnr_game_mammals_mast_link" in source_ids


def test_ecology_source_urls_are_official_sources() -> None:
    assert USGS_ANNUAL_NLCD_ACCESS_URL == (
        "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access"
    )
    assert CENSUS_BPS_COUNTY_INDEX_URL == "https://www2.census.gov/econ/bps/County/"
    assert USDA_MARYLAND_CDL_URL == (
        "https://data.nass.usda.gov/Statistics_by_State/Maryland/"
        "Publications/Cropland_Data_Layer/index.php"
    )


def test_mast_report_registry_includes_known_official_reports() -> None:
    assert [source.year for source in MARYLAND_DNR_MAST_REPORT_URLS] == [
        2017,
        2020,
        2021,
    ]
    assert all("dnr.maryland.gov" in source.url for source in MARYLAND_DNR_MAST_REPORT_URLS)


def test_source_default_paths_live_under_ignored_raw_data() -> None:
    source = EcologySourceFile(
        source_id="example",
        family="example",
        url="https://example.test/file.csv",
        raw_relative_path="example/file.csv",
        description="Example source",
        expected_format="csv",
    )

    assert str(source.raw_path()).endswith("data/raw/ecology/example/file.csv")
```

- [ ] **Step 2: Run the source registry tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_ecology_sources.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.ecology_sources'`.

- [ ] **Step 3: Implement the source registry**

Create `tickbiterisk/etl/ecology_sources.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ECOLOGY_RAW_DIR = Path("data/raw/ecology")

USGS_ANNUAL_NLCD_ACCESS_URL = (
    "https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access"
)
USGS_ANNUAL_NLCD_OVERVIEW_URL = "https://www.usgs.gov/annualNLCD"
MRLC_DATA_SERVICES_URL = "https://www.mrlc.gov/data-services-page"
CENSUS_BPS_PAGE_URL = "https://www.census.gov/construction/bps/index.html"
CENSUS_BPS_COUNTY_INDEX_URL = "https://www2.census.gov/econ/bps/County/"
CENSUS_BPS_DOCUMENTATION_URL = "https://www2.census.gov/econ/bps/Documentation/"
USDA_MARYLAND_CDL_URL = (
    "https://data.nass.usda.gov/Statistics_by_State/Maryland/"
    "Publications/Cropland_Data_Layer/index.php"
)
USDA_CROPSCAPE_URL = "https://www.nass.usda.gov/Research_and_Science/Cropland/Viewer/"
MARYLAND_DNR_GAME_MAMMALS_URL = (
    "https://dnr.maryland.gov/wildlife/Pages/hunt_trap/GameMammals.aspx"
)


@dataclass(frozen=True)
class EcologySourceFile:
    source_id: str
    family: str
    url: str
    raw_relative_path: str
    description: str
    expected_format: str

    def raw_path(self, raw_dir: Path = ECOLOGY_RAW_DIR) -> Path:
        return raw_dir / self.raw_relative_path


@dataclass(frozen=True)
class MarylandDnrMastReportSource:
    year: int
    url: str

    @property
    def source_id(self) -> str:
        return f"maryland_dnr_wmd_mast_survey_{self.year}"

    @property
    def raw_relative_path(self) -> str:
        return f"mast/maryland_dnr_wmd_mast_survey_{self.year}.pdf"

    def as_source_file(self) -> EcologySourceFile:
        return EcologySourceFile(
            source_id=self.source_id,
            family="mast",
            url=self.url,
            raw_relative_path=self.raw_relative_path,
            description=f"Maryland DNR Western Maryland mast survey summary {self.year}",
            expected_format="pdf",
        )


MARYLAND_DNR_MAST_REPORT_URLS = [
    MarylandDnrMastReportSource(
        year=2017,
        url="https://dnr.maryland.gov/wildlife/Documents/WMD_Mast_Survey.pdf",
    ),
    MarylandDnrMastReportSource(
        year=2020,
        url="https://dnr.maryland.gov/wildlife/documents/2020_wmd_mastsurvey_summary.pdf",
    ),
    MarylandDnrMastReportSource(
        year=2021,
        url="https://dnr.maryland.gov/wildlife/Documents/2021_WMD_MastSurvey_Summary.pdf",
    ),
]


ECOLOGY_SOURCE_FILES = [
    EcologySourceFile(
        source_id="usgs_annual_nlcd_access",
        family="habitat",
        url=USGS_ANNUAL_NLCD_ACCESS_URL,
        raw_relative_path="nlcd/usgs_annual_nlcd_access.html",
        description="USGS Annual NLCD data access page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usgs_annual_nlcd_overview",
        family="habitat",
        url=USGS_ANNUAL_NLCD_OVERVIEW_URL,
        raw_relative_path="nlcd/usgs_annual_nlcd_overview.html",
        description="USGS Annual NLCD overview page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="mrlc_data_services",
        family="habitat",
        url=MRLC_DATA_SERVICES_URL,
        raw_relative_path="nlcd/mrlc_data_services.html",
        description="MRLC data services page for Annual NLCD services",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_page",
        family="construction",
        url=CENSUS_BPS_PAGE_URL,
        raw_relative_path="building_permits/census_bps_page.html",
        description="Census Building Permits Survey landing page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_county_index",
        family="construction",
        url=CENSUS_BPS_COUNTY_INDEX_URL,
        raw_relative_path="building_permits/census_bps_county_index.html",
        description="Census BPS county ASCII file index",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="census_bps_documentation",
        family="construction",
        url=CENSUS_BPS_DOCUMENTATION_URL,
        raw_relative_path="building_permits/census_bps_documentation_index.html",
        description="Census BPS documentation index",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_nass_maryland_cdl",
        family="agriculture",
        url=USDA_MARYLAND_CDL_URL,
        raw_relative_path="cdl/usda_nass_maryland_cdl.html",
        description="USDA NASS Maryland Cropland Data Layer page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="usda_nass_cropscape",
        family="agriculture",
        url=USDA_CROPSCAPE_URL,
        raw_relative_path="cdl/usda_nass_cropscape.html",
        description="USDA NASS CropScape viewer page",
        expected_format="html",
    ),
    EcologySourceFile(
        source_id="maryland_dnr_game_mammals_mast_link",
        family="mast",
        url=MARYLAND_DNR_GAME_MAMMALS_URL,
        raw_relative_path="mast/maryland_dnr_game_mammals.html",
        description="Maryland DNR Game Mammals page linking mast survey reports",
        expected_format="html",
    ),
    *[source.as_source_file() for source in MARYLAND_DNR_MAST_REPORT_URLS],
]
```

- [ ] **Step 4: Run the source registry tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_ecology_sources.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the source registry**

Run:

```bash
git add tickbiterisk/etl/ecology_sources.py tests/test_ecology_sources.py
git commit -m "feat: catalog ecology land use sources"
```

Expected: commit succeeds.

---

### Task 2: Raw Download Manifest Utility

**Files:**
- Create: `tickbiterisk/etl/raw_download.py`
- Test: `tests/test_raw_download.py`

- [ ] **Step 1: Write failing tests for raw downloads and manifests**

Create `tests/test_raw_download.py`:

```python
from pathlib import Path

from tickbiterisk.etl.ecology_sources import EcologySourceFile
from tickbiterisk.etl.raw_download import download_source_files


def test_download_source_files_writes_files_and_manifest(tmp_path) -> None:
    source = EcologySourceFile(
        source_id="example_html",
        family="example",
        url="https://example.test/page",
        raw_relative_path="example/page.html",
        description="Example HTML page",
        expected_format="html",
    )

    def fake_fetch(url: str) -> bytes:
        assert url == "https://example.test/page"
        return b"<html>ok</html>"

    result = download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )

    output_path = tmp_path / "raw" / "example" / "page.html"
    assert output_path.read_bytes() == b"<html>ok</html>"
    assert result.row_count == 1
    assert result.manifest_path == tmp_path / "manifest.csv"
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    assert "example_html" in manifest_text
    assert "sha256" in manifest_text
    assert "bytes" in manifest_text


def test_download_source_files_overwrites_idempotently(tmp_path) -> None:
    source = EcologySourceFile(
        source_id="example_pdf",
        family="example",
        url="https://example.test/file.pdf",
        raw_relative_path="example/file.pdf",
        description="Example PDF",
        expected_format="pdf",
    )
    calls = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        return b"PDF"

    download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )
    download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )

    assert calls == ["https://example.test/file.pdf", "https://example.test/file.pdf"]
    assert (tmp_path / "raw" / "example" / "file.pdf").read_bytes() == b"PDF"
```

- [ ] **Step 2: Run the raw download tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_raw_download.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.raw_download'`.

- [ ] **Step 3: Implement the raw download utility**

Create `tickbiterisk/etl/raw_download.py`:

```python
from __future__ import annotations

import csv
import hashlib
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


def fetch_url_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read()


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
```

- [ ] **Step 4: Run raw download tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_raw_download.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the raw download utility**

Run:

```bash
git add tickbiterisk/etl/raw_download.py tests/test_raw_download.py
git commit -m "feat: add raw ecology source downloader"
```

Expected: commit succeeds.

---

### Task 3: Census Building Permits Parser

**Files:**
- Create: `tickbiterisk/etl/building_permits.py`
- Test: `tests/test_building_permits.py`

- [ ] **Step 1: Write failing BPS parser tests**

Create `tests/test_building_permits.py`:

```python
from tickbiterisk.etl.building_permits import (
    build_census_bps_county_annual_url,
    parse_census_bps_county_text,
)


BPS_SAMPLE = """Survey,FIPS,FIPS,Region,Division,County,,1-unit,,,2-units,,,3-4 units,,,5+ units,,,1-unit rep,,,2-units rep,,,3-4 units rep,,, 5+units rep
Date,State,County,Code,Code,Name,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value
 
202412,24,003,3,5,Anne Arundel County                                      ,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000,1150,1150,412000000,4,8,1800000,3,9,2100000,12,360,85000000
202412,24,005,3,5,Baltimore County                                         ,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000,890,890,301000000,0,0,0,2,8,1200000,8,240,60000000
202412,51,001,3,5,Accomack County                                          ,10,10,1000000,0,0,0,0,0,0,0,0,0,10,10,1000000,0,0,0,0,0,0,0,0,0
"""


def test_build_census_bps_county_annual_url_uses_december_ytd_file() -> None:
    assert build_census_bps_county_annual_url(2024) == (
        "https://www2.census.gov/econ/bps/County/co2412y.txt"
    )


def test_parse_census_bps_county_text_filters_maryland_and_totals_units() -> None:
    rows = parse_census_bps_county_text(
        BPS_SAMPLE,
        source_url="https://www2.census.gov/econ/bps/County/co2412y.txt",
        source_id="census_bps_county_2024",
    )

    assert len(rows) == 2
    anne_arundel = rows[0]
    assert anne_arundel.county_fips == "24003"
    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.year == 2024
    assert anne_arundel.month == 12
    assert anne_arundel.one_unit_units == 1150
    assert anne_arundel.two_unit_units == 8
    assert anne_arundel.three_four_unit_units == 9
    assert anne_arundel.five_plus_unit_units == 360
    assert anne_arundel.total_units_authorized == 1527
    assert anne_arundel.total_value_dollars == 500900000
    assert len(anne_arundel.source_url_hash) == 64
```

- [ ] **Step 2: Run BPS parser tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_building_permits.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.building_permits'`.

- [ ] **Step 3: Implement BPS parser**

Create `tickbiterisk/etl/building_permits.py`:

```python
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from urllib.request import Request, urlopen


CENSUS_BPS_COUNTY_BASE_URL = "https://www2.census.gov/econ/bps/County"
MARYLAND_STATE_FIPS = "24"


@dataclass(frozen=True)
class CensusBuildingPermitCountyYear:
    county_fips: str
    county_name: str
    year: int
    month: int
    one_unit_units: int
    two_unit_units: int
    three_four_unit_units: int
    five_plus_unit_units: int
    total_units_authorized: int
    total_value_dollars: int
    source_id: str
    source_url_hash: str


def build_census_bps_county_annual_url(year: int) -> str:
    if year < 2000 or year > 2025:
        raise ValueError("Census BPS county annual ASCII files are supported for 2000-2025")
    return f"{CENSUS_BPS_COUNTY_BASE_URL}/co{year % 100:02d}12y.txt"


def source_id_from_census_bps_year(year: int) -> str:
    return f"census_bps_county_{year}"


def fetch_census_bps_county_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("latin1")


def parse_census_bps_county_text(
    text: str,
    *,
    source_url: str,
    source_id: str,
) -> list[CensusBuildingPermitCountyYear]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows = []
    for record in csv.reader(text.splitlines()):
        if not record or not record[0].isdigit():
            continue
        if len(record) < 18:
            continue
        state_fips = record[1].zfill(2)
        if state_fips != MARYLAND_STATE_FIPS:
            continue
        survey_date = record[0]
        year = int(survey_date[:4])
        month = int(survey_date[4:6])
        one_unit_units = _parse_int(record[7])
        two_unit_units = _parse_int(record[10])
        three_four_unit_units = _parse_int(record[13])
        five_plus_unit_units = _parse_int(record[16])
        rows.append(
            CensusBuildingPermitCountyYear(
                county_fips=f"{state_fips}{record[2].zfill(3)}",
                county_name=record[5].strip(),
                year=year,
                month=month,
                one_unit_units=one_unit_units,
                two_unit_units=two_unit_units,
                three_four_unit_units=three_four_unit_units,
                five_plus_unit_units=five_plus_unit_units,
                total_units_authorized=(
                    one_unit_units
                    + two_unit_units
                    + three_four_unit_units
                    + five_plus_unit_units
                ),
                total_value_dollars=(
                    _parse_int(record[8])
                    + _parse_int(record[11])
                    + _parse_int(record[14])
                    + _parse_int(record[17])
                ),
                source_id=source_id,
                source_url_hash=source_url_hash,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _parse_int(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return 0
    return int(cleaned)
```

- [ ] **Step 4: Run BPS parser tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_building_permits.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit BPS parser**

Run:

```bash
git add tickbiterisk/etl/building_permits.py tests/test_building_permits.py
git commit -m "feat: parse Census building permits county files"
```

Expected: commit succeeds.

---

### Task 4: Building Permits CSV Writer

**Files:**
- Create: `tickbiterisk/etl/building_permits_build.py`
- Modify: `tests/test_building_permits.py`

- [ ] **Step 1: Add failing writer test**

Append to `tests/test_building_permits.py`:

```python
from dataclasses import replace

from tickbiterisk.etl.building_permits_build import write_building_permits_output


def test_write_building_permits_output_appends_and_dedupes(tmp_path) -> None:
    row = parse_census_bps_county_text(
        BPS_SAMPLE,
        source_url="https://www2.census.gov/econ/bps/County/co2412y.txt",
        source_id="census_bps_county_2024",
    )[0]
    replacement = replace(row, total_units_authorized=1600)

    write_building_permits_output([row], tmp_path)
    output = write_building_permits_output([replacement], tmp_path, append=True)

    text = output.read_text(encoding="utf-8")
    assert output.name == "maryland_building_permits_county_year.csv"
    assert "county_fips,county_name,year,month" in text
    assert text.count("24003") == 1
    assert "1600" in text
```

- [ ] **Step 2: Run the writer test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_building_permits.py::test_write_building_permits_output_appends_and_dedupes -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk.etl.building_permits_build'`.

- [ ] **Step 3: Implement BPS writer**

Create `tickbiterisk/etl/building_permits_build.py`:

```python
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.building_permits import CensusBuildingPermitCountyYear


BUILDING_PERMIT_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "month",
    "one_unit_units",
    "two_unit_units",
    "three_four_unit_units",
    "five_plus_unit_units",
    "total_units_authorized",
    "total_value_dollars",
    "source_id",
    "source_url_hash",
]


def write_building_permits_output(
    rows: list[CensusBuildingPermitCountyYear],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "maryland_building_permits_county_year.csv"
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record): record for record in records}
    ordered = sorted(
        keyed.values(),
        key=lambda record: (record["county_fips"], int(record["year"])),
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BUILDING_PERMIT_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: CensusBuildingPermitCountyYear) -> dict[str, object]:
    record = asdict(row)
    record["county_fips"] = str(record["county_fips"]).zfill(5)
    return record


def _read_existing_records(output_path: Path) -> list[dict[str, str]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                **record,
                "county_fips": str(record["county_fips"]).zfill(5),
            }
            for record in reader
        ]


def _record_key(record: dict[str, object]) -> tuple[str, int]:
    return (str(record["county_fips"]).zfill(5), int(record["year"]))
```

- [ ] **Step 4: Run BPS tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_building_permits.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit BPS writer**

Run:

```bash
git add tickbiterisk/etl/building_permits_build.py tests/test_building_permits.py
git commit -m "feat: write building permits county output"
```

Expected: commit succeeds.

---

### Task 5: Ecology And Building Permits CLI Commands

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_ecology.py`
- Test: `tests/test_cli_building_permits.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_ecology.py`:

```python
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.ecology_sources import EcologySourceFile


runner = CliRunner()


def test_ecology_sources_command_writes_raw_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.ECOLOGY_SOURCE_FILES",
        [
            EcologySourceFile(
                source_id="example",
                family="example",
                url="https://example.test/page",
                raw_relative_path="example/page.html",
                description="Example page",
                expected_format="html",
            )
        ],
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.download_source_files",
        lambda sources, raw_dir, manifest_path: type(
            "Result",
            (),
            {"row_count": 1, "manifest_path": manifest_path},
        )(),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "ecology-sources",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--manifest-path",
            str(tmp_path / "manifest.csv"),
        ],
    )

    assert result.exit_code == 0
    assert "Downloaded/catalogued 1 ecology source file(s)" in result.stdout
```

Create `tests/test_cli_building_permits.py`:

```python
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tests.test_building_permits import BPS_SAMPLE


runner = CliRunner()


def test_building_permits_command_writes_county_year_output(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_census_bps_county_text",
        lambda url: BPS_SAMPLE,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "building-permits",
            "--start-year",
            "2024",
            "--end-year",
            "2024",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 building permit row(s)" in result.stdout
    assert (tmp_path / "maryland_building_permits_county_year.csv").exists()
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_ecology.py tests/test_cli_building_permits.py -q
```

Expected: FAIL because the CLI commands and imports do not exist.

- [ ] **Step 3: Wire CLI imports and commands**

Modify `tickbiterisk/cli.py` imports:

```python
from tickbiterisk.etl.building_permits import (
    build_census_bps_county_annual_url,
    fetch_census_bps_county_text,
    parse_census_bps_county_text,
    source_id_from_census_bps_year,
)
from tickbiterisk.etl.building_permits_build import write_building_permits_output
from tickbiterisk.etl.ecology_sources import ECOLOGY_RAW_DIR, ECOLOGY_SOURCE_FILES
from tickbiterisk.etl.raw_download import download_source_files
```

Add these commands after `county_reference` or near other ETL commands:

```python
@etl_app.command("ecology-sources")
def ecology_sources(
    raw_dir: Path = typer.Option(
        ECOLOGY_RAW_DIR,
        help="Ignored raw-data directory for ecology source files.",
    ),
    manifest_path: Path = typer.Option(
        Path("build/etl/ecology/source_manifest.csv"),
        help="Output CSV manifest for downloaded ecology source files.",
    ),
) -> None:
    result = download_source_files(
        ECOLOGY_SOURCE_FILES,
        raw_dir=raw_dir,
        manifest_path=manifest_path,
    )
    typer.echo(
        f"Downloaded/catalogued {result.row_count} ecology source file(s) "
        f"to {result.manifest_path}"
    )


@etl_app.command("building-permits")
def building_permits(
    start_year: int = typer.Option(2000, help="First BPS annual county file year."),
    end_year: int = typer.Option(2025, help="Last BPS annual county file year."),
    output_dir: Path = typer.Option(
        Path("build/etl/building-permits"),
        help="Output directory for building permit ETL artifacts.",
    ),
) -> None:
    if start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")
    rows = []
    for year in range(start_year, end_year + 1):
        source_url = build_census_bps_county_annual_url(year)
        text = fetch_census_bps_county_text(source_url)
        rows.extend(
            parse_census_bps_county_text(
                text,
                source_url=source_url,
                source_id=source_id_from_census_bps_year(year),
            )
        )
    output = write_building_permits_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} building permit row(s) to {output}")
```

- [ ] **Step 4: Run CLI tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_ecology.py tests/test_cli_building_permits.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused ETL test suite**

Run:

```bash
.venv/bin/python -m pytest tests/test_ecology_sources.py tests/test_raw_download.py tests/test_building_permits.py tests/test_cli_ecology.py tests/test_cli_building_permits.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit CLI commands**

Run:

```bash
git add tickbiterisk/cli.py tests/test_cli_ecology.py tests/test_cli_building_permits.py
git commit -m "feat: add ecology acquisition CLI commands"
```

Expected: commit succeeds.

---

### Task 6: Live Acquisition Smoke Runs

**Files:**
- No code files expected.
- Generated ignored files under `data/raw/ecology/` and `build/etl/`.

- [ ] **Step 1: Run raw ecology source acquisition**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl ecology-sources \
  --raw-dir data/raw/ecology \
  --manifest-path build/etl/ecology/source_manifest.csv
```

Expected: command exits 0 and prints `Downloaded/catalogued 12 ecology source file(s)` or the current count from `ECOLOGY_SOURCE_FILES`.

- [ ] **Step 2: Verify raw source files are ignored by git**

Run:

```bash
git status --short --ignored data/raw/ecology build/etl/ecology | sed -n '1,80p'
```

Expected: raw files appear under ignored paths with `!! data/raw/`; generated `build/etl/ecology/source_manifest.csv` is also ignored through `build/`.

- [ ] **Step 3: Run a one-year BPS live smoke**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl building-permits \
  --start-year 2024 \
  --end-year 2024 \
  --output-dir build/etl/building-permits-smoke
```

Expected: command exits 0 and writes 24 Maryland rows for 2024 to `build/etl/building-permits-smoke/maryland_building_permits_county_year.csv`.

- [ ] **Step 4: Inspect the live BPS smoke output**

Run:

```bash
.venv/bin/python - <<'PY'
import csv
path = "build/etl/building-permits-smoke/maryland_building_permits_county_year.csv"
with open(path, newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
print(len(rows))
print(rows[0]["county_fips"], rows[0]["year"], rows[0]["total_units_authorized"])
print(rows[-1]["county_fips"], rows[-1]["year"], rows[-1]["total_units_authorized"])
PY
```

Expected:

```text
24
24001 2024 <integer>
24510 2024 <integer>
```

- [ ] **Step 5: Run the full practical BPS range**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl building-permits \
  --start-year 2000 \
  --end-year 2025 \
  --output-dir build/etl/building-permits
```

Expected: command exits 0 and writes up to 624 rows: 24 Maryland jurisdictions times 26 years. If a historical BPS county file omits Baltimore City or another independent city, record the observed row count in the docs update task instead of fabricating a row.

---

### Task 7: Documentation And Manifest Updates

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `docs/software-requirements-spec.md` only if implementation changes the accepted source scope.

- [ ] **Step 1: Update README command list**

Add these commands to the Maryland ETL command block in `README.md`:

```bash
tickbiterisk etl ecology-sources --raw-dir data/raw/ecology --manifest-path build/etl/ecology/source_manifest.csv
tickbiterisk etl building-permits --start-year 2000 --end-year 2025 --output-dir build/etl/building-permits
```

- [ ] **Step 2: Add a concise README status sentence**

In the paragraph below the command block, add:

```markdown
Ecology source acquisition downloads official Annual NLCD/MRLC, Census BPS, Maryland DNR mast, and USDA CDL source pages/files into ignored raw storage and writes a source manifest. Census BPS county annual files are normalized for Maryland county-year construction pressure starting with the practical 2000-2025 range available in the public county ASCII index.
```

- [ ] **Step 3: Update `docs/data-manifest.md` source statuses**

Replace the existing `nlcd_habitat`, `maryland_dnr_mast_survey`, and add a BPS row with:

```markdown
| `annual_nlcd_mrlc` | USGS Annual NLCD / MRLC | `https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access` plus MRLC data services | HTML/catalog now; raster/service extraction later | CONUS/Maryland county summaries targeted | 1985-2024 source coverage | Habitat, impervious, land-cover change | acquired, source_manifested, feature_extraction_pending | Public federal data | Raw source pages downloaded by `tickbiterisk etl ecology-sources`; county feature extraction waits on official summary/service decision |
| `census_bps_county` | Census Building Permits Survey county ASCII files | `https://www2.census.gov/econ/bps/County/coYY12y.txt` | TXT/CSV-like ASCII | County | 2000-2025 practical county annual files | Construction/contact pressure proxy | acquired, etl_supported | Public federal data | `tickbiterisk etl building-permits` writes Maryland county-year units authorized and valuation fields; pre-2000 county coverage remains unresolved |
| `maryland_dnr_mast_survey` | Maryland DNR Western Maryland mast/acorn survey reports | Maryland DNR Game Mammals page plus known PDF reports | PDF/HTML | Western Maryland study plots/counties | 2017, 2020, 2021 known report PDFs acquired | Host/reservoir ecology context | acquired, source_manifested, parser_pending | Public state data likely | Localized public-land plot reports; do not generalize statewide without quality flags |
```

- [ ] **Step 4: Update `docs/etl-pipeline.md`**

Add sections:

```markdown
### 2.10 Ecology Source Acquisition (`tickbiterisk etl ecology-sources`)

* Downloads official source pages/files for Annual NLCD/MRLC, Census BPS, Maryland DNR mast reports, and USDA CDL.
* Writes raw files under ignored `data/raw/ecology`.
* Writes `source_manifest.csv` with source ID, URL, local path, byte count, SHA-256, and ingestion timestamp.
* Does not process full raster data in this slice.

### 2.11 Census Building Permits (`tickbiterisk etl building-permits`)

* Downloads December year-to-date county ASCII files from the Census BPS county index.
* Filters Maryland jurisdictions and computes total residential units authorized from 1-unit, 2-unit, 3-4 unit, and 5+ unit columns.
* Writes `maryland_building_permits_county_year.csv`; warehouse target is `contact_pressure_features` or a future raw staging table.
* Treats construction as a contact/land-use pressure proxy, not direct evidence of tick or deer migration.
```

- [ ] **Step 5: Run docs/source tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ecology_sources.py tests/test_raw_download.py tests/test_building_permits.py tests/test_cli_ecology.py tests/test_cli_building_permits.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit docs and live acquisition status**

Run:

```bash
git add README.md docs/data-manifest.md docs/etl-pipeline.md
git commit -m "docs: catalog ecology acquisition outputs"
```

Expected: commit succeeds.

---

### Task 8: Final Verification

**Files:**
- No additional changes expected unless verification reveals a defect.

- [ ] **Step 1: Run lint**

Run:

```bash
.venv/bin/python -m ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 2: Run full tests**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Check working tree**

Run:

```bash
git status --short
```

Expected: only known untracked local files remain, such as `.DS_Store`, `AGENTS.md`, `api/.DS_Store`, and `review/`. No tracked files should be modified.

- [ ] **Step 4: Record unresolved source decisions in final response**

Final response must include:

```text
Implemented ecology source acquisition and Census BPS county-year ETL.
Annual NLCD/MRLC and USDA CDL are acquired/catalogued but not raster-processed yet.
Mast reports are downloaded/catalogued but not structured into model features yet.
Census BPS normalized output covers the practical county ASCII range 2000-2025; 1992-1999 county-level BPS remains unresolved.
```

---

## Plan Self-Review

- Spec coverage:
  - Annual NLCD/MRLC acquisition is covered by source registry, raw download, and manifest docs.
  - Census BPS acquisition and parser support are covered by parser, writer, CLI, live smoke, and docs tasks.
  - Maryland mast reports are covered by source registry/raw download and documented as parser-pending.
  - USDA CDL is covered by source registry/raw download and documented as enrichment/source-manifested.
  - Construction spillover is not modeled in this plan, matching the non-goal in the design.
- Placeholder scan:
  - No `TBD`, `TODO`, or "similar to previous" instructions remain.
  - Deferred work is named explicitly as parser-pending or raster-processing-pending with concrete boundaries.
- Type consistency:
  - `EcologySourceFile`, `RawDownloadResult`, and `CensusBuildingPermitCountyYear` are defined before use.
  - CLI command names match test invocations: `ecology-sources` and `building-permits`.
  - Output filenames match writer tests and documentation.
