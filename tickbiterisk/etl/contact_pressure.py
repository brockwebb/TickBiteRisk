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
    units_authorized_per_sqmi_prior_year: float | None = None
    units_authorized_per_100k_prior_year: float | None = None
    units_authorized_per_sqmi_trailing_3yr_mean: float | None = None
    units_authorized_per_100k_trailing_3yr_mean: float | None = None
    units_authorized_per_sqmi_yoy_change: float | None = None


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
    return _add_construction_lags(features)


def _add_construction_lags(
    features: list[ContactPressureFeature],
) -> list[ContactPressureFeature]:
    by_county_year = {(row.county_fips, row.year): row for row in features}
    enriched = []
    for row in features:
        prior = by_county_year.get((row.county_fips, row.year - 1))
        prior_sqmi = prior.units_authorized_per_sqmi if prior else None
        prior_100k = prior.units_authorized_per_100k if prior else None
        trailing_rows = [
            by_county_year.get((row.county_fips, prior_year))
            for prior_year in range(row.year - 3, row.year)
        ]
        trailing_sqmi_values = [
            prior_row.units_authorized_per_sqmi
            for prior_row in trailing_rows
            if prior_row and prior_row.units_authorized_per_sqmi is not None
        ]
        trailing_100k_values = [
            prior_row.units_authorized_per_100k
            for prior_row in trailing_rows
            if prior_row and prior_row.units_authorized_per_100k is not None
        ]
        yoy_change = None
        if row.units_authorized_per_sqmi is not None and prior_sqmi is not None:
            yoy_change = round(row.units_authorized_per_sqmi - prior_sqmi, 6)
        flags = row.feature_quality_flags.split(",") if row.feature_quality_flags else []
        if prior_sqmi is None or prior_100k is None:
            flags.append("missing_construction_lag")
        enriched.append(
            ContactPressureFeature(
                county_fips=row.county_fips,
                county_name=row.county_name,
                year=row.year,
                residential_units_authorized=row.residential_units_authorized,
                units_authorized_per_sqmi=row.units_authorized_per_sqmi,
                units_authorized_per_100k=row.units_authorized_per_100k,
                total_value_dollars=row.total_value_dollars,
                land_area_sqmi=row.land_area_sqmi,
                population=row.population,
                source_id=row.source_id,
                source_url_hash=row.source_url_hash,
                feature_quality_flags=",".join(flags),
                units_authorized_per_sqmi_prior_year=prior_sqmi,
                units_authorized_per_100k_prior_year=prior_100k,
                units_authorized_per_sqmi_trailing_3yr_mean=_mean(trailing_sqmi_values),
                units_authorized_per_100k_trailing_3yr_mean=_mean(trailing_100k_values),
                units_authorized_per_sqmi_yoy_change=yoy_change,
            )
        )
    return sorted(enriched, key=lambda item: (item.county_fips, item.year))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_building_permits(path: Path) -> list[dict[str, str]]:
    return _read_csv(path)


def _read_county_reference(path: Path) -> dict[str, dict[str, float | None]]:
    rows = {}
    for row in _read_csv(path):
        rows[str(row["county_fips"]).zfill(5)] = {
            "aland_sqmi": _parse_float_or_none(row["aland_sqmi"]),
        }
    return rows


def _read_population(path: Path) -> dict[tuple[str, int], int | None]:
    rows = {}
    for row in _read_csv(path):
        rows[(str(row["county_fips"]).zfill(5), int(row["year"]))] = _parse_int_or_none(
            row["population"]
        )
    return rows


def _year_counts(rows: list[dict[str, str]]) -> dict[int, int]:
    counts: dict[int, set[str]] = {}
    for row in rows:
        counts.setdefault(int(row["year"]), set()).add(str(row["county_fips"]).zfill(5))
    return {year: len(county_fips) for year, county_fips in counts.items()}


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _parse_int(value: str) -> int:
    return int(str(value).strip().replace(",", ""))


def _parse_int_or_none(value: str) -> int | None:
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return _parse_int(cleaned)


def _parse_float_or_none(value: str) -> float | None:
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return float(cleaned)
