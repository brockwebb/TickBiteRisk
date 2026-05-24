from datetime import date

import pytest
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.noaa_backfill import (
    NoaaCountyBackfillFailure,
    NoaaCountyBackfillResult,
    NoaaMarylandBackfillResult,
    NoaaStationCoverageAuditResult,
)
from tickbiterisk.etl.open_meteo import WeatherDailyObservation


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


def test_weather_backfill_writes_weekly_and_monthly_features(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [_weather_row(date(2020, 5, 1)), _weather_row(date(2020, 5, 2))]

    monkeypatch.setattr(
        "tickbiterisk.cli.fetch_open_meteo_archive",
        lambda location, start_date, end_date: rows,
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "weather-backfill-open-meteo",
            "--county-fips",
            "24003",
            "--start-date",
            "2020-05-01",
            "--end-date",
            "2020-05-02",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "weather_daily.csv").exists()
    assert (tmp_path / "weather_features_weekly.csv").exists()
    assert (tmp_path / "weather_features_monthly.csv").exists()
    assert "weather_features_weekly.csv" in result.stdout
    assert "weather_features_monthly.csv" in result.stdout


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
        assert kwargs["nearest_station_fallback"] is False
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


def test_noaa_backfill_maryland_command_passes_nearest_station_fallback(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_backfill(**kwargs) -> NoaaMarylandBackfillResult:
        assert kwargs["nearest_station_fallback"] is True
        return NoaaMarylandBackfillResult(county_results=[], failures=[])

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "token-value")
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
            "--nearest-station-fallback",
        ],
    )

    assert result.exit_code == 0


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


def test_noaa_audit_stations_dry_run_prints_station_urls(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-audit-stations",
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
    assert "Planned 2 NOAA station audit query(s)" in result.stdout
    assert "FIPS%3A24003" in result.stdout
    assert "FIPS%3A24005" in result.stdout
    assert not (tmp_path / "noaa_station_coverage_audit.csv").exists()


def test_noaa_audit_stations_command_reports_summary(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_audit(**kwargs) -> NoaaStationCoverageAuditResult:
        assert kwargs["county_fips_values"] == ["24003"]
        assert kwargs["output_dir"] == tmp_path
        assert kwargs["token"] == "token-value"
        assert kwargs["nearest_station_fallback"] is False
        return NoaaStationCoverageAuditResult(
            output_path=tmp_path / "noaa_station_coverage_audit.csv",
            county_count=1,
            ok_count=1,
            needs_fallback_count=0,
            error_count=0,
        )

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "token-value")
    monkeypatch.setattr("tickbiterisk.cli.audit_noaa_station_coverage", fake_audit)

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-audit-stations",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "2026-05-24",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
        ],
    )

    assert result.exit_code == 0
    assert "Audited 1 county station set(s)" in result.stdout
    assert "ok=1, needs_fallback=0, errors=0" in result.stdout
    assert "noaa_station_coverage_audit.csv" in result.stdout


def test_noaa_audit_stations_command_passes_nearest_station_fallback(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_audit(**kwargs) -> NoaaStationCoverageAuditResult:
        assert kwargs["nearest_station_fallback"] is True
        return NoaaStationCoverageAuditResult(
            output_path=tmp_path / "noaa_station_coverage_audit.csv",
            county_count=1,
            ok_count=1,
            needs_fallback_count=0,
            error_count=0,
        )

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "token-value")
    monkeypatch.setattr("tickbiterisk.cli.audit_noaa_station_coverage", fake_audit)

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-audit-stations",
            "--start-date",
            "1992-01-01",
            "--end-date",
            "2026-05-24",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--nearest-station-fallback",
        ],
    )

    assert result.exit_code == 0


def _weather_row(day: date) -> WeatherDailyObservation:
    return WeatherDailyObservation(
        county_fips="24003",
        date=day,
        source="open_meteo_archive",
        weather_model="open_meteo_archive",
        temp_mean_f=55.0,
        temp_max_f=62.0,
        temp_min_f=45.0,
        humidity_mean_pct=82.0,
        humidity_max_pct=95.0,
        humidity_min_pct=65.0,
        dew_point_mean_f=48.0,
        precipitation_mm=0.0,
        rain_mm=0.0,
        snowfall_mm=0.0,
        precipitation_hours=0.0,
        soil_temp_0_7cm_f=48.0,
        soil_moisture_0_7cm=0.30,
        evapotranspiration_mm=1.0,
        wind_mean_mph=5.0,
        wind_max_mph=10.0,
        source_url_hash="a" * 64,
    )
