from __future__ import annotations

import csv
import hashlib
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from tickbiterisk.modeling.spatial_neighbors import (
    CountyAdjacencyInputError,
    read_county_neighbors,
)


COMPARISON_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_stress_test,"
    "not_public_maryland_default,"
    "population_denominator_sensitive,"
    "localized_spatial_regime_research"
)
REGIME_METHOD = "adjacency_prior_history_similarity"
EVALUATION_MODE = "rolling_origin_prior_years"
TARGET_DEFINITION = "reported_lyme_incidence_per_100k"
FEATURE_SET = "localized_spatial_regime_prior_history"
MODEL_FEATURE_QUALITY_FLAGS = (
    "localized_spatial_regime_feature,"
    "forecast_safe_prior_history_spatial_regime,"
    "regional_county_adjacency_from_geojson,"
    "not_public_default"
)
REQUIRED_REGIONAL_INCIDENCE_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "population",
    "incidence_per_100k",
    "feature_quality_flags",
}


class RegionalSpatialRegimeInputError(ValueError):
    """Raised when regional spatial regime inputs are invalid."""


@dataclass(frozen=True)
class RegionalSpatialRegimeRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    regional_adjacency_path: str
    regional_adjacency_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    lookback_years: int
    max_prior_mean_difference: float
    max_prior_year_difference: float
    max_trend_difference: float
    regime_method: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    n_input_rows: int
    n_county_years: int
    n_summary_rows: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalSpatialRegimeCountyYear:
    run_id: str
    source_file_sha256: str
    regional_adjacency_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    spatial_regime_id: str
    spatial_regime_rank: int
    spatial_regime_member_count: int
    spatial_regime_neighbor_count: int
    feature_county_prior_mean_incidence_per_100k: float
    feature_county_prior_year_incidence_per_100k: float
    feature_county_prior_trend_incidence_per_100k: float
    feature_regime_trailing_mean_incidence_per_100k: float
    feature_regime_prior_year_mean_incidence_per_100k: float
    feature_regime_min_prior_mean_incidence_per_100k: float
    feature_regime_max_prior_mean_incidence_per_100k: float
    feature_regime_sd_prior_mean_incidence_per_100k: float
    train_start_year: int
    train_end_year: int
    train_year_count: int
    diagnostic_actual_incidence_per_100k: float | None
    diagnostic_actual_cases: int | None
    diagnostic_actual_population: int | None
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalSpatialRegimeSummary:
    run_id: str
    source_file_sha256: str
    regional_adjacency_sha256: str
    year: int
    spatial_regime_id: str
    spatial_regime_rank: int
    n_counties: int
    county_fips_list: str
    feature_regime_trailing_mean_incidence_per_100k: float
    feature_regime_prior_year_mean_incidence_per_100k: float
    feature_regime_min_prior_mean_incidence_per_100k: float
    feature_regime_max_prior_mean_incidence_per_100k: float
    feature_regime_sd_prior_mean_incidence_per_100k: float
    diagnostic_actual_regime_incidence_per_100k: float | None
    diagnostic_actual_regime_cases: int | None
    diagnostic_actual_regime_population: int | None
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalSpatialRegimeResult:
    run_id: str
    run: RegionalSpatialRegimeRun
    county_year_rows: list[RegionalSpatialRegimeCountyYear]
    summary_rows: list[RegionalSpatialRegimeSummary]


@dataclass(frozen=True)
class _IncidenceRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    population: int | None
    incidence_per_100k: float | None
    feature_quality_flags: str


@dataclass(frozen=True)
class _Signature:
    metadata_row: _IncidenceRow
    target_row: _IncidenceRow | None
    history: list[_IncidenceRow]
    prior_mean: float
    prior_year_incidence: float
    prior_trend: float


def build_regional_spatial_regimes(
    *,
    regional_incidence_path: Path,
    regional_adjacency_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 3,
    max_prior_mean_difference: float = 25.0,
    max_prior_year_difference: float = 25.0,
    max_trend_difference: float = 25.0,
) -> RegionalSpatialRegimeResult:
    if min_train_years < 1:
        raise RegionalSpatialRegimeInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise RegionalSpatialRegimeInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )
    _validate_threshold(max_prior_mean_difference, "max_prior_mean_difference")
    _validate_threshold(max_prior_year_difference, "max_prior_year_difference")
    _validate_threshold(max_trend_difference, "max_trend_difference")

    rows = _read_incidence_rows(regional_incidence_path)
    if not rows:
        raise RegionalSpatialRegimeInputError("regional incidence panel has no input rows")
    try:
        county_neighbors = read_county_neighbors(regional_adjacency_path)
    except CountyAdjacencyInputError as exc:
        raise RegionalSpatialRegimeInputError(str(exc)) from exc
    if not county_neighbors:
        raise RegionalSpatialRegimeInputError("regional adjacency has no usable edges")

    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise RegionalSpatialRegimeInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise RegionalSpatialRegimeInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise RegionalSpatialRegimeInputError(
            "start_year must be less than or equal to end_year"
        )

    rows_by_county = _group_by_county(rows)
    rows_by_year = _group_by_year(rows)
    source_file_sha256 = _sha256_file(regional_incidence_path)
    adjacency_sha256 = _sha256_file(regional_adjacency_path)
    run_id = (
        f"regional_spatial_regimes_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_lookback{lookback_years}_"
        f"mean{_slug_float(max_prior_mean_difference)}_"
        f"prior{_slug_float(max_prior_year_difference)}_"
        f"trend{_slug_float(max_trend_difference)}"
    )

    county_year_rows = []
    summary_rows = []
    for test_year in range(start_year, resolved_end_year + 1):
        signatures = _signatures(
            test_year=test_year,
            lookback_years=lookback_years,
            min_train_years=min_train_years,
            rows_by_county=rows_by_county,
            target_rows_by_county={
                row.county_fips: row for row in rows_by_year.get(test_year, [])
            },
        )
        if not signatures:
            continue
        components, regime_graph = _spatial_components(
            signatures=signatures,
            county_neighbors=county_neighbors,
            max_prior_mean_difference=max_prior_mean_difference,
            max_prior_year_difference=max_prior_year_difference,
            max_trend_difference=max_trend_difference,
        )
        year_county_rows, year_summary_rows = _rows_for_year(
            run_id=run_id,
            test_year=test_year,
            components=components,
            regime_graph=regime_graph,
            signatures=signatures,
            source_file_sha256=source_file_sha256,
            adjacency_sha256=adjacency_sha256,
        )
        county_year_rows.extend(year_county_rows)
        summary_rows.extend(year_summary_rows)

    county_year_rows = sorted(
        county_year_rows,
        key=lambda row: (row.year, row.spatial_regime_rank, row.county_fips),
    )
    summary_rows = sorted(
        summary_rows,
        key=lambda row: (row.year, row.spatial_regime_rank),
    )
    run = RegionalSpatialRegimeRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=source_file_sha256,
        regional_adjacency_path=str(regional_adjacency_path),
        regional_adjacency_sha256=adjacency_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        max_prior_mean_difference=max_prior_mean_difference,
        max_prior_year_difference=max_prior_year_difference,
        max_trend_difference=max_trend_difference,
        regime_method=REGIME_METHOD,
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        n_input_rows=len(rows),
        n_county_years=len(county_year_rows),
        n_summary_rows=len(summary_rows),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )
    return RegionalSpatialRegimeResult(
        run_id=run_id,
        run=run,
        county_year_rows=county_year_rows,
        summary_rows=summary_rows,
    )


def _read_incidence_rows(path: Path) -> list[_IncidenceRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_INCIDENCE_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalSpatialRegimeInputError(
                f"Missing regional incidence panel columns: {sorted(missing)}"
            )
        return sorted(
            [
                _IncidenceRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=str(row["county_fips"]).zfill(5),
                    county_name=str(row["county_name"]),
                    year=int(row["year"]),
                    total_cases=_parse_int(row["total_cases"]),
                    population=_parse_optional_int(row.get("population", "")),
                    incidence_per_100k=_parse_optional_float(
                        row.get("incidence_per_100k", "")
                    ),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _group_by_county(rows: list[_IncidenceRow]) -> dict[str, list[_IncidenceRow]]:
    grouped: dict[str, list[_IncidenceRow]] = {}
    for row in rows:
        grouped.setdefault(row.county_fips, []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: row.year)
        for county_fips, county_rows in grouped.items()
    }


def _group_by_year(rows: list[_IncidenceRow]) -> dict[int, list[_IncidenceRow]]:
    grouped: dict[int, list[_IncidenceRow]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(row)
    return grouped


def _signatures(
    *,
    test_year: int,
    lookback_years: int,
    min_train_years: int,
    rows_by_county: dict[str, list[_IncidenceRow]],
    target_rows_by_county: dict[str, _IncidenceRow],
) -> dict[str, _Signature]:
    signatures = {}
    train_window_start = test_year - lookback_years
    for county_fips, county_rows in rows_by_county.items():
        history = [
            prior
            for prior in county_rows
            if (
                train_window_start <= prior.year < test_year
                and prior.incidence_per_100k is not None
            )
        ]
        if len(history) < min_train_years:
            continue
        prior_year = next((prior for prior in history if prior.year == test_year - 1), None)
        if prior_year is None or prior_year.incidence_per_100k is None:
            continue
        ordered = sorted(history, key=lambda item: item.year)
        target_row = target_rows_by_county.get(county_fips)
        signatures[county_fips] = _Signature(
            metadata_row=target_row or ordered[-1],
            target_row=target_row,
            history=ordered,
            prior_mean=mean(_known_incidence(prior) for prior in ordered),
            prior_year_incidence=_known_incidence(prior_year),
            prior_trend=_known_incidence(ordered[-1]) - _known_incidence(ordered[0]),
        )
    return signatures


def _spatial_components(
    *,
    signatures: dict[str, _Signature],
    county_neighbors: dict[str, list[str]],
    max_prior_mean_difference: float,
    max_prior_year_difference: float,
    max_trend_difference: float,
) -> tuple[list[list[str]], dict[str, set[str]]]:
    graph = {county_fips: set() for county_fips in signatures}
    for county_fips, signature in signatures.items():
        for neighbor_fips in county_neighbors.get(county_fips, []):
            neighbor_signature = signatures.get(neighbor_fips)
            if neighbor_signature is None:
                continue
            if not _similar_signatures(
                signature,
                neighbor_signature,
                max_prior_mean_difference=max_prior_mean_difference,
                max_prior_year_difference=max_prior_year_difference,
                max_trend_difference=max_trend_difference,
            ):
                continue
            graph[county_fips].add(neighbor_fips)
            graph[neighbor_fips].add(county_fips)

    components = []
    seen = set()
    for county_fips in sorted(graph):
        if county_fips in seen:
            continue
        stack = [county_fips]
        component = []
        seen.add(county_fips)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(graph[current], reverse=True):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    components = sorted(
        components,
        key=lambda item: (
            mean(signatures[county_fips].prior_mean for county_fips in item),
            item[0],
        ),
    )
    return components, graph


def _similar_signatures(
    left: _Signature,
    right: _Signature,
    *,
    max_prior_mean_difference: float,
    max_prior_year_difference: float,
    max_trend_difference: float,
) -> bool:
    return (
        abs(left.prior_mean - right.prior_mean) <= max_prior_mean_difference
        and abs(left.prior_year_incidence - right.prior_year_incidence)
        <= max_prior_year_difference
        and abs(left.prior_trend - right.prior_trend) <= max_trend_difference
    )


def _rows_for_year(
    *,
    run_id: str,
    test_year: int,
    components: list[list[str]],
    regime_graph: dict[str, set[str]],
    signatures: dict[str, _Signature],
    source_file_sha256: str,
    adjacency_sha256: str,
) -> tuple[list[RegionalSpatialRegimeCountyYear], list[RegionalSpatialRegimeSummary]]:
    county_year_rows = []
    summary_rows = []
    for rank, component in enumerate(components, start=1):
        regime_id = f"{test_year}_regime_{rank:02d}"
        regime_signatures = [signatures[county_fips] for county_fips in component]
        prior_means = [signature.prior_mean for signature in regime_signatures]
        prior_year_values = [
            signature.prior_year_incidence for signature in regime_signatures
        ]
        observed_targets = [
            target_row
            for signature in regime_signatures
            if (target_row := _observed_target_row(signature)) is not None
        ]
        actual_values = [_known_incidence(row) for row in observed_targets]
        if len(observed_targets) == len(regime_signatures):
            actual_cases = sum(row.total_cases for row in observed_targets)
            actual_population = _sum_optional_population(
                row.population for row in observed_targets
            )
            actual_regime_incidence = _regime_actual_incidence(
                actual_cases=actual_cases,
                actual_population=actual_population,
                actual_values=actual_values,
            )
        else:
            actual_cases = None
            actual_population = None
            actual_regime_incidence = None
        summary_rows.append(
            RegionalSpatialRegimeSummary(
                run_id=run_id,
                source_file_sha256=source_file_sha256,
                regional_adjacency_sha256=adjacency_sha256,
                year=test_year,
                spatial_regime_id=regime_id,
                spatial_regime_rank=rank,
                n_counties=len(component),
                county_fips_list=";".join(component),
                feature_regime_trailing_mean_incidence_per_100k=_round(
                    mean(prior_means)
                ),
                feature_regime_prior_year_mean_incidence_per_100k=_round(
                    mean(prior_year_values)
                ),
                feature_regime_min_prior_mean_incidence_per_100k=_round(
                    min(prior_means)
                ),
                feature_regime_max_prior_mean_incidence_per_100k=_round(
                    max(prior_means)
                ),
                feature_regime_sd_prior_mean_incidence_per_100k=_round(
                    pstdev(prior_means) if len(prior_means) > 1 else 0.0
                ),
                diagnostic_actual_regime_incidence_per_100k=actual_regime_incidence,
                diagnostic_actual_regime_cases=actual_cases,
                diagnostic_actual_regime_population=actual_population,
                comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
            )
        )
        for signature in regime_signatures:
            metadata_row = signature.metadata_row
            observed_target = _observed_target_row(signature)
            county_year_rows.append(
                RegionalSpatialRegimeCountyYear(
                    run_id=run_id,
                    source_file_sha256=source_file_sha256,
                    regional_adjacency_sha256=adjacency_sha256,
                    state_fips=metadata_row.state_fips,
                    state_abbr=metadata_row.state_abbr,
                    state_name=metadata_row.state_name,
                    county_fips=metadata_row.county_fips,
                    county_name=metadata_row.county_name,
                    year=test_year,
                    spatial_regime_id=regime_id,
                    spatial_regime_rank=rank,
                    spatial_regime_member_count=len(component),
                    spatial_regime_neighbor_count=len(
                        regime_graph.get(metadata_row.county_fips, set())
                        & set(component)
                    ),
                    feature_county_prior_mean_incidence_per_100k=_round(
                        signature.prior_mean
                    ),
                    feature_county_prior_year_incidence_per_100k=_round(
                        signature.prior_year_incidence
                    ),
                    feature_county_prior_trend_incidence_per_100k=_round(
                        signature.prior_trend
                    ),
                    feature_regime_trailing_mean_incidence_per_100k=_round(
                        mean(prior_means)
                    ),
                    feature_regime_prior_year_mean_incidence_per_100k=_round(
                        mean(prior_year_values)
                    ),
                    feature_regime_min_prior_mean_incidence_per_100k=_round(
                        min(prior_means)
                    ),
                    feature_regime_max_prior_mean_incidence_per_100k=_round(
                        max(prior_means)
                    ),
                    feature_regime_sd_prior_mean_incidence_per_100k=_round(
                        pstdev(prior_means) if len(prior_means) > 1 else 0.0
                    ),
                    train_start_year=min(prior.year for prior in signature.history),
                    train_end_year=max(prior.year for prior in signature.history),
                    train_year_count=len(signature.history),
                    diagnostic_actual_incidence_per_100k=(
                        None
                        if observed_target is None
                        else _known_incidence(observed_target)
                    ),
                    diagnostic_actual_cases=(
                        None if observed_target is None else observed_target.total_cases
                    ),
                    diagnostic_actual_population=(
                        None if observed_target is None else observed_target.population
                    ),
                    model_feature_quality_flags=MODEL_FEATURE_QUALITY_FLAGS,
                    comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
                )
            )
    return county_year_rows, summary_rows


def _validate_threshold(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise RegionalSpatialRegimeInputError(f"{name} must be finite and non-negative")


def _known_incidence(row: _IncidenceRow) -> float:
    if row.incidence_per_100k is None:
        raise RegionalSpatialRegimeInputError(
            "internal error: missing incidence used as known value"
        )
    return row.incidence_per_100k


def _observed_target_row(signature: _Signature) -> _IncidenceRow | None:
    if (
        signature.target_row is None
        or signature.target_row.incidence_per_100k is None
    ):
        return None
    return signature.target_row


def _sum_optional_population(values: Iterable[int | None]) -> int | None:
    total = 0
    seen = False
    for value in values:
        seen = True
        if value is None:
            return None
        total += value
    return total if seen else None


def _regime_actual_incidence(
    *,
    actual_cases: int,
    actual_population: int | None,
    actual_values: list[float],
) -> float:
    if actual_population is not None and actual_population > 0:
        return _round(actual_cases / actual_population * 100_000)
    return _round(mean(actual_values))


def _parse_int(value: str) -> int:
    return int(float(value))


def _parse_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _parse_optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _round(value: float) -> float:
    return round(value, 6)


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
