"""Semantic checks for the committed static dashboard data bundle."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


PUBLIC_DATA_DIR = Path(__file__).resolve().parents[1] / "public" / "data"

EXPECTED_PUBLIC_DATA_FILES = {
    "md_counties.geojson",
    "md_county_metadata.json",
    "md_county_risk_weekly.json",
    "model_card.json",
    "source_catalog.json",
    "static_export_manifest.json",
}

EXPECTED_COUNTY_COUNT = 24
EXPECTED_MMWR_WEEKS = set(range(1, 54))
RISK_CATEGORIES = {"very_low", "low", "moderate", "high", "very_high"}
EXPECTED_RISK_CATEGORIES_BY_SCORE = {
    1: "very_low",
    2: "very_low",
    3: "low",
    4: "low",
    5: "moderate",
    6: "moderate",
    7: "high",
    8: "high",
    9: "very_high",
    10: "very_high",
}


def load_public_json(filename: str) -> dict:
    return json.loads((PUBLIC_DATA_DIR / filename).read_text())


def county_fips_from_geojson(geojson: dict) -> set[str]:
    return {
        feature["properties"]["county_fips"]
        for feature in geojson["features"]
    }


def test_manifest_covers_expected_committed_public_data_files() -> None:
    manifest = load_public_json("static_export_manifest.json")
    manifest_files = set(manifest["files"])
    committed_files = {
        path.name for path in PUBLIC_DATA_DIR.iterdir() if path.is_file()
    }

    assert committed_files == EXPECTED_PUBLIC_DATA_FILES
    assert manifest_files == EXPECTED_PUBLIC_DATA_FILES

    for filename in manifest_files:
        assert (PUBLIC_DATA_DIR / filename).is_file()


def test_manifest_record_counts_match_payloads() -> None:
    manifest = load_public_json("static_export_manifest.json")
    weekly = load_public_json("md_county_risk_weekly.json")
    metadata = load_public_json("md_county_metadata.json")
    geojson = load_public_json("md_counties.geojson")

    record_counts = manifest["record_counts"]

    assert record_counts["weekly_risk"] == weekly["record_count"]
    assert record_counts["weekly_risk"] == len(weekly["records"])

    assert record_counts["county_metadata"] == metadata["county_count"]
    assert record_counts["county_metadata"] == len(metadata["counties"])

    assert record_counts["county_geojson_features"] == geojson["metadata"]["feature_count"]
    assert record_counts["county_geojson_features"] == len(geojson["features"])


def test_county_fips_sets_match_across_dashboard_payloads() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    metadata = load_public_json("md_county_metadata.json")
    geojson = load_public_json("md_counties.geojson")

    weekly_fips = {record["county_fips"] for record in weekly["records"]}
    metadata_fips = {county["county_fips"] for county in metadata["counties"]}
    geojson_fips = county_fips_from_geojson(geojson)

    assert len(weekly_fips) == EXPECTED_COUNTY_COUNT
    assert weekly_fips == metadata_fips == geojson_fips


def test_weekly_records_cover_all_mmwr_weeks_for_each_county() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")

    weeks_by_county: dict[str, set[int]] = {}
    keys = set()
    for record in weekly["records"]:
        county_fips = record["county_fips"]
        mmwr_week = record["mmwr_week"]
        key = (county_fips, mmwr_week)
        assert key not in keys
        keys.add(key)
        weeks_by_county.setdefault(county_fips, set()).add(mmwr_week)

    assert len(weeks_by_county) == EXPECTED_COUNTY_COUNT
    assert all(weeks == EXPECTED_MMWR_WEEKS for weeks in weeks_by_county.values())
    assert len(keys) == EXPECTED_COUNTY_COUNT * len(EXPECTED_MMWR_WEEKS)


def test_public_weekly_records_are_2026_true_forecast_rows() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")

    assert {record["year"] for record in weekly["records"]} == {2026}
    assert weekly["temporal_contract"] == {
        "observed_truth_spatial_grain": "county",
        "observed_truth_temporal_grain": "year",
        "forecast_truth_spatial_grain": "county",
        "forecast_truth_temporal_grain": "year",
        "display_temporal_grain": "mmwr_week",
        "display_time_role": "seasonal_allocation_of_annual_forecast",
        "seasonality_scope": "national",
        "county_month_or_week_observed_truth_available": False,
        "historical_display_policy": (
            "Historical years are observed annual county incidence only; "
            "derived weekly or monthly allocations must not be labeled as "
            "observed historical risk."
        ),
    }
    assert weekly["selected_score_config"]["source_prediction_run_id"].startswith(
        "annual_forecast_target2026_origin2024"
    )
    assert weekly["selected_forecast_metadata"] == {
        "forecast_origin_year": 2024,
        "as_of_date": "2026-05-29",
        "data_cutoff_date": "2024-12-31",
        "source_vintage": "2024-inclusive-local",
        "update_mode": "pre_update",
    }


def test_weekly_risk_scores_and_categories_are_in_dashboard_ranges() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")

    for record in weekly["records"]:
        assert isinstance(record["risk_score"], int)
        assert 1 <= record["risk_score"] <= 10
        assert record["risk_category"] in RISK_CATEGORIES
        assert record["risk_category"] == EXPECTED_RISK_CATEGORIES_BY_SCORE[
            record["risk_score"]
        ]


def test_model_card_matches_weekly_export_metadata() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    model_card = load_public_json("model_card.json")

    for key in [
        "schema_version",
        "generated_at",
        "model_name",
        "caveats",
        "temporal_contract",
    ]:
        assert model_card[key] == weekly[key]

    assert model_card["target_definition"] == "lyme_incidence_per_100k"
    assert model_card["product_framing"] == (
        "Lyme risk forecasting tool for Maryland county annual disease "
        "pressure with seasonal allocation"
    )
    assert model_card["score_interpretation"].startswith(
        "Relative seasonal Lyme forecast"
    )
    assert model_card["forecasting_status"] == {
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
    }
    assert {item["topic"] for item in model_card["explainer_placeholders"]} == {
        "why_forecasting",
        "data_lag_and_reconciliation",
        "forecast_update_research",
        "regional_hotspot_patterns",
    }
    placeholder_text = json.dumps(model_card["explainer_placeholders"]).lower()
    assert "bayesian" not in placeholder_text
    assert "hierarchical" not in placeholder_text
    assert model_card["quality_flags"] == [
        "relative_seasonal_baseline",
        "static_seasonality_prior",
        "not_weather_adjusted",
    ]
    assert model_card["annual_prediction_source"]["artifact_type"] == (
        "annual_prediction_branch"
    )
    assert model_card["annual_prediction_source"]["run_id"].startswith(
        "annual_forecast_target2026_origin2024"
    )
    assert model_card["annual_prediction_source"]["sha256"] == (
        weekly["selected_score_config"]["source_prediction_sha256"]
    )
    assert "Selected annual forecast" in model_card["method_summary"]
    assert "not observed county-week data" in model_card["method_summary"]
    validation = model_card["validation_summary"]
    assert validation["model_name"] == weekly["model_name"]
    assert validation["run_id"].startswith("model_compare_")
    assert validation["rank_by_mae"] == 2
    assert validation["n_predictions"] == 432
    assert validation["validation_role"] == "historical_model_comparison"
    assert validation["validation_match_type"] == "annual_forecast_model_name"
    assert validation["forecast_model_name"] == "linear_blend_baseline"
    assert validation["mae_incidence_per_100k"] == 18.47245
    assert validation["rmse_incidence_per_100k"] == 29.737192
    assert validation["pearson_correlation"] == 0.771554
    assert "observational_not_causal" in validation["comparison_assumption_flags"]


def test_public_weekly_export_surfaces_probable_only_state_source_caveats() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    all_flags = {
        flag
        for record in weekly["records"]
        for flag in record.get("feature_quality_flags", [])
    }

    assert "mdh_probable_only_2024" in all_flags
    assert "state_source_not_cdc_public_use" in all_flags
    assert "population_structure_proxy" not in all_flags
    assert "human_exposure_context_only" not in all_flags
    assert "not_tick_bite_counts" not in all_flags
    assert "missing_mast_acorn_prior_year" not in all_flags
    assert weekly["selected_score_config"]["source_prediction_run_id"].startswith(
        "annual_forecast_target2026_origin2024"
    )


def test_source_catalog_exposes_selected_annual_prediction_branch() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    source_catalog = load_public_json("source_catalog.json")

    assert source_catalog["temporal_contract"] == weekly["temporal_contract"]
    annual_prediction = next(
        source
        for source in source_catalog["sources"]
        if source["source_id"] == "annual_prediction_branch"
    )

    assert annual_prediction["artifact_type"] == "annual prediction branch"
    assert annual_prediction["model_name"] == weekly["model_name"]
    assert annual_prediction["run_id"] == (
        weekly["selected_score_config"]["source_prediction_run_id"]
    )
    assert annual_prediction["sha256"] == (
        weekly["selected_score_config"]["source_prediction_sha256"]
    )
    assert annual_prediction["notes"].startswith("Selected annual no-observed-target")
    assert "no-observed-target" in annual_prediction["notes"]
    assert "prior-year validation" not in annual_prediction["notes"]
    seasonality = next(
        source
        for source in source_catalog["sources"]
        if source["source_id"] == "cdc_seasonality_week_2023"
    )
    assert seasonality["artifact_type"] == "derived seasonality prior"
    public_notes = " ".join(source["notes"] for source in source_catalog["sources"])
    assert "seasonal allocation" in public_notes
    assert "not observed county-week data" in public_notes
    assert "model-comparison" not in public_notes


def test_public_manifest_repeats_temporal_contract_for_auditability() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    manifest = load_public_json("static_export_manifest.json")

    assert manifest["temporal_contract"] == weekly["temporal_contract"]


def test_source_catalog_explains_forecast_lag_and_reconciliation() -> None:
    source_catalog = load_public_json("source_catalog.json")

    policy = source_catalog["data_lag_and_update_policy"]

    assert policy["summary"].startswith("Official Lyme surveillance data lag")
    assert policy["why_forecasting"].startswith("Forecasting gives timely")
    assert policy["reconciliation_policy"].startswith(
        "New observed reports are reconciled"
    )
    assert "surveillance-regime diagnostics" in policy["reconciliation_policy"]
    assert "calibration backtests" in policy["reconciliation_policy"]
    assert "source quality flags" in policy["reconciliation_policy"]
    assert policy["medical_boundary"].startswith("Forecasts do not diagnose")


def test_public_guidance_links_use_http_urls() -> None:
    payloads = [
        load_public_json("md_county_risk_weekly.json"),
        load_public_json("source_catalog.json"),
    ]

    for payload in payloads:
        for link in payload["guidance_links"]:
            parsed = urlparse(link["url"])
            assert parsed.scheme in {"http", "https"}
            assert parsed.netloc


def test_model_caveats_keep_non_medical_safety_framing() -> None:
    model_card = load_public_json("model_card.json")
    weekly = load_public_json("md_county_risk_weekly.json")
    caveat_text = " ".join(model_card["caveats"] + weekly["caveats"]).lower()

    assert "not medical advice" in caveat_text
    assert "does not diagnose" in caveat_text or "not diagnosis" in caveat_text
    assert "not a per-bite infection probability" in caveat_text
    assert (
        "not a personal infection probability" in caveat_text
        or "does not determine whether a person is infected" in caveat_text
    )
    assert "not a weather-adjusted forecast" in caveat_text
