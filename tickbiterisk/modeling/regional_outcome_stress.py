from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


COMPARISON_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "reported_cases_not_stable_true_incidence,"
    "regional_expansion_stress_test,"
    "not_public_maryland_default"
)
EVALUATION_MODE = "rolling_origin_prior_years"
TARGET_DEFINITION = "reported_lyme_cases"
FEATURE_SET = "historical_outcome_capacity_baselines"
REQUIRED_REGIONAL_OUTCOME_COLUMNS = {
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
}


class RegionalOutcomeStressInputError(ValueError):
    """Raised when regional outcome stress test inputs are invalid."""


@dataclass(frozen=True)
class RegionalOutcomeStressRun:
    run_id: str
    regional_lyme_path: str
    regional_lyme_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    lookback_years: int
    share_prior_strength: float
    model_names: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    n_input_rows: int
    n_predictions: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalOutcomeStressPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    source_file_sha256: str
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    train_year_count: int
    actual_cases: int
    predicted_cases: float
    residual_cases: float
    absolute_error_cases: float
    county_share_basis: float | None
    capacity_total_basis_cases: int | None
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalOutcomeStressMetric:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    evaluation_mode: str
    source_file_sha256: str
    aggregation: str
    state_fips: str | None
    state_name: str | None
    test_year: int | None
    n_predictions: int
    mae_cases: float
    rmse_cases: float
    mean_bias_cases: float
    comparison_assumption_flags: str


@dataclass(frozen=True)
class RegionalOutcomeStressResult:
    run_id: str
    run: RegionalOutcomeStressRun
    predictions: list[RegionalOutcomeStressPrediction]
    metrics: list[RegionalOutcomeStressMetric]


@dataclass(frozen=True)
class _OutcomeRow:
    state_fips: str
    state_abbr: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: int
    feature_quality_flags: str


@dataclass(frozen=True)
class _ModelPrediction:
    predicted_cases: float
    county_share_basis: float | None
    capacity_total_basis_cases: int | None


def build_regional_outcome_stress(
    *,
    regional_lyme_path: Path,
    start_year: int = 2007,
    end_year: int | None = None,
    min_train_years: int = 3,
    lookback_years: int = 3,
    share_prior_strength: float = 10.0,
) -> RegionalOutcomeStressResult:
    if min_train_years < 1:
        raise RegionalOutcomeStressInputError("min_train_years must be at least 1")
    if lookback_years < min_train_years:
        raise RegionalOutcomeStressInputError(
            "lookback_years must be greater than or equal to min_train_years"
        )
    if not math.isfinite(share_prior_strength) or share_prior_strength < 0:
        raise RegionalOutcomeStressInputError(
            "share_prior_strength must be finite and non-negative"
        )

    rows = _read_outcome_rows(regional_lyme_path)
    if not rows:
        raise RegionalOutcomeStressInputError("regional Lyme panel has no usable rows")
    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise RegionalOutcomeStressInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise RegionalOutcomeStressInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise RegionalOutcomeStressInputError(
            "start_year must be less than or equal to end_year"
        )

    rows_by_county = _group_by_county(rows)
    rows_by_year = _group_by_year(rows)
    rows_by_county_year = {(row.county_fips, row.year): row for row in rows}
    state_total_by_year = _state_totals(rows)
    regional_total_by_year = _regional_totals(rows)
    county_count_by_state = _county_counts_by_state(rows)
    regional_county_count = len({row.county_fips for row in rows})
    source_file_sha256 = _sha256_file(regional_lyme_path)
    run_id = (
        f"regional_outcome_stress_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_lookback{lookback_years}_"
        f"shareprior{_slug_float(share_prior_strength)}"
    )

    predictions = []
    for test_year in range(start_year, resolved_end_year + 1):
        for row in sorted(rows_by_year.get(test_year, []), key=lambda item: item.county_fips):
            county_history = [
                prior
                for prior in rows_by_county[row.county_fips]
                if test_year - lookback_years <= prior.year < test_year
            ]
            if len(county_history) < min_train_years:
                continue
            prior_year_row = rows_by_county_year.get((row.county_fips, test_year - 1))
            if prior_year_row is None:
                continue
            train_start_year = min(prior.year for prior in county_history)
            train_end_year = max(prior.year for prior in county_history)
            model_predictions = _predict_outcome_baselines(
                row=row,
                county_history=county_history,
                prior_year_row=prior_year_row,
                test_year=test_year,
                state_total_by_year=state_total_by_year,
                regional_total_by_year=regional_total_by_year,
                county_count_by_state=county_count_by_state,
                regional_county_count=regional_county_count,
                share_prior_strength=share_prior_strength,
            )
            flags = _combined_flags(row.feature_quality_flags, COMPARISON_ASSUMPTION_FLAGS)
            for model_name, model_prediction in model_predictions.items():
                predictions.append(
                    _prediction_row(
                        run_id=run_id,
                        model_name=model_name,
                        row=row,
                        model_prediction=model_prediction,
                        source_file_sha256=source_file_sha256,
                        train_start_year=train_start_year,
                        train_end_year=train_end_year,
                        train_year_count=len(county_history),
                        flags=flags,
                    )
                )

    predictions = sorted(
        predictions,
        key=lambda item: (item.test_year, item.model_name, item.county_fips),
    )
    metrics = _metric_rows(run_id, predictions, source_file_sha256)
    run = RegionalOutcomeStressRun(
        run_id=run_id,
        regional_lyme_path=str(regional_lyme_path),
        regional_lyme_sha256=source_file_sha256,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        lookback_years=lookback_years,
        share_prior_strength=share_prior_strength,
        model_names=",".join(sorted({row.model_name for row in predictions})),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        n_input_rows=len(rows),
        n_predictions=len(predictions),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )
    return RegionalOutcomeStressResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        metrics=metrics,
    )


def _read_outcome_rows(path: Path) -> list[_OutcomeRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_REGIONAL_OUTCOME_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RegionalOutcomeStressInputError(
                f"Missing regional Lyme panel columns: {sorted(missing)}"
            )
        return sorted(
            [
                _OutcomeRow(
                    state_fips=row["state_fips"].zfill(2),
                    state_abbr=str(row.get("state_abbr", "")),
                    state_name=str(row["state_name"]),
                    county_fips=row["county_fips"].zfill(5),
                    county_name=str(row["county_name"]),
                    year=int(row["year"]),
                    total_cases=_parse_int(row["total_cases"]),
                    feature_quality_flags=str(row.get("feature_quality_flags", "")),
                )
                for row in reader
            ],
            key=lambda row: (row.county_fips, row.year),
        )


def _group_by_county(rows: list[_OutcomeRow]) -> dict[str, list[_OutcomeRow]]:
    grouped: dict[str, list[_OutcomeRow]] = {}
    for row in rows:
        grouped.setdefault(row.county_fips, []).append(row)
    return {
        county_fips: sorted(county_rows, key=lambda row: row.year)
        for county_fips, county_rows in grouped.items()
    }


def _group_by_year(rows: list[_OutcomeRow]) -> dict[int, list[_OutcomeRow]]:
    grouped: dict[int, list[_OutcomeRow]] = {}
    for row in rows:
        grouped.setdefault(row.year, []).append(row)
    return grouped


def _state_totals(rows: list[_OutcomeRow]) -> dict[tuple[str, int], int]:
    totals: dict[tuple[str, int], int] = {}
    for row in rows:
        key = (row.state_fips, row.year)
        totals[key] = totals.get(key, 0) + row.total_cases
    return totals


def _regional_totals(rows: list[_OutcomeRow]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in rows:
        totals[row.year] = totals.get(row.year, 0) + row.total_cases
    return totals


def _county_counts_by_state(rows: list[_OutcomeRow]) -> dict[str, int]:
    counties_by_state: dict[str, set[str]] = {}
    for row in rows:
        counties_by_state.setdefault(row.state_fips, set()).add(row.county_fips)
    return {
        state_fips: len(county_fips)
        for state_fips, county_fips in counties_by_state.items()
    }


def _predict_outcome_baselines(
    *,
    row: _OutcomeRow,
    county_history: list[_OutcomeRow],
    prior_year_row: _OutcomeRow,
    test_year: int,
    state_total_by_year: dict[tuple[str, int], int],
    regional_total_by_year: dict[int, int],
    county_count_by_state: dict[str, int],
    regional_county_count: int,
    share_prior_strength: float,
) -> dict[str, _ModelPrediction]:
    prior_state_total = state_total_by_year.get((row.state_fips, test_year - 1), 0)
    prior_regional_total = regional_total_by_year.get(test_year - 1, 0)
    history_state_total = sum(
        state_total_by_year.get((row.state_fips, prior.year), 0)
        for prior in county_history
    )
    history_regional_total = sum(
        regional_total_by_year.get(prior.year, 0) for prior in county_history
    )
    history_county_total = sum(prior.total_cases for prior in county_history)
    state_share = _share(history_county_total, history_state_total)
    regional_share = _share(history_county_total, history_regional_total)
    empirical_bayes_state_share = _shrunk_share(
        numerator=history_county_total,
        denominator=history_state_total,
        prior_share=_equal_share(county_count_by_state.get(row.state_fips, 0)),
        prior_strength=share_prior_strength,
    )
    empirical_bayes_regional_share = _shrunk_share(
        numerator=history_county_total,
        denominator=history_regional_total,
        prior_share=_equal_share(regional_county_count),
        prior_strength=share_prior_strength,
    )
    return {
        "prior_year_county_cases": _ModelPrediction(
            predicted_cases=float(prior_year_row.total_cases),
            county_share_basis=None,
            capacity_total_basis_cases=None,
        ),
        "trailing_mean_county_cases": _ModelPrediction(
            predicted_cases=_round(mean(prior.total_cases for prior in county_history)),
            county_share_basis=None,
            capacity_total_basis_cases=None,
        ),
        "state_capacity_share_cases": _ModelPrediction(
            predicted_cases=_round((state_share or 0.0) * prior_state_total),
            county_share_basis=state_share,
            capacity_total_basis_cases=prior_state_total,
        ),
        "empirical_bayes_state_capacity_cases": _ModelPrediction(
            predicted_cases=_round(empirical_bayes_state_share * prior_state_total),
            county_share_basis=_round(empirical_bayes_state_share),
            capacity_total_basis_cases=prior_state_total,
        ),
        "midatlantic_capacity_share_cases": _ModelPrediction(
            predicted_cases=_round((regional_share or 0.0) * prior_regional_total),
            county_share_basis=regional_share,
            capacity_total_basis_cases=prior_regional_total,
        ),
        "empirical_bayes_midatlantic_capacity_cases": _ModelPrediction(
            predicted_cases=_round(empirical_bayes_regional_share * prior_regional_total),
            county_share_basis=_round(empirical_bayes_regional_share),
            capacity_total_basis_cases=prior_regional_total,
        ),
    }


def _prediction_row(
    *,
    run_id: str,
    model_name: str,
    row: _OutcomeRow,
    model_prediction: _ModelPrediction,
    source_file_sha256: str,
    train_start_year: int,
    train_end_year: int,
    train_year_count: int,
    flags: str,
) -> RegionalOutcomeStressPrediction:
    residual_cases = _round(row.total_cases - model_prediction.predicted_cases)
    return RegionalOutcomeStressPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family=_model_family(model_name),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        source_file_sha256=source_file_sha256,
        state_fips=row.state_fips,
        state_abbr=row.state_abbr,
        state_name=row.state_name,
        county_fips=row.county_fips,
        county_name=row.county_name,
        test_year=row.year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_year_count=train_year_count,
        actual_cases=row.total_cases,
        predicted_cases=model_prediction.predicted_cases,
        residual_cases=residual_cases,
        absolute_error_cases=_round(abs(residual_cases)),
        county_share_basis=model_prediction.county_share_basis,
        capacity_total_basis_cases=model_prediction.capacity_total_basis_cases,
        model_feature_quality_flags=row.feature_quality_flags,
        comparison_assumption_flags=flags,
    )


def _metric_rows(
    run_id: str,
    predictions: list[RegionalOutcomeStressPrediction],
    source_file_sha256: str,
) -> list[RegionalOutcomeStressMetric]:
    metrics = []
    for model_name in sorted({row.model_name for row in predictions}):
        model_rows = [row for row in predictions if row.model_name == model_name]
        metrics.append(
            _metric_row(
                run_id=run_id,
                model_name=model_name,
                source_file_sha256=source_file_sha256,
                aggregation="overall",
                rows=model_rows,
            )
        )
        for state_fips in sorted({row.state_fips for row in model_rows}):
            state_rows = [row for row in model_rows if row.state_fips == state_fips]
            metrics.append(
                _metric_row(
                    run_id=run_id,
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    aggregation="state",
                    rows=state_rows,
                    state_fips=state_fips,
                    state_name=state_rows[0].state_name,
                )
            )
        for test_year in sorted({row.test_year for row in model_rows}):
            year_rows = [row for row in model_rows if row.test_year == test_year]
            metrics.append(
                _metric_row(
                    run_id=run_id,
                    model_name=model_name,
                    source_file_sha256=source_file_sha256,
                    aggregation="year",
                    rows=year_rows,
                    test_year=test_year,
                )
            )
    return metrics


def _metric_row(
    *,
    run_id: str,
    model_name: str,
    source_file_sha256: str,
    aggregation: str,
    rows: list[RegionalOutcomeStressPrediction],
    state_fips: str | None = None,
    state_name: str | None = None,
    test_year: int | None = None,
) -> RegionalOutcomeStressMetric:
    residuals = [row.residual_cases for row in rows]
    absolute_errors = [row.absolute_error_cases for row in rows]
    return RegionalOutcomeStressMetric(
        run_id=run_id,
        model_name=model_name,
        model_family=_model_family(model_name),
        target_definition=TARGET_DEFINITION,
        feature_set=FEATURE_SET,
        evaluation_mode=EVALUATION_MODE,
        source_file_sha256=source_file_sha256,
        aggregation=aggregation,
        state_fips=state_fips,
        state_name=state_name,
        test_year=test_year,
        n_predictions=len(rows),
        mae_cases=_round(mean(absolute_errors)) if absolute_errors else 0.0,
        rmse_cases=(
            _round(math.sqrt(mean(residual * residual for residual in residuals)))
            if residuals
            else 0.0
        ),
        mean_bias_cases=_round(mean(residuals)) if residuals else 0.0,
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )


def _model_family(model_name: str) -> str:
    if model_name.startswith("empirical_bayes_"):
        return "empirical_bayes_capacity_share"
    if model_name.endswith("capacity_share_cases"):
        return "regional_capacity_share"
    return "county_history_baseline"


def _share(numerator: int, denominator: int | None) -> float | None:
    if denominator in (None, 0):
        return None
    return _round(numerator / denominator)


def _equal_share(count: int) -> float:
    if count <= 0:
        return 0.0
    return 1.0 / count


def _shrunk_share(
    *,
    numerator: int,
    denominator: int,
    prior_share: float,
    prior_strength: float,
) -> float:
    posterior_denominator = denominator + prior_strength
    if posterior_denominator <= 0:
        return prior_share
    return (numerator + (prior_strength * prior_share)) / posterior_denominator


def _combined_flags(*flag_groups: str) -> str:
    flags = []
    for group in flag_groups:
        flags.extend(flag for flag in group.split(",") if flag)
    return ",".join(dict.fromkeys(flags))


def _parse_int(value: str) -> int:
    return int(float(value))


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
