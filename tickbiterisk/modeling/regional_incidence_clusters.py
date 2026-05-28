from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev


COMPARISON_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_stress_test,"
    "not_public_maryland_default,"
    "population_denominator_sensitive,"
    "cluster_diagnostic_not_public_default"
)
CLUSTERING_METHOD = "prior_mean_1d_kmeans"
EVALUATION_MODE = "rolling_origin_prior_years"
TARGET_DEFINITION = "reported_lyme_incidence_per_100k"
FEATURE_SET = "prior_incidence_cluster_capacity_bands"
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


class RegionalIncidenceClusterInputError(ValueError):
    """Raised when regional incidence cluster inputs are invalid."""


@dataclass(frozen=True)
class RegionalIncidenceClusterRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    lookback_years: int
    n_clusters: int
    clustering_method: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    n_input_rows: int
    n_county_years: int
    n_summary_rows: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceClusterCountyYear:
    run_id: str
    source_file_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    cluster_id: str
    cluster_rank: int
    cluster_label: str
    cluster_centroid_prior_mean_incidence_per_100k: float
    feature_prior_mean_incidence_per_100k: float
    feature_prior_min_incidence_per_100k: float
    feature_prior_max_incidence_per_100k: float
    feature_prior_sd_incidence_per_100k: float
    feature_prior_year_incidence_per_100k: float
    train_start_year: int
    train_end_year: int
    train_year_count: int
    actual_incidence_per_100k: float
    actual_cases: int
    actual_population: int | None
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceClusterSummary:
    run_id: str
    source_file_sha256: str
    year: int
    cluster_id: str
    cluster_rank: int
    cluster_label: str
    n_counties: int
    feature_prior_cluster_min_incidence_per_100k: float
    feature_prior_cluster_mean_incidence_per_100k: float
    feature_prior_cluster_max_incidence_per_100k: float
    feature_prior_cluster_sd_incidence_per_100k: float
    diagnostic_actual_cluster_incidence_per_100k: float
    diagnostic_actual_cluster_cases: int
    diagnostic_actual_cluster_population: int | None
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalIncidenceClusterResult:
    run_id: str
    run: RegionalIncidenceClusterRun
    county_year_rows: list[RegionalIncidenceClusterCountyYear]
    summary_rows: list[RegionalIncidenceClusterSummary]


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
class _Candidate:
    row: _IncidenceRow
    county_history: list[_IncidenceRow]
    prior_year_row: _IncidenceRow
    prior_mean: float
    prior_min: float
    prior_max: float
    prior_sd: float


@dataclass(frozen=True)
class _Assignment:
    candidate: _Candidate
    cluster_rank: int
    cluster_label: str
    cluster_centroid: float


def build_regional_incidence_clusters(
    *,
    regional_incidence_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 5,
    n_clusters: int = 4,
) -> RegionalIncidenceClusterResult:
    if min_train_years < 1:
        raise RegionalIncidenceClusterInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise RegionalIncidenceClusterInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )
    if n_clusters < 2:
        raise RegionalIncidenceClusterInputError("n_clusters must be at least 2")

    rows = _read_incidence_rows(regional_incidence_path)
    if not rows:
        raise RegionalIncidenceClusterInputError(
            "regional incidence panel has no input rows"
        )
    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise RegionalIncidenceClusterInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise RegionalIncidenceClusterInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise RegionalIncidenceClusterInputError(
            "start_year must be less than or equal to end_year"
        )

    rows_by_county = _group_by_county(rows)
    rows_by_year = _group_by_year(rows)
    rows_by_county_year = {(row.county_fips, row.year): row for row in rows}
    source_file_sha256 = _sha256_file(regional_incidence_path)
    run_id = (
        f"regional_incidence_clusters_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_lookback{lookback_years}_clusters{n_clusters}"
    )

    county_year_rows = []
    summary_rows = []
    for test_year in range(start_year, resolved_end_year + 1):
        candidates = _candidate_rows(
            test_year=test_year,
            lookback_years=lookback_years,
            min_train_years=min_train_years,
            rows_by_county=rows_by_county,
            rows_by_year=rows_by_year,
            rows_by_county_year=rows_by_county_year,
        )
        if len(candidates) < 2:
            continue
        assignments = _assign_clusters(candidates, n_clusters=n_clusters)
        county_year_rows.extend(
            _county_year_row(
                run_id=run_id,
                assignment=assignment,
                source_file_sha256=source_file_sha256,
            )
            for assignment in assignments
        )
        summary_rows.extend(
            _summary_rows(
                run_id=run_id,
                assignments=assignments,
                source_file_sha256=source_file_sha256,
            )
        )

    county_year_rows = sorted(
        county_year_rows,
        key=lambda row: (row.year, row.cluster_rank, row.county_fips),
    )
    summary_rows = sorted(
        summary_rows,
        key=lambda row: (row.year, row.cluster_rank),
    )
    run = RegionalIncidenceClusterRun(
        run_id=run_id,
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=source_file_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        n_clusters=n_clusters,
        clustering_method=CLUSTERING_METHOD,
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        n_input_rows=len(rows),
        n_county_years=len(county_year_rows),
        n_summary_rows=len(summary_rows),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )
    return RegionalIncidenceClusterResult(
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
            raise RegionalIncidenceClusterInputError(
                f"Missing regional incidence panel columns: {sorted(missing)}"
            )
        return sorted(
            [
                _IncidenceRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row["state_abbr"]),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
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


def _candidate_rows(
    *,
    test_year: int,
    lookback_years: int,
    min_train_years: int,
    rows_by_county: dict[str, list[_IncidenceRow]],
    rows_by_year: dict[int, list[_IncidenceRow]],
    rows_by_county_year: dict[tuple[str, int], _IncidenceRow],
) -> list[_Candidate]:
    candidates = []
    train_window_start = test_year - lookback_years
    for row in rows_by_year.get(test_year, []):
        if row.incidence_per_100k is None:
            continue
        county_history = [
            prior
            for prior in rows_by_county[row.county_fips]
            if (
                train_window_start <= prior.year < test_year
                and prior.incidence_per_100k is not None
            )
        ]
        if len(county_history) < min_train_years:
            continue
        prior_year_row = rows_by_county_year.get((row.county_fips, test_year - 1))
        if prior_year_row is None or prior_year_row.incidence_per_100k is None:
            continue
        prior_values = [_known_incidence(prior) for prior in county_history]
        candidates.append(
            _Candidate(
                row=row,
                county_history=county_history,
                prior_year_row=prior_year_row,
                prior_mean=_round(mean(prior_values)),
                prior_min=_round(min(prior_values)),
                prior_max=_round(max(prior_values)),
                prior_sd=_round(pstdev(prior_values)) if len(prior_values) > 1 else 0.0,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.row.county_fips)


def _assign_clusters(
    candidates: list[_Candidate],
    *,
    n_clusters: int,
) -> list[_Assignment]:
    values = [candidate.prior_mean for candidate in candidates]
    active_clusters = min(n_clusters, len(values))
    raw_assignments, centroids = _kmeans_1d(values, active_clusters)
    populated = sorted(
        {
            cluster_index
            for cluster_index in raw_assignments
            if raw_assignments.count(cluster_index) > 0
        },
        key=lambda cluster_index: (centroids[cluster_index], cluster_index),
    )
    rank_by_raw_cluster = {
        cluster_index: rank
        for rank, cluster_index in enumerate(populated, start=1)
    }
    label_by_rank = _labels_by_rank(len(populated))
    return [
        _Assignment(
            candidate=candidate,
            cluster_rank=rank_by_raw_cluster[cluster_index],
            cluster_label=label_by_rank[rank_by_raw_cluster[cluster_index]],
            cluster_centroid=_round(centroids[cluster_index]),
        )
        for candidate, cluster_index in zip(
            candidates,
            raw_assignments,
            strict=True,
        )
    ]


def _kmeans_1d(values: list[float], n_clusters: int) -> tuple[list[int], list[float]]:
    sorted_values = sorted(values)
    if n_clusters == 1:
        return [0 for _ in values], [mean(values)]
    centroids = [
        sorted_values[round(index * (len(sorted_values) - 1) / (n_clusters - 1))]
        for index in range(n_clusters)
    ]
    assignments = [0 for _ in values]
    for _ in range(100):
        next_assignments = [
            min(
                range(n_clusters),
                key=lambda cluster_index: (
                    abs(value - centroids[cluster_index]),
                    cluster_index,
                ),
            )
            for value in values
        ]
        next_centroids = []
        for cluster_index in range(n_clusters):
            cluster_values = [
                value
                for value, assignment in zip(values, next_assignments, strict=True)
                if assignment == cluster_index
            ]
            next_centroids.append(
                mean(cluster_values) if cluster_values else centroids[cluster_index]
            )
        if next_assignments == assignments and all(
            math.isclose(current, updated)
            for current, updated in zip(centroids, next_centroids, strict=True)
        ):
            break
        assignments = next_assignments
        centroids = next_centroids
    return assignments, centroids


def _county_year_row(
    *,
    run_id: str,
    assignment: _Assignment,
    source_file_sha256: str,
) -> RegionalIncidenceClusterCountyYear:
    candidate = assignment.candidate
    row = candidate.row
    flags = _combined_flags(row.feature_quality_flags, COMPARISON_ASSUMPTION_FLAGS)
    train_start_year = min(prior.year for prior in candidate.county_history)
    train_end_year = max(prior.year for prior in candidate.county_history)
    return RegionalIncidenceClusterCountyYear(
        run_id=run_id,
        source_file_sha256=source_file_sha256,
        state_fips=row.state_fips,
        state_abbr=row.state_abbr,
        state_name=row.state_name,
        county_fips=row.county_fips,
        county_name=row.county_name,
        year=row.year,
        cluster_id=_cluster_id(row.year, assignment.cluster_rank),
        cluster_rank=assignment.cluster_rank,
        cluster_label=assignment.cluster_label,
        cluster_centroid_prior_mean_incidence_per_100k=assignment.cluster_centroid,
        feature_prior_mean_incidence_per_100k=candidate.prior_mean,
        feature_prior_min_incidence_per_100k=candidate.prior_min,
        feature_prior_max_incidence_per_100k=candidate.prior_max,
        feature_prior_sd_incidence_per_100k=candidate.prior_sd,
        feature_prior_year_incidence_per_100k=_known_incidence(
            candidate.prior_year_row
        ),
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=len(candidate.county_history),
        actual_incidence_per_100k=_known_incidence(row),
        actual_cases=row.total_cases,
        actual_population=row.population,
        model_feature_quality_flags=row.feature_quality_flags,
        comparison_assumption_flags=flags,
    )


def _summary_rows(
    *,
    run_id: str,
    assignments: list[_Assignment],
    source_file_sha256: str,
) -> list[RegionalIncidenceClusterSummary]:
    rows = []
    assignments_by_cluster: dict[int, list[_Assignment]] = {}
    for assignment in assignments:
        assignments_by_cluster.setdefault(assignment.cluster_rank, []).append(assignment)
    for cluster_rank, cluster_assignments in sorted(assignments_by_cluster.items()):
        year = cluster_assignments[0].candidate.row.year
        prior_values = _prior_cluster_weighted_values(cluster_assignments)
        actual_rows = [assignment.candidate.row for assignment in cluster_assignments]
        actual_population = _sum_population(actual_rows)
        rows.append(
            RegionalIncidenceClusterSummary(
                run_id=run_id,
                source_file_sha256=source_file_sha256,
                year=year,
                cluster_id=_cluster_id(year, cluster_rank),
                cluster_rank=cluster_rank,
                cluster_label=cluster_assignments[0].cluster_label,
                n_counties=len(cluster_assignments),
                feature_prior_cluster_min_incidence_per_100k=_round(
                    min(prior_values)
                ),
                feature_prior_cluster_mean_incidence_per_100k=_round(
                    mean(prior_values)
                ),
                feature_prior_cluster_max_incidence_per_100k=_round(
                    max(prior_values)
                ),
                feature_prior_cluster_sd_incidence_per_100k=(
                    _round(pstdev(prior_values)) if len(prior_values) > 1 else 0.0
                ),
                diagnostic_actual_cluster_incidence_per_100k=_weighted_incidence(
                    actual_rows
                ),
                diagnostic_actual_cluster_cases=sum(row.total_cases for row in actual_rows),
                diagnostic_actual_cluster_population=actual_population,
                comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
            )
        )
    return rows


def _prior_cluster_weighted_values(assignments: list[_Assignment]) -> list[float]:
    years = sorted(
        {
            prior.year
            for assignment in assignments
            for prior in assignment.candidate.county_history
        }
    )
    values = []
    for year in years:
        year_rows = [
            prior
            for assignment in assignments
            for prior in assignment.candidate.county_history
            if prior.year == year
        ]
        if year_rows:
            values.append(_weighted_incidence(year_rows))
    return values


def _weighted_incidence(rows: list[_IncidenceRow]) -> float:
    population = _sum_population(rows)
    if population is not None and population > 0:
        cases = sum(row.total_cases for row in rows)
        return _round((cases / population) * 100000)
    return _round(mean(_known_incidence(row) for row in rows))


def _sum_population(rows: list[_IncidenceRow]) -> int | None:
    if any(row.population is None for row in rows):
        return None
    return sum(row.population or 0 for row in rows)


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


def _labels_by_rank(n_clusters: int) -> dict[int, str]:
    known = {
        2: ["low", "high"],
        3: ["low", "moderate", "high"],
        4: ["low", "moderate", "high", "very_high"],
    }
    if n_clusters in known:
        return {
            rank: label
            for rank, label in enumerate(known[n_clusters], start=1)
        }
    return {
        rank: (
            "lowest"
            if rank == 1
            else "highest"
            if rank == n_clusters
            else f"cluster_{rank}"
        )
        for rank in range(1, n_clusters + 1)
    }


def _cluster_id(year: int, cluster_rank: int) -> str:
    return f"{year}_cluster_{cluster_rank}"


def _known_incidence(row: _IncidenceRow) -> float:
    if row.incidence_per_100k is None:
        raise RegionalIncidenceClusterInputError(
            "internal error: missing incidence used as known value"
        )
    return row.incidence_per_100k


def _combined_flags(*flag_groups: str) -> str:
    flags = []
    for group in flag_groups:
        flags.extend(flag for flag in group.split(",") if flag)
    return ",".join(dict.fromkeys(flags))


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
