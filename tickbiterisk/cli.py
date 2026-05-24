from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from tickbiterisk.etl.census_population import (
    CensusApiResponseError,
    build_census_intercensal_1990_population_url,
    build_census_intercensal_2000_population_url,
    build_census_pep_2019_population_url,
    build_census_pep_2023_charv_population_url,
    fetch_maryland_county_population_estimates,
    get_census_api_key,
    sanitize_census_url,
)
from tickbiterisk.etl.noaa import (
    build_noaa_daily_data_url,
    build_noaa_station_url,
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    get_noaa_token,
    select_long_coverage_stations,
)
from tickbiterisk.etl.noaa_backfill import (
    NoaaBackfillError,
    audit_noaa_station_coverage,
    resolve_maryland_noaa_county_fips,
    run_noaa_county_backfill,
    run_noaa_maryland_backfill,
    validate_noaa_backfill_args,
)
from tickbiterisk.etl.open_meteo import (
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
)
from tickbiterisk.etl.population_build import write_county_population_output
from tickbiterisk.etl.weather_build import (
    read_noaa_daily_observations_input,
    write_noaa_daily_observations_output,
    write_noaa_stations_output,
    write_weather_daily_output,
    write_weather_features_monthly_output,
    write_weather_features_weekly_output,
    write_weather_locations_output,
)
from tickbiterisk.etl.weather_features import (
    add_trailing_monthly_anomalies,
    add_trailing_weekly_anomalies,
    compute_noaa_monthly_weather_features,
    compute_noaa_weekly_weather_features,
    compute_monthly_weather_features,
    compute_weekly_weather_features,
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


@etl_app.command("census-population")
def census_population(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print planned Census queries."),
) -> None:
    api_key = get_census_api_key()
    urls = _census_population_urls(api_key=api_key)
    if dry_run:
        typer.echo(f"Planned Census population query(s): {len(urls)}")
        for url in urls:
            typer.echo(sanitize_census_url(url))
        return

    try:
        rows = fetch_maryland_county_population_estimates(api_key=api_key)
    except CensusApiResponseError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output = write_county_population_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} county-year population row(s) to {output}")


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
    weekly_features = add_trailing_weekly_anomalies(
        compute_weekly_weather_features(rows)
    )
    weekly_output = write_weather_features_weekly_output(
        weekly_features, output_dir, append=True
    )
    monthly_features = add_trailing_monthly_anomalies(
        compute_monthly_weather_features(rows)
    )
    monthly_output = write_weather_features_monthly_output(
        monthly_features, output_dir, append=True
    )
    typer.echo(f"Wrote {daily_output}")
    typer.echo(f"Wrote {weekly_output}")
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


@etl_app.command("noaa-weather-features")
def noaa_weather_features(
    input_path: Path = typer.Option(
        Path("build/etl/noaa_ghcnd_daily_observations.csv"),
        help="Input noaa_ghcnd_daily_observations.csv path.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
) -> None:
    rows = read_noaa_daily_observations_input(input_path)
    weekly_features = add_trailing_weekly_anomalies(
        compute_noaa_weekly_weather_features(rows)
    )
    weekly_output = write_weather_features_weekly_output(
        weekly_features, output_dir, append=True
    )
    monthly_features = add_trailing_monthly_anomalies(
        compute_noaa_monthly_weather_features(rows)
    )
    monthly_output = write_weather_features_monthly_output(
        monthly_features, output_dir, append=True
    )
    typer.echo(f"Wrote {len(weekly_features)} NOAA weekly feature row(s) to {weekly_output}")
    typer.echo(
        f"Wrote {len(monthly_features)} NOAA monthly feature row(s) to {monthly_output}"
    )


@etl_app.command("noaa-backfill-county")
def noaa_backfill_county(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    start_date: str = typer.Option(..., help="Daily observation start date."),
    end_date: str = typer.Option(..., help="Daily observation end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    station_limit: int = typer.Option(
        1, help="Maximum number of selected NOAA stations to backfill."
    ),
    min_data_coverage: float = typer.Option(
        0.5, help="Minimum NOAA station data coverage."
    ),
    max_end_lag_days: int = typer.Option(
        14, help="Allowed station-reporting lag at the requested end date."
    ),
    dry_run: bool = typer.Option(False, help="Print planned query without fetching data."),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    station_url = build_noaa_station_url(
        county_fips,
        parsed_start_date,
        parsed_end_date,
    )
    if dry_run:
        typer.echo(station_url)
        typer.echo("daily URLs require station selection")
        return

    try:
        result = run_noaa_county_backfill(
            county_fips=county_fips,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            output_dir=output_dir,
            token=get_noaa_token(),
            station_limit=station_limit,
            min_data_coverage=min_data_coverage,
            max_end_lag_days=max_end_lag_days,
        )
    except NoaaBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Selected {result.station_count} station(s): "
        f"{', '.join(result.selected_station_ids)}"
    )
    typer.echo(f"Wrote {result.stations_output_path}")
    typer.echo(
        f"Wrote {result.daily_observation_count} daily observation row(s) "
        f"to {result.daily_output_path}"
    )


@etl_app.command("noaa-backfill-maryland")
def noaa_backfill_maryland(
    start_date: str = typer.Option(..., help="Daily observation start date."),
    end_date: str = typer.Option(..., help="Daily observation end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    county_fips: list[str] | None = typer.Option(
        None,
        "--county-fips",
        help="Optional Maryland county FIPS subset. Repeat for multiple counties.",
    ),
    station_limit: int = typer.Option(
        1, help="Maximum number of selected NOAA stations per county."
    ),
    min_data_coverage: float = typer.Option(
        0.5, help="Minimum NOAA station data coverage."
    ),
    max_end_lag_days: int = typer.Option(
        14, help="Allowed station-reporting lag at the requested end date."
    ),
    fail_fast: bool = typer.Option(False, help="Stop at the first county failure."),
    allow_partial: bool = typer.Option(
        False, help="Exit successfully even when one or more counties fail."
    ),
    nearest_station_fallback: bool = typer.Option(
        False,
        help="Use nearest qualifying Maryland station when a county has no internal station.",
    ),
    dry_run: bool = typer.Option(False, help="Print planned queries without fetching data."),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    try:
        county_fips_values = resolve_maryland_noaa_county_fips(county_fips)
    except NoaaBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc
    try:
        validate_noaa_backfill_args(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            station_limit=station_limit,
        )
    except NoaaBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if dry_run:
        typer.echo(
            f"Planned {len(county_fips_values)} Maryland NOAA county backfill(s)"
        )
        for value in county_fips_values:
            typer.echo(
                build_noaa_station_url(
                    value,
                    parsed_start_date,
                    parsed_end_date,
                )
            )
        typer.echo("daily URLs require station selection")
        return

    try:
        result = run_noaa_maryland_backfill(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            output_dir=output_dir,
            token=get_noaa_token(),
            county_fips_values=county_fips_values,
            station_limit=station_limit,
            min_data_coverage=min_data_coverage,
            max_end_lag_days=max_end_lag_days,
            continue_on_error=not fail_fast,
            nearest_station_fallback=nearest_station_fallback,
        )
    except NoaaBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Completed {result.success_count}/{result.county_count} "
        "Maryland county backfill(s)"
    )
    typer.echo(f"Wrote {result.daily_observation_count} daily observation row(s)")
    if result.failure_count:
        typer.echo(f"Failures: {result.failure_count}")
        for failure in result.failures:
            typer.echo(f"{failure.county_fips}: {failure.error}")
        if not allow_partial:
            raise typer.Exit(1)


@etl_app.command("noaa-audit-stations")
def noaa_audit_stations(
    start_date: str = typer.Option(..., help="Coverage start date."),
    end_date: str = typer.Option(..., help="Coverage end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    county_fips: list[str] | None = typer.Option(
        None,
        "--county-fips",
        help="Optional Maryland county FIPS subset. Repeat for multiple counties.",
    ),
    station_limit: int = typer.Option(
        1, help="Maximum number of selected NOAA stations per county."
    ),
    min_data_coverage: float = typer.Option(
        0.5, help="Minimum NOAA station data coverage."
    ),
    max_end_lag_days: int = typer.Option(
        14, help="Allowed station-reporting lag at the requested end date."
    ),
    nearest_station_fallback: bool = typer.Option(
        False,
        help="Use nearest qualifying Maryland station when a county has no internal station.",
    ),
    dry_run: bool = typer.Option(False, help="Print planned station queries."),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    try:
        county_fips_values = resolve_maryland_noaa_county_fips(county_fips)
        validate_noaa_backfill_args(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            station_limit=station_limit,
        )
    except NoaaBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if dry_run:
        typer.echo(f"Planned {len(county_fips_values)} NOAA station audit query(s)")
        for value in county_fips_values:
            typer.echo(
                build_noaa_station_url(
                    value,
                    parsed_start_date,
                    parsed_end_date,
                )
            )
        return

    result = audit_noaa_station_coverage(
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        output_dir=output_dir,
        token=get_noaa_token(),
        county_fips_values=county_fips_values,
        station_limit=station_limit,
        min_data_coverage=min_data_coverage,
        max_end_lag_days=max_end_lag_days,
        nearest_station_fallback=nearest_station_fallback,
    )
    typer.echo(f"Audited {result.county_count} county station set(s)")
    typer.echo(
        f"ok={result.ok_count}, "
        f"needs_fallback={result.needs_fallback_count}, "
        f"errors={result.error_count}"
    )
    typer.echo(f"Wrote {result.output_path}")


def _parse_iso_date(value: str, option_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(
            f"{option_name} must use YYYY-MM-DD format"
        ) from exc


def _census_population_urls(*, api_key: str | None) -> list[str]:
    return [
        build_census_intercensal_1990_population_url(api_key=api_key),
        build_census_intercensal_2000_population_url(api_key=api_key),
        build_census_pep_2019_population_url(api_key=api_key),
        *[
            build_census_pep_2023_charv_population_url(year=year, api_key=api_key)
            for year in range(2020, 2024)
        ],
    ]


if __name__ == "__main__":
    app()
