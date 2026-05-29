import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.dashboard_assets import (
    TIGERWEB_COUNTIES_URL,
    normalize_maryland_county_geojson,
    normalize_regional_county_geojson,
    write_dashboard_assets,
    write_regional_research_dashboard_assets,
)


def test_normalize_maryland_county_geojson_keeps_public_county_fields() -> None:
    source = _fixture_geojson()

    normalized = normalize_maryland_county_geojson(source)
    anne_arundel = next(
        feature
        for feature in normalized["features"]
        if feature["properties"]["county_fips"] == "24003"
    )

    assert normalized["type"] == "FeatureCollection"
    assert normalized["metadata"]["source_url"] == TIGERWEB_COUNTIES_URL
    assert normalized["metadata"]["state_fips"] == "24"
    assert normalized["metadata"]["feature_count"] == 24
    assert anne_arundel["properties"] == {
        "county_fips": "24003",
        "county_name": "Anne Arundel County",
    }
    assert anne_arundel["geometry"]["type"] == "Polygon"


def test_write_dashboard_assets_writes_risk_json_and_geojson(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    model_summary_path = _write_model_summary(tmp_path / "model_summary.csv")
    output_dir = tmp_path / "public" / "data"
    fake_geojson = _fixture_geojson()

    result = write_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        model_summary_path=model_summary_path,
        fetch_geojson=lambda: fake_geojson,
    )

    assert result.output_dir == output_dir
    assert result.weekly_risk_path.name == "md_county_risk_weekly.json"
    assert result.county_geojson_path.name == "md_counties.geojson"

    weekly = json.loads(result.weekly_risk_path.read_text(encoding="utf-8"))
    model_card = json.loads(result.model_card_path.read_text(encoding="utf-8"))
    counties = json.loads(result.county_geojson_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.export_manifest_path.read_text(encoding="utf-8"))

    assert weekly["record_count"] == 2
    assert model_card["validation_summary"]["rank_by_mae"] == 1
    assert counties["metadata"]["feature_count"] == 24
    assert "md_counties.geojson" in manifest["files"]
    assert manifest["record_counts"]["county_geojson_features"] == 24
    assert any(
        feature["properties"]["county_fips"] == "24003"
        for feature in counties["features"]
    )


def test_normalize_regional_county_geojson_keeps_state_and_county_fields() -> None:
    normalized = normalize_regional_county_geojson(_regional_geojson())

    assert normalized["type"] == "FeatureCollection"
    assert normalized["metadata"]["feature_count"] == 2
    assert normalized["metadata"]["scope"] == "midatlantic_county_equivalent"
    assert normalized["features"][0]["properties"] == {
        "county_fips": "24003",
        "county_name": "Anne Arundel County",
        "state_fips": "24",
        "state_abbr": "MD",
    }


def test_write_regional_research_dashboard_assets_writes_map_and_overlay(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    regional_geojson_path = tmp_path / "regional_counties.geojson"
    regional_geojson_path.write_text(
        json.dumps(_regional_geojson()),
        encoding="utf-8",
    )
    overlays_path = _write_regional_overlay_summary(tmp_path / "overlays.csv")
    output_dir = tmp_path / "regional-dashboard"

    result = write_regional_research_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        regional_counties_geojson_path=regional_geojson_path,
        spatial_regime_summary_path=overlays_path,
        model_name="linear_blend_baseline",
    )

    assert result.weekly_risk_path.name == "regional_county_risk_weekly.json"
    assert result.county_geojson_path.name == "regional_counties.geojson"
    assert result.spatial_regime_overlays_path is not None
    assert result.spatial_regime_overlays_path.name == (
        "regional_spatial_regime_overlays.json"
    )

    weekly = json.loads(result.weekly_risk_path.read_text(encoding="utf-8"))
    counties = json.loads(result.county_geojson_path.read_text(encoding="utf-8"))
    overlays = json.loads(
        result.spatial_regime_overlays_path.read_text(encoding="utf-8")
    )
    manifest = json.loads(result.export_manifest_path.read_text(encoding="utf-8"))

    assert weekly["scope"] == "midatlantic_county_week"
    assert weekly["research_status"]["research_only"] is True
    assert counties["metadata"]["feature_count"] == 2
    assert overlays["record_count"] == 1
    assert overlays["records"][0]["region_id"] == "2024_regime_01"
    assert overlays["records"][0]["county_fips_list"] == ["24003", "42001"]
    assert "regional_counties.geojson" in manifest["files"]
    assert "regional_spatial_regime_overlays.json" in manifest["files"]
    assert manifest["record_counts"]["regional_county_geojson_features"] == 2
    assert manifest["record_counts"]["spatial_regime_overlays"] == 1


def _fixture_geojson() -> dict:
    county_rows = [
        ("24001", "Allegany County"),
        ("24003", "Anne Arundel County"),
        ("24005", "Baltimore County"),
        ("24009", "Calvert County"),
        ("24011", "Caroline County"),
        ("24013", "Carroll County"),
        ("24015", "Cecil County"),
        ("24017", "Charles County"),
        ("24019", "Dorchester County"),
        ("24021", "Frederick County"),
        ("24023", "Garrett County"),
        ("24025", "Harford County"),
        ("24027", "Howard County"),
        ("24029", "Kent County"),
        ("24031", "Montgomery County"),
        ("24033", "Prince George's County"),
        ("24035", "Queen Anne's County"),
        ("24037", "St. Mary's County"),
        ("24039", "Somerset County"),
        ("24041", "Talbot County"),
        ("24043", "Washington County"),
        ("24045", "Wicomico County"),
        ("24047", "Worcester County"),
        ("24510", "Baltimore city"),
    ]
    return {
        "type": "FeatureCollection",
        "features": [
            _county_feature(county_fips, county_name, index)
            for index, (county_fips, county_name) in enumerate(county_rows)
        ],
    }


def _regional_geojson() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "county_fips": "24003",
                    "county_name": "Anne Arundel County",
                    "state_fips": "24",
                    "source_geoid": "24003",
                },
                "geometry": {"type": "Point", "coordinates": [-76.6, 39.0]},
            },
            {
                "type": "Feature",
                "properties": {
                    "county_fips": "42001",
                    "county_name": "Adams County",
                    "state_fips": "42",
                    "source_geoid": "42001",
                },
                "geometry": {"type": "Point", "coordinates": [-77.2, 39.9]},
            },
        ],
    }


def _write_regional_overlay_summary(path: Path) -> Path:
    columns = [
        "run_id",
        "model_name",
        "region_id",
        "region_name",
        "spatial_regime_rank",
        "spatial_regime_feature_year",
        "forecast_year",
        "forecast_origin_year",
        "n_counties",
        "county_fips_list",
        "forecast_population",
        "predicted_total_cases",
        "predicted_incidence_per_100k",
        "lower_80_incidence_per_100k",
        "upper_80_incidence_per_100k",
        "lower_95_incidence_per_100k",
        "upper_95_incidence_per_100k",
        "summary_assumption_flags",
    ]
    row = {
        "run_id": "overlay-run",
        "model_name": "linear_blend_baseline",
        "region_id": "2024_regime_01",
        "region_name": "Spatial regime 1",
        "spatial_regime_rank": "1",
        "spatial_regime_feature_year": "2024",
        "forecast_year": "2026",
        "forecast_origin_year": "2023",
        "n_counties": "2",
        "county_fips_list": "24003,42001",
        "forecast_population": "210000",
        "predicted_total_cases": "12.5",
        "predicted_incidence_per_100k": "5.952381",
        "lower_80_incidence_per_100k": "3.0",
        "upper_80_incidence_per_100k": "8.0",
        "lower_95_incidence_per_100k": "1.0",
        "upper_95_incidence_per_100k": "10.0",
        "summary_assumption_flags": (
            "localized_spatial_regime_research,not_public_default"
        ),
    }
    path.write_text(
        ",".join(columns)
        + "\n"
        + ",".join(f'"{row[column]}"' for column in columns)
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_model_summary(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                (
                    "run_id,rank_by_mae,model_name,model_family,feature_profile,"
                    "n_predictions,mae_incidence_per_100k,rmse_incidence_per_100k,"
                    "pearson_correlation,comparison_assumption_flags"
                ),
                "run1,1,linear_blend_baseline,ensemble,lagged_outcome_blend,2,1.25,2.5,0.7,observational_not_causal",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _county_feature(county_fips: str, county_name: str, index: int) -> dict:
    lon = -79.5 + (index % 6) * 0.35
    lat = 37.9 + (index // 6) * 0.35
    return {
        "type": "Feature",
        "properties": {
            "GEOID": county_fips,
            "NAME": county_name,
            "STATE": "24",
            "COUNTY": county_fips[-3:],
            "EXTRA": "drop me",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon, lat],
                    [lon + 0.2, lat],
                    [lon + 0.2, lat + 0.2],
                    [lon, lat + 0.2],
                    [lon, lat],
                ]
            ],
        },
    }
