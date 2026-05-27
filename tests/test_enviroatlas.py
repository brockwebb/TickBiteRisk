import csv
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tickbiterisk.etl.enviroatlas import (
    ENVIROATLAS_HABITAT_FIELDS,
    ENVIROATLAS_HABITAT_QUERY_BASE_URL,
    build_enviroatlas_maryland_habitat_query_url,
    parse_enviroatlas_county_habitat,
)
from tickbiterisk.etl.enviroatlas_build import (
    ENVIROATLAS_COUNTY_HABITAT_COLUMNS,
    write_enviroatlas_county_habitat_output,
)


ARCGIS_SAMPLE = {
    "features": [
        {
            "attributes": {
                "GEOID": "24003",
                "NAME": "Anne Arundel County",
                "pfor": "38.5",
                "pfor90": 42.25,
                "pwetl": 11,
                "pwetl95": 3.75,
                "pdev": 27.125,
                "Pimprv": 14.5,
                "pagr": 18.0,
                "pagrp": 10.0,
                "pagrc": 8.0,
                "rNI45": 72.5,
                "rfor45": 51.25,
                "rfor9045": 55.0,
                "NINDEX": 68.9,
            }
        },
        {
            "attributes": {
                "GEOID": 24001,
                "County": "Allegany County",
                "pfor": 70,
                "pfor90": 72,
                "pwetl": 2,
                "pwetl95": 0.5,
                "pdev": 9,
                "Pimprv": 3,
                "pagr": 15,
                "pagrp": 12,
                "pagrc": 3,
                "rNI45": 81,
                "rfor45": 76,
                "rfor9045": 78,
                "NINDEX": 84,
            }
        },
        {
            "attributes": {
                "GEOID": "51013",
                "NAME": "Arlington County",
                "pfor": 8,
                "pfor90": 9,
                "pwetl": 1,
                "pwetl95": 0,
                "pdev": 75,
                "Pimprv": 45,
                "pagr": 0,
                "pagrp": 0,
                "pagrc": 0,
                "rNI45": 12,
                "rfor45": 8,
                "rfor9045": 9,
                "NINDEX": 20,
            }
        },
    ]
}


def test_build_enviroatlas_query_url_targets_maryland_without_geometry() -> None:
    url = build_enviroatlas_maryland_habitat_query_url()
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert url.startswith(f"{ENVIROATLAS_HABITAT_QUERY_BASE_URL}/query?")
    assert params["where"] == ["GEOID LIKE '24%'"]
    assert params["returnGeometry"] == ["false"]
    assert params["f"] == ["json"]
    assert params["outFields"] == [",".join(ENVIROATLAS_HABITAT_FIELDS)]


def test_parse_enviroatlas_county_habitat_maps_fields_and_filters_maryland() -> None:
    rows = parse_enviroatlas_county_habitat(
        ARCGIS_SAMPLE,
        source_url="https://example.test/enviroatlas/query",
    )

    assert [row.county_fips for row in rows] == ["24001", "24003"]
    assert rows[0].county_name == "Allegany County"
    assert rows[1].county_name == "Anne Arundel County"
    assert rows[1].forest_pct == 38.5
    assert rows[1].forest_woody_wetland_pct == 42.25
    assert rows[1].wetland_pct == 11.0
    assert rows[1].emergent_wetland_pct == 3.75
    assert rows[1].developed_pct == 27.125
    assert rows[1].impervious_pct == 14.5
    assert rows[1].agriculture_pct == 18.0
    assert rows[1].pasture_hay_pct == 10.0
    assert rows[1].cultivated_crop_pct == 8.0
    assert rows[1].riparian_natural_45m_pct == 72.5
    assert rows[1].riparian_forest_45m_pct == 51.25
    assert rows[1].riparian_forest_woody_wetland_45m_pct == 55.0
    assert rows[1].natural_land_cover_index == 68.9
    assert len(rows[1].source_url_hash) == 64
    assert rows[1].feature_quality_flags == "static_enviroatlas_2011"


def test_write_enviroatlas_county_habitat_output_orders_and_dedupes(
    tmp_path: Path,
) -> None:
    rows = parse_enviroatlas_county_habitat(
        ARCGIS_SAMPLE,
        source_url="https://example.test/enviroatlas/query",
    )
    replacement = replace(rows[1], forest_pct=39.0)

    write_enviroatlas_county_habitat_output([rows[1]], tmp_path)
    output = write_enviroatlas_county_habitat_output(
        [replacement, rows[0]],
        tmp_path,
        append=True,
    )

    assert output.name == "enviroatlas_county_habitat.csv"
    with output.open(newline="", encoding="utf-8") as handle:
        output_rows = list(csv.DictReader(handle))

    assert list(output_rows[0]) == ENVIROATLAS_COUNTY_HABITAT_COLUMNS
    assert [row["county_fips"] for row in output_rows] == ["24001", "24003"]
    assert len(output_rows) == 2
    assert output_rows[1]["forest_pct"] == "39.0"
    assert output_rows[1]["feature_quality_flags"] == "static_enviroatlas_2011"
