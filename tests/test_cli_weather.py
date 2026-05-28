import csv
from datetime import date

import pandas as pd
import pytest
from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.noaa import NoaaDailyObservation, NoaaStation
from tickbiterisk.etl.noaa_backfill import (
    NoaaCountyBackfillFailure,
    NoaaCountyBackfillResult,
    NoaaMarylandBackfillResult,
    NoaaStationCoverageAuditResult,
)
from tickbiterisk.etl.open_meteo_backfill import (
    OpenMeteoCountyBackfillResult,
    OpenMeteoMarylandBackfillResult,
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
    assert not (tmp_path / "acquisition_provenance.csv").exists()


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
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))

    assert len(provenance_rows) == 1
    provenance = provenance_rows[0]
    assert provenance["source_id"] == "open_meteo_archive_24003_2020_05_01_2020_05_02"
    assert provenance["source_name"] == "Open-Meteo Historical Weather API"
    assert "archive-api.open-meteo.com" in provenance["source_url"]
    assert "start_date=2020-05-01" in provenance["source_url"]
    assert "end_date=2020-05-02" in provenance["source_url"]
    assert (
        provenance["citation_url"]
        == "https://open-meteo.com/en/docs/historical-weather-api"
    )
    assert provenance["request_method"] == "GET"
    assert provenance["row_count"] == "2"
    assert (
        provenance["parser_method"]
        == "fetch_open_meteo_archive;parse_open_meteo_archive_response"
    )
    assert provenance["extraction_quality"] == "accepted"
    assert "tickbiterisk etl weather-backfill-open-meteo" in provenance[
        "acquisition_command"
    ]
    assert "--provenance-manifest-path" in provenance["acquisition_command"]
    assert "weather_daily.csv=" in provenance["derived_artifact_sha256s"]


def test_weather_backfill_appends_acquisition_provenance_manifest(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch(location, start_date, end_date):
        del location
        return [_weather_row(start_date), _weather_row(end_date)]

    monkeypatch.setattr("tickbiterisk.cli.fetch_open_meteo_archive", fake_fetch)

    for start, end in [
        ("2020-05-01", "2020-05-02"),
        ("2020-05-03", "2020-05-04"),
    ]:
        result = runner.invoke(
            app,
            [
                "etl",
                "weather-backfill-open-meteo",
                "--county-fips",
                "24003",
                "--start-date",
                start,
                "--end-date",
                end,
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert [row["source_id"] for row in rows] == [
        "open_meteo_archive_24003_2020_05_01_2020_05_02",
        "open_meteo_archive_24003_2020_05_03_2020_05_04",
    ]
    assert [row["row_count"] for row in rows] == ["2", "2"]


def test_weather_backfill_open_meteo_maryland_dry_run_prints_chunk_plan(
    tmp_path,
) -> None:
    result = runner.invoke(
        app,
        [
            "etl",
            "weather-backfill-open-meteo-maryland",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2020-01-03",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--county-fips",
            "24005",
            "--max-chunk-days",
            "2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Planned 4 Open-Meteo archive request(s)" in result.stdout
    assert "24003" in result.stdout
    assert "24005" in result.stdout
    assert "archive-api.open-meteo.com" in result.stdout
    assert not (tmp_path / "weather_daily.csv").exists()
    assert not (tmp_path / "acquisition_provenance.csv").exists()


def test_weather_backfill_open_meteo_maryland_command_reports_summary(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_backfill(**kwargs) -> OpenMeteoMarylandBackfillResult:
        assert kwargs["county_fips_values"] == ["24003"]
        assert kwargs["output_dir"] == tmp_path
        assert kwargs["max_chunk_days"] == 2
        assert kwargs["max_attempts"] == 5
        assert kwargs["sleep_seconds"] == 3.0
        assert kwargs["inter_chunk_sleep_seconds"] == 0.25
        assert kwargs["inter_county_sleep_seconds"] == 0.5
        for filename in [
            "weather_daily.csv",
            "weather_features_weekly.csv",
            "weather_features_monthly.csv",
        ]:
            (tmp_path / filename).write_text("placeholder\n", encoding="utf-8")
        return OpenMeteoMarylandBackfillResult(
            county_results=[
                OpenMeteoCountyBackfillResult(
                    county_fips="24003",
                    chunk_count=2,
                    daily_observation_count=3,
                    daily_output_path=tmp_path / "weather_daily.csv",
                    weekly_output_path=tmp_path / "weather_features_weekly.csv",
                    monthly_output_path=tmp_path / "weather_features_monthly.csv",
                )
            ],
            failures=[],
        )

    monkeypatch.setattr(
        "tickbiterisk.cli.run_open_meteo_maryland_backfill", fake_backfill
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "weather-backfill-open-meteo-maryland",
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2020-01-03",
            "--output-dir",
            str(tmp_path),
            "--county-fips",
            "24003",
            "--max-chunk-days",
            "2",
            "--max-attempts",
            "5",
            "--retry-sleep-seconds",
            "3",
            "--inter-chunk-sleep-seconds",
            "0.25",
            "--inter-county-sleep-seconds",
            "0.5",
        ],
    )

    assert result.exit_code == 0
    assert "Completed 1/1 Maryland Open-Meteo county backfill(s)" in result.stdout
    assert "Wrote 3 daily observation row(s)" in result.stdout
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        provenance_rows = list(csv.DictReader(handle))

    assert len(provenance_rows) == 1
    provenance = provenance_rows[0]
    assert provenance["source_id"] == "open_meteo_archive_24003_2020_01_01_2020_01_03"
    assert provenance["row_count"] == "3"
    assert provenance["source_url"].count("archive-api.open-meteo.com") == 2
    assert "start_date=2020-01-01" in provenance["source_url"]
    assert "end_date=2020-01-02" in provenance["source_url"]
    assert "start_date=2020-01-03" in provenance["source_url"]
    assert "end_date=2020-01-03" in provenance["source_url"]
    assert "weather-backfill-open-meteo-maryland" in provenance["acquisition_command"]
    assert "--county-fips 24003" in provenance["acquisition_command"]
    assert "--max-chunk-days 2" in provenance["acquisition_command"]
    assert "weather_features_monthly.csv=" in provenance["derived_artifact_sha256s"]


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
    assert not (tmp_path / "acquisition_provenance.csv").exists()


def test_noaa_stations_command_writes_acquisition_provenance(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(county_fips, start_date, end_date, *, token):
        assert county_fips == "24003"
        assert start_date == date(1992, 1, 1)
        assert end_date == date(2026, 5, 24)
        assert token == "fake-noaa-token"
        return [
            NoaaStation(
                county_fips="24003",
                station_id="GHCND:USW00093721",
                name="BWI",
                latitude=39.1733,
                longitude=-76.684,
                mindate=date(1939, 7, 1),
                maxdate=date(2026, 5, 24),
                data_coverage=0.99,
            )
        ]

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "fake-noaa-token")
    monkeypatch.setattr("tickbiterisk.cli.fetch_noaa_stations", fake_fetch)

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
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "noaa_ghcnd_stations.csv").exists()
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "noaa_cdo_ghcnd_stations_24003_1992_01_01_2026_05_24"
    assert row["source_name"] == "NOAA CDO GHCND station discovery"
    assert "ncei.noaa.gov/cdo-web/api/v2/stations" in row["source_url"]
    assert "FIPS%3A24003" in row["source_url"]
    assert row["citation_url"] == "https://www.ncei.noaa.gov/cdo-web/webservices/v2"
    assert row["request_method"] == "GET"
    assert row["row_count"] == "1"
    assert (
        row["parser_method"]
        == "fetch_noaa_stations;parse_noaa_station_response;select_long_coverage_stations"
    )
    assert row["extraction_quality"] == "accepted"
    assert "fake-noaa-token" not in "\n".join(row.values())
    assert "NOAA_TOKEN" in row["access_notes"]
    assert "--provenance-manifest-path" in row["acquisition_command"]
    assert "noaa_ghcnd_stations.csv=" in row["derived_artifact_sha256s"]


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
    assert not (tmp_path / "acquisition_provenance.csv").exists()


def test_noaa_daily_command_writes_acquisition_provenance(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(county_fips, station_id, start_date, end_date, *, token):
        assert county_fips == "24003"
        assert station_id == "GHCND:USW00093721"
        assert start_date == date(1992, 5, 1)
        assert end_date == date(1992, 5, 7)
        assert token == "fake-noaa-token"
        return [
            NoaaDailyObservation(
                county_fips="24003",
                station_id="GHCND:USW00093721",
                date=date(1992, 5, 1),
                source="noaa_cdo_ghcnd_daily",
                tmax_f=72.0,
                tmin_f=50.0,
                prcp_inches=0.1,
                snow_inches=0.0,
                snwd_inches=None,
                source_url_hash="a" * 64,
            )
        ]

    monkeypatch.setattr("tickbiterisk.cli.get_noaa_token", lambda: "fake-noaa-token")
    monkeypatch.setattr("tickbiterisk.cli.fetch_noaa_daily_observations", fake_fetch)

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
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "noaa_ghcnd_daily_observations.csv").exists()
    assert "Wrote acquisition provenance manifest" in result.stdout

    with (tmp_path / "acquisition_provenance.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == (
        "noaa_cdo_ghcnd_daily_24003_ghcnd_usw00093721_1992_05_01_1992_05_07"
    )
    assert row["source_name"] == "NOAA CDO GHCND daily observations"
    assert "ncei.noaa.gov/cdo-web/api/v2/data" in row["source_url"]
    assert "stationid=GHCND%3AUSW00093721" in row["source_url"]
    assert row["row_count"] == "1"
    assert (
        row["parser_method"]
        == "fetch_noaa_daily_observations;parse_noaa_daily_data_response"
    )
    assert "fake-noaa-token" not in "\n".join(row.values())
    assert "NOAA_TOKEN" in row["access_notes"]
    assert "--provenance-manifest-path" in row["acquisition_command"]
    assert "noaa_ghcnd_daily_observations.csv=" in row["derived_artifact_sha256s"]


def test_noaa_weather_features_command_reads_raw_noaa_csv(tmp_path) -> None:
    input_path = tmp_path / "noaa_ghcnd_daily_observations.csv"
    input_path.write_text(
        "\n".join(
            [
                "county_fips,station_id,date,source,tmax_f,tmin_f,prcp_inches,snow_inches,snwd_inches,source_url_hash",
                "24003,GHCND:USW00093721,2020-05-04,noaa_cdo_ghcnd_daily,70,50,0.10,0,,bbbb",
                "24003,GHCND:USW00093721,2020-05-05,noaa_cdo_ghcnd_daily,92,72,0,0,,bbbb",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "noaa-weather-features",
            "--input-path",
            str(input_path),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    weekly = tmp_path / "weather_features_weekly.csv"
    monthly = tmp_path / "weather_features_monthly.csv"
    assert weekly.exists()
    assert monthly.exists()
    assert "Wrote 1 NOAA weekly feature row(s)" in result.stdout
    assert "Wrote 1 NOAA monthly feature row(s)" in result.stdout
    df = pd.read_csv(weekly, dtype={"county_fips": str})
    assert df.loc[0, "source"] == "noaa_cdo_ghcnd_daily"
    assert df.loc[0, "weather_model"] == "ghcnd_station_daily"
    assert pd.isna(df.loc[0, "humidity_mean_pct"])


def test_open_meteo_weather_features_command_recomputes_existing_daily_csv(
    tmp_path,
) -> None:
    input_path = tmp_path / "weather_daily.csv"
    input_path.write_text(
        "\n".join(
            [
                "county_fips,date,source,weather_model,temp_mean_f,temp_max_f,temp_min_f,humidity_mean_pct,humidity_max_pct,humidity_min_pct,dew_point_mean_f,precipitation_mm,rain_mm,snowfall_mm,precipitation_hours,soil_temp_0_7cm_f,soil_moisture_0_7cm,evapotranspiration_mm,wind_mean_mph,wind_max_mph,source_url_hash",
                "24003,2021-01-01,open_meteo_archive,open_meteo_archive,60,65,55,82,95,65,48,0,0,0,0,48,0.30,1.0,5,10,aaaaaaaa",
                "24003,2020-01-01,open_meteo_archive,open_meteo_archive,50,55,45,72,85,55,40,0,0,0,0,45,0.25,1.0,5,10,bbbbbbbb",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "open-meteo-weather-features",
            "--input-path",
            str(input_path),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 2 Open-Meteo monthly feature row(s)" in result.stdout
    monthly = pd.read_csv(
        tmp_path / "weather_features_monthly.csv", dtype={"county_fips": str}
    )
    jan_2021 = monthly[(monthly["county_fips"] == "24003") & (monthly["year"] == 2021)]
    assert jan_2021.iloc[0]["temp_anomaly_vs_10yr"] == 10.0


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
