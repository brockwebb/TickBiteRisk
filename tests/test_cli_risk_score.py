import csv
from pathlib import Path

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_county_week_risk_command_writes_scores_and_scale(tmp_path: Path) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--backtest-predictions-path",
            str(predictions_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "prior_year_incidence",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 4 county-week risk score row(s)" in result.stdout
    assert "Wrote 1 risk score scale row(s)" in result.stdout
    assert (output_dir / "county_week_seasonal_risk_baseline.csv").exists()
    assert (output_dir / "risk_score_scale.csv").exists()
    with (output_dir / "county_week_seasonal_risk_baseline.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["county_fips"] == "24001"
    assert rows[0]["risk_category"] == "very_low"
    assert rows[-1]["risk_category"] == "high"


def test_county_week_risk_command_accepts_generic_predictions_path(
    tmp_path: Path,
) -> None:
    predictions_path = _write_model_comparison_predictions(
        tmp_path / "model_comparison_predictions.csv"
    )
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--predictions-path",
            str(predictions_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "ridge_forecast_safe",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 4 county-week risk score row(s)" in result.stdout
    with (output_dir / "county_week_seasonal_risk_baseline.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["model_name"] for row in rows} == {"ridge_forecast_safe"}
    assert rows[0]["weather_mode"] == "not_used_by_forecast_safe_model"
    assert "surveillance_reporting_sensitive" in rows[0]["backtest_assumption_flags"]


def test_county_week_risk_command_accepts_prediction_intervals(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    intervals_path = _write_prediction_intervals(tmp_path / "intervals.csv")
    seasonality_path = _write_seasonality(tmp_path / "seasonality.csv")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--predictions-path",
            str(predictions_path),
            "--prediction-intervals-path",
            str(intervals_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "prior_year_incidence",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "county_week_seasonal_risk_baseline.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["annual_interval_available"] == "True"
    assert rows[0]["annual_interval_method"] == "empirical_residual_interval"
    assert rows[0]["source_prediction_interval_sha256"]


def test_county_week_risk_command_selects_seasonality_source(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(
        tmp_path / "seasonality.csv",
        source_id="alternate_weekly_curve",
    )
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--backtest-predictions-path",
            str(predictions_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "prior_year_incidence",
            "--seasonality-source-id",
            "alternate_weekly_curve",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    with (output_dir / "county_week_seasonal_risk_baseline.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["seasonality_source_id"] for row in rows} == {
        "alternate_weekly_curve"
    }


def test_county_week_risk_command_appends_distinct_score_configs_by_default(
    tmp_path: Path,
) -> None:
    predictions_path = _write_predictions(tmp_path / "predictions.csv")
    seasonality_path = _write_seasonality(
        tmp_path / "seasonality.csv",
        include_alternate_source=True,
    )
    output_dir = tmp_path / "out"

    first_result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--backtest-predictions-path",
            str(predictions_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "prior_year_incidence",
            "--output-dir",
            str(output_dir),
        ],
    )
    second_result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--backtest-predictions-path",
            str(predictions_path),
            "--seasonality-baseline-path",
            str(seasonality_path),
            "--model-name",
            "prior_year_incidence",
            "--seasonality-source-id",
            "alternate_weekly_curve",
            "--benchmark-quantile",
            "0.8",
            "--headroom-multiplier",
            "1.1",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert first_result.exit_code == 0
    assert second_result.exit_code == 0
    with (output_dir / "county_week_seasonal_risk_baseline.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        score_rows = list(csv.DictReader(handle))
    with (output_dir / "risk_score_scale.csv").open(
        newline="",
        encoding="utf-8",
    ) as handle:
        scale_rows = list(csv.DictReader(handle))

    assert len(score_rows) == 8
    assert len(scale_rows) == 2
    assert {row["seasonality_source_id"] for row in score_rows} == {
        "alternate_weekly_curve",
        "cdc_seasonality_week_2023",
    }
    assert {row["benchmark_quantile"] for row in scale_rows} == {"0.8", "0.95"}


def test_county_week_risk_command_fails_cleanly_when_inputs_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "county-week-risk",
            "--backtest-predictions-path",
            str(tmp_path / "missing-predictions.csv"),
            "--seasonality-baseline-path",
            str(tmp_path / "missing-seasonality.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code != 0
    assert "Annual predictions file not found" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out" / "county_week_seasonal_risk_baseline.csv").exists()


def _write_predictions(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _prediction_row("24001", "County 24001", "20.0"),
            _prediction_row("24003", "County 24003", "100.0"),
        ],
    )


def _write_model_comparison_predictions(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _model_comparison_prediction_row("24001", "County 24001", "20.0"),
            _model_comparison_prediction_row("24003", "County 24003", "100.0"),
        ],
    )


def _write_prediction_intervals(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _prediction_interval_row("24001", "County 24001", "10.0", "30.0"),
            _prediction_interval_row("24003", "County 24003", "70.0", "120.0"),
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
        "county_fips": county_fips,
        "county_name": county_name,
        "test_year": "2020",
        "predicted_cases": predicted_incidence,
        "predicted_incidence_per_100k": predicted_incidence,
        "model_feature_quality_flags": "",
        "backtest_assumption_flags": "observational_not_causal",
    }


def _prediction_interval_row(
    county_fips: str,
    county_name: str,
    lower_80_incidence: str,
    upper_80_incidence: str,
) -> dict[str, str]:
    return {
        "source_forecast_run_id": "run1",
        "model_name": "prior_year_incidence",
        "county_fips": county_fips,
        "county_name": county_name,
        "forecast_year": "2020",
        "interval_method": "empirical_residual_interval",
        "lower_80_incidence_per_100k": lower_80_incidence,
        "median_incidence_per_100k": "20.0",
        "upper_80_incidence_per_100k": upper_80_incidence,
        "lower_95_incidence_per_100k": lower_80_incidence,
        "upper_95_incidence_per_100k": upper_80_incidence,
        "interval_assumption_flags": "empirical_rolling_origin_residual_interval",
    }


def _model_comparison_prediction_row(
    county_fips: str,
    county_name: str,
    predicted_incidence: str,
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
        "train_start_year": "2019",
        "train_end_year": "2019",
        "train_row_count": "24",
        "train_county_count": "24",
        "actual_cases": "5",
        "actual_population": "100000",
        "actual_incidence_per_100k": "5.0",
        "predicted_cases": predicted_incidence,
        "predicted_incidence_per_100k": predicted_incidence,
        "residual_incidence_per_100k": "0.0",
        "absolute_error_incidence_per_100k": "0.0",
        "residual_cases": "0.0",
        "absolute_error_cases": "0.0",
        "model_feature_quality_flags": "",
        "comparison_assumption_flags": (
            "observational_not_causal,surveillance_reporting_sensitive"
        ),
    }


def _write_seasonality(
    path: Path,
    *,
    source_id: str = "cdc_seasonality_week_2023",
    include_alternate_source: bool = False,
) -> Path:
    rows = [
        {
            "source_id": source_id,
            "disease": "lyme",
            "grain": "mmwr_week",
            "period": "1",
            "period_label": "MMWR Week 1",
            "mean_share": "0.1",
            "lower_80_share": "0.05",
            "upper_80_share": "0.2",
            "lower_95_share": "0.04",
            "upper_95_share": "0.3",
            "feature_quality_flags": "national_curve_not_county_specific",
        },
        {
            "source_id": source_id,
            "disease": "lyme",
            "grain": "mmwr_week",
            "period": "2",
            "period_label": "MMWR Week 2",
            "mean_share": "0.3",
            "lower_80_share": "0.2",
            "upper_80_share": "0.35",
            "lower_95_share": "0.1",
            "upper_95_share": "0.4",
            "feature_quality_flags": "national_curve_not_county_specific",
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
