from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tickbiterisk.runtime.risk_lookup import (
    CLINICAL_DISCLAIMER,
    GUIDANCE_LINKS,
    CountyWeekRiskRecord,
    RiskLookupInputError,
    read_county_week_risk_records,
    split_quality_flags,
)


STATIC_EXPORT_SCHEMA_VERSION = "county-week-risk-static-v1"
MARYLAND_GEOGRAPHY_SCOPE = "maryland_county_week"
MIDATLANTIC_GEOGRAPHY_SCOPE = "midatlantic_county_week"

PUBLIC_CAVEATS = [
    "Informational and educational only; not medical advice.",
    "Does not diagnose disease or determine whether a person is infected.",
    "Not a treatment recommendation or substitute for a healthcare professional.",
    "Relative Maryland county seasonal Lyme forecast, not a per-bite infection probability.",
    "Displayed county-week values are derived seasonal allocations of annual county forecasts, not observed county-week data.",
    "Not a personal infection probability.",
    "Static seasonal prior; not a weather-adjusted forecast.",
    "CDC national onset seasonality is not county-specific.",
    "Surveillance/reporting changes and interventions are unmodeled.",
    "Empirical intervals describe forecast uncertainty, not clinical confidence for an individual bite.",
]

EXPLAINER_PLACEHOLDERS = [
    {
        "topic": "why_forecasting",
        "status": "captured_for_public_review",
        "plain_language_goal": (
            "Explain why official Lyme data lag current prevention decisions."
        ),
    },
    {
        "topic": "data_lag_and_reconciliation",
        "status": "captured_for_public_review",
        "plain_language_goal": (
            "Explain how new reports are compared with prior forecasts before updates."
        ),
    },
    {
        "topic": "forecast_update_research",
        "status": "captured_for_public_review",
        "plain_language_goal": (
            "Explain how validated observations could revise future forecasts "
            "with uncertainty and caveats attached."
        ),
    },
    {
        "topic": "regional_hotspot_patterns",
        "status": "captured_for_public_review",
        "plain_language_goal": (
            "Explain regional clusters, neighboring counties, and year-over-year "
            "hotspot movement without overclaiming migration or causality."
        ),
    },
]

PUBLIC_VALIDATION_MODEL_NAMES = {
    "prior_year_incidence",
    "trailing_mean_incidence",
    "linear_blend_baseline",
    "empirical_bayes_shrinkage",
    "analog_year_forecast",
}

SCORE_CATEGORIES = {
    "1-2": "very_low",
    "3-4": "low",
    "5-6": "moderate",
    "7-8": "high",
    "9-10": "very_high",
}

TEMPORAL_CONTRACT = {
    "observed_truth_spatial_grain": "county",
    "observed_truth_temporal_grain": "year",
    "forecast_truth_spatial_grain": "county",
    "forecast_truth_temporal_grain": "year",
    "display_temporal_grain": "mmwr_week",
    "display_time_role": "seasonal_allocation_of_annual_forecast",
    "seasonality_scope": "national",
    "county_month_or_week_observed_truth_available": False,
    "historical_display_policy": (
        "Historical years are observed annual county incidence only; derived "
        "weekly or monthly allocations must not be labeled as observed "
        "historical risk."
    ),
}


class StaticExportInputError(ValueError):
    """Raised when static public export inputs are invalid."""


@dataclass(frozen=True)
class _GeographyScope:
    scope: str
    weekly_export_type: str
    county_export_type: str
    weekly_filename: str
    county_metadata_filename: str
    geography_label: str
    product_framing: str
    score_interpretation: str
    relative_risk_caveat: str
    research_only: bool = False
    not_public_maryland_default: bool = False
    state: str | None = None
    state_fips: str | None = None
    region: str | None = None
    region_state_fips: tuple[str, ...] = ()


@dataclass(frozen=True)
class StaticRiskExportPaths:
    weekly_risk_path: Path
    county_metadata_path: Path
    model_card_path: Path
    source_catalog_path: Path
    export_manifest_path: Path


def export_static_risk_data(
    *,
    scores_path: Path,
    output_dir: Path,
    model_name: str = "linear_blend_baseline",
    seasonality_source_id: str = "cdc_seasonality_week_2023",
    benchmark_quantile: float | None = None,
    headroom_multiplier: float | None = None,
    score_denominator: float | None = None,
    source_prediction_run_id: str | None = None,
    source_prediction_sha256: str | None = None,
    source_seasonality_sha256: str | None = None,
    model_summary_path: Path | None = None,
    geography_scope: str = MARYLAND_GEOGRAPHY_SCOPE,
) -> StaticRiskExportPaths:
    geography = _geography_scope(geography_scope)
    try:
        records = read_county_week_risk_records(scores_path)
    except RiskLookupInputError as exc:
        raise StaticExportInputError(str(exc)) from exc
    selected = _select_records(
        records,
        model_name=model_name,
        seasonality_source_id=seasonality_source_id,
        benchmark_quantile=benchmark_quantile,
        headroom_multiplier=headroom_multiplier,
        score_denominator=score_denominator,
        source_prediction_run_id=source_prediction_run_id,
        source_prediction_sha256=source_prediction_sha256,
        source_seasonality_sha256=source_seasonality_sha256,
        geography=geography,
    )
    source_records = selected
    _validate_duplicate_keys(source_records)
    selected = _display_records(selected, geography=geography)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = StaticRiskExportPaths(
        weekly_risk_path=output_dir / geography.weekly_filename,
        county_metadata_path=output_dir / geography.county_metadata_filename,
        model_card_path=output_dir / "model_card.json",
        source_catalog_path=output_dir / "source_catalog.json",
        export_manifest_path=output_dir / "static_export_manifest.json",
    )
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    weekly_payload = _weekly_payload(
        selected,
        generated_at=generated_at,
        input_sha256=_sha256_file(scores_path),
        geography=geography,
    )
    county_payload = _county_metadata_payload(
        selected,
        source_records=source_records,
        generated_at=generated_at,
        geography=geography,
    )
    model_card_payload = _model_card_payload(
        selected,
        generated_at=generated_at,
        model_summary_path=model_summary_path,
        geography=geography,
    )
    source_catalog_payload = _source_catalog_payload(
        selected,
        generated_at=generated_at,
        input_sha256=_sha256_file(scores_path),
        geography=geography,
    )
    manifest_payload = _manifest_payload(
        paths,
        weekly_payload=weekly_payload,
        county_payload=county_payload,
        generated_at=generated_at,
        geography=geography,
    )

    _write_json(paths.weekly_risk_path, weekly_payload)
    _write_json(paths.county_metadata_path, county_payload)
    _write_json(paths.model_card_path, model_card_payload)
    _write_json(paths.source_catalog_path, source_catalog_payload)
    _write_json(paths.export_manifest_path, manifest_payload)
    return paths


def _geography_scope(scope: str) -> _GeographyScope:
    if scope == MARYLAND_GEOGRAPHY_SCOPE:
        return _GeographyScope(
            scope=MARYLAND_GEOGRAPHY_SCOPE,
            weekly_export_type="md_county_risk_weekly",
            county_export_type="md_county_metadata",
            weekly_filename="md_county_risk_weekly.json",
            county_metadata_filename="md_county_metadata.json",
            geography_label="MD county/jurisdiction",
            product_framing=(
                "Lyme risk forecasting tool for Maryland county annual disease "
                "pressure with seasonal allocation"
            ),
            score_interpretation=(
                "Relative seasonal Lyme forecast on a 1-10 Maryland scale; "
                "annual county forecasts are allocated across MMWR weeks using "
                "national seasonality and are not per-bite infection probabilities."
            ),
            relative_risk_caveat=(
                "Relative Maryland county seasonal Lyme forecast, not a "
                "per-bite infection probability."
            ),
            state="MD",
            state_fips="24",
        )
    if scope == MIDATLANTIC_GEOGRAPHY_SCOPE:
        return _GeographyScope(
            scope=MIDATLANTIC_GEOGRAPHY_SCOPE,
            weekly_export_type="regional_county_risk_weekly",
            county_export_type="regional_county_metadata",
            weekly_filename="regional_county_risk_weekly.json",
            county_metadata_filename="regional_county_metadata.json",
            geography_label="DE/DC/MD/PA/VA/WV county-equivalent",
            product_framing=(
                "Lyme risk forecasting tool for DE/DC/MD/PA/VA/WV "
                "county annual disease pressure with seasonal allocation"
            ),
            score_interpretation=(
                "Relative seasonal Lyme forecast on a 1-10 regional scale; "
                "annual county forecasts are allocated across MMWR weeks using "
                "national seasonality and are not per-bite infection probabilities."
            ),
            relative_risk_caveat=(
                "Relative regional county seasonal Lyme forecast, not a "
                "per-bite infection probability."
            ),
            research_only=True,
            not_public_maryland_default=True,
            region="DE/DC/MD/PA/VA/WV",
            region_state_fips=("10", "11", "24", "42", "51", "54"),
        )
    raise StaticExportInputError(
        f"Unsupported static export geography_scope: {scope}"
    )


def _weekly_geography_payload(
    geography: _GeographyScope,
    records: list[CountyWeekRiskRecord],
) -> dict[str, object]:
    jurisdiction_count = len({record.county_fips for record in records})
    if geography.region is not None:
        return {
            "region": geography.region,
            "state_fips": list(geography.region_state_fips),
            "jurisdiction_count": jurisdiction_count,
        }
    return {
        "state": geography.state,
        "state_fips": geography.state_fips,
        "jurisdiction_count": jurisdiction_count,
    }


def _public_caveats(geography: _GeographyScope) -> list[str]:
    return [
        geography.relative_risk_caveat
        if caveat.startswith("Relative Maryland county seasonal")
        else caveat
        for caveat in PUBLIC_CAVEATS
    ]


def _research_status_field(geography: _GeographyScope) -> dict[str, object]:
    if not geography.research_only and not geography.not_public_maryland_default:
        return {}
    return {
        "research_status": {
            "research_only": geography.research_only,
            "not_public_maryland_default": geography.not_public_maryland_default,
        }
    }


def _select_records(
    records: list[CountyWeekRiskRecord],
    *,
    model_name: str,
    seasonality_source_id: str,
    benchmark_quantile: float | None,
    headroom_multiplier: float | None,
    score_denominator: float | None,
    source_prediction_run_id: str | None,
    source_prediction_sha256: str | None,
    source_seasonality_sha256: str | None,
    geography: _GeographyScope,
) -> list[CountyWeekRiskRecord]:
    selected = [
        record
        for record in records
        if record.model_name == model_name
        and record.seasonality_source_id == seasonality_source_id
    ]
    if benchmark_quantile is not None:
        selected = [
            record for record in selected if record.benchmark_quantile == benchmark_quantile
        ]
    if headroom_multiplier is not None:
        selected = [
            record
            for record in selected
            if record.headroom_multiplier == headroom_multiplier
        ]
    if score_denominator is not None:
        selected = [
            record
            for record in selected
            if record.score_denominator == score_denominator
        ]
    if source_prediction_run_id is not None:
        selected = [
            record
            for record in selected
            if record.source_prediction_run_id == source_prediction_run_id
        ]
    if source_prediction_sha256 is not None:
        selected = [
            record
            for record in selected
            if record.source_prediction_sha256 == source_prediction_sha256
        ]
    if source_seasonality_sha256 is not None:
        selected = [
            record
            for record in selected
            if record.source_seasonality_sha256 == source_seasonality_sha256
        ]
    if not selected:
        raise StaticExportInputError("No static export rows matched the selectors")

    branches = {_score_branch_key(record, geography) for record in selected}
    if len(branches) > 1:
        raise StaticExportInputError(
            "Multiple static export score branches found; provide selectors for "
            "model, seasonality source, score scale, and source version"
        )
    return sorted(
        selected,
        key=lambda row: (row.county_fips, row.year, row.mmwr_week),
    )


def _score_branch_key(
    record: CountyWeekRiskRecord,
    geography: _GeographyScope,
) -> tuple[object, ...]:
    key = (
        record.model_name,
        record.seasonality_source_id,
        record.benchmark_quantile,
        record.headroom_multiplier,
        record.score_denominator,
        record.source_prediction_sha256,
        record.source_seasonality_sha256,
    )
    if geography.scope == MIDATLANTIC_GEOGRAPHY_SCOPE:
        return key
    return (*key, record.source_prediction_run_id)


def _validate_duplicate_keys(records: list[CountyWeekRiskRecord]) -> None:
    seen = set()
    for record in records:
        key = (record.county_fips, record.year, record.mmwr_week)
        if key in seen:
            raise StaticExportInputError(
                "Duplicate county/year/MMWR week rows found after selectors"
            )
        seen.add(key)


def _display_records(
    records: list[CountyWeekRiskRecord],
    *,
    geography: _GeographyScope,
) -> list[CountyWeekRiskRecord]:
    if geography.scope == MIDATLANTIC_GEOGRAPHY_SCOPE:
        return sorted(records, key=lambda row: (row.county_fips, row.year, row.mmwr_week))
    return _latest_records_by_county_week(records)


def _latest_records_by_county_week(
    records: list[CountyWeekRiskRecord],
) -> list[CountyWeekRiskRecord]:
    latest: dict[tuple[str, int], CountyWeekRiskRecord] = {}
    for record in records:
        key = (record.county_fips, record.mmwr_week)
        current = latest.get(key)
        if current is None or record.year > current.year:
            latest[key] = record
    return sorted(latest.values(), key=lambda row: (row.county_fips, row.mmwr_week))


def _weekly_payload(
    records: list[CountyWeekRiskRecord],
    *,
    generated_at: str,
    input_sha256: str,
    geography: _GeographyScope,
) -> dict[str, object]:
    first = records[0]
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": geography.weekly_export_type,
        "generated_at": generated_at,
        "scope": geography.scope,
        "geography": _weekly_geography_payload(geography, records),
        "disease": "lyme",
        "grain": "mmwr_week",
        "date_system": {
            "name": "CDC MMWR",
            "week_starts_on": "Sunday",
            "year_start_rule": "week containing Jan 4",
        },
        "model_name": first.model_name,
        "seasonality_source_id": first.seasonality_source_id,
        "record_count": len(records),
        "year_selection": _year_selection(geography),
        "temporal_contract": TEMPORAL_CONTRACT,
        "selected_score_config": _selected_score_config(first),
        "selected_forecast_metadata": _selected_forecast_metadata(records),
        "forecast_basis": _forecast_basis_payload(records),
        "score_scale": {
            "range": [1, 10],
            "categories": SCORE_CATEGORIES,
            "score_denominator": first.score_denominator,
            "benchmark_quantile": first.benchmark_quantile,
            "headroom_multiplier": first.headroom_multiplier,
        },
        "input_artifact_sha256": input_sha256,
        **_research_status_field(geography),
        "caveats": _public_caveats(geography),
        "guidance_links": GUIDANCE_LINKS,
        "records": [_weekly_record(record) for record in records],
    }


def _weekly_record(record: CountyWeekRiskRecord) -> dict[str, object]:
    week_start = _mmwr_week_start(record.year, record.mmwr_week)
    week_end = week_start + timedelta(days=6)
    return {
        "county_fips": record.county_fips,
        "county_name": record.county_name,
        "year": record.year,
        "data_year": record.year,
        "mmwr_week": record.mmwr_week,
        "period_label": record.period_label,
        "week_start_date": week_start.isoformat(),
        "week_end_date": week_end.isoformat(),
        "risk_score": record.risk_score,
        "risk_category": record.risk_category,
        "risk_score_raw": record.risk_score_raw,
        "predicted_weekly_incidence_per_100k": (
            record.predicted_weekly_incidence_per_100k
        ),
        "predicted_weekly_incidence_80_interval": [
            record.lower_80_weekly_incidence_per_100k,
            record.upper_80_weekly_incidence_per_100k,
        ],
        "predicted_weekly_incidence_95_interval": [
            record.lower_95_weekly_incidence_per_100k,
            record.upper_95_weekly_incidence_per_100k,
        ],
        "predicted_weekly_cases": record.predicted_weekly_cases,
        "predicted_annual_incidence_per_100k": (
            record.predicted_annual_incidence_per_100k
        ),
        "feature_quality_flags": split_quality_flags(record.feature_quality_flags),
        "backtest_assumption_flags": split_quality_flags(
            record.backtest_assumption_flags
        ),
    }


def _mmwr_week_start(year: int, week: int) -> date:
    return _mmwr_year_start(year) + timedelta(days=(week - 1) * 7)


def _mmwr_year_start(year: int) -> date:
    jan4 = date(year, 1, 4)
    return jan4 - timedelta(days=(jan4.weekday() + 1) % 7)


def _county_metadata_payload(
    records: list[CountyWeekRiskRecord],
    *,
    source_records: list[CountyWeekRiskRecord],
    generated_at: str,
    geography: _GeographyScope,
) -> dict[str, object]:
    grouped: dict[str, list[CountyWeekRiskRecord]] = {}
    for record in records:
        grouped.setdefault(record.county_fips, []).append(record)
    source_years: dict[str, set[int]] = {}
    for record in source_records:
        source_years.setdefault(record.county_fips, set()).add(record.year)

    counties = []
    for county_fips, rows in sorted(grouped.items()):
        counties.append(
            {
                "county_fips": county_fips,
                "county_name": rows[0].county_name,
                "available_years": sorted({row.year for row in rows}),
                "source_available_years": sorted(source_years[county_fips]),
                "available_mmwr_weeks": sorted({row.mmwr_week for row in rows}),
                "max_risk_score": max(row.risk_score for row in rows),
            }
        )
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": geography.county_export_type,
        "generated_at": generated_at,
        "geography": geography.geography_label,
        "county_count": len(counties),
        **_research_status_field(geography),
        "counties": counties,
    }


def _model_card_payload(
    records: list[CountyWeekRiskRecord],
    *,
    generated_at: str,
    model_summary_path: Path | None,
    geography: _GeographyScope,
) -> dict[str, object]:
    first = records[0]
    payload: dict[str, object] = {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "model_card",
        "generated_at": generated_at,
        "model_name": first.model_name,
        "target_definition": "lyme_incidence_per_100k",
        "product_framing": geography.product_framing,
        "score_interpretation": geography.score_interpretation,
        "not_for": [
            "per-bite infection probability",
            "diagnosis",
            "treatment recommendation",
            "weather-adjusted forecast",
        ],
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
        "method_summary": (
            "Selected annual forecast rows apportioned by "
            "CDC national MMWR-week Lyme onset seasonality; displayed "
            "county-week values are seasonal allocation, not observed "
            "county-week data."
        ),
        "forecasting_status": {
            "status": "risk_forecasting_tool",
            "public_score_role": (
                "relative county-week Lyme risk forecast with source-lag and "
                "update diagnostics"
            ),
            "update_policy": (
                "New surveillance, ecology, exposure, and calibration evidence are "
                "reconciled against prior forecasts and backtests before they are "
                "considered for future reviewed estimates."
            ),
        },
        **_research_status_field(geography),
        "temporal_contract": TEMPORAL_CONTRACT,
        "explainer_placeholders": EXPLAINER_PLACEHOLDERS,
        "annual_prediction_source": _annual_prediction_source(records),
        "forecast_basis": _forecast_basis_payload(records),
        "quality_flags": [
            "relative_seasonal_baseline",
            "static_seasonality_prior",
            "not_weather_adjusted",
        ],
        "caveats": _public_caveats(geography),
    }
    if model_summary_path is not None:
        payload["validation_summary"] = _validation_summary_payload(
            first,
            model_summary_path,
        )
    return payload


def _validation_summary_payload(
    selected: CountyWeekRiskRecord,
    model_summary_path: Path,
) -> dict[str, object]:
    if not model_summary_path.exists():
        raise StaticExportInputError(
            f"Model comparison summary file not found: {model_summary_path}"
        )
    with model_summary_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    model_name_matches = [row for row in rows if row.get("model_name") == selected.model_name]
    for row in rows:
        if (
            row.get("run_id") == selected.source_prediction_run_id
            and row.get("model_name") == selected.model_name
        ):
            return _model_summary_payload_from_row(
                row,
                forecast_model_name=selected.model_name,
                validation_match_type="selected_prediction_run",
                summary_rows=rows,
            )
    if (
        selected.source_prediction_run_id.startswith("annual_forecast_")
        and len(model_name_matches) == 1
    ):
        return _model_summary_payload_from_row(
            model_name_matches[0],
            forecast_model_name=selected.model_name,
            validation_match_type="annual_forecast_model_name",
            summary_rows=rows,
        )
    raise StaticExportInputError(
        "No model comparison summary row matched selected run_id="
        f"{selected.source_prediction_run_id} and model_name={selected.model_name}"
    )


def _model_summary_payload_from_row(
    row: dict[str, str],
    *,
    forecast_model_name: str,
    validation_match_type: str,
    summary_rows: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "run_id": str(row["run_id"]),
        "model_name": str(row["model_name"]),
        "rank_by_mae": _public_validation_rank_by_mae(row, summary_rows),
        "n_predictions": _optional_int(row.get("n_predictions")),
        "mae_incidence_per_100k": _optional_float(
            row.get("mae_incidence_per_100k")
        ),
        "rmse_incidence_per_100k": _optional_float(
            row.get("rmse_incidence_per_100k")
        ),
        "pearson_correlation": _optional_float(row.get("pearson_correlation")),
        "validation_role": "historical_model_comparison",
        "validation_match_type": validation_match_type,
        "forecast_model_name": forecast_model_name,
        "comparison_assumption_flags": split_quality_flags(
            row.get("comparison_assumption_flags", "")
        ),
    }


def _public_validation_rank_by_mae(
    row: dict[str, str],
    summary_rows: list[dict[str, str]] | None,
) -> int | None:
    fallback_rank = _optional_int(row.get("rank_by_mae"))
    if row.get("model_name") not in PUBLIC_VALIDATION_MODEL_NAMES:
        return fallback_rank
    if summary_rows is None:
        return fallback_rank
    run_id = row.get("run_id")
    ranked_rows = [
        candidate
        for candidate in summary_rows
        if candidate.get("run_id") == run_id
        and candidate.get("model_name") in PUBLIC_VALIDATION_MODEL_NAMES
        and _optional_float(candidate.get("mae_incidence_per_100k")) is not None
    ]
    if not ranked_rows:
        return fallback_rank
    ranked_rows.sort(
        key=lambda candidate: (
            _optional_float(candidate.get("mae_incidence_per_100k")),
            str(candidate.get("model_name", "")),
        )
    )
    for index, candidate in enumerate(ranked_rows, start=1):
        if candidate is row:
            return index
    return fallback_rank


def _source_catalog_payload(
    records: list[CountyWeekRiskRecord],
    *,
    generated_at: str,
    input_sha256: str,
    geography: _GeographyScope,
) -> dict[str, object]:
    first = records[0]
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "source_catalog",
        "generated_at": generated_at,
        "source_prediction_run_id": first.source_prediction_run_id,
        "source_prediction_sha256": first.source_prediction_sha256,
        "source_seasonality_sha256": first.source_seasonality_sha256,
        "input_artifact_sha256": input_sha256,
        **_research_status_field(geography),
        "temporal_contract": TEMPORAL_CONTRACT,
        "guidance_links": GUIDANCE_LINKS,
        "data_lag_and_update_policy": {
            "summary": (
                "Official Lyme surveillance data lag real-world exposure conditions, "
                "so TickBiteRisk treats forecasts as provisional informational "
                "estimates that improve as new validated data arrive."
            ),
            "why_forecasting": (
                "Forecasting gives timely prevention context while county-level "
                "surveillance reports, population denominators, and reviewed source "
                "updates catch up."
            ),
            "reconciliation_policy": (
                "New observed reports are reconciled against prior forecasts using "
                "surveillance-regime diagnostics, calibration backtests, and source "
                "quality flags before they are promoted into future reviewed estimates."
            ),
            "forecast_boundary": (
                "Forecast-safe branches use prior-year and trailing data; nowcast or "
                "retrospective branches must be labeled separately."
            ),
            "bayesian_update_boundary": (
                "Gamma-Poisson Bayesian case-multiplier updates are research-only "
                "until rolling-origin backtests show they improve forecast error or "
                "calibration."
            ),
            "medical_boundary": (
                "Forecasts do not diagnose disease, decide treatment, or determine "
                "whether an individual bite caused infection."
            ),
        },
        "sources": [
            {
                "source_id": "county_week_seasonal_risk_baseline",
                "artifact_type": "derived",
                "redistribution": "public derived data",
                "sha256": input_sha256,
                "notes": (
                    "Derived from selected annual forecast rows "
                    "and CDC seasonality as a seasonal allocation; not "
                    "observed county-week data. Do not publish raw restricted "
                    "or terms-unclear source extracts."
                ),
            },
            {
                "source_id": "annual_prediction_branch",
                "artifact_type": "annual prediction branch",
                "redistribution": "public derived data",
                "sha256": first.source_prediction_sha256,
                "run_id": first.source_prediction_run_id,
                "model_name": first.model_name,
                "model_family": first.model_family,
                "evaluation_mode": first.evaluation_mode,
                "weather_mode": first.weather_mode,
                **_selected_forecast_metadata(records),
                **_annual_interval_metadata(first),
                "notes": (
                    "Selected annual no-observed-target forecast rows; "
                    "historical backtests are separate validation evidence, "
                    "not the forecast source."
                ),
            },
            {
                "source_id": first.seasonality_source_id,
                "artifact_type": "derived seasonality prior",
                "redistribution": "public derived data",
                "sha256": first.source_seasonality_sha256,
                "notes": "CDC national onset seasonality; not county-specific.",
            },
        ],
        "forecast_basis": _forecast_basis_payload(records),
    }


def _annual_prediction_source(
    records: CountyWeekRiskRecord | list[CountyWeekRiskRecord],
) -> dict[str, object]:
    selected = records if isinstance(records, list) else [records]
    record = selected[0]
    return {
        "artifact_type": "annual_prediction_branch",
        "run_id": record.source_prediction_run_id,
        "sha256": record.source_prediction_sha256,
        "model_name": record.model_name,
        "model_family": record.model_family,
        "evaluation_mode": record.evaluation_mode,
        "weather_mode": record.weather_mode,
        **_selected_forecast_metadata(selected),
        **_annual_interval_metadata(record),
    }


def _forecast_basis_payload(
    records: CountyWeekRiskRecord | list[CountyWeekRiskRecord],
) -> dict[str, object]:
    selected = records if isinstance(records, list) else [records]
    record = selected[0]
    return {
        "target": {
            "disease": "Lyme disease",
            "metric": "reported_lyme_incidence_per_100k",
            "spatial_grain": "county",
            "temporal_grain": "year",
            "interpretation": (
                "reported surveillance incidence used as a proxy for relative "
                "Lyme disease pressure"
            ),
        },
        "selected_branch": {
            "model_name": record.model_name,
            "model_family": record.model_family,
            "feature_set": record.feature_set,
            "evaluation_mode": record.evaluation_mode,
            "forecast_origin_year": record.forecast_origin_year,
            "data_cutoff_date": record.data_cutoff_date,
            "source_vintage": record.source_vintage,
            "update_mode": record.update_mode,
        },
        "signals_used": _forecast_basis_signals_used(record),
        "signals_not_used": [
            "observed county-week Lyme cases",
            "observed county-month Lyme cases",
            "observed county-week tick counts",
            "observed county-week infected tick prevalence",
            "individual bite outcomes",
        ],
        "seasonal_allocation": {
            "source": record.seasonality_source_id,
            "role": (
                "allocates the annual county forecast across MMWR weeks; it is "
                "not observed county-week truth"
            ),
            "scope": "national Lyme onset seasonality",
        },
        "analog_year_definition": {
            "current_role": "comparison_or_research_branch_unless_selected",
            "current_like_year_features": [
                "origin-year reported Lyme incidence",
                "trailing mean reported Lyme incidence",
            ],
            "not_currently_matched_on": [
                "daily weather",
                "tick abundance",
                "infected tick prevalence",
                "observed county-month cases",
            ],
        },
        "uncertainty": {
            "public_term": "forecast interval",
            "avoid_term": "clinical confidence interval",
            "interval_method": (
                record.annual_interval_method
                if record.annual_interval_available
                else "not_available"
            ),
            "interpretation": (
                "Intervals describe historical forecast residual uncertainty "
                "around reported-incidence proxy forecasts, not clinical "
                "certainty for a person or bite."
            ),
        },
        "update_policy": {
            "new_observed_data_steps": [
                "ingest reviewed county-year surveillance data with source caveats",
                "compare the prior forecast with the newly observed county-year outcome",
                "record residuals by county, branch, surveillance regime, and region",
                "refit eligible forecast branches when coverage is complete enough",
                "regenerate forecasts, intervals, scores, and source notes",
            ],
            "bayesian_update_status": "research_backtest_only",
            "bayesian_update_method": "gamma_poisson_case_multiplier",
            "promotion_rule": (
                "Bayesian or calibration updates are not promoted to public scores "
                "unless rolling-origin backtests show improved error or calibration."
            ),
        },
    }


def _forecast_basis_signals_used(record: CountyWeekRiskRecord) -> list[str]:
    signals = [
        "prior reported Lyme incidence",
        "trailing reported Lyme incidence",
        "county population denominator",
        "CDC national Lyme onset seasonality for display allocation",
    ]
    flags = set(split_quality_flags(record.feature_quality_flags))
    if (
        "localized_spatial_regime_feature" in flags
        or "forecast_safe_prior_history_spatial_regime" in flags
        or record.model_name == "empirical_bayes_spatial_regime_incidence"
    ):
        signals.append("localized spatial-regime prior incidence")
    if (
        "regional_county_adjacency_from_geojson" in flags
        or "spatial_neighbor_feature" in flags
        or "forecast_safe_prior_year_neighbor_signal" in flags
    ):
        signals.append("prior-year adjacent-county incidence")
    if record.model_family.startswith("empirical_bayes"):
        signals.append("empirical Bayes shrinkage toward a broader prior")
    return signals


def _manifest_payload(
    paths: StaticRiskExportPaths,
    *,
    weekly_payload: dict[str, object],
    county_payload: dict[str, object],
    generated_at: str,
    geography: _GeographyScope,
) -> dict[str, object]:
    files = [
        paths.weekly_risk_path.name,
        paths.county_metadata_path.name,
        paths.model_card_path.name,
        paths.source_catalog_path.name,
        paths.export_manifest_path.name,
    ]
    record_counts = {
        "weekly_risk": int(weekly_payload["record_count"]),
        "county_metadata": int(county_payload["county_count"]),
    }
    county_geojson_path = paths.export_manifest_path.parent / "md_counties.geojson"
    if geography.scope == MARYLAND_GEOGRAPHY_SCOPE and county_geojson_path.exists():
        files.append(county_geojson_path.name)
        record_counts["county_geojson_features"] = _county_geojson_feature_count(
            county_geojson_path
        )
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "static_export_manifest",
        "generated_at": generated_at,
        **_research_status_field(geography),
        "temporal_contract": TEMPORAL_CONTRACT,
        "files": files,
        "record_counts": record_counts,
    }


def _county_geojson_feature_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata_count = payload.get("metadata", {}).get("feature_count")
    if metadata_count is not None:
        return int(metadata_count)
    return len(payload.get("features", []))


def _selected_score_config(record: CountyWeekRiskRecord) -> dict[str, object]:
    config = {
        "model_name": record.model_name,
        "seasonality_source_id": record.seasonality_source_id,
        "benchmark_quantile": record.benchmark_quantile,
        "headroom_multiplier": record.headroom_multiplier,
        "score_denominator": record.score_denominator,
        "source_prediction_run_id": record.source_prediction_run_id,
        "source_prediction_sha256": record.source_prediction_sha256,
        "source_seasonality_sha256": record.source_seasonality_sha256,
    }
    if record.annual_interval_available:
        config["source_prediction_interval_sha256"] = (
            record.source_prediction_interval_sha256
        )
    return config


def _selected_forecast_metadata(
    records: CountyWeekRiskRecord | list[CountyWeekRiskRecord],
) -> dict[str, object]:
    selected = records if isinstance(records, list) else [records]
    record = selected[0]
    metadata = {
        "forecast_origin_year": record.forecast_origin_year,
        "as_of_date": record.as_of_date,
        "data_cutoff_date": record.data_cutoff_date,
        "source_vintage": record.source_vintage,
        "update_mode": record.update_mode,
    }
    forecast_years = sorted({row.year for row in selected})
    run_ids = _ordered_unique_run_ids(selected)
    if len(forecast_years) > 1:
        metadata["forecast_years"] = forecast_years
    if len(run_ids) > 1:
        metadata["source_prediction_run_ids"] = run_ids
    if record.annual_interval_available:
        metadata["annual_interval_available"] = True
        metadata["annual_interval_method"] = record.annual_interval_method
    return metadata


def _ordered_unique_run_ids(records: list[CountyWeekRiskRecord]) -> list[str]:
    first_year_by_run_id: dict[str, int] = {}
    for record in records:
        first_year_by_run_id.setdefault(record.source_prediction_run_id, record.year)
    return [
        run_id
        for run_id, _ in sorted(
            first_year_by_run_id.items(), key=lambda item: (item[1], item[0])
        )
    ]


def _year_selection(geography: _GeographyScope) -> str:
    if geography.scope == MIDATLANTIC_GEOGRAPHY_SCOPE:
        return "all_available_years"
    return "latest_available_per_county_mmwr_week"


def _annual_interval_metadata(record: CountyWeekRiskRecord) -> dict[str, object]:
    if not record.annual_interval_available:
        return {}
    return {
        "annual_interval_available": True,
        "annual_interval_method": record.annual_interval_method,
        "interval_sha256": record.source_prediction_interval_sha256,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
