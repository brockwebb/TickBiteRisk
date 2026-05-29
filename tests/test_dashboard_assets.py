import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.dashboard_assets import (
    TIGERWEB_COUNTIES_URL,
    normalize_maryland_county_geojson,
    normalize_regional_county_geojson,
    normalize_regional_state_geojson,
    simplify_regional_geojson_for_web_map,
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


def test_normalize_regional_state_geojson_keeps_public_boundary_fields() -> None:
    normalized = normalize_regional_state_geojson(_regional_state_geojson())

    assert normalized["type"] == "FeatureCollection"
    assert normalized["metadata"]["feature_count"] == 2
    assert normalized["metadata"]["scope"] == "midatlantic_state_boundary"
    assert normalized["metadata"]["research_only"] is True
    assert normalized["features"][0]["properties"] == {
        "state_fips": "24",
        "state_abbr": "MD",
        "state_name": "Maryland",
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
    regional_states_path = tmp_path / "regional_states.geojson"
    regional_states_path.write_text(
        json.dumps(_regional_state_geojson()),
        encoding="utf-8",
    )
    regional_incidence_path = _write_regional_incidence(
        tmp_path / "regional_incidence.csv"
    )
    overlays_path = _write_regional_overlay_summary(tmp_path / "overlays.csv")
    output_dir = tmp_path / "regional-dashboard"

    result = write_regional_research_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        regional_counties_geojson_path=regional_geojson_path,
        regional_states_geojson_path=regional_states_path,
        regional_incidence_path=regional_incidence_path,
        spatial_regime_summary_path=overlays_path,
        model_name="linear_blend_baseline",
    )

    assert result.weekly_risk_path.name == "regional_county_risk_weekly.json"
    assert result.county_geojson_path.name == "regional_counties.geojson"
    assert result.state_geojson_path is not None
    assert result.state_geojson_path.name == "regional_states.geojson"
    assert result.annual_incidence_path is not None
    assert result.annual_incidence_path.name == "regional_county_incidence_annual.json"
    assert result.spatial_regime_overlays_path is not None
    assert result.spatial_regime_overlays_path.name == (
        "regional_spatial_regime_overlays.json"
    )

    weekly = json.loads(result.weekly_risk_path.read_text(encoding="utf-8"))
    county_metadata = json.loads(
        result.county_metadata_path.read_text(encoding="utf-8")
    )
    counties = json.loads(result.county_geojson_path.read_text(encoding="utf-8"))
    states = json.loads(result.state_geojson_path.read_text(encoding="utf-8"))
    annual_incidence = json.loads(
        result.annual_incidence_path.read_text(encoding="utf-8")
    )
    overlays = json.loads(
        result.spatial_regime_overlays_path.read_text(encoding="utf-8")
    )
    manifest = json.loads(result.export_manifest_path.read_text(encoding="utf-8"))
    source_catalog = json.loads(result.source_catalog_path.read_text(encoding="utf-8"))

    assert weekly["scope"] == "midatlantic_county_week"
    assert weekly["research_status"]["research_only"] is True
    assert counties["metadata"]["feature_count"] == 2
    assert states["metadata"]["scope"] == "midatlantic_state_boundary"
    assert states["metadata"]["feature_count"] == 2
    assert states["features"][0]["properties"]["state_abbr"] == "MD"
    assert annual_incidence["export_type"] == "regional_county_incidence_annual"
    assert annual_incidence["data_role"] == "observed_historical"
    assert annual_incidence["research_status"]["research_only"] is True
    assert annual_incidence["record_count"] == 2
    assert annual_incidence["year_range"] == [2023, 2024]
    assert "reported cases are not stable true incidence" in (
        " ".join(annual_incidence["caveats"]).lower()
    )
    assert annual_incidence["records"][0] == {
        "county_fips": "24003",
        "county_name": "Anne Arundel County",
        "data_role": "observed_historical",
        "diagnostic_midatlantic_incidence_percentile": 0.72,
        "diagnostic_midatlantic_incidence_rank": 80,
        "diagnostic_midatlantic_incidence_tier": "upper_half",
        "feature_quality_flags": [
            "regional_incidence_diagnostic",
            "reported_cases_not_stable_true_incidence",
        ],
        "incidence_per_100k": 18.5,
        "population": 590000,
        "reported_cases": 109,
        "state_abbr": "MD",
        "state_fips": "24",
        "state_name": "Maryland",
        "year": 2023,
    }
    assert "lyme_panel_sha256" not in annual_incidence["records"][0]
    assert "population_panel_sha256" not in annual_incidence["records"][0]
    assert overlays["record_count"] == 1
    assert overlays["records"][0]["region_id"] == "2024_regime_01"
    assert overlays["records"][0]["county_fips_list"] == ["24003", "42001"]
    anne_arundel = next(
        county
        for county in county_metadata["counties"]
        if county["county_fips"] == "24003"
    )
    assert anne_arundel["selected_spatial_regime"] == {
        "region_id": "2024_regime_01",
        "region_name": "Spatial regime 1",
        "spatial_regime_rank": 1,
        "spatial_regime_feature_year": 2024,
        "forecast_year": 2026,
        "forecast_origin_year": 2023,
    }
    assert "regional_counties.geojson" in manifest["files"]
    assert "regional_states.geojson" in manifest["files"]
    assert "regional_county_incidence_annual.json" in manifest["files"]
    assert "regional_spatial_regime_overlays.json" in manifest["files"]
    assert manifest["record_counts"]["regional_county_geojson_features"] == 2
    assert manifest["record_counts"]["regional_state_geojson_features"] == 2
    assert manifest["record_counts"]["regional_annual_observed_incidence"] == 2
    assert manifest["record_counts"]["spatial_regime_overlays"] == 1
    assert any(
        source["source_id"] == "regional_observed_annual_incidence"
        and source["artifact_type"] == "derived observed surveillance layer"
        for source in source_catalog["sources"]
    )


def test_simplify_regional_geojson_for_web_map_reduces_dense_polygon_rings() -> None:
    normalized = normalize_regional_county_geojson(_dense_regional_geojson())

    simplified = simplify_regional_geojson_for_web_map(
        normalized,
        tolerance=0.01,
        coordinate_precision=4,
    )

    source_ring = normalized["features"][0]["geometry"]["coordinates"][0]
    simplified_ring = simplified["features"][0]["geometry"]["coordinates"][0]

    assert len(source_ring) > 80
    assert len(simplified_ring) < len(source_ring) / 4
    assert simplified_ring[0] == simplified_ring[-1]
    assert len(simplified_ring) >= 4
    assert simplified["metadata"]["web_map_simplified"] is True
    assert simplified["metadata"]["geometry_simplification"] == {
        "coordinate_precision": 4,
        "method": "radial_distance_ring_simplification",
        "tolerance_degrees": 0.01,
    }


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


def _regional_state_geojson() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "STATE": "24",
                    "STUSAB": "MD",
                    "NAME": "Maryland",
                    "GEOID": "24",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-79.5, 37.8],
                            [-75.0, 37.8],
                            [-75.0, 39.8],
                            [-79.5, 39.8],
                            [-79.5, 37.8],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "STATE": "42",
                    "STUSAB": "PA",
                    "NAME": "Pennsylvania",
                    "GEOID": "42",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-80.6, 39.7],
                            [-74.7, 39.7],
                            [-74.7, 42.3],
                            [-80.6, 42.3],
                            [-80.6, 39.7],
                        ]
                    ],
                },
            },
        ],
    }


def _dense_regional_geojson() -> dict:
    ring = []
    for step in range(31):
        ring.append([-77.0 + step * 0.001, 39.0])
    for step in range(1, 31):
        ring.append([-76.97, 39.0 + step * 0.001])
    for step in range(1, 31):
        ring.append([-76.97 - step * 0.001, 39.03])
    for step in range(1, 31):
        ring.append([-77.0, 39.03 - step * 0.001])
    ring.append(ring[0])
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
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring],
                },
            }
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


def _write_regional_incidence(path: Path) -> Path:
    columns = [
        "state_fips",
        "state_abbr",
        "state_name",
        "county_fips",
        "county_name",
        "year",
        "total_cases",
        "population",
        "incidence_per_100k",
        "diagnostic_midatlantic_incidence_rank",
        "diagnostic_midatlantic_incidence_percentile",
        "diagnostic_midatlantic_incidence_tier",
        "diagnostic_prior_year_midatlantic_incidence_rank",
        "diagnostic_midatlantic_incidence_rank_change",
        "lyme_panel_sha256",
        "population_panel_sha256",
        "feature_quality_flags",
    ]
    rows = [
        {
            "state_fips": "24",
            "state_abbr": "MD",
            "state_name": "Maryland",
            "county_fips": "24003",
            "county_name": "Anne Arundel County",
            "year": "2023",
            "total_cases": "109",
            "population": "590000",
            "incidence_per_100k": "18.5",
            "diagnostic_midatlantic_incidence_rank": "80",
            "diagnostic_midatlantic_incidence_percentile": "0.72",
            "diagnostic_midatlantic_incidence_tier": "upper_half",
            "diagnostic_prior_year_midatlantic_incidence_rank": "75",
            "diagnostic_midatlantic_incidence_rank_change": "5",
            "lyme_panel_sha256": "a" * 64,
            "population_panel_sha256": "b" * 64,
            "feature_quality_flags": (
                "regional_incidence_diagnostic,"
                "reported_cases_not_stable_true_incidence"
            ),
        },
        {
            "state_fips": "42",
            "state_abbr": "PA",
            "state_name": "Pennsylvania",
            "county_fips": "42001",
            "county_name": "Adams County",
            "year": "2024",
            "total_cases": "210",
            "population": "105000",
            "incidence_per_100k": "200.0",
            "diagnostic_midatlantic_incidence_rank": "5",
            "diagnostic_midatlantic_incidence_percentile": "0.98",
            "diagnostic_midatlantic_incidence_tier": "top_decile",
            "diagnostic_prior_year_midatlantic_incidence_rank": "10",
            "diagnostic_midatlantic_incidence_rank_change": "-5",
            "lyme_panel_sha256": "a" * 64,
            "population_panel_sha256": "b" * 64,
            "feature_quality_flags": (
                "regional_incidence_diagnostic,"
                "reported_cases_not_stable_true_incidence"
            ),
        },
    ]
    path.write_text(
        ",".join(columns)
        + "\n"
        + "\n".join(
            ",".join(f'"{row[column]}"' for column in columns) for row in rows
        )
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
