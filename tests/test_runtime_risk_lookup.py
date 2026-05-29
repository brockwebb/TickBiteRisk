import csv
from pathlib import Path

from tickbiterisk.runtime.risk_lookup import (
    RiskLookupInputError,
    RiskLookupStore,
    mmwr_year_week,
)


def test_mmwr_year_week_uses_cdc_sunday_based_boundaries() -> None:
    assert mmwr_year_week("2023-01-01") == (2023, 1)
    assert mmwr_year_week("2020-12-31") == (2020, 53)
    assert mmwr_year_week("2021-01-02") == (2020, 53)
    assert mmwr_year_week("2021-01-03") == (2021, 1)


def test_lookup_returns_county_date_response_with_disclaimer_and_guidance(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    store = RiskLookupStore.from_csv(scores_path)

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        model_name="linear_blend_baseline",
    )

    assert response.county_fips == "24003"
    assert response.county_name == "Anne Arundel County"
    assert response.query_date == "2023-01-01"
    assert response.mmwr_year == 2023
    assert response.mmwr_week == 1
    assert response.data_year == 2023
    assert response.model_family == "ensemble"
    assert response.target_definition == "lyme_incidence_per_100k"
    assert response.feature_set == "historical_outcome_baselines"
    assert response.evaluation_mode == "forecast_prior_year"
    assert response.weather_mode == "not_used_by_baseline"
    assert response.risk_score == 7
    assert response.risk_category == "high"
    assert response.predicted_weekly_incidence_per_100k == 2.5
    assert response.predicted_weekly_incidence_95_interval == [1.5, 3.5]
    assert response.score_scale["benchmark_quantile"] == 0.95
    assert response.score_interpretation.startswith("Relative seasonal Lyme forecast")
    assert "exact_forecast_year" in response.data_quality_flags
    assert "exact_baseline_year" not in response.data_quality_flags
    assert "not_weather_adjusted" in response.feature_quality_flags
    assert "not medical advice" in response.clinical_disclaimer.lower()
    assert any("CDC" in link["title"] for link in response.guidance_links)


def test_lookup_uses_latest_available_year_when_query_year_is_missing(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    store = RiskLookupStore.from_csv(scores_path)

    response = store.lookup(
        county_fips="24003",
        query_date="2026-01-04",
        model_name="linear_blend_baseline",
    )

    assert response.mmwr_year == 2026
    assert response.data_year == 2023
    assert "requested_year_unavailable" in response.data_quality_flags
    assert "using_latest_available_year" in response.data_quality_flags


def test_lookup_requires_unambiguous_score_scale_when_configs_overlap(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path / "scores.csv",
        [
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "8"),
                "benchmark_quantile": "0.8",
                "headroom_multiplier": "1.1",
                "score_denominator": "2.5",
            },
        ],
    )
    store = RiskLookupStore.from_csv(path)

    try:
        store.lookup(county_fips="24003", query_date="2023-01-01")
    except RiskLookupInputError as exc:
        assert "Multiple risk score scale configurations found" in str(exc)
    else:
        raise AssertionError("Expected ambiguous runtime lookup to fail")

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        benchmark_quantile=0.8,
        headroom_multiplier=1.1,
    )

    assert response.risk_score == 8
    assert response.score_scale["benchmark_quantile"] == 0.8
    assert response.score_scale["headroom_multiplier"] == 1.1


def test_lookup_requires_unambiguous_score_denominator_when_scale_overlaps(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path / "scores.csv",
        [
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "8"),
                "score_denominator": "4.5",
            },
        ],
    )
    store = RiskLookupStore.from_csv(path)

    try:
        store.lookup(county_fips="24003", query_date="2023-01-01")
    except RiskLookupInputError as exc:
        assert "Multiple risk score scale configurations found" in str(exc)
    else:
        raise AssertionError("Expected ambiguous denominator lookup to fail")

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        score_denominator=4.5,
    )

    assert response.risk_score == 8
    assert response.score_scale["score_denominator"] == 4.5


def test_lookup_requires_unambiguous_source_version_when_same_scale_overlaps(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path / "scores.csv",
        [
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "8"),
                "source_prediction_run_id": "run2",
                "source_prediction_sha256": "c" * 64,
            },
        ],
    )
    store = RiskLookupStore.from_csv(path)

    try:
        store.lookup(county_fips="24003", query_date="2023-01-01")
    except RiskLookupInputError as exc:
        assert "Multiple risk score source versions found" in str(exc)
    else:
        raise AssertionError("Expected ambiguous source version lookup to fail")

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        source_prediction_sha256="c" * 64,
    )

    assert response.risk_score == 8
    assert response.source_metadata["source_prediction_run_id"] == "run2"


def test_lookup_exposes_forecast_vintage_metadata(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    store = RiskLookupStore.from_csv(scores_path)

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        model_name="linear_blend_baseline",
    )

    assert response.source_metadata["forecast_origin_year"] == "2022"
    assert response.source_metadata["as_of_date"] == "2026-05-28"
    assert response.source_metadata["data_cutoff_date"] == "2024-12-31"
    assert response.source_metadata["source_vintage"] == "mdh_2024_reviewed_v1"
    assert response.source_metadata["update_mode"] == "pre_update"


def test_lookup_exposes_annual_interval_metadata_when_available(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path / "scores.csv",
        [
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "7"),
                "source_prediction_interval_sha256": "d" * 64,
                "annual_interval_method": "empirical_residual_interval",
                "annual_interval_available": "True",
            }
        ],
    )
    store = RiskLookupStore.from_csv(path)

    response = store.lookup(
        county_fips="24003",
        query_date="2023-01-01",
        model_name="linear_blend_baseline",
    )

    assert response.source_metadata["source_prediction_interval_sha256"] == "d" * 64
    assert response.source_metadata["annual_interval_method"] == (
        "empirical_residual_interval"
    )
    assert response.source_metadata["annual_interval_available"] == "true"


def test_lookup_rejects_unknown_county(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    store = RiskLookupStore.from_csv(scores_path)

    try:
        store.lookup(county_fips="99999", query_date="2023-01-01")
    except RiskLookupInputError as exc:
        assert "No risk forecast rows found for county_fips=99999" in str(exc)
    else:
        raise AssertionError("Expected unknown county lookup to fail")


def test_lookup_rejects_missing_required_score_columns(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "bad_scores.csv",
        [
            {
                "county_fips": "24003",
                "year": "2023",
                "mmwr_week": "1",
            }
        ],
    )

    try:
        RiskLookupStore.from_csv(path)
    except RiskLookupInputError as exc:
        assert "missing required risk lookup column(s):" in str(exc)
        assert "model_name" in str(exc)
        assert "risk_score" in str(exc)
    else:
        raise AssertionError("Expected malformed score file to fail")


def _write_scores(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _score_row("24003", "Anne Arundel County", "2022", "1", "6"),
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            _score_row("24005", "Baltimore County", "2023", "1", "4"),
        ],
    )


def _score_row(
    county_fips: str,
    county_name: str,
    year: str,
    mmwr_week: str,
    risk_score: str,
) -> dict[str, str]:
    return {
        "source_prediction_run_id": "run1",
        "source_prediction_sha256": "a" * 64,
        "source_seasonality_sha256": "b" * 64,
        "model_name": "linear_blend_baseline",
        "model_family": "ensemble",
        "target_definition": "lyme_incidence_per_100k",
        "feature_set": "historical_outcome_baselines",
        "evaluation_mode": "forecast_prior_year",
        "weather_mode": "not_used_by_baseline",
        "forecast_origin_year": "2022",
        "as_of_date": "2026-05-28",
        "data_cutoff_date": "2024-12-31",
        "source_vintage": "mdh_2024_reviewed_v1",
        "update_mode": "pre_update",
        "county_fips": county_fips,
        "county_name": county_name,
        "year": year,
        "mmwr_week": mmwr_week,
        "period_label": f"MMWR Week {mmwr_week}",
        "predicted_annual_incidence_per_100k": "50.0",
        "predicted_annual_cases": "40.0",
        "seasonal_mean_share": "0.05",
        "seasonal_lower_80_share": "0.03",
        "seasonal_upper_80_share": "0.06",
        "seasonal_lower_95_share": "0.03",
        "seasonal_upper_95_share": "0.07",
        "predicted_weekly_incidence_per_100k": "2.5",
        "lower_80_weekly_incidence_per_100k": "1.6",
        "upper_80_weekly_incidence_per_100k": "3.0",
        "lower_95_weekly_incidence_per_100k": "1.5",
        "upper_95_weekly_incidence_per_100k": "3.5",
        "predicted_weekly_cases": "2.0",
        "benchmark_quantile": "0.95",
        "headroom_multiplier": "1.2",
        "score_denominator": "3.5",
        "risk_score_raw": "7.1",
        "risk_score": risk_score,
        "risk_category": "high" if risk_score == "7" else "moderate",
        "seasonality_source_id": "cdc_seasonality_week_2023",
        "model_feature_quality_flags": "missing_deer_harvest_prior_season",
        "seasonality_feature_quality_flags": (
            "national_curve_not_county_specific,shares_normalized_by_annual_total"
        ),
        "feature_quality_flags": (
            "relative_seasonal_baseline,static_seasonality_prior,"
            "not_weather_adjusted"
        ),
        "backtest_assumption_flags": (
            "observational_not_causal,intervention_history_unmodeled"
        ),
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
