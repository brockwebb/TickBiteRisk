from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
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

PUBLIC_CAVEATS = [
    "Informational and educational only; not medical advice.",
    "Does not diagnose disease or determine whether a person is infected.",
    "Not a treatment recommendation or substitute for a healthcare professional.",
    "Relative Maryland county-week Lyme forecast, not a per-bite infection probability.",
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

SCORE_CATEGORIES = {
    "1-2": "very_low",
    "3-4": "low",
    "5-6": "moderate",
    "7-8": "high",
    "9-10": "very_high",
}


class StaticExportInputError(ValueError):
    """Raised when static public export inputs are invalid."""


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
) -> StaticRiskExportPaths:
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
    )
    source_records = selected
    _validate_duplicate_keys(source_records)
    selected = _latest_records_by_county_week(selected)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = StaticRiskExportPaths(
        weekly_risk_path=output_dir / "md_county_risk_weekly.json",
        county_metadata_path=output_dir / "md_county_metadata.json",
        model_card_path=output_dir / "model_card.json",
        source_catalog_path=output_dir / "source_catalog.json",
        export_manifest_path=output_dir / "static_export_manifest.json",
    )
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    weekly_payload = _weekly_payload(
        selected,
        generated_at=generated_at,
        input_sha256=_sha256_file(scores_path),
    )
    county_payload = _county_metadata_payload(
        selected,
        source_records=source_records,
        generated_at=generated_at,
    )
    model_card_payload = _model_card_payload(
        selected,
        generated_at=generated_at,
        model_summary_path=model_summary_path,
    )
    source_catalog_payload = _source_catalog_payload(
        selected,
        generated_at=generated_at,
        input_sha256=_sha256_file(scores_path),
    )
    manifest_payload = _manifest_payload(
        paths,
        weekly_payload=weekly_payload,
        county_payload=county_payload,
        generated_at=generated_at,
    )

    _write_json(paths.weekly_risk_path, weekly_payload)
    _write_json(paths.county_metadata_path, county_payload)
    _write_json(paths.model_card_path, model_card_payload)
    _write_json(paths.source_catalog_path, source_catalog_payload)
    _write_json(paths.export_manifest_path, manifest_payload)
    return paths


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

    branches = {
        (
            record.model_name,
            record.seasonality_source_id,
            record.benchmark_quantile,
            record.headroom_multiplier,
            record.score_denominator,
            record.source_prediction_run_id,
            record.source_prediction_sha256,
            record.source_seasonality_sha256,
        )
        for record in selected
    }
    if len(branches) > 1:
        raise StaticExportInputError(
            "Multiple static export score branches found; provide selectors for "
            "model, seasonality source, score scale, and source version"
        )
    return sorted(
        selected,
        key=lambda row: (row.county_fips, row.year, row.mmwr_week),
    )


def _validate_duplicate_keys(records: list[CountyWeekRiskRecord]) -> None:
    seen = set()
    for record in records:
        key = (record.county_fips, record.year, record.mmwr_week)
        if key in seen:
            raise StaticExportInputError(
                "Duplicate county/year/MMWR week rows found after selectors"
            )
        seen.add(key)


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
) -> dict[str, object]:
    first = records[0]
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "md_county_risk_weekly",
        "generated_at": generated_at,
        "scope": "maryland_county_week",
        "geography": {
            "state": "MD",
            "state_fips": "24",
            "jurisdiction_count": len({record.county_fips for record in records}),
        },
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
        "year_selection": "latest_available_per_county_mmwr_week",
        "selected_score_config": _selected_score_config(first),
        "selected_forecast_metadata": _selected_forecast_metadata(first),
        "score_scale": {
            "range": [1, 10],
            "categories": SCORE_CATEGORIES,
            "score_denominator": first.score_denominator,
            "benchmark_quantile": first.benchmark_quantile,
            "headroom_multiplier": first.headroom_multiplier,
        },
        "input_artifact_sha256": input_sha256,
        "caveats": PUBLIC_CAVEATS,
        "guidance_links": GUIDANCE_LINKS,
        "records": [_weekly_record(record) for record in records],
    }


def _weekly_record(record: CountyWeekRiskRecord) -> dict[str, object]:
    return {
        "county_fips": record.county_fips,
        "county_name": record.county_name,
        "year": record.year,
        "data_year": record.year,
        "mmwr_week": record.mmwr_week,
        "period_label": record.period_label,
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


def _county_metadata_payload(
    records: list[CountyWeekRiskRecord],
    *,
    source_records: list[CountyWeekRiskRecord],
    generated_at: str,
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
        "export_type": "md_county_metadata",
        "generated_at": generated_at,
        "geography": "MD county/jurisdiction",
        "county_count": len(counties),
        "counties": counties,
    }


def _model_card_payload(
    records: list[CountyWeekRiskRecord],
    *,
    generated_at: str,
    model_summary_path: Path | None,
) -> dict[str, object]:
    first = records[0]
    payload: dict[str, object] = {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "model_card",
        "generated_at": generated_at,
        "model_name": first.model_name,
        "target_definition": "lyme_incidence_per_100k",
        "product_framing": (
            "Lyme risk forecasting tool for Maryland county-week conditions"
        ),
        "score_interpretation": (
            "Relative seasonal Lyme forecast on a 1-10 Maryland scale; not a "
            "per-bite infection probability."
        ),
        "not_for": [
            "per-bite infection probability",
            "diagnosis",
            "treatment recommendation",
            "weather-adjusted forecast",
        ],
        "clinical_disclaimer": CLINICAL_DISCLAIMER,
        "method_summary": (
            "Selected annual forecast rows apportioned by "
            "CDC national MMWR-week Lyme onset seasonality."
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
        "explainer_placeholders": EXPLAINER_PLACEHOLDERS,
        "annual_prediction_source": _annual_prediction_source(first),
        "quality_flags": [
            "relative_seasonal_baseline",
            "static_seasonality_prior",
            "not_weather_adjusted",
        ],
        "caveats": PUBLIC_CAVEATS,
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
        for row in csv.DictReader(handle):
            if (
                row.get("run_id") == selected.source_prediction_run_id
                and row.get("model_name") == selected.model_name
            ):
                return {
                    "run_id": str(row["run_id"]),
                    "model_name": str(row["model_name"]),
                    "rank_by_mae": _optional_int(row.get("rank_by_mae")),
                    "n_predictions": _optional_int(row.get("n_predictions")),
                    "mae_incidence_per_100k": _optional_float(
                        row.get("mae_incidence_per_100k")
                    ),
                    "rmse_incidence_per_100k": _optional_float(
                        row.get("rmse_incidence_per_100k")
                    ),
                    "pearson_correlation": _optional_float(
                        row.get("pearson_correlation")
                    ),
                    "comparison_assumption_flags": split_quality_flags(
                        row.get("comparison_assumption_flags", "")
                    ),
                }
    raise StaticExportInputError(
        "No model comparison summary row matched selected run_id="
        f"{selected.source_prediction_run_id} and model_name={selected.model_name}"
    )


def _source_catalog_payload(
    records: list[CountyWeekRiskRecord],
    *,
    generated_at: str,
    input_sha256: str,
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
                    "and CDC seasonality; do not publish raw restricted or "
                    "terms-unclear source extracts."
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
                **_selected_forecast_metadata(first),
                "notes": (
                    "Selected annual forecast rows from prior-year validation; "
                    "not raw surveillance data."
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
    }


def _annual_prediction_source(record: CountyWeekRiskRecord) -> dict[str, object]:
    return {
        "artifact_type": "annual_prediction_branch",
        "run_id": record.source_prediction_run_id,
        "sha256": record.source_prediction_sha256,
        "model_name": record.model_name,
        "model_family": record.model_family,
        "evaluation_mode": record.evaluation_mode,
        "weather_mode": record.weather_mode,
        **_selected_forecast_metadata(record),
    }


def _manifest_payload(
    paths: StaticRiskExportPaths,
    *,
    weekly_payload: dict[str, object],
    county_payload: dict[str, object],
    generated_at: str,
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
    if county_geojson_path.exists():
        files.append(county_geojson_path.name)
        record_counts["county_geojson_features"] = _county_geojson_feature_count(
            county_geojson_path
        )
    return {
        "schema_version": STATIC_EXPORT_SCHEMA_VERSION,
        "export_type": "static_export_manifest",
        "generated_at": generated_at,
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
    return {
        "model_name": record.model_name,
        "seasonality_source_id": record.seasonality_source_id,
        "benchmark_quantile": record.benchmark_quantile,
        "headroom_multiplier": record.headroom_multiplier,
        "score_denominator": record.score_denominator,
        "source_prediction_run_id": record.source_prediction_run_id,
        "source_prediction_sha256": record.source_prediction_sha256,
        "source_seasonality_sha256": record.source_seasonality_sha256,
    }


def _selected_forecast_metadata(record: CountyWeekRiskRecord) -> dict[str, object]:
    return {
        "forecast_origin_year": record.forecast_origin_year,
        "as_of_date": record.as_of_date,
        "data_cutoff_date": record.data_cutoff_date,
        "source_vintage": record.source_vintage,
        "update_mode": record.update_mode,
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
