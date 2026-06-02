from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from tickbiterisk.modeling.regimes import (
    CASE_DEFINITION_2022_PLUS,
    COVID_REPORTING_DISRUPTION,
    MDH_PROBABLE_ONLY_2024,
    OTHER_SURVEILLANCE_REGIME,
    PRE_2020_BASELINE,
)


CDC_2022_MMWR_URL = "https://www.cdc.gov/mmwr/volumes/73/wr/mm7306a1.htm"
CDC_PUBLISHED_HIGH_INCIDENCE_LEVEL_SHIFT = 1.729
CDC_PUBLISHED_ANCHOR_SE_LOG = 0.15
DID_CONTROL_FAILURE_REASON = "insufficient_unsuppressed_county_panel_2017_2019"
DID_CONTROL_DECISION_REFERENCE = (
    "docs/research/lab-notes/08-reporting-basis-identification.md;"
    "docs/research/source-materials/did-control-verification-2017-2019.csv"
)
DEFAULT_DISPLAY_LABEL = (
    "Estimate adjusted to 2022 CDC reporting guidelines based on "
    "difference-in-differences vs out-of-region low-incidence controls"
)


class ReportingBasisAdjustmentInputError(ValueError):
    """Raised when reporting-basis adjustment inputs are invalid."""


@dataclass(frozen=True)
class HighIncidenceClassification:
    jurisdiction_fips: str
    classification: str
    qualifying_years: str
    threshold_per_100k: float
    consecutive_years_required: int
    pre_window: str
    source_panel_sha256: str
    source_citation_url: str
    assumption_flags: str
    notes: str


@dataclass(frozen=True)
class HighIncidenceClassificationResult:
    rows: list[HighIncidenceClassification]
    pre_window: str
    source_panel_sha256: str


@dataclass(frozen=True)
class ReportingBasisAdjustment:
    adjustment_id: str
    jurisdiction_scope: str
    boundary_year: int
    source_regime: str
    target_reference_basis: str
    adjustment_method: str
    multiplicative_factor: float
    factor_se_log: float
    factor_ci80_low: float
    factor_ci80_high: float
    factor_ci95_low: float
    factor_ci95_high: float
    treatment_status: str
    n_control_jurisdictions: int
    n_observations_used: int
    identification_quality: str
    smoothed_on_adjacency: bool
    displayed_as: str
    pre_window: str
    source_citation_url: str
    source_panel_sha256: str
    source_vintage: str
    assumption_flags: str
    notes: str


@dataclass(frozen=True)
class DidControlPanelRow:
    candidate_state_fips: str
    candidate_state_name: str
    county_fips: str
    county_name: str
    instrument_role: str
    forecast_exclusion: str
    candidate_pre_window: str
    candidate_low_incidence_status: str
    parallel_trends_status: str
    parallel_trends_treatment_slope: float
    parallel_trends_control_slope: float
    parallel_trends_slope_difference: float
    inclusion_decision: str
    failure_reason: str
    source_panel_sha256: str
    source_vintage: str
    assumption_flags: str
    notes: str


@dataclass(frozen=True)
class ReportingBasisAdjustmentRun:
    run_id: str
    regional_incidence_path: str
    regional_incidence_sha256: str
    county_adjacency_path: str
    county_adjacency_sha256: str
    did_control_panel_path: str
    did_control_panel_sha256: str
    pre_window: str
    boundary_year: int
    target_reference_basis: str
    identification_method: str
    did_control_evaluated: bool
    did_control_passed: bool
    did_control_failure_reason: str
    did_control_decision_reference: str
    threshold_per_100k: float
    consecutive_years_required: int
    did_treatment_shift: float
    did_control_shift: float
    did_ratio: float
    parallel_trends_status: str
    parallel_trends_treatment_slope: float
    parallel_trends_control_slope: float
    parallel_trend_tolerance: float
    candidate_control_states_passed: str
    candidate_control_states_failed: str
    method_validation_2008_status: str
    method_validation_2008_observed_ratio: float
    method_validation_2017_status: str
    method_validation_2017_observed_ratio: float
    n_treatment_jurisdictions: int
    n_control_jurisdictions: int
    source_citation_url: str
    source_vintage: str


@dataclass(frozen=True)
class ReportingBasisAdjustmentResult:
    classifications: list[HighIncidenceClassification]
    did_control_panel: list[DidControlPanelRow]
    adjustments: list[ReportingBasisAdjustment]
    run: ReportingBasisAdjustmentRun


@dataclass(frozen=True)
class _IncidenceRow:
    state_fips: str
    state_name: str
    county_fips: str
    county_name: str
    year: int
    total_cases: float
    population: float
    incidence_per_100k: float


def build_high_incidence_classification(
    *,
    regional_incidence_path: Path,
    pre_window_start: int = 2017,
    pre_window_end: int = 2019,
    threshold_per_100k: float = 10.0,
    consecutive_years_required: int = 3,
) -> HighIncidenceClassificationResult:
    rows = _read_incidence_rows(regional_incidence_path)
    source_sha = _sha256_file(regional_incidence_path)
    pre_window = _pre_window_label(pre_window_start, pre_window_end)
    state_year_incidence = _state_year_incidence(rows)
    states = sorted({row.state_fips for row in rows})
    output = []
    for state_fips in states:
        qualifying_years = [
            year
            for year in range(pre_window_start, pre_window_end + 1)
            if (
                state_year_incidence.get((state_fips, year)) is not None
                and state_year_incidence[(state_fips, year)] >= threshold_per_100k
            )
        ]
        observed_pre_years = [
            year
            for year in range(pre_window_start, pre_window_end + 1)
            if state_year_incidence.get((state_fips, year)) is not None
        ]
        if len(observed_pre_years) < consecutive_years_required:
            classification = "excluded_insufficient_pre_window"
            assumption_flags = "insufficient_pre_window_years"
            notes = "Jurisdiction lacks enough pre-window incidence rows for CDC-style classification."
        elif _has_consecutive_years(qualifying_years, consecutive_years_required):
            classification = "high_incidence"
            assumption_flags = ""
            notes = "Jurisdiction meets the high-incidence threshold in the declared pre-window."
        else:
            classification = "low_incidence"
            assumption_flags = ""
            notes = "Jurisdiction does not meet the high-incidence threshold in the declared pre-window."
        output.append(
            HighIncidenceClassification(
                jurisdiction_fips=state_fips,
                classification=classification,
                qualifying_years=";".join(str(year) for year in qualifying_years),
                threshold_per_100k=threshold_per_100k,
                consecutive_years_required=consecutive_years_required,
                pre_window=pre_window,
                source_panel_sha256=source_sha,
                source_citation_url=CDC_2022_MMWR_URL,
                assumption_flags=assumption_flags,
                notes=notes,
            )
        )
    return HighIncidenceClassificationResult(
        rows=output,
        pre_window=pre_window,
        source_panel_sha256=source_sha,
    )


def build_reporting_basis_adjustment(
    *,
    regional_incidence_path: Path,
    county_adjacency_path: Path | None = None,
    did_control_panel_path: Path | None = None,
    pre_window_start: int = 2017,
    pre_window_end: int = 2019,
    boundary_year: int = 2022,
    threshold_per_100k: float = 10.0,
    consecutive_years_required: int = 3,
    parallel_trend_tolerance: float = 0.25,
    target_reference_basis: str = CASE_DEFINITION_2022_PLUS,
    source_vintage: str = "regional_incidence_panel",
) -> ReportingBasisAdjustmentResult:
    rows = _read_incidence_rows(regional_incidence_path)
    if not rows:
        raise ReportingBasisAdjustmentInputError("regional incidence panel has no rows")
    source_sha = _sha256_file(regional_incidence_path)
    adjacency_sha = "" if county_adjacency_path is None else _sha256_file(county_adjacency_path)
    control_rows = (
        [] if did_control_panel_path is None else _read_incidence_rows(did_control_panel_path)
    )
    control_sha = "" if did_control_panel_path is None else _sha256_file(did_control_panel_path)
    pre_window = _pre_window_label(pre_window_start, pre_window_end)
    classification_result = build_high_incidence_classification(
        regional_incidence_path=regional_incidence_path,
        pre_window_start=pre_window_start,
        pre_window_end=pre_window_end,
        threshold_per_100k=threshold_per_100k,
        consecutive_years_required=consecutive_years_required,
    )
    classifications = {
        row.jurisdiction_fips: row.classification
        for row in classification_result.rows
    }
    state_year_incidence = _state_year_incidence(rows)
    treatment_states = sorted(
        state
        for state, classification in classifications.items()
        if classification == "high_incidence"
    )
    treatment_slope = (
        _group_pre_slope(
            state_year_incidence,
            treatment_states,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
        )
        if treatment_states
        else 0.0
    )
    did_control_panel, passed_control_states, failed_control_states = (
        _select_out_of_region_controls(
            control_rows,
            control_sha=control_sha,
            treatment_slope=treatment_slope,
            pre_window=pre_window,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
            boundary_year=boundary_year,
            threshold_per_100k=threshold_per_100k,
            consecutive_years_required=consecutive_years_required,
            parallel_trend_tolerance=parallel_trend_tolerance,
            source_vintage=source_vintage,
        )
    )
    control_state_year_incidence = _state_year_incidence(control_rows)
    did_available = bool(treatment_states and passed_control_states)
    treatment_shift = (
        _group_shift(
            state_year_incidence,
            treatment_states,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
            boundary_year=boundary_year,
        )
        if treatment_states
        else 0.0
    )
    validation_2008 = _method_validation(
        state_year_incidence,
        treatment_states,
        boundary_year=2008,
    )
    validation_2017 = _method_validation(
        state_year_incidence,
        treatment_states,
        boundary_year=2017,
    )
    if did_available:
        control_shift = _group_shift(
            control_state_year_incidence,
            passed_control_states,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
            boundary_year=boundary_year,
        )
        control_slope = _group_pre_slope(
            control_state_year_incidence,
            passed_control_states,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
        )
        did_ratio = 0.0 if control_shift == 0 else treatment_shift / control_shift
        factor = did_ratio
        base_factor_by_county = _base_factor_by_county(
            rows,
            classifications=classifications,
            treatment_factor=factor,
            non_treatment_factor=1.0,
        )
        identification_method = "out_of_region_low_incidence_did"
        parallel_trends_status = "passed"
        assumption_flags = _join_flags(
            "did_parallel_trends_passed",
            "out_of_region_low_incidence_controls",
            "control_panel_walled_off_non_forecast",
            "covid_years_excluded_from_pre_window",
        )
        factor_se_log = _factor_se_log(
            did_ratio,
            len(treatment_states),
            len(passed_control_states),
        )
    else:
        control_shift = 0.0
        control_slope = (
            mean(
                row.parallel_trends_control_slope
                for row in did_control_panel
                if row.parallel_trends_status == "violated"
            )
            if any(row.parallel_trends_status == "violated" for row in did_control_panel)
            else 0.0
        )
        did_ratio = 0.0
        factor = CDC_PUBLISHED_HIGH_INCIDENCE_LEVEL_SHIFT
        base_factor_by_county = _base_factor_by_county(
            rows,
            classifications=classifications,
            treatment_factor=factor,
            non_treatment_factor=1.0,
        )
        identification_method = "cdc_published_anchor"
        parallel_trends_status = (
            "violated"
            if failed_control_states and did_control_panel
            else "not_applicable"
        )
        assumption_flags = _join_flags(
            "did_treatment_group_unavailable" if not treatment_states else "",
            "did_control_group_unavailable" if not passed_control_states else "",
            "did_parallel_trends_violated" if failed_control_states else "",
            "cdc_published_anchor_prior",
            "interrupted_time_series_diagnostic_only",
            "covid_years_excluded_from_pre_window",
        )
        factor_se_log = CDC_PUBLISHED_ANCHOR_SE_LOG
    smoothed_factor_by_county = _smooth_factors(
        base_factor_by_county,
        _read_adjacency(county_adjacency_path),
    )
    counties = sorted({row.county_fips for row in rows})
    n_observations_used = len(
        [
            row
            for row in rows
            if row.state_fips in treatment_states
            and (
                pre_window_start <= row.year <= pre_window_end
                or row.year == boundary_year
            )
        ]
    )
    if passed_control_states:
        n_observations_used += len(
            [
                row
                for row in control_rows
                if row.state_fips in passed_control_states
                and (
                    pre_window_start <= row.year <= pre_window_end
                    or row.year == boundary_year
                )
            ]
        )
    adjustments = []
    for county_fips in counties:
        treatment_status = classifications.get(
            county_fips[:2],
            "excluded_insufficient_pre_window",
        )
        smoothed_factor = smoothed_factor_by_county[county_fips]
        smoothed_on_adjacency = (
            smoothed_factor != base_factor_by_county[county_fips]
        )
        for source_regime in (
            PRE_2020_BASELINE,
            COVID_REPORTING_DISRUPTION,
            OTHER_SURVEILLANCE_REGIME,
        ):
            adjustments.append(
                _adjustment_row(
                    county_fips=county_fips,
                    boundary_year=boundary_year,
                    source_regime=source_regime,
                    target_reference_basis=target_reference_basis,
                    treatment_status=treatment_status,
                    adjustment_method=identification_method,
                    factor=smoothed_factor,
                    factor_se_log=factor_se_log,
                    smoothed_on_adjacency=smoothed_on_adjacency,
                    pre_window=pre_window,
                    source_panel_sha256=source_sha,
                    source_vintage=source_vintage,
                    assumption_flags=assumption_flags,
                    n_control_jurisdictions=len(passed_control_states),
                    n_observations_used=n_observations_used,
                )
            )
        for source_regime in (CASE_DEFINITION_2022_PLUS, MDH_PROBABLE_ONLY_2024):
            adjustments.append(
                _adjustment_row(
                    county_fips=county_fips,
                    boundary_year=boundary_year,
                    source_regime=source_regime,
                    target_reference_basis=target_reference_basis,
                    treatment_status=treatment_status,
                    adjustment_method="reference_basis_no_adjustment",
                    factor=1.0,
                    factor_se_log=0.0,
                    smoothed_on_adjacency=False,
                    pre_window=pre_window,
                    source_panel_sha256=source_sha,
                    source_vintage=source_vintage,
                    assumption_flags="reference_basis_no_adjustment",
                    n_control_jurisdictions=len(passed_control_states),
                    n_observations_used=n_observations_used,
                )
            )
    run = ReportingBasisAdjustmentRun(
        run_id=(
            "reporting_basis_adjustment_"
            f"{pre_window}_boundary{boundary_year}_{source_sha[:12]}_{adjacency_sha[:12]}"
        ),
        regional_incidence_path=str(regional_incidence_path),
        regional_incidence_sha256=source_sha,
        county_adjacency_path="" if county_adjacency_path is None else str(county_adjacency_path),
        county_adjacency_sha256=adjacency_sha,
        did_control_panel_path="" if did_control_panel_path is None else str(did_control_panel_path),
        did_control_panel_sha256=control_sha,
        pre_window=pre_window,
        boundary_year=boundary_year,
        target_reference_basis=target_reference_basis,
        identification_method=identification_method,
        did_control_evaluated=True,
        did_control_passed=did_available,
        did_control_failure_reason=_did_control_failure_reason(
            did_available=did_available,
            did_control_panel_path=did_control_panel_path,
            failed_control_states=failed_control_states,
        ),
        did_control_decision_reference=DID_CONTROL_DECISION_REFERENCE,
        threshold_per_100k=threshold_per_100k,
        consecutive_years_required=consecutive_years_required,
        did_treatment_shift=_round(treatment_shift),
        did_control_shift=_round(control_shift),
        did_ratio=_round(did_ratio),
        parallel_trends_status=parallel_trends_status,
        parallel_trends_treatment_slope=_round(treatment_slope),
        parallel_trends_control_slope=_round(control_slope),
        parallel_trend_tolerance=parallel_trend_tolerance,
        candidate_control_states_passed=";".join(passed_control_states),
        candidate_control_states_failed=";".join(
            f"{state}:{reason}" for state, reason in failed_control_states
        ),
        method_validation_2008_status=validation_2008[0],
        method_validation_2008_observed_ratio=_round(validation_2008[1]),
        method_validation_2017_status=validation_2017[0],
        method_validation_2017_observed_ratio=_round(validation_2017[1]),
        n_treatment_jurisdictions=len(treatment_states),
        n_control_jurisdictions=len(passed_control_states),
        source_citation_url=CDC_2022_MMWR_URL,
        source_vintage=source_vintage,
    )
    return ReportingBasisAdjustmentResult(
        classifications=classification_result.rows,
        did_control_panel=did_control_panel,
        adjustments=adjustments,
        run=run,
    )


def read_reporting_basis_adjustment(path: Path) -> list[ReportingBasisAdjustment]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            ReportingBasisAdjustment(
                adjustment_id=row["adjustment_id"],
                jurisdiction_scope=row["jurisdiction_scope"],
                boundary_year=_parse_int(row["boundary_year"], "boundary_year"),
                source_regime=row["source_regime"],
                target_reference_basis=row["target_reference_basis"],
                adjustment_method=row["adjustment_method"],
                multiplicative_factor=_parse_float(row["multiplicative_factor"], "multiplicative_factor"),
                factor_se_log=_parse_float(row["factor_se_log"], "factor_se_log"),
                factor_ci80_low=_parse_float(row["factor_ci80_low"], "factor_ci80_low"),
                factor_ci80_high=_parse_float(row["factor_ci80_high"], "factor_ci80_high"),
                factor_ci95_low=_parse_float(row["factor_ci95_low"], "factor_ci95_low"),
                factor_ci95_high=_parse_float(row["factor_ci95_high"], "factor_ci95_high"),
                treatment_status=row["treatment_status"],
                n_control_jurisdictions=_parse_int(row["n_control_jurisdictions"], "n_control_jurisdictions"),
                n_observations_used=_parse_int(row["n_observations_used"], "n_observations_used"),
                identification_quality=row["identification_quality"],
                smoothed_on_adjacency=_parse_bool(row["smoothed_on_adjacency"]),
                displayed_as=row["displayed_as"],
                pre_window=row["pre_window"],
                source_citation_url=row["source_citation_url"],
                source_panel_sha256=row["source_panel_sha256"],
                source_vintage=row["source_vintage"],
                assumption_flags=row["assumption_flags"],
                notes=row["notes"],
            )
            for row in reader
        ]


def _adjustment_row(
    *,
    county_fips: str,
    boundary_year: int,
    source_regime: str,
    target_reference_basis: str,
    treatment_status: str,
    adjustment_method: str,
    factor: float,
    factor_se_log: float,
    smoothed_on_adjacency: bool,
    pre_window: str,
    source_panel_sha256: str,
    source_vintage: str,
    assumption_flags: str,
    n_control_jurisdictions: int,
    n_observations_used: int,
) -> ReportingBasisAdjustment:
    ci80_low, ci80_high = _log_scale_ci(factor, factor_se_log, z=1.281551565545)
    ci95_low, ci95_high = _log_scale_ci(factor, factor_se_log, z=1.95996398454)
    return ReportingBasisAdjustment(
        adjustment_id=(
            f"county_{county_fips}__{source_regime}__boundary{boundary_year}__"
            f"{adjustment_method}"
        ),
        jurisdiction_scope=f"county_{county_fips}",
        boundary_year=boundary_year,
        source_regime=source_regime,
        target_reference_basis=target_reference_basis,
        adjustment_method=adjustment_method,
        multiplicative_factor=_round(factor),
        factor_se_log=_round(factor_se_log),
        factor_ci80_low=_round(ci80_low),
        factor_ci80_high=_round(ci80_high),
        factor_ci95_low=_round(ci95_low),
        factor_ci95_high=_round(ci95_high),
        treatment_status=treatment_status,
        n_control_jurisdictions=n_control_jurisdictions,
        n_observations_used=n_observations_used,
        identification_quality=_identification_quality(
            adjustment_method,
            assumption_flags,
        ),
        smoothed_on_adjacency=smoothed_on_adjacency,
        displayed_as=_display_label(adjustment_method),
        pre_window=pre_window,
        source_citation_url=CDC_2022_MMWR_URL,
        source_panel_sha256=source_panel_sha256,
        source_vintage=source_vintage,
        assumption_flags=assumption_flags,
        notes=_adjustment_notes(adjustment_method),
    )


def _read_incidence_rows(path: Path) -> list[_IncidenceRow]:
    required_columns = {
        "state_fips",
        "county_fips",
        "year",
        "total_cases",
        "population",
        "incidence_per_100k",
    }
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = required_columns - fieldnames
        if missing:
            raise ReportingBasisAdjustmentInputError(
                "missing required regional incidence column(s): "
                f"{', '.join(sorted(missing))}"
            )
        rows = []
        for row in reader:
            incidence = row.get("incidence_per_100k", "")
            population = row.get("population", "")
            if incidence == "" or population == "":
                continue
            rows.append(
                _IncidenceRow(
                    state_fips=str(row["state_fips"]).zfill(2),
                    state_name=str(row.get("state_name", "")).strip(),
                    county_fips=str(row["county_fips"]).zfill(5),
                    county_name=str(row.get("county_name", "")).strip(),
                    year=_parse_int(row["year"], "year"),
                    total_cases=_parse_float(row["total_cases"], "total_cases"),
                    population=_parse_float(population, "population"),
                    incidence_per_100k=_parse_float(incidence, "incidence_per_100k"),
                )
            )
    return sorted(rows, key=lambda row: (row.state_fips, row.county_fips, row.year))


def _state_year_incidence(rows: list[_IncidenceRow]) -> dict[tuple[str, int], float]:
    groups: dict[tuple[str, int], list[_IncidenceRow]] = {}
    for row in rows:
        groups.setdefault((row.state_fips, row.year), []).append(row)
    return {
        key: _round(
            sum(row.incidence_per_100k * row.population for row in group)
            / sum(row.population for row in group)
        )
        for key, group in groups.items()
        if sum(row.population for row in group) > 0
    }


def _has_consecutive_years(years: list[int], required: int) -> bool:
    year_set = set(years)
    return any(
        all((start + offset) in year_set for offset in range(required))
        for start in years
    )


def _group_shift(
    state_year_incidence: dict[tuple[str, int], float],
    states: list[str],
    *,
    pre_window_start: int,
    pre_window_end: int,
    boundary_year: int,
) -> float:
    pre_values = [
        state_year_incidence[(state, year)]
        for state in states
        for year in range(pre_window_start, pre_window_end + 1)
        if (state, year) in state_year_incidence
    ]
    post_values = [
        state_year_incidence[(state, boundary_year)]
        for state in states
        if (state, boundary_year) in state_year_incidence
    ]
    if not pre_values or not post_values:
        raise ReportingBasisAdjustmentInputError(
            "DiD adjustment requires observed pre-window and boundary-year "
            "incidence for treatment and control groups"
        )
    pre_mean = mean(pre_values)
    post_mean = mean(post_values)
    if pre_mean <= 0:
        raise ReportingBasisAdjustmentInputError("pre-window incidence mean must be positive")
    return post_mean / pre_mean


def _group_pre_slope(
    state_year_incidence: dict[tuple[str, int], float],
    states: list[str],
    *,
    pre_window_start: int,
    pre_window_end: int,
) -> float:
    year_values = []
    for year in range(pre_window_start, pre_window_end + 1):
        values = [
            state_year_incidence[(state, year)]
            for state in states
            if (state, year) in state_year_incidence
        ]
        if values:
            year_values.append(mean(values))
    if len(year_values) < 2:
        return 0.0
    return (year_values[-1] - year_values[0]) / (len(year_values) - 1)


def _select_out_of_region_controls(
    rows: list[_IncidenceRow],
    *,
    control_sha: str,
    treatment_slope: float,
    pre_window: str,
    pre_window_start: int,
    pre_window_end: int,
    boundary_year: int,
    threshold_per_100k: float,
    consecutive_years_required: int,
    parallel_trend_tolerance: float,
    source_vintage: str,
) -> tuple[list[DidControlPanelRow], list[str], list[tuple[str, str]]]:
    if not rows:
        return [], [], []
    state_year_incidence = _state_year_incidence(rows)
    states = sorted({row.state_fips for row in rows})
    passed_states: list[str] = []
    failed_states: list[tuple[str, str]] = []
    decisions = {}
    for state_fips in states:
        low_incidence_status = _classify_state_from_years(
            state_year_incidence,
            state_fips,
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
            threshold_per_100k=threshold_per_100k,
            consecutive_years_required=consecutive_years_required,
        )
        control_slope = _group_pre_slope(
            state_year_incidence,
            [state_fips],
            pre_window_start=pre_window_start,
            pre_window_end=pre_window_end,
        )
        slope_difference = abs(treatment_slope - control_slope)
        failure_reason = ""
        parallel_trends_status = "not_applicable"
        inclusion_decision = "excluded"
        if low_incidence_status != "low_incidence":
            failure_reason = f"candidate_not_low_incidence:{low_incidence_status}"
        else:
            try:
                _group_shift(
                    state_year_incidence,
                    [state_fips],
                    pre_window_start=pre_window_start,
                    pre_window_end=pre_window_end,
                    boundary_year=boundary_year,
                )
            except ReportingBasisAdjustmentInputError:
                failure_reason = "insufficient_boundary_or_pre_window_data"
            else:
                parallel_trends_status = (
                    "passed"
                    if slope_difference <= parallel_trend_tolerance
                    else "violated"
                )
                if parallel_trends_status == "passed":
                    inclusion_decision = "included"
                    passed_states.append(state_fips)
                else:
                    failure_reason = "did_parallel_trends_violated"
        if failure_reason:
            failed_states.append((state_fips, failure_reason))
        decisions[state_fips] = {
            "low_incidence_status": low_incidence_status,
            "parallel_trends_status": parallel_trends_status,
            "control_slope": control_slope,
            "slope_difference": slope_difference,
            "inclusion_decision": inclusion_decision,
            "failure_reason": failure_reason,
        }

    output = []
    for state_fips, county_fips in sorted(
        {(row.state_fips, row.county_fips) for row in rows}
    ):
        county_rows = [
            row
            for row in rows
            if row.state_fips == state_fips and row.county_fips == county_fips
        ]
        first = county_rows[0]
        decision = decisions[state_fips]
        assumption_flags = _join_flags(
            "non_forecast_identification_instrument",
            (
                "did_parallel_trends_passed"
                if decision["parallel_trends_status"] == "passed"
                else decision["failure_reason"]
            ),
        )
        output.append(
            DidControlPanelRow(
                candidate_state_fips=state_fips,
                candidate_state_name=first.state_name,
                county_fips=county_fips,
                county_name=first.county_name,
                instrument_role="non_forecast_identification_instrument",
                forecast_exclusion="must_not_enter_forecast_design_matrix",
                candidate_pre_window=pre_window,
                candidate_low_incidence_status=decision["low_incidence_status"],
                parallel_trends_status=decision["parallel_trends_status"],
                parallel_trends_treatment_slope=_round(treatment_slope),
                parallel_trends_control_slope=_round(decision["control_slope"]),
                parallel_trends_slope_difference=_round(
                    decision["slope_difference"]
                ),
                inclusion_decision=decision["inclusion_decision"],
                failure_reason=decision["failure_reason"],
                source_panel_sha256=control_sha,
                source_vintage=source_vintage,
                assumption_flags=assumption_flags,
                notes=(
                    "Out-of-region low-incidence DiD candidate; this row is "
                    "provenance for identification only and must not enter "
                    "forecast feature engineering."
                ),
            )
        )
    return output, passed_states, failed_states


def _classify_state_from_years(
    state_year_incidence: dict[tuple[str, int], float],
    state_fips: str,
    *,
    pre_window_start: int,
    pre_window_end: int,
    threshold_per_100k: float,
    consecutive_years_required: int,
) -> str:
    qualifying_years = [
        year
        for year in range(pre_window_start, pre_window_end + 1)
        if (
            state_year_incidence.get((state_fips, year)) is not None
            and state_year_incidence[(state_fips, year)] >= threshold_per_100k
        )
    ]
    observed_pre_years = [
        year
        for year in range(pre_window_start, pre_window_end + 1)
        if state_year_incidence.get((state_fips, year)) is not None
    ]
    if len(observed_pre_years) < consecutive_years_required:
        return "excluded_insufficient_pre_window"
    if _has_consecutive_years(qualifying_years, consecutive_years_required):
        return "high_incidence"
    return "low_incidence"


def _method_validation(
    state_year_incidence: dict[tuple[str, int], float],
    states: list[str],
    *,
    boundary_year: int,
) -> tuple[str, float]:
    pre_values = [
        state_year_incidence[(state, year)]
        for state in states
        for year in range(boundary_year - 3, boundary_year)
        if (state, year) in state_year_incidence
    ]
    boundary_values = [
        state_year_incidence[(state, boundary_year)]
        for state in states
        if (state, boundary_year) in state_year_incidence
    ]
    if not pre_values or not boundary_values:
        return "insufficient_data", 0.0
    pre_mean = mean(pre_values)
    if pre_mean <= 0:
        return "insufficient_data", 0.0
    ratio = mean(boundary_values) / pre_mean
    return ("passed" if ratio > 1.0 else "failed"), ratio


def _did_control_failure_reason(
    *,
    did_available: bool,
    did_control_panel_path: Path | None,
    failed_control_states: list[tuple[str, str]],
) -> str:
    if did_available:
        return ""
    if did_control_panel_path is None:
        return DID_CONTROL_FAILURE_REASON
    if failed_control_states:
        return "no_parallel_trends_control_passed"
    return DID_CONTROL_FAILURE_REASON


def _base_factor_by_county(
    rows: list[_IncidenceRow],
    *,
    classifications: dict[str, str],
    treatment_factor: float,
    non_treatment_factor: float,
) -> dict[str, float]:
    return {
        county_fips: (
            treatment_factor
            if classifications.get(county_fips[:2]) == "high_incidence"
            else non_treatment_factor
        )
        for county_fips in sorted({row.county_fips for row in rows})
    }


def _base_factors(
    rows: list[_IncidenceRow],
    *,
    classifications: dict[str, str],
    treatment_shift: float,
    control_shift: float,
) -> dict[str, float]:
    factors = {}
    for county_fips in sorted({row.county_fips for row in rows}):
        classification = classifications.get(county_fips[:2])
        if classification == "high_incidence":
            factors[county_fips] = treatment_shift
        elif classification == "low_incidence":
            factors[county_fips] = control_shift
        else:
            factors[county_fips] = 1.0
    return factors


def _interrupted_time_series_factors(
    rows: list[_IncidenceRow],
    *,
    pre_window_start: int,
    pre_window_end: int,
    boundary_year: int,
) -> dict[str, float]:
    by_county: dict[str, list[_IncidenceRow]] = {}
    for row in rows:
        by_county.setdefault(row.county_fips, []).append(row)
    factors = {}
    for county_fips, county_rows in by_county.items():
        pre_values = [
            row.incidence_per_100k
            for row in county_rows
            if pre_window_start <= row.year <= pre_window_end
        ]
        boundary_values = [
            row.incidence_per_100k
            for row in county_rows
            if row.year == boundary_year
        ]
        if not pre_values or not boundary_values:
            factors[county_fips] = 1.0
            continue
        pre_mean = mean(pre_values)
        boundary_mean = mean(boundary_values)
        factors[county_fips] = (
            1.0
            if pre_mean <= 0 or boundary_mean <= 0
            else boundary_mean / pre_mean
        )
    return factors


def _smooth_factors(
    base_factor_by_county: dict[str, float],
    adjacency: dict[str, list[str]],
) -> dict[str, float]:
    if not adjacency:
        return base_factor_by_county
    smoothed = {}
    for county_fips, factor in base_factor_by_county.items():
        neighbor_factors = [
            base_factor_by_county[neighbor]
            for neighbor in adjacency.get(county_fips, [])
            if neighbor in base_factor_by_county
        ]
        smoothed[county_fips] = (
            mean([factor, *neighbor_factors])
            if neighbor_factors
            else factor
        )
    return smoothed


def _read_adjacency(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"county_fips", "neighbor_county_fips"} - set(reader.fieldnames or [])
        if missing:
            raise ReportingBasisAdjustmentInputError(
                "missing required adjacency column(s): "
                f"{', '.join(sorted(missing))}"
            )
        neighbors: dict[str, set[str]] = {}
        for row in reader:
            county_fips = str(row["county_fips"]).zfill(5)
            neighbor = str(row["neighbor_county_fips"]).zfill(5)
            if county_fips == neighbor:
                continue
            neighbors.setdefault(county_fips, set()).add(neighbor)
    return {county: sorted(values) for county, values in neighbors.items()}


def _factor_se_log(did_ratio: float, n_treatment: int, n_control: int) -> float:
    if did_ratio <= 0:
        return 0.0
    return abs(math.log(did_ratio)) / math.sqrt(max(1, n_treatment + n_control))


def _factor_se_log_from_county_factors(factors: dict[str, float]) -> float:
    log_factors = [
        math.log(factor)
        for factor in factors.values()
        if factor > 0
    ]
    if len(log_factors) < 2:
        return 0.0
    average = mean(log_factors)
    variance = sum((value - average) ** 2 for value in log_factors) / (
        len(log_factors) - 1
    )
    return math.sqrt(variance / len(log_factors))


def _log_scale_ci(factor: float, factor_se_log: float, *, z: float) -> tuple[float, float]:
    if factor_se_log == 0:
        return factor, factor
    log_factor = math.log(factor)
    return (
        math.exp(log_factor - z * factor_se_log),
        math.exp(log_factor + z * factor_se_log),
    )


def _pre_window_label(start: int, end: int) -> str:
    if start > end:
        raise ReportingBasisAdjustmentInputError("pre_window_start must be <= pre_window_end")
    return f"{start}-{end}"


def _identification_quality(adjustment_method: str, assumption_flags: str) -> str:
    if adjustment_method == "interrupted_time_series":
        return "weak_identification"
    if adjustment_method == "reference_basis_no_adjustment":
        return "strong"
    if adjustment_method == "cdc_published_anchor":
        return "moderate"
    return "moderate" if "did_parallel_trends_violated" in assumption_flags else "strong"


def _display_label(adjustment_method: str) -> str:
    if adjustment_method == "reference_basis_no_adjustment":
        return "Already on 2022 CDC reporting guidelines reference basis"
    if adjustment_method == "interrupted_time_series":
        return (
            "Estimate adjusted to 2022 CDC reporting guidelines based on "
            "within-jurisdiction interrupted time-series fallback"
        )
    if adjustment_method == "cdc_published_anchor":
        return (
            "Estimate adjusted to 2022 CDC reporting guidelines using the "
            "CDC published high-incidence fixed-prior anchor"
        )
    return DEFAULT_DISPLAY_LABEL


def _adjustment_notes(adjustment_method: str) -> str:
    if adjustment_method == "reference_basis_no_adjustment":
        return "Reference-basis rows carry a neutral factor for total joins."
    if adjustment_method == "interrupted_time_series":
        return (
            "County reporting-basis factor estimated from its own pre-window "
            "to boundary-year level shift because no in-region DiD control "
            "jurisdiction was available."
        )
    if adjustment_method == "cdc_published_anchor":
        return (
            "County reporting-basis factor uses the CDC published national "
            "high-incidence level-shift anchor because no out-of-region "
            "low-incidence control passed the parallel-trends gate."
        )
    return (
        "County reporting-basis factor estimated from in-region high-incidence "
        "treatment counties and out-of-region low-incidence controls that "
        "passed the pre-2022 parallel-trends gate."
    )


def _join_flags(*values: str) -> str:
    flags = []
    for value in values:
        for raw_flag in str(value).split(","):
            flag = raw_flag.strip()
            if flag and flag not in flags:
                flags.append(flag)
    return ",".join(flags)


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _parse_int(value: str, field_name: str) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise ReportingBasisAdjustmentInputError(f"{field_name} must be an integer") from exc


def _parse_float(value: str, field_name: str) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise ReportingBasisAdjustmentInputError(f"{field_name} must be numeric") from exc


def _round(value: float) -> float:
    return round(value, 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
