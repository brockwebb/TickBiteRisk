"""CLI tests for the config-driven six-state regional NOAA backfill command."""

from __future__ import annotations

from datetime import date

from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation

runner = CliRunner()

CONFIG = """
[weather]
states = ["DC"]
ghcnd_datatypes = ["TMAX", "TMIN", "PRCP", "SNOW", "SNWD"]
start_date = "2017-01-01"
end_date = "2021-12-31"
baseline_years = 30

[weather.station_selection]
station_limit = 1
min_data_coverage = 0.5
max_end_lag_days = 14
nearest_station_fallback = false
"""


def _config(tmp_path):
    path = tmp_path / "weather.toml"
    path.write_text(CONFIG, encoding="utf-8")
    return path


def test_regional_backfill_county_fips_override_targets_subset(tmp_path):
    # Targeted re-pull (e.g. recovering failed counties) without re-fetching the rest.
    cfg = tmp_path / "weather.toml"
    cfg.write_text(CONFIG.replace('states = ["DC"]', 'states = ["PA"]'), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-regional",
            "--config-path",
            str(cfg),
            "--output-dir",
            str(tmp_path / "out"),
            "--county-fips",
            "42001",
            "--county-fips",
            "42003",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Planned 2 " in result.stdout
    assert "42001" in result.stdout and "42003" in result.stdout


def test_regional_backfill_county_fips_outside_region_fails_loud(tmp_path):
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-regional",
            "--config-path",
            str(_config(tmp_path)),
            "--county-fips",
            "36001",  # NY county, not in the six-state universe
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    # Fail-loud signal must be version-robust: click 8.1.7's default CliRunner mixes
    # stderr into result.output (and result.stderr raises "not separately captured"),
    # while click >=8.2 captures stderr separately (absent from result.output). Search
    # a combined string so the message assertion holds under either stream policy.
    combined = result.output
    if result.stderr_bytes is not None:
        combined += result.stderr
    assert "36001" in combined


def test_regional_backfill_dry_run_plans_counties_without_network(tmp_path):
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-regional",
            "--config-path",
            str(_config(tmp_path)),
            "--output-dir",
            str(tmp_path / "out"),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "DC" in result.stdout
    assert "11001" in result.stdout  # District of Columbia FIPS
    assert not (tmp_path / "out" / "noaa_ghcnd_daily_observations.csv").exists()


def test_regional_backfill_run_writes_daily_and_provenance(tmp_path, monkeypatch):
    def fake_stations(county_fips, start_date, end_date, *, token, json_get=None):
        return [
            NoaaStation(
                county_fips=county_fips,
                station_id="GHCND:USW00013743",
                name="DCA",
                latitude=38.85,
                longitude=-77.03,
                mindate=date(1990, 1, 1),
                maxdate=date(2026, 1, 1),
                data_coverage=0.99,
            )
        ]

    def fake_dly(county_fips, station_id, start_date, end_date, *, datatypes=None):
        # Temp must reach the validation window end (config validate_temp_through
        # = 2021-12-31) or the station is correctly rejected.
        return [
            NoaaDailyObservation(
                county_fips=county_fips,
                station_id=station_id,
                date=d,
                source="noaa_ghcnd_dly_bulk",
                tmax_f=50.0,
                tmin_f=32.0,
                prcp_inches=1.0,
                snow_inches=0.0,
                snwd_inches=None,
                source_url_hash="hash",
            )
            for d in (date(2019, 1, 1), date(2021, 12, 31))
        ]

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "fake-token")
    monkeypatch.setattr("tickbiterisk.etl.noaa_backfill.fetch_noaa_stations", fake_stations)
    monkeypatch.setattr("tickbiterisk.cli.fetch_ghcnd_dly_observations", fake_dly)

    out = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-backfill-regional",
            "--config-path",
            str(_config(tmp_path)),
            "--output-dir",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (out / "noaa_ghcnd_daily_observations.csv").exists()
    assert (out / "acquisition_provenance.csv").exists()
