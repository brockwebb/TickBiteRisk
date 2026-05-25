from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_deer_harvest_command_writes_density_output(tmp_path, monkeypatch) -> None:
    county_reference = tmp_path / "county_reference.csv"
    county_reference.write_text(
        "\n".join(
            [
                "county_fips,state_fips,state,county_name,aland_sqmi,awater_sqmi,intptlat,intptlon,geography_source,source_url_hash",
                "24001,24,MD,Allegany County,422.199,5.68,39.612313,-78.703104,Census Gazetteer 2024 counties,cccc",
            ]
        ),
        encoding="utf-8",
    )
    sample_html = """
    <table>
      <tr><td colspan="10">Maryland Reported Antlered and Antlerless Deer Harvest for the 2024-2025 and 2025-2026 Hunting Seasons</td></tr>
      <tr><td></td><td colspan="3">Antlered</td><td colspan="3">Antlerless</td><td colspan="3">Total</td></tr>
      <tr><td>County</td><td>2024-25</td><td>2025-26</td><td>% Change</td><td>2024-25</td><td>2025-26</td><td>% Change</td><td>2024-25</td><td>2025-26</td><td>% Change</td></tr>
      <tr><td>Allegany</td><td>1,868</td><td>1,739</td><td>-6.9</td><td>1,544</td><td>1,185</td><td>-23.3</td><td>3,412</td><td>2,924</td><td>-14.3</td></tr>
    </table>
    """

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_maryland_dnr_deer_harvest_html",
        lambda url: sample_html,
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.MARYLAND_DNR_DEER_HARVEST_URLS",
        ["https://example.test/deer-harvest"],
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "deer-harvest",
            "--county-reference-path",
            str(county_reference),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 deer harvest row(s)" in result.stdout
    assert (tmp_path / "maryland_dnr_deer_harvest.csv").exists()
