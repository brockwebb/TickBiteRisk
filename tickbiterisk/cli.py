from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import typer

from tickbiterisk.etl.build import write_reconciled_lyme_outputs
from tickbiterisk.etl.building_permits import (
    build_census_bps_county_annual_url,
    fetch_census_bps_county_text,
    parse_census_bps_county_text,
    source_id_from_census_bps_year,
)
from tickbiterisk.etl.building_permits_build import write_building_permits_output
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
from tickbiterisk.etl.contact_pressure import build_contact_pressure_features
from tickbiterisk.etl.contact_pressure_build import write_contact_pressure_output
from tickbiterisk.etl.county_reference import (
    CENSUS_GAZETTEER_COUNTIES_2024_URL,
    fetch_census_gazetteer_counties_text,
    parse_census_gazetteer_counties,
)
from tickbiterisk.etl.county_reference_build import (
    read_county_reference_output,
    write_county_reference_output,
)
from tickbiterisk.etl.deer_build import (
    dedupe_deer_harvest_rows,
    write_deer_harvest_output,
)
from tickbiterisk.etl.deer_harvest import (
    MARYLAND_DNR_DEER_ANNUAL_REPORT_URLS,
    MARYLAND_DNR_DEER_HARVEST_URLS,
    attach_deer_harvest_density,
    fetch_maryland_dnr_deer_harvest_html,
    parse_maryland_dnr_deer_harvest_html,
    parse_maryland_dnr_deer_harvest_pdf,
    source_id_from_deer_harvest_url,
)
from tickbiterisk.etl.ecology_sources import (
    ECOLOGY_RAW_DIR,
    ECOLOGY_SOURCE_FILES,
    MARYLAND_DNR_MAST_REPORT_URLS,
)
from tickbiterisk.etl.lyme import (
    parse_cdc_county_dashboard,
    parse_cdc_lyme_geodata,
    parse_cdc_lyme_public_use,
)
from tickbiterisk.etl.mast_acorn import (
    build_mast_acorn_from_pdf,
    read_manual_mast_observations,
)
from tickbiterisk.etl.mast_acorn_build import (
    write_manual_mast_observations_output,
    write_mast_acorn_output,
    write_mast_acorn_summary_output,
)
from tickbiterisk.etl.model_features import build_model_feature_matrix
from tickbiterisk.etl.model_features_build import write_model_feature_matrix_output
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
from tickbiterisk.etl.raw_download import download_source_files
from tickbiterisk.etl.seasonality import (
    SeasonalityInputError,
    build_seasonality_baseline,
    parse_cdc_lyme_monthly_onset,
    parse_cdc_lyme_weekly_onset,
)
from tickbiterisk.etl.seasonality_build import write_seasonality_outputs
from tickbiterisk.etl.tick_status import (
    build_tick_status_county_features,
    parse_ixodes_status,
    parse_lone_star_status,
    parse_pathogen_status,
)
from tickbiterisk.etl.tick_status_build import write_tick_status_outputs
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
    compute_monthly_weather_features,
    compute_noaa_monthly_weather_features,
    compute_noaa_weekly_weather_features,
    compute_weekly_weather_features,
)
from tickbiterisk.etl.weather_locations import load_maryland_weather_locations
from tickbiterisk.modeling.backtest import BacktestInputError, run_baseline_backtests
from tickbiterisk.modeling.backtest_build import write_model_backtest_outputs
from tickbiterisk.modeling.risk_score import (
    RiskScoreInputError,
    build_seasonal_risk_scores,
)
from tickbiterisk.modeling.risk_score_build import write_seasonal_risk_score_outputs

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


@etl_app.command("county-reference")
def county_reference(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
) -> None:
    text = fetch_census_gazetteer_counties_text()
    rows = parse_census_gazetteer_counties(
        text,
        source_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
    )
    output = write_county_reference_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} county reference row(s) to {output}")


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


@etl_app.command("ecology-sources")
def ecology_sources(
    raw_dir: Path = typer.Option(
        ECOLOGY_RAW_DIR,
        help="Ignored raw-data directory for ecology source files.",
    ),
    manifest_path: Path = typer.Option(
        Path("build/etl/ecology/source_manifest.csv"),
        help="Output CSV manifest for downloaded ecology source files.",
    ),
) -> None:
    result = download_source_files(
        ECOLOGY_SOURCE_FILES,
        raw_dir=raw_dir,
        manifest_path=manifest_path,
    )
    typer.echo(
        f"Downloaded/catalogued {result.row_count} ecology source file(s) "
        f"to {result.manifest_path}"
    )


@etl_app.command("building-permits")
def building_permits(
    start_year: int = typer.Option(2000, help="First BPS annual county file year."),
    end_year: int = typer.Option(2025, help="Last BPS annual county file year."),
    output_dir: Path = typer.Option(
        Path("build/etl/building-permits"),
        help="Output directory for building permit ETL artifacts.",
    ),
) -> None:
    if start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")
    if start_year < 2000 or end_year > 2025:
        raise typer.BadParameter(
            "Census BPS county annual ASCII files are supported for 2000-2025"
        )
    rows = []
    for year in range(start_year, end_year + 1):
        source_url = build_census_bps_county_annual_url(year)
        text = fetch_census_bps_county_text(source_url)
        rows.extend(
            parse_census_bps_county_text(
                text,
                source_url=source_url,
                source_id=source_id_from_census_bps_year(year),
            )
        )
    output = write_building_permits_output(rows, output_dir)
    written_row_count = len({(row.county_fips.zfill(5), row.year) for row in rows})
    typer.echo(f"Wrote {written_row_count} building permit row(s) to {output}")


@etl_app.command("contact-pressure")
def contact_pressure(
    building_permits_path: Path = typer.Option(
        Path("build/etl/building-permits/maryland_building_permits_county_year.csv"),
        help="Input Maryland building permits county-year CSV.",
    ),
    county_reference_path: Path = typer.Option(
        Path("build/etl/county-reference/county_reference.csv"),
        help="County reference CSV with Census land area.",
    ),
    population_path: Path = typer.Option(
        Path("build/etl/population/county_population_year.csv"),
        help="County-year population denominator CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/contact-pressure"),
        help="Output directory for contact pressure feature artifacts.",
    ),
) -> None:
    rows = build_contact_pressure_features(
        building_permits_path=building_permits_path,
        county_reference_path=county_reference_path,
        population_path=population_path,
    )
    output = write_contact_pressure_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} contact pressure feature row(s) to {output}")


@etl_app.command("tick-status")
def tick_status(
    raw_dir: Path = typer.Option(
        Path("data/raw/tick-status"),
        help="Raw directory containing CDC tick status XLSX files.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/tick-status"),
        help="Output directory for normalized tick status artifacts.",
    ),
) -> None:
    source_files = [
        (
            "cdc_ixodes_county_status_2025.xlsx",
            "cdc_ixodes_county_status_2025",
            parse_ixodes_status,
        ),
        (
            "cdc_ixodes_pathogen_status_2025.xlsx",
            "cdc_ixodes_pathogen_status_2025",
            parse_pathogen_status,
        ),
        (
            "cdc_lone_star_status_2024.xlsx",
            "cdc_lone_star_status_2024",
            parse_lone_star_status,
        ),
    ]
    for filename, _, _ in source_files:
        source_path = raw_dir / filename
        if not source_path.exists():
            raise typer.BadParameter(
                f"tick status source file not found: {source_path}"
            )

    ixodes_rows = parse_ixodes_status(
        raw_dir / "cdc_ixodes_county_status_2025.xlsx",
        source_id="cdc_ixodes_county_status_2025",
    )
    pathogen_rows = parse_pathogen_status(
        raw_dir / "cdc_ixodes_pathogen_status_2025.xlsx",
        source_id="cdc_ixodes_pathogen_status_2025",
    )
    lone_star_rows = parse_lone_star_status(
        raw_dir / "cdc_lone_star_status_2024.xlsx",
        source_id="cdc_lone_star_status_2024",
    )
    feature_rows = build_tick_status_county_features(
        ixodes_rows=ixodes_rows,
        pathogen_rows=pathogen_rows,
        lone_star_rows=lone_star_rows,
    )
    outputs = write_tick_status_outputs(
        ixodes_rows=ixodes_rows,
        pathogen_rows=pathogen_rows,
        lone_star_rows=lone_star_rows,
        feature_rows=feature_rows,
        output_dir=output_dir,
    )
    typer.echo(
        f"Wrote {len(feature_rows)} tick status feature row(s) to "
        f"{outputs.features_path}"
    )


@etl_app.command("seasonality-baseline")
def seasonality_baseline(
    raw_dir: Path = typer.Option(
        Path("data/raw/seasonality"),
        help="Raw directory containing CDC Lyme seasonality CSV files.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/seasonality"),
        help="Output directory for seasonality baseline ETL artifacts.",
    ),
) -> None:
    monthly_path = raw_dir / "cdc_lyme_monthly_onset_2010_2023.csv"
    weekly_path = raw_dir / "cdc_lyme_weekly_onset_2010_2023.csv"
    for source_path in [monthly_path, weekly_path]:
        if not source_path.exists():
            raise typer.BadParameter(
                f"seasonality source file not found: {source_path}"
            )

    try:
        observations = [
            *parse_cdc_lyme_monthly_onset(
                monthly_path,
                source_id="cdc_seasonality_month_2023",
            ),
            *parse_cdc_lyme_weekly_onset(
                weekly_path,
                source_id="cdc_seasonality_week_2023",
            ),
        ]
    except SeasonalityInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    baseline_rows = build_seasonality_baseline(observations)
    outputs = write_seasonality_outputs(
        observations=observations,
        baseline_rows=baseline_rows,
        output_dir=output_dir,
    )
    typer.echo(
        f"Wrote {len(observations)} seasonality observation row(s) to "
        f"{outputs.observations_path}"
    )
    typer.echo(
        f"Wrote {len(baseline_rows)} seasonality baseline row(s) to "
        f"{outputs.baseline_path}"
    )


@etl_app.command("model-features")
def model_features(
    lyme_outcomes_path: Path = typer.Option(
        Path("build/etl/lyme/lyme_county_year_reconciled.csv"),
        help="Input reconciled Lyme county-year outcome CSV.",
    ),
    population_path: Path = typer.Option(
        Path("build/etl/population/county_population_year.csv"),
        help="Input county-year population CSV.",
    ),
    weather_weekly_path: Path = typer.Option(
        Path("build/etl/noaa-md-1992-2026/weather_features_weekly.csv"),
        help="Input weekly county weather feature CSV.",
    ),
    contact_pressure_path: Path = typer.Option(
        Path("build/etl/contact-pressure/contact_pressure_features_county_year.csv"),
        help="Optional contact pressure county-year feature CSV.",
    ),
    deer_harvest_path: Path = typer.Option(
        Path("build/etl/deer-harvest/maryland_dnr_deer_harvest.csv"),
        help="Optional Maryland deer harvest CSV.",
    ),
    tick_status_path: Path | None = typer.Option(
        None,
        help=(
            "Optional county tick vector/pathogen status feature CSV. Supplying "
            "this opts into current cumulative status as a retrospective proxy."
        ),
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/model"),
        help="Output directory for model-ready feature artifacts.",
    ),
) -> None:
    if not lyme_outcomes_path.exists():
        raise typer.BadParameter(f"Lyme outcomes file not found: {lyme_outcomes_path}")
    if not population_path.exists():
        raise typer.BadParameter(f"Population file not found: {population_path}")
    if not weather_weekly_path.exists():
        raise typer.BadParameter(
            f"Weekly weather features file not found: {weather_weekly_path}"
        )
    if tick_status_path is not None and not tick_status_path.exists():
        raise typer.BadParameter(f"Tick status file not found: {tick_status_path}")

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme_outcomes_path,
        population_path=population_path,
        weather_weekly_path=weather_weekly_path,
        contact_pressure_path=(
            contact_pressure_path if contact_pressure_path.exists() else None
        ),
        deer_harvest_path=deer_harvest_path if deer_harvest_path.exists() else None,
        tick_status_path=tick_status_path,
    )
    output = write_model_feature_matrix_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} model feature row(s) to {output}")


@etl_app.command("model-backtest")
def model_backtest(
    model_features_path: Path = typer.Option(
        Path("build/etl/model/model_features_county_year.csv"),
        help="Input model feature matrix CSV.",
    ),
    start_year: int = typer.Option(
        2007,
        help="First held-out test year to evaluate.",
    ),
    end_year: int | None = typer.Option(
        None,
        help="Last held-out test year to evaluate. Defaults to max year in input.",
    ),
    min_train_years: int = typer.Option(
        5,
        help="Minimum prior county years required for a prediction.",
    ),
    lookback_years: int = typer.Option(
        5,
        help="Maximum number of prior county/state years used by baseline models.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/backtest"),
        help="Output directory for backtest prediction and metric artifacts.",
    ),
) -> None:
    if not model_features_path.exists():
        raise typer.BadParameter(
            f"Model features file not found: {model_features_path}"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if lookback_years < min_train_years:
        raise typer.BadParameter(
            "lookback-years must be greater than or equal to min-train-years"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = run_baseline_backtests(
            model_features_path=model_features_path,
            start_year=start_year,
            end_year=end_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
        )
    except BacktestInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_model_backtest_outputs(result, output_dir)
    typer.echo(f"Wrote 1 backtest run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} backtest prediction row(s) to "
        f"{outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} backtest metric row(s) to "
        f"{outputs.metrics_path}"
    )


@etl_app.command("county-week-risk")
def county_week_risk(
    backtest_predictions_path: Path = typer.Option(
        Path("build/etl/backtest/model_backtest_predictions.csv"),
        help="Input backtest prediction CSV with annual county predictions.",
    ),
    seasonality_baseline_path: Path = typer.Option(
        Path("build/etl/seasonality/seasonality_baseline.csv"),
        help="Input CDC Lyme seasonality baseline CSV.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Annual backtest model branch to convert into weekly risk scores.",
    ),
    seasonality_source_id: str = typer.Option(
        "cdc_seasonality_week_2023",
        help="Seasonality baseline source_id to use for the weekly Lyme curve.",
    ),
    benchmark_quantile: float = typer.Option(
        0.95,
        help="Quantile of generated weekly incidence used as score benchmark.",
    ),
    headroom_multiplier: float = typer.Option(
        1.2,
        help="Multiplier applied to benchmark before mapping onto the 1-10 scale.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/county-week-risk"),
        help="Output directory for county-week risk score artifacts.",
    ),
    append: bool = typer.Option(
        True,
        "--append/--replace",
        help=(
            "Append to existing score artifacts with key-based dedupe, or replace "
            "the output files."
        ),
    ),
) -> None:
    if not backtest_predictions_path.exists():
        raise typer.BadParameter(
            f"Backtest predictions file not found: {backtest_predictions_path}"
        )
    if not seasonality_baseline_path.exists():
        raise typer.BadParameter(
            f"Seasonality baseline file not found: {seasonality_baseline_path}"
        )

    try:
        result = build_seasonal_risk_scores(
            predictions_path=backtest_predictions_path,
            seasonality_baseline_path=seasonality_baseline_path,
            model_name=model_name,
            seasonality_source_id=seasonality_source_id,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
        )
    except RiskScoreInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_seasonal_risk_score_outputs(result, output_dir, append=append)
    typer.echo(
        f"Wrote {len(result.rows)} county-week risk score row(s) to "
        f"{outputs.scores_path}"
    )
    typer.echo(f"Wrote 1 risk score scale row(s) to {outputs.scale_path}")


@etl_app.command("lyme-outcomes")
def lyme_outcomes(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme"),
        help="Raw directory containing CDC Lyme source CSV files.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/lyme"),
        help="Output directory for reconciled Lyme ETL artifacts.",
    ),
) -> None:
    source_files = [
        (
            "cdc_lyme_public_1992_2007.csv",
            "cdc_lyme_public_1992_2007",
            parse_cdc_lyme_public_use,
        ),
        (
            "cdc_lyme_public_2008_2021.csv",
            "cdc_lyme_public_2008_2021",
            parse_cdc_lyme_public_use,
        ),
        (
            "cdc_lyme_public_2022_2023.csv",
            "cdc_lyme_public_2022_2023",
            parse_cdc_lyme_public_use,
        ),
        (
            "cdc_lyme_county_dashboard_2023.csv",
            "cdc_lyme_county_dashboard_2023",
            parse_cdc_county_dashboard,
        ),
        (
            "cdc_lyme_county_geodata_2000_2021.csv",
            "cdc_lyme_county_geodata_2000_2021",
            parse_cdc_lyme_geodata,
        ),
    ]
    for filename, source_id, parser in source_files:
        source_path = raw_dir / filename
        if not source_path.exists():
            raise typer.BadParameter(f"Lyme source file not found: {source_path}")

    rows = []
    for filename, source_id, parser in source_files:
        source_path = raw_dir / filename
        rows.extend(parser(source_path, source_id=source_id))

    output = write_reconciled_lyme_outputs(rows, output_dir)
    with output.open(newline="", encoding="utf-8") as handle:
        row_count = sum(1 for _ in csv.DictReader(handle))
    typer.echo(f"Wrote {row_count} reconciled Lyme county-year outcome row(s) to {output}")


@etl_app.command("mast-acorn")
def mast_acorn(
    raw_dir: Path = typer.Option(
        Path("data/raw/ecology/mast"),
        help="Raw directory containing Maryland DNR mast/acorn PDFs.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/mast"),
        help="Output directory for mast/acorn ETL artifacts.",
    ),
    parser: str = typer.Option(
        "pypdfium",
        help="PDF parser: pypdfium or docling.",
    ),
    manual_observations_path: Path | None = typer.Option(
        None,
        help="Optional manual mast observation CSV.",
    ),
) -> None:
    if parser not in {"pypdfium", "docling"}:
        raise typer.BadParameter("parser must be pypdfium or docling")
    if manual_observations_path is not None and not manual_observations_path.exists():
        raise typer.BadParameter(
            f"manual mast observation file not found: {manual_observations_path}"
        )
    rows = []
    summaries = []
    for source in MARYLAND_DNR_MAST_REPORT_URLS:
        source_file = raw_dir / Path(source.raw_relative_path).name
        if not source_file.exists():
            raise typer.BadParameter(f"mast source file not found: {source_file}")
        source_rows, summary = build_mast_acorn_from_pdf(
            source_file,
            year=source.year,
            source_id=source.source_id,
            source_url=source.url,
            parser=parser,
        )
        rows.extend(source_rows)
        summaries.append(summary)
    rows_output = write_mast_acorn_output(rows, output_dir)
    summary_output = write_mast_acorn_summary_output(summaries, output_dir)
    typer.echo(f"Wrote {len(rows)} mast/acorn row(s) to {rows_output}")
    typer.echo(
        f"Wrote {len(summaries)} mast/acorn extraction summary row(s) "
        f"to {summary_output}"
    )
    if manual_observations_path is not None:
        manual_rows = read_manual_mast_observations(manual_observations_path)
        manual_output = write_manual_mast_observations_output(manual_rows, output_dir)
        typer.echo(
            f"Wrote {len(manual_rows)} manual mast observation row(s) to "
            f"{manual_output}"
        )


@etl_app.command("deer-harvest")
def deer_harvest(
    county_reference_path: Path = typer.Option(
        Path("build/etl/county-reference/county_reference.csv"),
        help="County reference CSV with Census land area.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/deer-harvest"),
        help="Output directory for deer harvest ETL artifacts.",
    ),
    url: list[str] | None = typer.Option(
        None,
        "--url",
        help="Maryland DNR deer harvest source URL. Repeat to override defaults.",
    ),
    include_annual_report_pdfs: bool = typer.Option(
        False,
        help="Include DNR annual report PDFs from the Deer Project archive.",
    ),
    skip_news_html: bool = typer.Option(
        False,
        help="Skip DNR news-page HTML harvest tables.",
    ),
    annual_report_parser: str = typer.Option(
        "pypdfium",
        help="Annual report PDF parser: pypdfium or docling.",
    ),
) -> None:
    if annual_report_parser not in {"pypdfium", "docling"}:
        raise typer.BadParameter("annual-report-parser must be pypdfium or docling")
    county_references = read_county_reference_output(county_reference_path)
    source_urls = url or MARYLAND_DNR_DEER_HARVEST_URLS
    rows = []
    if not skip_news_html:
        for source_url in source_urls:
            html = fetch_maryland_dnr_deer_harvest_html(source_url)
            rows.extend(
                parse_maryland_dnr_deer_harvest_html(
                    html,
                    source_url=source_url,
                    source_id=source_id_from_deer_harvest_url(source_url),
                )
            )
    if include_annual_report_pdfs:
        for source in MARYLAND_DNR_DEER_ANNUAL_REPORT_URLS:
            rows.extend(
                parse_maryland_dnr_deer_harvest_pdf(
                    source.url,
                    source_url=source.url,
                    source_id=source.source_id,
                    parser=annual_report_parser,
                )
            )
    rows = dedupe_deer_harvest_rows(
        attach_deer_harvest_density(rows, county_references)
    )
    output = write_deer_harvest_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} deer harvest row(s) to {output}")


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
