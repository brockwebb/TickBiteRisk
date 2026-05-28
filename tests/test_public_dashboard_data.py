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

    for key in ["schema_version", "generated_at", "model_name", "caveats"]:
        assert model_card[key] == weekly[key]

    assert model_card["target_definition"] == "lyme_incidence_per_100k"
    assert model_card["product_framing"] == "relative county-week seasonal Lyme baseline"
    assert model_card["quality_flags"] == [
        "relative_seasonal_baseline",
        "static_seasonality_prior",
        "not_weather_adjusted",
    ]
    assert model_card["annual_prediction_source"]["artifact_type"] == (
        "annual_prediction_branch"
    )
    assert model_card["annual_prediction_source"]["run_id"].startswith(
        "model_compare_"
    )
    assert model_card["annual_prediction_source"]["sha256"] == (
        weekly["selected_score_config"]["source_prediction_sha256"]
    )
    assert "model-comparison" in model_card["method_summary"]
    validation = model_card["validation_summary"]
    assert validation["model_name"] == weekly["model_name"]
    assert validation["run_id"] == weekly["selected_score_config"]["source_prediction_run_id"]
    assert validation["rank_by_mae"] == 1
    assert validation["n_predictions"] == 408
    assert validation["mae_incidence_per_100k"] == 18.240783
    assert validation["rmse_incidence_per_100k"] == 29.536604
    assert validation["pearson_correlation"] == 0.755185
    assert "observational_not_causal" in validation["comparison_assumption_flags"]


def test_public_weekly_export_excludes_probable_only_state_source_rows() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    all_flags = {
        flag
        for record in weekly["records"]
        for flag in record.get("feature_quality_flags", [])
    }

    assert "mdh_probable_only_2024" not in all_flags
    assert "state_source_not_cdc_public_use" not in all_flags
    assert weekly["selected_score_config"]["source_prediction_run_id"].endswith(
        "end2023_mintrain5_ridge1p0_shrink5p0"
    )


def test_source_catalog_exposes_selected_annual_prediction_branch() -> None:
    weekly = load_public_json("md_county_risk_weekly.json")
    source_catalog = load_public_json("source_catalog.json")

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
    assert annual_prediction["notes"].startswith(
        "Selected annual prediction rows from model-comparison output"
    )


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
