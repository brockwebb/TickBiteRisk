from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from tickbiterisk.etl.noaa import (
    build_noaa_daily_data_url,
    build_noaa_station_url,
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    get_noaa_token,
    select_long_coverage_stations,
)
from tickbiterisk.etl.open_meteo import (
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
)
from tickbiterisk.etl.weather_build import (
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_locations_output,
)
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    compute_monthly_weather_features,
)
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations

app = typer.Typer(help="TickBiteRisk ETL utilities")
etl_app = typer.Typer(help="ETL commands")
app.add_typer(etl_app, name="etl")


@etl_app.command("check")
def etl_check(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    )
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"ETL output directory ready: {output_dir}")


@etl_app.command("weather-locations")
def weather_locations(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    )
) -> None:
    output = write_weather_locations_output(
        load_maryland_weather_locations(), output_dir
    )
    typer.echo(f"Wrote {output}")


@etl_app.command("weather-backfill-open-meteo")
def weather_backfill_open_meteo(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    start_date: str = typer.Option(..., help="Start date for archive pull."),
    end_date: str = typer.Option(..., help="End date for archive pull."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print URL without fetching data."),
) -> None:
    locations = load_maryland_weather_locations()
    location = next(
        (row for row in locations if row.county_fips == county_fips.zfill(5)),
        None,
    )
    if location is None:
        raise typer.BadParameter(f"Unknown Maryland county FIPS: {county_fips}")

    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    url = build_open_meteo_archive_url(location, parsed_start_date, parsed_end_date)
    if dry_run:
        typer.echo(f"{location.county_fips} {location.county_name}: {url}")
        return

    rows = fetch_open_meteo_archive(location, parsed_start_date, parsed_end_date)
    daily_output = write_weather_daily_output(rows, output_dir, append=True)
    monthly_features = add_trailing_monthly_anomalies(
        compute_monthly_weather_features(rows)
    )
    monthly_output = write_weather_features_monthly_output(
        monthly_features, output_dir, append=True
    )
    typer.echo(f"Wrote {daily_output}")
    typer.echo(f"Wrote {monthly_output}")


@etl_app.command("noaa-stations")
def noaa_stations(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    start_date: str = typer.Option(..., help="Coverage start date."),
    end_date: str = typer.Option(..., help="Coverage end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    min_data_coverage: float = typer.Option(
        0.5, help="Minimum NOAA station data coverage."
    ),
    max_end_lag_days: int = typer.Option(
        14, help="Allowed station-reporting lag at the requested end date."
    ),
    dry_run: bool = typer.Option(False, help="Print URL without fetching data."),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    url = build_noaa_station_url(county_fips, parsed_start_date, parsed_end_date)
    if dry_run:
        typer.echo(url)
        return

    stations = fetch_noaa_stations(
        county_fips,
        parsed_start_date,
        parsed_end_date,
        token=get_noaa_token(),
    )
    selected = select_long_coverage_stations(
        stations,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
    )
    output = write_noaa_stations_output(selected, output_dir, append=True)
    typer.echo(f"Wrote {output}")


@etl_app.command("noaa-daily")
def noaa_daily(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    station_id: str = typer.Option(..., help="NOAA GHCND station ID."),
    start_date: str = typer.Option(..., help="Daily observation start date."),
    end_date: str = typer.Option(..., help="Daily observation end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print URL without fetching data."),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    url = build_noaa_daily_data_url(station_id, parsed_start_date, parsed_end_date)
    if dry_run:
        typer.echo(url)
        return

    rows = fetch_noaa_daily_observations(
        county_fips,
        station_id,
        parsed_start_date,
        parsed_end_date,
        token=get_noaa_token(),
    )
    output = write_noaa_daily_observations_output(rows, output_dir, append=True)
    typer.echo(f"Wrote {output}")


def _parse_iso_date(value: str, option_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(
            f"{option_name} must use YYYY-MM-DD format"
        ) from exc


if __name__ == "__main__":
    app()
