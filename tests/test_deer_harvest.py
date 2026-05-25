from dataclasses import replace

import pandas as pd

from tickbiterisk.etl.county_reference import CountyReference
from tickbiterisk.etl.deer_build import write_deer_harvest_output
from tickbiterisk.etl.deer_harvest import (
    MarylandDeerHarvest,
    attach_deer_harvest_density,
    parse_maryland_dnr_deer_harvest_html,
)


DEER_HARVEST_HTML = """
<html>
  <body>
    <table>
      <tbody>
        <tr><td colspan="10">Maryland Reported Antlered and Antlerless Deer Harvest for the 2024-2025 and 2025-2026 Hunting Seasons</td></tr>
        <tr><td></td><td colspan="3">Antlered</td><td colspan="3">Antlerless</td><td colspan="3">Total</td></tr>
        <tr>
          <td>County</td>
          <td>2024-25</td><td>2025-26</td><td>% Change</td>
          <td>2024-25</td><td>2025-26</td><td>% Change</td>
          <td>2024-25</td><td>2025-26</td><td>% Change</td>
        </tr>
        <tr>
          <td>Allegany</td>
          <td>1,868</td><td>1,739</td><td>-6.9</td>
          <td>1,544</td><td>1,185</td><td>-23.3</td>
          <td>3,412</td><td>2,924</td><td>-14.3</td>
        </tr>
        <tr>
          <td>Baltimore</td>
          <td>2,109</td><td>2,008</td><td>-4.8</td>
          <td>3,130</td><td>2,771</td><td>-11.5</td>
          <td>5,239</td><td>4,779</td><td>-8.8</td>
        </tr>
        <tr><td>Caroline</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
        <tr>
          <td>whitetail</td>
          <td>878</td><td>914</td><td>4.1</td>
          <td>2,262</td><td>1,622</td><td>-28.3</td>
          <td>3,140</td><td>2,536</td><td>-19.2</td>
        </tr>
        <tr>
          <td>sika</td>
          <td>2</td><td>2</td><td>*</td>
          <td>2</td><td>2</td><td>*</td>
          <td>4</td><td>4</td><td>*</td>
        </tr>
        <tr>
          <td>Prince George’s</td>
          <td>755</td><td>466</td><td>-38.3</td>
          <td>1,051</td><td>532</td><td>-49.4</td>
          <td>1,806</td><td>998</td><td>-44.7</td>
        </tr>
        <tr><td>Total</td><td>34,291</td><td>31,688</td><td>-7.6</td><td>49,910</td><td>39,961</td><td>-19.9</td><td>84,201</td><td>71,649</td><td>-14.9</td></tr>
      </tbody>
    </table>
  </body>
</html>
"""


def county_ref(county_fips: str, county_name: str, aland_sqmi: float) -> CountyReference:
    return CountyReference(
        county_fips=county_fips,
        state_fips="24",
        state="MD",
        county_name=county_name,
        aland_sqmi=aland_sqmi,
        awater_sqmi=1.0,
        intptlat=39.0,
        intptlon=-76.0,
        geography_source="Census Gazetteer 2024 counties",
        source_url_hash="c" * 64,
    )


def test_parse_maryland_dnr_deer_harvest_html_extracts_county_seasons() -> None:
    rows = parse_maryland_dnr_deer_harvest_html(
        DEER_HARVEST_HTML,
        source_url="https://example.test/deer-harvest",
        source_id="md_dnr_deer_harvest_2026",
    )

    allegany_2025 = next(
        row
        for row in rows
        if row.county_fips == "24001"
        and row.season_start_year == 2025
        and row.species == "all_deer"
    )
    assert allegany_2025.county_name == "Allegany County"
    assert allegany_2025.season_label == "2025-26"
    assert allegany_2025.antlered_harvest == 1739
    assert allegany_2025.antlerless_harvest == 1185
    assert allegany_2025.total_harvest == 2924
    assert allegany_2025.is_derived_total is False
    assert allegany_2025.land_area_sqmi is None
    assert allegany_2025.harvest_per_sqmi is None
    assert len(allegany_2025.source_url_hash) == 64


def test_parse_maryland_dnr_deer_harvest_html_keeps_species_and_derived_totals() -> None:
    rows = parse_maryland_dnr_deer_harvest_html(
        DEER_HARVEST_HTML,
        source_url="https://example.test/deer-harvest",
        source_id="md_dnr_deer_harvest_2026",
    )

    caroline_rows = [
        row
        for row in rows
        if row.county_fips == "24011" and row.season_start_year == 2025
    ]

    assert sorted(row.species for row in caroline_rows) == [
        "all_deer",
        "sika_deer",
        "white_tailed_deer",
    ]
    derived_total = next(row for row in caroline_rows if row.species == "all_deer")
    assert derived_total.antlered_harvest == 916
    assert derived_total.antlerless_harvest == 1624
    assert derived_total.total_harvest == 2540
    assert derived_total.is_derived_total is True


def test_parse_maryland_dnr_deer_harvest_html_normalizes_curly_county_names() -> None:
    rows = parse_maryland_dnr_deer_harvest_html(
        DEER_HARVEST_HTML,
        source_url="https://example.test/deer-harvest",
        source_id="md_dnr_deer_harvest_2026",
    )

    prince_georges = next(
        row
        for row in rows
        if row.county_fips == "24033"
        and row.season_start_year == 2025
        and row.species == "all_deer"
    )
    assert prince_georges.county_name == "Prince George's County"
    assert prince_georges.total_harvest == 998


def test_parse_maryland_dnr_deer_harvest_html_maps_baltimore_to_county() -> None:
    rows = parse_maryland_dnr_deer_harvest_html(
        DEER_HARVEST_HTML,
        source_url="https://example.test/deer-harvest",
        source_id="md_dnr_deer_harvest_2026",
    )

    baltimore = next(
        row
        for row in rows
        if row.season_start_year == 2025
        and row.species == "all_deer"
        and row.county_name.startswith("Baltimore")
    )
    assert baltimore.county_fips == "24005"
    assert baltimore.county_name == "Baltimore County"
    assert baltimore.total_harvest == 4779


def test_attach_deer_harvest_density_uses_census_land_area() -> None:
    rows = parse_maryland_dnr_deer_harvest_html(
        DEER_HARVEST_HTML,
        source_url="https://example.test/deer-harvest",
        source_id="md_dnr_deer_harvest_2026",
    )

    with_density = attach_deer_harvest_density(
        rows,
        [county_ref("24001", "Allegany County", 422.199)],
    )

    allegany_2025 = next(
        row
        for row in with_density
        if row.county_fips == "24001"
        and row.season_start_year == 2025
        and row.species == "all_deer"
    )
    assert allegany_2025.land_area_sqmi == 422.199
    assert allegany_2025.harvest_per_sqmi == 6.925644


def test_write_deer_harvest_output_appends_and_dedupes_by_county_season_species(
    tmp_path,
) -> None:
    row = MarylandDeerHarvest(
        county_fips="24001",
        county_name="Allegany County",
        season_start_year=2025,
        season_label="2025-26",
        species="all_deer",
        antlered_harvest=1739,
        antlerless_harvest=1185,
        total_harvest=2924,
        land_area_sqmi=422.199,
        harvest_per_sqmi=6.925644,
        is_derived_total=False,
        source_id="md_dnr_deer_harvest_2026",
        source_url_hash="d" * 64,
    )
    replacement = replace(row, total_harvest=2925, harvest_per_sqmi=6.928014)

    write_deer_harvest_output([row], tmp_path)
    output = write_deer_harvest_output([replacement], tmp_path, append=True)

    df = pd.read_csv(output, dtype={"county_fips": str})
    assert output.name == "maryland_dnr_deer_harvest.csv"
    assert list(df.columns) == [
        "county_fips",
        "county_name",
        "season_start_year",
        "season_label",
        "species",
        "antlered_harvest",
        "antlerless_harvest",
        "total_harvest",
        "land_area_sqmi",
        "harvest_per_sqmi",
        "is_derived_total",
        "source_id",
        "source_url_hash",
    ]
    assert len(df) == 1
    assert int(df.loc[0, "total_harvest"]) == 2925
