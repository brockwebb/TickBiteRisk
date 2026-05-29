from __future__ import annotations

import csv
import json
import math
import shlex
from dataclasses import asdict
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import typer

from tickbiterisk.dashboard_assets import write_dashboard_assets
from tickbiterisk.etl.acs_exposure import (
    ACS_TABLE_BASED_SUMMARY_FILE_CITATION_URL,
    AcsExposureInputError,
    AcsExposureSourceUrls,
    build_acs_exposure_source_urls,
    build_midatlantic_acs_exposure_from_paths,
    materialize_acs_exposure_sources,
)
from tickbiterisk.etl.acs_exposure_build import write_acs_exposure_output
from tickbiterisk.etl.acquisition_provenance import (
    AcquisitionProvenanceRecord,
    write_acquisition_provenance_manifest,
)
from tickbiterisk.etl.build import write_reconciled_lyme_outputs
from tickbiterisk.etl.building_permits import (
    CENSUS_BPS_CITATION_URL,
    build_census_bps_county_annual_url,
    fetch_census_bps_county_text,
    parse_census_bps_county_text,
    source_id_from_census_bps_year,
)
from tickbiterisk.etl.building_permits_build import write_building_permits_output
from tickbiterisk.etl.census_population import (
    CensusApiResponseError,
    CENSUS_INTERCENSAL_1990_DATASET,
    CENSUS_INTERCENSAL_2000_DATASET,
    build_census_intercensal_1990_population_url,
    build_census_intercensal_2000_population_url,
    build_census_pep_2019_population_url,
    build_census_pep_2023_charv_population_url,
    build_census_pep_2025_county_totals_url,
    fetch_maryland_latest_county_population_estimates,
    fetch_maryland_county_population_estimates,
    get_census_api_key,
    sanitize_census_url,
)
from tickbiterisk.etl.contact_pressure import build_contact_pressure_features
from tickbiterisk.etl.contact_pressure_build import write_contact_pressure_output
from tickbiterisk.etl.county_reference import (
    CENSUS_GAZETTEER_CITATION_URL,
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
    MARYLAND_DNR_DEER_ANNUAL_REPORT_ARCHIVE_URL,
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
    MarylandDnrMastReportSource,
    MARYLAND_DNR_MAST_REPORT_URLS,
)
from tickbiterisk.etl.enviroatlas import (
    EPA_ENVIROATLAS_DATA_DOWNLOAD_URL,
    build_enviroatlas_maryland_habitat_query_url,
    fetch_enviroatlas_json,
    parse_enviroatlas_county_habitat,
)
from tickbiterisk.etl.enviroatlas_build import write_enviroatlas_county_habitat_output
from tickbiterisk.etl.enso import (
    NOAA_CPC_ONI_URL,
    NOAA_PSL_MEI_V2_CITATION_URL,
    NOAA_PSL_MEI_V2_URL,
    MeiV2InputError,
    OniInputError,
    build_mei_v2_model_year_features,
    build_oni_model_year_features,
    fetch_mei_v2_text,
    fetch_oni_text,
    parse_mei_v2_csv_text,
    parse_oni_ascii_text,
)
from tickbiterisk.etl.enso_build import (
    write_mei_v2_model_year_output,
    write_mei_v2_monthly_output,
    write_oni_model_year_output,
    write_oni_season_output,
)
from tickbiterisk.etl.lyme import (
    parse_cdc_county_dashboard,
    parse_cdc_lyme_geodata,
    parse_cdc_lyme_public_use,
    parse_mdh_lyme_pdf,
)
from tickbiterisk.etl.lyme_aggregate import (
    build_aggregate_observations,
    parse_cdc_lyme_aggregate_cases,
    parse_cdc_lyme_aggregate_rates,
)
from tickbiterisk.etl.lyme_aggregate_build import (
    LymeAggregateOutputPaths,
    write_lyme_aggregate_outputs,
)
from tickbiterisk.etl.maine_jmmc_tickborne import (
    MaineJmmcTickborneCountyRate,
    parse_maine_jmmc_tickborne_rates_pdf,
)
from tickbiterisk.etl.maine_jmmc_tickborne_build import (
    write_maine_jmmc_tickborne_rates_output,
)
from tickbiterisk.etl.mass_dph_syndromic_ed import (
    MassDphSyndromicEdCountySummary,
    parse_mass_dph_syndromic_ed_docx,
)
from tickbiterisk.etl.mass_dph_syndromic_ed_build import (
    write_mass_dph_syndromic_ed_output,
)
from tickbiterisk.etl.nj_reportable_tickborne import (
    NewJerseyReportableTickborneCountyYear,
    parse_nj_doh_reportable_tickborne_pdf,
)
from tickbiterisk.etl.nj_reportable_tickborne_build import (
    write_nj_doh_reportable_tickborne_output,
)
from tickbiterisk.etl.regional_lyme import (
    RegionalLymeCountyYear,
    parse_cdc_midatlantic_county_dashboard,
    parse_de_dhss_lyme_county_html,
    parse_pa_doh_lyme_county_workbook,
    parse_va_vdh_reportable_disease_locality_csv,
)
from tickbiterisk.etl.regional_demographics import (
    CENSUS_PEP_AGE_SEX_CITATION_URL,
    build_midatlantic_age_sex_urls,
    fetch_midatlantic_age_sex_demographics,
)
from tickbiterisk.etl.regional_demographics_build import (
    write_regional_age_demographics_output,
)
from tickbiterisk.etl.regional_hotspots import build_midatlantic_hotspot_diagnostics
from tickbiterisk.etl.regional_hotspots_build import write_regional_hotspot_outputs
from tickbiterisk.etl.regional_incidence import build_midatlantic_incidence_panel
from tickbiterisk.etl.regional_incidence_build import write_regional_incidence_outputs
from tickbiterisk.etl.regional_lyme_build import (
    write_regional_lyme_output,
    write_regional_lyme_state_validation_output,
)
from tickbiterisk.etl.regional_population import (
    REGIONAL_POPULATION_PROJECTION_SOURCE_ID,
    build_midatlantic_population_urls,
    build_census_pep_2025_county_totals_url as build_midatlantic_census_pep_2025_county_totals_url,
    fetch_midatlantic_county_population_estimates,
)
from tickbiterisk.etl.regional_population_build import (
    write_regional_county_population_output,
)
from tickbiterisk.etl.regional_signals import build_midatlantic_regional_signals
from tickbiterisk.etl.regional_signals_build import write_regional_signals_output
from tickbiterisk.etl.wv_vectorborne import (
    WestVirginiaVectorborneStateSummary,
    parse_wv_vectorborne_report_pdf,
)
from tickbiterisk.etl.wv_vectorborne_build import write_wv_vectorborne_state_summary
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
    NoaaCountyBackfillResult,
    audit_noaa_station_coverage,
    resolve_maryland_noaa_county_fips,
    run_noaa_county_backfill,
    run_noaa_maryland_backfill,
    validate_noaa_backfill_args,
)
from tickbiterisk.etl.nssp_coverage import (
    CDC_NSSP_ABOUT_URL,
    CDC_NSSP_COVERAGE_CSV_URL,
    NSSP_COVERAGE_AS_OF_DATE,
    NSSP_COVERAGE_SOURCE_ID,
    NsspCoverageInputError,
    build_maryland_nssp_coverage,
    ensure_nssp_coverage_raw,
    parse_nssp_coverage_csv,
)
from tickbiterisk.etl.nssp_coverage_build import write_nssp_coverage_output
from tickbiterisk.etl.open_meteo import (
    build_open_meteo_archive_url,
    fetch_open_meteo_archive,
)
from tickbiterisk.etl.open_meteo_backfill import (
    OpenMeteoArchiveRequestPlan,
    OpenMeteoBackfillError,
    OpenMeteoCountyBackfillResult,
    plan_open_meteo_archive_requests,
    read_open_meteo_weather_daily_rows,
    resolve_maryland_open_meteo_county_fips,
    run_open_meteo_maryland_backfill,
    validate_open_meteo_backfill_args,
)
from tickbiterisk.etl.population_build import write_county_population_output
from tickbiterisk.etl.provenance_audit import (
    audit_provenance_manifests,
    discover_provenance_manifests,
)
from tickbiterisk.etl.raw_download import download_source_files
from tickbiterisk.etl.seasonality import (
    SeasonalityInputError,
    build_seasonality_baseline,
    parse_cdc_lyme_monthly_onset,
    parse_cdc_lyme_weekly_onset,
)
from tickbiterisk.etl.seasonality_build import write_seasonality_outputs
from tickbiterisk.etl.sources import compute_sha256
from tickbiterisk.etl.tick_status import (
    DEFAULT_TICK_STATUS_STATE_FIPS,
    MIDATLANTIC_TICK_STATUS_STATE_FIPS,
    build_tick_status_county_features,
    parse_ixodes_status,
    parse_lone_star_status,
    parse_pathogen_status,
)
from tickbiterisk.etl.tick_status_build import (
    TickStatusOutputPaths,
    write_tick_status_outputs,
)
from tickbiterisk.etl.usdm_drought import (
    USDM_DATA_DOWNLOAD_URL,
    build_usdm_drought_urls,
    build_usdm_county_year_features,
    fetch_usdm_drought_year,
    fetch_usdm_text,
)
from tickbiterisk.etl.usdm_drought_build import (
    write_usdm_county_year_output,
    write_usdm_weekly_output,
)
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
from tickbiterisk.modeling.annual_forecast import (
    AnnualForecastInputError,
    build_annual_forecast,
)
from tickbiterisk.modeling.annual_forecast_build import (
    write_annual_forecast_outputs,
)
from tickbiterisk.modeling.design_matrix import (
    ModelDesignMatrixInputError,
    build_model_design_matrix,
)
from tickbiterisk.modeling.design_matrix_build import write_model_design_matrix_outputs
from tickbiterisk.modeling.forecast_calibration_backtest import (
    ForecastCalibrationBacktestInputError,
    build_forecast_calibration_backtest,
)
from tickbiterisk.modeling.forecast_calibration_backtest_build import (
    write_forecast_calibration_backtest_outputs,
)
from tickbiterisk.modeling.forecast_bayesian_update_backtest import (
    ForecastBayesianUpdateBacktestInputError,
    build_forecast_bayesian_update_backtest,
)
from tickbiterisk.modeling.forecast_bayesian_update_backtest_build import (
    write_forecast_bayesian_update_backtest_outputs,
)
from tickbiterisk.modeling.model_compare import (
    ModelComparisonInputError,
    RANDOM_FOREST_MAX_FEATURES,
    RANDOM_FOREST_MIN_SAMPLES_LEAF,
    RANDOM_FOREST_N_ESTIMATORS,
    RANDOM_FOREST_RANDOM_STATE,
    run_model_comparison,
)
from tickbiterisk.modeling.model_compare_build import write_model_comparison_outputs
from tickbiterisk.modeling.model_diagnostics import (
    ModelDiagnosticsInputError,
    build_model_diagnostics,
)
from tickbiterisk.modeling.model_diagnostics_build import (
    write_model_diagnostics_outputs,
)
from tickbiterisk.modeling.regional_annual_forecast import (
    RegionalAnnualForecastInputError,
    build_regional_annual_forecast,
)
from tickbiterisk.modeling.regional_annual_forecast_build import (
    write_regional_annual_forecast_outputs,
)
from tickbiterisk.modeling.regional_forecast_capacity import (
    RegionalForecastCapacityInputError,
    build_regional_forecast_capacity,
)
from tickbiterisk.modeling.regional_forecast_capacity_build import (
    write_regional_forecast_capacity_outputs,
)
from tickbiterisk.modeling.regional_outcome_stress import (
    RegionalOutcomeStressInputError,
    build_regional_outcome_stress,
)
from tickbiterisk.modeling.regional_outcome_stress_build import (
    write_regional_outcome_stress_outputs,
)
from tickbiterisk.modeling.regional_incidence_stress import (
    RANDOM_FOREST_MAX_FEATURES as REGIONAL_RF_MAX_FEATURES,
    RANDOM_FOREST_MIN_SAMPLES_LEAF as REGIONAL_RF_MIN_SAMPLES_LEAF,
    RANDOM_FOREST_N_ESTIMATORS as REGIONAL_RF_N_ESTIMATORS,
    RANDOM_FOREST_RANDOM_STATE as REGIONAL_RF_RANDOM_STATE,
    RegionalIncidenceStressInputError,
    build_regional_incidence_stress,
)
from tickbiterisk.modeling.regional_incidence_stress_build import (
    write_regional_incidence_stress_outputs,
)
from tickbiterisk.modeling.regional_incidence_clusters import (
    RegionalIncidenceClusterInputError,
    build_regional_incidence_clusters,
)
from tickbiterisk.modeling.regional_incidence_clusters_build import (
    write_regional_incidence_cluster_outputs,
)
from tickbiterisk.modeling.spatial_neighbors import (
    build_county_adjacency_from_geojson,
    write_county_adjacency_output,
)
from tickbiterisk.modeling.risk_score import (
    RiskScoreInputError,
    build_seasonal_risk_scores,
)
from tickbiterisk.modeling.risk_score_build import write_seasonal_risk_score_outputs
from tickbiterisk.runtime.risk_lookup import (
    RiskLookupInputError,
    RiskLookupStore,
)
from tickbiterisk.runtime.single_bite import (
    SingleBiteRiskInputError,
    estimate_single_bite_risk,
)
from tickbiterisk.runtime.static_export import (
    StaticExportInputError,
    export_static_risk_data,
)

app = typer.Typer(help="TickBiteRisk ETL utilities")
etl_app = typer.Typer(help="ETL commands")
risk_app = typer.Typer(help="Runtime risk lookup commands")
dashboard_app = typer.Typer(help="Static dashboard asset commands")
app.add_typer(etl_app, name="etl")
app.add_typer(risk_app, name="risk")
app.add_typer(dashboard_app, name="dashboard")

FORECAST_UPDATE_MODE_CHOICES = ("pre_update", "post_observed_outcome")


def _validate_forecast_update_mode(update_mode: str) -> None:
    if update_mode not in FORECAST_UPDATE_MODE_CHOICES:
        allowed = ", ".join(FORECAST_UPDATE_MODE_CHOICES)
        raise typer.BadParameter(f"update-mode must be one of: {allowed}")


OPEN_METEO_HISTORICAL_WEATHER_CITATION_URL = (
    "https://open-meteo.com/en/docs/historical-weather-api"
)
NOAA_CDO_WEBSERVICES_CITATION_URL = (
    "https://www.ncei.noaa.gov/cdo-web/webservices/v2"
)
CDC_LYME_SURVEILLANCE_CITATION_URL = (
    "https://www.cdc.gov/lyme/data-research/facts-stats/index.html"
)
CDC_TICK_SURVEILLANCE_DATASETS_URL = (
    "https://www.cdc.gov/ticks/data-research/facts-stats/"
    "tick-surveillance-data-sets.html"
)
CDC_LONE_STAR_SURVEILLANCE_URL = (
    "https://www.cdc.gov/ticks/data-research/facts-stats/"
    "lone-star-tick-surveillance.html"
)
CDC_IXODES_COUNTY_STATUS_2026_XLSX_URL = (
    "https://www.cdc.gov/ticks/media/files/2026/04/"
    "Public_Use_Ixodes_County_Table_2026_03252026.xlsx"
)
CDC_IXODES_PATHOGEN_STATUS_2026_XLSX_URL = (
    "https://www.cdc.gov/ticks/media/files/2026/04/"
    "Public_Use_Ixodes_Pathogens_County_Table_2026_04292026.xlsx"
)
CDC_LONE_STAR_STATUS_2025_XLSX_URL = (
    "https://www.cdc.gov/ticks/media/files/2026/05/"
    "2025-lone-star-tick-surveillance-map-data.xlsx"
)
MDH_LYME_2013_2024_PDF_URL = (
    "https://health.maryland.gov/phpa/OIDEOR/CZVBD/Shared%20Documents/"
    "Lyme%20Disease%20Data%202013%20to%202024.pdf"
)
LYME_OUTCOME_SOURCE_METADATA = [
    {
        "filename": "cdc_lyme_public_1992_2007.csv",
        "source_id": "cdc_lyme_public_1992_2007",
        "source_name": "CDC Lyme public-use aggregated geography, 1992-2007",
        "source_url": (
            "https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-"
            "Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/"
            "84rx-ksgd/about_data"
        ),
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_public_use",
        "modeling_caveats": (
            "Early CDC public-use Lyme surveillance rows include suppression "
            "and should be reconciled with later source-vintage changes."
        ),
    },
    {
        "filename": "cdc_lyme_public_2008_2021.csv",
        "source_id": "cdc_lyme_public_2008_2021",
        "source_name": "CDC Lyme public-use aggregated geography, 2008-2021",
        "source_url": (
            "https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-"
            "Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/"
            "qtbi-xd4i/about_data"
        ),
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_public_use",
        "modeling_caveats": (
            "CDC public-use Lyme surveillance rows include suppression and "
            "source-vintage changes; treat as observed reported incidence."
        ),
    },
    {
        "filename": "cdc_lyme_public_2022_2023.csv",
        "source_id": "cdc_lyme_public_2022_2023",
        "source_name": "CDC Lyme public-use aggregated geography, 2022-2023",
        "source_url": (
            "https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-"
            "Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/"
            "4zup-3pz4/about_data"
        ),
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_public_use",
        "modeling_caveats": (
            "CDC Lyme case definition changed for 2022 and later; models "
            "should treat the surveillance regime break explicitly."
        ),
    },
    {
        "filename": "cdc_lyme_county_dashboard_2023.csv",
        "source_id": "cdc_lyme_county_dashboard_2023",
        "source_name": "CDC Lyme county counts dashboard export, 2023",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_county_dashboard",
        "modeling_caveats": (
            "CDC dashboard export is reconciliation context; CDC public-use "
            "rows remain canonical when overlapping source vintages agree."
        ),
    },
    {
        "filename": "cdc_lyme_county_geodata_2000_2021.csv",
        "source_id": "cdc_lyme_county_geodata_2000_2021",
        "source_name": "CDC Lyme county geodata, 2000-2021",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_geodata",
        "modeling_caveats": (
            "CDC geodata is reconciliation and geography context; use public "
            "CDC county-year outcomes as the canonical target where available."
        ),
    },
]
LYME_MDH_SOURCE_METADATA = {
    "filename": "mdh_lyme_2013_2024.pdf",
    "source_id": "mdh_lyme_2013_2024_pdf",
    "source_name": "Maryland MDH Lyme Disease Data 2013 to 2024 PDF",
    "source_url": MDH_LYME_2013_2024_PDF_URL,
    "citation_url": MDH_LYME_2013_2024_PDF_URL,
    "parser_method": "parse_mdh_lyme_pdf",
    "modeling_caveats": (
        "MDH 2024 is a latest state/probable-only outcome lane; CDC remains "
        "canonical for overlapping 2013-2023 rows."
    ),
}
SEASONALITY_SOURCE_METADATA = [
    {
        "filename": "cdc_lyme_monthly_onset_2010_2023.csv",
        "source_id": "cdc_seasonality_month_2023",
        "source_name": "CDC Lyme cases by month of disease onset",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_monthly_onset",
        "grain": "month",
    },
    {
        "filename": "cdc_lyme_weekly_onset_2010_2023.csv",
        "source_id": "cdc_seasonality_week_2023",
        "source_name": "CDC Lyme cases by MMWR week of disease onset",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_weekly_onset",
        "grain": "mmwr_week",
    },
]
TICK_STATUS_SOURCE_METADATA = [
    {
        "filename": "cdc_ixodes_county_status_2026.xlsx",
        "source_id": "cdc_ixodes_county_status_2026",
        "source_name": "CDC ArboNET Ixodes county status workbook through 2025",
        "source_url": CDC_IXODES_COUNTY_STATUS_2026_XLSX_URL,
        "citation_url": CDC_TICK_SURVEILLANCE_DATASETS_URL,
        "parser_method": "parse_ixodes_status",
        "output_kind": "vector",
        "fallbacks": [
            {
                "filename": "cdc_ixodes_county_status_2025.xlsx",
                "source_id": "cdc_ixodes_county_status_2025",
                "source_name": "CDC ArboNET Ixodes county status workbook through 2025",
                "source_url": CDC_IXODES_COUNTY_STATUS_2026_XLSX_URL,
                "citation_url": CDC_TICK_SURVEILLANCE_DATASETS_URL,
                "parser_method": "parse_ixodes_status",
                "output_kind": "vector",
            }
        ],
    },
    {
        "filename": "cdc_ixodes_pathogen_status_2026.xlsx",
        "source_id": "cdc_ixodes_pathogen_status_2026",
        "source_name": "CDC ArboNET Ixodes pathogen status workbook through 2025",
        "source_url": CDC_IXODES_PATHOGEN_STATUS_2026_XLSX_URL,
        "citation_url": CDC_TICK_SURVEILLANCE_DATASETS_URL,
        "parser_method": "parse_pathogen_status",
        "output_kind": "pathogen",
        "fallbacks": [
            {
                "filename": "cdc_ixodes_pathogen_status_2025.xlsx",
                "source_id": "cdc_ixodes_pathogen_status_2025",
                "source_name": "CDC ArboNET Ixodes pathogen status workbook through 2025",
                "source_url": CDC_IXODES_PATHOGEN_STATUS_2026_XLSX_URL,
                "citation_url": CDC_TICK_SURVEILLANCE_DATASETS_URL,
                "parser_method": "parse_pathogen_status",
                "output_kind": "pathogen",
            }
        ],
    },
    {
        "filename": "cdc_lone_star_status_2025.xlsx",
        "source_id": "cdc_lone_star_status_2025",
        "source_name": "CDC Amblyomma americanum county status workbook through 2025",
        "source_url": CDC_LONE_STAR_STATUS_2025_XLSX_URL,
        "citation_url": CDC_LONE_STAR_SURVEILLANCE_URL,
        "parser_method": "parse_lone_star_status",
        "output_kind": "lone_star",
        "fallbacks": [
            {
                "filename": "cdc_lone_star_status_2024.xlsx",
                "source_id": "cdc_lone_star_status_2024",
                "source_name": "CDC Amblyomma americanum county status workbook through 2024",
                "source_url": CDC_LONE_STAR_SURVEILLANCE_URL,
                "citation_url": CDC_LONE_STAR_SURVEILLANCE_URL,
                "parser_method": "parse_lone_star_status",
                "output_kind": "lone_star",
            }
        ],
    },
]
LYME_AGGREGATE_SOURCE_METADATA = [
    {
        "filename": "state_caseincid_cases.csv",
        "source_id": "cdc_caseincid_cases_state_2023",
        "source_name": "CDC Lyme cases by state/locality dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_cases",
        "geography_type": "state",
        "value_type": "cases",
        "output_kind": "state",
    },
    {
        "filename": "state_caseincid_rates.csv",
        "source_id": "cdc_caseincid_rates_state_2023",
        "source_name": "CDC Lyme rates by state/locality dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_rates",
        "geography_type": "state",
        "value_type": "rates",
        "output_kind": "state",
    },
    {
        "filename": "region_caseincid_cases.csv",
        "source_id": "cdc_caseincid_cases_region_2023",
        "source_name": "CDC Lyme cases by year and region dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_cases",
        "geography_type": "region",
        "value_type": "cases",
        "output_kind": "region",
    },
    {
        "filename": "region_caseincid_rates.csv",
        "source_id": "cdc_caseincid_rates_region_2023",
        "source_name": "CDC Lyme rates by year and region dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_rates",
        "geography_type": "region",
        "value_type": "rates",
        "output_kind": "region",
    },
    {
        "filename": "national_caseincid_cases.csv",
        "source_id": "cdc_caseincid_overall_cases_2023",
        "source_name": "CDC overall Lyme cases by year dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_cases",
        "geography_type": "national",
        "value_type": "cases",
        "output_kind": "national",
    },
    {
        "filename": "national_caseincid_rates.csv",
        "source_id": "cdc_caseincid_overall_rate_2023",
        "source_name": "CDC overall Lyme incidence by year dashboard export",
        "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
        "parser_method": "parse_cdc_lyme_aggregate_rates",
        "geography_type": "national",
        "value_type": "rates",
        "output_kind": "national",
    },
]
REGIONAL_LYME_SOURCE_METADATA = {
    "filename": "cdc_lyme_county_dashboard_2023.csv",
    "source_id": "cdc_lyme_county_dashboard_2023",
    "source_name": "CDC Lyme county counts dashboard export, 2023",
    "source_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
    "citation_url": CDC_LYME_SURVEILLANCE_CITATION_URL,
    "parser_method": "parse_cdc_midatlantic_county_dashboard",
    "modeling_caveats": (
        "Mid-Atlantic regional expansion/stress-test panel only; not the "
        "public Maryland default, not a direct exposure observation, and "
        "reported cases are not stable true incidence across surveillance "
        "regime changes."
    ),
}
REGIONAL_PA_LYME_2024_SOURCE_METADATA = {
    "filename": "pennsylvania_doh_official_lyme_by_report_2024_with_map.xlsx",
    "source_id": "pa_doh_lyme_1980_2024_xlsx",
    "source_name": "Pennsylvania DOH Lyme disease county case workbook through 2024",
    "source_url": (
        "https://www.pa.gov/content/dam/copapwp-pagov/en/health/documents/"
        "topics/documents/diseases-and-conditions/vectorborne/"
        "OfficialLymeByReport2024withMap.xlsx"
    ),
    "citation_url": (
        "https://www.pa.gov/agencies/health/diseases-conditions/"
        "infectious-disease/vectorborne-diseases/tick-diseases.html"
    ),
    "parser_method": "parse_pa_doh_lyme_county_workbook:target_year=2024",
    "modeling_caveats": (
        "Pennsylvania state 2024 overlay for regional expansion/stress-test "
        "panel only; state-source rows are not the public Maryland default, "
        "suppressed county counts are represented as zero with flags, and "
        "reported cases are not stable true incidence."
    ),
}
REGIONAL_DE_LYME_SOURCE_METADATA = {
    "filename": "delaware_dhss_lyme_data_2019_2023.html",
    "source_id": "delaware_dhss_lyme_table",
    "source_name": "Delaware DHSS Lyme disease county case table, 2019-2023",
    "source_url": "https://dhss.delaware.gov/dph/epi/tick-lyme-data/",
    "citation_url": "https://dhss.delaware.gov/dph/epi/tick-lyme-data/",
    "parser_method": "parse_de_dhss_lyme_county_html",
    "modeling_caveats": (
        "Delaware state-source validation sidecar only; rows overlap CDC "
        "regional years and are not appended to the model input panel, not "
        "the public Maryland default, and reported cases are not stable true "
        "incidence."
    ),
}
REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA = {
    "filename": "virginia_vdh_reportable_disease_geography_2024.csv",
    "source_id": "virginia_vdh_reportable_disease_locality_2024_csv",
    "source_name": "Virginia VDH reportable disease surveillance locality CSV, 2024",
    "source_url": (
        "https://data.virginia.gov/datastore/dump/"
        "5b1fc1e7-3ef9-42cd-8dd1-6c3d4ef4da79?bom=True"
    ),
    "citation_url": "https://www.vdh.virginia.gov/surveillance-and-investigation/annual-report/",
    "parser_method": "parse_va_vdh_reportable_disease_locality_csv:target_year=2024",
    "modeling_caveats": (
        "Virginia VDH state 2024 locality overlay for regional expansion/"
        "stress-test panel only; Virginia localities include counties and "
        "independent cities, rows are not the public Maryland default, and "
        "reported cases are not stable true incidence."
    ),
}
WV_VECTORBORNE_SOURCE_METADATA = [
    {
        "filename": "west_virginia_oeps_vectorborne_2024.pdf",
        "source_id": "west_virginia_oeps_vectorborne_2024_pdf",
        "source_name": "West Virginia OEPS vectorborne disease summary, 2024",
        "source_url": "https://oeps.wv.gov/media/20/download?inline",
        "citation_url": "https://oeps.wv.gov/arboviral-diseases",
        "parser_method": "parse_wv_vectorborne_report_pdf:pypdfium_text_table3",
        "report_year": "2024",
    },
    {
        "filename": "west_virginia_oeps_vectorborne_2025.pdf",
        "source_id": "west_virginia_oeps_vectorborne_2025_pdf",
        "source_name": "West Virginia OEPS vectorborne disease summary, 2025",
        "source_url": "https://oeps.wv.gov/media/21/download?inline",
        "citation_url": "https://oeps.wv.gov/arboviral-diseases",
        "parser_method": "parse_wv_vectorborne_report_pdf:pypdfium_text_table3",
        "report_year": "2025",
    },
]
MASS_DPH_SYNDROMIC_ED_SOURCE_METADATA = [
    {
        "filename": "mass_dph_tickborne_syndromic_2024_jan_dec.docx",
        "source_id": "mass_dph_tickborne_syndromic_2024_jan_dec_docx",
        "source_name": (
            "Massachusetts DPH Tick Exposure and Tickborne Disease "
            "Syndromic Surveillance Report, January-December 2024"
        ),
        "source_url": (
            "https://www.mass.gov/doc/"
            "tick-exposure-and-tickborne-disease-syndromic-surveillance-report-"
            "january-december-2024/download"
        ),
        "citation_url": "https://www.mass.gov/lists/monthly-tick-borne-disease-reports",
        "parser_method": "parse_mass_dph_syndromic_ed_docx:DOCX Table 1",
        "report_year": "2024",
        "report_period_label": "January-December 2024",
        "report_period_start": "2024-01-01",
        "report_period_end": "2024-12-31",
    },
    {
        "filename": "mass_dph_tickborne_syndromic_2025_jan_dec.docx",
        "source_id": "mass_dph_tickborne_syndromic_2025_jan_dec_docx",
        "source_name": (
            "Massachusetts DPH Tick Exposure and Tickborne Disease "
            "Syndromic Surveillance Report, January-December 2025"
        ),
        "source_url": (
            "https://www.mass.gov/doc/"
            "tick-exposure-and-tickborne-disease-syndromic-surveillance-report-"
            "january-december-2025/download"
        ),
        "citation_url": "https://www.mass.gov/lists/monthly-tick-borne-disease-reports",
        "parser_method": "parse_mass_dph_syndromic_ed_docx:DOCX Table 1",
        "report_year": "2025",
        "report_period_label": "January-December 2025",
        "report_period_start": "2025-01-01",
        "report_period_end": "2025-12-31",
    },
    {
        "filename": "mass_dph_tickborne_syndromic_2026_april.docx",
        "source_id": "mass_dph_tickborne_syndromic_2026_april_docx",
        "source_name": (
            "Massachusetts DPH Tick Exposure and Tickborne Disease "
            "Syndromic Surveillance Report, April 2026"
        ),
        "source_url": (
            "https://www.mass.gov/doc/"
            "tick-exposure-and-tickborne-disease-syndromic-surveillance-report-"
            "april-2026/download"
        ),
        "citation_url": "https://www.mass.gov/lists/monthly-tick-borne-disease-reports",
        "parser_method": "parse_mass_dph_syndromic_ed_docx:DOCX Table 1",
        "report_year": "2026",
        "report_period_label": "April 2026",
        "report_period_start": "2026-01-01",
        "report_period_end": "2026-04-30",
    },
]
NJ_DOH_REPORTABLE_TICKBORNE_METADATA = {
    "filename": "new_jersey_doh_reportable_disease_statistics_2024.pdf",
    "technical_notes_filename": (
        "new_jersey_doh_reportable_disease_technical_notes_2024.pdf"
    ),
    "source_id": "nj_doh_reportable_tickborne_2024_pdf",
    "source_name": "New Jersey DOH 2024 reportable disease statistics, tickborne rows",
    "source_url": (
        "https://www.nj.gov/health/cd/documents/reportable_disease/"
        "web_statistics_2024.pdf"
    ),
    "technical_notes_url": (
        "https://www.nj.gov/health/cd/documents/reportable_disease/"
        "technical_notes_2024.pdf"
    ),
    "citation_url": "https://www.nj.gov/health/cd/statistics/reportable-disease-stats/",
    "parser_method": "parse_nj_doh_reportable_tickborne_pdf:pypdfium_text_reportable_rows",
}
MAINE_JMMC_TICKBORNE_RATES_METADATA = {
    "filename": "jmmc_maine_tickborne_trends_2001_2024.pdf",
    "source_id": "maine_jmmc_2024_county_rates_pdf",
    "source_name": "Maine JMMC tickborne disease trends county rates, 2024",
    "source_url": (
        "https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi"
        "?article=1219&context=jmmc"
    ),
    "citation_url": "https://knowledgeconnection.mainehealth.org/jmmc/vol7/iss2/10/",
    "doi_url": "https://doi.org/10.46804/2641-2225.1219",
    "underlying_data_url": "https://data.mainepublichealth.gov/tracking/tickborne",
    "parser_method": "parse_maine_jmmc_tickborne_rates_pdf:pypdfium_text_table2_rates",
}


@etl_app.command("check")
def etl_check(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    )
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"ETL output directory ready: {output_dir}")


@etl_app.command("provenance-audit")
def etl_provenance_audit(
    root_dir: Path = typer.Option(
        Path("build/etl"),
        help="Root directory to scan for acquisition provenance manifests.",
    ),
    manifest_paths: list[Path] | None = typer.Option(
        None,
        "--manifest-path",
        help="Specific acquisition_provenance.csv or source_manifest.csv to audit.",
    ),
) -> None:
    paths = manifest_paths or discover_provenance_manifests(root_dir)
    if not paths:
        typer.echo(f"No provenance manifests found under {root_dir}.")
        raise typer.Exit(1)
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        for path in missing_paths:
            typer.echo(f"Provenance manifest not found: {path}")
        raise typer.Exit(1)

    result = audit_provenance_manifests(paths)
    summary = (
        f"Audited {result.manifest_count} provenance manifest(s), "
        f"{result.row_count} row(s), {result.issue_count} issue(s)."
    )
    if result.issue_count:
        typer.echo(f"Provenance audit found {result.issue_count} issue(s).")
        for issue in result.issues:
            typer.echo(issue.format())
        raise typer.Exit(1)
    typer.echo(summary)


@risk_app.command("lookup")
def risk_lookup(
    county_fips: str = typer.Option(
        ...,
        help="Five-digit Maryland county FIPS code.",
    ),
    lookup_date: str = typer.Option(
        date.today().isoformat(),
        "--date",
        help="Calendar date to convert to MMWR week.",
    ),
    scores_path: Path = typer.Option(
        Path("build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv"),
        help="County-week seasonal risk forecast CSV.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Risk score model branch to query.",
    ),
    seasonality_source_id: str = typer.Option(
        "cdc_seasonality_week_2023",
        help="Weekly seasonality source_id to query.",
    ),
    benchmark_quantile: float | None = typer.Option(
        None,
        help="Optional score-scale benchmark quantile selector.",
    ),
    headroom_multiplier: float | None = typer.Option(
        None,
        help="Optional score-scale headroom multiplier selector.",
    ),
    score_denominator: float | None = typer.Option(
        None,
        help="Optional score-scale denominator selector.",
    ),
    source_prediction_run_id: str | None = typer.Option(
        None,
        help="Optional source prediction run selector.",
    ),
    source_prediction_sha256: str | None = typer.Option(
        None,
        help="Optional source prediction SHA-256 selector.",
    ),
    source_seasonality_sha256: str | None = typer.Option(
        None,
        help="Optional source seasonality SHA-256 selector.",
    ),
    pretty: bool = typer.Option(
        False,
        help="Pretty-print JSON output.",
    ),
) -> None:
    if not scores_path.exists():
        raise typer.BadParameter(f"Risk score file not found: {scores_path}")
    try:
        store = RiskLookupStore.from_csv(scores_path)
        response = store.lookup(
            county_fips=county_fips,
            query_date=lookup_date,
            model_name=model_name,
            seasonality_source_id=seasonality_source_id,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
            score_denominator=score_denominator,
            source_prediction_run_id=source_prediction_run_id,
            source_prediction_sha256=source_prediction_sha256,
            source_seasonality_sha256=source_seasonality_sha256,
        )
    except RiskLookupInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(asdict(response), indent=2 if pretty else None))


@risk_app.command("single-bite")
def risk_single_bite(
    county_fips: str = typer.Option(
        ...,
        help="Five-digit Maryland county FIPS code.",
    ),
    lookup_date: str = typer.Option(
        date.today().isoformat(),
        "--date",
        help="Calendar date to convert to MMWR week.",
    ),
    scores_path: Path = typer.Option(
        Path("build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv"),
        help="County-week seasonal risk forecast CSV.",
    ),
    tick_species: str = typer.Option(
        ...,
        help="Tick identity, such as blacklegged, ixodes_scapularis, unknown, or not_ixodes.",
    ),
    tick_stage: str = typer.Option(
        "unknown",
        help="Tick life stage: nymph, adult, larva, or unknown.",
    ),
    attachment_hours: float | None = typer.Option(
        None,
        help="Estimated attachment duration in hours.",
    ),
    engorgement: str = typer.Option(
        "unknown",
        help="Observed engorgement: flat, slightly_engorged, engorged, or unknown.",
    ),
    hours_since_removal: float | None = typer.Option(
        None,
        help="Hours since the tick was removed.",
    ),
    doxycycline_safe: bool | None = typer.Option(
        None,
        "--doxycycline-safe/--doxycycline-unsafe",
        help="Whether doxycycline is known to be safe for the person; omit if unknown.",
    ),
    tick_count: int = typer.Option(
        1,
        help="Number of attached ticks represented by this estimate.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Risk score model branch to query for the county-week forecast.",
    ),
    seasonality_source_id: str = typer.Option(
        "cdc_seasonality_week_2023",
        help="Weekly seasonality source_id to query.",
    ),
    pretty: bool = typer.Option(
        False,
        help="Pretty-print JSON output.",
    ),
) -> None:
    if not scores_path.exists():
        raise typer.BadParameter(f"Risk score file not found: {scores_path}")
    try:
        store = RiskLookupStore.from_csv(scores_path)
        baseline = store.lookup(
            county_fips=county_fips,
            query_date=lookup_date,
            model_name=model_name,
            seasonality_source_id=seasonality_source_id,
        )
        response = estimate_single_bite_risk(
            baseline=baseline,
            tick_species=tick_species,
            tick_stage=tick_stage,
            attachment_hours=attachment_hours,
            engorgement=engorgement,
            hours_since_removal=hours_since_removal,
            doxycycline_safe=doxycycline_safe,
            tick_count=tick_count,
        )
    except (RiskLookupInputError, SingleBiteRiskInputError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(asdict(response), indent=2 if pretty else None))


@risk_app.command("export-static")
def risk_export_static(
    scores_path: Path = typer.Option(
        Path("build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv"),
        help="County-week seasonal risk forecast CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("public/data"),
        help="Output directory for public static JSON artifacts.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Risk score model branch to export.",
    ),
    seasonality_source_id: str = typer.Option(
        "cdc_seasonality_week_2023",
        help="Weekly seasonality source_id to export.",
    ),
    benchmark_quantile: float | None = typer.Option(
        None,
        help="Optional score-scale benchmark quantile selector.",
    ),
    headroom_multiplier: float | None = typer.Option(
        None,
        help="Optional score-scale headroom multiplier selector.",
    ),
    score_denominator: float | None = typer.Option(
        None,
        help="Optional score-scale denominator selector.",
    ),
    source_prediction_run_id: str | None = typer.Option(
        None,
        help="Optional source prediction run selector.",
    ),
    source_prediction_sha256: str | None = typer.Option(
        None,
        help="Optional source prediction SHA-256 selector.",
    ),
    source_seasonality_sha256: str | None = typer.Option(
        None,
        help="Optional source seasonality SHA-256 selector.",
    ),
    model_summary_path: Path | None = typer.Option(
        None,
        help="Optional model comparison summary CSV for public validation metrics.",
    ),
) -> None:
    if not scores_path.exists():
        raise typer.BadParameter(f"Risk score file not found: {scores_path}")
    if model_summary_path is not None and not model_summary_path.exists():
        raise typer.BadParameter(
            f"Model comparison summary file not found: {model_summary_path}"
        )
    try:
        outputs = export_static_risk_data(
            scores_path=scores_path,
            output_dir=output_dir,
            model_name=model_name,
            seasonality_source_id=seasonality_source_id,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
            score_denominator=score_denominator,
            source_prediction_run_id=source_prediction_run_id,
            source_prediction_sha256=source_prediction_sha256,
            source_seasonality_sha256=source_seasonality_sha256,
            model_summary_path=model_summary_path,
        )
    except StaticExportInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Wrote static public risk export to {output_dir}")
    typer.echo(f"Wrote {outputs.weekly_risk_path}")
    typer.echo(f"Wrote {outputs.county_metadata_path}")
    typer.echo(f"Wrote {outputs.model_card_path}")
    typer.echo(f"Wrote {outputs.source_catalog_path}")
    typer.echo(f"Wrote {outputs.export_manifest_path}")


def _fixture_maryland_geojson() -> dict[str, object]:
    features = []
    for index in range(24):
        county_fips = f"24{index + 1:03d}"
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "GEOID": county_fips,
                    "NAME": f"Fixture County {index + 1}",
                    "STATE": "24",
                    "COUNTY": f"{index + 1:03d}",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-77.0 + index * 0.01, 39.0],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@dashboard_app.command("build-assets")
def dashboard_build_assets(
    scores_path: Path = typer.Option(
        Path("build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv"),
        help="County-week seasonal risk forecast CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("public/data"),
        help="Output directory for dashboard static data assets.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Risk score model branch to export.",
    ),
    seasonality_source_id: str = typer.Option(
        "cdc_seasonality_week_2023",
        help="Weekly seasonality source_id to export.",
    ),
    benchmark_quantile: float | None = typer.Option(
        None,
        help="Optional score-scale benchmark quantile selector.",
    ),
    headroom_multiplier: float | None = typer.Option(
        None,
        help="Optional score-scale headroom multiplier selector.",
    ),
    score_denominator: float | None = typer.Option(
        None,
        help="Optional score-scale denominator selector.",
    ),
    source_prediction_run_id: str | None = typer.Option(
        None,
        help="Optional source prediction run selector.",
    ),
    source_prediction_sha256: str | None = typer.Option(
        None,
        help="Optional source prediction SHA-256 selector.",
    ),
    source_seasonality_sha256: str | None = typer.Option(
        None,
        help="Optional source seasonality SHA-256 selector.",
    ),
    model_summary_path: Path | None = typer.Option(
        None,
        help="Optional model comparison summary CSV for public validation metrics.",
    ),
    use_fixture_geometry: bool = typer.Option(
        False,
        help="Use generated fixture geometry instead of Census TIGERweb.",
    ),
) -> None:
    if not scores_path.exists():
        raise typer.BadParameter(f"Risk score file not found: {scores_path}")
    if model_summary_path is not None and not model_summary_path.exists():
        raise typer.BadParameter(
            f"Model comparison summary file not found: {model_summary_path}"
        )
    fetcher = _fixture_maryland_geojson if use_fixture_geometry else None
    try:
        outputs = write_dashboard_assets(
            scores_path=scores_path,
            output_dir=output_dir,
            model_name=model_name,
            seasonality_source_id=seasonality_source_id,
            benchmark_quantile=benchmark_quantile,
            headroom_multiplier=headroom_multiplier,
            score_denominator=score_denominator,
            source_prediction_run_id=source_prediction_run_id,
            source_prediction_sha256=source_prediction_sha256,
            source_seasonality_sha256=source_seasonality_sha256,
            model_summary_path=model_summary_path,
            fetch_geojson=fetcher,
        )
    except StaticExportInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Wrote dashboard assets to {output_dir}")
    typer.echo(f"Wrote {outputs.weekly_risk_path}")
    typer.echo(f"Wrote {outputs.county_geojson_path}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for static Census CSV acquisition provenance.",
    ),
) -> None:
    text = fetch_census_gazetteer_counties_text()
    rows = parse_census_gazetteer_counties(
        text,
        source_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
    )
    output = write_county_reference_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            AcquisitionProvenanceRecord(
                source_id="census_county_reference_2024",
                source_name="U.S. Census Gazetteer county reference file",
                source_url=CENSUS_GAZETTEER_COUNTIES_2024_URL,
                citation_url=CENSUS_GAZETTEER_CITATION_URL,
                acquisition_command=_format_cli_command(
                    [
                        "tickbiterisk",
                        "etl",
                        "county-reference",
                        "--output-dir",
                        str(output_dir),
                        "--provenance-manifest-path",
                        str(resolved_manifest_path),
                    ]
                ),
                acquisition_procedure=(
                    "Fetch the Census Gazetteer national counties ZIP and "
                    "extract the county TXT table for Maryland reference rows."
                ),
                request_method="GET",
                request_description="Census Gazetteer 2024 national counties ZIP request.",
                derived_artifact_paths=[output],
                row_count=len(rows),
                parser_method="parse_census_gazetteer_counties",
                extraction_quality="accepted",
                access_notes="Public Census static ZIP; no API key required.",
                modeling_caveats=(
                    "County geography and area denominator reference only; not "
                    "a disease or exposure observation."
                ),
            )
        ],
        manifest_path=resolved_manifest_path,
    )
    typer.echo(f"Wrote {len(rows)} county reference row(s) to {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("census-population")
def census_population(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print planned Census queries."),
    latest_only: bool = typer.Option(
        False,
        help="Fetch only the latest static Census county totals CSV.",
    ),
    append: bool = typer.Option(
        False,
        help="Append to an existing population CSV and dedupe by county-year.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    api_key = get_census_api_key()
    urls = _census_population_urls(api_key=api_key, latest_only=latest_only)
    if dry_run:
        typer.echo(f"Planned Census population query(s): {len(urls)}")
        for url in urls:
            typer.echo(sanitize_census_url(url))
        return

    try:
        if latest_only:
            rows = fetch_maryland_latest_county_population_estimates()
        else:
            rows = fetch_maryland_county_population_estimates(api_key=api_key)
    except CensusApiResponseError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output = write_county_population_output(rows, output_dir, append=append)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _census_population_provenance_records(
            urls=urls,
            rows=rows,
            output_path=output,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            latest_only=latest_only,
            append=append,
            api_key_present=api_key is not None,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} county-year population row(s) to {output} "
        f"(append={append})"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("regional-population")
def regional_population(
    output_dir: Path = typer.Option(
        Path("build/etl/regional-population"),
        help="Output directory for Mid-Atlantic population artifacts.",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Print planned Census API queries without fetching data.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    api_key = get_census_api_key()
    urls = build_midatlantic_population_urls(api_key=api_key)
    if dry_run:
        typer.echo(f"Planned Mid-Atlantic Census population query(s): {len(urls)}")
        for url in urls:
            typer.echo(sanitize_census_url(url))
        return

    try:
        rows = fetch_midatlantic_county_population_estimates(api_key=api_key)
    except CensusApiResponseError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output = write_regional_county_population_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _regional_population_provenance_records(
            urls=urls,
            rows=rows,
            output_path=output,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            api_key_present=api_key is not None,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Mid-Atlantic county-year population row(s) to {output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("regional-demographics")
def regional_demographics(
    output_dir: Path = typer.Option(
        Path("build/etl/regional-demographics"),
        help="Output directory for Mid-Atlantic demographic artifacts.",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Print planned Census static CSV requests without fetching data.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for source acquisition provenance.",
    ),
) -> None:
    urls = build_midatlantic_age_sex_urls()
    if dry_run:
        typer.echo(f"Planned Mid-Atlantic Census age/sex request(s): {len(urls)}")
        for url in urls:
            typer.echo(url)
        return

    rows = fetch_midatlantic_age_sex_demographics()
    output = write_regional_age_demographics_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _regional_demographics_provenance_records(
            urls=urls,
            rows=rows,
            output_path=output,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Mid-Atlantic county-year demographic row(s) to {output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("acs-exposure")
def acs_exposure(
    year: int = typer.Option(
        2024,
        help="ACS 5-year table-based summary file vintage year.",
    ),
    raw_dir: Path = typer.Option(
        Path("data/raw/acs-exposure"),
        help="Ignored raw-data directory for ACS exposure source files.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/acs-exposure"),
        help="Output directory for ACS exposure artifacts.",
    ),
    download_if_missing: bool = typer.Option(
        True,
        help="Download public ACS source files if they are missing from --raw-dir.",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Print planned ACS source URLs without fetching data.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for source acquisition provenance.",
    ),
    append: bool = typer.Option(
        False,
        "--append/--replace",
        help=(
            "Append to existing ACS exposure artifacts with key-based dedupe, "
            "or replace the output files."
        ),
    ),
) -> None:
    try:
        source_urls = build_acs_exposure_source_urls(year=year)
    except AcsExposureInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if dry_run:
        typer.echo(f"Planned ACS exposure source URL(s): {len(source_urls.all_urls)}")
        for url in source_urls.all_urls:
            typer.echo(url)
        return

    try:
        source_paths = materialize_acs_exposure_sources(
            raw_dir,
            year=year,
            download_if_missing=download_if_missing,
        )
        rows = build_midatlantic_acs_exposure_from_paths(
            source_paths,
            source_urls=source_urls,
        )
    except AcsExposureInputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output = write_acs_exposure_output(rows, output_dir, append=append)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _acs_exposure_provenance_records(
            source_urls=source_urls,
            source_paths=source_paths,
            output_path=output,
            output_dir=output_dir,
            raw_dir=raw_dir,
            manifest_path=resolved_manifest_path,
            row_count=len(rows),
            append=append,
        ),
        manifest_path=resolved_manifest_path,
        append=append,
    )
    typer.echo(f"Wrote {len(rows)} ACS exposure row(s) to {output} (append={append})")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    if start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")
    if start_year < 2000 or end_year > 2025:
        raise typer.BadParameter(
            "Census BPS county annual ASCII files are supported for 2000-2025"
        )
    rows = []
    rows_by_year = {}
    for year in range(start_year, end_year + 1):
        source_url = build_census_bps_county_annual_url(year)
        text = fetch_census_bps_county_text(source_url)
        year_rows = parse_census_bps_county_text(
            text,
            source_url=source_url,
            source_id=source_id_from_census_bps_year(year),
        )
        rows_by_year[year] = year_rows
        rows.extend(year_rows)
    output = write_building_permits_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _building_permits_provenance_records(
            start_year=start_year,
            end_year=end_year,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            output_path=output,
            rows_by_year=rows_by_year,
        ),
        manifest_path=resolved_manifest_path,
    )
    written_row_count = len({(row.county_fips.zfill(5), row.year) for row in rows})
    typer.echo(f"Wrote {written_row_count} building permit row(s) to {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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


@etl_app.command("usdm-drought")
def usdm_drought(
    start_year: int = typer.Option(2000, help="First USDM calendar year."),
    end_year: int = typer.Option(2025, help="Last USDM calendar year."),
    aoi: str = typer.Option("MD", help="USDM area of interest, such as MD."),
    output_dir: Path = typer.Option(
        Path("build/etl/usdm-drought"),
        help="Output directory for USDM drought ETL artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    if start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")
    rows = []
    rows_by_year = {}
    for year in range(start_year, end_year + 1):
        year_rows = fetch_usdm_drought_year(
            aoi=aoi,
            year=year,
            fetcher=fetch_usdm_text,
        )
        rows_by_year[year] = year_rows
        rows.extend(year_rows)
    weekly_output = write_usdm_weekly_output(rows, output_dir)
    county_year_rows = build_usdm_county_year_features(rows)
    county_year_output = write_usdm_county_year_output(county_year_rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _usdm_provenance_records(
            start_year=start_year,
            end_year=end_year,
            aoi=aoi,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            rows_by_year=rows_by_year,
            derived_artifact_paths=[weekly_output, county_year_output],
        ),
        manifest_path=resolved_manifest_path,
    )
    weekly_row_count = len({(row.county_fips, row.map_date) for row in rows})
    typer.echo(
        f"Wrote {weekly_row_count} USDM weekly drought row(s) to {weekly_output}"
    )
    typer.echo(
        f"Wrote {len(county_year_rows)} USDM county-year drought feature row(s) "
        f"to {county_year_output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("enso-oni")
def enso_oni(
    source_url: str = typer.Option(
        NOAA_CPC_ONI_URL,
        help="NOAA CPC ONI ASCII table URL.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/enso"),
        help="Output directory for ENSO ONI ETL artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    try:
        rows = parse_oni_ascii_text(
            fetch_oni_text(source_url),
            source_url=source_url,
        )
    except OniInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    season_output = write_oni_season_output(rows, output_dir)
    model_year_rows = build_oni_model_year_features(rows)
    model_year_output = write_oni_model_year_output(model_year_rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_source_url = _sanitize_provenance_url(source_url)
    manifest_output = _write_single_request_provenance_manifest(
        manifest_path=resolved_manifest_path,
        record=AcquisitionProvenanceRecord(
            source_id="noaa_cpc_oni",
            source_name="NOAA CPC Oceanic Nino Index",
            source_url=provenance_source_url,
            citation_url=provenance_source_url,
            acquisition_command=_format_cli_command(
                [
                    "tickbiterisk",
                    "etl",
                    "enso-oni",
                    "--source-url",
                    provenance_source_url,
                    "--output-dir",
                    str(output_dir),
                    "--provenance-manifest-path",
                    str(resolved_manifest_path),
                ]
            ),
            acquisition_procedure=(
                "Fetch the official NOAA CPC ONI ASCII table and parse seasonal "
                "rows into lagged model-year ENSO features."
            ),
            request_method="GET",
            request_description="NOAA CPC ONI ASCII table request.",
            derived_artifact_paths=[season_output, model_year_output],
            row_count=len(rows),
            parser_method="parse_oni_ascii_text",
            extraction_quality="accepted",
            access_notes="Public NOAA CPC endpoint; no API key required.",
            modeling_caveats=(
                "Global climate context only; not Maryland-specific and not a "
                "public-default input without model evidence."
            ),
        ),
    )
    typer.echo(f"Wrote {len(rows)} NOAA CPC ONI season row(s) to {season_output}")
    typer.echo(
        f"Wrote {len(model_year_rows)} NOAA CPC ONI model-year feature row(s) "
        f"to {model_year_output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {manifest_output}")


@etl_app.command("enso-mei-v2")
def enso_mei_v2(
    source_url: str = typer.Option(
        NOAA_PSL_MEI_V2_URL,
        help="NOAA PSL MEI.v2 CSV table URL.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/enso"),
        help="Output directory for ENSO MEI.v2 ETL artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    try:
        rows = parse_mei_v2_csv_text(
            fetch_mei_v2_text(source_url),
            source_url=source_url,
        )
    except MeiV2InputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    monthly_output = write_mei_v2_monthly_output(rows, output_dir)
    model_year_rows = build_mei_v2_model_year_features(rows)
    model_year_output = write_mei_v2_model_year_output(model_year_rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_source_url = _sanitize_provenance_url(source_url)
    manifest_output = _write_single_request_provenance_manifest(
        manifest_path=resolved_manifest_path,
        record=AcquisitionProvenanceRecord(
            source_id="noaa_psl_mei_v2",
            source_name="NOAA PSL Multivariate ENSO Index version 2",
            source_url=provenance_source_url,
            citation_url=NOAA_PSL_MEI_V2_CITATION_URL,
            acquisition_command=_format_cli_command(
                [
                    "tickbiterisk",
                    "etl",
                    "enso-mei-v2",
                    "--source-url",
                    provenance_source_url,
                    "--output-dir",
                    str(output_dir),
                    "--provenance-manifest-path",
                    str(resolved_manifest_path),
                ]
            ),
            acquisition_procedure=(
                "Fetch the official NOAA PSL MEI.v2 CSV table and parse monthly "
                "rows into complete prior-year global climate context features."
            ),
            request_method="GET",
            request_description="NOAA PSL MEI.v2 CSV table request.",
            derived_artifact_paths=[monthly_output, model_year_output],
            row_count=len(rows),
            parser_method="parse_mei_v2_csv_text",
            extraction_quality="accepted",
            access_notes="Public NOAA PSL endpoint; no API key required.",
            modeling_caveats=(
                "Global ocean-atmosphere ENSO context only; not Maryland-specific, "
                "not an official CPC phase classification, and not a public-default "
                "input without model evidence."
            ),
        ),
    )
    typer.echo(f"Wrote {len(rows)} NOAA PSL MEI.v2 monthly row(s) to {monthly_output}")
    typer.echo(
        f"Wrote {len(model_year_rows)} NOAA PSL MEI.v2 model-year feature row(s) "
        f"to {model_year_output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {manifest_output}")


@etl_app.command("enviroatlas-habitat")
def enviroatlas_habitat(
    output_dir: Path = typer.Option(
        Path("build/etl/enviroatlas"),
        help="Output directory for EnviroAtlas habitat ETL artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    source_url = build_enviroatlas_maryland_habitat_query_url()
    response_json = fetch_enviroatlas_json(source_url)
    rows = parse_enviroatlas_county_habitat(response_json, source_url=source_url)
    output = write_enviroatlas_county_habitat_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    manifest_output = _write_single_request_provenance_manifest(
        manifest_path=resolved_manifest_path,
        record=AcquisitionProvenanceRecord(
            source_id="epa_enviroatlas_habitat",
            source_name="EPA EnviroAtlas county landscape layer",
            source_url=source_url,
            citation_url=EPA_ENVIROATLAS_DATA_DOWNLOAD_URL,
            acquisition_command=_format_cli_command(
                [
                    "tickbiterisk",
                    "etl",
                    "enviroatlas-habitat",
                    "--output-dir",
                    str(output_dir),
                    "--provenance-manifest-path",
                    str(resolved_manifest_path),
                ]
            ),
            acquisition_procedure=(
                "Fetch the EPA EnviroAtlas ArcGIS query for Maryland county "
                "landscape attributes and normalize accepted county records."
            ),
            request_method="GET",
            request_description="EPA EnviroAtlas ArcGIS county habitat query.",
            derived_artifact_paths=[output],
            row_count=len(rows),
            parser_method="parse_enviroatlas_county_habitat",
            extraction_quality="accepted",
            access_notes="Public EPA ArcGIS endpoint; no API key required.",
            modeling_caveats=(
                "Static county context; not annual land-cover change and not "
                "causal exposure evidence by itself."
            ),
        ),
    )
    typer.echo(f"Wrote {len(rows)} EnviroAtlas county habitat row(s) to {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {manifest_output}")


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
    region: str = typer.Option(
        "maryland",
        help="County filter: maryland or midatlantic.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    state_fips_values = _tick_status_state_fips_for_region(region)
    source_metadata, source_paths_by_id = _resolve_tick_status_sources(raw_dir)

    ixodes_rows = parse_ixodes_status(
        source_paths_by_id["vector"],
        source_id=source_metadata["vector"]["source_id"],
        state_fips_values=state_fips_values,
    )
    pathogen_rows = parse_pathogen_status(
        source_paths_by_id["pathogen"],
        source_id=source_metadata["pathogen"]["source_id"],
        state_fips_values=state_fips_values,
    )
    lone_star_rows = parse_lone_star_status(
        source_paths_by_id["lone_star"],
        source_id=source_metadata["lone_star"]["source_id"],
        state_fips_values=state_fips_values,
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _tick_status_provenance_records(
            source_metadata=[
                source_metadata["vector"],
                source_metadata["pathogen"],
                source_metadata["lone_star"],
            ],
            rows_by_source={
                source_metadata["vector"]["source_id"]: ixodes_rows,
                source_metadata["pathogen"]["source_id"]: pathogen_rows,
                source_metadata["lone_star"]["source_id"]: lone_star_rows,
            },
            source_paths_by_id=source_paths_by_id,
            outputs=outputs,
            raw_dir=raw_dir,
            output_dir=output_dir,
            region=region,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(feature_rows)} tick status feature row(s) to "
        f"{outputs.features_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


def _tick_status_state_fips_for_region(region: str) -> tuple[str, ...]:
    region_key = region.strip().lower()
    if region_key == "maryland":
        return DEFAULT_TICK_STATUS_STATE_FIPS
    if region_key == "midatlantic":
        return MIDATLANTIC_TICK_STATUS_STATE_FIPS
    raise typer.BadParameter("region must be one of: maryland, midatlantic")


@etl_app.command("nssp-coverage")
def nssp_coverage(
    raw_path: Path = typer.Option(
        Path("data/raw/nssp/Coverage_Map_Tbl_2024Jul01.csv"),
        help="Raw CDC NSSP county coverage CSV path.",
    ),
    county_reference_path: Path = typer.Option(
        Path("build/etl/county-reference/county_reference.csv"),
        help="County reference CSV used to attach Maryland FIPS codes.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/nssp-coverage"),
        help="Output directory for normalized NSSP coverage artifacts.",
    ),
    coverage_url: str = typer.Option(
        CDC_NSSP_COVERAGE_CSV_URL,
        help="CDC NSSP county coverage CSV URL.",
    ),
    download_if_missing: bool = typer.Option(
        True,
        help="Download the public CDC CSV if --raw-path is missing.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    try:
        downloaded = ensure_nssp_coverage_raw(
            raw_path,
            coverage_url=coverage_url,
            download_if_missing=download_if_missing,
        )
        raw_text = raw_path.read_text(encoding="utf-8-sig")
        raw_rows = parse_nssp_coverage_csv(raw_text)
        rows = build_maryland_nssp_coverage(
            raw_rows,
            county_reference_path=county_reference_path,
            source_id=NSSP_COVERAGE_SOURCE_ID,
            source_url=coverage_url,
            coverage_as_of_date=NSSP_COVERAGE_AS_OF_DATE,
        )
    except NsspCoverageInputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output_path = write_nssp_coverage_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            _nssp_coverage_provenance_record(
                raw_path=raw_path,
                output_path=output_path,
                output_dir=output_dir,
                county_reference_path=county_reference_path,
                manifest_path=resolved_manifest_path,
                coverage_url=coverage_url,
                downloaded=downloaded,
                row_count=len(rows),
            )
        ],
        manifest_path=resolved_manifest_path,
    )
    typer.echo(f"Wrote {len(rows)} NSSP coverage row(s) to {output_path}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    monthly_path = raw_dir / str(SEASONALITY_SOURCE_METADATA[0]["filename"])
    weekly_path = raw_dir / str(SEASONALITY_SOURCE_METADATA[1]["filename"])
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _seasonality_provenance_records(
            source_metadata=SEASONALITY_SOURCE_METADATA,
            observations=observations,
            source_paths_by_id={
                "cdc_seasonality_month_2023": monthly_path,
                "cdc_seasonality_week_2023": weekly_path,
            },
            output_paths=[
                outputs.observations_path,
                outputs.baseline_path,
            ],
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(observations)} seasonality observation row(s) to "
        f"{outputs.observations_path}"
    )
    typer.echo(
        f"Wrote {len(baseline_rows)} seasonality baseline row(s) to "
        f"{outputs.baseline_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    mast_acorn_path: Path = typer.Option(
        Path("build/etl/mast/maryland_dnr_mast_acorn_county_year.csv"),
        help="Optional Maryland DNR mast/acorn county-year feature CSV.",
    ),
    usdm_drought_path: Path = typer.Option(
        Path("build/etl/usdm-drought/usdm_drought_county_year.csv"),
        help="Optional USDM county-year drought feature CSV.",
    ),
    enviroatlas_habitat_path: Path = typer.Option(
        Path("build/etl/enviroatlas/enviroatlas_county_habitat.csv"),
        help="Optional EPA EnviroAtlas static county habitat feature CSV.",
    ),
    enso_oni_path: Path = typer.Option(
        Path("build/etl/enso/noaa_cpc_oni_model_year_features.csv"),
        help="Optional NOAA CPC ONI prior-year global climate feature CSV.",
    ),
    enso_mei_v2_path: Path = typer.Option(
        Path("build/etl/enso/noaa_psl_mei_v2_model_year_features.csv"),
        help="Optional NOAA PSL MEI.v2 prior-year global climate feature CSV.",
    ),
    regional_demographics_path: Path | None = typer.Option(
        None,
        help=(
            "Optional Mid-Atlantic Census PEP county age/sex CSV for prior-year "
            "age-structure exposure-context features."
        ),
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
    if (
        regional_demographics_path is not None
        and not regional_demographics_path.exists()
    ):
        raise typer.BadParameter(
            f"Regional demographics file not found: {regional_demographics_path}"
        )

    rows = build_model_feature_matrix(
        lyme_outcomes_path=lyme_outcomes_path,
        population_path=population_path,
        weather_weekly_path=weather_weekly_path,
        contact_pressure_path=(
            contact_pressure_path if contact_pressure_path.exists() else None
        ),
        deer_harvest_path=deer_harvest_path if deer_harvest_path.exists() else None,
        mast_acorn_path=mast_acorn_path if mast_acorn_path.exists() else None,
        usdm_drought_path=(
            usdm_drought_path if usdm_drought_path.exists() else None
        ),
        enviroatlas_habitat_path=(
            enviroatlas_habitat_path
            if enviroatlas_habitat_path.exists()
            else None
        ),
        enso_oni_path=enso_oni_path if enso_oni_path.exists() else None,
        enso_mei_v2_path=(
            enso_mei_v2_path if enso_mei_v2_path.exists() else None
        ),
        regional_demographics_path=regional_demographics_path,
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


@etl_app.command("model-design-matrix")
def model_design_matrix(
    model_features_path: Path = typer.Option(
        Path("build/etl/model/model_features_county_year.csv"),
        help="Input rich model feature matrix CSV.",
    ),
    county_adjacency_path: Path | None = typer.Option(
        None,
        help="Optional county adjacency CSV for spatial lag features.",
    ),
    regional_signals_path: Path | None = typer.Option(
        None,
        help="Optional Mid-Atlantic regional signal CSV for lagged regional features.",
    ),
    regional_incidence_clusters_path: Path | None = typer.Option(
        None,
        help=(
            "Optional Mid-Atlantic regional incidence cluster CSV for prior-history "
            "capacity-band features."
        ),
    ),
    lookback_years: int = typer.Option(
        5,
        help="Maximum prior county years used for lagged outcome features.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/model"),
        help="Output directory for numeric model design matrix artifacts.",
    ),
) -> None:
    if not model_features_path.exists():
        raise typer.BadParameter(
            f"Model features file not found: {model_features_path}"
        )
    if lookback_years < 1:
        raise typer.BadParameter("lookback-years must be at least 1")
    if county_adjacency_path is not None and not county_adjacency_path.exists():
        raise typer.BadParameter(
            f"County adjacency file not found: {county_adjacency_path}"
        )
    if regional_signals_path is not None and not regional_signals_path.exists():
        raise typer.BadParameter(
            f"Regional signals file not found: {regional_signals_path}"
        )
    if (
        regional_incidence_clusters_path is not None
        and not regional_incidence_clusters_path.exists()
    ):
        raise typer.BadParameter(
            "Regional incidence clusters file not found: "
            f"{regional_incidence_clusters_path}"
        )

    try:
        result = build_model_design_matrix(
            model_features_path=model_features_path,
            lookback_years=lookback_years,
            county_adjacency_path=county_adjacency_path,
            regional_signals_path=regional_signals_path,
            regional_incidence_clusters_path=regional_incidence_clusters_path,
        )
    except ModelDesignMatrixInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_model_design_matrix_outputs(result, output_dir)
    typer.echo(f"Wrote {len(result.rows)} model design matrix row(s) to {outputs.matrix_path}")
    typer.echo(f"Wrote model design matrix schema to {outputs.schema_path}")


@etl_app.command("county-adjacency")
def county_adjacency(
    county_geojson_path: Path = typer.Option(
        Path("public/data/md_counties.geojson"),
        help="Input Maryland county GeoJSON.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/county-adjacency"),
        help="Output directory for county adjacency CSV.",
    ),
) -> None:
    if not county_geojson_path.exists():
        raise typer.BadParameter(
            f"County GeoJSON file not found: {county_geojson_path}"
        )
    rows = build_county_adjacency_from_geojson(county_geojson_path)
    output_path = write_county_adjacency_output(rows, output_dir)
    typer.echo(f"Wrote {len(rows)} county adjacency row(s) to {output_path}")


@etl_app.command("model-compare")
def model_compare(
    design_matrix_path: Path = typer.Option(
        Path("build/etl/model/model_design_matrix_county_year.csv"),
        help="Input numeric model design matrix CSV.",
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
        help="Minimum prior county years required for model comparison.",
    ),
    ridge_alpha: float = typer.Option(
        1.0,
        help="Ridge penalty for the regularized linear comparison model.",
    ),
    shrinkage_strength: float = typer.Option(
        5.0,
        help="Pseudo-count strength for empirical Bayes county shrinkage.",
    ),
    random_forest_n_estimators: int = typer.Option(
        RANDOM_FOREST_N_ESTIMATORS,
        help="Tree count for the random forest research comparison lane.",
    ),
    random_forest_min_samples_leaf: int = typer.Option(
        RANDOM_FOREST_MIN_SAMPLES_LEAF,
        help="Minimum leaf size for the random forest research comparison lane.",
    ),
    random_forest_max_features: str = typer.Option(
        RANDOM_FOREST_MAX_FEATURES,
        help="Max-feature strategy for the random forest research comparison lane.",
    ),
    random_forest_random_state: int = typer.Option(
        RANDOM_FOREST_RANDOM_STATE,
        help="Random seed for the random forest research comparison lane.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/model-comparison"),
        help="Output directory for model comparison artifacts.",
    ),
    append: bool = typer.Option(
        False,
        "--append/--replace",
        help="Append to existing comparison artifacts with key-based dedupe, or replace.",
    ),
) -> None:
    if not design_matrix_path.exists():
        raise typer.BadParameter(
            f"Model design matrix file not found: {design_matrix_path}"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if ridge_alpha <= 0:
        raise typer.BadParameter("ridge-alpha must be greater than 0")
    if shrinkage_strength < 0:
        raise typer.BadParameter("shrinkage-strength must be non-negative")
    if random_forest_n_estimators < 1:
        raise typer.BadParameter("random-forest-n-estimators must be at least 1")
    if random_forest_min_samples_leaf < 1:
        raise typer.BadParameter(
            "random-forest-min-samples-leaf must be at least 1"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = run_model_comparison(
            design_matrix_path=design_matrix_path,
            start_year=start_year,
            end_year=end_year,
            min_train_years=min_train_years,
            ridge_alpha=ridge_alpha,
            shrinkage_strength=shrinkage_strength,
            random_forest_n_estimators=random_forest_n_estimators,
            random_forest_min_samples_leaf=random_forest_min_samples_leaf,
            random_forest_max_features=random_forest_max_features,
            random_forest_random_state=random_forest_random_state,
        )
    except ModelComparisonInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_model_comparison_outputs(result, output_dir, append=append)
    typer.echo(f"Wrote 1 model comparison run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} model comparison prediction row(s) to "
        f"{outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.intervals)} model comparison interval row(s) to "
        f"{outputs.intervals_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} model comparison metric row(s) to "
        f"{outputs.metrics_path}"
    )
    typer.echo(
        f"Wrote {len(result.summary)} model comparison summary row(s) to "
        f"{outputs.summary_path}"
    )


@etl_app.command("annual-forecast")
def annual_forecast(
    design_matrix_path: Path = typer.Option(
        Path("build/etl/model/model_design_matrix_county_year.csv"),
        help="Input observed-history numeric model design matrix CSV.",
    ),
    population_path: Path = typer.Option(
        Path("build/etl/regional-population/midatlantic_county_population_year.csv"),
        help="County-year population panel containing the forecast target year.",
    ),
    target_year: int = typer.Option(
        2026,
        help="Future forecast year to score.",
    ),
    forecast_origin_year: int = typer.Option(
        2024,
        help="Latest observed outcome year allowed in training.",
    ),
    min_train_years: int = typer.Option(
        5,
        help="Minimum prior county years required for annual forecast.",
    ),
    shrinkage_strength: float = typer.Option(
        5.0,
        help="Pseudo-count strength for empirical Bayes county shrinkage.",
    ),
    as_of_date: str = typer.Option(
        "unspecified",
        help="Forecast artifact as-of date for provenance.",
    ),
    data_cutoff_date: str = typer.Option(
        "unspecified",
        help="Latest source data cutoff date represented by this forecast.",
    ),
    source_vintage: str | None = typer.Option(
        None,
        help="Source vintage label. Defaults to the input design matrix SHA-256.",
    ),
    update_mode: str = typer.Option(
        "pre_update",
        help=(
            "Forecast update mode label: pre_update or post_observed_outcome."
        ),
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/annual-forecast"),
        help="Output directory for annual forecast artifacts.",
    ),
) -> None:
    if not design_matrix_path.exists():
        raise typer.BadParameter(
            f"Model design matrix file not found: {design_matrix_path}"
        )
    if not population_path.exists():
        raise typer.BadParameter(f"Population file not found: {population_path}")
    if target_year <= forecast_origin_year:
        raise typer.BadParameter(
            "target-year must be greater than forecast-origin-year"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if shrinkage_strength < 0:
        raise typer.BadParameter("shrinkage-strength must be non-negative")
    _validate_forecast_update_mode(update_mode)

    try:
        result = build_annual_forecast(
            design_matrix_path=design_matrix_path,
            population_path=population_path,
            target_year=target_year,
            forecast_origin_year=forecast_origin_year,
            min_train_years=min_train_years,
            shrinkage_strength=shrinkage_strength,
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
            update_mode=update_mode,
        )
    except AnnualForecastInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_annual_forecast_outputs(result, output_dir)
    typer.echo(f"Wrote 1 annual forecast run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} annual forecast prediction row(s) to "
        f"{outputs.predictions_path}"
    )


@etl_app.command("model-diagnostics")
def model_diagnostics(
    predictions_path: Path = typer.Option(
        Path("build/etl/model-comparison/model_comparison_predictions.csv"),
        help="Input model comparison predictions CSV.",
    ),
    intervals_path: Path | None = typer.Option(
        None,
        help="Optional model interval CSV reserved for capacity diagnostics.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/model-diagnostics"),
        help="Output directory for model diagnostics artifacts.",
    ),
    as_of_date: str = typer.Option(
        "unspecified",
        help="Forecast diagnostic as-of date.",
    ),
    data_cutoff_date: str = typer.Option(
        "unspecified",
        help="Latest source data date represented in forecast diagnostics.",
    ),
    source_vintage: str | None = typer.Option(
        None,
        help="Optional source vintage label for forecast diagnostics.",
    ),
) -> None:
    if not predictions_path.exists():
        raise typer.BadParameter(
            f"Model comparison predictions file not found: {predictions_path}"
        )
    if intervals_path is not None and not intervals_path.exists():
        raise typer.BadParameter(
            f"Model comparison intervals file not found: {intervals_path}"
        )

    try:
        result = build_model_diagnostics(
            predictions_path=predictions_path,
            intervals_path=intervals_path,
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
        )
    except ModelDiagnosticsInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_model_diagnostics_outputs(result, output_dir)
    typer.echo(
        f"Wrote {len(result.surveillance_residuals)} surveillance residual row(s) to "
        f"{outputs.surveillance_residuals_path}"
    )
    typer.echo(
        f"Wrote {len(result.surveillance_summary)} surveillance summary row(s) to "
        f"{outputs.surveillance_summary_path}"
    )
    typer.echo(
        f"Wrote {len(result.regional_hotspot_summary)} regional hotspot row(s) to "
        f"{outputs.regional_hotspot_summary_path}"
    )
    typer.echo(
        f"Wrote {len(result.regional_capacity_intervals)} regional capacity row(s) to "
        f"{outputs.regional_capacity_intervals_path}"
    )
    typer.echo(
        f"Wrote {len(result.forecast_update_audit)} forecast update audit row(s) to "
        f"{outputs.forecast_update_audit_path}"
    )
    typer.echo(
        f"Wrote {len(result.forecast_update_summary)} forecast update summary row(s) to "
        f"{outputs.forecast_update_summary_path}"
    )
    typer.echo(
        f"Wrote {len(result.forecast_calibration_summary)} forecast calibration "
        f"summary row(s) to {outputs.forecast_calibration_summary_path}"
    )


@etl_app.command("forecast-calibration-backtest")
def forecast_calibration_backtest(
    predictions_path: Path = typer.Option(
        Path("build/etl/model-comparison/model_comparison_predictions.csv"),
        help="Input model comparison predictions CSV.",
    ),
    start_year: int = typer.Option(
        2007,
        help="First held-out year to calibrate.",
    ),
    end_year: int | None = typer.Option(
        None,
        help="Last held-out year to calibrate. Defaults to max year in input.",
    ),
    min_calibration_updates: int = typer.Option(
        5,
        help="Minimum prior update rows required before applying calibration.",
    ),
    calibration_prior_strength: float = typer.Option(
        5.0,
        help="Pseudo-update strength shrinking calibration multipliers toward 1.0.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/forecast-calibration-backtest"),
        help="Output directory for forecast calibration backtest artifacts.",
    ),
) -> None:
    if not predictions_path.exists():
        raise typer.BadParameter(
            f"Model comparison predictions file not found: {predictions_path}"
        )
    if min_calibration_updates < 1:
        raise typer.BadParameter("min-calibration-updates must be at least 1")
    if not math.isfinite(calibration_prior_strength) or calibration_prior_strength < 0:
        raise typer.BadParameter(
            "calibration-prior-strength must be finite and non-negative"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = build_forecast_calibration_backtest(
            predictions_path=predictions_path,
            start_year=start_year,
            end_year=end_year,
            min_calibration_updates=min_calibration_updates,
            calibration_prior_strength=calibration_prior_strength,
        )
    except ForecastCalibrationBacktestInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_forecast_calibration_backtest_outputs(result, output_dir)
    typer.echo(
        f"Wrote 1 forecast calibration backtest run row(s) to {outputs.runs_path}"
    )
    typer.echo(
        f"Wrote {len(result.predictions)} forecast calibration backtest prediction "
        f"row(s) to {outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} forecast calibration backtest metric row(s) to "
        f"{outputs.metrics_path}"
    )


@etl_app.command("forecast-bayesian-update-backtest")
def forecast_bayesian_update_backtest(
    predictions_path: Path = typer.Option(
        Path("build/etl/model-comparison/model_comparison_predictions.csv"),
        help="Input model comparison predictions CSV.",
    ),
    start_year: int = typer.Option(
        2007,
        help="First held-out year to update.",
    ),
    end_year: int | None = typer.Option(
        None,
        help="Last held-out year to update. Defaults to max year in input.",
    ),
    min_prior_updates: int = typer.Option(
        5,
        help="Minimum prior update rows required before applying posterior evidence.",
    ),
    prior_strength_cases: float = typer.Option(
        10.0,
        help="Gamma prior case strength centered on a multiplier of 1.0.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/forecast-bayesian-update-backtest"),
        help="Output directory for forecast Bayesian update backtest artifacts.",
    ),
) -> None:
    if not predictions_path.exists():
        raise typer.BadParameter(
            f"Model comparison predictions file not found: {predictions_path}"
        )
    if min_prior_updates < 1:
        raise typer.BadParameter("min-prior-updates must be at least 1")
    if not math.isfinite(prior_strength_cases) or prior_strength_cases <= 0:
        raise typer.BadParameter(
            "prior-strength-cases must be finite and greater than 0"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = build_forecast_bayesian_update_backtest(
            predictions_path=predictions_path,
            start_year=start_year,
            end_year=end_year,
            min_prior_updates=min_prior_updates,
            prior_strength_cases=prior_strength_cases,
        )
    except ForecastBayesianUpdateBacktestInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_forecast_bayesian_update_backtest_outputs(result, output_dir)
    typer.echo(
        f"Wrote 1 forecast Bayesian update backtest run row(s) to "
        f"{outputs.runs_path}"
    )
    typer.echo(
        f"Wrote {len(result.predictions)} forecast Bayesian update backtest "
        f"prediction row(s) to {outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} forecast Bayesian update backtest metric row(s) to "
        f"{outputs.metrics_path}"
    )


@etl_app.command("county-week-risk")
def county_week_risk(
    predictions_path: Path = typer.Option(
        Path("build/etl/model-comparison/model_comparison_predictions.csv"),
        "--predictions-path",
        "--backtest-predictions-path",
        help=(
            "Input annual county prediction CSV from annual forecast, model "
            "comparison, or legacy backtest outputs."
        ),
    ),
    seasonality_baseline_path: Path = typer.Option(
        Path("build/etl/seasonality/seasonality_baseline.csv"),
        help="Input CDC Lyme seasonality baseline CSV.",
    ),
    model_name: str = typer.Option(
        "linear_blend_baseline",
        help="Annual prediction model branch to convert into weekly risk scores.",
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
    if not predictions_path.exists():
        raise typer.BadParameter(
            f"Annual predictions file not found: {predictions_path}"
        )
    if not seasonality_baseline_path.exists():
        raise typer.BadParameter(
            f"Seasonality baseline file not found: {seasonality_baseline_path}"
        )

    try:
        result = build_seasonal_risk_scores(
            predictions_path=predictions_path,
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


@etl_app.command("lyme-aggregate-validation")
def lyme_aggregate_validation(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme-aggregate"),
        help="Raw directory containing CDC Lyme aggregate dashboard exports.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/lyme-aggregate"),
        help="Output directory for CDC Lyme aggregate validation artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    source_paths_by_id = {
        metadata["source_id"]: raw_dir / str(metadata["filename"])
        for metadata in LYME_AGGREGATE_SOURCE_METADATA
    }
    for source_path in source_paths_by_id.values():
        if not source_path.exists():
            raise typer.BadParameter(
                f"Lyme aggregate source file not found: {source_path}"
            )

    parsed_values_by_source = _parse_lyme_aggregate_sources(source_paths_by_id)
    state_rows = build_aggregate_observations(
        case_rows=parsed_values_by_source["cdc_caseincid_cases_state_2023"],
        rate_rows=parsed_values_by_source["cdc_caseincid_rates_state_2023"],
    )
    region_rows = build_aggregate_observations(
        case_rows=parsed_values_by_source["cdc_caseincid_cases_region_2023"],
        rate_rows=parsed_values_by_source["cdc_caseincid_rates_region_2023"],
    )
    national_rows = build_aggregate_observations(
        case_rows=parsed_values_by_source["cdc_caseincid_overall_cases_2023"],
        rate_rows=parsed_values_by_source["cdc_caseincid_overall_rate_2023"],
    )
    outputs = write_lyme_aggregate_outputs(
        state_rows=state_rows,
        region_rows=region_rows,
        national_rows=national_rows,
        output_dir=output_dir,
    )
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _lyme_aggregate_provenance_records(
            source_metadata=LYME_AGGREGATE_SOURCE_METADATA,
            parsed_values_by_source=parsed_values_by_source,
            source_paths_by_id=source_paths_by_id,
            outputs=outputs,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(state_rows)} CDC Lyme state aggregate row(s) to "
        f"{outputs.state_path}"
    )
    typer.echo(
        f"Wrote {len(region_rows)} CDC Lyme regional aggregate row(s) to "
        f"{outputs.region_path}"
    )
    typer.echo(
        f"Wrote {len(national_rows)} CDC Lyme national aggregate row(s) to "
        f"{outputs.national_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("wv-vectorborne-summary")
def wv_vectorborne_summary(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme/west-virginia"),
        help="Raw directory containing WV OEPS vectorborne PDF summaries.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/wv-vectorborne"),
        help="Output directory for WV vectorborne aggregate artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    rows_by_source: dict[str, list[WestVirginiaVectorborneStateSummary]] = {}
    source_paths_by_id = {}
    for metadata in WV_VECTORBORNE_SOURCE_METADATA:
        source_path = raw_dir / str(metadata["filename"])
        if not source_path.exists():
            raise typer.BadParameter(
                f"WV vectorborne report source file not found: {source_path}"
            )
        source_id = str(metadata["source_id"])
        source_paths_by_id[source_id] = source_path
        rows_by_source[source_id] = parse_wv_vectorborne_report_pdf(
            source_path,
            source_id=source_id,
            source_url=str(metadata["source_url"]),
        )

    rows = [
        row
        for source_id in sorted(rows_by_source)
        for row in rows_by_source[source_id]
    ]
    output_path = write_wv_vectorborne_state_summary(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _wv_vectorborne_provenance_records(
            rows_by_source=rows_by_source,
            source_paths_by_id=source_paths_by_id,
            output_path=output_path,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} West Virginia vectorborne state summary row(s) to "
        f"{output_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("mass-dph-syndromic-ed")
def mass_dph_syndromic_ed(
    raw_dir: Path = typer.Option(
        Path("data/raw/exposure/massachusetts"),
        help="Raw directory containing Massachusetts DPH syndromic ED DOCX reports.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/mass-dph-syndromic-ed"),
        help="Output directory for Massachusetts DPH syndromic ED artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    rows_by_source: dict[str, list[MassDphSyndromicEdCountySummary]] = {}
    source_paths_by_id = {}
    for metadata in MASS_DPH_SYNDROMIC_ED_SOURCE_METADATA:
        source_path = raw_dir / str(metadata["filename"])
        if not source_path.exists():
            raise typer.BadParameter(
                "Massachusetts DPH syndromic ED source file not found: "
                f"{source_path}"
            )
        source_id = str(metadata["source_id"])
        source_paths_by_id[source_id] = source_path
        rows_by_source[source_id] = parse_mass_dph_syndromic_ed_docx(
            source_path,
            source_id=source_id,
            source_url=str(metadata["source_url"]),
            report_year=int(str(metadata["report_year"])),
            report_period_label=str(metadata["report_period_label"]),
            report_period_start=str(metadata["report_period_start"]),
            report_period_end=str(metadata["report_period_end"]),
        )

    rows = [
        row
        for metadata in MASS_DPH_SYNDROMIC_ED_SOURCE_METADATA
        for row in rows_by_source[str(metadata["source_id"])]
    ]
    output_path = write_mass_dph_syndromic_ed_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _mass_dph_syndromic_ed_provenance_records(
            rows_by_source=rows_by_source,
            source_paths_by_id=source_paths_by_id,
            output_path=output_path,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Massachusetts DPH syndromic ED county summary row(s) "
        f"to {output_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("nj-doh-reportable-tickborne")
def nj_doh_reportable_tickborne(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme/new-jersey"),
        help="Raw directory containing NJ DOH reportable disease PDFs.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/nj-doh-reportable-tickborne"),
        help="Output directory for NJ DOH reportable tickborne artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    stats_pdf_path = raw_dir / str(NJ_DOH_REPORTABLE_TICKBORNE_METADATA["filename"])
    technical_notes_path = raw_dir / str(
        NJ_DOH_REPORTABLE_TICKBORNE_METADATA["technical_notes_filename"]
    )
    if not stats_pdf_path.exists():
        raise typer.BadParameter(
            f"New Jersey DOH reportable disease statistics PDF not found: {stats_pdf_path}"
        )
    if not technical_notes_path.exists():
        raise typer.BadParameter(
            f"New Jersey DOH technical notes PDF not found: {technical_notes_path}"
        )

    rows = parse_nj_doh_reportable_tickborne_pdf(
        stats_pdf_path,
        source_id=str(NJ_DOH_REPORTABLE_TICKBORNE_METADATA["source_id"]),
        source_url=str(NJ_DOH_REPORTABLE_TICKBORNE_METADATA["source_url"]),
    )
    output_path = write_nj_doh_reportable_tickborne_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _nj_doh_reportable_tickborne_provenance_records(
            rows=rows,
            stats_pdf_path=stats_pdf_path,
            technical_notes_path=technical_notes_path,
            output_path=output_path,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} New Jersey DOH reportable tickborne row(s) to "
        f"{output_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("maine-jmmc-tickborne-rates")
def maine_jmmc_tickborne_rates(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme/maine"),
        help="Raw directory containing the Maine JMMC tickborne trends PDF.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/maine-jmmc-tickborne-rates"),
        help="Output directory for Maine JMMC tickborne county-rate artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    pdf_path = raw_dir / str(MAINE_JMMC_TICKBORNE_RATES_METADATA["filename"])
    if not pdf_path.exists():
        raise typer.BadParameter(f"Maine JMMC tickborne trends PDF not found: {pdf_path}")

    rows = parse_maine_jmmc_tickborne_rates_pdf(
        pdf_path,
        source_id=str(MAINE_JMMC_TICKBORNE_RATES_METADATA["source_id"]),
        source_url=str(MAINE_JMMC_TICKBORNE_RATES_METADATA["source_url"]),
    )
    output_path = write_maine_jmmc_tickborne_rates_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _maine_jmmc_tickborne_rates_provenance_records(
            rows=rows,
            pdf_path=pdf_path,
            output_path=output_path,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Maine JMMC tickborne county-rate row(s) to "
        f"{output_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("regional-lyme-outcomes")
def regional_lyme_outcomes(
    raw_dir: Path = typer.Option(
        Path("data/raw/lyme"),
        help="Raw directory containing the CDC Lyme county dashboard export.",
    ),
    pa_2024_workbook_path: Path | None = typer.Option(
        None,
        help=(
            "Optional Pennsylvania DOH Lyme county workbook through 2024; "
            "when provided, appends flagged PA 2024 state-source rows."
        ),
    ),
    de_lyme_html_path: Path | None = typer.Option(
        None,
        help=(
            "Optional Delaware DHSS Lyme data HTML page; when provided, writes "
            "flagged 2019-2023 state-source validation rows to a sidecar file "
            "without appending overlapping years to the model panel."
        ),
    ),
    va_vdh_locality_csv_path: Path | None = typer.Option(
        None,
        help=(
            "Optional Virginia VDH reportable disease geography CSV; when "
            "provided, appends flagged 2024 locality state-source rows to the "
            "regional outcome panel."
        ),
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-lyme"),
        help="Output directory for Mid-Atlantic Lyme outcome artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    source_path = raw_dir / str(REGIONAL_LYME_SOURCE_METADATA["filename"])
    if not source_path.exists():
        raise typer.BadParameter(f"Regional Lyme source file not found: {source_path}")

    cdc_rows = parse_cdc_midatlantic_county_dashboard(
        source_path,
        source_id=str(REGIONAL_LYME_SOURCE_METADATA["source_id"]),
    )
    rows = list(cdc_rows)
    pa_rows: list[RegionalLymeCountyYear] = []
    if pa_2024_workbook_path is not None:
        if not pa_2024_workbook_path.exists():
            raise typer.BadParameter(
                f"PA 2024 Lyme workbook not found: {pa_2024_workbook_path}"
            )
        pa_rows = parse_pa_doh_lyme_county_workbook(
            pa_2024_workbook_path,
            source_id=str(REGIONAL_PA_LYME_2024_SOURCE_METADATA["source_id"]),
            target_year=2024,
        )
        rows.extend(pa_rows)
        rows.sort(key=lambda row: (row.state_fips, row.county_fips, row.year))
    de_validation_rows: list[RegionalLymeCountyYear] = []
    if de_lyme_html_path is not None:
        if not de_lyme_html_path.exists():
            raise typer.BadParameter(
                f"Delaware Lyme HTML source not found: {de_lyme_html_path}"
            )
        de_validation_rows = parse_de_dhss_lyme_county_html(
            de_lyme_html_path,
            source_id=str(REGIONAL_DE_LYME_SOURCE_METADATA["source_id"]),
        )
    va_rows: list[RegionalLymeCountyYear] = []
    if va_vdh_locality_csv_path is not None:
        if not va_vdh_locality_csv_path.exists():
            raise typer.BadParameter(
                "Virginia VDH locality CSV source not found: "
                f"{va_vdh_locality_csv_path}"
            )
        va_rows = parse_va_vdh_reportable_disease_locality_csv(
            va_vdh_locality_csv_path,
            source_id=str(REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA["source_id"]),
            target_year=2024,
        )
        rows.extend(va_rows)
        rows.sort(key=lambda row: (row.state_fips, row.county_fips, row.year))
    output_path = write_regional_lyme_output(rows, output_dir)
    de_validation_output_path: Path | None = None
    if de_validation_rows:
        de_validation_output_path = write_regional_lyme_state_validation_output(
            de_validation_rows,
            output_dir,
        )
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _regional_lyme_provenance_records(
            metadata=REGIONAL_LYME_SOURCE_METADATA,
            rows=cdc_rows,
            source_path=source_path,
            pa_rows=pa_rows,
            pa_source_path=pa_2024_workbook_path,
            de_validation_rows=de_validation_rows,
            de_source_path=de_lyme_html_path,
            de_validation_output_path=de_validation_output_path,
            va_rows=va_rows,
            va_source_path=va_vdh_locality_csv_path,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            output_path=output_path,
        ),
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Mid-Atlantic Lyme county-year outcome row(s) to "
        f"{output_path}"
    )
    if de_validation_output_path is not None:
        typer.echo(
            f"Wrote {len(de_validation_rows)} regional state-source validation "
            f"row(s) to {de_validation_output_path}"
        )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("regional-signals")
def regional_signals(
    regional_lyme_path: Path = typer.Option(
        Path("build/etl/regional-lyme/midatlantic_lyme_county_year.csv"),
        help="Input Mid-Atlantic Lyme county-year panel.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-signals"),
        help="Output directory for Mid-Atlantic regional signal artifacts.",
    ),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for source artifact provenance.",
    ),
) -> None:
    if not regional_lyme_path.exists():
        raise typer.BadParameter(f"Regional Lyme panel not found: {regional_lyme_path}")

    source_panel_sha256 = compute_sha256(regional_lyme_path)
    rows = build_midatlantic_regional_signals(
        regional_lyme_path,
        source_panel_sha256=source_panel_sha256,
    )
    output_path = write_regional_signals_output(rows, output_dir)
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            _regional_signals_provenance_record(
                rows=rows,
                regional_lyme_path=regional_lyme_path,
                output_path=output_path,
                output_dir=output_dir,
                manifest_path=resolved_manifest_path,
            )
        ],
        manifest_path=resolved_manifest_path,
    )
    typer.echo(
        f"Wrote {len(rows)} Mid-Atlantic regional signal row(s) to {output_path}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("regional-hotspots")
def regional_hotspots(
    regional_lyme_path: Path = typer.Option(
        Path("build/etl/regional-lyme/midatlantic_lyme_county_year.csv"),
        help="Input Mid-Atlantic Lyme county-year panel.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-hotspots"),
        help="Output directory for Mid-Atlantic hotspot diagnostic artifacts.",
    ),
) -> None:
    if not regional_lyme_path.exists():
        raise typer.BadParameter(f"Regional Lyme panel not found: {regional_lyme_path}")

    source_panel_sha256 = compute_sha256(regional_lyme_path)
    result = build_midatlantic_hotspot_diagnostics(
        regional_lyme_path,
        source_panel_sha256=source_panel_sha256,
    )
    outputs = write_regional_hotspot_outputs(result, output_dir)
    typer.echo(
        f"Wrote {len(result.county_year_rows)} Mid-Atlantic hotspot county-year "
        f"row(s) to {outputs.county_year_path}"
    )
    typer.echo(
        f"Wrote {len(result.summary_rows)} Mid-Atlantic hotspot summary row(s) to "
        f"{outputs.summary_path}"
    )


@etl_app.command("regional-incidence")
def regional_incidence(
    regional_lyme_path: Path = typer.Option(
        Path("build/etl/regional-lyme/midatlantic_lyme_county_year.csv"),
        help="Input Mid-Atlantic Lyme county-year panel.",
    ),
    regional_population_path: Path = typer.Option(
        Path("build/etl/regional-population/midatlantic_county_population_year.csv"),
        help="Input Mid-Atlantic county-year population denominator panel.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-incidence"),
        help="Output directory for Mid-Atlantic incidence diagnostic artifacts.",
    ),
) -> None:
    if not regional_lyme_path.exists():
        raise typer.BadParameter(f"Regional Lyme panel not found: {regional_lyme_path}")
    if not regional_population_path.exists():
        raise typer.BadParameter(
            f"Regional population panel not found: {regional_population_path}"
        )

    result = build_midatlantic_incidence_panel(
        regional_lyme_path=regional_lyme_path,
        regional_population_path=regional_population_path,
        lyme_panel_sha256=compute_sha256(regional_lyme_path),
        population_panel_sha256=compute_sha256(regional_population_path),
    )
    outputs = write_regional_incidence_outputs(result, output_dir)
    typer.echo(
        f"Wrote {len(result.county_year_rows)} Mid-Atlantic incidence county-year "
        f"row(s) to {outputs.county_year_path}"
    )
    typer.echo(
        f"Wrote {len(result.summary_rows)} Mid-Atlantic incidence summary row(s) to "
        f"{outputs.summary_path}"
    )


@etl_app.command("regional-outcome-stress")
def regional_outcome_stress(
    regional_lyme_path: Path = typer.Option(
        Path("build/etl/regional-lyme/midatlantic_lyme_county_year.csv"),
        help="Input Mid-Atlantic Lyme county-year panel.",
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
        3,
        help="Minimum prior county years required for outcome stress tests.",
    ),
    lookback_years: int = typer.Option(
        3,
        help="Number of prior years used to estimate capacity shares.",
    ),
    share_prior_strength: float = typer.Option(
        10.0,
        help="Pseudo-case strength for empirical-Bayes county share shrinkage.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-outcome-stress"),
        help="Output directory for regional outcome stress artifacts.",
    ),
) -> None:
    if not regional_lyme_path.exists():
        raise typer.BadParameter(f"Regional Lyme panel not found: {regional_lyme_path}")
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if lookback_years < min_train_years:
        raise typer.BadParameter(
            "lookback-years must be greater than or equal to min-train-years"
        )
    if not math.isfinite(share_prior_strength) or share_prior_strength < 0:
        raise typer.BadParameter(
            "share-prior-strength must be finite and non-negative"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = build_regional_outcome_stress(
            regional_lyme_path=regional_lyme_path,
            start_year=start_year,
            end_year=end_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
            share_prior_strength=share_prior_strength,
        )
    except RegionalOutcomeStressInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_regional_outcome_stress_outputs(result, output_dir)
    typer.echo(f"Wrote 1 regional outcome stress run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} regional outcome stress prediction row(s) to "
        f"{outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} regional outcome stress metric row(s) to "
        f"{outputs.metrics_path}"
    )


@etl_app.command("regional-incidence-stress")
def regional_incidence_stress(
    regional_incidence_path: Path = typer.Option(
        Path("build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"),
        help="Input Mid-Atlantic Lyme incidence county-year panel.",
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
        3,
        help="Minimum prior county years required for incidence stress tests.",
    ),
    lookback_years: int = typer.Option(
        3,
        help="Number of prior years used to estimate incidence baselines.",
    ),
    shrinkage_strength: float = typer.Option(
        5.0,
        help="Pseudo-year strength for empirical-Bayes incidence shrinkage.",
    ),
    random_forest_n_estimators: int = typer.Option(
        REGIONAL_RF_N_ESTIMATORS,
        help="Tree count for the regional random forest incidence research lane.",
    ),
    random_forest_min_samples_leaf: int = typer.Option(
        REGIONAL_RF_MIN_SAMPLES_LEAF,
        help="Minimum leaf size for the regional random forest incidence lane.",
    ),
    random_forest_max_features: str = typer.Option(
        REGIONAL_RF_MAX_FEATURES,
        help="Max-feature strategy for the regional random forest incidence lane.",
    ),
    random_forest_random_state: int = typer.Option(
        REGIONAL_RF_RANDOM_STATE,
        help="Random seed for the regional random forest incidence lane.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-incidence-stress"),
        help="Output directory for regional incidence stress artifacts.",
    ),
) -> None:
    if not regional_incidence_path.exists():
        raise typer.BadParameter(
            f"Regional incidence panel not found: {regional_incidence_path}"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if lookback_years < min_train_years:
        raise typer.BadParameter(
            "lookback-years must be greater than or equal to min-train-years"
        )
    if not math.isfinite(shrinkage_strength) or shrinkage_strength < 0:
        raise typer.BadParameter(
            "shrinkage-strength must be finite and non-negative"
        )
    if random_forest_n_estimators < 1:
        raise typer.BadParameter("random-forest-n-estimators must be at least 1")
    if random_forest_min_samples_leaf < 1:
        raise typer.BadParameter(
            "random-forest-min-samples-leaf must be at least 1"
        )
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = build_regional_incidence_stress(
            regional_incidence_path=regional_incidence_path,
            start_year=start_year,
            end_year=end_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
            shrinkage_strength=shrinkage_strength,
            random_forest_n_estimators=random_forest_n_estimators,
            random_forest_min_samples_leaf=random_forest_min_samples_leaf,
            random_forest_max_features=random_forest_max_features,
            random_forest_random_state=random_forest_random_state,
        )
    except RegionalIncidenceStressInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_regional_incidence_stress_outputs(result, output_dir)
    typer.echo(f"Wrote 1 regional incidence stress run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} regional incidence stress prediction row(s) to "
        f"{outputs.predictions_path}"
    )
    typer.echo(
        f"Wrote {len(result.metrics)} regional incidence stress metric row(s) to "
        f"{outputs.metrics_path}"
    )


@etl_app.command("regional-annual-forecast")
def regional_annual_forecast(
    regional_incidence_path: Path = typer.Option(
        Path("build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"),
        help="Input Mid-Atlantic Lyme incidence county-year panel.",
    ),
    population_path: Path = typer.Option(
        Path("build/etl/regional-population/midatlantic_county_population_year.csv"),
        "--regional-population-path",
        "--population-path",
        help="Mid-Atlantic county-year population panel containing the target year.",
    ),
    target_year: int = typer.Option(
        2026,
        help="Future regional forecast year to score.",
    ),
    forecast_origin_year: int | None = typer.Option(
        None,
        help=(
            "Latest observed regional outcome year allowed in training. "
            "Defaults to the latest incidence year in the input."
        ),
    ),
    min_train_years: int = typer.Option(
        3,
        help="Minimum prior county years required for regional forecast.",
    ),
    lookback_years: int = typer.Option(
        3,
        help="Number of origin-era years used to estimate forecast baselines.",
    ),
    shrinkage_strength: float = typer.Option(
        5.0,
        help="Pseudo-year strength for empirical-Bayes incidence shrinkage.",
    ),
    as_of_date: str = typer.Option(
        "unspecified",
        help="Forecast artifact as-of date for provenance.",
    ),
    data_cutoff_date: str = typer.Option(
        "unspecified",
        help="Latest source data cutoff date represented by this forecast.",
    ),
    source_vintage: str | None = typer.Option(
        None,
        help="Source vintage label. Defaults to the regional incidence SHA-256.",
    ),
    update_mode: str = typer.Option(
        "pre_update",
        help=(
            "Forecast update mode label: pre_update or post_observed_outcome."
        ),
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-annual-forecast"),
        help="Output directory for regional annual forecast artifacts.",
    ),
) -> None:
    if not regional_incidence_path.exists():
        raise typer.BadParameter(
            f"Regional incidence panel not found: {regional_incidence_path}"
        )
    if not population_path.exists():
        raise typer.BadParameter(f"Population panel not found: {population_path}")
    if forecast_origin_year is not None and target_year <= forecast_origin_year:
        raise typer.BadParameter(
            "target-year must be greater than forecast-origin-year"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if lookback_years < min_train_years:
        raise typer.BadParameter(
            "lookback-years must be greater than or equal to min-train-years"
        )
    if not math.isfinite(shrinkage_strength) or shrinkage_strength < 0:
        raise typer.BadParameter(
            "shrinkage-strength must be finite and non-negative"
        )
    _validate_forecast_update_mode(update_mode)

    try:
        result = build_regional_annual_forecast(
            regional_incidence_path=regional_incidence_path,
            population_path=population_path,
            target_year=target_year,
            forecast_origin_year=forecast_origin_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
            shrinkage_strength=shrinkage_strength,
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            source_vintage=source_vintage,
            update_mode=update_mode,
        )
    except RegionalAnnualForecastInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_regional_annual_forecast_outputs(result, output_dir)
    typer.echo(f"Wrote 1 regional annual forecast run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.predictions)} regional annual forecast prediction row(s) "
        f"to {outputs.predictions_path}"
    )


@etl_app.command("regional-forecast-capacity")
def regional_forecast_capacity(
    regional_incidence_path: Path = typer.Option(
        Path("build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"),
        help="Input Mid-Atlantic Lyme incidence county-year panel.",
    ),
    forecast_predictions_path: Path = typer.Option(
        Path("build/etl/regional-annual-forecast/regional_annual_forecast_predictions.csv"),
        help="Input regional annual forecast predictions CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-forecast-capacity"),
        help="Output directory for regional forecast capacity artifacts.",
    ),
) -> None:
    if not regional_incidence_path.exists():
        raise typer.BadParameter(
            f"Regional incidence panel not found: {regional_incidence_path}"
        )
    if not forecast_predictions_path.exists():
        raise typer.BadParameter(
            f"Regional forecast predictions not found: {forecast_predictions_path}"
        )

    try:
        result = build_regional_forecast_capacity(
            regional_incidence_path=regional_incidence_path,
            forecast_predictions_path=forecast_predictions_path,
        )
    except RegionalForecastCapacityInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_regional_forecast_capacity_outputs(result, output_dir)
    typer.echo(
        f"Wrote 1 regional forecast capacity run row(s) to {outputs.runs_path}"
    )
    typer.echo(
        f"Wrote {len(result.capacity_summary)} regional forecast capacity row(s) "
        f"to {outputs.capacity_summary_path}"
    )


@etl_app.command("regional-incidence-clusters")
def regional_incidence_clusters(
    regional_incidence_path: Path = typer.Option(
        Path("build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"),
        help="Input Mid-Atlantic Lyme incidence county-year panel.",
    ),
    start_year: int = typer.Option(
        2007,
        help="First held-out year for forecast-safe cluster assignment.",
    ),
    end_year: int | None = typer.Option(
        None,
        help="Last held-out year to assign. Defaults to max year in input.",
    ),
    min_train_years: int = typer.Option(
        3,
        help="Minimum prior county years required for cluster assignment.",
    ),
    lookback_years: int = typer.Option(
        5,
        help="Number of prior years used for cluster assignment.",
    ),
    n_clusters: int = typer.Option(
        4,
        help="Requested number of prior-incidence clusters per held-out year.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/regional-incidence-clusters"),
        help="Output directory for regional incidence cluster artifacts.",
    ),
) -> None:
    if not regional_incidence_path.exists():
        raise typer.BadParameter(
            f"Regional incidence panel not found: {regional_incidence_path}"
        )
    if min_train_years < 1:
        raise typer.BadParameter("min-train-years must be at least 1")
    if lookback_years < min_train_years:
        raise typer.BadParameter(
            "lookback-years must be greater than or equal to min-train-years"
        )
    if n_clusters < 2:
        raise typer.BadParameter("n-clusters must be at least 2")
    if end_year is not None and start_year > end_year:
        raise typer.BadParameter("start-year must be less than or equal to end-year")

    try:
        result = build_regional_incidence_clusters(
            regional_incidence_path=regional_incidence_path,
            start_year=start_year,
            end_year=end_year,
            min_train_years=min_train_years,
            lookback_years=lookback_years,
            n_clusters=n_clusters,
        )
    except RegionalIncidenceClusterInputError as exc:
        raise typer.BadParameter(str(exc)) from exc
    outputs = write_regional_incidence_cluster_outputs(result, output_dir)
    typer.echo(f"Wrote 1 regional incidence cluster run row(s) to {outputs.runs_path}")
    typer.echo(
        f"Wrote {len(result.county_year_rows)} regional incidence cluster "
        f"county-year row(s) to {outputs.county_year_path}"
    )
    typer.echo(
        f"Wrote {len(result.summary_rows)} regional incidence cluster summary row(s) "
        f"to {outputs.summary_path}"
    )


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
    ),
) -> None:
    source_parsers = {
        "cdc_lyme_public_1992_2007": parse_cdc_lyme_public_use,
        "cdc_lyme_public_2008_2021": parse_cdc_lyme_public_use,
        "cdc_lyme_public_2022_2023": parse_cdc_lyme_public_use,
        "cdc_lyme_county_dashboard_2023": parse_cdc_county_dashboard,
        "cdc_lyme_county_geodata_2000_2021": parse_cdc_lyme_geodata,
    }
    for metadata in LYME_OUTCOME_SOURCE_METADATA:
        source_path = raw_dir / str(metadata["filename"])
        if not source_path.exists():
            raise typer.BadParameter(f"Lyme source file not found: {source_path}")

    rows = []
    rows_by_source = {}
    source_paths_by_id = {}
    active_metadata = list(LYME_OUTCOME_SOURCE_METADATA)
    for metadata in LYME_OUTCOME_SOURCE_METADATA:
        source_id = str(metadata["source_id"])
        source_path = raw_dir / str(metadata["filename"])
        source_rows = list(source_parsers[source_id](source_path, source_id=source_id))
        rows_by_source[source_id] = source_rows
        source_paths_by_id[source_id] = source_path
        rows.extend(source_rows)
    mdh_pdf_path = raw_dir / str(LYME_MDH_SOURCE_METADATA["filename"])
    if mdh_pdf_path.exists():
        source_id = str(LYME_MDH_SOURCE_METADATA["source_id"])
        mdh_rows = [
            row
            for row in parse_mdh_lyme_pdf(mdh_pdf_path, source_id=source_id)
            if row.year == 2024
        ]
        rows_by_source[source_id] = mdh_rows
        source_paths_by_id[source_id] = mdh_pdf_path
        active_metadata.append(LYME_MDH_SOURCE_METADATA)
        rows.extend(mdh_rows)

    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    output = write_reconciled_lyme_outputs(rows, output_dir)
    provenance_output = write_acquisition_provenance_manifest(
        _lyme_outcome_provenance_records(
            source_metadata=active_metadata,
            rows_by_source=rows_by_source,
            source_paths_by_id=source_paths_by_id,
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=resolved_manifest_path,
            output_path=output,
        ),
        manifest_path=resolved_manifest_path,
    )
    with output.open(newline="", encoding="utf-8") as handle:
        row_count = sum(1 for _ in csv.DictReader(handle))
    typer.echo(
        f"Wrote {row_count} reconciled Lyme county-year outcome row(s) to {output}"
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for raw-source acquisition provenance.",
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_records = _mast_acorn_provenance_records(
        sources=MARYLAND_DNR_MAST_REPORT_URLS,
        summaries=summaries,
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=resolved_manifest_path,
        rows_output=rows_output,
        summary_output=summary_output,
        parser=parser,
    )
    typer.echo(f"Wrote {len(rows)} mast/acorn row(s) to {rows_output}")
    typer.echo(
        f"Wrote {len(summaries)} mast/acorn extraction summary row(s) "
        f"to {summary_output}"
    )
    if manual_observations_path is not None:
        manual_rows = read_manual_mast_observations(manual_observations_path)
        manual_output = write_manual_mast_observations_output(manual_rows, output_dir)
        provenance_records.append(
            _manual_mast_observation_provenance_record(
                manual_observations_path=manual_observations_path,
                manual_output=manual_output,
                row_count=len(manual_rows),
                raw_dir=raw_dir,
                output_dir=output_dir,
                manifest_path=resolved_manifest_path,
                parser=parser,
            )
        )
        typer.echo(
            f"Wrote {len(manual_rows)} manual mast observation row(s) to "
            f"{manual_output}"
        )
    provenance_output = write_acquisition_provenance_manifest(
        provenance_records,
        manifest_path=resolved_manifest_path,
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    if annual_report_parser not in {"pypdfium", "docling"}:
        raise typer.BadParameter("annual-report-parser must be pypdfium or docling")
    county_references = read_county_reference_output(county_reference_path)
    source_urls = url or MARYLAND_DNR_DEER_HARVEST_URLS
    rows = []
    provenance_records = []
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    acquisition_command = _deer_harvest_acquisition_command(
        county_reference_path=county_reference_path,
        output_dir=output_dir,
        source_urls=source_urls,
        include_annual_report_pdfs=include_annual_report_pdfs,
        skip_news_html=skip_news_html,
        annual_report_parser=annual_report_parser,
        manifest_path=resolved_manifest_path,
    )
    if not skip_news_html:
        for source_url in source_urls:
            source_id = source_id_from_deer_harvest_url(source_url)
            html = fetch_maryland_dnr_deer_harvest_html(source_url)
            source_rows = parse_maryland_dnr_deer_harvest_html(
                html,
                source_url=source_url,
                source_id=source_id,
            )
            rows.extend(source_rows)
            provenance_records.append(
                _deer_harvest_html_provenance_record(
                    source_url=source_url,
                    source_id=source_id,
                    acquisition_command=acquisition_command,
                    output_path=output_dir / "maryland_dnr_deer_harvest.csv",
                    row_count=len(source_rows),
                )
            )
    if include_annual_report_pdfs:
        for source in MARYLAND_DNR_DEER_ANNUAL_REPORT_URLS:
            source_rows = parse_maryland_dnr_deer_harvest_pdf(
                source.url,
                source_url=source.url,
                source_id=source.source_id,
                parser=annual_report_parser,
            )
            rows.extend(source_rows)
            provenance_records.append(
                _deer_harvest_pdf_provenance_record(
                    source_url=source.url,
                    source_id=source.source_id,
                    acquisition_command=acquisition_command,
                    output_path=output_dir / "maryland_dnr_deer_harvest.csv",
                    row_count=len(source_rows),
                    annual_report_parser=annual_report_parser,
                )
            )
    rows = dedupe_deer_harvest_rows(
        attach_deer_harvest_density(rows, county_references)
    )
    output = write_deer_harvest_output(rows, output_dir)
    provenance_output = write_acquisition_provenance_manifest(
        provenance_records,
        manifest_path=resolved_manifest_path,
    )
    typer.echo(f"Wrote {len(rows)} deer harvest row(s) to {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("weather-backfill-open-meteo")
def weather_backfill_open_meteo(
    county_fips: str = typer.Option(..., help="Maryland county FIPS code."),
    start_date: str = typer.Option(..., help="Start date for archive pull."),
    end_date: str = typer.Option(..., help="End date for archive pull."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    dry_run: bool = typer.Option(False, help="Print URL without fetching data."),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            _open_meteo_provenance_record(
                county_fips=location.county_fips,
                county_name=location.county_name,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                source_urls=[url],
                acquisition_command=_open_meteo_single_acquisition_command(
                    county_fips=county_fips,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    manifest_path=resolved_manifest_path,
                ),
                output_paths=[daily_output, weekly_output, monthly_output],
                row_count=len(rows),
                chunk_count=1,
                weather_model="open_meteo_archive",
            )
        ],
        manifest_path=resolved_manifest_path,
        append=True,
    )
    typer.echo(f"Wrote {daily_output}")
    typer.echo(f"Wrote {weekly_output}")
    typer.echo(f"Wrote {monthly_output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


@etl_app.command("weather-backfill-open-meteo-maryland")
def weather_backfill_open_meteo_maryland(
    start_date: str = typer.Option(..., help="Daily weather start date."),
    end_date: str = typer.Option(..., help="Daily weather end date."),
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    ),
    county_fips: list[str] | None = typer.Option(
        None,
        "--county-fips",
        help="Optional Maryland county FIPS subset. Repeat for multiple counties.",
    ),
    max_chunk_days: int = typer.Option(
        366, help="Maximum inclusive days per Open-Meteo archive request."
    ),
    weather_model: str = typer.Option(
        "open_meteo_archive", help="Optional Open-Meteo archive model selector."
    ),
    max_attempts: int = typer.Option(3, help="Maximum attempts per archive request."),
    retry_sleep_seconds: float = typer.Option(
        1.0, help="Base sleep seconds between Open-Meteo request retries."
    ),
    inter_chunk_sleep_seconds: float = typer.Option(
        0.0, help="Sleep seconds between chunks for the same county."
    ),
    inter_county_sleep_seconds: float = typer.Option(
        0.0, help="Sleep seconds between county backfills."
    ),
    fail_fast: bool = typer.Option(False, help="Stop at the first county failure."),
    allow_partial: bool = typer.Option(
        False, help="Exit successfully even when one or more counties fail."
    ),
    dry_run: bool = typer.Option(False, help="Print planned queries without fetching data."),
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
) -> None:
    parsed_start_date = _parse_iso_date(start_date, "start-date")
    parsed_end_date = _parse_iso_date(end_date, "end-date")
    try:
        county_fips_values = resolve_maryland_open_meteo_county_fips(county_fips)
        validate_open_meteo_backfill_args(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            max_chunk_days=max_chunk_days,
        )
    except OpenMeteoBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    plans = plan_open_meteo_archive_requests(
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        county_fips_values=county_fips_values,
        max_chunk_days=max_chunk_days,
        weather_model=weather_model,
    )
    if dry_run:
        typer.echo(f"Planned {len(plans)} Open-Meteo archive request(s)")
        for plan in plans:
            typer.echo(
                f"{plan.county_fips} {plan.chunk_start_date.isoformat()} "
                f"to {plan.chunk_end_date.isoformat()}: {plan.url}"
            )
        return

    try:
        result = run_open_meteo_maryland_backfill(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            output_dir=output_dir,
            county_fips_values=county_fips_values,
            max_chunk_days=max_chunk_days,
            weather_model=weather_model,
            continue_on_error=not fail_fast,
            max_attempts=max_attempts,
            sleep_seconds=retry_sleep_seconds,
            inter_chunk_sleep_seconds=inter_chunk_sleep_seconds,
            inter_county_sleep_seconds=inter_county_sleep_seconds,
        )
    except OpenMeteoBackfillError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Completed {result.success_count}/{result.county_count} "
        "Maryland Open-Meteo county backfill(s)"
    )
    typer.echo(f"Fetched {result.chunk_count} archive request chunk(s)")
    typer.echo(f"Wrote {result.daily_observation_count} daily observation row(s)")
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _open_meteo_maryland_provenance_records(
            plans=plans,
            county_results=result.county_results,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            acquisition_command=_open_meteo_maryland_acquisition_command(
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                county_fips_values=county_fips_values,
                max_chunk_days=max_chunk_days,
                weather_model=weather_model,
                max_attempts=max_attempts,
                retry_sleep_seconds=retry_sleep_seconds,
                inter_chunk_sleep_seconds=inter_chunk_sleep_seconds,
                inter_county_sleep_seconds=inter_county_sleep_seconds,
                fail_fast=fail_fast,
                allow_partial=allow_partial,
                manifest_path=resolved_manifest_path,
            ),
            weather_model=weather_model,
        ),
        manifest_path=resolved_manifest_path,
        append=True,
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")
    if result.failure_count:
        typer.echo(f"Failures: {result.failure_count}")
        for failure in result.failures:
            typer.echo(f"{failure.county_fips}: {failure.error}")
        if not allow_partial:
            raise typer.Exit(1)


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            _noaa_provenance_record(
                source_id=(
                    f"noaa_cdo_ghcnd_stations_{county_fips.zfill(5)}_"
                    f"{_date_slug(parsed_start_date)}_{_date_slug(parsed_end_date)}"
                ),
                source_name="NOAA CDO GHCND station discovery",
                source_url=url,
                acquisition_command=_noaa_stations_acquisition_command(
                    county_fips=county_fips,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    min_data_coverage=min_data_coverage,
                    max_end_lag_days=max_end_lag_days,
                    manifest_path=resolved_manifest_path,
                ),
                request_description=(
                    "NOAA CDO GHCND station discovery request for "
                    f"Maryland county FIPS {county_fips.zfill(5)}."
                ),
                output_path=output,
                row_count=len(selected),
                parser_method=(
                    "fetch_noaa_stations;parse_noaa_station_response;"
                    "select_long_coverage_stations"
                ),
            )
        ],
        manifest_path=resolved_manifest_path,
        append=True,
    )
    typer.echo(f"Wrote {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        [
            _noaa_provenance_record(
                source_id=(
                    f"noaa_cdo_ghcnd_daily_{county_fips.zfill(5)}_"
                    f"{_source_id_slug(station_id)}_"
                    f"{_date_slug(parsed_start_date)}_{_date_slug(parsed_end_date)}"
                ),
                source_name="NOAA CDO GHCND daily observations",
                source_url=url,
                acquisition_command=_noaa_daily_acquisition_command(
                    county_fips=county_fips,
                    station_id=station_id,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                    manifest_path=resolved_manifest_path,
                ),
                request_description=(
                    "NOAA CDO daily observations request for "
                    f"{station_id} mapped to Maryland county FIPS "
                    f"{county_fips.zfill(5)}."
                ),
                output_path=output,
                row_count=len(rows),
                parser_method=(
                    "fetch_noaa_daily_observations;parse_noaa_daily_data_response"
                ),
            )
        ],
        manifest_path=resolved_manifest_path,
        append=True,
    )
    typer.echo(f"Wrote {output}")
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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


@etl_app.command("open-meteo-weather-features")
def open_meteo_weather_features(
    input_path: Path = typer.Option(
        Path("build/etl/open-meteo/weather_daily.csv"),
        help="Input Open-Meteo weather_daily.csv path.",
    ),
    output_dir: Path = typer.Option(
        Path("build/etl/open-meteo"), help="Output directory for ETL artifacts."
    ),
) -> None:
    rows = read_open_meteo_weather_daily_rows(input_path)
    weekly_features = add_trailing_weekly_anomalies(
        compute_weekly_weather_features(rows)
    )
    weekly_output = write_weather_features_weekly_output(
        weekly_features, output_dir, append=False
    )
    monthly_features = add_trailing_monthly_anomalies(
        compute_monthly_weather_features(rows)
    )
    monthly_output = write_weather_features_monthly_output(
        monthly_features, output_dir, append=False
    )
    typer.echo(
        f"Wrote {len(weekly_features)} Open-Meteo weekly feature row(s) to "
        f"{weekly_output}"
    )
    typer.echo(
        f"Wrote {len(monthly_features)} Open-Meteo monthly feature row(s) to "
        f"{monthly_output}"
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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
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
    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_output = write_acquisition_provenance_manifest(
        _noaa_backfill_provenance_records(
            result=result,
            source_id_prefix="county_backfill",
            acquisition_command=_noaa_backfill_county_acquisition_command(
                county_fips=county_fips,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                station_limit=station_limit,
                min_data_coverage=min_data_coverage,
                max_end_lag_days=max_end_lag_days,
                manifest_path=resolved_manifest_path,
            ),
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        ),
        manifest_path=resolved_manifest_path,
        append=True,
    )
    typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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
    provenance_manifest_path: Path | None = typer.Option(
        None,
        help="Output CSV manifest for API acquisition provenance.",
    ),
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

    resolved_manifest_path = (
        provenance_manifest_path or output_dir / "acquisition_provenance.csv"
    )
    provenance_records = [
        record
        for county_result in result.county_results
        for record in _noaa_backfill_provenance_records(
            result=county_result,
            source_id_prefix="maryland_backfill",
            acquisition_command=_noaa_backfill_maryland_acquisition_command(
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                county_fips_values=county_fips_values,
                station_limit=station_limit,
                min_data_coverage=min_data_coverage,
                max_end_lag_days=max_end_lag_days,
                fail_fast=fail_fast,
                allow_partial=allow_partial,
                nearest_station_fallback=nearest_station_fallback,
                manifest_path=resolved_manifest_path,
            ),
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        )
    ]
    if provenance_records:
        provenance_output = write_acquisition_provenance_manifest(
            provenance_records,
            manifest_path=resolved_manifest_path,
            append=True,
        )
        typer.echo(f"Wrote acquisition provenance manifest to {provenance_output}")


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


def _lyme_outcome_provenance_records(
    *,
    source_metadata: list[dict[str, str]],
    rows_by_source: dict[str, list[object]],
    source_paths_by_id: dict[str, Path],
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    output_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _lyme_outcomes_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    records = []
    for metadata in source_metadata:
        source_id = metadata["source_id"]
        source_path = source_paths_by_id[source_id]
        is_mdh_pdf = source_id == LYME_MDH_SOURCE_METADATA["source_id"]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=metadata["source_name"],
                source_url=metadata["source_url"],
                citation_url=metadata["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read an ignored local raw Lyme outcome source file, parse "
                    "Maryland county-year rows, and reconcile source vintages "
                    "into the canonical outcome artifact."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=_lyme_outcome_request_description(
                    source_path=source_path,
                    is_mdh_pdf=is_mdh_pdf,
                ),
                derived_artifact_paths=[source_path, output_path],
                derived_artifact_path_labels=[source_path.name, output_path.name],
                row_count=len(rows_by_source.get(source_id, [])),
                parser_method=metadata["parser_method"],
                extraction_quality="accepted",
                access_notes=(
                    "Local ignored raw file from public CDC/MDH source; no "
                    "secret or credential required."
                ),
                modeling_caveats=metadata["modeling_caveats"],
            )
        )
    return records


def _lyme_outcome_request_description(
    *,
    source_path: Path,
    is_mdh_pdf: bool,
) -> str:
    if is_mdh_pdf:
        return (
            f"Read local raw Lyme PDF {source_path.name} from --raw-dir; "
            "2024 rows selected from the 2013-2024 PDF before reconciliation."
        )
    return (
        f"Read local raw Lyme CSV {source_path.name} from --raw-dir; source "
        "rows contributed to reconciliation are counted before priority dedupe."
    )


def _lyme_outcomes_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "lyme-outcomes",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _parse_lyme_aggregate_sources(
    source_paths_by_id: dict[str, Path],
) -> dict[str, list[object]]:
    parsed_values = {}
    for metadata in LYME_AGGREGATE_SOURCE_METADATA:
        source_id = metadata["source_id"]
        parser_function = (
            parse_cdc_lyme_aggregate_cases
            if metadata["value_type"] == "cases"
            else parse_cdc_lyme_aggregate_rates
        )
        parsed_values[source_id] = parser_function(
            source_paths_by_id[source_id],
            source_id=source_id,
            geography_type=metadata["geography_type"],
        )
    return parsed_values


def _lyme_aggregate_provenance_records(
    *,
    source_metadata: list[dict[str, str]],
    parsed_values_by_source: dict[str, list[object]],
    source_paths_by_id: dict[str, Path],
    outputs: LymeAggregateOutputPaths,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    output_paths_by_kind = {
        "state": outputs.state_path,
        "region": outputs.region_path,
        "national": outputs.national_path,
    }
    command = _lyme_aggregate_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    records = []
    for metadata in source_metadata:
        source_id = metadata["source_id"]
        source_path = source_paths_by_id[source_id]
        output_path = output_paths_by_kind[metadata["output_kind"]]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=metadata["source_name"],
                source_url=metadata["source_url"],
                citation_url=metadata["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read an ignored local CDC Lyme dashboard aggregate export, "
                    "normalize state/region/national annual case or incidence "
                    "values, and merge cases with rates into validation-anchor "
                    "artifacts."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    f"Read local raw CDC Lyme aggregate CSV {source_path.name} "
                    f"for {metadata['geography_type']} {metadata['value_type']}."
                ),
                derived_artifact_paths=[source_path, output_path],
                derived_artifact_path_labels=[source_path.name, output_path.name],
                row_count=len(parsed_values_by_source.get(source_id, [])),
                parser_method=metadata["parser_method"],
                extraction_quality="accepted",
                access_notes=(
                    "Local ignored raw export from public CDC Lyme surveillance "
                    "dashboard source; no secret or credential required."
                ),
                modeling_caveats=(
                    "Aggregate validation/capacity anchor only; no county "
                    "detail, no direct human exposure signal, and reported "
                    "cases are not stable true incidence across surveillance "
                    "regime changes."
                ),
            )
        )
    return records


def _lyme_aggregate_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "lyme-aggregate-validation",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _wv_vectorborne_provenance_records(
    *,
    rows_by_source: dict[str, list[WestVirginiaVectorborneStateSummary]],
    source_paths_by_id: dict[str, Path],
    output_path: Path,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _wv_vectorborne_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    metadata_by_source = {
        str(metadata["source_id"]): metadata
        for metadata in WV_VECTORBORNE_SOURCE_METADATA
    }
    records = []
    for source_id in sorted(rows_by_source):
        metadata = metadata_by_source[source_id]
        source_path = source_paths_by_id[source_id]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=str(metadata["source_name"]),
                source_url=str(metadata["source_url"]),
                citation_url=str(metadata["citation_url"]),
                acquisition_command=command,
                acquisition_procedure=(
                    "Read the ignored local West Virginia OEPS vectorborne "
                    "disease summary PDF, extract text from Table 3, and write "
                    "state aggregate validation rows for provisional "
                    "confirmed/probable tickborne disease counts."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    "Read local raw West Virginia OEPS vectorborne summary PDF "
                    f"{source_path.name}."
                ),
                derived_artifact_paths=[source_path, output_path],
                derived_artifact_path_labels=[source_path.name, output_path.name],
                row_count=len(rows_by_source[source_id]),
                parser_method=str(metadata["parser_method"]),
                extraction_quality="accepted_state_aggregate_only",
                access_notes=(
                    "Public West Virginia OEPS PDF reached from the official "
                    "Arboviral Diseases Vectorborne Disease Summary page; no "
                    "secret or credential required. Raw PDF remains in ignored "
                    "storage."
                ),
                modeling_caveats=(
                    "West Virginia state aggregate validation/context only; "
                    "provisional YTD counts, no county rows, county maps are "
                    "not digitized, and reported cases are not stable true "
                    "incidence."
                ),
            )
        )
    return records


def _wv_vectorborne_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "wv-vectorborne-summary",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _mass_dph_syndromic_ed_provenance_records(
    *,
    rows_by_source: dict[str, list[MassDphSyndromicEdCountySummary]],
    source_paths_by_id: dict[str, Path],
    output_path: Path,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _mass_dph_syndromic_ed_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    metadata_by_source = {
        str(metadata["source_id"]): metadata
        for metadata in MASS_DPH_SYNDROMIC_ED_SOURCE_METADATA
    }
    records = []
    for source_id in sorted(rows_by_source):
        metadata = metadata_by_source[source_id]
        source_path = source_paths_by_id[source_id]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=str(metadata["source_name"]),
                source_url=str(metadata["source_url"]),
                citation_url=str(metadata["citation_url"]),
                acquisition_command=command,
                acquisition_procedure=(
                    "Read the ignored local Massachusetts DPH DOCX report, "
                    "extract Table 1 county residence emergency-department "
                    "tick-borne disease visit counts and rates, and write a "
                    "syndromic exposure/diagnosis sidecar."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    "Read local raw Massachusetts DPH syndromic surveillance "
                    f"DOCX report {source_path.name}."
                ),
                derived_artifact_paths=[source_path, output_path],
                derived_artifact_path_labels=[source_path.name, output_path.name],
                row_count=len(rows_by_source[source_id]),
                parser_method=str(metadata["parser_method"]),
                extraction_quality="accepted_docx_table1_county_residence_rows",
                access_notes=(
                    "Public Massachusetts DPH DOCX report reached from the "
                    "official Monthly Tick-borne Disease Reports page; no "
                    "secret or credential required. Raw DOCX remains in "
                    "ignored storage."
                ),
                modeling_caveats=(
                    "Massachusetts DPH syndromic ED sidecar only; ED visits "
                    "are exposure/surveillance context, not Lyme incidence, "
                    "not tick-bite counts, not disease-specific, not a "
                    "confirmed disease truth label, not public-default, and "
                    "not model input in this slice."
                ),
            )
        )
    return records


def _mass_dph_syndromic_ed_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "mass-dph-syndromic-ed",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _nj_doh_reportable_tickborne_provenance_records(
    *,
    rows: list[NewJerseyReportableTickborneCountyYear],
    stats_pdf_path: Path,
    technical_notes_path: Path,
    output_path: Path,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    metadata = NJ_DOH_REPORTABLE_TICKBORNE_METADATA
    return [
        AcquisitionProvenanceRecord(
            source_id=str(metadata["source_id"]),
            source_name=str(metadata["source_name"]),
            source_url=str(metadata["source_url"]),
            citation_url=str(metadata["citation_url"]),
            acquisition_command=_nj_doh_reportable_tickborne_acquisition_command(
                raw_dir=raw_dir,
                output_dir=output_dir,
                manifest_path=manifest_path,
            ),
            acquisition_procedure=(
                "Read the ignored local New Jersey DOH 2024 Reportable "
                "Communicable Disease Report PDF, keep only the supported "
                "tickborne disease rows for state total and county "
                "jurisdictions, and attach the official 2024 Technical Notes "
                "PDF for surveillance caveats."
            ),
            request_method="LOCAL_FILE_READ",
            request_description=(
                "Read local raw New Jersey DOH reportable disease statistics "
                f"PDF {stats_pdf_path.name} and technical notes PDF "
                f"{technical_notes_path.name}; source URLs are "
                f"{metadata['source_url']} and {metadata['technical_notes_url']}."
            ),
            derived_artifact_paths=[stats_pdf_path, technical_notes_path, output_path],
            derived_artifact_path_labels=[
                stats_pdf_path.name,
                technical_notes_path.name,
                output_path.name,
            ],
            row_count=len(rows),
            parser_method=str(metadata["parser_method"]),
            extraction_quality="accepted_tickborne_reportable_rows_only",
            access_notes=(
                "Public New Jersey DOH PDFs reached from the official "
                "Reportable Disease Statistics page; no secret or credential "
                "required. Raw PDFs remain in ignored storage."
            ),
            modeling_caveats=(
                "New Jersey state-source Northeast extension sidecar only; "
                "reported cases are not stable true incidence, not a "
                "confirmed disease truth label, not public-default, and not "
                "model input in this slice. Technical notes specify 2022 Lyme "
                "laboratory-based surveillance increased expected counts; "
                "2024 anaplasmosis/ehrlichiosis reporting changed; alpha-gal "
                "voluntary reporting may underestimate actual cases; values "
                "less than five need accompanying interpretation."
            ),
        )
    ]


def _nj_doh_reportable_tickborne_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "nj-doh-reportable-tickborne",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _maine_jmmc_tickborne_rates_provenance_records(
    *,
    rows: list[MaineJmmcTickborneCountyRate],
    pdf_path: Path,
    output_path: Path,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    metadata = MAINE_JMMC_TICKBORNE_RATES_METADATA
    return [
        AcquisitionProvenanceRecord(
            source_id=str(metadata["source_id"]),
            source_name=str(metadata["source_name"]),
            source_url=str(metadata["source_url"]),
            citation_url=str(metadata["citation_url"]),
            acquisition_command=_maine_jmmc_tickborne_rates_acquisition_command(
                raw_dir=raw_dir,
                output_dir=output_dir,
                manifest_path=manifest_path,
            ),
            acquisition_procedure=(
                "Read the ignored local Journal of Maine Medical Center PDF, "
                "extract only Table 2 county/state rates of selected "
                "tick-borne diseases per 100,000 persons for 2024, and keep "
                "rates as rates without deriving case counts."
            ),
            request_method="LOCAL_FILE_READ",
            request_description=(
                "Read local raw Maine JMMC review PDF "
                f"{pdf_path.name}; source URL is {metadata['source_url']}; "
                f"DOI is {metadata['doi_url']}; underlying official dashboard "
                f"lead is {metadata['underlying_data_url']}."
            ),
            derived_artifact_paths=[pdf_path, output_path],
            derived_artifact_path_labels=[pdf_path.name, output_path.name],
            row_count=len(rows),
            parser_method=str(metadata["parser_method"]),
            extraction_quality="accepted_table2_county_state_rates_only",
            access_notes=(
                "Open-access Journal of Maine Medical Center article under "
                "CC-BY 4.0; raw PDF remains in ignored storage. The article "
                "cites Maine CDC/Maine Tracking Network surveillance data."
            ),
            modeling_caveats=(
                "Maine external comparator sidecar only; Maine is outside "
                "the active forecast footprint. Values are preliminary rates "
                "only as of January 20, 2025, not county case counts, not a "
                "confirmed disease truth label, not stable true incidence, "
                "not public-default, and not model input in this slice. "
                "Later Maine CDC surveillance reports may revise statewide "
                "counts."
            ),
        )
    ]


def _maine_jmmc_tickborne_rates_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "maine-jmmc-tickborne-rates",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _regional_lyme_provenance_records(
    *,
    metadata: dict[str, str],
    rows: list[RegionalLymeCountyYear],
    source_path: Path,
    pa_rows: list[RegionalLymeCountyYear],
    pa_source_path: Path | None,
    de_validation_rows: list[RegionalLymeCountyYear],
    de_source_path: Path | None,
    de_validation_output_path: Path | None,
    va_rows: list[RegionalLymeCountyYear],
    va_source_path: Path | None,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    output_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _regional_lyme_acquisition_command(
        raw_dir=raw_dir,
        pa_source_path=pa_source_path,
        de_source_path=de_source_path,
        va_source_path=va_source_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    records = [
        AcquisitionProvenanceRecord(
            source_id=metadata["source_id"],
            source_name=metadata["source_name"],
            source_url=metadata["source_url"],
            citation_url=metadata["citation_url"],
            acquisition_command=command,
            acquisition_procedure=(
                "Read an ignored local CDC Lyme county dashboard export, "
                "filter to DE, DC, MD, PA, VA, and WV county-equivalent rows, "
                "and reshape annual wide columns into a regional county-year "
                "outcome panel."
            ),
            request_method="LOCAL_FILE_READ",
            request_description=(
                f"Read local raw CDC Lyme county dashboard CSV {source_path.name} "
                "for the Mid-Atlantic regional expansion outcome panel."
            ),
            derived_artifact_paths=[source_path, output_path],
            derived_artifact_path_labels=[source_path.name, output_path.name],
            row_count=len(rows),
            parser_method=metadata["parser_method"],
            extraction_quality="accepted",
            access_notes=(
                "Local ignored raw export from public CDC Lyme surveillance "
                "dashboard source; no secret or credential required."
            ),
            modeling_caveats=metadata["modeling_caveats"],
        )
    ]
    if pa_source_path is not None:
        records.append(
            AcquisitionProvenanceRecord(
                source_id=REGIONAL_PA_LYME_2024_SOURCE_METADATA["source_id"],
                source_name=REGIONAL_PA_LYME_2024_SOURCE_METADATA["source_name"],
                source_url=REGIONAL_PA_LYME_2024_SOURCE_METADATA["source_url"],
                citation_url=REGIONAL_PA_LYME_2024_SOURCE_METADATA["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read the ignored local Pennsylvania DOH Lyme county "
                    "workbook, extract only 2024 county rows, and append them "
                    "as flagged state-source rows to the regional outcome panel."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    "Read local raw Pennsylvania DOH Lyme workbook "
                    f"{pa_source_path.name} for the 2024 regional state-source "
                    "overlay."
                ),
                derived_artifact_paths=[pa_source_path, output_path],
                derived_artifact_path_labels=[
                    pa_source_path.name,
                    output_path.name,
                ],
                row_count=len(pa_rows),
                parser_method=REGIONAL_PA_LYME_2024_SOURCE_METADATA[
                    "parser_method"
                ],
                extraction_quality="accepted_with_suppression_flags",
                access_notes=(
                    "Public Pennsylvania DOH workbook; no secret or credential "
                    "required. Raw workbook remains in ignored storage."
                ),
                modeling_caveats=REGIONAL_PA_LYME_2024_SOURCE_METADATA[
                    "modeling_caveats"
                ],
            )
        )
    if de_source_path is not None and de_validation_output_path is not None:
        records.append(
            AcquisitionProvenanceRecord(
                source_id=REGIONAL_DE_LYME_SOURCE_METADATA["source_id"],
                source_name=REGIONAL_DE_LYME_SOURCE_METADATA["source_name"],
                source_url=REGIONAL_DE_LYME_SOURCE_METADATA["source_url"],
                citation_url=REGIONAL_DE_LYME_SOURCE_METADATA["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read the ignored local Delaware DHSS Lyme data HTML page, "
                    "extract 2019-2023 county case-count rows, and write them "
                    "to a state-source validation sidecar without appending "
                    "overlapping years to the regional model panel."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    "Read local raw Delaware DHSS Lyme data HTML page "
                    f"{de_source_path.name} for state-source validation."
                ),
                derived_artifact_paths=[de_source_path, de_validation_output_path],
                derived_artifact_path_labels=[
                    de_source_path.name,
                    de_validation_output_path.name,
                ],
                row_count=len(de_validation_rows),
                parser_method=REGIONAL_DE_LYME_SOURCE_METADATA["parser_method"],
                extraction_quality="accepted_validation_only",
                access_notes=(
                    "Public Delaware DHSS HTML page; no secret or credential "
                    "required. Raw HTML remains in ignored storage."
                ),
                modeling_caveats=REGIONAL_DE_LYME_SOURCE_METADATA[
                    "modeling_caveats"
                ],
            )
        )
    if va_source_path is not None:
        records.append(
            AcquisitionProvenanceRecord(
                source_id=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA["source_id"],
                source_name=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA[
                    "source_name"
                ],
                source_url=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA["source_url"],
                citation_url=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA[
                    "citation_url"
                ],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read the ignored local Virginia VDH reportable disease "
                    "geography CSV, filter to 2024 Lyme disease locality rows, "
                    "and append them as flagged state-source rows to the "
                    "regional outcome panel."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    "Read local raw Virginia VDH reportable disease geography "
                    f"CSV {va_source_path.name} for the state 2024 locality "
                    "overlay."
                ),
                derived_artifact_paths=[va_source_path, output_path],
                derived_artifact_path_labels=[
                    va_source_path.name,
                    output_path.name,
                ],
                row_count=len(va_rows),
                parser_method=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA[
                    "parser_method"
                ],
                extraction_quality="accepted_state_overlay",
                access_notes=(
                    "Public Virginia VDH data.virginia.gov CSV export; no "
                    "secret or credential required. Raw CSV remains in ignored "
                    "storage."
                ),
                modeling_caveats=REGIONAL_VA_VDH_LYME_2024_SOURCE_METADATA[
                    "modeling_caveats"
                ],
            )
        )
    return records


def _regional_lyme_acquisition_command(
    *,
    raw_dir: Path,
    pa_source_path: Path | None,
    de_source_path: Path | None,
    va_source_path: Path | None,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    command_parts = [
        "tickbiterisk",
        "etl",
        "regional-lyme-outcomes",
        "--raw-dir",
        _public_provenance_path(raw_dir),
    ]
    if pa_source_path is not None:
        command_parts.extend(
            [
                "--pa-2024-workbook-path",
                _public_provenance_path(pa_source_path),
            ]
        )
    if de_source_path is not None:
        command_parts.extend(
            [
                "--de-lyme-html-path",
                _public_provenance_path(de_source_path),
            ]
        )
    if va_source_path is not None:
        command_parts.extend(
            [
                "--va-vdh-locality-csv-path",
                _public_provenance_path(va_source_path),
            ]
        )
    command_parts.extend(
        [
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )
    return _format_cli_command(command_parts)


def _regional_signals_provenance_record(
    *,
    rows: list[object],
    regional_lyme_path: Path,
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id="midatlantic_regional_signals",
        source_name="Mid-Atlantic regional Lyme reported-case signal table",
        source_url=regional_lyme_path.name,
        citation_url=CDC_LYME_SURVEILLANCE_CITATION_URL,
        acquisition_command=_regional_signals_acquisition_command(
            regional_lyme_path=regional_lyme_path,
            output_dir=output_dir,
            manifest_path=manifest_path,
        ),
        acquisition_procedure=(
            "Read the derived Mid-Atlantic CDC county dashboard outcome panel "
            "and compute same-year diagnostic regional totals plus prior-year "
            "and trailing-history regional signal features."
        ),
        request_method="LOCAL_FILE_READ",
        request_description=(
            f"Read derived regional Lyme panel {regional_lyme_path.name} and "
            "write forecast-safe lagged regional signal candidates."
        ),
        derived_artifact_paths=[regional_lyme_path, output_path],
        derived_artifact_path_labels=[regional_lyme_path.name, output_path.name],
        row_count=len(rows),
        parser_method="build_midatlantic_regional_signals",
        extraction_quality="accepted",
        access_notes=(
            "Derived from a local public CDC dashboard panel; no secret or "
            "credential required."
        ),
        modeling_caveats=(
            "Regional signal candidate only; same-year diagnostic columns are "
            "not forecast-time features, case counts are not population rates, "
            "and reported cases are not stable true incidence."
        ),
    )


def _regional_signals_acquisition_command(
    *,
    regional_lyme_path: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "regional-signals",
            "--regional-lyme-path",
            _public_provenance_path(regional_lyme_path),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _seasonality_provenance_records(
    *,
    source_metadata: list[dict[str, str]],
    observations: list[object],
    source_paths_by_id: dict[str, Path],
    output_paths: list[Path],
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _seasonality_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
    )
    row_counts = _seasonality_observation_row_counts(observations)
    records = []
    for metadata in source_metadata:
        source_id = metadata["source_id"]
        source_path = source_paths_by_id[source_id]
        artifact_paths = [source_path, *output_paths]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=metadata["source_name"],
                source_url=metadata["source_url"],
                citation_url=metadata["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read an ignored local CDC Lyme seasonality source export, "
                    "normalize disease-onset observations, and build national "
                    "month/MMWR-week seasonal-share baselines."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    f"Read local raw CDC Lyme seasonality CSV {source_path.name} "
                    f"for {metadata['grain']} observations from --raw-dir."
                ),
                derived_artifact_paths=artifact_paths,
                derived_artifact_path_labels=[
                    artifact_path.name for artifact_path in artifact_paths
                ],
                row_count=row_counts.get(source_id, 0),
                parser_method=metadata["parser_method"],
                extraction_quality="accepted",
                access_notes=(
                    "Local ignored raw export from public CDC Lyme surveillance "
                    "dashboard source; no secret or credential required."
                ),
                modeling_caveats=(
                    "national curve only, not county-specific; shares are "
                    "normalized by annual total and should be used as a static "
                    "seasonality prior rather than a live case forecast."
                ),
            )
        )
    return records


def _seasonality_observation_row_counts(observations: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for observation in observations:
        source_id = str(getattr(observation, "source_id", ""))
        counts[source_id] = counts.get(source_id, 0) + 1
    return counts


def _seasonality_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "seasonality-baseline",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _tick_status_provenance_records(
    *,
    source_metadata: list[dict[str, str]],
    rows_by_source: dict[str, list[dict[str, object]]],
    source_paths_by_id: dict[str, Path],
    outputs: TickStatusOutputPaths,
    raw_dir: Path,
    output_dir: Path,
    region: str,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _tick_status_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        region=region,
        manifest_path=manifest_path,
    )
    output_paths_by_kind = {
        "vector": outputs.vector_path,
        "pathogen": outputs.pathogen_path,
        "lone_star": outputs.lone_star_path,
    }
    feature_path = outputs.features_path
    records = []
    for metadata in source_metadata:
        source_id = metadata["source_id"]
        source_path = source_paths_by_id[source_id]
        output_path = output_paths_by_kind[metadata["output_kind"]]
        artifact_paths = [source_path, output_path, feature_path]
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id,
                source_name=metadata["source_name"],
                source_url=metadata["source_url"],
                citation_url=metadata["citation_url"],
                acquisition_command=command,
                acquisition_procedure=(
                    "Read an ignored local CDC tick status workbook, normalize "
                    "selected county status rows, and build status-only "
                    "county feature indicators."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    f"Read local raw CDC tick status workbook {source_path.name} "
                    "from --raw-dir."
                ),
                derived_artifact_paths=artifact_paths,
                derived_artifact_path_labels=[
                    artifact_path.name for artifact_path in artifact_paths
                ],
                row_count=len(rows_by_source.get(source_id, [])),
                parser_method=metadata["parser_method"],
                extraction_quality="accepted",
                access_notes=(
                    "Local ignored CDC tick surveillance workbook; review CDC "
                    "data-use language before publishing full row-level "
                    "derived tables."
                ),
                modeling_caveats=(
                    "Current county status only, not prevalence or abundance; "
                    "no_records is not absence, and status timing may lag "
                    "actual tick/pathogen establishment."
                ),
            )
        )
    return records


def _nssp_coverage_provenance_record(
    *,
    raw_path: Path,
    output_path: Path,
    output_dir: Path,
    county_reference_path: Path,
    manifest_path: Path,
    coverage_url: str,
    downloaded: bool,
    row_count: int,
) -> AcquisitionProvenanceRecord:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "nssp-coverage",
            "--raw-path",
            _public_provenance_path(raw_path),
            "--county-reference-path",
            _public_provenance_path(county_reference_path),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--coverage-url",
            coverage_url,
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )
    return AcquisitionProvenanceRecord(
        source_id=NSSP_COVERAGE_SOURCE_ID,
        source_name=(
            "CDC NSSP emergency-care facility participation coverage table"
        ),
        source_url=coverage_url,
        citation_url=CDC_NSSP_ABOUT_URL,
        acquisition_command=command,
        acquisition_procedure=(
            "Download or read the public CDC NSSP county coverage table, "
            "filter Maryland rows, attach county FIPS codes, and preserve "
            "coverage-status caveats."
        ),
        request_method="GET" if downloaded else "LOCAL_FILE_READ",
        request_description=(
            f"{'Downloaded' if downloaded else 'Read local'} CDC NSSP coverage "
            f"CSV {raw_path.name} from {coverage_url}."
        ),
        derived_artifact_paths=[raw_path, output_path],
        derived_artifact_path_labels=[raw_path.name, output_path.name],
        row_count=row_count,
        parser_method=(
            "parse_nssp_coverage_csv;build_maryland_nssp_coverage"
        ),
        extraction_quality="accepted",
        access_notes=(
            "Public CDC NSSP coverage table; county status only and no API "
            "key required."
        ),
        modeling_caveats=(
            "Coverage feasibility only; not tick-bite ED volume, not Lyme "
            "incidence, and not human-exposure truth."
        ),
    )


def _resolve_tick_status_sources(
    raw_dir: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, Path]]:
    selected_by_kind: dict[str, dict[str, str]] = {}
    paths_by_key: dict[str, Path] = {}
    missing_messages = []
    for metadata in TICK_STATUS_SOURCE_METADATA:
        candidates = [
            metadata,
            *metadata.get("fallbacks", []),
        ]
        selected_metadata = None
        selected_path = None
        for candidate in candidates:
            path = raw_dir / str(candidate["filename"])
            if path.exists():
                selected_metadata = {
                    key: str(value)
                    for key, value in candidate.items()
                    if key != "fallbacks"
                }
                selected_path = path
                break
        if selected_metadata is None or selected_path is None:
            expected = ", ".join(str(candidate["filename"]) for candidate in candidates)
            missing_messages.append(f"{metadata['output_kind']}: {expected}")
            continue
        output_kind = selected_metadata["output_kind"]
        source_id = selected_metadata["source_id"]
        selected_by_kind[output_kind] = selected_metadata
        paths_by_key[output_kind] = selected_path
        paths_by_key[source_id] = selected_path
    if missing_messages:
        raise typer.BadParameter(
            "tick status source file not found: " + "; ".join(missing_messages)
        )
    return selected_by_kind, paths_by_key


def _tick_status_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    region: str,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "tick-status",
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--region",
            region,
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
        ]
    )


def _mast_acorn_provenance_records(
    *,
    sources: list[MarylandDnrMastReportSource],
    summaries: list[object],
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    rows_output: Path,
    summary_output: Path,
    parser: str,
) -> list[AcquisitionProvenanceRecord]:
    command = _mast_acorn_acquisition_command(
        raw_dir=raw_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
        parser=parser,
        manual_observations_path=None,
    )
    summary_by_source_id = {
        str(getattr(summary, "source_id", "")): summary for summary in summaries
    }
    records = []
    for source in sources:
        summary = summary_by_source_id[source.source_id]
        source_path = raw_dir / Path(source.raw_relative_path).name
        artifact_paths = [source_path, rows_output, summary_output]
        extraction_status = str(getattr(summary, "extraction_status", "not_recorded"))
        quality_flags = str(getattr(summary, "feature_quality_flags", "")).strip()
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source.source_id,
                source_name=(
                    f"Maryland DNR Western Maryland mast survey summary "
                    f"{source.year}"
                ),
                source_url=source.url,
                citation_url=source.url,
                acquisition_command=command,
                acquisition_procedure=(
                    "Read an ignored local Maryland DNR mast survey PDF, "
                    "extract text with the selected PDF parser, parse supported "
                    "Western Maryland study-plot mast/acorn tables, and write "
                    "structured rows plus extraction summaries."
                ),
                request_method="LOCAL_FILE_READ",
                request_description=(
                    f"Read local raw Maryland DNR mast survey PDF "
                    f"{source_path.name} from --raw-dir."
                ),
                derived_artifact_paths=artifact_paths,
                derived_artifact_path_labels=[
                    artifact_path.name for artifact_path in artifact_paths
                ],
                row_count=int(getattr(summary, "structured_row_count", 0)),
                parser_method=f"build_mast_acorn_from_pdf:{parser}",
                extraction_quality=extraction_status,
                access_notes=(
                    "Public Maryland DNR PDF retained in ignored raw storage; "
                    "no secret or credential required."
                ),
                modeling_caveats=_mast_acorn_modeling_caveats(
                    extraction_status=extraction_status,
                    quality_flags=quality_flags,
                ),
            )
        )
    return records


def _manual_mast_observation_provenance_record(
    *,
    manual_observations_path: Path,
    manual_output: Path,
    row_count: int,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    parser: str,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id="manual_mast_observations",
        source_name="Manual mast observations",
        source_url="local_manual_mast_observations",
        citation_url="",
        acquisition_command=_mast_acorn_acquisition_command(
            raw_dir=raw_dir,
            output_dir=output_dir,
            manifest_path=manifest_path,
            parser=parser,
            manual_observations_path=manual_observations_path,
        ),
        acquisition_procedure=(
            "Read an optional local manual mast observation CSV and normalize "
            "rows into a separate not-public-default mast observation artifact."
        ),
        request_method="LOCAL_FILE_READ",
        request_description=(
            f"Read local manual mast observation CSV {manual_observations_path.name}."
        ),
        derived_artifact_paths=[manual_observations_path, manual_output],
        derived_artifact_path_labels=[
            manual_observations_path.name,
            manual_output.name,
        ],
        row_count=row_count,
        parser_method="read_manual_mast_observations",
        extraction_quality="manual_observation",
        access_notes=(
            "Local manual observation file; not an official public source and "
            "not intended for public default modeling."
        ),
        modeling_caveats=(
            "manual_observation; anecdotal; not_official; not_model_default; "
            "use only for exploratory review."
        ),
    )


def _mast_acorn_modeling_caveats(
    *,
    extraction_status: str,
    quality_flags: str,
) -> str:
    caveats = [
        "western Maryland study-plot data only",
        "not countywide or statewide",
        "mast/acorn values are prior-year predictors, not same-year defaults",
    ]
    if quality_flags:
        caveats.append(f"quality_flags={quality_flags}")
    if extraction_status != "structured":
        caveats.append("do not model until extraction confidence improves")
    return "; ".join(caveats)


def _mast_acorn_acquisition_command(
    *,
    raw_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    parser: str,
    manual_observations_path: Path | None,
) -> str:
    command_parts = [
        "tickbiterisk",
        "etl",
        "mast-acorn",
        "--raw-dir",
        _public_provenance_path(raw_dir),
        "--output-dir",
        _public_provenance_path(output_dir),
        "--parser",
        parser,
        "--provenance-manifest-path",
        _public_provenance_path(manifest_path),
    ]
    if manual_observations_path is not None:
        command_parts.extend(
            [
                "--manual-observations-path",
                _public_provenance_path(manual_observations_path),
            ]
        )
    return _format_cli_command(command_parts)


def _public_provenance_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        pass
    return path.name if path.is_absolute() else str(path)


def _write_single_request_provenance_manifest(
    *,
    manifest_path: Path,
    record: AcquisitionProvenanceRecord,
) -> Path:
    return write_acquisition_provenance_manifest(
        [record],
        manifest_path=manifest_path,
        append=True,
        replace_source_ids=True,
    )


def _usdm_provenance_records(
    *,
    start_year: int,
    end_year: int,
    aoi: str,
    output_dir: Path,
    manifest_path: Path,
    rows_by_year: dict[int, list[object]],
    derived_artifact_paths: list[Path],
) -> list[AcquisitionProvenanceRecord]:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "usdm-drought",
            "--start-year",
            str(start_year),
            "--end-year",
            str(end_year),
            "--aoi",
            aoi,
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )
    records = []
    for year in range(start_year, end_year + 1):
        urls = build_usdm_drought_urls(aoi=aoi, year=year)
        year_rows = rows_by_year.get(year, [])
        row_count = len(
            {
                (
                    getattr(row, "county_fips", ""),
                    getattr(row, "map_date", ""),
                )
                for row in year_rows
            }
        )
        records.append(
            AcquisitionProvenanceRecord(
                source_id=f"usdm_county_statistics_{aoi.lower()}_{year}",
                source_name="U.S. Drought Monitor County Statistics",
                source_url=f"{urls.dsci_url} {urls.severity_url}",
                citation_url=USDM_DATA_DOWNLOAD_URL,
                acquisition_command=command,
                acquisition_procedure=(
                    "Fetch paired USDM CountyStatistics DSCI and drought "
                    "severity area-percent CSV responses, then merge them by "
                    "county FIPS and map date."
                ),
                request_method="GET",
                request_description=(
                    "USDM CountyStatistics GetDSCI and "
                    "GetDroughtSeverityStatisticsByAreaPercent requests for "
                    f"{aoi} {year}."
                ),
                derived_artifact_paths=derived_artifact_paths,
                row_count=row_count,
                parser_method=(
                    "fetch_usdm_drought_year;parse_usdm_dsci_csv;"
                    "parse_usdm_severity_csv"
                ),
                extraction_quality="accepted",
                access_notes="Public U.S. Drought Monitor endpoint; no API key required.",
                modeling_caveats=(
                    "Retrospective county drought exposure proxy; county-level "
                    "weekly summaries do not establish tick exposure causality."
                ),
            )
        )
    return records


def _census_population_provenance_records(
    *,
    urls: list[str],
    rows: list[object],
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
    latest_only: bool,
    append: bool,
    api_key_present: bool,
) -> list[AcquisitionProvenanceRecord]:
    command_parts = [
        "tickbiterisk",
        "etl",
        "census-population",
        "--output-dir",
        str(output_dir),
    ]
    if latest_only:
        command_parts.append("--latest-only")
    if append:
        command_parts.append("--append")
    command_parts.extend(["--provenance-manifest-path", str(manifest_path)])
    command = _format_cli_command(command_parts)
    row_counts = _census_population_row_counts(rows)
    return [
        AcquisitionProvenanceRecord(
            source_id=metadata["source_id"],
            source_name="U.S. Census Bureau county population estimates",
            source_url=sanitize_census_url(url),
            citation_url=metadata["citation_url"],
            acquisition_command=command,
            acquisition_procedure=metadata["acquisition_procedure"],
            request_method="GET",
            request_description=metadata["request_description"],
            derived_artifact_paths=[output_path],
            row_count=row_counts.get(metadata["row_count_key"], 0),
            parser_method=metadata["parser_method"],
            extraction_quality="accepted",
            access_notes=(
                "Public Census API endpoint; optional CENSUS_API_KEY is read "
                "from the local environment and redacted from provenance."
                if api_key_present and "api.census.gov" in url
                else "Public Census endpoint; no secret is required in provenance."
            ),
            modeling_caveats=(
                "County population denominator estimate; not exposure evidence "
                "and subject to Census vintage/revision changes."
            ),
        )
        for url, metadata in zip(
            urls,
            _census_population_source_metadata(latest_only=latest_only),
            strict=True,
        )
    ]


def _census_population_row_counts(rows: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source_id = str(getattr(row, "source_id", ""))
        census_dataset = str(getattr(row, "census_dataset", ""))
        year = getattr(row, "year", "")
        if source_id == "census_pep_2023_charv":
            key = f"{source_id}_{year}"
        elif source_id == "census_pep_2025_county_totals":
            key = source_id
        elif census_dataset == CENSUS_INTERCENSAL_1990_DATASET:
            key = "census_pep_intercensal_1990_2000"
        elif census_dataset == CENSUS_INTERCENSAL_2000_DATASET:
            key = "census_pep_intercensal_2000_2010"
        else:
            key = source_id
        counts[key] = counts.get(key, 0) + 1
    return counts


def _census_population_source_metadata(*, latest_only: bool = False) -> list[dict[str, str]]:
    metadata = [
        {
            "source_id": "census_population_intercensal_1990_2000",
            "row_count_key": "census_pep_intercensal_1990_2000",
            "citation_url": "https://www.census.gov/programs-surveys/popest.html",
            "acquisition_procedure": (
                "Fetch Census intercensal county population API rows and "
                "normalize Maryland county denominators for 1992-1999."
            ),
            "request_description": "Census intercensal 1990 population API request.",
            "parser_method": "parse_census_intercensal_1990_population",
        },
        {
            "source_id": "census_population_intercensal_2000_2010",
            "row_count_key": "census_pep_intercensal_2000_2010",
            "citation_url": "https://www.census.gov/programs-surveys/popest.html",
            "acquisition_procedure": (
                "Fetch Census intercensal county population API rows and "
                "normalize Maryland county denominators for 2000-2009."
            ),
            "request_description": "Census intercensal 2000 population API request.",
            "parser_method": "parse_census_intercensal_2000_population",
        },
        {
            "source_id": "census_population_pep_2019",
            "row_count_key": "census_pep_2019",
            "citation_url": "https://www.census.gov/programs-surveys/popest.html",
            "acquisition_procedure": (
                "Fetch Census PEP 2019 API rows and normalize Maryland county "
                "denominators for 2010-2019."
            ),
            "request_description": "Census PEP 2019 county population API request.",
            "parser_method": "parse_census_pep_2019_population",
        },
        *[
            {
                "source_id": f"census_population_pep_2023_charv_{year}",
                "row_count_key": f"census_pep_2023_charv_{year}",
                "citation_url": "https://www.census.gov/programs-surveys/popest.html",
                "acquisition_procedure": (
                    "Fetch Census PEP 2023 characteristics API rows and "
                    f"normalize Maryland July {year} total county denominators."
                ),
                "request_description": (
                    f"Census PEP 2023 characteristics population API request for {year}."
                ),
                "parser_method": "parse_census_pep_2023_charv_population",
            }
            for year in range(2020, 2024)
        ],
        {
            "source_id": "census_population_2025_county_totals",
            "row_count_key": "census_pep_2025_county_totals",
            "citation_url": "https://www.census.gov/programs-surveys/popest.html",
            "acquisition_procedure": (
                "Fetch the official Census county totals CSV and normalize "
                "Maryland county denominators for 2024-2025."
            ),
            "request_description": "Census Vintage 2025 county totals CSV request.",
            "parser_method": "parse_census_pep_2025_county_totals_population",
        },
    ]
    if latest_only:
        return [metadata[-1]]
    return metadata


def _regional_population_row_counts(rows: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        state_fips = str(getattr(row, "state_fips", ""))
        source_id = str(getattr(row, "source_id", ""))
        if source_id == "census_pep_intercensal_2000_2010_static":
            key = f"{state_fips}_intercensal_2000_2010_static"
        elif source_id == "census_pep_2019_county_totals":
            key = "pep_2019_county_totals"
        elif source_id == "census_pep_2023_county_totals":
            key = "pep_2023_county_totals"
        elif source_id == "census_pep_2025_county_totals":
            key = "pep_2025_county_totals"
        elif source_id == REGIONAL_POPULATION_PROJECTION_SOURCE_ID:
            key = "population_projection_2026"
        else:
            key = f"{state_fips}_{source_id}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _regional_population_url_metadata(url: str) -> dict[str, str]:
    if "co-est00int-alldata-" in url:
        state_fips = (
            Path(urlsplit(url).path)
            .name.removeprefix("co-est00int-alldata-")
            .removesuffix(".csv")
            .zfill(2)
        )
        return {
            "source_id": (
                "census_midatlantic_population_intercensal_2000_2010_static_"
                f"{state_fips}"
            ),
            "row_count_key": f"{state_fips}_intercensal_2000_2010_static",
            "acquisition_procedure": (
                "Fetch Census intercensal county population static CSV rows and "
                "normalize Mid-Atlantic county denominators for 2001-2009."
            ),
            "request_description": (
                f"Census intercensal 2000 population CSV request for state {state_fips}."
            ),
            "parser_method": "parse_census_intercensal_2000_county_totals",
        }
    if "co-est2019-alldata.csv" in url:
        return {
            "source_id": "census_midatlantic_population_pep_2019_county_totals",
            "row_count_key": "pep_2019_county_totals",
            "acquisition_procedure": (
                "Fetch Census PEP 2019 county totals CSV rows and "
                "normalize Mid-Atlantic county denominators for 2010-2019."
            ),
            "request_description": "Census PEP 2019 county totals CSV request.",
            "parser_method": "parse_census_pep_2019_county_totals",
        }
    if "co-est2023-alldata.csv" in url:
        return {
            "source_id": "census_midatlantic_population_pep_2023_county_totals",
            "row_count_key": "pep_2023_county_totals",
            "acquisition_procedure": (
                "Fetch Census PEP 2023 county totals CSV rows and normalize "
                "Mid-Atlantic county denominators for 2020-2023."
            ),
            "request_description": "Census PEP 2023 county totals CSV request.",
            "parser_method": "parse_census_pep_2023_county_totals",
        }
    return {
        "source_id": "census_midatlantic_population_pep_2025_county_totals",
        "row_count_key": "pep_2025_county_totals",
        "acquisition_procedure": (
            "Fetch Census PEP 2025 county totals CSV rows and normalize "
            "Mid-Atlantic county denominators for 2020-2025."
        ),
        "request_description": "Census PEP 2025 county totals CSV request.",
        "parser_method": "parse_census_pep_2025_county_totals",
    }


def _regional_population_projection_provenance_records(
    *,
    rows: list[object],
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    row_count = sum(
        1
        for row in rows
        if str(getattr(row, "source_id", "")) == REGIONAL_POPULATION_PROJECTION_SOURCE_ID
    )
    if row_count == 0:
        return []
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "regional-population",
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )
    return [
        AcquisitionProvenanceRecord(
            source_id="census_midatlantic_population_projection_2026",
            source_name=(
                "Derived Mid-Atlantic county population projection from "
                "U.S. Census Bureau county population estimates"
            ),
            source_url=sanitize_census_url(
                build_midatlantic_census_pep_2025_county_totals_url()
            ),
            citation_url="https://www.census.gov/programs-surveys/popest.html",
            acquisition_command=command,
            acquisition_procedure=(
                "Fetch the official Census PEP 2025 county totals CSV and derive "
                "2026 county denominators with a simple trailing linear trend by "
                "county."
            ),
            request_method="GET",
            request_description=(
                "Census PEP 2025 county totals CSV request used as the observed "
                "base for 2026 population projection."
            ),
            derived_artifact_paths=[output_path],
            row_count=row_count,
            parser_method="project_county_population_linear_trend",
            extraction_quality="derived_projection",
            access_notes=(
                "Projection is derived locally from public Census static CSV "
                "estimates; no API key required."
            ),
            modeling_caveats=(
                "Forecast denominator only: there is no official 2026 Census "
                "county denominator in this source yet. Replace with observed "
                "Census estimates when published."
            ),
        )
    ]


def _regional_population_observed_provenance_records(
    *,
    urls: list[str],
    rows: list[object],
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
    api_key_present: bool,
) -> list[AcquisitionProvenanceRecord]:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "regional-population",
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )
    row_counts = _regional_population_row_counts(rows)
    return [
        AcquisitionProvenanceRecord(
            source_id=metadata["source_id"],
            source_name="U.S. Census Bureau Mid-Atlantic county population estimates",
            source_url=sanitize_census_url(url),
            citation_url="https://www.census.gov/programs-surveys/popest.html",
            acquisition_command=command,
            acquisition_procedure=metadata["acquisition_procedure"],
            request_method="GET",
            request_description=metadata["request_description"],
            derived_artifact_paths=[output_path],
            row_count=row_counts.get(metadata["row_count_key"], 0),
            parser_method=metadata["parser_method"],
            extraction_quality="accepted",
            access_notes="Public Census static CSV endpoint; no secret is required.",
            modeling_caveats=(
                "County population denominator estimate for regional rate "
                "diagnostics; not exposure evidence and subject to Census "
                "vintage/revision changes."
            ),
        )
        for url, metadata in (
            (url, _regional_population_url_metadata(url)) for url in urls
        )
    ]


def _regional_population_provenance_records(
    *,
    urls: list[str],
    rows: list[object],
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
    api_key_present: bool,
) -> list[AcquisitionProvenanceRecord]:
    return [
        *_regional_population_observed_provenance_records(
            urls=urls,
            rows=rows,
            output_path=output_path,
            output_dir=output_dir,
            manifest_path=manifest_path,
            api_key_present=api_key_present,
        ),
        *_regional_population_projection_provenance_records(
            rows=rows,
            output_path=output_path,
            output_dir=output_dir,
            manifest_path=manifest_path,
        ),
    ]

def _regional_demographics_provenance_records(
    *,
    urls: list[str],
    rows: list[object],
    output_path: Path,
    output_dir: Path,
    manifest_path: Path,
) -> list[AcquisitionProvenanceRecord]:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "regional-demographics",
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )
    row_counts = _regional_demographics_row_counts(rows)
    return [
        AcquisitionProvenanceRecord(
            source_id=metadata["source_id"],
            source_name=(
                "U.S. Census Bureau Mid-Atlantic county age/sex estimates"
            ),
            source_url=url,
            citation_url=CENSUS_PEP_AGE_SEX_CITATION_URL,
            acquisition_command=command,
            acquisition_procedure=metadata["acquisition_procedure"],
            request_method="GET",
            request_description=metadata["request_description"],
            derived_artifact_paths=[output_path],
            row_count=row_counts.get(metadata["row_count_key"], 0),
            parser_method=metadata["parser_method"],
            extraction_quality="accepted",
            access_notes="Public Census static CSV endpoint; no API key required.",
            modeling_caveats=(
                "County age-structure context for exposure research only; not "
                "tick-bite counts, not Lyme incidence, and subject to Census "
                "vintage/revision changes."
            ),
        )
        for metadata, url in [
            (_regional_demographics_url_metadata(url), url) for url in urls
        ]
    ]


def _regional_demographics_row_counts(rows: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source_id = str(getattr(row, "source_id", ""))
        counts[source_id] = counts.get(source_id, 0) + 1
    return counts


def _regional_demographics_url_metadata(url: str) -> dict[str, str]:
    filename = Path(urlsplit(url).path).name
    state_fips = filename.removesuffix(".csv").split("-")[-1].zfill(2)
    if "cc-est2019-agesex-" in filename:
        return {
            "source_id": f"census_pep_2019_county_age_sex_{state_fips}",
            "row_count_key": f"census_pep_2019_county_age_sex_{state_fips}",
            "acquisition_procedure": (
                "Fetch Census PEP 2019 county age/sex static CSV rows and "
                "normalize Mid-Atlantic county age-structure context for "
                "2010-2019."
            ),
            "request_description": (
                f"Census PEP 2019 county age/sex CSV request for state {state_fips}."
            ),
            "parser_method": "parse_census_pep_2019_age_sex",
        }
    return {
        "source_id": f"census_pep_2024_county_age_sex_{state_fips}",
        "row_count_key": f"census_pep_2024_county_age_sex_{state_fips}",
        "acquisition_procedure": (
            "Fetch Census PEP 2024 county age/sex static CSV rows and "
            "normalize Mid-Atlantic county age-structure context for 2020-2024."
        ),
        "request_description": (
            f"Census PEP 2024 county age/sex CSV request for state {state_fips}."
        ),
        "parser_method": "parse_census_pep_2024_age_sex",
    }


def _acs_exposure_provenance_records(
    *,
    source_urls: AcsExposureSourceUrls,
    source_paths: dict[str, Path],
    output_path: Path,
    output_dir: Path,
    raw_dir: Path,
    manifest_path: Path,
    row_count: int,
    append: bool,
) -> list[AcquisitionProvenanceRecord]:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "acs-exposure",
            "--year",
            str(source_urls.year),
            "--raw-dir",
            _public_provenance_path(raw_dir),
            "--output-dir",
            _public_provenance_path(output_dir),
            "--provenance-manifest-path",
            _public_provenance_path(manifest_path),
            "--append" if append else "--replace",
        ]
    )
    source_items = [
        (
            "census_acs5_{year}_geography",
            "ACS 5-year table-based summary file geography table",
            source_urls.geography_url,
            source_paths["geography"],
            "parse_acs_geography",
        ),
        *[
            (
                f"census_acs5_{{year}}_{table}",
                f"ACS 5-year detailed table {table.upper()}",
                source_urls.table_urls[table],
                source_paths[table],
                f"parse_acs_table:{table}",
            )
            for table in ["b01001", "b25024", "b25003"]
        ],
        (
            "census_gazetteer_2024_counties_national",
            "Census Gazetteer 2024 national counties",
            source_urls.gazetteer_url,
            source_paths["gazetteer"],
            "parse_gazetteer_land_area",
        ),
    ]
    return [
        AcquisitionProvenanceRecord(
            source_id=source_id_template.format(year=source_urls.year),
            source_name=source_name,
            source_url=url,
            citation_url=ACS_TABLE_BASED_SUMMARY_FILE_CITATION_URL,
            acquisition_command=command,
            acquisition_procedure=(
                "Download or read keyless public ACS 5-year table-based summary "
                "files, filter Mid-Atlantic county rows, combine age, housing "
                "structure, tenure, and Census Gazetteer land-area context."
            ),
            request_method="GET_OR_LOCAL_FILE_READ",
            request_description=(
                f"ACS exposure source file {source_path.name} for vintage "
                f"{source_urls.year}."
            ),
            derived_artifact_paths=[source_path, output_path],
            derived_artifact_path_labels=[source_path.name, output_path.name],
            row_count=row_count,
            parser_method=parser_method,
            extraction_quality="accepted",
            access_notes=(
                "Public Census static file; no API key required. Raw ACS "
                "summary files stay in ignored local storage."
            ),
            modeling_caveats=(
                "ACS 5-year rolling survey context only; residential form and "
                "density are exposure proxies, not tick-bite counts, direct "
                "exposure evidence, Lyme incidence, disease truth, and not "
                "public-default model inputs."
            ),
        )
        for (
            source_id_template,
            source_name,
            url,
            source_path,
            parser_method,
        ) in source_items
    ]


def _census_url_state_fips(url: str) -> str:
    state_predicate = _census_url_query_value(url, "in")
    if state_predicate.startswith("state:"):
        return state_predicate.removeprefix("state:").zfill(2)
    return "unknown"


def _census_url_query_value(url: str, key: str) -> str:
    query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    return query.get(key, "")


def _building_permits_provenance_records(
    *,
    start_year: int,
    end_year: int,
    output_dir: Path,
    manifest_path: Path,
    output_path: Path,
    rows_by_year: dict[int, list[object]],
) -> list[AcquisitionProvenanceRecord]:
    command = _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "building-permits",
            "--start-year",
            str(start_year),
            "--end-year",
            str(end_year),
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )
    records = []
    for year in range(start_year, end_year + 1):
        source_url = build_census_bps_county_annual_url(year)
        year_rows = rows_by_year.get(year, [])
        records.append(
            AcquisitionProvenanceRecord(
                source_id=source_id_from_census_bps_year(year),
                source_name="U.S. Census Bureau Building Permits Survey county file",
                source_url=source_url,
                citation_url=CENSUS_BPS_CITATION_URL,
                acquisition_command=command,
                acquisition_procedure=(
                    "Fetch the annual Census Building Permits Survey county "
                    "December year-to-date ASCII file and normalize Maryland "
                    "county totals."
                ),
                request_method="GET",
                request_description=(
                    "Census Building Permits Survey annual county ASCII file "
                    f"request for {year}."
                ),
                derived_artifact_paths=[output_path],
                row_count=len(
                    {(row.county_fips.zfill(5), row.year) for row in year_rows}
                ),
                parser_method="parse_census_bps_county_text",
                extraction_quality="accepted",
                access_notes="Public Census static file; no API key required.",
                modeling_caveats=(
                    "Construction/contact-pressure proxy only; permits do not "
                    "prove human tick exposure or disease incidence."
                ),
            )
        )
    return records


def _deer_harvest_acquisition_command(
    *,
    county_reference_path: Path,
    output_dir: Path,
    source_urls: list[str] | None,
    include_annual_report_pdfs: bool,
    skip_news_html: bool,
    annual_report_parser: str,
    manifest_path: Path,
) -> str:
    command_parts = [
        "tickbiterisk",
        "etl",
        "deer-harvest",
        "--county-reference-path",
        str(county_reference_path),
        "--output-dir",
        str(output_dir),
    ]
    for source_url in source_urls or []:
        command_parts.extend(["--url", source_url])
    if include_annual_report_pdfs:
        command_parts.extend(
            [
                "--include-annual-report-pdfs",
                "--annual-report-parser",
                annual_report_parser,
            ]
        )
    if skip_news_html:
        command_parts.append("--skip-news-html")
    command_parts.extend(["--provenance-manifest-path", str(manifest_path)])
    return _format_cli_command(command_parts)


def _deer_harvest_html_provenance_record(
    *,
    source_url: str,
    source_id: str,
    acquisition_command: str,
    output_path: Path,
    row_count: int,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id=source_id,
        source_name="Maryland DNR deer harvest news table",
        source_url=source_url,
        citation_url=source_url,
        acquisition_command=acquisition_command,
        acquisition_procedure=(
            "Fetch a Maryland DNR news-page HTML harvest table and normalize "
            "county-season deer harvest totals."
        ),
        request_method="GET",
        request_description="Maryland DNR deer harvest news page request.",
        derived_artifact_paths=[output_path],
        row_count=row_count,
        parser_method="parse_maryland_dnr_deer_harvest_html",
        extraction_quality="accepted",
        access_notes="Public Maryland DNR news page; no API key required.",
        modeling_caveats=(
            "Reported harvest is a host-pressure proxy, not a direct deer "
            "abundance, tick exposure, or disease observation."
        ),
    )


def _deer_harvest_pdf_provenance_record(
    *,
    source_url: str,
    source_id: str,
    acquisition_command: str,
    output_path: Path,
    row_count: int,
    annual_report_parser: str,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id=source_id,
        source_name="Maryland DNR deer annual report PDF",
        source_url=source_url,
        citation_url=MARYLAND_DNR_DEER_ANNUAL_REPORT_ARCHIVE_URL,
        acquisition_command=acquisition_command,
        acquisition_procedure=(
            "Fetch a Maryland DNR deer/big-game annual report PDF, extract the "
            "county harvest table, and normalize county-season totals."
        ),
        request_method="GET",
        request_description="Maryland DNR deer annual report PDF request.",
        derived_artifact_paths=[output_path],
        row_count=row_count,
        parser_method=f"parse_maryland_dnr_deer_harvest_pdf:{annual_report_parser}",
        extraction_quality="accepted",
        access_notes=(
            "Public Maryland DNR PDF; no API key required. Older annual "
            "reports may require OCR review before modeling use."
        ),
        modeling_caveats=(
            "Reported harvest is a prior-season host-pressure proxy, not a "
            "direct deer abundance, tick exposure, or disease observation."
        ),
    )


def _open_meteo_single_acquisition_command(
    *,
    county_fips: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "weather-backfill-open-meteo",
            "--county-fips",
            county_fips,
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )


def _open_meteo_maryland_acquisition_command(
    *,
    start_date: str,
    end_date: str,
    output_dir: Path,
    county_fips_values: list[str],
    max_chunk_days: int,
    weather_model: str,
    max_attempts: int,
    retry_sleep_seconds: float,
    inter_chunk_sleep_seconds: float,
    inter_county_sleep_seconds: float,
    fail_fast: bool,
    allow_partial: bool,
    manifest_path: Path,
) -> str:
    command_parts = [
        "tickbiterisk",
        "etl",
        "weather-backfill-open-meteo-maryland",
        "--start-date",
        start_date,
        "--end-date",
        end_date,
        "--output-dir",
        str(output_dir),
    ]
    for county_fips in county_fips_values:
        command_parts.extend(["--county-fips", county_fips])
    command_parts.extend(
        [
            "--max-chunk-days",
            str(max_chunk_days),
            "--weather-model",
            weather_model,
            "--max-attempts",
            str(max_attempts),
            "--retry-sleep-seconds",
            str(retry_sleep_seconds),
            "--inter-chunk-sleep-seconds",
            str(inter_chunk_sleep_seconds),
            "--inter-county-sleep-seconds",
            str(inter_county_sleep_seconds),
        ]
    )
    if fail_fast:
        command_parts.append("--fail-fast")
    if allow_partial:
        command_parts.append("--allow-partial")
    command_parts.extend(["--provenance-manifest-path", str(manifest_path)])
    return _format_cli_command(command_parts)


def _open_meteo_maryland_provenance_records(
    *,
    plans: list[OpenMeteoArchiveRequestPlan],
    county_results: list[OpenMeteoCountyBackfillResult],
    start_date: date,
    end_date: date,
    acquisition_command: str,
    weather_model: str,
) -> list[AcquisitionProvenanceRecord]:
    plans_by_county: dict[str, list[OpenMeteoArchiveRequestPlan]] = {}
    county_names: dict[str, str] = {}
    for plan in plans:
        plans_by_county.setdefault(plan.county_fips, []).append(plan)
        county_names[plan.county_fips] = plan.county_name

    return [
        _open_meteo_provenance_record(
            county_fips=result.county_fips,
            county_name=county_names.get(result.county_fips, result.county_fips),
            start_date=start_date,
            end_date=end_date,
            source_urls=[plan.url for plan in plans_by_county.get(result.county_fips, [])],
            acquisition_command=acquisition_command,
            output_paths=[
                result.daily_output_path,
                result.weekly_output_path,
                result.monthly_output_path,
            ],
            row_count=result.daily_observation_count,
            chunk_count=result.chunk_count,
            weather_model=weather_model,
        )
        for result in county_results
    ]


def _open_meteo_provenance_record(
    *,
    county_fips: str,
    county_name: str,
    start_date: date,
    end_date: date,
    source_urls: list[str],
    acquisition_command: str,
    output_paths: list[Path],
    row_count: int,
    chunk_count: int,
    weather_model: str,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id=(
            f"{_open_meteo_source_slug(weather_model)}_{county_fips}_"
            f"{_date_slug(start_date)}_{_date_slug(end_date)}"
        ),
        source_name="Open-Meteo Historical Weather API",
        source_url=" ".join(source_urls),
        citation_url=OPEN_METEO_HISTORICAL_WEATHER_CITATION_URL,
        acquisition_command=acquisition_command,
        acquisition_procedure=(
            "Fetch Open-Meteo archive API JSON for a Maryland county internal "
            "point, normalize daily weather observations, and compute weekly "
            "and monthly weather features."
        ),
        request_method="GET",
        request_description=(
            "Open-Meteo Historical Weather API archive request"
            f"{'s' if chunk_count != 1 else ''} for {county_name} "
            f"({county_fips}) from {start_date.isoformat()} through "
            f"{end_date.isoformat()} using {weather_model}."
        ),
        derived_artifact_paths=output_paths,
        row_count=row_count,
        parser_method="fetch_open_meteo_archive;parse_open_meteo_archive_response",
        extraction_quality="accepted",
        access_notes=(
            "Public Open-Meteo archive API; no API key required. Use throttling "
            "for larger backfills to respect rate limits."
        ),
        modeling_caveats=(
            "County internal-point reanalysis/gap-fill weather proxy; not a "
            "direct tick exposure or disease observation."
        ),
    )


def _noaa_stations_acquisition_command(
    *,
    county_fips: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    min_data_coverage: float,
    max_end_lag_days: int,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "noaa-stations",
            "--county-fips",
            county_fips,
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--output-dir",
            str(output_dir),
            "--min-data-coverage",
            str(min_data_coverage),
            "--max-end-lag-days",
            str(max_end_lag_days),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )


def _noaa_daily_acquisition_command(
    *,
    county_fips: str,
    station_id: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "noaa-daily",
            "--county-fips",
            county_fips,
            "--station-id",
            station_id,
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--output-dir",
            str(output_dir),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )


def _noaa_backfill_county_acquisition_command(
    *,
    county_fips: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    station_limit: int,
    min_data_coverage: float,
    max_end_lag_days: int,
    manifest_path: Path,
) -> str:
    return _format_cli_command(
        [
            "tickbiterisk",
            "etl",
            "noaa-backfill-county",
            "--county-fips",
            county_fips,
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--output-dir",
            str(output_dir),
            "--station-limit",
            str(station_limit),
            "--min-data-coverage",
            str(min_data_coverage),
            "--max-end-lag-days",
            str(max_end_lag_days),
            "--provenance-manifest-path",
            str(manifest_path),
        ]
    )


def _noaa_backfill_maryland_acquisition_command(
    *,
    start_date: str,
    end_date: str,
    output_dir: Path,
    county_fips_values: list[str],
    station_limit: int,
    min_data_coverage: float,
    max_end_lag_days: int,
    fail_fast: bool,
    allow_partial: bool,
    nearest_station_fallback: bool,
    manifest_path: Path,
) -> str:
    command_parts = [
        "tickbiterisk",
        "etl",
        "noaa-backfill-maryland",
        "--start-date",
        start_date,
        "--end-date",
        end_date,
        "--output-dir",
        str(output_dir),
    ]
    for county_fips in county_fips_values:
        command_parts.extend(["--county-fips", county_fips])
    command_parts.extend(
        [
            "--station-limit",
            str(station_limit),
            "--min-data-coverage",
            str(min_data_coverage),
            "--max-end-lag-days",
            str(max_end_lag_days),
        ]
    )
    if fail_fast:
        command_parts.append("--fail-fast")
    if allow_partial:
        command_parts.append("--allow-partial")
    if nearest_station_fallback:
        command_parts.append("--nearest-station-fallback")
    command_parts.extend(["--provenance-manifest-path", str(manifest_path)])
    return _format_cli_command(command_parts)


def _noaa_backfill_provenance_records(
    *,
    result: NoaaCountyBackfillResult,
    source_id_prefix: str,
    acquisition_command: str,
    start_date: date,
    end_date: date,
) -> list[AcquisitionProvenanceRecord]:
    records = [
        _noaa_provenance_record(
            source_id=(
                f"noaa_cdo_ghcnd_stations_{source_id_prefix}_"
                f"{result.county_fips}_{_date_slug(start_date)}_{_date_slug(end_date)}"
            ),
            source_name="NOAA CDO GHCND station discovery",
            source_url=build_noaa_station_url(result.county_fips, start_date, end_date),
            acquisition_command=acquisition_command,
            request_description=(
                "NOAA CDO GHCND station discovery request for "
                f"Maryland county FIPS {result.county_fips} during backfill."
            ),
            output_path=result.stations_output_path,
            row_count=result.station_count,
            parser_method=(
                "run_noaa_county_backfill;fetch_noaa_stations;"
                "parse_noaa_station_response;select_long_coverage_stations"
            ),
        )
    ]
    for station_id in result.selected_station_ids:
        station_row_count = result.daily_observation_count_by_station.get(
            station_id,
            result.daily_observation_count
            if len(result.selected_station_ids) == 1
            else 0,
        )
        records.append(
            _noaa_provenance_record(
                source_id=(
                    f"noaa_cdo_ghcnd_daily_{source_id_prefix}_"
                    f"{result.county_fips}_{_source_id_slug(station_id)}_"
                    f"{_date_slug(start_date)}_{_date_slug(end_date)}"
                ),
                source_name="NOAA CDO GHCND daily observations",
                source_url=build_noaa_daily_data_url(station_id, start_date, end_date),
                acquisition_command=acquisition_command,
                request_description=(
                    "NOAA CDO daily observations request for selected backfill "
                    f"station {station_id} mapped to Maryland county FIPS "
                    f"{result.county_fips}."
                ),
                output_path=result.daily_output_path,
                row_count=station_row_count,
                parser_method=(
                    "run_noaa_county_backfill;fetch_noaa_daily_observations;"
                    "parse_noaa_daily_data_response"
                ),
            )
        )
    return records


def _noaa_provenance_record(
    *,
    source_id: str,
    source_name: str,
    source_url: str,
    acquisition_command: str,
    request_description: str,
    output_path: Path,
    row_count: int,
    parser_method: str,
) -> AcquisitionProvenanceRecord:
    return AcquisitionProvenanceRecord(
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        citation_url=NOAA_CDO_WEBSERVICES_CITATION_URL,
        acquisition_command=acquisition_command,
        acquisition_procedure=(
            "Fetch NOAA Climate Data Online GHCND API JSON using a local "
            "NOAA_TOKEN request header, then normalize the selected weather "
            "records for TickBiteRisk ETL artifacts."
        ),
        request_method="GET",
        request_description=request_description,
        derived_artifact_paths=[output_path],
        row_count=row_count,
        parser_method=parser_method,
        extraction_quality="accepted",
        access_notes=(
            "Public NOAA CDO API endpoint; a local NOAA_TOKEN is required in "
            "the request header and is not written to provenance."
        ),
        modeling_caveats=(
            "Station weather observations mapped to county features; weather "
            "is an environmental proxy, not a direct tick exposure or disease "
            "observation."
        ),
    )


def _source_id_slug(value: str) -> str:
    return "".join(
        character if character.isalnum() else "_"
        for character in value.lower()
    ).strip("_")


def _open_meteo_source_slug(weather_model: str) -> str:
    return _source_id_slug(weather_model)


def _date_slug(value: date) -> str:
    return value.isoformat().replace("-", "_")


def _format_cli_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _sanitize_provenance_url(url: str) -> str:
    secret_key_terms = ("auth", "key", "password", "secret", "token")
    parsed = urlsplit(url)
    if not parsed.query:
        return url
    sanitized_query = urlencode(
        [
            (
                key,
                "<redacted>"
                if any(term in _normalized_query_key(key) for term in secret_key_terms)
                else value,
            )
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
    )
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            sanitized_query,
            parsed.fragment,
        )
    )


def _normalized_query_key(key: str) -> str:
    return "".join(character for character in key.lower() if character.isalnum())


def _census_population_urls(
    *, api_key: str | None, latest_only: bool = False
) -> list[str]:
    latest_url = build_census_pep_2025_county_totals_url()
    if latest_only:
        return [latest_url]
    return [
        build_census_intercensal_1990_population_url(api_key=api_key),
        build_census_intercensal_2000_population_url(api_key=api_key),
        build_census_pep_2019_population_url(api_key=api_key),
        *[
            build_census_pep_2023_charv_population_url(year=year, api_key=api_key)
            for year in range(2020, 2024)
        ],
        latest_url,
    ]


if __name__ == "__main__":
    app()
