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
    assert "Backtest predictions file not found" in result.output
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
