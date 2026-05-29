from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.maryland import maryland_fips_set

DEFAULT_TICK_STATUS_STATE_FIPS = ("24",)
MIDATLANTIC_TICK_STATUS_STATE_FIPS = ("10", "11", "24", "42", "51", "54")


@dataclass(frozen=True)
class TickStatusCountyFeature:
    county_fips: str
    county_name: str
    ixodes_scapularis_status: str | None
    ixodes_pacificus_status: str | None
    borrelia_burgdorferi_status: str | None
    borrelia_mayonii_status: str | None
    borrelia_miyamotoi_status: str | None
    anaplasma_phagocytophilum_status: str | None
    ehrlichia_muris_eauclairensis_status: str | None
    babesia_microti_status: str | None
    powassan_virus_status: str | None
    amblyomma_americanum_status: str | None
    tick_status_source_ids: str
    tick_status_feature_quality_flags: str


def _norm_status(value: object) -> str:
    text = str(value).strip().lower().replace(" ", "_")
    if text in {"nan", "", "none"}:
        return "unknown"
    return text


def _clean_optional_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
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


def _filter_states(
    df: pd.DataFrame,
    fips_column: str,
    state_fips_values: Iterable[str] = DEFAULT_TICK_STATUS_STATE_FIPS,
) -> pd.DataFrame:
    filtered = df.copy()
    filtered[fips_column] = (
        filtered[fips_column].astype(str).str.split(".").str[0].str.zfill(5)
    )
    state_fips = {str(value).zfill(2) for value in state_fips_values}
    if state_fips == set(DEFAULT_TICK_STATUS_STATE_FIPS):
        return filtered[filtered[fips_column].isin(maryland_fips_set())].copy()
    return filtered[filtered[fips_column].str[:2].isin(state_fips)].copy()


def parse_ixodes_status(
    path: Path,
    source_id: str,
    state_fips_values: Iterable[str] = DEFAULT_TICK_STATUS_STATE_FIPS,
) -> list[dict[str, object]]:
    required = {
        "FIPSCode",
        "State",
        "County",
        "Ixodes_scapularis_County_Status",
        "Ixodes_pacificus_county_status",
    }
    df = _read_excel_sheet(path, "Ixodes records 2025", required)
    df = _filter_states(df, "FIPSCode", state_fips_values)
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
                "ixodes_scapularis_source": _clean_optional_text(
                    record.get("Ixodes_scapularis_data_source", "")
                ),
                "ixodes_pacificus_status": _norm_status(
                    record["Ixodes_pacificus_county_status"]
                ),
                "ixodes_pacificus_source": _clean_optional_text(
                    record.get("Ixodes_pacificus_data_source", "")
                ),
            }
        )
    return sorted(rows, key=lambda row: str(row["county_fips"]))


def parse_pathogen_status(
    path: Path,
    source_id: str,
    state_fips_values: Iterable[str] = DEFAULT_TICK_STATUS_STATE_FIPS,
) -> list[dict[str, object]]:
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
    df = _filter_states(df, "FIPS_Code", state_fips_values)
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
                "borrelia_mayonii_status": _norm_status(
                    record.get("Borrelia_mayonii_County_Status", "")
                ),
                "borrelia_miyamotoi_status": _norm_status(
                    record["Borrelia_miyamotoi_County_Status"]
                ),
                "anaplasma_phagocytophilum_status": _norm_status(
                    record[
                        "Anaplasma_phagocytophilum_human_active_variant_County_Status"
                    ]
                ),
                "ehrlichia_muris_eauclairensis_status": _norm_status(
                    record.get("Ehrlichia_muris_eauclairensis_County_Status", "")
                ),
                "babesia_microti_status": _norm_status(
                    record["Babesia_microti_County_Status"]
                ),
                "powassan_virus_status": _norm_status(
                    record["Powassan_virus_County_Status"]
                ),
            }
        )
    return sorted(rows, key=lambda row: str(row["county_fips"]))


def parse_lone_star_status(
    path: Path,
    source_id: str,
    state_fips_values: Iterable[str] = DEFAULT_TICK_STATUS_STATE_FIPS,
) -> list[dict[str, object]]:
    workbook_variants = [
        (
            "A. americanum Records 2025",
            {"FIPS", "State", "County", "2025 County Status of A. americanum"},
            "2025 County Status of A. americanum",
        ),
        (
            "A. americanum Records 2024",
            {"FIPS", "State", "County", "County Status of A. americanum"},
            "County Status of A. americanum",
        ),
    ]
    df = None
    status_column = ""
    errors = []
    for sheet_name, required, candidate_status_column in workbook_variants:
        try:
            df = _read_excel_sheet(path, sheet_name, required)
            status_column = candidate_status_column
            break
        except ValueError as exc:
            errors.append(str(exc))
    if df is None:
        raise ValueError(
            "Missing supported A. americanum workbook shape: " + "; ".join(errors)
        )
    df = _filter_states(df, "FIPS", state_fips_values)
    rows: list[dict[str, object]] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            {
                "source_id": source_id,
                "county_fips": record["FIPS"],
                "county_name": record["County"],
                "amblyomma_americanum_status": _norm_status(
                    record[status_column]
                ),
                "status_source": _clean_optional_text(record.get("Source", "")),
                "source_comments": _clean_optional_text(
                    record.get("Source Comments", "")
                ),
            }
        )
    return sorted(rows, key=lambda row: str(row["county_fips"]))


def build_tick_status_county_features(
    *,
    ixodes_rows: list[dict[str, object]],
    pathogen_rows: list[dict[str, object]],
    lone_star_rows: list[dict[str, object]],
) -> list[TickStatusCountyFeature]:
    ixodes = _index_by_county(ixodes_rows)
    pathogens = _index_by_county(pathogen_rows)
    lone_star = _index_by_county(lone_star_rows)
    county_fips_values = sorted(set(ixodes) | set(pathogens) | set(lone_star))
    rows = []
    for county_fips in county_fips_values:
        ixodes_row = ixodes.get(county_fips)
        pathogen_row = pathogens.get(county_fips)
        lone_star_row = lone_star.get(county_fips)
        status_values = [
            _text_or_none(ixodes_row, "ixodes_scapularis_status"),
            _text_or_none(ixodes_row, "ixodes_pacificus_status"),
            _text_or_none(pathogen_row, "borrelia_burgdorferi_status"),
            _text_or_none(pathogen_row, "borrelia_mayonii_status"),
            _text_or_none(pathogen_row, "borrelia_miyamotoi_status"),
            _text_or_none(pathogen_row, "anaplasma_phagocytophilum_status"),
            _text_or_none(pathogen_row, "ehrlichia_muris_eauclairensis_status"),
            _text_or_none(pathogen_row, "babesia_microti_status"),
            _text_or_none(pathogen_row, "powassan_virus_status"),
            _text_or_none(lone_star_row, "amblyomma_americanum_status"),
        ]
        rows.append(
            TickStatusCountyFeature(
                county_fips=county_fips,
                county_name=_county_name(ixodes_row, pathogen_row, lone_star_row),
                ixodes_scapularis_status=status_values[0],
                ixodes_pacificus_status=status_values[1],
                borrelia_burgdorferi_status=status_values[2],
                borrelia_mayonii_status=status_values[3],
                borrelia_miyamotoi_status=status_values[4],
                anaplasma_phagocytophilum_status=status_values[5],
                ehrlichia_muris_eauclairensis_status=status_values[6],
                babesia_microti_status=status_values[7],
                powassan_virus_status=status_values[8],
                amblyomma_americanum_status=status_values[9],
                tick_status_source_ids=",".join(
                    _source_ids(ixodes_row, pathogen_row, lone_star_row)
                ),
                tick_status_feature_quality_flags=",".join(
                    _feature_quality_flags(
                        status_values,
                        ixodes_missing=ixodes_row is None,
                        pathogen_missing=pathogen_row is None,
                        lone_star_missing=lone_star_row is None,
                    )
                ),
            )
        )
    return rows


def _index_by_county(
    rows: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    return {str(row["county_fips"]).zfill(5): row for row in rows}


def _county_name(*rows: dict[str, object] | None) -> str:
    for row in rows:
        if row is not None:
            return str(row.get("county_name", ""))
    return ""


def _source_ids(*rows: dict[str, object] | None) -> list[str]:
    return [
        source_id
        for row in rows
        if row is not None and (source_id := str(row.get("source_id", "")).strip())
    ]


def _feature_quality_flags(
    status_values: list[str | None],
    *,
    ixodes_missing: bool,
    pathogen_missing: bool,
    lone_star_missing: bool,
) -> list[str]:
    flags = [
        "current_status_retrospective_proxy",
        "status_only_not_prevalence",
    ]
    if any(value == "no_records" for value in status_values):
        flags.append("no_records_not_absence")
    if ixodes_missing:
        flags.append("missing_ixodes_status")
    if pathogen_missing:
        flags.append("missing_pathogen_status")
    if lone_star_missing:
        flags.append("missing_lone_star_status")
    return flags


def _text_or_none(row: dict[str, object] | None, column: str) -> str | None:
    if row is None:
        return None
    value = str(row.get(column, "")).strip()
    return value or None
