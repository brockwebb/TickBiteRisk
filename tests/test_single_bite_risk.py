from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.runtime.risk_lookup import RiskLookupStore
from tickbiterisk.runtime.single_bite import (
    SingleBiteRiskInputError,
    estimate_single_bite_risk,
)


def test_single_bite_risk_combines_county_week_prior_with_bite_evidence(
    tmp_path,
) -> None:
    store = RiskLookupStore.from_csv(_write_scores(tmp_path / "scores.csv"))
    baseline = store.lookup(county_fips="24003", query_date="2023-01-01")

    response = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="ixodes_scapularis",
        tick_stage="nymph",
        attachment_hours=40,
        engorgement="engorged",
        hours_since_removal=24,
        doxycycline_safe=True,
        tick_count=1,
    )

    assert response.county_fips == "24003"
    assert response.query_date == "2023-01-01"
    assert response.single_bite_risk_score >= baseline.risk_score
    assert response.single_bite_risk_band in {"elevated", "high"}
    assert response.pep_consideration == "meets_cdc_consideration_criteria"
    assert response.forecast_context["county_week_risk_score"] == 7
    assert response.input_summary["tick_species"] == "ixodes_scapularis"
    assert response.evidence_modifiers["attachment"] >= 1.0
    assert _criterion(response, "attachment_duration")["status"] == "meets"
    assert _criterion(response, "tick_identity")["status"] == "meets"
    assert "not an absolute infection probability" in response.risk_interpretation


def test_single_bite_risk_keeps_brief_flat_non_ixodes_bites_low(tmp_path) -> None:
    store = RiskLookupStore.from_csv(_write_scores(tmp_path / "scores.csv"))
    baseline = store.lookup(county_fips="24003", query_date="2023-01-01")

    response = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="not_ixodes",
        tick_stage="adult",
        attachment_hours=2,
        engorgement="flat",
        hours_since_removal=4,
        doxycycline_safe=True,
    )

    assert response.single_bite_risk_score == 1
    assert response.single_bite_risk_band == "very_low"
    assert response.pep_consideration == "does_not_meet_cdc_consideration_criteria"
    assert _criterion(response, "tick_identity")["status"] == "not_met"
    assert _criterion(response, "attachment_duration")["status"] == "not_met"
    assert "non_ixodes_lyme_vector_unlikely" in response.caveats


def test_single_bite_risk_increases_with_attachment_and_tick_count(tmp_path) -> None:
    store = RiskLookupStore.from_csv(_write_scores(tmp_path / "scores.csv"))
    baseline = store.lookup(county_fips="24003", query_date="2023-01-01")

    short = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="blacklegged",
        tick_stage="nymph",
        attachment_hours=12,
        engorgement="flat",
    )
    long_single = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="blacklegged",
        tick_stage="nymph",
        attachment_hours=48,
        engorgement="engorged",
    )
    long_multiple = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="blacklegged",
        tick_stage="nymph",
        attachment_hours=48,
        engorgement="engorged",
        tick_count=2,
    )

    assert short.single_bite_risk_score < long_single.single_bite_risk_score
    assert long_multiple.single_bite_risk_score >= long_single.single_bite_risk_score


def test_high_risk_bite_is_not_suppressed_by_low_seasonal_baseline(tmp_path) -> None:
    path = _write_csv(
        tmp_path / "scores.csv",
        [_score_row("24003", "Anne Arundel County", "2023", "21", "1")],
    )
    store = RiskLookupStore.from_csv(path)
    baseline = store.lookup(county_fips="24003", query_date="2023-05-26")

    response = estimate_single_bite_risk(
        baseline=baseline,
        tick_species="ixodes_scapularis",
        tick_stage="nymph",
        attachment_hours=40,
        engorgement="engorged",
        hours_since_removal=24,
        doxycycline_safe=True,
    )

    assert response.forecast_context["county_week_risk_score"] == 1
    assert response.single_bite_risk_score >= 5
    assert response.pep_consideration == "meets_cdc_consideration_criteria"
    assert response.evidence_modifiers["location_season"] > 0.1
    assert "maryland_high_incidence_geography_floor" in response.caveats


def test_single_bite_risk_uses_forecast_language_for_latest_year_caveat(
    tmp_path,
) -> None:
    store = RiskLookupStore.from_csv(_write_scores(tmp_path / "scores.csv"))
    forecast = store.lookup(county_fips="24003", query_date="2026-01-04")

    response = estimate_single_bite_risk(
        baseline=forecast,
        tick_species="ixodes_scapularis",
    )

    assert "using_latest_available_forecast_year" in response.caveats
    assert "using_latest_available_baseline_year" not in response.caveats


def test_single_bite_risk_validates_inputs(tmp_path) -> None:
    store = RiskLookupStore.from_csv(_write_scores(tmp_path / "scores.csv"))
    baseline = store.lookup(county_fips="24003", query_date="2023-01-01")

    try:
        estimate_single_bite_risk(
            baseline=baseline,
            tick_species="ixodes_scapularis",
            attachment_hours=-1,
        )
    except SingleBiteRiskInputError as exc:
        assert "attachment_hours must be between 0 and 240" in str(exc)
    else:
        raise AssertionError("Expected negative attachment hours to fail")

    try:
        estimate_single_bite_risk(
            baseline=baseline,
            tick_species="ixodes_scapularis",
            tick_count=0,
        )
    except SingleBiteRiskInputError as exc:
        assert "tick_count must be between 1 and 20" in str(exc)
    else:
        raise AssertionError("Expected zero tick count to fail")


def _criterion(response, criterion_name: str) -> dict[str, str]:
    return next(
        criterion
        for criterion in response.pep_criteria
        if criterion["criterion"] == criterion_name
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
        "county_fips": county_fips,
        "county_name": county_name,
        "year": year,
        "mmwr_week": mmwr_week,
        "period_label": f"MMWR Week {mmwr_week}",
        "predicted_annual_incidence_per_100k": "20",
        "predicted_annual_cases": "100",
        "seasonal_mean_share": "0.1",
        "seasonal_lower_80_share": "0.08",
        "seasonal_upper_80_share": "0.12",
        "seasonal_lower_95_share": "0.06",
        "seasonal_upper_95_share": "0.14",
        "predicted_weekly_incidence_per_100k": "0.5",
        "lower_80_weekly_incidence_per_100k": "0.4",
        "upper_80_weekly_incidence_per_100k": "0.6",
        "lower_95_weekly_incidence_per_100k": "0.3",
        "upper_95_weekly_incidence_per_100k": "0.7",
        "predicted_weekly_cases": "2.0",
        "benchmark_quantile": "0.95",
        "headroom_multiplier": "1.2",
        "score_denominator": "10",
        "risk_score_raw": risk_score,
        "risk_score": risk_score,
        "risk_category": "very_low",
        "seasonality_source_id": "cdc_seasonality_week_2023",
        "feature_quality_flags": "relative_seasonal_baseline,not_weather_adjusted",
        "backtest_assumption_flags": "observational_not_causal",
    }


def _write_csv(path, rows: list[dict[str, str]]):
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path
