from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REGIONAL_DATA_DIR = REPO_ROOT / "public" / "research-data" / "regional"

EXPECTED_REGIONAL_DATA_FILES = {
    "model_card.json",
    "regional_counties.geojson",
    "regional_county_incidence_annual.json",
    "regional_states.geojson",
    "regional_county_metadata.json",
    "regional_county_risk_weekly.json",
    "regional_spatial_regime_overlays.json",
    "source_catalog.json",
    "static_export_manifest.json",
}

EXPECTED_RESEARCH_STATUS = {
    "not_public_maryland_default": True,
    "research_only": True,
}


def load_regional_json(filename: str) -> dict:
    return json.loads((REGIONAL_DATA_DIR / filename).read_text(encoding="utf-8"))


def test_regional_research_bundle_is_not_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "public/research-data/regional/" not in gitignore


def test_regional_research_bundle_files_are_present_for_pages_preview() -> None:
    committed_files = {
        path.relative_to(REGIONAL_DATA_DIR).as_posix()
        for path in REGIONAL_DATA_DIR.rglob("*")
        if path.is_file()
    }

    assert committed_files == EXPECTED_REGIONAL_DATA_FILES


def test_regional_research_bundle_has_complete_county_week_contract() -> None:
    weekly = load_regional_json("regional_county_risk_weekly.json")
    metadata = load_regional_json("regional_county_metadata.json")
    geojson = load_regional_json("regional_counties.geojson")
    annual = load_regional_json("regional_county_incidence_annual.json")
    states = load_regional_json("regional_states.geojson")
    overlays = load_regional_json("regional_spatial_regime_overlays.json")
    source_catalog = load_regional_json("source_catalog.json")
    research_status_payloads = [
        load_regional_json(filename)
        for filename in EXPECTED_REGIONAL_DATA_FILES
        if filename.endswith(".json") and filename != "regional_counties.geojson"
    ]

    weekly_counties = {record["county_fips"] for record in weekly["records"]}
    metadata_counties = {county["county_fips"] for county in metadata["counties"]}
    geojson_counties = {
        feature["properties"]["county_fips"] for feature in geojson["features"]
    }

    assert all(
        payload["research_status"] == EXPECTED_RESEARCH_STATUS
        for payload in research_status_payloads
    )
    assert weekly["record_count"] == len(weekly["records"])
    assert len(weekly_counties) == 283
    assert weekly_counties == metadata_counties == geojson_counties
    assert weekly["year_selection"] == "all_available_years"
    assert {record["year"] for record in weekly["records"]} == {2024, 2025, 2026}
    assert {record["data_year"] for record in weekly["records"]} == {
        2024,
        2025,
        2026,
    }
    assert weekly["selected_forecast_metadata"]["forecast_years"] == [
        2024,
        2025,
        2026,
    ]
    assert len(weekly["selected_forecast_metadata"]["source_prediction_run_ids"]) == 3
    assert len(weekly["records"]) == 283 * 53 * 3
    assert {record["mmwr_week"] for record in weekly["records"]} == set(range(1, 54))
    assert all(
        county["available_years"] == [2024, 2025, 2026]
        for county in metadata["counties"]
    )

    assert geojson["metadata"]["web_map_simplified"] is True
    assert geojson["metadata"]["feature_count"] == 283
    assert len(geojson["features"]) == 283
    assert states["metadata"]["scope"] == "midatlantic_state_boundary"
    assert states["metadata"]["web_map_simplified"] is True
    assert states["metadata"]["feature_count"] == 6
    assert len(states["features"]) == 6
    assert {
        feature["properties"]["state_abbr"] for feature in states["features"]
    } == {"DE", "DC", "MD", "PA", "VA", "WV"}
    assert annual["data_role"] == "observed_historical"
    assert annual["research_status"] == EXPECTED_RESEARCH_STATUS
    assert annual["record_count"] == len(annual["records"])
    assert annual["year_range"] == [2001, 2024]
    assert sum(1 for record in annual["records"] if record["year"] == 2024) == 67
    assert {
        record["state_abbr"] for record in annual["records"] if record["year"] == 2024
    } == {"PA"}
    assert len({record["county_fips"] for record in annual["records"]}) == 283
    assert set(annual["records"][0]) == {
        "county_fips",
        "county_name",
        "data_role",
        "diagnostic_midatlantic_incidence_percentile",
        "diagnostic_midatlantic_incidence_rank",
        "diagnostic_midatlantic_incidence_tier",
        "feature_quality_flags",
        "incidence_per_100k",
        "population",
        "reported_cases",
        "state_abbr",
        "state_fips",
        "state_name",
        "year",
    }
    assert {record["data_role"] for record in annual["records"]} == {
        "observed_historical"
    }
    assert all("total_cases" not in record for record in annual["records"])
    assert all("lyme_panel_sha256" not in record for record in annual["records"])
    assert all("population_panel_sha256" not in record for record in annual["records"])
    assert all(
        "reported_cases_not_stable_true_incidence" in record["feature_quality_flags"]
        for record in annual["records"]
    )
    assert "reported cases are not stable true incidence" in (
        " ".join(annual["caveats"]).lower()
    )
    assert any(
        source["source_id"] == "regional_observed_annual_incidence"
        for source in source_catalog["sources"]
    )

    assert overlays["record_count"] == len(overlays["records"])
    assert overlays["research_status"]["research_only"] is True
    assert all(
        county.get("selected_spatial_regime")
        for county in metadata["counties"]
    )


def test_pages_workflow_validates_regional_research_preview_assets() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )

    for token in [
        "node --check public/regional-research.js",
        "Validate regional research preview data",
        "public/research-data/regional",
        'data_dir.rglob("*")',
        "present != sorted(expected_files)",
        "regional_payloads",
        "regional_county_incidence_annual.json",
        "reported_cases",
        "total_cases",
        "regional_county_risk_weekly.json",
        "regional_counties.geojson",
        "regional_states.geojson",
    ]:
        assert token in workflow
