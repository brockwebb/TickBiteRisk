from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import load_maryland_jurisdictions, maryland_fips_set


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
    if text.lower() in {"", "-", "n", "nan", "suppressed", "u"}:
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
        if column.lower().startswith("cases")
        and column.lower().replace("cases", "").isdigit()
    ]
    md_fips = maryland_fips_set()
    rows: list[LymeCountyYearValue] = []
    for record in md.to_dict(orient="records"):
        county_fips = f"{int(record['stcode']):02d}{int(record['ctycode']):03d}"
        if county_fips not in md_fips:
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
    md = md[md["fips"].isin(maryland_fips_set())].copy()
    md["year_int"] = md["year"].map(lambda value: int(float(value)))
    md = md[(md["year_int"] >= 2000) & (md["year_int"] <= 2021)].copy()
    md["confirmed_int"] = md["Lyme_Confirmed_Cases"].map(_frequency_to_int)
    md["probable_int"] = md["Lyme_Probable_Cases"].map(_frequency_to_int)
    md["total_int"] = md["Lyme_Confirmed_Probable_Cases"].map(_frequency_to_int)

    rows: list[LymeCountyYearValue] = []
    for (fips, year), group in md.groupby(["fips", "year_int"]):
        totals = {int(value) for value in group["total_int"]}
        if len(totals) > 1:
            raise ValueError(
                "Conflicting CDC Lyme geodata totals for county FIPS "
                f"{fips} year {int(year)}: {sorted(totals)}"
            )

        components = {
            (int(row.confirmed_int), int(row.probable_int))
            for row in group.itertuples(index=False)
        }
        if len(components) == 1:
            confirmed, probable = next(iter(components))
        else:
            confirmed = None
            probable = None

        rows.append(
            LymeCountyYearValue(
                source_id=source_id,
                county_fips=fips,
                year=int(year),
                confirmed_cases=confirmed,
                probable_cases=probable,
                total_cases=totals.pop(),
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))


def parse_mdh_lyme_pdf(path: Path, source_id: str) -> list[LymeCountyYearValue]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency is present in CI
        raise ValueError("pypdfium2 is required to parse the MDH Lyme PDF") from exc

    pdf = pdfium.PdfDocument(path)
    text_parts = []
    for page in pdf:
        text_parts.append(page.get_textpage().get_text_range())
    return parse_mdh_lyme_pdf_text("\n".join(text_parts), source_id=source_id)


def parse_mdh_lyme_pdf_text(text: str, source_id: str) -> list[LymeCountyYearValue]:
    county_lookup = _mdh_county_name_lookup()
    rows: list[LymeCountyYearValue] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line or line.startswith(("Lyme Disease", "2013 ", "JURISDICTION")):
            continue
        if line.startswith(("Statewide total", "Incidence per", "^ ", "* ", "Revised ")):
            continue
        parts = line.split()
        numeric_start = next(
            (index for index, part in enumerate(parts) if _is_number_token(part)),
            None,
        )
        if numeric_start is None:
            continue
        county_name = " ".join(parts[:numeric_start])
        county_fips = county_lookup.get(county_name)
        if county_fips is None:
            continue
        numeric_values = [_frequency_to_int(part) for part in parts[numeric_start:-1]]
        if len(numeric_values) != 12:
            raise ValueError(
                f"Expected 12 MDH Lyme year values for {county_name}, "
                f"found {len(numeric_values)}"
            )
        for offset, total in enumerate(numeric_values):
            year = 2013 + offset
            rows.append(
                LymeCountyYearValue(
                    source_id=source_id,
                    county_fips=county_fips,
                    year=year,
                    confirmed_cases=None,
                    probable_cases=total if year == 2024 else None,
                    total_cases=total,
                )
            )
    if not rows:
        raise ValueError("No MDH Lyme county-year rows parsed from PDF text")
    return sorted(rows, key=lambda row: (row.county_fips, row.year, row.source_id))


def _mdh_county_name_lookup() -> dict[str, str]:
    lookup = {}
    for jurisdiction in load_maryland_jurisdictions():
        county_name = jurisdiction.county_name
        mdh_name = county_name.removesuffix(" County")
        lookup[mdh_name] = jurisdiction.county_fips
    return lookup


def _is_number_token(value: str) -> bool:
    try:
        float(str(value).replace(",", ""))
        return True
    except ValueError:
        return False
