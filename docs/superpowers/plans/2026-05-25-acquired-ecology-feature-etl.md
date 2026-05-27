# Acquired Ecology Feature ETL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Maryland contact-pressure and mast/acorn feature ETL from already acquired source data.

**Architecture:** Add CSV-first feature builders that follow the repo's existing ETL pattern: domain dataclasses and parsers in focused modules, deterministic CSV writers in paired build modules, thin Typer CLI commands, source provenance on every row, and quality flags for uncertainty. Contact pressure becomes a model-ready county-year feature table; mast/acorn becomes a cautious parser plus extraction-summary output so weak document extraction is visible without fabricating features.

**Tech Stack:** Python 3.12 stdlib (`csv`, `dataclasses`, `hashlib`, `pathlib`, `re`), existing `pypdfium2` and optional Docling via current deer PDF helper functions, Typer, pytest, ruff. No new dependency is required in this slice.

---

## File Structure

- Create `tickbiterisk/etl/contact_pressure.py`
  - Reads BPS, county reference, and population CSVs.
  - Builds `ContactPressureFeature` rows with denominator-adjusted features and quality flags.
- Create `tickbiterisk/etl/contact_pressure_build.py`
  - Writes `contact_pressure_features_county_year.csv` with append/dedupe semantics.
- Create `tests/test_contact_pressure.py`
  - Covers feature calculations, missing denominators, historical coverage flags, and writer behavior.
- Modify `tickbiterisk/cli.py`
  - Add `etl contact-pressure`.
  - Add `etl mast-acorn`.
- Create `tests/test_cli_contact_pressure.py`
  - Covers contact-pressure CLI wiring.
- Create `tickbiterisk/etl/mast_acorn.py`
  - Defines mast/acorn dataclasses, text parser, PDF extraction wrapper, extraction summary builder, and manual observation reader.
- Create `tickbiterisk/etl/mast_acorn_build.py`
  - Writes structured mast rows, extraction summaries, and optional manual observation rows.
- Create `tests/test_mast_acorn.py`
  - Covers mast text parsing, parser fallback summaries, manual observation flags, and writers.
- Create `tests/test_cli_mast_acorn.py`
  - Covers CLI behavior without live OCR/network.
- Modify docs:
  - `README.md`
  - `docs/data-manifest.md`
  - `docs/etl-pipeline.md`

---

## Task 1: Contact Pressure Feature Builder

**Files:**
- Create: `tickbiterisk/etl/contact_pressure.py`
- Create: `tickbiterisk/etl/contact_pressure_build.py`
- Test: `tests/test_contact_pressure.py`

- [ ] **Step 1: Write failing contact-pressure tests**

Create `tests/test_contact_pressure.py` with fixture writers and these tests:

```python
import csv
from dataclasses import replace

from tickbiterisk.etl.contact_pressure import (
    ContactPressureFeature,
    build_contact_pressure_features,
)
from tickbiterisk.etl.contact_pressure_build import (
    CONTACT_PRESSURE_COLUMNS,
    write_contact_pressure_output,
)


def _write(path, header, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _sample_inputs(tmp_path):
    bps = tmp_path / "building_permits.csv"
    county_reference = tmp_path / "county_reference.csv"
    population = tmp_path / "county_population_year.csv"
    _write(
        bps,
        [
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
        ],
        [
            ["24003", "Anne Arundel County", "2023", "12", "100", "2", "4", "10", "116", "42000000", "census_bps_county_2023", "hash2023"],
            ["24003", "Anne Arundel County", "2024", "12", "120", "0", "0", "0", "120", "43000000", "census_bps_county_2024", "hash2024"],
            ["24005", "Baltimore County", "2023", "12", "50", "0", "0", "0", "50", "10000000", "census_bps_county_2023", "hash2023"],
        ],
    )
    _write(
        county_reference,
        [
            "county_fips",
            "state_fips",
            "state",
            "county_name",
            "aland_sqmi",
            "awater_sqmi",
            "intptlat",
            "intptlon",
            "geography_source",
            "source_url_hash",
        ],
        [
            ["24003", "24", "MD", "Anne Arundel County", "414.806", "172.995", "38.99", "-76.56", "Census Gazetteer", "geo"],
            ["24005", "24", "MD", "Baltimore County", "598.358", "83.382", "39.44", "-76.61", "Census Gazetteer", "geo"],
        ],
    )
    _write(
        population,
        [
            "county_fips",
            "county_name",
            "year",
            "population",
            "source_id",
            "census_dataset",
            "vintage",
            "source_url_hash",
        ],
        [
            ["24003", "Anne Arundel County", "2023", "590000", "census_population_2023", "pep", "2023", "pop"],
            ["24005", "Baltimore County", "2023", "850000", "census_population_2023", "pep", "2023", "pop"],
        ],
    )
    return bps, county_reference, population


def test_build_contact_pressure_features_calculates_denominator_rates(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2023 = next(row for row in rows if row.county_fips == "24003" and row.year == 2023)
    assert anne_2023.residential_units_authorized == 116
    assert anne_2023.units_authorized_per_sqmi == round(116 / 414.806, 6)
    assert anne_2023.units_authorized_per_100k == round(116 / 590000 * 100000, 6)
    assert anne_2023.total_value_dollars == 42000000
    assert anne_2023.population == 590000
    assert anne_2023.land_area_sqmi == 414.806
    assert anne_2023.feature_quality_flags == (
        "construction_proxy_only,historical_partial_jurisdiction_coverage"
    )


def test_build_contact_pressure_features_flags_missing_population(tmp_path) -> None:
    bps, county_reference, population = _sample_inputs(tmp_path)

    rows = build_contact_pressure_features(
        building_permits_path=bps,
        county_reference_path=county_reference,
        population_path=population,
    )

    anne_2024 = next(row for row in rows if row.county_fips == "24003" and row.year == 2024)
    assert anne_2024.units_authorized_per_100k is None
    assert anne_2024.population is None
    assert "missing_population" in anne_2024.feature_quality_flags
    assert "construction_proxy_only" in anne_2024.feature_quality_flags


def test_write_contact_pressure_output_appends_and_dedupes(tmp_path) -> None:
    row = ContactPressureFeature(
        county_fips="24003",
        county_name="Anne Arundel County",
        year=2024,
        residential_units_authorized=120,
        units_authorized_per_sqmi=0.289292,
        units_authorized_per_100k=None,
        total_value_dollars=43000000,
        land_area_sqmi=414.806,
        population=None,
        source_id="census_bps_county_2024",
        source_url_hash="hash2024",
        feature_quality_flags="construction_proxy_only,missing_population",
    )
    replacement = replace(row, residential_units_authorized=121)

    write_contact_pressure_output([row], tmp_path)
    output = write_contact_pressure_output([replacement], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert output.name == "contact_pressure_features_county_year.csv"
    assert list(records[0].keys()) == CONTACT_PRESSURE_COLUMNS
    assert len(records) == 1
    assert records[0]["county_fips"] == "24003"
    assert records[0]["residential_units_authorized"] == "121"
```

- [ ] **Step 2: Run the contact-pressure tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_contact_pressure.py -q
```

Expected: FAIL because `tickbiterisk.etl.contact_pressure` and `tickbiterisk.etl.contact_pressure_build` do not exist.

- [ ] **Step 3: Implement contact-pressure domain code**

Create `tickbiterisk/etl/contact_pressure.py` with:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContactPressureFeature:
    county_fips: str
    county_name: str
    year: int
    residential_units_authorized: int
    units_authorized_per_sqmi: float | None
    units_authorized_per_100k: float | None
    total_value_dollars: int
    land_area_sqmi: float | None
    population: int | None
    source_id: str
    source_url_hash: str
    feature_quality_flags: str


def build_contact_pressure_features(
    *,
    building_permits_path: Path,
    county_reference_path: Path,
    population_path: Path,
) -> list[ContactPressureFeature]:
    county_reference = _read_county_reference(county_reference_path)
    population = _read_population(population_path)
    permit_rows = _read_building_permits(building_permits_path)
    year_counts = _year_counts(permit_rows)
    features = []
    for row in permit_rows:
        county_fips = str(row["county_fips"]).zfill(5)
        year = int(row["year"])
        units = _parse_int(row["total_units_authorized"])
        land_area = county_reference.get(county_fips, {}).get("aland_sqmi")
        pop = population.get((county_fips, year))
        flags = ["construction_proxy_only"]
        units_per_sqmi = None
        if land_area is None or land_area <= 0:
            flags.append("missing_land_area")
        else:
            units_per_sqmi = round(units / land_area, 6)
        units_per_100k = None
        if pop is None or pop <= 0:
            flags.append("missing_population")
        else:
            units_per_100k = round(units / pop * 100000, 6)
        if year_counts[year] < 24:
            flags.append("historical_partial_jurisdiction_coverage")
        features.append(
            ContactPressureFeature(
                county_fips=county_fips,
                county_name=row["county_name"],
                year=year,
                residential_units_authorized=units,
                units_authorized_per_sqmi=units_per_sqmi,
                units_authorized_per_100k=units_per_100k,
                total_value_dollars=_parse_int(row["total_value_dollars"]),
                land_area_sqmi=land_area,
                population=pop,
                source_id=row["source_id"],
                source_url_hash=row["source_url_hash"],
                feature_quality_flags=",".join(flags),
            )
        )
    return sorted(features, key=lambda item: (item.county_fips, item.year))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_building_permits(path: Path) -> list[dict[str, str]]:
    return _read_csv(path)


def _read_county_reference(path: Path) -> dict[str, dict[str, float]]:
    rows = {}
    for row in _read_csv(path):
        rows[str(row["county_fips"]).zfill(5)] = {
            "aland_sqmi": _parse_float_or_none(row["aland_sqmi"]),
        }
    return rows


def _read_population(path: Path) -> dict[tuple[str, int], int]:
    rows = {}
    for row in _read_csv(path):
        rows[(str(row["county_fips"]).zfill(5), int(row["year"]))] = _parse_int(
            row["population"]
        )
    return rows


def _year_counts(rows: list[dict[str, str]]) -> dict[int, int]:
    counts: dict[int, set[str]] = {}
    for row in rows:
        counts.setdefault(int(row["year"]), set()).add(str(row["county_fips"]).zfill(5))
    return {year: len(county_fips) for year, county_fips in counts.items()}


def _parse_int(value: str) -> int:
    return int(str(value).strip().replace(",", ""))


def _parse_float_or_none(value: str) -> float | None:
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return float(cleaned)
```

- [ ] **Step 4: Implement contact-pressure writer**

Create `tickbiterisk/etl/contact_pressure_build.py` with:

```python
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.contact_pressure import ContactPressureFeature


CONTACT_PRESSURE_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "residential_units_authorized",
    "units_authorized_per_sqmi",
    "units_authorized_per_100k",
    "total_value_dollars",
    "land_area_sqmi",
    "population",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
]


def write_contact_pressure_output(
    rows: list[ContactPressureFeature],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "contact_pressure_features_county_year.csv"
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record): record for record in records}
    ordered = sorted(
        keyed.values(),
        key=lambda record: (record["county_fips"], int(record["year"])),
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONTACT_PRESSURE_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: ContactPressureFeature) -> dict[str, object]:
    record = asdict(row)
    record["county_fips"] = str(record["county_fips"]).zfill(5)
    return record


def _read_existing_records(output_path: Path) -> list[dict[str, str]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _record_key(record: dict[str, object]) -> tuple[str, int]:
    return (str(record["county_fips"]).zfill(5), int(record["year"]))
```

- [ ] **Step 5: Run contact-pressure tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_contact_pressure.py -q
.venv/bin/python -m ruff check tickbiterisk/etl/contact_pressure.py tickbiterisk/etl/contact_pressure_build.py tests/test_contact_pressure.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 6: Commit contact-pressure feature builder**

Run:

```bash
git add tickbiterisk/etl/contact_pressure.py tickbiterisk/etl/contact_pressure_build.py tests/test_contact_pressure.py
git commit -m "feat: build contact pressure features"
```

Expected: commit succeeds.

---

## Task 2: Contact Pressure CLI

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_contact_pressure.py`

- [ ] **Step 1: Write failing CLI test**

Create `tests/test_cli_contact_pressure.py`:

```python
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.contact_pressure import ContactPressureFeature


runner = CliRunner()


def test_contact_pressure_command_writes_features(tmp_path, monkeypatch) -> None:
    building_permits = tmp_path / "bps.csv"
    county_reference = tmp_path / "county_reference.csv"
    population = tmp_path / "population.csv"
    building_permits.write_text("fixture", encoding="utf-8")
    county_reference.write_text("fixture", encoding="utf-8")
    population.write_text("fixture", encoding="utf-8")

    monkeypatch.setattr(
        "tickbiterisk.cli.build_contact_pressure_features",
        lambda *, building_permits_path, county_reference_path, population_path: [
            ContactPressureFeature(
                county_fips="24003",
                county_name="Anne Arundel County",
                year=2024,
                residential_units_authorized=120,
                units_authorized_per_sqmi=0.289292,
                units_authorized_per_100k=None,
                total_value_dollars=43000000,
                land_area_sqmi=414.806,
                population=None,
                source_id="census_bps_county_2024",
                source_url_hash="hash2024",
                feature_quality_flags="construction_proxy_only,missing_population",
            )
        ],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "contact-pressure",
            "--building-permits-path",
            str(building_permits),
            "--county-reference-path",
            str(county_reference),
            "--population-path",
            str(population),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 contact pressure feature row(s)" in result.stdout
    assert (tmp_path / "out" / "contact_pressure_features_county_year.csv").exists()
```

- [ ] **Step 2: Run CLI test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_contact_pressure.py -q
```

Expected: FAIL because the CLI command/imports do not exist.

- [ ] **Step 3: Wire CLI imports and command**

Modify `tickbiterisk/cli.py` imports:

```python
from tickbiterisk.etl.contact_pressure import build_contact_pressure_features
from tickbiterisk.etl.contact_pressure_build import write_contact_pressure_output
```

Add command near the other ETL commands:

```python
@etl_app.command("contact-pressure")
def contact_pressure(
    building_permits_path: Path = typer.Option(
        Path("build/etl/building-permits/maryland_building_permits_county_year.csv"),
        help="Input Maryland building permits county-year CSV.",
    ),
    county_reference_path: Path = typer.Option(
        Path("build/etl/county-reference/county_reference.csv"),
        help="County reference CSV with Census land area.",
    ),
    population_path: Path = typer.Option(
        Path("build/etl/population/county_population_year.csv"),
        help="County-year population denominator CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/contact-pressure"),
        help="Output directory for contact pressure feature artifacts.",
    ),
) -> None:
    rows = build_contact_pressure_features(
        building_permits_path=building_permits_path,
        county_reference_path=county_reference_path,
        population_path=population_path,
    )
    output = write_contact_pressure_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} contact pressure feature row(s) to {output}")
```

- [ ] **Step 4: Run CLI and focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_contact_pressure.py tests/test_contact_pressure.py -q
.venv/bin/python -m ruff check tickbiterisk/cli.py tests/test_cli_contact_pressure.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 5: Commit contact-pressure CLI**

Run:

```bash
git add tickbiterisk/cli.py tests/test_cli_contact_pressure.py
git commit -m "feat: add contact pressure cli"
```

Expected: commit succeeds.

---

## Task 3: Mast/Acorn Parser And Extraction Summaries

**Files:**
- Create: `tickbiterisk/etl/mast_acorn.py`
- Test: `tests/test_mast_acorn.py`

- [ ] **Step 1: Write failing mast parser tests**

Create `tests/test_mast_acorn.py` with the first parser/extraction tests:

```python
from pathlib import Path

from tickbiterisk.etl.mast_acorn import (
    MastAcornExtractionSummary,
    build_mast_acorn_from_pdf,
    parse_mast_acorn_text,
)


MAST_TEXT = """
Western Maryland Mast Survey 2021
Region: Western Maryland
County: Garrett County
Mast Category: overall
Hard Mast Index: 82.5
Soft Mast Index: 41
Acorn Index: 77
Mast Rating: bumper
Plots Observed: 20
Expected Plots: 20
"""


def test_parse_mast_acorn_text_extracts_supported_county_values() -> None:
    rows = parse_mast_acorn_text(
        MAST_TEXT,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24023"
    assert row.county_name == "Garrett County"
    assert row.year == 2021
    assert row.region == "Western Maryland"
    assert row.mast_category == "overall"
    assert row.mast_index == 82.5
    assert row.hard_mast_index == 82.5
    assert row.soft_mast_index == 41.0
    assert row.acorn_index == 77.0
    assert row.mast_rating == "bumper"
    assert row.plots_observed == 20
    assert row.expected_plots == 20
    assert row.coverage_complete is True
    assert "western_maryland_only" in row.feature_quality_flags


def test_build_mast_acorn_from_pdf_uses_injected_text_extractor(tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    rows, summary = build_mast_acorn_from_pdf(
        pdf,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
        parser="pypdfium",
        text_extractor=lambda source: MAST_TEXT,
    )

    assert len(rows) == 1
    assert summary.extraction_status == "structured"
    assert summary.structured_row_count == 1
    assert summary.parser == "pypdfium"


def test_build_mast_acorn_from_pdf_records_no_supported_values(tmp_path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    rows, summary = build_mast_acorn_from_pdf(
        pdf,
        year=2020,
        source_id="maryland_dnr_wmd_mast_survey_2020",
        source_url="https://example.test/mast2020.pdf",
        parser="pypdfium",
        text_extractor=lambda source: "Western Maryland Mast Survey 2020",
    )

    assert rows == []
    assert isinstance(summary, MastAcornExtractionSummary)
    assert summary.extraction_status == "no_supported_values"
    assert summary.structured_row_count == 0
    assert "ocr_pending" in summary.feature_quality_flags
```

- [ ] **Step 2: Run mast parser tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_mast_acorn.py -q
```

Expected: FAIL because `tickbiterisk.etl.mast_acorn` does not exist.

- [ ] **Step 3: Implement mast/acorn parser and extraction summary**

Create `tickbiterisk/etl/mast_acorn.py` with:

```python
from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tickbiterisk.etl.deer_harvest import extract_docling_markdown, extract_pypdfium_text
from tickbiterisk.etl.maryland import load_maryland_jurisdictions


@dataclass(frozen=True)
class MastAcornCountyYear:
    county_fips: str
    county_name: str
    year: int
    region: str
    mast_category: str
    mast_index: float | None
    mast_rating: str
    acorn_index: float | None
    hard_mast_index: float | None
    soft_mast_index: float | None
    plots_observed: int | None
    expected_plots: int | None
    coverage_complete: bool | None
    source_id: str
    source_url_hash: str
    feature_quality_flags: str
    extracted_text_excerpt: str


@dataclass(frozen=True)
class MastAcornExtractionSummary:
    source_id: str
    source_url_hash: str
    year: int
    parser: str
    source_path: str
    extraction_status: str
    structured_row_count: int
    feature_quality_flags: str
    notes: str
    extracted_text_excerpt: str


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
    county_name = _extract_label(text, "County")
    if county_name is None:
        return []
    county = _county_lookup().get(_county_key(county_name))
    if county is None:
        return []
    hard_mast_index = _extract_float(text, "Hard Mast Index")
    soft_mast_index = _extract_float(text, "Soft Mast Index")
    acorn_index = _extract_float(text, "Acorn Index")
    mast_index = _extract_float(text, "Mast Index") or hard_mast_index
    plots_observed = _extract_int(text, "Plots Observed")
    expected_plots = _extract_int(text, "Expected Plots")
    coverage_complete = None
    if plots_observed is not None and expected_plots is not None:
        coverage_complete = plots_observed >= expected_plots
    flags = ["western_maryland_only"]
    return [
        MastAcornCountyYear(
            county_fips=county.county_fips,
            county_name=county.county_name,
            year=year,
            region=_extract_label(text, "Region") or "Western Maryland",
            mast_category=(_extract_label(text, "Mast Category") or "overall").lower(),
            mast_index=mast_index,
            mast_rating=(_extract_label(text, "Mast Rating") or "").lower(),
            acorn_index=acorn_index,
            hard_mast_index=hard_mast_index,
            soft_mast_index=soft_mast_index,
            plots_observed=plots_observed,
            expected_plots=expected_plots,
            coverage_complete=coverage_complete,
            source_id=source_id,
            source_url_hash=_source_url_hash(source_url),
            feature_quality_flags=",".join(flags),
            extracted_text_excerpt=_excerpt(text),
        )
    ]


def build_mast_acorn_from_pdf(
    source_path: Path,
    *,
    year: int,
    source_id: str,
    source_url: str,
    parser: str,
    text_extractor: Callable[[str | Path], str] = extract_pypdfium_text,
    converter_factory: Callable[[], object] | None = None,
) -> tuple[list[MastAcornCountyYear], MastAcornExtractionSummary]:
    if parser not in {"pypdfium", "docling"}:
        raise ValueError("mast-acorn parser must be pypdfium or docling")
    try:
        if parser == "docling" or converter_factory is not None:
            text = extract_docling_markdown(source_path, converter_factory=converter_factory)
        else:
            text = text_extractor(source_path)
    except Exception as exc:
        return [], _summary(
            source_path=source_path,
            source_id=source_id,
            source_url=source_url,
            year=year,
            parser=parser,
            extraction_status="parser_failed",
            structured_row_count=0,
            flags=["parser_low_confidence"],
            notes=str(exc),
            text="",
        )
    rows = parse_mast_acorn_text(
        text,
        year=year,
        source_id=source_id,
        source_url=source_url,
    )
    if not rows:
        return [], _summary(
            source_path=source_path,
            source_id=source_id,
            source_url=source_url,
            year=year,
            parser=parser,
            extraction_status="no_supported_values",
            structured_row_count=0,
            flags=["ocr_pending", "parser_low_confidence"],
            notes="No supported mast/acorn county table values were found.",
            text=text,
        )
    return rows, _summary(
        source_path=source_path,
        source_id=source_id,
        source_url=source_url,
        year=year,
        parser=parser,
        extraction_status="structured",
        structured_row_count=len(rows),
        flags=[],
        notes="Structured mast/acorn rows extracted.",
        text=text,
    )


def read_manual_mast_observations(input_path: Path) -> list[ManualMastObservation]:
    required_flags = ["manual_observation", "anecdotal", "not_official", "not_model_default"]
    observations = []
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            flags = _merge_flags(row.get("feature_quality_flags", ""), required_flags)
            observations.append(
                ManualMastObservation(
                    county_fips=str(row["county_fips"]).zfill(5),
                    county_name=row["county_name"],
                    year=int(row["year"]),
                    mast_rating=row["mast_rating"],
                    observation_basis=row["observation_basis"],
                    observer_scope=row.get("observer_scope", ""),
                    source_id=row["source_id"],
                    feature_quality_flags=flags,
                    notes=row.get("notes", ""),
                )
            )
    return sorted(observations, key=lambda row: (row.county_fips, row.year, row.source_id))


def _summary(
    *,
    source_path: Path,
    source_id: str,
    source_url: str,
    year: int,
    parser: str,
    extraction_status: str,
    structured_row_count: int,
    flags: list[str],
    notes: str,
    text: str,
) -> MastAcornExtractionSummary:
    return MastAcornExtractionSummary(
        source_id=source_id,
        source_url_hash=_source_url_hash(source_url),
        year=year,
        parser=parser,
        source_path=str(source_path),
        extraction_status=extraction_status,
        structured_row_count=structured_row_count,
        feature_quality_flags=",".join(flags),
        notes=notes,
        extracted_text_excerpt=_excerpt(text),
    )


def _county_lookup():
    return {_county_key(row.county_name): row for row in load_maryland_jurisdictions()}


def _county_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower().replace("county", ""))


def _extract_label(text: str, label: str) -> str | None:
    match = re.search(rf"{re.escape(label)}\\s*:\\s*([^\\n\\r]+)", text, flags=re.I)
    if match is None:
        return None
    return match.group(1).strip()


def _extract_float(text: str, label: str) -> float | None:
    value = _extract_label(text, label)
    if value is None:
        return None
    match = re.search(r"-?\\d+(?:\\.\\d+)?", value)
    return float(match.group(0)) if match else None


def _extract_int(text: str, label: str) -> int | None:
    value = _extract_float(text, label)
    return int(value) if value is not None else None


def _source_url_hash(source_url: str) -> str:
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def _excerpt(text: str, length: int = 500) -> str:
    return " ".join(text.split())[:length]


def _merge_flags(existing: str, required: list[str]) -> str:
    flags = [flag for flag in existing.split(",") if flag]
    for flag in required:
        if flag not in flags:
            flags.append(flag)
    return ",".join(flags)
```

- [ ] **Step 4: Run mast parser tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_mast_acorn.py -q
.venv/bin/python -m ruff check tickbiterisk/etl/mast_acorn.py tests/test_mast_acorn.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 5: Commit mast/acorn parser**

Run:

```bash
git add tickbiterisk/etl/mast_acorn.py tests/test_mast_acorn.py
git commit -m "feat: parse mast acorn reports"
```

Expected: commit succeeds.

---

## Task 4: Mast/Acorn Writers And Manual Observation Output

**Files:**
- Create: `tickbiterisk/etl/mast_acorn_build.py`
- Modify: `tests/test_mast_acorn.py`

- [ ] **Step 1: Add failing writer/manual observation tests**

Append tests to `tests/test_mast_acorn.py`:

```python
import csv
from dataclasses import replace

from tickbiterisk.etl.mast_acorn import ManualMastObservation, read_manual_mast_observations
from tickbiterisk.etl.mast_acorn_build import (
    MAST_ACORN_COLUMNS,
    MAST_ACORN_SUMMARY_COLUMNS,
    MANUAL_MAST_OBSERVATION_COLUMNS,
    write_manual_mast_observations_output,
    write_mast_acorn_output,
    write_mast_acorn_summary_output,
)


def test_write_mast_acorn_output_and_summary_dedupe(tmp_path) -> None:
    rows = parse_mast_acorn_text(
        MAST_TEXT,
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
    )
    replacement = replace(rows[0], mast_rating="good")
    output = write_mast_acorn_output(rows, tmp_path)
    output = write_mast_acorn_output([replacement], tmp_path, append=True)

    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert list(records[0].keys()) == MAST_ACORN_COLUMNS
    assert len(records) == 1
    assert records[0]["mast_rating"] == "good"

    _, summary = build_mast_acorn_from_pdf(
        tmp_path / "report.pdf",
        year=2021,
        source_id="maryland_dnr_wmd_mast_survey_2021",
        source_url="https://example.test/mast2021.pdf",
        parser="pypdfium",
        text_extractor=lambda source: MAST_TEXT,
    )
    summary_output = write_mast_acorn_summary_output([summary], tmp_path)
    with summary_output.open("r", encoding="utf-8", newline="") as handle:
        summary_records = list(csv.DictReader(handle))
    assert list(summary_records[0].keys()) == MAST_ACORN_SUMMARY_COLUMNS
    assert summary_records[0]["extraction_status"] == "structured"


def test_manual_mast_observations_are_flagged_and_written(tmp_path) -> None:
    manual = tmp_path / "manual.csv"
    manual.write_text(
        "\\n".join(
            [
                "county_fips,county_name,year,mast_rating,observation_basis,observer_scope,source_id,feature_quality_flags,notes",
                "24003,Anne Arundel County,2025,bumper,local resident observation of heavy acorn fall,neighborhood,manual_aa_2025,,Not official",
            ]
        ),
        encoding="utf-8",
    )

    rows = read_manual_mast_observations(manual)
    assert len(rows) == 1
    assert rows[0].county_fips == "24003"
    assert rows[0].mast_rating == "bumper"
    assert rows[0].feature_quality_flags == (
        "manual_observation,anecdotal,not_official,not_model_default"
    )

    output = write_manual_mast_observations_output(rows, tmp_path)
    with output.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert list(records[0].keys()) == MANUAL_MAST_OBSERVATION_COLUMNS
    assert records[0]["source_id"] == "manual_aa_2025"
```

- [ ] **Step 2: Run writer tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_mast_acorn.py::test_write_mast_acorn_output_and_summary_dedupe tests/test_mast_acorn.py::test_manual_mast_observations_are_flagged_and_written -q
```

Expected: FAIL because `tickbiterisk.etl.mast_acorn_build` does not exist.

- [ ] **Step 3: Implement mast/acorn writers**

Create `tickbiterisk/etl/mast_acorn_build.py` with:

```python
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.mast_acorn import (
    ManualMastObservation,
    MastAcornCountyYear,
    MastAcornExtractionSummary,
)


MAST_ACORN_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "region",
    "mast_category",
    "mast_index",
    "mast_rating",
    "acorn_index",
    "hard_mast_index",
    "soft_mast_index",
    "plots_observed",
    "expected_plots",
    "coverage_complete",
    "source_id",
    "source_url_hash",
    "feature_quality_flags",
    "extracted_text_excerpt",
]

MAST_ACORN_SUMMARY_COLUMNS = [
    "source_id",
    "source_url_hash",
    "year",
    "parser",
    "source_path",
    "extraction_status",
    "structured_row_count",
    "feature_quality_flags",
    "notes",
    "extracted_text_excerpt",
]

MANUAL_MAST_OBSERVATION_COLUMNS = [
    "county_fips",
    "county_name",
    "year",
    "mast_rating",
    "observation_basis",
    "observer_scope",
    "source_id",
    "feature_quality_flags",
    "notes",
]


def write_mast_acorn_output(
    rows: list[MastAcornCountyYear],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_rows(
        rows,
        output_dir / "maryland_dnr_mast_acorn_county_year.csv",
        MAST_ACORN_COLUMNS,
        key_fields=("county_fips", "year", "mast_category", "source_id"),
        append=append,
    )


def write_mast_acorn_summary_output(
    rows: list[MastAcornExtractionSummary],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_rows(
        rows,
        output_dir / "maryland_dnr_mast_acorn_extraction_summary.csv",
        MAST_ACORN_SUMMARY_COLUMNS,
        key_fields=("source_id", "parser"),
        append=append,
    )


def write_manual_mast_observations_output(
    rows: list[ManualMastObservation],
    output_dir: Path,
    *,
    append: bool = False,
) -> Path:
    return _write_rows(
        rows,
        output_dir / "manual_mast_observations_county_year.csv",
        MANUAL_MAST_OBSERVATION_COLUMNS,
        key_fields=("county_fips", "year", "source_id"),
        append=append,
    )


def _write_rows(
    rows: list[object],
    output_path: Path,
    fieldnames: list[str],
    *,
    key_fields: tuple[str, ...],
    append: bool,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = [_record_from_row(row) for row in rows]
    if append and output_path.exists():
        records = [*_read_existing_records(output_path), *records]
    keyed = {_record_key(record, key_fields): record for record in records}
    ordered = sorted(keyed.values(), key=lambda record: _record_key(record, key_fields))
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ordered)
    return output_path


def _record_from_row(row: object) -> dict[str, object]:
    record = asdict(row)
    if "county_fips" in record:
        record["county_fips"] = str(record["county_fips"]).zfill(5)
    return record


def _read_existing_records(output_path: Path) -> list[dict[str, str]]:
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _record_key(record: dict[str, object], key_fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(record[field]) for field in key_fields)
```

- [ ] **Step 4: Run mast tests and ruff**

Run:

```bash
.venv/bin/python -m pytest tests/test_mast_acorn.py -q
.venv/bin/python -m ruff check tickbiterisk/etl/mast_acorn.py tickbiterisk/etl/mast_acorn_build.py tests/test_mast_acorn.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 5: Commit mast/acorn writers**

Run:

```bash
git add tickbiterisk/etl/mast_acorn_build.py tests/test_mast_acorn.py
git commit -m "feat: write mast acorn outputs"
```

Expected: commit succeeds.

---

## Task 5: Mast/Acorn CLI

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_mast_acorn.py`

- [ ] **Step 1: Write failing mast/acorn CLI tests**

Create `tests/test_cli_mast_acorn.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.mast_acorn import MastAcornCountyYear, MastAcornExtractionSummary


runner = CliRunner()


def test_mast_acorn_command_writes_structured_and_summary_outputs(
    tmp_path, monkeypatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for year in [2017, 2020, 2021]:
        (raw_dir / f"maryland_dnr_wmd_mast_survey_{year}.pdf").write_bytes(b"%PDF")

    def fake_build(source_path, *, year, source_id, source_url, parser):
        return (
            [
                MastAcornCountyYear(
                    county_fips="24023",
                    county_name="Garrett County",
                    year=year,
                    region="Western Maryland",
                    mast_category="overall",
                    mast_index=82.5,
                    mast_rating="bumper",
                    acorn_index=77.0,
                    hard_mast_index=82.5,
                    soft_mast_index=41.0,
                    plots_observed=20,
                    expected_plots=20,
                    coverage_complete=True,
                    source_id=source_id,
                    source_url_hash="hash",
                    feature_quality_flags="western_maryland_only",
                    extracted_text_excerpt="excerpt",
                )
            ],
            MastAcornExtractionSummary(
                source_id=source_id,
                source_url_hash="hash",
                year=year,
                parser=parser,
                source_path=str(source_path),
                extraction_status="structured",
                structured_row_count=1,
                feature_quality_flags="",
                notes="ok",
                extracted_text_excerpt="excerpt",
            ),
        )

    monkeypatch.setattr("tickbiterisk.cli.build_mast_acorn_from_pdf", fake_build)

    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 3 mast/acorn row(s)" in result.stdout
    assert (tmp_path / "out" / "maryland_dnr_mast_acorn_county_year.csv").exists()
    assert (tmp_path / "out" / "maryland_dnr_mast_acorn_extraction_summary.csv").exists()


def test_mast_acorn_command_writes_manual_observations_when_provided(
    tmp_path, monkeypatch
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for year in [2017, 2020, 2021]:
        (raw_dir / f"maryland_dnr_wmd_mast_survey_{year}.pdf").write_bytes(b"%PDF")
    manual = tmp_path / "manual.csv"
    manual.write_text(
        "\\n".join(
            [
                "county_fips,county_name,year,mast_rating,observation_basis,observer_scope,source_id,feature_quality_flags,notes",
                "24003,Anne Arundel County,2025,bumper,heavy acorn fall,neighborhood,manual_aa_2025,,Not official",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tickbiterisk.cli.build_mast_acorn_from_pdf",
        lambda source_path, *, year, source_id, source_url, parser: (
            [],
            MastAcornExtractionSummary(
                source_id=source_id,
                source_url_hash="hash",
                year=year,
                parser=parser,
                source_path=str(source_path),
                extraction_status="no_supported_values",
                structured_row_count=0,
                feature_quality_flags="ocr_pending",
                notes="none",
                extracted_text_excerpt="",
            ),
        ),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "mast-acorn",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "out"),
            "--manual-observations-path",
            str(manual),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 1 manual mast observation row(s)" in result.stdout
    assert (tmp_path / "out" / "manual_mast_observations_county_year.csv").exists()
```

- [ ] **Step 2: Run mast CLI tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_mast_acorn.py -q
```

Expected: FAIL because `etl mast-acorn` and CLI imports do not exist.

- [ ] **Step 3: Wire CLI imports**

Modify `tickbiterisk/cli.py` imports:

```python
from tickbiterisk.etl.mast_acorn import (
    build_mast_acorn_from_pdf,
    read_manual_mast_observations,
)
from tickbiterisk.etl.mast_acorn_build import (
    write_manual_mast_observations_output,
    write_mast_acorn_output,
    write_mast_acorn_summary_output,
)
```

- [ ] **Step 4: Add mast-acorn CLI command**

Add command near ecology/contact commands:

```python
@etl_app.command("mast-acorn")
def mast_acorn(
    raw_dir: Path = typer.Option(
        Path("data/raw/ecology/mast"),
        help="Raw directory containing Maryland DNR mast/acorn PDFs.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/mast"),
        help="Output directory for mast/acorn ETL artifacts.",
    ),
    parser: str = typer.Option(
        "pypdfium",
        help="PDF parser: pypdfium or docling.",
    ),
    manual_observations_path: Path | None = typer.Option(
        None,
        help="Optional manual mast observation CSV.",
    ),
) -> None:
    if parser not in {"pypdfium", "docling"}:
        raise typer.BadParameter("parser must be pypdfium or docling")
    rows = []
    summaries = []
    for source in MARYLAND_DNR_MAST_REPORT_URLS:
        source_file = raw_dir / Path(source.raw_relative_path).name
        if not source_file.exists():
            raise typer.BadParameter(f"mast source file not found: {source_file}")
        source_rows, summary = build_mast_acorn_from_pdf(
            source_file,
            year=source.year,
            source_id=source.source_id,
            source_url=source.url,
            parser=parser,
        )
        rows.extend(source_rows)
        summaries.append(summary)
    rows_output = write_mast_acorn_output(rows, output_dir)
    summary_output = write_mast_acorn_summary_output(summaries, output_dir)
    typer.echo(f"Wrote {len(rows)} mast/acorn row(s) to {rows_output}")
    typer.echo(f"Wrote {len(summaries)} mast/acorn extraction summary row(s) to {summary_output}")
    if manual_observations_path is not None:
        manual_rows = read_manual_mast_observations(manual_observations_path)
        manual_output = write_manual_mast_observations_output(manual_rows, output_dir)
        typer.echo(f"Wrote {len(manual_rows)} manual mast observation row(s) to {manual_output}")
```

Also import `MARYLAND_DNR_MAST_REPORT_URLS` from `tickbiterisk.etl.ecology_sources` if it is not already imported.

- [ ] **Step 5: Run mast CLI and focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_mast_acorn.py tests/test_mast_acorn.py -q
.venv/bin/python -m ruff check tickbiterisk/cli.py tests/test_cli_mast_acorn.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 6: Commit mast/acorn CLI**

Run:

```bash
git add tickbiterisk/cli.py tests/test_cli_mast_acorn.py
git commit -m "feat: add mast acorn cli"
```

Expected: commit succeeds.

---

## Task 6: Docs And Live Smoke

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`

- [ ] **Step 1: Run live contact-pressure smoke**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl contact-pressure \
  --building-permits-path build/etl/building-permits/maryland_building_permits_county_year.csv \
  --county-reference-path build/etl/county-reference/county_reference.csv \
  --population-path build/etl/population/county_population_year.csv \
  --output-dir build/etl/contact-pressure
```

Expected: command exits 0 and writes `build/etl/contact-pressure/contact_pressure_features_county_year.csv`. Record row count and count of rows flagged `missing_population`.

- [ ] **Step 2: Run live mast-acorn smoke**

Run:

```bash
.venv/bin/python -m tickbiterisk.cli etl mast-acorn \
  --raw-dir data/raw/ecology/mast \
  --output-dir build/etl/mast
```

Expected: command exits 0, writes structured mast output with header even if zero rows, and writes three extraction-summary rows. Record extraction statuses.

- [ ] **Step 3: Update README command block**

Add:

```bash
tickbiterisk etl contact-pressure --output-dir build/etl/contact-pressure
tickbiterisk etl mast-acorn --raw-dir data/raw/ecology/mast --output-dir build/etl/mast
```

Add one concise status sentence describing the live smoke outputs and caveats.

- [ ] **Step 4: Update data manifest**

Update `docs/data-manifest.md`:

- Mark `census_bps_county` as feeding `contact_pressure_features_county_year.csv`.
- Mark `maryland_dnr_mast_survey` as `parser_scaffolded` or `etl_supported_limited`, depending on live smoke status.
- Add a note that manual mast observations are optional, anecdotal, and not model-default.

- [ ] **Step 5: Update ETL pipeline docs**

Add sections after BPS:

```markdown
### 2.12  Contact Pressure Features (`tickbiterisk etl contact-pressure`)

* Reads normalized Census BPS, county reference, and county population CSVs.
* Writes `contact_pressure_features_county_year.csv`.
* Computes residential units authorized per square mile and per 100,000 residents.
* Carries `construction_proxy_only`, `missing_population`, `missing_land_area`, and historical coverage flags.

### 2.13  Mast/Acorn Features (`tickbiterisk etl mast-acorn`)

* Reads acquired Maryland DNR Western Maryland mast survey PDFs.
* Uses `pypdfium2` by default and Docling on request.
* Writes structured mast rows only when text supports them.
* Always writes an extraction summary so OCR-pending or low-confidence sources stay visible.
* Optional manual observations are stored separately and flagged anecdotal/not-model-default.
```

- [ ] **Step 6: Run focused docs/source tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_contact_pressure.py tests/test_cli_contact_pressure.py tests/test_mast_acorn.py tests/test_cli_mast_acorn.py -q
.venv/bin/python -m ruff check tickbiterisk/etl/contact_pressure.py tickbiterisk/etl/contact_pressure_build.py tickbiterisk/etl/mast_acorn.py tickbiterisk/etl/mast_acorn_build.py tickbiterisk/cli.py tests/test_contact_pressure.py tests/test_cli_contact_pressure.py tests/test_mast_acorn.py tests/test_cli_mast_acorn.py
```

Expected: PASS and `All checks passed!`.

- [ ] **Step 7: Commit docs and smoke status**

Run:

```bash
git add README.md docs/data-manifest.md docs/etl-pipeline.md
git commit -m "docs: catalog acquired ecology feature outputs"
```

Expected: commit succeeds.

---

## Task 7: Final Verification

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

- [ ] **Step 4: Final response must include**

```text
Implemented contact-pressure feature ETL from BPS, county reference, and population denominators.
Implemented mast/acorn extraction scaffolding with structured rows when defensible and extraction summaries for every PDF.
Manual mast observations are supported as anecdotal/not-model-default sidecar data only.
NLCD/CDL raster feature extraction remains pending.
```

---

## Plan Self-Review

- Spec coverage:
  - Contact-pressure output and quality flags are covered by Tasks 1, 2, and 6.
  - Mast/acorn structured rows and extraction summaries are covered by Tasks 3, 4, 5, and 6.
  - Manual mast observations are covered by Tasks 4, 5, and docs in Task 6.
  - No OCR dependency is added; pypdfium/Docling adapter pattern is used.
  - NLCD/CDL raster processing is explicitly not included.
- Placeholder scan:
  - No `TBD`, `TODO`, or "similar to previous" instructions remain.
  - Optional behavior has a concrete `--manual-observations-path` input and output file.
- Type consistency:
  - `ContactPressureFeature`, `MastAcornCountyYear`, `MastAcornExtractionSummary`, and `ManualMastObservation` are defined before use.
  - CLI command names match tests: `contact-pressure` and `mast-acorn`.
  - Default population path uses the actual repo output: `build/etl/population/county_population_year.csv`.
