import hashlib
from urllib.parse import parse_qs, urlparse

from tickbiterisk.etl.regional_county_geometry import (
    CENSUS_TIGERWEB_COUNTY_QUERY_URL,
    MIDATLANTIC_STATE_FIPS,
    build_regional_county_geojson_provenance,
    build_tigerweb_county_query_url,
    normalize_tigerweb_county_geojson,
    validate_regional_county_geojson_footprint,
)


def test_build_tigerweb_county_query_url_targets_midatlantic_geojson() -> None:
    url = build_tigerweb_county_query_url()

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert url.startswith(CENSUS_TIGERWEB_COUNTY_QUERY_URL)
    assert query["f"] == ["geojson"]
    assert query["returnGeometry"] == ["true"]
    assert query["outSR"] == ["4326"]
    assert query["geometryPrecision"] == ["6"]
    where = query["where"][0]
    for state_fips in MIDATLANTIC_STATE_FIPS:
        assert f"'{state_fips}'" in where


def test_normalize_tigerweb_county_geojson_maps_properties() -> None:
    source_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": "24001",
                    "STATE": "24",
                    "COUNTY": "001",
                    "NAME": "Allegany County",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                },
            }
        ],
    }

    normalized = normalize_tigerweb_county_geojson(source_geojson)

    assert normalized["type"] == "FeatureCollection"
    feature = normalized["features"][0]
    assert feature["properties"]["county_fips"] == "24001"
    assert feature["properties"]["state_fips"] == "24"
    assert feature["properties"]["county_name"] == "Allegany County"
    assert feature["properties"]["source_geoid"] == "24001"
    assert feature["geometry"] == source_geojson["features"][0]["geometry"]


def test_normalize_tigerweb_county_geojson_hashes_supplied_source_url() -> None:
    source_url = "file:///tmp/regional-counties.geojson"
    source_geojson = _tigerweb_geojson(
        [
            ("24001", "24", "Allegany County"),
        ]
    )

    normalized = normalize_tigerweb_county_geojson(
        source_geojson,
        source_url=source_url,
    )

    feature = normalized["features"][0]
    assert feature["properties"]["source_url_hash"] == hashlib.sha256(
        source_url.encode("utf-8")
    ).hexdigest()


def test_validate_regional_county_geojson_footprint_rejects_missing_states() -> None:
    normalized = normalize_tigerweb_county_geojson(
        _tigerweb_geojson(
            [
                ("24001", "24", "Allegany County"),
            ]
        )
    )

    try:
        validate_regional_county_geojson_footprint(normalized)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected missing-state footprint validation failure")

    assert "Regional county GeoJSON footprint incomplete" in message
    assert "missing state FIPS" in message
    assert "10" in message
    assert "42" in message


def test_build_regional_county_geojson_provenance_records_artifact(tmp_path) -> None:
    artifact_path = tmp_path / "regional_counties.geojson"
    artifact_path.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    source_url = build_tigerweb_county_query_url()

    record = build_regional_county_geojson_provenance(
        source_url=source_url,
        artifact_paths=[artifact_path],
        row_count=283,
        output_dir=tmp_path,
    )

    assert record.source_id == "census_tigerweb_midatlantic_county_geojson"
    assert record.source_url == source_url
    assert record.row_count == 283
    assert "regional-county-adjacency" in record.acquisition_command
    assert "DE/DC/MD/PA/VA/WV" in record.request_description


def _tigerweb_geojson(features: list[tuple[str, str, str]]) -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "GEOID": county_fips,
                    "STATE": state_fips,
                    "COUNTY": county_fips[2:],
                    "NAME": county_name,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                },
            }
            for county_fips, state_fips, county_name in features
        ],
    }
