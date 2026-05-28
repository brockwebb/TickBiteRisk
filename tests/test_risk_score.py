import csv
from pathlib import Path

from tickbiterisk.modeling.risk_score import (
    RiskScoreInputError,
    build_seasonal_risk_scores,
)
from tickbiterisk.modeling.risk_score_build import (
    RISK_SCORE_SCALE_COLUMNS,
    SEASONAL_RISK_SCORE_COLUMNS,
    write_seasonal_risk_score_outputs,
)


def test_build_seasonal_risk_scores_apportions_annual_predictions_to_weeks(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
        benchmark_quantile=0.95,
        headroom_multiplier=1.2,
    )

    assert result.scale.model_name == "prior_year_incidence"
    assert result.scale.grain == "mmwr_week"
    assert result.scale.seasonality_source_id == "cdc_seasonality_week_2023"
    assert result.scale.benchmark_weekly_incidence_per_100k == 30.0
    assert result.scale.score_denominator == 36.0
    assert result.scale.n_score_rows == 4
    assert len(result.source_prediction_sha256) == 64
    assert len(result.source_seasonality_sha256) == 64

    high_row = next(
        row
        for row in result.rows
        if row.county_fips == "24001" and row.mmwr_week == 2
    )
    assert high_row.predicted_annual_incidence_per_100k == 100.0
    assert high_row.seasonal_mean_share == 0.3
    assert high_row.predicted_weekly_incidence_per_100k == 30.0
    assert high_row.lower_80_weekly_incidence_per_100k == 20.0
    assert high_row.upper_95_weekly_incidence_per_100k == 40.0
    assert high_row.risk_score_raw == 8.333333
    assert high_row.benchmark_quantile == 0.95
    assert high_row.headroom_multiplier == 1.2
    assert high_row.score_denominator == 36.0
    assert high_row.risk_score == 8
    assert high_row.risk_category == "high"
    assert high_row.source_prediction_run_id == "run1"
    assert "static_seasonality_prior" in high_row.feature_quality_flags
    assert "not_weather_adjusted" in high_row.feature_quality_flags
    assert "observational_not_causal" in high_row.backtest_assumption_flags

    low_row = next(
        row
        for row in result.rows
        if row.county_fips == "24003" and row.mmwr_week == 1
    )
    assert low_row.predicted_weekly_incidence_per_100k == 5.0
    assert low_row.risk_score == 1
    assert low_row.risk_category == "very_low"


def test_build_seasonal_risk_scores_filters_to_requested_model(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(
        tmp_path / "predictions.csv",
        extra_model=True,
    )
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
    )

    assert {row.model_name for row in result.rows} == {"prior_year_incidence"}
    assert len(result.rows) == 4


def test_build_seasonal_risk_scores_reads_model_comparison_predictions(
    tmp_path: Path,
) -> None:
    predictions_path = _write_model_comparison_predictions(
        tmp_path / "model_comparison_predictions.csv"
    )
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="ridge_forecast_safe",
    )

    assert result.scale.model_name == "ridge_forecast_safe"
    assert result.scale.scale_quality_flags == "relative_to_maryland_prediction_distribution"
    assert len(result.rows) == 4
    first = result.rows[0]
    assert first.source_prediction_run_id == "compare-run"
    assert first.model_family == "regularized_linear"
    assert first.feature_set == "safe_numeric_design_matrix"
    assert first.evaluation_mode == "rolling_origin_prior_years"
    assert first.weather_mode == "not_used_by_forecast_safe_model"
    assert first.predicted_annual_cases == 11.25
    assert "surveillance_reporting_sensitive" in first.backtest_assumption_flags


def test_build_seasonal_risk_scores_filters_unused_research_flags_for_lagged_branch(
    tmp_path: Path,
) -> None:
    predictions_path = _write_csv(
        tmp_path / "model_comparison_predictions.csv",
        [
            {
                **_model_comparison_prediction_row(
                    "24003",
                    "Anne Arundel County",
                    "30.0",
                    "7.5",
                ),
                "model_name": "linear_blend_baseline",
                "model_family": "ensemble",
                "feature_profile": "lagged_outcome_blend",
                "weather_mode": "not_used_by_lagged_model",
                "model_feature_quality_flags": (
                    "population_structure_proxy,human_exposure_context_only,"
                    "not_tick_bite_counts,census_vintage_revision_sensitive,"
                    "missing_mast_acorn_prior_year,mdh_probable_only_2024,"
                    "state_source_not_cdc_public_use,lyme_case_definition_change"
                ),
            }
        ],
    )
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="linear_blend_baseline",
    )

    flags = set(result.rows[0].feature_quality_flags.split(","))
    assert "mdh_probable_only_2024" in flags
    assert "state_source_not_cdc_public_use" in flags
    assert "lyme_case_definition_change" in flags
    assert "population_structure_proxy" not in flags
    assert "human_exposure_context_only" not in flags
    assert "not_tick_bite_counts" not in flags
    assert "census_vintage_revision_sensitive" not in flags
    assert "missing_mast_acorn_prior_year" not in flags


def test_build_seasonal_risk_scores_filters_to_requested_seasonality_source(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(
        tmp_path / "seasonality.csv",
        include_alternate_source=True,
    )

    default_result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
    )
    alternate_result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
        seasonality_source_id="alternate_weekly_curve",
    )

    assert len(default_result.rows) == 4
    assert {row.seasonality_source_id for row in default_result.rows} == {
        "cdc_seasonality_week_2023"
    }
    assert len(alternate_result.rows) == 4
    assert {row.seasonality_source_id for row in alternate_result.rows} == {
        "alternate_weekly_curve"
    }
    assert alternate_result.scale.seasonality_source_id == "alternate_weekly_curve"


def test_build_seasonal_risk_scores_fails_when_model_missing(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    try:
        build_seasonal_risk_scores(
            predictions_path=predictions_path,
            seasonality_baseline_path=seasonality_path,
            model_name="missing_model",
        )
    except RiskScoreInputError as exc:
        assert "No annual predictions found for model_name=missing_model" in str(exc)
    else:
        raise AssertionError("Expected missing model to fail")


def test_build_seasonal_risk_scores_rejects_missing_prediction_columns(
    tmp_path: Path,
) -> None:
    predictions_path = _write_csv(
        tmp_path / "predictions.csv",
        [
            {
                "run_id": "run1",
                "model_name": "prior_year_incidence",
                "county_fips": "24001",
                "county_name": "County 24001",
                "test_year": "2020",
                "predicted_incidence_per_100k": "20",
            }
        ],
    )
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")

    try:
        build_seasonal_risk_scores(
            predictions_path=predictions_path,
            seasonality_baseline_path=seasonality_path,
            model_name="prior_year_incidence",
        )
    except RiskScoreInputError as exc:
        assert "missing required risk score column(s): model_family" in str(exc)
    else:
        raise AssertionError("Expected missing prediction column to fail")


def test_build_seasonal_risk_scores_rejects_bad_numeric_values(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_csv(
        tmp_path / "seasonality.csv",
        [
            {
                "source_id": "cdc_seasonality_week_2023",
                "disease": "lyme",
                "grain": "mmwr_week",
                "period": "1",
                "period_label": "MMWR Week 1",
                "mean_share": "not-a-number",
                "lower_80_share": "0.05",
                "upper_80_share": "0.2",
                "lower_95_share": "0.04",
                "upper_95_share": "0.3",
                "feature_quality_flags": "national_curve_not_county_specific",
            }
        ],
    )

    try:
        build_seasonal_risk_scores(
            predictions_path=predictions_path,
            seasonality_baseline_path=seasonality_path,
            model_name="prior_year_incidence",
        )
    except RiskScoreInputError as exc:
        assert "mean_share must be numeric" in str(exc)
    else:
        raise AssertionError("Expected bad numeric seasonality value to fail")


def test_build_seasonal_risk_scores_fails_when_weekly_seasonality_missing(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_csv(
        tmp_path / "seasonality.csv",
        [
            {
                "source_id": "cdc_seasonality_month_2023",
                "disease": "lyme",
                "grain": "month",
                "period": "1",
                "period_label": "January",
                "mean_share": "0.1",
                "lower_80_share": "0.05",
                "upper_80_share": "0.2",
                "lower_95_share": "0.04",
                "upper_95_share": "0.3",
                "feature_quality_flags": "national_curve_not_county_specific",
            }
        ],
    )

    try:
        build_seasonal_risk_scores(
            predictions_path=predictions_path,
            seasonality_baseline_path=seasonality_path,
            model_name="prior_year_incidence",
        )
    except RiskScoreInputError as exc:
        assert (
            "No seasonality baseline rows found for "
            "source_id=cdc_seasonality_week_2023, grain=mmwr_week"
        ) in str(exc)
    else:
        raise AssertionError("Expected missing weekly seasonality to fail")


def test_write_seasonal_risk_score_outputs_orders_and_dedupes(
    tmp_path: Path,
) -> None:
    result = build_seasonal_risk_scores(
        predictions_path=_write_predictions(tmp_path / "predictions.csv"),
        seasonality_baseline_path=_write_seasonality(tmp_path / "seasonality.csv"),
        model_name="prior_year_incidence",
    )

    outputs = write_seasonal_risk_score_outputs(result, tmp_path / "out")
    second_outputs = write_seasonal_risk_score_outputs(
        result,
        tmp_path / "out",
        append=True,
    )

    assert second_outputs == outputs
    with outputs.scores_path.open(newline="", encoding="utf-8") as handle:
        score_rows = list(csv.DictReader(handle))
    with outputs.scale_path.open(newline="", encoding="utf-8") as handle:
        scale_rows = list(csv.DictReader(handle))

    assert list(score_rows[0]) == SEASONAL_RISK_SCORE_COLUMNS
    assert list(scale_rows[0]) == RISK_SCORE_SCALE_COLUMNS
    assert len(score_rows) == 4
    assert len(scale_rows) == 1
    assert score_rows[0]["county_fips"] == "24001"
    assert score_rows[0]["mmwr_week"] == "1"


def test_write_seasonal_risk_score_outputs_preserves_distinct_scale_configs(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(
        tmp_path / "seasonality.csv",
        include_alternate_source=True,
    )
    default_result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
    )
    alternate_result = build_seasonal_risk_scores(
        predictions_path=predictions_path,
        seasonality_baseline_path=seasonality_path,
        model_name="prior_year_incidence",
        seasonality_source_id="alternate_weekly_curve",
        benchmark_quantile=0.8,
        headroom_multiplier=1.1,
    )

    outputs = write_seasonal_risk_score_outputs(default_result, tmp_path / "out")
    write_seasonal_risk_score_outputs(alternate_result, tmp_path / "out", append=True)

    with outputs.scores_path.open(newline="", encoding="utf-8") as handle:
        score_rows = list(csv.DictReader(handle))
    with outputs.scale_path.open(newline="", encoding="utf-8") as handle:
        scale_rows = list(csv.DictReader(handle))

    assert len(score_rows) == 8
    assert len(scale_rows) == 2
    assert {row["seasonality_source_id"] for row in score_rows} == {
        "alternate_weekly_curve",
        "cdc_seasonality_week_2023",
    }
    assert {row["benchmark_quantile"] for row in scale_rows} == {"0.8", "0.95"}
    assert {row["headroom_multiplier"] for row in score_rows} == {"1.1", "1.2"}


def test_write_seasonal_risk_score_outputs_upgrades_stale_append_files(
    tmp_path: Path,
) -> None:
    result = build_seasonal_risk_scores(
        predictions_path=_write_predictions(tmp_path / "predictions.csv"),
        seasonality_baseline_path=_write_seasonality(tmp_path / "seasonality.csv"),
        model_name="prior_year_incidence",
    )
    output_dir = tmp_path / "out"
    _write_csv(
        output_dir / "county_week_seasonal_risk_baseline.csv",
        [
            {
                "county_fips": "24001",
                "model_name": "prior_year_incidence",
                "year": "2019",
                "mmwr_week": "1",
                "source_prediction_run_id": "old",
            }
        ],
    )
    _write_csv(
        output_dir / "risk_score_scale.csv",
        [
            {
                "model_name": "prior_year_incidence",
                "grain": "mmwr_week",
                "source_prediction_sha256": "old",
            }
        ],
    )

    outputs = write_seasonal_risk_score_outputs(result, output_dir, append=True)

    with outputs.scores_path.open(newline="", encoding="utf-8") as handle:
        score_rows = list(csv.DictReader(handle))
    with outputs.scale_path.open(newline="", encoding="utf-8") as handle:
        scale_rows = list(csv.DictReader(handle))

    assert len(score_rows) == 4
    assert len(scale_rows) == 1
    assert score_rows[0]["benchmark_quantile"] == "0.95"
    assert scale_rows[0]["seasonality_source_id"] == "cdc_seasonality_week_2023"


def _write_predictions(
    path: Path,
    *,
    extra_model: bool = False,
) -> Path:
    rows = [
        _prediction_row("24001", "County 24001", "100.0"),
        _prediction_row("24003", "County 24003", "50.0"),
    ]
    if extra_model:
        rows.append(
            {
                **_prediction_row("24001", "County 24001", "999.0"),
                "model_name": "county_trailing_mean_incidence",
            }
        )
    return _write_csv(path, rows)


def _write_model_comparison_predictions(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _model_comparison_prediction_row("24001", "County 24001", "45.0", "11.25"),
            _model_comparison_prediction_row("24003", "County 24003", "30.0", "7.5"),
        ],
    )


def _prediction_row(
    county_fips: str,
    county_name: str,
    predicted_incidence: str,
) -> dict[str, str]:
    return {
        "run_id": "run1",
        "model_name": "prior_year_incidence",
        "model_family": "baseline",
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "historical_outcome_baselines",
        "evaluation_mode": "forecast_prior_year",
        "weather_mode": "not_used_by_baseline",
        "source_file_sha256": "a" * 64,
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": "2020",
        "predicted_incidence_per_100k": predicted_incidence,
        "model_feature_quality_flags": "missing_deer_harvest_prior_season",
        "backtest_assumption_flags": (
            "observational_not_causal,intervention_history_unmodeled"
        ),
    }


def _model_comparison_prediction_row(
    county_fips: str,
    county_name: str,
    predicted_incidence: str,
    predicted_cases: str,
) -> dict[str, str]:
    return {
        "run_id": "compare-run",
        "model_name": "ridge_forecast_safe",
        "model_family": "regularized_linear",
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "safe_numeric_design_matrix",
        "feature_profile": "forecast_safe_lagged",
        "evaluation_mode": "rolling_origin_prior_years",
        "weather_mode": "not_used_by_forecast_safe_model",
        "source_file_sha256": "b" * 64,
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": "2020",
        "train_start_year": "1993",
        "train_end_year": "2019",
        "train_row_count": "100",
        "train_county_count": "24",
        "actual_cases": "10",
        "actual_population": "25000",
        "actual_incidence_per_100k": "40.0",
        "predicted_cases": predicted_cases,
        "predicted_incidence_per_100k": predicted_incidence,
        "residual_incidence_per_100k": "-5.0",
        "absolute_error_incidence_per_100k": "5.0",
        "residual_cases": "-1.25",
        "absolute_error_cases": "1.25",
        "model_feature_quality_flags": "current_status_retrospective_proxy",
        "comparison_assumption_flags": (
            "observational_not_causal,surveillance_reporting_sensitive"
        ),
    }


def _write_seasonality(
    path: Path,
    *,
    include_alternate_source: bool = False,
) -> Path:
    rows = [
        {
            "source_id": "cdc_seasonality_week_2023",
            "disease": "lyme",
            "grain": "mmwr_week",
            "period": "1",
            "period_label": "MMWR Week 1",
            "mean_share": "0.1",
            "lower_80_share": "0.05",
            "upper_80_share": "0.2",
            "lower_95_share": "0.04",
            "upper_95_share": "0.3",
            "feature_quality_flags": (
                "national_curve_not_county_specific,"
                "shares_normalized_by_annual_total"
            ),
        },
        {
            "source_id": "cdc_seasonality_week_2023",
            "disease": "lyme",
            "grain": "mmwr_week",
            "period": "2",
            "period_label": "MMWR Week 2",
            "mean_share": "0.3",
            "lower_80_share": "0.2",
            "upper_80_share": "0.35",
            "lower_95_share": "0.1",
            "upper_95_share": "0.4",
            "feature_quality_flags": (
                "national_curve_not_county_specific,"
                "shares_normalized_by_annual_total"
            ),
        },
    ]
    if include_alternate_source:
        rows.extend(
            [
                {
                    **rows[0],
                    "source_id": "alternate_weekly_curve",
                    "mean_share": "0.2",
                },
                {
                    **rows[1],
                    "source_id": "alternate_weekly_curve",
                    "mean_share": "0.4",
                },
            ]
        )
    return _write_csv(path, rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
