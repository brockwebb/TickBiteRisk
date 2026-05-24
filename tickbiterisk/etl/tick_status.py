from __future__ import annotations

from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import maryland_fips_set


def _norm_status(value: object) -> str:
    text = str(value).strip().lower().replace(" ", "_")
    if text in {"nan", "", "none"}:
        return "unknown"
    return text


def _read_excel_sheet(
    path: Path, sheet_name: str, required_columns: set[str]
) -> pd.DataFrame:
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
                "ixodes_scapularis_status": _norm_status(
                    record["Ixodes_scapularis_County_Status"]
                ),
                "ixodes_scapularis_source": record.get(
                    "Ixodes_scapularis_data_source", ""
                ),
                "ixodes_pacificus_status": _norm_status(
                    record["Ixodes_pacificus_county_status"]
                ),
                "ixodes_pacificus_source": record.get(
                    "Ixodes_pacificus_data_source", ""
                ),
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
                "borrelia_burgdorferi_status": _norm_status(
                    record["Borrelia_burgdorferi_sensu_stricto_County_Status"]
                ),
                "borrelia_miyamotoi_status": _norm_status(
                    record["Borrelia_miyamotoi_County_Status"]
                ),
                "anaplasma_phagocytophilum_status": _norm_status(
                    record[
                        "Anaplasma_phagocytophilum_human_active_variant_County_Status"
                    ]
                ),
                "babesia_microti_status": _norm_status(
                    record["Babesia_microti_County_Status"]
                ),
                "powassan_virus_status": _norm_status(
                    record["Powassan_virus_County_Status"]
                ),
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
                "amblyomma_americanum_status": _norm_status(
                    record["County Status of A. americanum"]
                ),
                "status_source": record.get("Source", ""),
                "source_comments": record.get("Source Comments", ""),
            }
        )
    return rows
