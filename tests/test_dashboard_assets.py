import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.dashboard_assets import (
    TIGERWEB_COUNTIES_URL,
    normalize_maryland_county_geojson,
    write_dashboard_assets,
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
    output_dir = tmp_path / "public" / "data"
    fake_geojson = _fixture_geojson()

    result = write_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        fetch_geojson=lambda: fake_geojson,
    )

    assert result.output_dir == output_dir
    assert result.weekly_risk_path.name == "md_county_risk_weekly.json"
    assert result.county_geojson_path.name == "md_counties.geojson"

    weekly = json.loads(result.weekly_risk_path.read_text(encoding="utf-8"))
    counties = json.loads(result.county_geojson_path.read_text(encoding="utf-8"))

    assert weekly["record_count"] == 2
    assert counties["metadata"]["feature_count"] == 24
    assert any(
        feature["properties"]["county_fips"] == "24003"
        for feature in counties["features"]
    )


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
