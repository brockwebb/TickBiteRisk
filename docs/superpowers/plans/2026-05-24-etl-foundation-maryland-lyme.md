# ETL Foundation And Maryland Lyme Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable ETL slice: validate local source files, normalize Maryland Lyme county-year source values, reconcile canonical Lyme outcomes, normalize tick/vector status layers, and define a Postgres-ready warehouse schema.

**Architecture:** Create a small Python package with pure ETL functions, source metadata models, and a CLI. The first implementation writes deterministic CSV outputs under `build/etl/` and includes SQL schema for Postgres loading; live database loading can be added after the normalized outputs are tested. Keep raw downloaded files outside the repo and reference them through the manifest.

**Tech Stack:** Python 3.12, pandas, openpyxl, pydantic, typer, pytest, SQL DDL for Postgres/PostGIS.

---

## File Structure

Create these implementation files:

- `pyproject.toml`: package metadata, dependencies, pytest config, console script.
- `tickbiterisk/__init__.py`: package version.
- `tickbiterisk/config.py`: constants for default paths.
- `tickbiterisk/cli.py`: Typer CLI entrypoint.
- `tickbiterisk/etl/__init__.py`: ETL package exports.
- `tickbiterisk/etl/sources.py`: source manifest parsing and checksum verification.
- `tickbiterisk/etl/maryland.py`: canonical Maryland jurisdiction reference.
- `tickbiterisk/etl/lyme.py`: CDC/MD Lyme source parsers and source-value normalization.
- `tickbiterisk/etl/reconcile.py`: canonical Lyme county-year reconciliation logic.
- `tickbiterisk/etl/tick_status.py`: Ixodes/pathogen/lone-star workbook parsers.
- `tickbiterisk/etl/build.py`: orchestration functions for local ETL outputs.
- `tickbiterisk/resources/__init__.py`: package marker for importlib resource loading.
- `tickbiterisk/resources/maryland_jurisdictions.csv`: 24 Maryland jurisdictions and FIPS codes.
- `sql/schema.sql`: Postgres-ready warehouse schema.

Create these test files:

- `tests/test_sources.py`
- `tests/test_maryland.py`
- `tests/test_lyme_parsers.py`
- `tests/test_reconcile.py`
- `tests/test_tick_status.py`
- `tests/test_build_outputs.py`

Create these fixture files:

- `tests/fixtures/manifest-mini.md`
- `tests/fixtures/lyme_public_use_2022_2023_mini.csv`
- `tests/fixtures/ld_case_counts_by_county_mini.csv`
- `tests/fixtures/lyme_geodata_mini.csv`

The tick-status XLSX fixtures are created as temporary Excel workbooks inside `tests/test_tick_status.py` so the tests do not need binary fixtures committed to the repo.

Modify these docs:

- `docs/software-requirements-spec.md`: add a brief implementation status note after this slice lands.
- `docs/data-manifest.md`: update source statuses from `needs_etl` to `etl_supported` only after tests pass.

---

### Task 1: Package Skeleton And Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `tickbiterisk/__init__.py`
- Create: `tickbiterisk/config.py`
- Create: `tickbiterisk/etl/__init__.py`
- Create: `tests/test_maryland.py`

- [ ] **Step 1: Write the failing import/version test**

Create `tests/test_maryland.py`:

```python
from tickbiterisk import __version__


def test_package_version_is_exposed() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_maryland.py::test_package_version_is_exposed -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tickbiterisk'`.

- [ ] **Step 3: Create package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tickbiterisk"
version = "0.1.0"
description = "Maryland-first tickborne disease risk data warehouse and model toolkit"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "openpyxl>=3.1",
  "pandas>=2.2",
  "pydantic>=2.7",
  "typer>=0.12",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "ruff>=0.5",
]

[project.scripts]
tickbiterisk = "tickbiterisk.cli:app"

[tool.setuptools.packages.find]
include = ["tickbiterisk*"]

[tool.setuptools.package-data]
tickbiterisk = ["resources/*.csv"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Create minimal package files**

Create `tickbiterisk/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `tickbiterisk/config.py`:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_MANIFEST = PROJECT_ROOT / "docs" / "data-manifest.md"
DEFAULT_BUILD_DIR = PROJECT_ROOT / "build" / "etl"
```

Create `tickbiterisk/etl/__init__.py`:

```python
"""ETL utilities for TickBiteRisk."""
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```bash
pytest tests/test_maryland.py::test_package_version_is_exposed -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add pyproject.toml tickbiterisk tests/test_maryland.py
git commit -m "feat: add ETL package skeleton"
```

---

### Task 2: Maryland Jurisdiction Reference

**Files:**
- Create: `tickbiterisk/resources/__init__.py`
- Create: `tickbiterisk/resources/maryland_jurisdictions.csv`
- Create: `tickbiterisk/etl/maryland.py`
- Modify: `tests/test_maryland.py`

- [ ] **Step 1: Add failing Maryland reference tests**

Append to `tests/test_maryland.py`:

```python
from tickbiterisk.etl.maryland import load_maryland_jurisdictions


def test_maryland_reference_has_24_jurisdictions() -> None:
    jurisdictions = load_maryland_jurisdictions()
    assert len(jurisdictions) == 24
    assert {row.county_fips for row in jurisdictions} >= {"24003", "24510"}


def test_anne_arundel_reference_supports_zip_21146_use_case() -> None:
    jurisdictions = load_maryland_jurisdictions()
    anne_arundel = next(row for row in jurisdictions if row.county_fips == "24003")
    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.state == "MD"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_maryland.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `load_maryland_jurisdictions`.

- [ ] **Step 3: Add the Maryland jurisdiction resource**

Create `tickbiterisk/resources/maryland_jurisdictions.csv`:

```csv
county_fips,state_fips,state,county_name
24001,24,MD,Allegany County
24003,24,MD,Anne Arundel County
24005,24,MD,Baltimore County
24510,24,MD,Baltimore City
24009,24,MD,Calvert County
24011,24,MD,Caroline County
24013,24,MD,Carroll County
24015,24,MD,Cecil County
24017,24,MD,Charles County
24019,24,MD,Dorchester County
24021,24,MD,Frederick County
24023,24,MD,Garrett County
24025,24,MD,Harford County
24027,24,MD,Howard County
24029,24,MD,Kent County
24031,24,MD,Montgomery County
24033,24,MD,Prince George's County
24035,24,MD,Queen Anne's County
24037,24,MD,St. Mary's County
24039,24,MD,Somerset County
24041,24,MD,Talbot County
24043,24,MD,Washington County
24045,24,MD,Wicomico County
24047,24,MD,Worcester County
```

- [ ] **Step 4: Implement Maryland loader**

Create `tickbiterisk/resources/__init__.py`:

```python
"""Package resources for TickBiteRisk."""
```

Create `tickbiterisk/etl/maryland.py`:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class MarylandJurisdiction:
    county_fips: str
    state_fips: str
    state: str
    county_name: str


def load_maryland_jurisdictions() -> list[MarylandJurisdiction]:
    resource = files("tickbiterisk.resources").joinpath("maryland_jurisdictions.csv")
    with resource.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    jurisdictions = [
        MarylandJurisdiction(
            county_fips=str(row["county_fips"]).zfill(5),
            state_fips=str(row["state_fips"]).zfill(2),
            state=row["state"],
            county_name=row["county_name"],
        )
        for row in rows
    ]
    if len(jurisdictions) != 24:
        raise ValueError(f"Expected 24 Maryland jurisdictions, found {len(jurisdictions)}")
    return jurisdictions


def maryland_fips_set() -> set[str]:
    return {row.county_fips for row in load_maryland_jurisdictions()}
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_maryland.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add tickbiterisk/resources/__init__.py tickbiterisk/resources/maryland_jurisdictions.csv tickbiterisk/etl/maryland.py tests/test_maryland.py
git commit -m "feat: add Maryland jurisdiction reference"
```

---

### Task 3: Source Manifest Parser And Checksum Verification

**Files:**
- Create: `tickbiterisk/etl/sources.py`
- Create: `tests/fixtures/manifest-mini.md`
- Create: `tests/test_sources.py`

- [ ] **Step 1: Create fixture manifest**

Create `tests/fixtures/manifest-mini.md`:

```markdown
# Mini Manifest

| ID | Source | Local path / URL | Format | Geography | Time coverage | Role | Status | Redistribution | SHA-256 / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `fixture_csv` | Fixture CSV | `tests/fixtures/lyme_public_use_2022_2023_mini.csv` | CSV | County | 2022 | Outcome | acquired, needs_etl | Test fixture | fixture checksum not used in parser unit test |
| `remote_candidate` | Remote Source | `https://example.test/data.csv` | CSV | County | 2024 | Candidate | candidate, missing | Public | No local file |
```

- [ ] **Step 2: Write failing source tests**

Create `tests/test_sources.py`:

```python
from pathlib import Path

from tickbiterisk.etl.sources import compute_sha256, load_sources_from_markdown


def test_load_sources_from_markdown_table() -> None:
    sources = load_sources_from_markdown(Path("tests/fixtures/manifest-mini.md"))
    assert [source.source_id for source in sources] == ["fixture_csv", "remote_candidate"]
    assert sources[0].format == "CSV"
    assert sources[0].is_local is True
    assert sources[1].is_local is False


def test_compute_sha256_for_local_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("tick risk\n", encoding="utf-8")
    assert compute_sha256(file_path) == "952085cb1f514d1814cab4821b26563f88fa4a65a1a57a240afb7e69a89b2762"
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
pytest tests/test_sources.py -v
```

Expected: FAIL with missing `tickbiterisk.etl.sources`.

- [ ] **Step 4: Implement source parser**

Create `tickbiterisk/etl/sources.py`:

```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


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
        return not self.location.startswith(("http://", "https://"))


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and "`" in value[1:]:
        return value.strip("`")
    return value


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
```

- [ ] **Step 5: Fix expected hash if needed**

Run:

```bash
python - <<'PY'
from pathlib import Path
from tickbiterisk.etl.sources import compute_sha256
p = Path("/tmp/tickrisk-hash-check.txt")
p.write_text("tick risk\n", encoding="utf-8")
print(compute_sha256(p))
PY
```

If the printed hash differs from the test expectation, update only the expected value in `tests/test_sources.py`.

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_sources.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add tickbiterisk/etl/sources.py tests/test_sources.py tests/fixtures/manifest-mini.md
git commit -m "feat: parse data manifest sources"
```

---

### Task 4: CDC Lyme Public-Use Parser

**Files:**
- Create: `tests/fixtures/lyme_public_use_2022_2023_mini.csv`
- Create: `tickbiterisk/etl/lyme.py`
- Create: `tests/test_lyme_parsers.py`

- [ ] **Step 1: Create CDC public-use fixture**

Create `tests/fixtures/lyme_public_use_2022_2023_mini.csv`:

```csv
Year,State,FIPS,Case_status,Sex,Age_cat_yrs,Frequency
2022,MD,24003,Probable,Male,0-19,15
2022,MD,24003,Probable,Male,20+,45
2022,MD,24003,Probable,Female,0-19,10
2022,MD,24003,Probable,Female,20+,57
2022,MD,24005,Probable,Suppressed,Suppressed,278
2022,MD,Suppressed,Probable,Suppressed,Suppressed,8
2022,VA,51013,Probable,Suppressed,Suppressed,99
2023,MD,24003,Probable,Suppressed,Suppressed,131
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_lyme_parsers.py`:

```python
from pathlib import Path

from tickbiterisk.etl.lyme import parse_cdc_lyme_public_use


def test_parse_cdc_lyme_public_use_filters_maryland_counties() -> None:
    rows = parse_cdc_lyme_public_use(
        Path("tests/fixtures/lyme_public_use_2022_2023_mini.csv"),
        source_id="cdc_lyme_public_2022_2023",
    )
    assert {(row.county_fips, row.year) for row in rows} == {
        ("24003", 2022),
        ("24005", 2022),
        ("24003", 2023),
    }


def test_parse_cdc_lyme_public_use_sums_case_statuses() -> None:
    rows = parse_cdc_lyme_public_use(
        Path("tests/fixtures/lyme_public_use_2022_2023_mini.csv"),
        source_id="cdc_lyme_public_2022_2023",
    )
    anne_2022 = next(row for row in rows if row.county_fips == "24003" and row.year == 2022)
    assert anne_2022.confirmed_cases is None
    assert anne_2022.probable_cases == 127
    assert anne_2022.total_cases == 127
    assert anne_2022.source_id == "cdc_lyme_public_2022_2023"
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
pytest tests/test_lyme_parsers.py -v
```

Expected: FAIL with missing `parse_cdc_lyme_public_use`.

- [ ] **Step 4: Implement public-use parser**

Create `tickbiterisk/etl/lyme.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import maryland_fips_set


@dataclass(frozen=True)
class LymeCountyYearValue:
    source_id: str
    county_fips: str
    year: int
    confirmed_cases: int | None
    probable_cases: int | None
    total_cases: int


def _frequency_to_int(value: object) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "N", "U", "Suppressed"}:
        return 0
    return int(float(text))


def parse_cdc_lyme_public_use(path: Path, source_id: str) -> list[LymeCountyYearValue]:
    df = pd.read_csv(path, dtype=str)
    df.columns = [column.strip().lower() for column in df.columns]
    required = {"year", "state", "fips", "case_status", "frequency"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CDC Lyme public-use columns: {sorted(missing)}")

    md_fips = maryland_fips_set()
    df = df[df["state"].eq("MD")].copy()
    df["fips"] = df["fips"].astype(str).str.strip().str.zfill(5)
    df = df[df["fips"].isin(md_fips)].copy()
    df["frequency_int"] = df["frequency"].map(_frequency_to_int)
    grouped = (
        df.groupby(["fips", "year", "case_status"], dropna=False)["frequency_int"]
        .sum()
        .reset_index()
    )

    rows: list[LymeCountyYearValue] = []
    for (fips, year), group in grouped.groupby(["fips", "year"]):
        statuses = {
            str(row.case_status).strip().lower(): int(row.frequency_int)
            for row in group.itertuples(index=False)
        }
        confirmed = statuses.get("confirmed")
        probable = statuses.get("probable")
        total = sum(statuses.values())
        rows.append(
            LymeCountyYearValue(
                source_id=source_id,
                county_fips=str(fips).zfill(5),
                year=int(year),
                confirmed_cases=confirmed,
                probable_cases=probable,
                total_cases=total,
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))
```

- [ ] **Step 5: Run parser tests**

Run:

```bash
pytest tests/test_lyme_parsers.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add tickbiterisk/etl/lyme.py tests/test_lyme_parsers.py tests/fixtures/lyme_public_use_2022_2023_mini.csv
git commit -m "feat: parse CDC Lyme public use data"
```

---

### Task 5: Dashboard And Geodata Lyme Parsers

**Files:**
- Create: `tests/fixtures/ld_case_counts_by_county_mini.csv`
- Create: `tests/fixtures/lyme_geodata_mini.csv`
- Modify: `tickbiterisk/etl/lyme.py`
- Modify: `tests/test_lyme_parsers.py`

- [ ] **Step 1: Create fixture files**

Create `tests/fixtures/ld_case_counts_by_county_mini.csv`:

```csv
Ctyname,stname,ststatus,stcode,ctycode,Cases2020,cases2021,cases2022,cases2023
Anne Arundel County,Maryland,High Incidence,24,3,71,81,127,131
Baltimore County,Maryland,High Incidence,24,5,178,171,278,220
Fairfax County,Virginia,High Incidence,51,59,1,2,3,4
```

Create `tests/fixtures/lyme_geodata_mini.csv`:

```csv
STATEFP,COUNTYFP,GEOID,NAME,STUSPS,STATE_NAME,fips,year,Lyme_Confirmed_Cases,Lyme_Probable_Cases,Lyme_Confirmed_Probable_Cases
24,003,24003,Anne Arundel,MD,Maryland,24003,2020,53,18,71
24,003,24003,Anne Arundel,MD,Maryland,24003,2021,60,21,81
24,005,24005,Baltimore,MD,Maryland,24005,2020,120,58,178
51,059,51059,Fairfax,VA,Virginia,51059,2020,1,0,1
```

- [ ] **Step 2: Add failing parser tests**

Append to `tests/test_lyme_parsers.py`:

```python
from tickbiterisk.etl.lyme import parse_cdc_county_dashboard, parse_cdc_lyme_geodata


def test_parse_cdc_county_dashboard_handles_latin1_style_columns() -> None:
    rows = parse_cdc_county_dashboard(
        Path("tests/fixtures/ld_case_counts_by_county_mini.csv"),
        source_id="cdc_lyme_county_dashboard_2023",
    )
    anne = next(row for row in rows if row.county_fips == "24003" and row.year == 2022)
    assert anne.total_cases == 127
    assert anne.confirmed_cases is None
    assert anne.probable_cases is None


def test_parse_cdc_lyme_geodata_reads_confirmed_probable_components() -> None:
    rows = parse_cdc_lyme_geodata(
        Path("tests/fixtures/lyme_geodata_mini.csv"),
        source_id="cdc_lyme_county_geodata_2000_2021",
    )
    anne = next(row for row in rows if row.county_fips == "24003" and row.year == 2020)
    assert anne.confirmed_cases == 53
    assert anne.probable_cases == 18
    assert anne.total_cases == 71
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
pytest tests/test_lyme_parsers.py -v
```

Expected: FAIL with missing parser functions.

- [ ] **Step 4: Implement parsers**

Append to `tickbiterisk/etl/lyme.py`:

```python
def parse_cdc_county_dashboard(path: Path, source_id: str) -> list[LymeCountyYearValue]:
    df = pd.read_csv(path, dtype=str, encoding="latin1")
    required = {"Ctyname", "stname", "stcode", "ctycode"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CDC county dashboard columns: {sorted(missing)}")

    md = df[df["stname"].eq("Maryland")].copy()
    year_columns = [
        column
        for column in md.columns
        if column.lower().startswith("cases") and column.lower().replace("cases", "").isdigit()
    ]
    rows: list[LymeCountyYearValue] = []
    for record in md.to_dict(orient="records"):
        county_fips = f"{int(record['stcode']):02d}{int(record['ctycode']):03d}"
        if county_fips not in maryland_fips_set():
            continue
        for column in year_columns:
            year = int(column.lower().replace("cases", ""))
            total = _frequency_to_int(record[column])
            rows.append(
                LymeCountyYearValue(
                    source_id=source_id,
                    county_fips=county_fips,
                    year=year,
                    confirmed_cases=None,
                    probable_cases=None,
                    total_cases=total,
                )
            )
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))


def parse_cdc_lyme_geodata(path: Path, source_id: str) -> list[LymeCountyYearValue]:
    df = pd.read_csv(path, dtype=str)
    required = {
        "STUSPS",
        "fips",
        "year",
        "Lyme_Confirmed_Cases",
        "Lyme_Probable_Cases",
        "Lyme_Confirmed_Probable_Cases",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CDC Lyme geodata columns: {sorted(missing)}")

    md = df[df["STUSPS"].eq("MD")].copy()
    md["fips"] = md["fips"].astype(str).str.split(".").str[0].str.zfill(5)
    md = md[md["fips"].isin(maryland_fips_set())]

    rows: list[LymeCountyYearValue] = []
    for record in md.to_dict(orient="records"):
        rows.append(
            LymeCountyYearValue(
                source_id=source_id,
                county_fips=record["fips"],
                year=int(float(record["year"])),
                confirmed_cases=_frequency_to_int(record["Lyme_Confirmed_Cases"]),
                probable_cases=_frequency_to_int(record["Lyme_Probable_Cases"]),
                total_cases=_frequency_to_int(record["Lyme_Confirmed_Probable_Cases"]),
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))
```

- [ ] **Step 5: Run parser tests**

Run:

```bash
pytest tests/test_lyme_parsers.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add tickbiterisk/etl/lyme.py tests/test_lyme_parsers.py tests/fixtures/ld_case_counts_by_county_mini.csv tests/fixtures/lyme_geodata_mini.csv
git commit -m "feat: parse Lyme dashboard and geodata sources"
```

---

### Task 6: Maryland Lyme Reconciliation

**Files:**
- Create: `tickbiterisk/etl/reconcile.py`
- Create: `tests/test_reconcile.py`

- [ ] **Step 1: Write failing reconciliation tests**

Create `tests/test_reconcile.py`:

```python
from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.reconcile import reconcile_lyme_county_year


def test_reconcile_prefers_public_use_when_values_agree() -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue("cdc_lyme_county_dashboard_2023", "24003", 2022, None, None, 127),
    ]
    reconciled = reconcile_lyme_county_year(rows)
    assert len(reconciled) == 1
    assert reconciled[0].total_cases == 127
    assert reconciled[0].canonical_source_id == "cdc_lyme_public_2022_2023"
    assert reconciled[0].reconciliation_status == "matched"


def test_reconcile_flags_conflicting_comparator() -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue("cdc_all_tbd_2022_public", "24003", 2022, None, None, 460),
    ]
    reconciled = reconcile_lyme_county_year(rows)
    assert reconciled[0].total_cases == 127
    assert reconciled[0].canonical_source_id == "cdc_lyme_public_2022_2023"
    assert reconciled[0].reconciliation_status == "conflict"
    assert "cdc_all_tbd_2022_public=460" in reconciled[0].source_values_summary
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_reconcile.py -v
```

Expected: FAIL with missing `tickbiterisk.etl.reconcile`.

- [ ] **Step 3: Implement reconciliation**

Create `tickbiterisk/etl/reconcile.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from tickbiterisk.etl.lyme import LymeCountyYearValue

SOURCE_PRIORITY = [
    "mdh_lyme_2013_2024_pdf",
    "cdc_lyme_public_2022_2023",
    "cdc_lyme_public_2008_2021",
    "cdc_lyme_public_1992_2007",
    "cdc_lyme_county_dashboard_2023",
    "cdc_lyme_county_geodata_2000_2021",
    "cdc_all_tbd_2022_public",
]


@dataclass(frozen=True)
class ReconciledLymeCountyYear:
    county_fips: str
    year: int
    confirmed_cases: int | None
    probable_cases: int | None
    total_cases: int
    canonical_source_id: str
    source_values_summary: str
    reconciliation_status: str
    data_quality_flags: str


def _source_rank(source_id: str) -> int:
    try:
        return SOURCE_PRIORITY.index(source_id)
    except ValueError:
        return len(SOURCE_PRIORITY)


def reconcile_lyme_county_year(rows: list[LymeCountyYearValue]) -> list[ReconciledLymeCountyYear]:
    grouped: dict[tuple[str, int], list[LymeCountyYearValue]] = {}
    for row in rows:
        grouped.setdefault((row.county_fips, row.year), []).append(row)

    reconciled: list[ReconciledLymeCountyYear] = []
    for (county_fips, year), values in sorted(grouped.items()):
        ordered = sorted(values, key=lambda item: _source_rank(item.source_id))
        canonical = ordered[0]
        totals = {value.total_cases for value in values}
        status = "matched" if len(totals) == 1 else "conflict"
        flags: list[str] = []
        if year == 2020:
            flags.append("covid_reporting_disruption")
        if year >= 2022:
            flags.append("lyme_case_definition_change")
        if any(value.source_id == "cdc_all_tbd_2022_public" for value in values):
            flags.append("contains_noncanonical_all_tbd_comparator")

        summary = ";".join(f"{value.source_id}={value.total_cases}" for value in ordered)
        reconciled.append(
            ReconciledLymeCountyYear(
                county_fips=county_fips,
                year=year,
                confirmed_cases=canonical.confirmed_cases,
                probable_cases=canonical.probable_cases,
                total_cases=canonical.total_cases,
                canonical_source_id=canonical.source_id,
                source_values_summary=summary,
                reconciliation_status=status,
                data_quality_flags=";".join(flags),
            )
        )
    return reconciled
```

- [ ] **Step 4: Run reconciliation tests**

Run:

```bash
pytest tests/test_reconcile.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tickbiterisk/etl/reconcile.py tests/test_reconcile.py
git commit -m "feat: reconcile Maryland Lyme source values"
```

---

### Task 7: Tick Vector And Pathogen Status Parsers

**Files:**
- Create: `tickbiterisk/etl/tick_status.py`
- Create: `tests/test_tick_status.py`
- Use temporary XLSX files created inside the tests.

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_tick_status.py`:

```python
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.tick_status import parse_ixodes_status, parse_lone_star_status, parse_pathogen_status


def _write_excel(path: Path, sheet_name: str, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_excel(path, sheet_name=sheet_name, index=False)


def test_parse_ixodes_status_normalizes_maryland_rows(tmp_path: Path) -> None:
    path = tmp_path / "ixodes.xlsx"
    _write_excel(
        path,
        "Ixodes records 2025",
        [
            {
                "FIPSCode": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Ixodes_scapularis_County_Status": "Established",
                "Ixodes_scapularis_data_source": "CDC historic",
                "Ixodes_pacificus_county_status": "No records",
                "Ixodes_pacificus_data_source": "CDC historic",
            }
        ],
    )
    rows = parse_ixodes_status(path, source_id="cdc_ixodes_county_status_2025")
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["ixodes_scapularis_status"] == "established"


def test_parse_pathogen_status_preserves_no_records_language(tmp_path: Path) -> None:
    path = tmp_path / "pathogens.xlsx"
    _write_excel(
        path,
        "Ixodes Pathogens 2025",
        [
            {
                "FIPS_Code": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "Borrelia_burgdorferi_sensu_stricto_County_Status": "No records",
                "Borrelia_miyamotoi_County_Status": "Present",
                "Anaplasma_phagocytophilum_human_active_variant_County_Status": "No records",
                "Babesia_microti_County_Status": "No records",
                "Powassan_virus_County_Status": "No records",
            }
        ],
    )
    rows = parse_pathogen_status(path, source_id="cdc_ixodes_pathogen_status_2025")
    assert rows[0]["borrelia_burgdorferi_status"] == "no_records"
    assert rows[0]["borrelia_miyamotoi_status"] == "present"


def test_parse_lone_star_status(tmp_path: Path) -> None:
    path = tmp_path / "lone-star.xlsx"
    _write_excel(
        path,
        "A. americanum Records 2024",
        [
            {
                "FIPS": "24003",
                "State": "MD",
                "County": "Anne Arundel County",
                "County Status of A. americanum": "Established",
                "Source": "Springer et al. 2014",
                "Source Comments": "",
            }
        ],
    )
    rows = parse_lone_star_status(path, source_id="cdc_lone_star_status_2024")
    assert rows[0]["county_fips"] == "24003"
    assert rows[0]["amblyomma_americanum_status"] == "established"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_tick_status.py -v
```

Expected: FAIL with missing `tickbiterisk.etl.tick_status`.

- [ ] **Step 3: Implement tick status parsers**

Create `tickbiterisk/etl/tick_status.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import maryland_fips_set


def _norm_status(value: object) -> str:
    text = str(value).strip().lower().replace(" ", "_")
    if text in {"nan", "", "none"}:
        return "unknown"
    return text


def _read_excel_sheet(path: Path, sheet_name: str, required_columns: set[str]) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, dtype=str)
    if required_columns.issubset(set(df.columns)):
        return df
    df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, header=1)
    if required_columns.issubset(set(df.columns)):
        return df
    missing = required_columns - set(df.columns)
    raise ValueError(f"Missing columns in {sheet_name}: {sorted(missing)}")


def _filter_md(df: pd.DataFrame, fips_column: str) -> pd.DataFrame:
    md = df.copy()
    md[fips_column] = md[fips_column].astype(str).str.split(".").str[0].str.zfill(5)
    return md[md[fips_column].isin(maryland_fips_set())].copy()


def parse_ixodes_status(path: Path, source_id: str) -> list[dict[str, object]]:
    required = {
        "FIPSCode",
        "State",
        "County",
        "Ixodes_scapularis_County_Status",
        "Ixodes_pacificus_county_status",
    }
    df = _read_excel_sheet(path, "Ixodes records 2025", required)
    df = _filter_md(df, "FIPSCode")
    rows: list[dict[str, object]] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            {
                "source_id": source_id,
                "county_fips": record["FIPSCode"],
                "county_name": record["County"],
                "ixodes_scapularis_status": _norm_status(record["Ixodes_scapularis_County_Status"]),
                "ixodes_scapularis_source": record.get("Ixodes_scapularis_data_source", ""),
                "ixodes_pacificus_status": _norm_status(record["Ixodes_pacificus_county_status"]),
                "ixodes_pacificus_source": record.get("Ixodes_pacificus_data_source", ""),
            }
        )
    return rows


def parse_pathogen_status(path: Path, source_id: str) -> list[dict[str, object]]:
    required = {
        "FIPS_Code",
        "State",
        "County",
        "Borrelia_burgdorferi_sensu_stricto_County_Status",
        "Borrelia_miyamotoi_County_Status",
        "Anaplasma_phagocytophilum_human_active_variant_County_Status",
        "Babesia_microti_County_Status",
        "Powassan_virus_County_Status",
    }
    df = _read_excel_sheet(path, "Ixodes Pathogens 2025", required)
    df = _filter_md(df, "FIPS_Code")
    rows: list[dict[str, object]] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            {
                "source_id": source_id,
                "county_fips": record["FIPS_Code"],
                "county_name": record["County"],
                "borrelia_burgdorferi_status": _norm_status(record["Borrelia_burgdorferi_sensu_stricto_County_Status"]),
                "borrelia_miyamotoi_status": _norm_status(record["Borrelia_miyamotoi_County_Status"]),
                "anaplasma_phagocytophilum_status": _norm_status(record["Anaplasma_phagocytophilum_human_active_variant_County_Status"]),
                "babesia_microti_status": _norm_status(record["Babesia_microti_County_Status"]),
                "powassan_virus_status": _norm_status(record["Powassan_virus_County_Status"]),
            }
        )
    return rows


def parse_lone_star_status(path: Path, source_id: str) -> list[dict[str, object]]:
    required = {"FIPS", "State", "County", "County Status of A. americanum"}
    df = _read_excel_sheet(path, "A. americanum Records 2024", required)
    df = _filter_md(df, "FIPS")
    rows: list[dict[str, object]] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            {
                "source_id": source_id,
                "county_fips": record["FIPS"],
                "county_name": record["County"],
                "amblyomma_americanum_status": _norm_status(record["County Status of A. americanum"]),
                "status_source": record.get("Source", ""),
                "source_comments": record.get("Source Comments", ""),
            }
        )
    return rows
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_tick_status.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tickbiterisk/etl/tick_status.py tests/test_tick_status.py
git commit -m "feat: parse Maryland tick status workbooks"
```

---

### Task 8: Local ETL Output Builder

**Files:**
- Create: `tickbiterisk/etl/build.py`
- Create: `tests/test_build_outputs.py`
- Modify: `tickbiterisk/cli.py`

- [ ] **Step 1: Write failing build-output tests**

Create `tests/test_build_outputs.py`:

```python
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.build import write_reconciled_lyme_outputs
from tickbiterisk.etl.lyme import LymeCountyYearValue


def test_write_reconciled_lyme_outputs_creates_csv(tmp_path: Path) -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue("cdc_lyme_county_dashboard_2023", "24003", 2022, None, None, 127),
    ]
    output = write_reconciled_lyme_outputs(rows, tmp_path)
    assert output.name == "lyme_county_year_reconciled.csv"
    df = pd.read_csv(output, dtype={"county_fips": str})
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "total_cases"]) == 127
    assert df.loc[0, "reconciliation_status"] == "matched"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_build_outputs.py -v
```

Expected: FAIL with missing `tickbiterisk.etl.build`.

- [ ] **Step 3: Implement build output writer**

Create `tickbiterisk/etl/build.py`:

```python
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.reconcile import reconcile_lyme_county_year


def write_reconciled_lyme_outputs(rows: list[LymeCountyYearValue], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    reconciled = reconcile_lyme_county_year(rows)
    output_path = output_dir / "lyme_county_year_reconciled.csv"
    pd.DataFrame([asdict(row) for row in reconciled]).to_csv(output_path, index=False)
    return output_path
```

- [ ] **Step 4: Add CLI shell**

Create `tickbiterisk/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="TickBiteRisk ETL utilities")
etl_app = typer.Typer(help="ETL commands")
app.add_typer(etl_app, name="etl")


@etl_app.command("check")
def etl_check(output_dir: Path = typer.Option(Path("build/etl"), help="Output directory for ETL artifacts.")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"ETL output directory ready: {output_dir}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_build_outputs.py -v
```

Expected: PASS.

- [ ] **Step 6: Verify CLI**

Run:

```bash
python -m tickbiterisk.cli etl check --output-dir build/etl
```

Expected output includes `ETL output directory ready: build/etl`.

- [ ] **Step 7: Commit**

Run:

```bash
git add tickbiterisk/etl/build.py tickbiterisk/cli.py tests/test_build_outputs.py
git commit -m "feat: write reconciled Lyme ETL outputs"
```

---

### Task 9: Postgres Warehouse Schema

**Files:**
- Create: `sql/schema.sql`
- Create: `tests/test_schema.py`

- [ ] **Step 1: Write failing schema smoke test**

Create `tests/test_schema.py`:

```python
from pathlib import Path


def test_schema_defines_core_tables() -> None:
    schema = Path("sql/schema.sql").read_text(encoding="utf-8")
    for table in [
        "source_files",
        "md_jurisdictions",
        "lyme_county_year_source_values",
        "lyme_county_year_reconciled",
        "tick_vector_status",
        "tick_pathogen_status",
        "lone_star_status",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_schema.py -v
```

Expected: FAIL with missing `sql/schema.sql`.

- [ ] **Step 3: Add schema**

Create `sql/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS source_files (
    source_id text PRIMARY KEY,
    source_name text NOT NULL,
    source_location text NOT NULL,
    file_format text NOT NULL,
    geography text NOT NULL,
    time_coverage text NOT NULL,
    role text NOT NULL,
    status text NOT NULL,
    redistribution text NOT NULL,
    sha256 text,
    notes text,
    ingested_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS md_jurisdictions (
    county_fips char(5) PRIMARY KEY,
    state_fips char(2) NOT NULL DEFAULT '24',
    state char(2) NOT NULL DEFAULT 'MD',
    county_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS lyme_county_year_source_values (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    confirmed_cases integer,
    probable_cases integer,
    total_cases integer NOT NULL,
    ingested_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips, year)
);

CREATE TABLE IF NOT EXISTS lyme_county_year_reconciled (
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    year integer NOT NULL,
    confirmed_cases integer,
    probable_cases integer,
    total_cases integer NOT NULL,
    canonical_source_id text NOT NULL,
    source_values_summary text NOT NULL,
    reconciliation_status text NOT NULL,
    data_quality_flags text NOT NULL DEFAULT '',
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (county_fips, year)
);

CREATE TABLE IF NOT EXISTS tick_vector_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    ixodes_scapularis_status text,
    ixodes_pacificus_status text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);

CREATE TABLE IF NOT EXISTS tick_pathogen_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    borrelia_burgdorferi_status text,
    borrelia_miyamotoi_status text,
    anaplasma_phagocytophilum_status text,
    babesia_microti_status text,
    powassan_virus_status text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);

CREATE TABLE IF NOT EXISTS lone_star_status (
    source_id text NOT NULL,
    county_fips char(5) NOT NULL REFERENCES md_jurisdictions(county_fips),
    amblyomma_americanum_status text,
    status_source text,
    source_comments text,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (source_id, county_fips)
);
```

- [ ] **Step 4: Run schema test**

Run:

```bash
pytest tests/test_schema.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add sql/schema.sql tests/test_schema.py
git commit -m "feat: add warehouse schema"
```

---

### Task 10: Documentation Status Update And Full Verification

**Files:**
- Modify: `docs/software-requirements-spec.md`
- Modify: `docs/data-manifest.md`
- Modify: `README.md`

- [ ] **Step 1: Update docs with implementation status**

In `docs/software-requirements-spec.md`, add this after the version block:

```markdown
Implementation status: the first ETL slice is implemented through source parsing, Maryland Lyme reconciliation, tick-status normalization, and Postgres-ready schema. Weather acquisition and model backtesting are the next planned slices.
```

In `docs/data-manifest.md`, update statuses for supported ETL sources by appending `etl_supported` to these rows:

- `cdc_lyme_public_1992_2007`
- `cdc_lyme_public_2008_2021`
- `cdc_lyme_public_2022_2023`
- `cdc_lyme_county_dashboard_2023`
- `cdc_lyme_county_geodata_2000_2021`
- `cdc_ixodes_county_status_2025`
- `cdc_ixodes_pathogen_status_2025`
- `cdc_lone_star_status_2024`

In `README.md`, add a short "Current build status" section:

```markdown
## current build status

The active implementation is a Maryland-first ETL and modeling prototype. The current code focuses on source manifest parsing, Maryland Lyme county-year reconciliation, tick/vector status normalization, and a Postgres-ready warehouse schema. The FastAPI endpoint described below is roadmap behavior until the model-ready warehouse tables are built.
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run diff check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Confirm no secrets are tracked**

Run:

```bash
git status --short --ignored .env
git check-ignore -v .env
```

Expected: `.env` appears ignored and `.gitignore` is reported as the ignore source.

- [ ] **Step 5: Commit docs update**

Run:

```bash
git add docs/software-requirements-spec.md docs/data-manifest.md README.md
git commit -m "docs: update ETL implementation status"
```

---

## Plan Self-Review

Spec coverage:

- SRS FR1-FR2 are covered by Task 3.
- SRS FR3 is covered by Task 9 and local CSV outputs in Task 8.
- SRS FR4 is covered by Tasks 4-6.
- SRS FR5 is covered by Task 7.
- SRS FR6 weather acquisition is intentionally deferred to the next plan; this plan creates the Lyme outcome foundation first.
- SRS FR7 host ecology is intentionally deferred until deer/mast sources are acquired.
- SRS FR8-FR10 model scoring/backtests are intentionally deferred until the reconciled county-year panel exists.
- SRS FR11-FR12 are partially prepared through reconciliation flags and CSV outputs; product explanations and model-ready exports follow in the modeling plan.

Known gaps for the next plans:

- Maryland weather acquisition implementation.
- Population denominator ingestion.
- MDH PDF extraction through 2024.
- Baseline backtest harness.
- Risk score generation.
- Postgres live loader command.
