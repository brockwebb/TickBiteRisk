from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_weather_locations_command_writes_locations(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["etl", "weather-locations", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert (tmp_path / "weather_locations.csv").exists()
    assert "weather_locations.csv" in result.stdout


def test_weather_backfill_dry_run_prints_open_meteo_url(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "weather-backfill-open-meteo",
            "--county-fips",
            "24003",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2020-01-02",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "archive-api.open-meteo.com" in result.stdout
    assert "24003" in result.stdout
    assert not (tmp_path / "weather_daily.csv").exists()
