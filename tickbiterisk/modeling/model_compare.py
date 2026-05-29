from __future__ import annotations

import csv
import hashlib
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


COMPARISON_ASSUMPTION_FLAGS = (
    "observational_not_causal,"
    "retrospective_weather_reconstruction,"
    "intervention_history_unmodeled,"
    "surveillance_reporting_sensitive"
)
TARGET_DEFINITION = "lyme_incidence_per_100k"
EVALUATION_MODE = "rolling_origin_prior_years"
WEATHER_MODE = "retrospective_current_year_weather"
RUN_WEATHER_MODE = "mixed_model_specific"
FORECAST_SAFE_WEATHER_MODE = "not_used_by_forecast_safe_model"
LAGGED_WEATHER_MODE = "not_used_by_lagged_model"
ANALOG_BOOTSTRAP_SEED = 1337
ANALOG_BOOTSTRAP_ITERATIONS = 200
ANALOG_NEIGHBOR_COUNT = 5
ANALOG_FEATURE_PROFILE = "forecast_safe_analog_years"
ANALOG_INTERVAL_METHOD = "weighted_analog_bootstrap"
RANDOM_FOREST_FEATURE_PROFILE = "forecast_safe_lagged_ecology_spatial_regional"
RANDOM_FOREST_N_ESTIMATORS = 200
RANDOM_FOREST_MIN_SAMPLES_LEAF = 3
RANDOM_FOREST_MAX_FEATURES = "sqrt"
RANDOM_FOREST_RANDOM_STATE = 1337
RANDOM_FOREST_ALLOWED_MAX_FEATURES = {"sqrt", "log2"}
EXCLUDED_FEATURE_PREFIXES = (
    "feature_tick_",
    "feature_regional_diagnostic_",
)
EXCLUDED_FEATURE_NAMES = {
    "feature_regional_incidence_cluster_cluster_id",
}
REQUIRED_MODEL_COMPARISON_COLUMNS = [
    "county_fips",
    "year",
    "target_total_cases",
    "target_population",
    "target_lyme_incidence_per_100k",
]
FORECAST_SAFE_EXACT_FEATURES = {
    "feature_year",
    "feature_prior_year_lyme_incidence_per_100k",
    "feature_trailing_history_years",
    "feature_missing_prior_year_lyme_incidence",
    "feature_state_prior_year_lyme_incidence_per_100k",
    "feature_missing_state_prior_year_lyme_incidence",
    "feature_log_population_offset",
}
FORECAST_SAFE_TRAILING_PREFIX = "feature_trailing_"
FORECAST_SAFE_TRAILING_SUFFIX = "yr_mean_lyme_incidence_per_100k"
FORECAST_ECOLOGY_EXACT_FEATURES = {
    "feature_deer_total_harvest_prior_season",
    "feature_deer_harvest_per_sqmi_prior_season",
    "feature_missing_deer_harvest_prior_season",
    "feature_missing_deer_total_harvest_prior_season",
    "feature_missing_deer_harvest_per_sqmi_prior_season",
    "feature_deer_is_derived_total",
    "feature_missing_deer_is_derived_total",
    "feature_mast_index_prior_year",
    "feature_acorn_index_prior_year",
    "feature_hard_mast_index_prior_year",
    "feature_soft_mast_index_prior_year",
    "feature_black_oak_acorns_per_branch_prior_year",
    "feature_white_oak_acorns_per_branch_prior_year",
    "feature_unit_average_acorns_per_branch_prior_year",
    "feature_white_oak_subjective_crown_pct_prior_year",
    "feature_black_oak_subjective_crown_pct_prior_year",
    "feature_missing_mast_index_prior_year",
    "feature_missing_acorn_index_prior_year",
    "feature_missing_hard_mast_index_prior_year",
    "feature_missing_soft_mast_index_prior_year",
    "feature_missing_black_oak_acorns_per_branch_prior_year",
    "feature_missing_white_oak_acorns_per_branch_prior_year",
    "feature_missing_unit_average_acorns_per_branch_prior_year",
    "feature_missing_white_oak_subjective_crown_pct_prior_year",
    "feature_missing_black_oak_subjective_crown_pct_prior_year",
    "feature_units_authorized_per_sqmi_prior_year",
    "feature_units_authorized_per_100k_prior_year",
    "feature_units_authorized_per_sqmi_trailing_3yr_mean",
    "feature_units_authorized_per_100k_trailing_3yr_mean",
    "feature_missing_units_authorized_per_sqmi_prior_year",
    "feature_missing_units_authorized_per_100k_prior_year",
    "feature_missing_units_authorized_per_sqmi_trailing_3yr_mean",
    "feature_missing_units_authorized_per_100k_trailing_3yr_mean",
    "feature_population_prior_year",
    "feature_population_change_prior_year",
    "feature_population_pct_change_prior_year",
    "feature_population_pct_change_trailing_3yr_mean",
    "feature_missing_population_prior_year",
    "feature_missing_population_change_prior_year",
    "feature_missing_population_pct_change_prior_year",
    "feature_missing_population_pct_change_trailing_3yr_mean",
    "feature_age_structure_median_age_prior_year",
    "feature_age_structure_under5_share_prior_year",
    "feature_age_structure_age5_17_share_prior_year",
    "feature_age_structure_age18_24_share_prior_year",
    "feature_age_structure_age25_44_share_prior_year",
    "feature_age_structure_age45_64_share_prior_year",
    "feature_age_structure_age65plus_share_prior_year",
    "feature_missing_age_structure_median_age_prior_year",
    "feature_missing_age_structure_under5_share_prior_year",
    "feature_missing_age_structure_age5_17_share_prior_year",
    "feature_missing_age_structure_age18_24_share_prior_year",
    "feature_missing_age_structure_age25_44_share_prior_year",
    "feature_missing_age_structure_age45_64_share_prior_year",
    "feature_missing_age_structure_age65plus_share_prior_year",
    "feature_ecological_pressure_prior_year_index",
    "feature_ecological_pressure_component_count",
    "feature_missing_ecological_pressure_prior_year_index",
    "feature_forest_pct",
    "feature_forest_woody_wetland_pct",
    "feature_wetland_pct",
    "feature_emergent_wetland_pct",
    "feature_developed_pct",
    "feature_impervious_pct",
    "feature_agriculture_pct",
    "feature_pasture_hay_pct",
    "feature_cultivated_crop_pct",
    "feature_riparian_natural_45m_pct",
    "feature_riparian_forest_45m_pct",
    "feature_riparian_forest_woody_wetland_45m_pct",
    "feature_natural_land_cover_index",
    "feature_missing_forest_pct",
    "feature_missing_forest_woody_wetland_pct",
    "feature_missing_wetland_pct",
    "feature_missing_emergent_wetland_pct",
    "feature_missing_developed_pct",
    "feature_missing_impervious_pct",
    "feature_missing_agriculture_pct",
    "feature_missing_pasture_hay_pct",
    "feature_missing_cultivated_crop_pct",
    "feature_missing_riparian_natural_45m_pct",
    "feature_missing_riparian_forest_45m_pct",
    "feature_missing_riparian_forest_woody_wetland_45m_pct",
    "feature_missing_natural_land_cover_index",
    "feature_usdm_prior_year_dsci_mean",
    "feature_usdm_prior_year_dsci_max",
    "feature_usdm_prior_year_weeks_d0_or_worse",
    "feature_usdm_prior_year_weeks_d1_or_worse",
    "feature_usdm_prior_year_weeks_d2_or_worse",
    "feature_usdm_prior_year_tick_season_dsci_mean",
    "feature_usdm_prior_year_tick_season_weeks_d1_or_worse",
    "feature_missing_usdm_prior_year_dsci_mean",
    "feature_missing_usdm_prior_year_dsci_max",
    "feature_missing_usdm_prior_year_weeks_d0_or_worse",
    "feature_missing_usdm_prior_year_weeks_d1_or_worse",
    "feature_missing_usdm_prior_year_weeks_d2_or_worse",
    "feature_missing_usdm_prior_year_tick_season_dsci_mean",
    "feature_missing_usdm_prior_year_tick_season_weeks_d1_or_worse",
    "feature_oni_prior_year_mean_anomaly_c",
    "feature_oni_prior_year_max_anomaly_c",
    "feature_oni_prior_year_min_anomaly_c",
    "feature_oni_prior_year_el_nino_season_count",
    "feature_oni_prior_year_la_nina_season_count",
    "feature_missing_oni_prior_year_mean_anomaly_c",
    "feature_missing_oni_prior_year_max_anomaly_c",
    "feature_missing_oni_prior_year_min_anomaly_c",
    "feature_missing_oni_prior_year_el_nino_season_count",
    "feature_missing_oni_prior_year_la_nina_season_count",
    "feature_mei_v2_prior_year_mean",
    "feature_mei_v2_prior_year_max",
    "feature_mei_v2_prior_year_min",
    "feature_mei_v2_prior_year_positive_month_count",
    "feature_mei_v2_prior_year_negative_month_count",
    "feature_missing_mei_v2_prior_year_mean",
    "feature_missing_mei_v2_prior_year_max",
    "feature_missing_mei_v2_prior_year_min",
    "feature_missing_mei_v2_prior_year_positive_month_count",
    "feature_missing_mei_v2_prior_year_negative_month_count",
}
AGE_STRUCTURE_EXACT_FEATURES = {
    "feature_age_structure_median_age_prior_year",
    "feature_age_structure_under5_share_prior_year",
    "feature_age_structure_age5_17_share_prior_year",
    "feature_age_structure_age18_24_share_prior_year",
    "feature_age_structure_age25_44_share_prior_year",
    "feature_age_structure_age45_64_share_prior_year",
    "feature_age_structure_age65plus_share_prior_year",
    "feature_missing_age_structure_median_age_prior_year",
    "feature_missing_age_structure_under5_share_prior_year",
    "feature_missing_age_structure_age5_17_share_prior_year",
    "feature_missing_age_structure_age18_24_share_prior_year",
    "feature_missing_age_structure_age25_44_share_prior_year",
    "feature_missing_age_structure_age45_64_share_prior_year",
    "feature_missing_age_structure_age65plus_share_prior_year",
}
FORECAST_SPATIAL_EXACT_FEATURES = {
    "feature_neighbor_prior_year_lyme_incidence_mean",
    "feature_neighbor_prior_year_lyme_incidence_max",
    "feature_neighbor_prior_year_count",
    "feature_missing_neighbor_prior_year_lyme_incidence",
}
FORECAST_REGIONAL_SIGNAL_EXACT_FEATURES = {
    "feature_regional_prior_year_total_cases",
    "feature_regional_prior_year_county_share_of_state_cases",
    "feature_regional_prior_year_county_share_of_midatlantic_cases",
    "feature_regional_prior_year_state_total_cases",
    "feature_regional_prior_year_midatlantic_total_cases",
    "feature_regional_trailing_5yr_midatlantic_total_min",
    "feature_regional_trailing_5yr_midatlantic_total_mean",
    "feature_regional_trailing_5yr_midatlantic_total_max",
    "feature_missing_regional_prior_year_total_cases",
    "feature_missing_regional_prior_year_county_share_of_state_cases",
    "feature_missing_regional_prior_year_county_share_of_midatlantic_cases",
    "feature_missing_regional_prior_year_state_total_cases",
    "feature_missing_regional_prior_year_midatlantic_total_cases",
    "feature_missing_regional_trailing_5yr_midatlantic_total_min",
    "feature_missing_regional_trailing_5yr_midatlantic_total_mean",
    "feature_missing_regional_trailing_5yr_midatlantic_total_max",
}
REGIONAL_INCIDENCE_CLUSTER_EXACT_FEATURES = {
    "feature_regional_incidence_cluster_rank",
    "feature_regional_incidence_cluster_centroid_prior_mean_incidence_per_100k",
    "feature_regional_incidence_cluster_prior_mean_incidence_per_100k",
    "feature_regional_incidence_cluster_prior_min_incidence_per_100k",
    "feature_regional_incidence_cluster_prior_max_incidence_per_100k",
    "feature_regional_incidence_cluster_prior_sd_incidence_per_100k",
    "feature_regional_incidence_cluster_prior_year_incidence_per_100k",
    "feature_regional_incidence_cluster_train_year_count",
    "feature_regional_incidence_cluster_band_low",
    "feature_regional_incidence_cluster_band_moderate",
    "feature_regional_incidence_cluster_band_high",
    "feature_regional_incidence_cluster_band_very_high",
    "feature_missing_regional_incidence_cluster",
}
FORECAST_REGIONAL_EXACT_FEATURES = (
    FORECAST_REGIONAL_SIGNAL_EXACT_FEATURES
    | REGIONAL_INCIDENCE_CLUSTER_EXACT_FEATURES
)


class ModelComparisonInputError(ValueError):
    """Raised when model comparison inputs or options are invalid."""


@dataclass(frozen=True)
class ModelComparisonRun:
    run_id: str
    design_matrix_path: str
    design_matrix_sha256: str
    start_year: int
    end_year: int
    min_train_years: int
    ridge_alpha: float
    shrinkage_strength: float
    random_forest_n_estimators: int
    random_forest_min_samples_leaf: int
    random_forest_max_features: str
    random_forest_random_state: int
    model_names: str
    target_definition: str
    evaluation_mode: str
    weather_mode: str
    feature_set: str
    n_design_rows: int
    n_predictions: int
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelComparisonPrediction:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    train_row_count: int
    train_county_count: int
    actual_cases: int
    actual_population: int
    actual_incidence_per_100k: float
    predicted_cases: float
    predicted_incidence_per_100k: float
    residual_incidence_per_100k: float
    absolute_error_incidence_per_100k: float
    residual_cases: float
    absolute_error_cases: float
    model_feature_quality_flags: str
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelComparisonMetric:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    aggregation: str
    test_year: int | None
    n_predictions: int
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    mean_bias_incidence_per_100k: float
    mae_cases: float
    rmse_cases: float
    pearson_correlation: float | None
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelComparisonInterval:
    run_id: str
    model_name: str
    model_family: str
    target_definition: str
    feature_set: str
    feature_profile: str
    evaluation_mode: str
    weather_mode: str
    source_file_sha256: str
    county_fips: str
    county_name: str
    test_year: int
    train_start_year: int
    train_end_year: int
    interval_method: str
    bootstrap_seed: int
    bootstrap_iterations: int
    analog_count: int
    analog_years: str
    analog_counties: str
    analog_weights: str
    lower_80_incidence_per_100k: float
    median_incidence_per_100k: float
    upper_80_incidence_per_100k: float
    lower_95_incidence_per_100k: float
    upper_95_incidence_per_100k: float
    observed_incidence_per_100k: float
    covered_80: bool
    covered_95: bool
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelComparisonSummary:
    run_id: str
    rank_by_mae: int
    model_name: str
    model_family: str
    feature_profile: str
    n_predictions: int
    mae_incidence_per_100k: float
    rmse_incidence_per_100k: float
    pearson_correlation: float | None
    comparison_assumption_flags: str


@dataclass(frozen=True)
class ModelComparisonResult:
    run_id: str
    run: ModelComparisonRun
    predictions: list[ModelComparisonPrediction]
    intervals: list[ModelComparisonInterval]
    metrics: list[ModelComparisonMetric]
    summary: list[ModelComparisonSummary]


@dataclass(frozen=True)
class _DesignRow:
    county_fips: str
    county_name: str
    year: int
    actual_cases: int
    population: int
    incidence_per_100k: float
    features: dict[str, float]
    model_feature_quality_flags: str


@dataclass(frozen=True)
class _FittedRidgeModel:
    columns: list[str]
    means: dict[str, float]
    scales: dict[str, float]
    coefficients: list[float]
    train_state_mean: float


def run_model_comparison(
    *,
    design_matrix_path: Path,
    start_year: int,
    end_year: int | None = None,
    min_train_years: int = 5,
    ridge_alpha: float = 1.0,
    shrinkage_strength: float = 5.0,
    random_forest_n_estimators: int = RANDOM_FOREST_N_ESTIMATORS,
    random_forest_min_samples_leaf: int = RANDOM_FOREST_MIN_SAMPLES_LEAF,
    random_forest_max_features: str = RANDOM_FOREST_MAX_FEATURES,
    random_forest_random_state: int = RANDOM_FOREST_RANDOM_STATE,
) -> ModelComparisonResult:
    if min_train_years < 1:
        raise ModelComparisonInputError("min_train_years must be at least 1")
    if ridge_alpha <= 0:
        raise ModelComparisonInputError("ridge_alpha must be greater than 0")
    if shrinkage_strength < 0:
        raise ModelComparisonInputError("shrinkage_strength must be non-negative")
    if random_forest_n_estimators < 1:
        raise ModelComparisonInputError(
            "random_forest_n_estimators must be at least 1"
        )
    if random_forest_min_samples_leaf < 1:
        raise ModelComparisonInputError(
            "random_forest_min_samples_leaf must be at least 1"
        )
    if random_forest_max_features not in RANDOM_FOREST_ALLOWED_MAX_FEATURES:
        allowed = ", ".join(sorted(RANDOM_FOREST_ALLOWED_MAX_FEATURES))
        raise ModelComparisonInputError(
            "random_forest_max_features must be one of: " f"{allowed}"
        )

    rows, feature_columns = _read_design_rows(design_matrix_path)
    if not rows:
        raise ModelComparisonInputError("model design matrix has no usable rows")
    input_min_year = min(row.year for row in rows)
    input_max_year = max(row.year for row in rows)
    if start_year < input_min_year or start_year > input_max_year:
        raise ModelComparisonInputError(
            f"start-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    resolved_end_year = end_year if end_year is not None else input_max_year
    if resolved_end_year < input_min_year or resolved_end_year > input_max_year:
        raise ModelComparisonInputError(
            f"end-year must be between input years {input_min_year} and "
            f"{input_max_year}"
        )
    if start_year > resolved_end_year:
        raise ModelComparisonInputError("start_year must be less than or equal to end_year")

    source_sha = _sha256_file(design_matrix_path)
    run_id = (
        f"model_compare_start{start_year}_end{resolved_end_year}_"
        f"mintrain{min_train_years}_ridge{_slug_float(ridge_alpha)}_"
        f"shrink{_slug_float(shrinkage_strength)}_"
        f"rf{random_forest_n_estimators}_leaf{random_forest_min_samples_leaf}_"
        f"max{random_forest_max_features}_seed{random_forest_random_state}"
    )
    predictions: list[ModelComparisonPrediction] = []
    intervals: list[ModelComparisonInterval] = []
    for test_year in range(start_year, resolved_end_year + 1):
        train_rows = [row for row in rows if row.year < test_year]
        if not _has_training_depth(train_rows, min_train_years=min_train_years):
            continue
        test_rows = [row for row in rows if row.year == test_year]
        if not test_rows:
            continue
        train_start_year = min(row.year for row in train_rows)
        train_end_year = max(row.year for row in train_rows)
        train_county_count = len({row.county_fips for row in train_rows})
        ridge_cache: dict[
            tuple[float, tuple[str, ...]], _FittedRidgeModel
        ] = {}
        random_forest_cache: dict[
            tuple[int, int, str, int, tuple[str, ...]], object
        ] = {}
        for row in test_rows:
            for model_name, model_family, profile, predicted in _predict_models(
                row=row,
                train_rows=train_rows,
                feature_columns=feature_columns,
                ridge_alpha=ridge_alpha,
                shrinkage_strength=shrinkage_strength,
                ridge_cache=ridge_cache,
                random_forest_n_estimators=random_forest_n_estimators,
                random_forest_min_samples_leaf=random_forest_min_samples_leaf,
                random_forest_max_features=random_forest_max_features,
                random_forest_random_state=random_forest_random_state,
                random_forest_cache=random_forest_cache,
            ):
                predictions.append(
                    _prediction_row(
                        run_id=run_id,
                        model_name=model_name,
                        model_family=model_family,
                        feature_profile=profile,
                        row=row,
                        predicted_incidence=predicted,
                        source_sha=source_sha,
                        train_start_year=train_start_year,
                        train_end_year=train_end_year,
                        train_row_count=len(train_rows),
                        train_county_count=train_county_count,
                    )
                )
                if model_name == "analog_year_forecast":
                    intervals.append(
                        _analog_interval_row(
                            run_id=run_id,
                            row=row,
                            train_rows=train_rows,
                            feature_columns=feature_columns,
                            source_sha=source_sha,
                            train_start_year=train_start_year,
                            train_end_year=train_end_year,
                        )
                    )
    metrics = _metric_rows(run_id, predictions)
    summary = _summary_rows(run_id, metrics)
    model_names = ",".join(sorted({row.model_name for row in predictions}))
    run = ModelComparisonRun(
        run_id=run_id,
        design_matrix_path=str(design_matrix_path),
        design_matrix_sha256=source_sha,
        start_year=start_year,
        end_year=resolved_end_year,
        min_train_years=min_train_years,
        ridge_alpha=ridge_alpha,
        shrinkage_strength=shrinkage_strength,
        random_forest_n_estimators=random_forest_n_estimators,
        random_forest_min_samples_leaf=random_forest_min_samples_leaf,
        random_forest_max_features=random_forest_max_features,
        random_forest_random_state=random_forest_random_state,
        model_names=model_names,
        target_definition=TARGET_DEFINITION,
        evaluation_mode=EVALUATION_MODE,
        weather_mode=RUN_WEATHER_MODE,
        feature_set="safe_numeric_design_matrix",
        n_design_rows=len(rows),
        n_predictions=len(predictions),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )
    return ModelComparisonResult(
        run_id=run_id,
        run=run,
        predictions=predictions,
        intervals=intervals,
        metrics=metrics,
        summary=summary,
    )


def _read_design_rows(path: Path) -> tuple[list[_DesignRow], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        fieldname_set = set(fieldnames)
        missing_columns = [
            column
            for column in REQUIRED_MODEL_COMPARISON_COLUMNS
            if column not in fieldname_set
        ]
        if missing_columns:
            raise ModelComparisonInputError(
                "missing required model comparison column(s): "
                f"{', '.join(missing_columns)}"
            )
        feature_columns = [
            column
            for column in fieldnames
            if _is_safe_feature_column(column)
        ]
        rows = [
            _DesignRow(
                county_fips=str(row["county_fips"]).zfill(5),
                county_name=str(row.get("county_name", "")),
                year=int(row["year"]),
                actual_cases=_parse_int(row["target_total_cases"]),
                population=_parse_int(row["target_population"]),
                incidence_per_100k=_parse_float(
                    row["target_lyme_incidence_per_100k"]
                ),
                features={
                    column: _parse_float(row.get(column, ""))
                    for column in feature_columns
                },
                model_feature_quality_flags=str(
                    row.get("model_feature_quality_flags", "")
                ),
            )
            for row in reader
            if _parse_int(row["target_population"]) > 0
        ]
    return rows, feature_columns


def _is_safe_feature_column(column: str) -> bool:
    return (
        column.startswith("feature_")
        and column not in EXCLUDED_FEATURE_NAMES
        and not column.startswith(EXCLUDED_FEATURE_PREFIXES)
        and not column.startswith("feature_flag_")
        and "_actual_" not in column
    )


def _is_forecast_safe_feature_column(column: str) -> bool:
    return (
        column in FORECAST_SAFE_EXACT_FEATURES
        or _is_trailing_mean_incidence_feature(column)
    )


def _is_trailing_mean_incidence_feature(column: str) -> bool:
    if not (
        column.startswith(FORECAST_SAFE_TRAILING_PREFIX)
        and column.endswith(FORECAST_SAFE_TRAILING_SUFFIX)
    ):
        return False
    window = column[
        len(FORECAST_SAFE_TRAILING_PREFIX) : -len(FORECAST_SAFE_TRAILING_SUFFIX)
    ]
    return window.isdigit()


def _is_forecast_ecology_feature_column(column: str) -> bool:
    return (
        _is_forecast_safe_feature_column(column)
        or column in FORECAST_ECOLOGY_EXACT_FEATURES
    )


def _is_forecast_spatial_feature_column(column: str) -> bool:
    return (
        _is_forecast_safe_feature_column(column)
        or column in FORECAST_SPATIAL_EXACT_FEATURES
    )


def _is_forecast_regional_feature_column(column: str) -> bool:
    return (
        _is_forecast_safe_feature_column(column)
        or column in FORECAST_REGIONAL_EXACT_FEATURES
    )


def _is_forecast_regional_signal_feature_column(column: str) -> bool:
    return (
        _is_forecast_safe_feature_column(column)
        or column in FORECAST_REGIONAL_SIGNAL_EXACT_FEATURES
    )


def _is_random_forest_forecast_feature_column(column: str) -> bool:
    return _is_safe_feature_column(column) and (
        _is_forecast_safe_feature_column(column)
        or _is_forecast_ecology_feature_column(column)
        or _is_forecast_spatial_feature_column(column)
        or _is_forecast_regional_feature_column(column)
    )


def _is_regional_incidence_cluster_feature_column(column: str) -> bool:
    return column in REGIONAL_INCIDENCE_CLUSTER_EXACT_FEATURES


def _is_age_structure_feature_column(column: str) -> bool:
    return column in AGE_STRUCTURE_EXACT_FEATURES


def _is_analog_feature_column(column: str) -> bool:
    return (
        _is_forecast_spatial_feature_column(column)
        or (
            _is_forecast_ecology_feature_column(column)
            and not _is_age_structure_feature_column(column)
        )
        or _is_forecast_regional_signal_feature_column(column)
    )


def _is_retrospective_weather_ecology_feature_column(column: str) -> bool:
    return (
        not _is_regional_incidence_cluster_feature_column(column)
        and not _is_age_structure_feature_column(column)
    )


def _has_training_depth(
    rows: list[_DesignRow],
    *,
    min_train_years: int,
) -> bool:
    by_county: dict[str, set[int]] = {}
    for row in rows:
        by_county.setdefault(row.county_fips, set()).add(row.year)
    return any(len(years) >= min_train_years for years in by_county.values())


def _predict_models(
    *,
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    ridge_alpha: float,
    shrinkage_strength: float,
    ridge_cache: dict[tuple[float, tuple[str, ...]], _FittedRidgeModel],
    random_forest_n_estimators: int,
    random_forest_min_samples_leaf: int,
    random_forest_max_features: str,
    random_forest_random_state: int,
    random_forest_cache: dict[tuple[int, int, str, int, tuple[str, ...]], object],
) -> list[tuple[str, str, str, float]]:
    prior_prediction = row.features.get(
        "feature_prior_year_lyme_incidence_per_100k", 0.0
    )
    trailing_prediction = _county_trailing_mean(row, train_rows)
    predictions = [
        (
            "prior_year_incidence",
            "baseline",
            "lagged_outcome",
            prior_prediction,
        ),
        (
            "trailing_mean_incidence",
            "baseline",
            "lagged_outcome",
            trailing_prediction,
        ),
        (
            "linear_blend_baseline",
            "ensemble",
            "lagged_outcome_blend",
            mean([prior_prediction, trailing_prediction]),
        ),
        (
            "empirical_bayes_shrinkage",
            "empirical_bayes",
            "lagged_outcome_with_shrinkage",
            _empirical_bayes_prediction(row, train_rows, shrinkage_strength),
        ),
    ]
    predictions.append(
        (
            "analog_year_forecast",
            "analog",
            ANALOG_FEATURE_PROFILE,
            _analog_prediction(row, train_rows, feature_columns),
        )
    )
    forecast_columns = [
        column for column in feature_columns if _is_forecast_safe_feature_column(column)
    ]
    forecast_ridge_prediction = _ridge_prediction(
        row=row,
        train_rows=train_rows,
        feature_columns=forecast_columns,
        ridge_alpha=ridge_alpha,
        ridge_cache=ridge_cache,
    )
    predictions.append(
        (
            "ridge_forecast_safe",
            "regularized_linear",
            "forecast_safe_lagged",
            forecast_ridge_prediction,
        )
    )
    random_forest_columns = [
        column
        for column in feature_columns
        if _is_random_forest_forecast_feature_column(column)
    ]
    predictions.append(
        (
            "random_forest_forecast_research",
            "random_forest",
            RANDOM_FOREST_FEATURE_PROFILE,
            _random_forest_prediction(
                row=row,
                train_rows=train_rows,
                feature_columns=random_forest_columns,
                n_estimators=random_forest_n_estimators,
                min_samples_leaf=random_forest_min_samples_leaf,
                max_features=random_forest_max_features,
                random_state=random_forest_random_state,
                random_forest_cache=random_forest_cache,
            ),
        )
    )
    if any(column in FORECAST_SPATIAL_EXACT_FEATURES for column in feature_columns):
        spatial_columns = [
            column
            for column in feature_columns
            if _is_forecast_spatial_feature_column(column)
        ]
        spatial_ridge_prediction = _ridge_prediction(
            row=row,
            train_rows=train_rows,
            feature_columns=spatial_columns,
            ridge_alpha=ridge_alpha,
            ridge_cache=ridge_cache,
        )
        predictions.append(
            (
                "ridge_forecast_spatial",
                "regularized_linear",
                "forecast_safe_lagged_spatial",
                spatial_ridge_prediction,
            )
        )
    if any(column in FORECAST_REGIONAL_EXACT_FEATURES for column in feature_columns):
        regional_columns = [
            column
            for column in feature_columns
            if _is_forecast_regional_feature_column(column)
        ]
        regional_ridge_prediction = _ridge_prediction(
            row=row,
            train_rows=train_rows,
            feature_columns=regional_columns,
            ridge_alpha=ridge_alpha,
            ridge_cache=ridge_cache,
        )
        predictions.append(
            (
                "ridge_forecast_regional",
                "regularized_linear",
                "forecast_safe_lagged_regional",
                regional_ridge_prediction,
            )
        )
    ecology_columns = [
        column for column in feature_columns if _is_forecast_ecology_feature_column(column)
    ]
    ecology_ridge_prediction = _ridge_prediction(
        row=row,
        train_rows=train_rows,
        feature_columns=ecology_columns,
        ridge_alpha=ridge_alpha,
        ridge_cache=ridge_cache,
    )
    predictions.append(
        (
            "ridge_forecast_ecology",
            "regularized_linear",
            "forecast_safe_lagged_ecology",
            ecology_ridge_prediction,
        )
    )
    retrospective_columns = [
        column
        for column in feature_columns
        if _is_retrospective_weather_ecology_feature_column(column)
    ]
    ridge_prediction = _ridge_prediction(
        row=row,
        train_rows=train_rows,
        feature_columns=retrospective_columns,
        ridge_alpha=ridge_alpha,
        ridge_cache=ridge_cache,
    )
    predictions.append(
        (
            "ridge_lag_weather_ecology",
            "regularized_linear",
            "retrospective_weather_ecology",
            ridge_prediction,
        )
    )
    return predictions


def _analog_prediction(
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
) -> float:
    forecast = _analog_forecast(row, train_rows, feature_columns)
    return forecast[0]


def _analog_forecast(
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
) -> tuple[float, list[tuple[_DesignRow, float, float]]]:
    columns = [
        column
        for column in feature_columns
        if _is_analog_feature_column(column)
    ]
    if not train_rows or not columns:
        return _county_trailing_mean(row, train_rows), []
    means = {
        column: mean(train_row.features.get(column, 0.0) for train_row in train_rows)
        for column in columns
    }
    scales = {
        column: _stddev(
            [train_row.features.get(column, 0.0) for train_row in train_rows]
        )
        for column in columns
    }
    distances = []
    for train_row in train_rows:
        squared_distance = sum(
            (
                _standardized(row.features.get(column, 0.0), means[column], scales[column])
                - _standardized(
                    train_row.features.get(column, 0.0),
                    means[column],
                    scales[column],
                )
            )
            ** 2
            for column in columns
        )
        distances.append((math.sqrt(squared_distance), train_row))
    nearest = sorted(
        distances,
        key=lambda item: (item[0], item[1].year, item[1].county_fips),
    )[:ANALOG_NEIGHBOR_COUNT]
    if not nearest:
        return _county_trailing_mean(row, train_rows), []
    if all(distance <= 1e-12 for distance, _train_row in nearest):
        weights = [1.0 / len(nearest) for _distance, _train_row in nearest]
    else:
        raw_weights = [1.0 / (distance + 1e-9) for distance, _train_row in nearest]
        total_weight = sum(raw_weights)
        weights = [weight / total_weight for weight in raw_weights]
    analogs = [
        (train_row, distance, weight)
        for (distance, train_row), weight in zip(nearest, weights, strict=True)
    ]
    prediction = sum(
        analog.incidence_per_100k * weight
        for analog, _distance, weight in analogs
    )
    return prediction, analogs


def _analog_interval_row(
    *,
    run_id: str,
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    source_sha: str,
    train_start_year: int,
    train_end_year: int,
) -> ModelComparisonInterval:
    prediction, analogs = _analog_forecast(row, train_rows, feature_columns)
    if not analogs:
        lower_95 = lower_80 = median = upper_80 = upper_95 = _round(prediction)
        analog_years = ""
        analog_counties = ""
        analog_weights = ""
    else:
        bootstrap_values = _analog_bootstrap_values(row, analogs)
        lower_95 = _round(_percentile(bootstrap_values, 2.5))
        lower_80 = _round(_percentile(bootstrap_values, 10.0))
        median = _round(_percentile(bootstrap_values, 50.0))
        upper_80 = _round(_percentile(bootstrap_values, 90.0))
        upper_95 = _round(_percentile(bootstrap_values, 97.5))
        analog_years = ";".join(str(analog.year) for analog, _distance, _weight in analogs)
        analog_counties = ";".join(
            analog.county_fips for analog, _distance, _weight in analogs
        )
        analog_weights = ";".join(
            str(_round(weight)) for _analog, _distance, weight in analogs
        )
    observed = _round(row.incidence_per_100k)
    return ModelComparisonInterval(
        run_id=run_id,
        model_name="analog_year_forecast",
        model_family="analog",
        target_definition=TARGET_DEFINITION,
        feature_set="safe_numeric_design_matrix",
        feature_profile=ANALOG_FEATURE_PROFILE,
        evaluation_mode=EVALUATION_MODE,
        weather_mode=FORECAST_SAFE_WEATHER_MODE,
        source_file_sha256=source_sha,
        county_fips=row.county_fips,
        county_name=row.county_name,
        test_year=row.year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        interval_method=ANALOG_INTERVAL_METHOD,
        bootstrap_seed=ANALOG_BOOTSTRAP_SEED,
        bootstrap_iterations=ANALOG_BOOTSTRAP_ITERATIONS,
        analog_count=len(analogs),
        analog_years=analog_years,
        analog_counties=analog_counties,
        analog_weights=analog_weights,
        lower_80_incidence_per_100k=lower_80,
        median_incidence_per_100k=median,
        upper_80_incidence_per_100k=upper_80,
        lower_95_incidence_per_100k=lower_95,
        upper_95_incidence_per_100k=upper_95,
        observed_incidence_per_100k=observed,
        covered_80=lower_80 <= observed <= upper_80,
        covered_95=lower_95 <= observed <= upper_95,
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )


def _analog_bootstrap_values(
    row: _DesignRow,
    analogs: list[tuple[_DesignRow, float, float]],
) -> list[float]:
    rng = random.Random(
        ANALOG_BOOTSTRAP_SEED + row.year * 100000 + int(row.county_fips)
    )
    rows = [analog for analog, _distance, _weight in analogs]
    weights = [weight for _analog, _distance, weight in analogs]
    values = []
    for _iteration in range(ANALOG_BOOTSTRAP_ITERATIONS):
        sampled = rng.choices(rows, weights=weights, k=len(rows))
        values.append(mean(analog.incidence_per_100k for analog in sampled))
    return values


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    return lower_value + (upper_value - lower_value) * (position - lower_index)


def _county_trailing_mean(row: _DesignRow, train_rows: list[_DesignRow]) -> float:
    county_rows = [
        prior.incidence_per_100k
        for prior in train_rows
        if prior.county_fips == row.county_fips
    ]
    if not county_rows:
        return _state_mean(train_rows)
    return mean(county_rows)


def _empirical_bayes_prediction(
    row: _DesignRow,
    train_rows: list[_DesignRow],
    shrinkage_strength: float,
) -> float:
    county_values = [
        prior.incidence_per_100k
        for prior in train_rows
        if prior.county_fips == row.county_fips
    ]
    state_mean = _state_mean(train_rows)
    if not county_values:
        return state_mean
    county_mean = mean(county_values)
    n = len(county_values)
    if shrinkage_strength == 0:
        return county_mean
    return (n * county_mean + shrinkage_strength * state_mean) / (
        n + shrinkage_strength
    )


def _ridge_prediction(
    *,
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    ridge_alpha: float,
    ridge_cache: dict[tuple[float, tuple[str, ...]], _FittedRidgeModel] | None = None,
) -> float:
    if not train_rows or not feature_columns:
        return _county_trailing_mean(row, train_rows)
    cache_key = (ridge_alpha, tuple(feature_columns))
    model = ridge_cache.get(cache_key) if ridge_cache is not None else None
    if model is None:
        model = _fit_ridge_model(
            train_rows=train_rows,
            feature_columns=feature_columns,
            ridge_alpha=ridge_alpha,
        )
        if ridge_cache is not None:
            ridge_cache[cache_key] = model
    if not model.columns:
        return model.train_state_mean
    x = [
        1.0,
        *[
            _standardized(row.features.get(column, 0.0), model.means[column], model.scales[column])
            for column in model.columns
        ],
    ]
    return max(_dot(model.coefficients, x), 0.0)


def _random_forest_prediction(
    *,
    row: _DesignRow,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    n_estimators: int = RANDOM_FOREST_N_ESTIMATORS,
    min_samples_leaf: int = RANDOM_FOREST_MIN_SAMPLES_LEAF,
    max_features: str = RANDOM_FOREST_MAX_FEATURES,
    random_state: int = RANDOM_FOREST_RANDOM_STATE,
    random_forest_cache: dict[tuple[int, int, str, int, tuple[str, ...]], object] | None = None,
) -> float:
    columns = _select_varying_columns(train_rows, feature_columns)
    if not train_rows or not columns:
        return _county_trailing_mean(row, train_rows)
    cache_key = (
        n_estimators,
        min_samples_leaf,
        max_features,
        random_state,
        tuple(columns),
    )
    model = random_forest_cache.get(cache_key) if random_forest_cache is not None else None
    if model is None:
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(
            n_estimators=n_estimators,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            random_state=random_state,
            n_jobs=1,
        )
        model.fit(
            [
                [train_row.features.get(column, 0.0) for column in columns]
                for train_row in train_rows
            ],
            [train_row.incidence_per_100k for train_row in train_rows],
        )
        if random_forest_cache is not None:
            random_forest_cache[cache_key] = model
    prediction = model.predict(
        [[row.features.get(column, 0.0) for column in columns]]
    )[0]
    return max(float(prediction), 0.0)


def _fit_ridge_model(
    *,
    train_rows: list[_DesignRow],
    feature_columns: list[str],
    ridge_alpha: float,
) -> _FittedRidgeModel:
    columns = _select_varying_columns(train_rows, feature_columns)
    train_state_mean = _state_mean(train_rows)
    if not columns:
        return _FittedRidgeModel(
            columns=[],
            means={},
            scales={},
            coefficients=[],
            train_state_mean=train_state_mean,
        )
    means = {
        column: mean(train_row.features.get(column, 0.0) for train_row in train_rows)
        for column in columns
    }
    scales = {
        column: _stddev(
            [train_row.features.get(column, 0.0) for train_row in train_rows]
        )
        for column in columns
    }
    x_train = [
        [1.0, *[_standardized(train_row.features.get(column, 0.0), means[column], scales[column]) for column in columns]]
        for train_row in train_rows
    ]
    y_train = [train_row.incidence_per_100k for train_row in train_rows]
    coefficients = _solve_ridge(x_train, y_train, ridge_alpha=ridge_alpha)
    return _FittedRidgeModel(
        columns=columns,
        means=means,
        scales=scales,
        coefficients=coefficients,
        train_state_mean=train_state_mean,
    )


def _select_varying_columns(
    train_rows: list[_DesignRow],
    feature_columns: list[str],
) -> list[str]:
    columns = []
    for column in feature_columns:
        values = {row.features.get(column, 0.0) for row in train_rows}
        if len(values) > 1:
            columns.append(column)
    return columns


def _solve_ridge(
    x_rows: list[list[float]],
    y_values: list[float],
    *,
    ridge_alpha: float,
) -> list[float]:
    n_features = len(x_rows[0])
    xtx = [[0.0 for _ in range(n_features)] for _ in range(n_features)]
    xty = [0.0 for _ in range(n_features)]
    for x, y in zip(x_rows, y_values, strict=True):
        for i in range(n_features):
            xty[i] += x[i] * y
            for j in range(n_features):
                xtx[i][j] += x[i] * x[j]
    for i in range(1, n_features):
        xtx[i][i] += ridge_alpha
    return _gaussian_solve(xtx, xty)


def _gaussian_solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            augmented[col][col] += 1e-8
            pivot = col
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        if abs(divisor) < 1e-12:
            continue
        for idx in range(col, n + 1):
            augmented[col][idx] /= divisor
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            for idx in range(col, n + 1):
                augmented[row][idx] -= factor * augmented[col][idx]
    return [augmented[row][n] for row in range(n)]


def _prediction_row(
    *,
    run_id: str,
    model_name: str,
    model_family: str,
    feature_profile: str,
    row: _DesignRow,
    predicted_incidence: float,
    source_sha: str,
    train_start_year: int,
    train_end_year: int,
    train_row_count: int,
    train_county_count: int,
) -> ModelComparisonPrediction:
    predicted_incidence = max(predicted_incidence, 0.0)
    predicted_cases = predicted_incidence / 100000 * row.population
    residual_incidence = row.incidence_per_100k - predicted_incidence
    residual_cases = row.actual_cases - predicted_cases
    return ModelComparisonPrediction(
        run_id=run_id,
        model_name=model_name,
        model_family=model_family,
        target_definition=TARGET_DEFINITION,
        feature_set="safe_numeric_design_matrix",
        feature_profile=feature_profile,
        evaluation_mode=EVALUATION_MODE,
        weather_mode=(
            FORECAST_SAFE_WEATHER_MODE
            if feature_profile.startswith("forecast_safe")
            else (
                LAGGED_WEATHER_MODE
                if feature_profile.startswith("lagged_outcome")
                else WEATHER_MODE
            )
        ),
        source_file_sha256=source_sha,
        county_fips=row.county_fips,
        county_name=row.county_name,
        test_year=row.year,
        train_start_year=train_start_year,
        train_end_year=train_end_year,
        train_row_count=train_row_count,
        train_county_count=train_county_count,
        actual_cases=row.actual_cases,
        actual_population=row.population,
        actual_incidence_per_100k=_round(row.incidence_per_100k),
        predicted_cases=_round(predicted_cases),
        predicted_incidence_per_100k=_round(predicted_incidence),
        residual_incidence_per_100k=_round(residual_incidence),
        absolute_error_incidence_per_100k=_round(abs(residual_incidence)),
        residual_cases=_round(residual_cases),
        absolute_error_cases=_round(abs(residual_cases)),
        model_feature_quality_flags=row.model_feature_quality_flags,
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )


def _metric_rows(
    run_id: str,
    predictions: list[ModelComparisonPrediction],
) -> list[ModelComparisonMetric]:
    rows = []
    for model_name in sorted({row.model_name for row in predictions}):
        model_rows = [row for row in predictions if row.model_name == model_name]
        for test_year in sorted({row.test_year for row in model_rows}):
            rows.append(_metric_row(run_id, model_rows, model_name, test_year))
        rows.append(_metric_row(run_id, model_rows, model_name, None))
    return rows


def _metric_row(
    run_id: str,
    model_rows: list[ModelComparisonPrediction],
    model_name: str,
    test_year: int | None,
) -> ModelComparisonMetric:
    rows = [
        row for row in model_rows if test_year is None or row.test_year == test_year
    ]
    first = rows[0]
    n = len(rows)
    residuals = [row.residual_incidence_per_100k for row in rows]
    case_residuals = [row.residual_cases for row in rows]
    return ModelComparisonMetric(
        run_id=run_id,
        model_name=model_name,
        model_family=first.model_family,
        target_definition=TARGET_DEFINITION,
        feature_set=first.feature_set,
        feature_profile=first.feature_profile,
        evaluation_mode=EVALUATION_MODE,
        weather_mode=first.weather_mode,
        source_file_sha256=first.source_file_sha256,
        aggregation="overall" if test_year is None else "test_year",
        test_year=test_year,
        n_predictions=n,
        mae_incidence_per_100k=_round(mean(abs(value) for value in residuals)),
        rmse_incidence_per_100k=_round(math.sqrt(mean(value * value for value in residuals))),
        mean_bias_incidence_per_100k=_round(mean(residuals)),
        mae_cases=_round(mean(abs(value) for value in case_residuals)),
        rmse_cases=_round(math.sqrt(mean(value * value for value in case_residuals))),
        pearson_correlation=_correlation(
            [row.actual_incidence_per_100k for row in rows],
            [row.predicted_incidence_per_100k for row in rows],
        ),
        comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
    )


def _summary_rows(
    run_id: str,
    metrics: list[ModelComparisonMetric],
) -> list[ModelComparisonSummary]:
    overall = [row for row in metrics if row.aggregation == "overall"]
    ranked = sorted(
        overall,
        key=lambda row: (
            row.mae_incidence_per_100k,
            row.rmse_incidence_per_100k,
            row.model_name,
        ),
    )
    return [
        ModelComparisonSummary(
            run_id=run_id,
            rank_by_mae=index,
            model_name=row.model_name,
            model_family=row.model_family,
            feature_profile=row.feature_profile,
            n_predictions=row.n_predictions,
            mae_incidence_per_100k=row.mae_incidence_per_100k,
            rmse_incidence_per_100k=row.rmse_incidence_per_100k,
            pearson_correlation=row.pearson_correlation,
            comparison_assumption_flags=COMPARISON_ASSUMPTION_FLAGS,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def _state_mean(rows: list[_DesignRow]) -> float:
    if not rows:
        return 0.0
    return mean(row.incidence_per_100k for row in rows)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    value_mean = mean(values)
    variance = mean((value - value_mean) ** 2 for value in values)
    stddev = math.sqrt(variance)
    return stddev if stddev > 1e-12 else 1.0


def _standardized(value: float, value_mean: float, value_stddev: float) -> float:
    return (value - value_mean) / value_stddev


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _correlation(actual: list[float], predicted: list[float]) -> float | None:
    if len(actual) < 2 or len(set(actual)) < 2 or len(set(predicted)) < 2:
        return None
    actual_mean = mean(actual)
    predicted_mean = mean(predicted)
    numerator = sum(
        (a - actual_mean) * (p - predicted_mean)
        for a, p in zip(actual, predicted, strict=True)
    )
    actual_denominator = math.sqrt(sum((a - actual_mean) ** 2 for a in actual))
    predicted_denominator = math.sqrt(
        sum((p - predicted_mean) ** 2 for p in predicted)
    )
    if actual_denominator == 0 or predicted_denominator == 0:
        return None
    return _round(numerator / (actual_denominator * predicted_denominator))


def _parse_int(value: str) -> int:
    return int(float(str(value or "0").strip() or "0"))


def _parse_float(value: str) -> float:
    return float(str(value or "0").strip() or "0")


def _round(value: float) -> float:
    return round(float(value), 6)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p").replace("-", "neg")
