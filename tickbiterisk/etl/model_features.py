from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelCountyYearFeature:
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    confirmed_cases: int | None
    probable_cases: int | None
    population: int
    lyme_incidence_per_100k: float
    log_population_offset: float
    lyme_canonical_source_id: str
    lyme_reconciliation_status: str
    lyme_data_quality_flags: str
    weather_weeks_observed: int
    weather_complete_week_count: int
    weather_days_observed: float | None
    weather_expected_days: float | None
    weather_observation_ratio: float | None
    weather_days_above_40f: float | None
    weather_days_50_65f: float | None
    weather_days_70_85f: float | None
    weather_degree_days_above_40f: float | None
    weather_freeze_thaw_days: float | None
    weather_precip_total_mm: float | None
    weather_snowfall_total_mm: float | None
    weather_precip_days: float | None
    weather_dry_spell_max_days: int | None
    weather_temp_mean_f: float | None
    weather_precip_mean_mm: float | None
    weather_temp_anomaly_vs_10yr: float | None
    weather_precip_anomaly_vs_10yr: float | None
    tick_season_days_above_40f: float | None
    tick_season_days_70_85f: float | None
    tick_season_precip_total_mm: float | None
    spring_days_above_40f: float | None
    summer_days_70_85f: float | None
    weather_feature_quality_flags: str
    residential_units_authorized: int | None
    units_authorized_per_sqmi: float | None
    units_authorized_per_100k: float | None
    units_authorized_per_sqmi_prior_year: float | None
    units_authorized_per_100k_prior_year: float | None
    units_authorized_per_sqmi_trailing_3yr_mean: float | None
    units_authorized_per_100k_trailing_3yr_mean: float | None
    units_authorized_per_sqmi_yoy_change: float | None
    contact_pressure_total_value_dollars: int | None
    contact_pressure_feature_quality_flags: str | None
    deer_total_harvest_prior_season: int | None
    deer_harvest_per_sqmi_prior_season: float | None
    deer_is_derived_total: bool | None
    mast_index_prior_year: float | None
    acorn_index_prior_year: float | None
    hard_mast_index_prior_year: float | None
    soft_mast_index_prior_year: float | None
    black_oak_acorns_per_branch_prior_year: float | None
    white_oak_acorns_per_branch_prior_year: float | None
    unit_average_acorns_per_branch_prior_year: float | None
    white_oak_subjective_crown_pct_prior_year: float | None
    black_oak_subjective_crown_pct_prior_year: float | None
    mast_coverage_complete_prior_year: bool | None
    mast_source_ids_prior_year: str | None
    mast_source_report_year_prior_year: int | None
    mast_parser_method_prior_year: str | None
    mast_extraction_confidence_prior_year: str | None
    mast_feature_quality_flags_prior_year: str | None
    ixodes_scapularis_status: str | None
    ixodes_pacificus_status: str | None
    borrelia_burgdorferi_status: str | None
    borrelia_miyamotoi_status: str | None
    anaplasma_phagocytophilum_status: str | None
    babesia_microti_status: str | None
    powassan_virus_status: str | None
    amblyomma_americanum_status: str | None
    tick_status_source_ids: str | None
    tick_status_feature_quality_flags: str | None
    model_feature_quality_flags: str
    usdm_week_count: int | None = None
    usdm_dsci_mean: float | None = None
    usdm_dsci_max: float | None = None
    usdm_weeks_d0_or_worse: int | None = None
    usdm_weeks_d1_or_worse: int | None = None
    usdm_weeks_d2_or_worse: int | None = None
    usdm_tick_season_week_count: int | None = None
    usdm_tick_season_dsci_mean: float | None = None
    usdm_tick_season_weeks_d1_or_worse: int | None = None
    usdm_source_ids: str | None = None
    usdm_feature_quality_flags: str | None = None
    usdm_prior_year_week_count: int | None = None
    usdm_prior_year_dsci_mean: float | None = None
    usdm_prior_year_dsci_max: float | None = None
    usdm_prior_year_weeks_d0_or_worse: int | None = None
    usdm_prior_year_weeks_d1_or_worse: int | None = None
    usdm_prior_year_weeks_d2_or_worse: int | None = None
    usdm_prior_year_tick_season_week_count: int | None = None
    usdm_prior_year_tick_season_dsci_mean: float | None = None
    usdm_prior_year_tick_season_weeks_d1_or_worse: int | None = None
    usdm_prior_year_source_ids: str | None = None
    usdm_prior_year_feature_quality_flags: str | None = None
    forest_pct: float | None = None
    forest_woody_wetland_pct: float | None = None
    wetland_pct: float | None = None
    emergent_wetland_pct: float | None = None
    developed_pct: float | None = None
    impervious_pct: float | None = None
    agriculture_pct: float | None = None
    pasture_hay_pct: float | None = None
    cultivated_crop_pct: float | None = None
    riparian_natural_45m_pct: float | None = None
    riparian_forest_45m_pct: float | None = None
    riparian_forest_woody_wetland_45m_pct: float | None = None
    natural_land_cover_index: float | None = None
    enviroatlas_source_url_hash: str | None = None
    enviroatlas_feature_quality_flags: str | None = None
    oni_prior_year_season_count: int | None = None
    oni_prior_year_mean_anomaly_c: float | None = None
    oni_prior_year_max_anomaly_c: float | None = None
    oni_prior_year_min_anomaly_c: float | None = None
    oni_prior_year_el_nino_season_count: int | None = None
    oni_prior_year_la_nina_season_count: int | None = None
    enso_source_ids: str | None = None
    enso_source_url_hashes: str | None = None
    enso_feature_quality_flags: str | None = None


def build_model_feature_matrix(
    *,
    lyme_outcomes_path: Path,
    population_path: Path,
    weather_weekly_path: Path,
    contact_pressure_path: Path | None = None,
    deer_harvest_path: Path | None = None,
    mast_acorn_path: Path | None = None,
    usdm_drought_path: Path | None = None,
    enviroatlas_habitat_path: Path | None = None,
    enso_oni_path: Path | None = None,
    tick_status_path: Path | None = None,
) -> list[ModelCountyYearFeature]:
    population = _read_population(population_path)
    weather = _aggregate_weather_weekly(weather_weekly_path)
    contact = _read_contact_pressure(contact_pressure_path)
    deer = _read_deer_harvest(deer_harvest_path)
    mast = _read_mast_acorn(mast_acorn_path)
    drought = _read_usdm_drought(usdm_drought_path)
    habitat = _read_enviroatlas_habitat(enviroatlas_habitat_path)
    enso = _read_enso_oni(enso_oni_path)
    tick_status = _read_tick_status(tick_status_path)
    tick_status_enabled = tick_status_path is not None
    mast_enabled = mast_acorn_path is not None
    drought_enabled = usdm_drought_path is not None
    habitat_enabled = enviroatlas_habitat_path is not None
    enso_enabled = enso_oni_path is not None

    rows = []
    for lyme in _read_csv(lyme_outcomes_path):
        county_fips = str(lyme["county_fips"]).zfill(5)
        year = int(lyme["year"])
        population_row = population.get((county_fips, year))
        weather_row = weather.get((county_fips, year))
        if population_row is None or weather_row is None:
            continue
        pop = population_row["population"]
        if pop is None or pop <= 0:
            continue

        contact_row = contact.get((county_fips, year))
        deer_row = deer.get((county_fips, year))
        mast_row = mast.get((county_fips, year))
        drought_row = drought.get((county_fips, year))
        drought_prior_year_row = drought.get((county_fips, year - 1))
        habitat_row = habitat.get(county_fips)
        enso_row = enso.get(year)
        tick_status_row = tick_status.get(county_fips)
        total_cases = _parse_int(lyme["total_cases"])
        weather_ratio = weather_row["weather_observation_ratio"]
        flags = _model_quality_flags(
            lyme_flags=str(lyme.get("data_quality_flags", "")),
            reconciliation_status=str(lyme.get("reconciliation_status", "")),
            weather_observation_ratio=weather_ratio,
            contact_missing=contact_row is None,
            contact_flags=_contact_quality_flags(contact_row),
            deer_missing=deer_row is None,
            deer_is_derived_total=(
                None if deer_row is None else deer_row["deer_is_derived_total"]
            ),
            mast_missing=mast_enabled and mast_row is None,
            mast_flags=_mast_quality_flags(mast_row),
            drought_missing=drought_enabled and drought_row is None,
            drought_flags=_drought_quality_flags(drought_row),
            drought_prior_year_missing=(
                drought_enabled and drought_prior_year_row is None
            ),
            drought_prior_year_flags=_drought_quality_flags(drought_prior_year_row),
            habitat_missing=habitat_enabled and habitat_row is None,
            habitat_flags=_habitat_quality_flags(habitat_row),
            enso_missing=enso_enabled and enso_row is None,
            enso_flags=_enso_quality_flags(enso_row),
            tick_status_missing=tick_status_enabled and tick_status_row is None,
            tick_status_flags=_tick_status_quality_flags(tick_status_row),
        )
        rows.append(
            ModelCountyYearFeature(
                county_fips=county_fips,
                county_name=str(population_row["county_name"]),
                year=year,
                total_cases=total_cases,
                confirmed_cases=_parse_int_or_none(lyme.get("confirmed_cases", "")),
                probable_cases=_parse_int_or_none(lyme.get("probable_cases", "")),
                population=pop,
                lyme_incidence_per_100k=round(total_cases / pop * 100000, 6),
                log_population_offset=round(math.log(pop), 6),
                lyme_canonical_source_id=str(lyme.get("canonical_source_id", "")),
                lyme_reconciliation_status=str(
                    lyme.get("reconciliation_status", "")
                ),
                lyme_data_quality_flags=str(lyme.get("data_quality_flags", "")),
                **weather_row,
                residential_units_authorized=_contact_int(
                    contact_row, "residential_units_authorized"
                ),
                units_authorized_per_sqmi=_contact_float(
                    contact_row, "units_authorized_per_sqmi"
                ),
                units_authorized_per_100k=_contact_float(
                    contact_row, "units_authorized_per_100k"
                ),
                units_authorized_per_sqmi_prior_year=_contact_float(
                    contact_row, "units_authorized_per_sqmi_prior_year"
                ),
                units_authorized_per_100k_prior_year=_contact_float(
                    contact_row, "units_authorized_per_100k_prior_year"
                ),
                units_authorized_per_sqmi_trailing_3yr_mean=_contact_float(
                    contact_row, "units_authorized_per_sqmi_trailing_3yr_mean"
                ),
                units_authorized_per_100k_trailing_3yr_mean=_contact_float(
                    contact_row, "units_authorized_per_100k_trailing_3yr_mean"
                ),
                units_authorized_per_sqmi_yoy_change=_contact_float(
                    contact_row, "units_authorized_per_sqmi_yoy_change"
                ),
                contact_pressure_total_value_dollars=_contact_int(
                    contact_row, "total_value_dollars"
                ),
                contact_pressure_feature_quality_flags=(
                    None
                    if contact_row is None
                    else str(contact_row.get("feature_quality_flags", ""))
                ),
                deer_total_harvest_prior_season=(
                    None if deer_row is None else deer_row["deer_total_harvest"]
                ),
                deer_harvest_per_sqmi_prior_season=(
                    None if deer_row is None else deer_row["deer_harvest_per_sqmi"]
                ),
                deer_is_derived_total=(
                    None if deer_row is None else deer_row["deer_is_derived_total"]
                ),
                mast_index_prior_year=_mast_float(mast_row, "mast_index"),
                acorn_index_prior_year=_mast_float(mast_row, "acorn_index"),
                hard_mast_index_prior_year=_mast_float(mast_row, "hard_mast_index"),
                soft_mast_index_prior_year=_mast_float(mast_row, "soft_mast_index"),
                black_oak_acorns_per_branch_prior_year=_mast_float(
                    mast_row, "black_oak_acorns_per_branch"
                ),
                white_oak_acorns_per_branch_prior_year=_mast_float(
                    mast_row, "white_oak_acorns_per_branch"
                ),
                unit_average_acorns_per_branch_prior_year=_mast_float(
                    mast_row, "unit_average_acorns_per_branch"
                ),
                white_oak_subjective_crown_pct_prior_year=_mast_float(
                    mast_row, "white_oak_subjective_crown_pct"
                ),
                black_oak_subjective_crown_pct_prior_year=_mast_float(
                    mast_row, "black_oak_subjective_crown_pct"
                ),
                mast_coverage_complete_prior_year=_mast_bool(
                    mast_row, "coverage_complete"
                ),
                mast_source_ids_prior_year=_mast_text(mast_row, "source_id"),
                mast_source_report_year_prior_year=_mast_int(
                    mast_row, "source_report_year"
                ),
                mast_parser_method_prior_year=_mast_text(mast_row, "parser_method"),
                mast_extraction_confidence_prior_year=_mast_text(
                    mast_row, "extraction_confidence"
                ),
                mast_feature_quality_flags_prior_year=_mast_quality_flags(mast_row),
                ixodes_scapularis_status=_tick_status_text(
                    tick_status_row, "ixodes_scapularis_status"
                ),
                ixodes_pacificus_status=_tick_status_text(
                    tick_status_row, "ixodes_pacificus_status"
                ),
                borrelia_burgdorferi_status=_tick_status_text(
                    tick_status_row, "borrelia_burgdorferi_status"
                ),
                borrelia_miyamotoi_status=_tick_status_text(
                    tick_status_row, "borrelia_miyamotoi_status"
                ),
                anaplasma_phagocytophilum_status=_tick_status_text(
                    tick_status_row, "anaplasma_phagocytophilum_status"
                ),
                babesia_microti_status=_tick_status_text(
                    tick_status_row, "babesia_microti_status"
                ),
                powassan_virus_status=_tick_status_text(
                    tick_status_row, "powassan_virus_status"
                ),
                amblyomma_americanum_status=_tick_status_text(
                    tick_status_row, "amblyomma_americanum_status"
                ),
                tick_status_source_ids=_tick_status_text(
                    tick_status_row, "tick_status_source_ids"
                ),
                tick_status_feature_quality_flags=_tick_status_text(
                    tick_status_row, "tick_status_feature_quality_flags"
                ),
                model_feature_quality_flags=",".join(flags),
                usdm_week_count=_drought_int(drought_row, "usdm_week_count"),
                usdm_dsci_mean=_drought_float(drought_row, "usdm_dsci_mean"),
                usdm_dsci_max=_drought_float(drought_row, "usdm_dsci_max"),
                usdm_weeks_d0_or_worse=_drought_int(
                    drought_row, "usdm_weeks_d0_or_worse"
                ),
                usdm_weeks_d1_or_worse=_drought_int(
                    drought_row, "usdm_weeks_d1_or_worse"
                ),
                usdm_weeks_d2_or_worse=_drought_int(
                    drought_row, "usdm_weeks_d2_or_worse"
                ),
                usdm_tick_season_week_count=_drought_int(
                    drought_row, "usdm_tick_season_week_count"
                ),
                usdm_tick_season_dsci_mean=_drought_float(
                    drought_row, "usdm_tick_season_dsci_mean"
                ),
                usdm_tick_season_weeks_d1_or_worse=_drought_int(
                    drought_row, "usdm_tick_season_weeks_d1_or_worse"
                ),
                usdm_source_ids=_drought_text(drought_row, "source_ids"),
                usdm_feature_quality_flags=_drought_quality_flags(drought_row),
                usdm_prior_year_week_count=_drought_int(
                    drought_prior_year_row, "usdm_week_count"
                ),
                usdm_prior_year_dsci_mean=_drought_float(
                    drought_prior_year_row, "usdm_dsci_mean"
                ),
                usdm_prior_year_dsci_max=_drought_float(
                    drought_prior_year_row, "usdm_dsci_max"
                ),
                usdm_prior_year_weeks_d0_or_worse=_drought_int(
                    drought_prior_year_row, "usdm_weeks_d0_or_worse"
                ),
                usdm_prior_year_weeks_d1_or_worse=_drought_int(
                    drought_prior_year_row, "usdm_weeks_d1_or_worse"
                ),
                usdm_prior_year_weeks_d2_or_worse=_drought_int(
                    drought_prior_year_row, "usdm_weeks_d2_or_worse"
                ),
                usdm_prior_year_tick_season_week_count=_drought_int(
                    drought_prior_year_row, "usdm_tick_season_week_count"
                ),
                usdm_prior_year_tick_season_dsci_mean=_drought_float(
                    drought_prior_year_row, "usdm_tick_season_dsci_mean"
                ),
                usdm_prior_year_tick_season_weeks_d1_or_worse=_drought_int(
                    drought_prior_year_row,
                    "usdm_tick_season_weeks_d1_or_worse",
                ),
                usdm_prior_year_source_ids=_drought_text(
                    drought_prior_year_row, "source_ids"
                ),
                usdm_prior_year_feature_quality_flags=_drought_quality_flags(
                    drought_prior_year_row
                ),
                forest_pct=_habitat_float(habitat_row, "forest_pct"),
                forest_woody_wetland_pct=_habitat_float(
                    habitat_row, "forest_woody_wetland_pct"
                ),
                wetland_pct=_habitat_float(habitat_row, "wetland_pct"),
                emergent_wetland_pct=_habitat_float(
                    habitat_row, "emergent_wetland_pct"
                ),
                developed_pct=_habitat_float(habitat_row, "developed_pct"),
                impervious_pct=_habitat_float(habitat_row, "impervious_pct"),
                agriculture_pct=_habitat_float(habitat_row, "agriculture_pct"),
                pasture_hay_pct=_habitat_float(habitat_row, "pasture_hay_pct"),
                cultivated_crop_pct=_habitat_float(
                    habitat_row, "cultivated_crop_pct"
                ),
                riparian_natural_45m_pct=_habitat_float(
                    habitat_row, "riparian_natural_45m_pct"
                ),
                riparian_forest_45m_pct=_habitat_float(
                    habitat_row, "riparian_forest_45m_pct"
                ),
                riparian_forest_woody_wetland_45m_pct=_habitat_float(
                    habitat_row, "riparian_forest_woody_wetland_45m_pct"
                ),
                natural_land_cover_index=_habitat_float(
                    habitat_row, "natural_land_cover_index"
                ),
                enviroatlas_source_url_hash=_habitat_text(
                    habitat_row, "source_url_hash"
                ),
                enviroatlas_feature_quality_flags=_habitat_quality_flags(
                    habitat_row
                ),
                oni_prior_year_season_count=_enso_int(
                    enso_row, "oni_prior_year_season_count"
                ),
                oni_prior_year_mean_anomaly_c=_enso_float(
                    enso_row, "oni_prior_year_mean_anomaly_c"
                ),
                oni_prior_year_max_anomaly_c=_enso_float(
                    enso_row, "oni_prior_year_max_anomaly_c"
                ),
                oni_prior_year_min_anomaly_c=_enso_float(
                    enso_row, "oni_prior_year_min_anomaly_c"
                ),
                oni_prior_year_el_nino_season_count=_enso_int(
                    enso_row, "oni_prior_year_el_nino_season_count"
                ),
                oni_prior_year_la_nina_season_count=_enso_int(
                    enso_row, "oni_prior_year_la_nina_season_count"
                ),
                enso_source_ids=_enso_text(enso_row, "source_ids"),
                enso_source_url_hashes=_enso_text(enso_row, "source_url_hashes"),
                enso_feature_quality_flags=_enso_quality_flags(enso_row),
            )
        )
    return sorted(rows, key=lambda row: (row.county_fips, row.year))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_population(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    rows = {}
    for row in _read_csv(path):
        county_fips = str(row["county_fips"]).zfill(5)
        year = int(row["year"])
        rows[(county_fips, year)] = {
            "county_name": row["county_name"],
            "population": _parse_int_or_none(row["population"]),
        }
    return rows


def _aggregate_weather_weekly(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in _read_csv(path):
        county_fips = str(row["county_fips"]).zfill(5)
        for year, fragment in _calendar_year_fragments(row):
            grouped.setdefault((county_fips, year), []).append(fragment)
    return {key: _aggregate_weather_rows(rows) for key, rows in grouped.items()}


def _calendar_year_fragments(row: dict[str, str]) -> list[tuple[int, dict[str, str]]]:
    week_start = _parse_date(row.get("week_start_date", ""))
    week_end = _parse_week_end(row)
    total_days = (week_end - week_start).days + 1
    if total_days <= 0:
        raise ValueError(
            f"Weekly weather row ends before it starts: {week_start} to {week_end}"
        )
    fragments = []
    for year in range(week_start.year, week_end.year + 1):
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        overlap_start = max(week_start, year_start)
        overlap_end = min(week_end, year_end)
        overlap_days = (overlap_end - overlap_start).days + 1
        if overlap_days <= 0:
            continue
        fragment = dict(row)
        fragment["_calendar_year"] = str(year)
        fragment["_calendar_weight"] = str(overlap_days / total_days)
        fragments.append((year, fragment))
    return fragments


def _aggregate_weather_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    days_observed = _sum_int(rows, "days_observed")
    expected_days = _sum_int(rows, "expected_days")
    ratio = None
    if expected_days is not None and expected_days > 0 and days_observed is not None:
        ratio = round(days_observed / expected_days, 6)
    return {
        "weather_weeks_observed": len(rows),
        "weather_complete_week_count": sum(
            1 for row in rows if _parse_bool(row.get("week_complete"))
        ),
        "weather_days_observed": days_observed,
        "weather_expected_days": expected_days,
        "weather_observation_ratio": ratio,
        "weather_days_above_40f": _sum_int(rows, "days_above_40f"),
        "weather_days_50_65f": _sum_int(rows, "days_50_65f"),
        "weather_days_70_85f": _sum_int(rows, "days_70_85f"),
        "weather_degree_days_above_40f": _sum_float(rows, "degree_days_above_40f"),
        "weather_freeze_thaw_days": _sum_int(rows, "freeze_thaw_days"),
        "weather_precip_total_mm": _sum_float(rows, "precip_total_mm"),
        "weather_snowfall_total_mm": _sum_float(rows, "snowfall_total_mm"),
        "weather_precip_days": _sum_int(rows, "precip_days"),
        "weather_dry_spell_max_days": _max_int(rows, "dry_spell_max_days"),
        "weather_temp_mean_f": _weighted_mean(rows, "temp_mean_f"),
        "weather_precip_mean_mm": _weighted_mean(rows, "precip_mean_mm"),
        "weather_temp_anomaly_vs_10yr": _weighted_mean(
            rows, "temp_anomaly_vs_10yr"
        ),
        "weather_precip_anomaly_vs_10yr": _weighted_mean(
            rows, "precip_anomaly_vs_10yr"
        ),
        "tick_season_days_above_40f": _sum_int_for_months(
            rows, "days_above_40f", range(4, 10)
        ),
        "tick_season_days_70_85f": _sum_int_for_months(
            rows, "days_70_85f", range(4, 10)
        ),
        "tick_season_precip_total_mm": _sum_float_for_months(
            rows, "precip_total_mm", range(4, 10)
        ),
        "spring_days_above_40f": _sum_int_for_months(
            rows, "days_above_40f", range(3, 6)
        ),
        "summer_days_70_85f": _sum_int_for_months(
            rows, "days_70_85f", range(6, 9)
        ),
        "weather_feature_quality_flags": ",".join(
            sorted(
                {
                    flag
                    for row in rows
                    for flag in _split_flags(row.get("feature_quality_flags", ""))
                }
            )
        ),
    }


def _read_contact_pressure(
    path: Path | None,
) -> dict[tuple[str, int], dict[str, str]]:
    if path is None:
        return {}
    return {
        (str(row["county_fips"]).zfill(5), int(row["year"])): row
        for row in _read_csv(path)
    }


def _read_deer_harvest(path: Path | None) -> dict[tuple[str, int], dict[str, Any]]:
    if path is None:
        return {}
    rows = {}
    for row in _read_csv(path):
        if str(row.get("species", "")).strip() != "all_deer":
            continue
        county_fips = str(row["county_fips"]).zfill(5)
        model_year = int(row["season_start_year"]) + 1
        rows[(county_fips, model_year)] = {
            "deer_total_harvest": _parse_int_or_none(row.get("total_harvest", "")),
            "deer_harvest_per_sqmi": _parse_float_or_none(
                row.get("harvest_per_sqmi", "")
            ),
            "deer_is_derived_total": _parse_bool(row.get("is_derived_total")),
        }
    return rows


def _read_mast_acorn(path: Path | None) -> dict[tuple[str, int], dict[str, str]]:
    if path is None:
        return {}
    rows: dict[tuple[str, int], dict[str, str]] = {}
    for row in _read_csv(path):
        if str(row.get("mast_category", "")).strip() not in {
            "",
            "overall",
            "oak_acorn_abundance",
        }:
            continue
        county_fips = str(row["county_fips"]).zfill(5)
        observation_year = int(row["year"])
        model_year = observation_year + 1
        key = (county_fips, model_year)
        existing = rows.get(key)
        if existing is None or _mast_preferred_sort_key(row) > _mast_preferred_sort_key(
            existing
        ):
            rows[key] = row
    return rows


def _read_usdm_drought(
    path: Path | None,
) -> dict[tuple[str, int], dict[str, str]]:
    if path is None:
        return {}
    return {
        (str(row["county_fips"]).zfill(5), int(row["year"])): row
        for row in _read_csv(path)
    }


def _read_enviroatlas_habitat(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    return {
        str(row["county_fips"]).zfill(5): row
        for row in _read_csv(path)
    }


def _read_enso_oni(path: Path | None) -> dict[int, dict[str, str]]:
    if path is None:
        return {}
    return {
        int(row["model_year"]): row
        for row in _read_csv(path)
    }


def _mast_preferred_sort_key(row: dict[str, str]) -> tuple[int, str]:
    return (
        _parse_int_or_none(row.get("source_report_year", "")) or _parse_int(row["year"]),
        str(row.get("source_id", "")),
    )


def _read_tick_status(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    return {
        str(row["county_fips"]).zfill(5): row
        for row in _read_csv(path)
    }


def _model_quality_flags(
    *,
    lyme_flags: str,
    reconciliation_status: str,
    weather_observation_ratio: float | None,
    contact_missing: bool,
    contact_flags: str,
    deer_missing: bool,
    deer_is_derived_total: bool | None,
    mast_missing: bool,
    mast_flags: str,
    drought_missing: bool,
    drought_flags: str,
    drought_prior_year_missing: bool,
    drought_prior_year_flags: str,
    habitat_missing: bool,
    habitat_flags: str,
    enso_missing: bool,
    enso_flags: str,
    tick_status_missing: bool,
    tick_status_flags: str,
) -> list[str]:
    flags = _split_flags(lyme_flags)
    if reconciliation_status != "matched":
        flags.append("lyme_source_conflict")
    if weather_observation_ratio is not None and weather_observation_ratio < 0.95:
        flags.append("partial_weather_year")
    if contact_missing:
        flags.append("missing_contact_pressure")
    flags.extend(_split_flags(contact_flags))
    if deer_missing:
        flags.append("missing_deer_harvest_prior_season")
    if deer_is_derived_total:
        flags.append("deer_prior_season_derived_total")
    if mast_missing:
        flags.append("missing_mast_acorn_prior_year")
    flags.extend(_split_flags(mast_flags))
    if drought_missing:
        flags.append("missing_usdm_drought")
    flags.extend(_split_flags(drought_flags))
    if drought_prior_year_missing:
        flags.append("missing_usdm_drought_prior_year")
    flags.extend(_split_flags(drought_prior_year_flags))
    if habitat_missing:
        flags.append("missing_enviroatlas_habitat")
    flags.extend(_split_flags(habitat_flags))
    if enso_missing:
        flags.append("missing_enso_oni_prior_year")
    flags.extend(_split_flags(enso_flags))
    if tick_status_missing:
        flags.append("missing_tick_status")
    flags.extend(_split_flags(tick_status_flags))
    return _dedupe_preserve_order(flags)


def _contact_int(row: dict[str, str] | None, column: str) -> int | None:
    if row is None:
        return None
    return _parse_int_or_none(row.get(column, ""))


def _contact_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _parse_float_or_none(row.get(column, ""))


def _contact_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    return ",".join(_dedupe_preserve_order(_split_flags(row.get("feature_quality_flags", ""))))


def _tick_status_text(row: dict[str, str] | None, column: str) -> str | None:
    if row is None:
        return None
    text = str(row.get(column, "")).strip()
    return text or None


def _mast_text(row: dict[str, str] | None, column: str) -> str | None:
    if row is None:
        return None
    text = str(row.get(column, "")).strip()
    return text or None


def _mast_int(row: dict[str, str] | None, column: str) -> int | None:
    if row is None:
        return None
    return _parse_int_or_none(row.get(column, ""))


def _mast_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _parse_float_or_none(row.get(column, ""))


def _mast_bool(row: dict[str, str] | None, column: str) -> bool | None:
    if row is None or not str(row.get(column, "")).strip():
        return None
    return _parse_bool(row.get(column))


def _mast_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    return ",".join(_dedupe_preserve_order(_split_flags(row.get("feature_quality_flags", ""))))


def _drought_text(row: dict[str, str] | None, column: str) -> str | None:
    if row is None:
        return None
    text = str(row.get(column, "")).strip()
    return text or None


def _drought_int(row: dict[str, str] | None, column: str) -> int | None:
    if row is None:
        return None
    return _parse_int_or_none(row.get(column, ""))


def _drought_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _parse_float_or_none(row.get(column, ""))


def _drought_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    return ",".join(_dedupe_preserve_order(_split_flags(row.get("feature_quality_flags", ""))))


def _habitat_text(row: dict[str, str] | None, column: str) -> str | None:
    if row is None:
        return None
    text = str(row.get(column, "")).strip()
    return text or None


def _habitat_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _parse_float_or_none(row.get(column, ""))


def _habitat_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    return ",".join(_dedupe_preserve_order(_split_flags(row.get("feature_quality_flags", ""))))


def _enso_text(row: dict[str, str] | None, column: str) -> str | None:
    if row is None:
        return None
    text = str(row.get(column, "")).strip()
    return text or None


def _enso_int(row: dict[str, str] | None, column: str) -> int | None:
    if row is None:
        return None
    return _parse_int_or_none(row.get(column, ""))


def _enso_float(row: dict[str, str] | None, column: str) -> float | None:
    if row is None:
        return None
    return _parse_float_or_none(row.get(column, ""))


def _enso_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    return ",".join(_dedupe_preserve_order(_split_flags(row.get("feature_quality_flags", ""))))


def _tick_status_quality_flags(row: dict[str, str] | None) -> str:
    if row is None:
        return ""
    flags = _split_flags(row.get("tick_status_feature_quality_flags", ""))
    status_columns = [
        "ixodes_scapularis_status",
        "ixodes_pacificus_status",
        "borrelia_burgdorferi_status",
        "borrelia_miyamotoi_status",
        "anaplasma_phagocytophilum_status",
        "babesia_microti_status",
        "powassan_virus_status",
        "amblyomma_americanum_status",
    ]
    if any(str(row.get(column, "")).strip() == "no_records" for column in status_columns):
        flags.append("no_records_not_absence")
    return ",".join(_dedupe_preserve_order(flags))


def _sum_int(rows: list[dict[str, str]], column: str) -> float | None:
    return _sum_float(rows, column)


def _sum_float(rows: list[dict[str, str]], column: str) -> float | None:
    total = 0.0
    present = False
    for row in rows:
        value = _parse_float_or_none(row.get(column, ""))
        if value is None:
            continue
        total += value * _calendar_weight(row)
        present = True
    if not present:
        return None
    return _normalize_number(total)


def _max_int(rows: list[dict[str, str]], column: str) -> int | None:
    values = [
        min(value, _calendar_fragment_day_count(row))
        for row in rows
        if (value := _parse_int_or_none(row.get(column, ""))) is not None
    ]
    if not values:
        return None
    return max(values)


def _weighted_mean(rows: list[dict[str, str]], column: str) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = _parse_float_or_none(row.get(column, ""))
        weight = _parse_int_or_none(row.get("days_observed", ""))
        if value is None or weight is None or weight <= 0:
            continue
        adjusted_weight = weight * _calendar_weight(row)
        numerator += value * adjusted_weight
        denominator += adjusted_weight
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _sum_int_for_months(
    rows: list[dict[str, str]], column: str, months: range
) -> float | None:
    return _sum_float_for_months(rows, column, months)


def _sum_float_for_months(
    rows: list[dict[str, str]], column: str, months: range
) -> float | None:
    total = 0.0
    present = False
    for row in rows:
        value = _parse_float_or_none(row.get(column, ""))
        if value is None:
            continue
        weight = _month_weight(row, months)
        if weight <= 0:
            continue
        total += value * weight
        present = True
    if not present:
        return 0
    return _normalize_number(total)


def _month_weight(row: dict[str, str], months: range) -> float:
    month_set = set(months)
    fragment_start, fragment_end = _calendar_fragment_bounds(row)
    total_start = _parse_date(row.get("week_start_date", ""))
    total_end = _parse_week_end(row)
    total_days = (total_end - total_start).days + 1
    if total_days <= 0:
        return 0

    overlap_days = 0
    current = fragment_start
    while current <= fragment_end:
        if current.month in month_set:
            overlap_days += 1
        current += timedelta(days=1)
    return overlap_days / total_days


def _calendar_fragment_bounds(row: dict[str, str]) -> tuple[date, date]:
    week_start = _parse_date(row.get("week_start_date", ""))
    week_end = _parse_week_end(row)
    year = int(row.get("_calendar_year", week_start.year))
    return max(week_start, date(year, 1, 1)), min(week_end, date(year, 12, 31))


def _calendar_fragment_day_count(row: dict[str, str]) -> int:
    fragment_start, fragment_end = _calendar_fragment_bounds(row)
    return (fragment_end - fragment_start).days + 1


def _calendar_weight(row: dict[str, str]) -> float:
    return _parse_float_or_none(row.get("_calendar_weight")) or 1.0


def _parse_date(value: str) -> date:
    return date.fromisoformat(str(value).strip())


def _parse_week_end(row: dict[str, str]) -> date:
    value = row.get("week_end_date", "")
    if str(value).strip():
        return _parse_date(value)
    return _parse_date(row.get("week_start_date", "")) + timedelta(days=6)


def _normalize_number(value: float) -> float:
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def _split_flags(value: str | None) -> list[str]:
    if value is None:
        return []
    return [flag.strip() for flag in re.split(r"[;,]", value) if flag.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _parse_int(value: str) -> int:
    number = float(str(value).strip().replace(",", ""))
    if not number.is_integer():
        raise ValueError(f"Expected integer-like value, got {value!r}")
    return int(number)


def _parse_int_or_none(value: str | None) -> int | None:
    cleaned = "" if value is None else str(value).strip()
    if not cleaned:
        return None
    return _parse_int(cleaned)


def _parse_float_or_none(value: str | None) -> float | None:
    cleaned = "" if value is None else str(value).strip()
    if not cleaned or cleaned.lower() == "nan":
        return None
    return float(cleaned.replace(",", ""))


def _parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}
