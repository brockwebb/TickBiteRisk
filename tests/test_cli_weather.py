import pytest
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.noaa_backfill import (
    NoaaCountyBackfillFailure,
    NoaaCountyBackfillResult,
    NoaaMarylandBackfillResult,
)


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


def test_noaa_stations_dry_run_prints_noaa_url(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-stations",
            "--county-fips",
            "24003",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "2026-05-24",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ncei.noaa.gov" in result.stdout
    assert "FIPS%3A24003" in result.stdout
    assert not (tmp_path / "noaa_ghcnd_stations.csv").exists()


def test_noaa_daily_dry_run_prints_noaa_url(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-daily",
            "--county-fips",
            "24003",
            "--station-id",
            "GHCND:USW00093721",
            "--start-date",
            "1992-05-01",
            "--end-date",
            "1992-05-07",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ncei.noaa.gov" in result.stdout
    assert "GHCND%3AUSW00093721" in result.stdout
    assert not (tmp_path / "noaa_ghcnd_daily_observations.csv").exists()


def test_noaa_backfill_county_dry_run_prints_station_discovery_url(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-county",
            "--county-fips",
            "24003",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "2026-05-24",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ncei.noaa.gov" in result.stdout
    assert "FIPS%3A24003" in result.stdout
    assert "daily URLs require station selection" in result.stdout
    assert not (tmp_path / "noaa_ghcnd_stations.csv").exists()


def test_noaa_backfill_county_command_reports_result(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_token() -> str:
        return "token-value"

    def fake_backfill(**kwargs) -> NoaaCountyBackfillResult:
        assert kwargs["county_fips"] == "24003"
        assert kwargs["token"] == "token-value"
        assert kwargs["station_limit"] == 1
        assert kwargs["output_dir"] == tmp_path
        return NoaaCountyBackfillResult(
            county_fips="24003",
            selected_station_ids=["GHCND:BWI"],
            station_count=1,
            daily_observation_count=2,
            stations_output_path=tmp_path / "noaa_ghcnd_stations.csv",
            daily_output_path=tmp_path / "noaa_ghcnd_daily_observations.csv",
        )

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", fake_token)
    monkeypatch.setattr("tickbiterisk.cli.run_noaa_county_backfill", fake_backfill)

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-county",
            "--county-fips",
            "24003",
            "--start-date",
            "1992-05-01",
            "--end-date",
            "1992-05-02",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Selected 1 station(s): GHCND:BWI" in result.stdout
    assert "Wrote 2 daily observation row(s)" in result.stdout


def test_noaa_backfill_maryland_dry_run_prints_county_plan(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "2026-05-24",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--county-fips",
            "24005",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Planned 2 Maryland NOAA county backfill(s)" in result.stdout
    assert "FIPS%3A24003" in result.stdout
    assert "FIPS%3A24005" in result.stdout
    assert not (tmp_path / "noaa_ghcnd_daily_observations.csv").exists()


def test_noaa_backfill_maryland_command_reports_summary(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_token() -> str:
        return "token-value"

    def fake_backfill(**kwargs) -> NoaaMarylandBackfillResult:
        assert kwargs["token"] == "token-value"
        assert kwargs["county_fips_values"] == ["24003"]
        assert kwargs["output_dir"] == tmp_path
        return NoaaMarylandBackfillResult(
            county_results=[
                NoaaCountyBackfillResult(
                    county_fips="24003",
                    selected_station_ids=["GHCND:BWI"],
                    station_count=1,
                    daily_observation_count=2,
                    stations_output_path=tmp_path / "noaa_ghcnd_stations.csv",
                    daily_output_path=tmp_path / "noaa_ghcnd_daily_observations.csv",
                )
            ],
            failures=[],
        )

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", fake_token)
    monkeypatch.setattr("tickbiterisk.cli.run_noaa_maryland_backfill", fake_backfill)

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "1992-05-01",
            "--end-date",
            "1992-05-02",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
        ],
    )

    assert result.exit_code == 0
    assert "Completed 1/1 Maryland county backfill(s)" in result.stdout
    assert "Wrote 2 daily observation row(s)" in result.stdout


def test_noaa_backfill_maryland_exits_nonzero_on_partial_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_token() -> str:
        return "token-value"

    def fake_backfill(**kwargs) -> NoaaMarylandBackfillResult:
        return NoaaMarylandBackfillResult(
            county_results=[],
            failures=[
                NoaaCountyBackfillFailure(
                    county_fips="24003",
                    error="No NOAA GHCND station covers county_fips=24003",
                )
            ],
        )

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", fake_token)
    monkeypatch.setattr("tickbiterisk.cli.run_noaa_maryland_backfill", fake_backfill)

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "1992-05-01",
            "--end-date",
            "1992-05-02",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
        ],
    )

    assert result.exit_code == 1
    assert "Failures: 1" in result.stdout
    assert "24003: No NOAA GHCND station covers county_fips=24003" in result.stdout


def test_noaa_backfill_maryland_allow_partial_exits_zero(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "token-value")
    monkeypatch.setattr(
        "tickbiterisk.cli.run_noaa_maryland_backfill",
        lambda **kwargs: NoaaMarylandBackfillResult(
            county_results=[],
            failures=[
                NoaaCountyBackfillFailure(county_fips="24003", error="station miss")
            ],
        ),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "1992-05-01",
            "--end-date",
            "1992-05-02",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--allow-partial",
        ],
    )

    assert result.exit_code == 0
    assert "Failures: 1" in result.stdout


def test_noaa_backfill_maryland_dry_run_rejects_non_maryland_fips(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "1992-01-02",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "99999",
            "--dry-run",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown Maryland county FIPS: 99999" in result.output


def test_noaa_backfill_maryland_dry_run_rejects_inverted_dates(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-maryland",
            "--start-date",
            "2026-05-24",
            "--end-date",
            "1992-01-01",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--dry-run",
        ],
    )

    assert result.exit_code != 0
    assert "end_date must be on or after start_date" in result.output
