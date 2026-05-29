# TickBiteRisk Data Sources

## Current source catalog

This catalog describes the data used or acquired for the current Maryland v0
product. Public runtime artifacts are derived files in `public/data`; raw
downloads stay outside the public site unless a source license and privacy
boundary clearly allow redistribution.

| Source ID | Source | Grain | Current use | Status |
| --- | --- | --- | --- | --- |
| `cdc_lyme_public_use` | CDC Lyme public-use aggregated geography files | County-year | Long-run Lyme outcome spine | active_etl |
| `cdc_lyme_dashboard_exports` | CDC county/state/region Lyme dashboard exports through 2023 | County/state/region-year | Reconciliation and validation checks | active_etl |
| `pa_doh_lyme_1980_2024_xlsx` | Pennsylvania DOH official Lyme county workbook through 2024 | Pennsylvania county-year | Optional 2024 state-source overlay for Mid-Atlantic regional stress tests | active_etl_optional_2024_not_public_default |
| `virginia_vdh_reportable_disease_locality_2024_csv` | Virginia VDH reportable disease surveillance geography CSV, 2024 | Virginia locality-year | Optional VDH 2024 locality state overlay for Mid-Atlantic regional stress tests | active_etl_optional_2024_state_overlay_not_public_default |
| `west_virginia_oeps_vectorborne_reports` | West Virginia OEPS Vectorborne Disease Summary PDFs, 2024-2025 | West Virginia state-year/disease | Provisional state aggregate validation/context; not county training rows | active_etl_state_aggregate_not_public_default |
| `mass_dph_monthly_tickborne_reports` | Massachusetts DPH monthly tick-borne disease DOCX reports | Massachusetts county/combined-county report period | Syndromic ED tickborne-disease diagnosis visit sidecar; not Lyme incidence or model input | active_etl_syndromic_ed_signal_not_public_default |
| `nj_doh_reportable_tickborne_2024_pdf` | New Jersey DOH 2024 reportable disease statistics PDF | New Jersey state/county disease-year | Northeast extension sidecar for reportable tickborne counts; not model input | active_etl_reportable_tickborne_sidecar_not_public_default |
| `maine_jmmc_2024_county_rates` | Journal of Maine Medical Center tickborne trends review PDF | Maine state/county disease-rate year | External comparator sidecar for preliminary 2024 tickborne disease rates; not active forecast geography, case counts, or model input | active_etl_external_comparator_not_public_default |
| `delaware_dhss_lyme_table` | Delaware DHSS Lyme disease county case table, 2019-2023 | Delaware county-year | State-source validation sidecar for overlapping CDC regional years | active_etl_validation_sidecar_not_model_input |
| `maryland_lyme_pdf` | Maryland Department of Health Lyme PDF, 2013-2024 | Maryland county-year | Latest Maryland 2024 outcome lane, with overlapping years kept as validation context | active_etl_latest_2024 |
| `cdc_lyme_seasonality` | CDC Lyme onset by MMWR week and month | National week/month | Static seasonal allocation from annual predictions to county-week forecast | active_etl |
| `noaa_ghcnd` | NOAA daily station observations | Station-day to county-week/year | Weather feature candidates and backtesting inputs | active_etl |
| `census_county_reference` | Census Gazetteer county file | County | County names, FIPS, land/water area, internal points | active_etl |
| `census_tigerweb_midatlantic_counties` | Census TIGERweb county geometry for DE/DC/MD/PA/VA/WV | County/county-equivalent GeoJSON | Regional cross-border shared-boundary adjacency graph | active_etl_spatial_support_not_public_default |
| `census_population` | Census PEP/intercensal population APIs and county totals CSV | County-year | Incidence denominators and per-capita feature normalization through 2025 | active_etl |
| `census_regional_age_sex` | Census PEP county age/sex static CSVs | County-year | Mid-Atlantic age-structure context for exposure research; not tick-bite counts | active_etl_candidate_feature |
| `acs_residential_exposure_context` | ACS 5-year table-based summary files B01001/B25024/B25003 | County-year ACS vintage | 2023-2024 Mid-Atlantic residential form, tenure, age, and density exposure-context proxy; not tick-bite counts | active_etl_2023_2024_candidate_feature_not_public_default |
| `maryland_dnr_deer_harvest` | Maryland DNR deer harvest tables and annual reports | County-season | Host-pressure proxy; prior completed season maps into model year | active_etl |
| `cdc_tick_vector_status` | CDC public tick vector county table through 2025 | County/species/status | Vector presence/status feature candidates | active_etl_latest_2025 |
| `cdc_tick_pathogen_status` | CDC public Ixodes pathogen county table through 2025 | County/pathogen/status | Pathogen detection feature candidates | active_etl_latest_2025 |
| `nlcd_mrlc` | MRLC/NLCD land cover files | Raster/county summary candidate | Habitat and forest/edge proxy source | acquired_needs_feature_depth |
| `census_bps` | Census Building Permits Survey county files | County-year | Contact/land-use pressure proxy | active_etl |
| `maryland_mast_reports` | Maryland DNR mast/acorn reports | Region/report | Ecological food pulse candidate | acquired_low_confidence |
| `noaa_cpc_oni` | NOAA CPC Oceanic Nino Index | Global seasonal climate index | Lagged ENSO phase overtone candidate; materialized as complete prior-year model features, not promoted into the public model | active_etl_candidate_feature |
| `noaa_psl_mei_v2` | NOAA PSL Multivariate ENSO Index v2 | Global monthly climate index | Lagged ocean-atmosphere ENSO companion to ONI; materialized as complete prior-year model features, not promoted into the public model | active_etl_candidate_feature_not_public_default |
| `nssp_coverage` | NSSP coverage map table | County/status | Feasibility check for future ED tick-bite feed; materialized with county FIPS and caveats, but not tick-bite counts | active_etl_feasibility_only_not_model_input |
| `capc_dog_serology` | CAPC canine Lyme data | County/month | Possible veterinary sentinel source | not_redistributed_license_sensitive |

## Potential source and feature candidates

These are not current public-runtime inputs. They are candidate feeds or derived
feature ideas to test in time-aware backtests before any public model claim.

| Source ID | Candidate | Grain | Why try it | Status |
| --- | --- | --- | --- | --- |
| `open_meteo_archive_md_county_daily` | Open-Meteo historical/reanalysis weather | County-day | 2020-2023 Maryland-wide enriched weather layer with humidity, dew point, soil moisture, soil temperature, evapotranspiration, and wind fields that NOAA GHCND does not currently populate | candidate_etl_supported_recent_backfill_materialized |
| `usda_fia_fiadb` | USDA Forest Service FIA / FIADB / EVALIDator | Forest inventory estimate | Oak-hickory and forest-composition context that may be more biologically meaningful than generic forest percent | source_manifested_needs_feature_extraction |
| `maryland_dnr_archery_hunter_survey` | Maryland DNR Archery Hunter / Bowhunter Survey | Hunter report / county-season if extractable | Host and wildlife observation proxy, potentially lighter than raster GIS if report tables are defensible | source_manifested_needs_review |
| `usda_nass_maryland_cdl` | USDA NASS Cropland Data Layer / CropScape | Raster/county summary candidate | Annual crop, pasture, hay, and open-land change context around land-use and edge habitat | source_manifested_needs_feature_extraction |
| `noaa_cpc_enso_index` | NOAA CPC ENSO index, ONI/RONI | Global seasonal climate index | ONI is now materialized; RONI remains a candidate companion index to test as a lagged climate-regime overtone | oni_active_roni_candidate_needs_etl |
| `acs_residential_exposure_history` | ACS 5-year B01001/B25024/B25003 detailed-table history | County-year ACS vintage | Historical backfill before the materialized 2023-2024 exposure-context proxy if the rolling-survey caveats remain useful in backtests | candidate_historical_backfill_needs_static_summary_parser |
| `cdc_tick_bite_tracker` | CDC Tick Bite Data Tracker | HHS region/week dashboard | Human tick-bite exposure pressure overlay if backing data becomes available; current public dashboard grain is not county-year and is not a disease truth label | candidate_missing_bulk_data |
| `nssp_tick_bite_ed` | NSSP tick-bite emergency department visits | Facility/county/region-week likely | Privacy-sensitive human exposure pressure feed candidate; useful only after acquisition, suppression, coverage, and privacy review, and not a confirmed disease truth label | candidate_needs_acquisition_privacy_review_not_public_default |
| `poison_center_tick_bite_inquiries` | Poison center tick-bite inquiries | Call center region/county-week likely | Privacy-sensitive exposure pressure feed candidate that could capture tick-bite concern or advice-seeking behavior, not confirmed Lyme disease outcomes | candidate_needs_acquisition_privacy_review_not_public_default |
| `inaturalist_tick_observations` | iNaturalist tick observations | Point observation | Experimental tick-observation activity proxy if normalized by observer effort and license terms | candidate_bias_sensitive |
| `gbif_tick_occurrences` | GBIF tick occurrence records | Point occurrence | Comparator for public tick observations and museum/citizen-science records, with per-record license review | candidate_bias_sensitive |
| `park_attendance_county_year` | Park attendance or trail-use records | Park/county/agency-year | Outdoor recreation exposure pressure proxy if reliable Maryland aggregate sources can be found; visits do not confirm tick exposure or Lyme infection | candidate_needs_source_selection |
| `dog_license_pet_ownership_proxy` | Dog license or pet ownership aggregate proxy | County-year likely | Public aggregate pet/outdoor-contact exposure proxy candidate, not a confirmed disease truth label | candidate_needs_acquisition_not_public_default |
| `parcel_low_density_residential_proxy` | Parcel or land-use low-density residential proxy | Parcel to county-year summary likely | Public aggregate residential edge/contact exposure proxy candidate, not a confirmed disease truth label | candidate_needs_acquisition_not_public_default |
| `surveillance_regime_calibration` | Surveillance regime calibration indicators | County-year or region-year | Calibration diagnostics for reporting-regime shifts, coverage, and capacity artifacts; not a disease truth label or public dashboard branch input | candidate_needs_acquisition_privacy_review_not_public_default |
| `ecological_pressure_index` | Composite ecological pressure index | County-year derived feature | derived feature candidate, not a raw feed; would combine lagged host, habitat, climate stress, contact pressure, spatial disease pressure, and optional ENSO/Open-Meteo/FIA inputs | candidate_needs_design_and_backtest |

## 2024+ regional and exposure watchlist

This is the working potential-sources file for candidates that may help the
forecasting model after the current Maryland/Mid-Atlantic inputs. These rows are
source leads, not public-runtime promises. Each candidate needs a saved
official/source URL or acquisition procedure, raw-file checksum or request URL,
parser evidence, and time-aware validation before it can move into a model lane.

| Source ID | Official/source URL or acquisition procedure | Why it matters | Caveat/status |
| --- | --- | --- | --- |
| `pa_doh_lyme_1980_2024_xlsx` | Download "1980-2024 Lyme Disease Data" from [PA DOH Tick Diseases](https://www.pa.gov/agencies/health/diseases-conditions/infectious-disease/vectorborne-diseases/tick-diseases); local optional raw path is `data/raw/lyme/pennsylvania_doh_official_lyme_by_report_2024_with_map.xlsx` | Best immediate 2024 county Lyme overlay in the DE/DC/MD/PA/VA/WV footprint | active optional regional overlay; state-source rows are not a confirmed disease truth label for latent incidence |
| `delaware_dhss_lyme_table` | Review [Delaware DHSS Lyme data](https://dhss.delaware.gov/dph/epi/tick-lyme-data/) and save the page/table before extraction | Adjacent county-scale outcome validation source for the regional panel | active validation sidecar for 2019-2023; rows overlap CDC regional years and are not appended to the model input panel; no 2024 county export verified yet; not a confirmed disease truth label |
| `virginia_vdh_reportable_disease_dashboard` | Use [Virginia Communicable Disease Data](https://www.vdh.virginia.gov/surveillance-and-investigation/virginia-communicable-disease-data/), the [2024 Annual Report dashboard](https://www.vdh.virginia.gov/surveillance-and-investigation/annual-report/), and the official [geography CSV export](https://data.virginia.gov/datastore/dump/5b1fc1e7-3ef9-42cd-8dd1-6c3d4ef4da79?bom=True); local optional raw path is `data/raw/lyme/virginia_vdh_reportable_disease_geography_2024.csv` | Adds VDH 2024 locality reported Lyme counts for Virginia to the regional panel | active state 2024 locality overlay via `--va-vdh-locality-csv-path`; Virginia localities include counties and independent cities; not a confirmed disease truth label |
| `west_virginia_oeps_vectorborne_reports` | Download 2024 and 2025 Vectorborne Disease Summary PDFs from [WV OEPS Arboviral Diseases](https://oeps.wv.gov/arboviral-diseases); local optional raw paths are `data/raw/lyme/west-virginia/west_virginia_oeps_vectorborne_2024.pdf` and `data/raw/lyme/west-virginia/west_virginia_oeps_vectorborne_2025.pdf` | Adds WV provisional state aggregate validation/context: Lyme disease 2,867 through 2024-10-25 and 4,019 through 2025-11-14, both reported in 55 counties | active state aggregate validation via `wv-vectorborne-summary`; county maps are not digitized and no county rows are emitted; not a confirmed disease truth label |
| `dc_health_tickborne_report` | Review [DC Health Tickborne Diseases](https://dchealth.dc.gov/page/tickborne-diseases), [DC Health Lyme Disease](https://dchealth.dc.gov/page/lyme-disease), the [2014-2020 summary PDF](https://dchealth.dc.gov/sites/default/files/dc/sites/doh/publication/attachments/Tickborne%20Diseases%20Summary%20report%202014%20to%202020.pdf), and DC Open Data search | DC is a county-equivalent in the regional footprint and needs jurisdiction-level caveats | DC Health current-data blocker: official pages/fact sheets are current, but no reproducible 2024+ numeric jurisdiction table, dashboard export, CSV, or current surveillance PDF found; not a confirmed disease truth label |
| `mass_dph_monthly_tickborne_reports` | Download DOCX reports from [Massachusetts Monthly Tick-borne Disease Reports](https://www.mass.gov/lists/monthly-tick-borne-disease-reports); local optional raw paths are `data/raw/exposure/massachusetts/mass_dph_tickborne_syndromic_2024_jan_dec.docx`, `data/raw/exposure/massachusetts/mass_dph_tickborne_syndromic_2025_jan_dec.docx`, and `data/raw/exposure/massachusetts/mass_dph_tickborne_syndromic_2026_april.docx` | Strong human-exposure/syndromic proxy with 2024, 2025, and 2026 report-period ED visit counts/rates by Massachusetts county residence | active syndromic ED sidecar via `mass-dph-syndromic-ed`; ED visits and diagnoses are exposure/syndromic signals, not Lyme incidence, not a confirmed disease truth label, and not model input |
| `maine_jmmc_2024_county_rates` | Use the [Journal of Maine Medical Center article](https://knowledgeconnection.mainehealth.org/jmmc/vol7/iss2/10), direct [review PDF](https://knowledgeconnection.mainehealth.org/cgi/viewcontent.cgi?article=1219&context=jmmc), DOI [10.46804/2641-2225.1219](https://doi.org/10.46804/2641-2225.1219), and [Maine Tracking Network Tickborne Diseases](https://data.mainepublichealth.gov/tracking/tickborne); local optional raw path is `data/raw/lyme/maine/jmmc_maine_tickborne_trends_2001_2024.pdf` | Peer-reviewed/open county-rate signal for 2024 Maine tickborne diseases | active external comparator sidecar via `maine-jmmc-tickborne-rates`; outside the active forecast footprint; JMMC Table 2 values are preliminary rates only as of 2025-01-20, not county case counts, not a confirmed disease truth label, and not model input |
| `ohio_odh_lyme_dashboard` | Review [Ohio ODH Lyme Disease Map](https://odh.ohio.gov/know-our-programs/zoonotic-disease-program/media/lyme-disease-map) and any Tableau/export route | Potential 2025 YTD county case signal west of Pennsylvania | needs official export check and interactive-data acquisition; not a confirmed disease truth label |
| `nj_doh_tickborne_page` | Use the [NJ DOH Reportable Disease Statistics page](https://www.nj.gov/health/cd/statistics/reportable-disease-stats/), the 2024 [statistics PDF](https://www.nj.gov/health/cd/documents/reportable_disease/web_statistics_2024.pdf), and the 2024 [technical notes PDF](https://www.nj.gov/health/cd/documents/reportable_disease/technical_notes_2024.pdf); keep 2025 vector-borne reports and the vector-borne dashboard as candidates | Adjacent Northeast extension with 2024 county/state reportable tickborne counts and 2025/dashboard leads | active reportable tickborne sidecar via `nj-doh-reportable-tickborne`; 2025 vector summary/dashboard remain candidates; state-source reported cases are not a confirmed disease truth label |
| `cdc_surveillance_based_lyme_disease_network` | Track CDC [Lyme Disease Surveillance and Data](https://www.cdc.gov/lyme/data-research/facts-stats/index.html) for public EHR-based SubLyme releases | Future measurement-error/update layer candidate for ME/MA/PA/WI | no public county data yet; EHR-derived estimates would need privacy and method review; not a confirmed disease truth label |
| `foia_nndss_preliminary_county` | If needed, file a CDC/NNDSS FOIA or data-request package through official CDC channels and save the request/response evidence | Could test whether 2023-2025 county preliminary case data can update forecasts before public release | restricted/request-only candidate; likely suppression and data-use limits; not a confirmed disease truth label |
| `state_essence_tick_bite_proxy` | Use [CDC NSSP dashboard documentation](https://www.cdc.gov/nssp/php/data-research/dashboards/index.html), state ESSENCE contacts, and `nssp_coverage` feasibility rows | Best direct human-tick-encounter proxy if county/suppressed aggregates become available | privacy-sensitive syndromic exposure signal; not a confirmed disease truth label or public-default input |

## Current v0 derived artifacts

| Artifact | Producer | Use |
| --- | --- | --- |
| `lyme_county_year_reconciled.csv` | `tickbiterisk etl lyme-outcomes` | Maryland Lyme outcome panel with source reconciliation flags |
| `county_population_year.csv` | `tickbiterisk etl census-population` | County-year population denominators |
| `midatlantic_county_population_year.csv` | `tickbiterisk etl regional-population` | DE/DC/MD/PA/VA/WV county-year population denominators for regional rate diagnostics, with flagged 2026 forecast projections |
| `midatlantic_age_demographics_county_year.csv` | `tickbiterisk etl regional-demographics` | DE/DC/MD/PA/VA/WV county-year age-structure context through 2024 |
| `midatlantic_acs_exposure_county_year.csv` | `tickbiterisk etl acs-exposure` | DE/DC/MD/PA/VA/WV 2023-2024 ACS residential-form, tenure, age, and density exposure-context proxy |
| `regional_counties.geojson` | `tickbiterisk etl regional-county-adjacency --fetch-census-geojson` | Normalized DE/DC/MD/PA/VA/WV county-equivalent geometry for regional spatial support |
| `regional_county_adjacency.csv` | `tickbiterisk etl regional-county-adjacency --fetch-census-geojson` | Cross-border shared-boundary county-neighbor graph for regional spatial pressure diagnostics and forecast research |
| `county_reference.csv` | `tickbiterisk etl county-reference` | County FIPS, names, land area, and internal points |
| `weather_features_weekly.csv` | `tickbiterisk etl noaa-weather-features` | Weekly weather predictors and quality flags |
| `model_features_county_year.csv` | `tickbiterisk etl model-features` | Model-ready joined county-year panel |
| `model_design_matrix_county_year.csv` | `tickbiterisk etl model-design-matrix` | Numeric feature matrix |
| `model_design_matrix_schema.json` | `tickbiterisk etl model-design-matrix` | Design-matrix schema sidecar |
| `midatlantic_hotspot_county_year.csv` | `tickbiterisk etl regional-hotspots` | Count/share/rank hotspot movement diagnostics from the Mid-Atlantic panel |
| `midatlantic_hotspot_summary.csv` | `tickbiterisk etl regional-hotspots` | Annual top-quintile persistence, entry, and exit diagnostics |
| `midatlantic_lyme_incidence_county_year.csv` | `tickbiterisk etl regional-incidence` | Mid-Atlantic county-year Lyme incidence per 100k diagnostics |
| `midatlantic_lyme_incidence_summary.csv` | `tickbiterisk etl regional-incidence` | Annual denominator coverage and incidence hotspot transition diagnostics |
| `regional_lyme_state_source_validation.csv` | `tickbiterisk etl regional-lyme-outcomes --de-lyme-html-path` | Delaware DHSS state-source validation sidecar; rows overlap CDC regional years and are not appended to the model input panel |
| `wv_vectorborne_state_summary.csv` | `tickbiterisk etl wv-vectorborne-summary` | West Virginia OEPS provisional state aggregate validation/context; not county training rows |
| `mass_dph_syndromic_ed_county_summary.csv` | `tickbiterisk etl mass-dph-syndromic-ed` | Massachusetts DPH syndromic ED county residence sidecar for tickborne-disease diagnosis visit pressure; not Lyme incidence, not a confirmed disease truth label, and not model input |
| `nj_doh_reportable_tickborne_county_year.csv` | `tickbiterisk etl nj-doh-reportable-tickborne` | New Jersey DOH reportable tickborne state/county sidecar for 2024; not a confirmed disease truth label and not model input |
| `maine_jmmc_tickborne_county_rates_2024.csv` | `tickbiterisk etl maine-jmmc-tickborne-rates` | Maine JMMC tickborne county rates external comparator sidecar for 2024 preliminary rates only; not active forecast geography, case counts, a confirmed disease truth label, or model input |
| `regional_outcome_stress_predictions.csv` | `tickbiterisk etl regional-outcome-stress` | Mid-Atlantic outcome-only capacity-share stress predictions |
| `regional_outcome_stress_metrics.csv` | `tickbiterisk etl regional-outcome-stress` | Case-count MAE/RMSE metrics for regional historical-range baselines |
| `regional_incidence_stress_runs.csv` | `tickbiterisk etl regional-incidence-stress` | Mid-Atlantic incidence-rate stress run manifest |
| `regional_incidence_stress_predictions.csv` | `tickbiterisk etl regional-incidence-stress` | Mid-Atlantic incidence-rate shrinkage, analog, random-forest, optional prior-year spatial-neighbor, and optional localized spatial-regime stress predictions |
| `regional_incidence_stress_metrics.csv` | `tickbiterisk etl regional-incidence-stress` | Incidence MAE/RMSE metrics for regional historical-range baselines |
| `regional_spatial_regime_runs.csv` | `tickbiterisk etl regional-spatial-regimes` | Localized spatial regime run manifest with incidence and adjacency hashes |
| `regional_spatial_regime_county_year.csv` | `tickbiterisk etl regional-spatial-regimes` | Forecast-safe localized spatial regime county-year assignments and prior-history features |
| `regional_spatial_regime_summary.csv` | `tickbiterisk etl regional-spatial-regimes` | Localized spatial regime annual summaries with feature priors and diagnostic held-out outcomes |
| `regional_annual_forecast_runs.csv` | `tickbiterisk etl regional-annual-forecast` | Mid-Atlantic target-year forecast run manifest with origin, hashes, and forecast caveats |
| `regional_annual_forecast_predictions.csv` | `tickbiterisk etl regional-annual-forecast` | Mid-Atlantic county-year forecast rows, including horizon-matched analog branch, without observed target, residual, or error columns |
| `regional_forecast_capacity_runs.csv` | `tickbiterisk etl regional-forecast-capacity` | Mid-Atlantic forecast-capacity diagnostic run manifest |
| `regional_forecast_capacity_summary.csv` | `tickbiterisk etl regional-forecast-capacity` | State and Mid-Atlantic forecast totals compared with historical reported-incidence ranges |
| `regional_incidence_cluster_runs.csv` | `tickbiterisk etl regional-incidence-clusters` | Mid-Atlantic prior-incidence cluster run manifest |
| `regional_incidence_cluster_county_year.csv` | `tickbiterisk etl regional-incidence-clusters` | Forecast-safe low/moderate/high/very-high prior-incidence band assignments |
| `regional_incidence_cluster_summary.csv` | `tickbiterisk etl regional-incidence-clusters` | Prior cluster capacity bands and held-out actual incidence diagnostics |
| `model_comparison_predictions.csv` | `tickbiterisk etl model-compare` | Rolling-origin predictions from candidate model branches |
| `model_comparison_intervals.csv` | `tickbiterisk etl model-compare` | Bootstrap prediction intervals companion artifact for comparison branches |
| `annual_forecast_runs.csv` | `tickbiterisk etl annual-forecast` | Target-year forecast run manifest with declared origin, hashes, and forecast caveats |
| `annual_forecast_predictions.csv` | `tickbiterisk etl annual-forecast` | Maryland county-year forecast rows without observed target, residual, or error columns |
| `forecast_calibration_summary.csv` | `tickbiterisk etl model-diagnostics` | Empirical observed-to-predicted calibration factors by branch, surveillance regime, and year |
| `forecast_calibration_backtest_predictions.csv` | `tickbiterisk etl forecast-calibration-backtest` | Forecast-safe shrunken calibration predictions using prior update evidence only |
| `forecast_calibration_backtest_metrics.csv` | `tickbiterisk etl forecast-calibration-backtest` | Original-vs-calibrated MAE/RMSE metrics for empirical update multipliers |
| `forecast_bayesian_update_backtest_runs.csv` | `tickbiterisk etl forecast-bayesian-update-backtest` | Gamma-Poisson forecast-update run manifest with prior strength and source hash |
| `forecast_bayesian_update_backtest_predictions.csv` | `tickbiterisk etl forecast-bayesian-update-backtest` | Posterior updated prediction rows using prior forecast errors as evidence |
| `forecast_bayesian_update_backtest_metrics.csv` | `tickbiterisk etl forecast-bayesian-update-backtest` | Original-vs-updated MAE/RMSE and interval coverage metrics for Bayesian update tests |
| `noaa_cpc_oni_seasons.csv` | `tickbiterisk etl enso-oni` | NOAA CPC ONI seasonal anomalies and El Nino / La Nina phase labels |
| `noaa_cpc_oni_model_year_features.csv` | `tickbiterisk etl enso-oni` | Complete prior-year ONI model-year climate context features |
| `noaa_psl_mei_v2_monthly.csv` | `tickbiterisk etl enso-mei-v2` | NOAA PSL MEI.v2 monthly global ocean-atmosphere index values |
| `noaa_psl_mei_v2_model_year_features.csv` | `tickbiterisk etl enso-mei-v2` | Complete prior-year MEI.v2 model-year climate context features |
| `nssp_coverage_county_status.csv` | `tickbiterisk etl nssp-coverage` | CDC NSSP county emergency-care coverage feasibility status |
| `seasonality_baseline.csv` | `tickbiterisk etl seasonality-baseline` | CDC weekly/monthly Lyme onset share baseline |
| `county_week_seasonal_risk_baseline.csv` | `tickbiterisk etl county-week-risk` | Product-shaped county-week relative risk rows |
| `md_county_risk_weekly.json` | `tickbiterisk risk export-static` | Public dashboard score payload |
| `md_county_metadata.json` | `tickbiterisk risk export-static` | Public county metadata payload |
| `model_card.json` | `tickbiterisk risk export-static` | Public model, caveat, and provenance summary |
| `source_catalog.json` | `tickbiterisk risk export-static` | Public source and artifact metadata |

## Redistribution boundary

- Public federal sources are generally reusable, but the repo still publishes
  derived artifacts rather than raw dumps by default.
- State reports and dashboards are cited and transformed conservatively.
- CAPC veterinary data is license-sensitive and should not be redistributed
  from this repo.
- Public dashboard files should remain source-attributed, checksum-backed, and
  small enough for static hosting.

## Known gaps

- NSSP tick-bite ED data is not wired into the current model. The materialized
  coverage table only tells us where future ED/syndromic data work may be
  feasible; it is not a tick-bite feed or a disease outcome.
- ACS residential-form exposure context is materialized for the 2023 and 2024
  ACS 5-year vintages from static table-based summary files. Earlier historical
  ACS backfill remains a candidate, and the raw files are large enough to keep
  cached under ignored storage. These values remain exposure-context proxies,
  not tick-bite counts or annual observed exposure; density fields use static
  2024 Census Gazetteer land area.
- Mast/acorn reports are currently low-confidence for structured county-year
  extraction and should be treated as notes until better extraction or manual
  review exists.
- Land-cover features need deeper county summarization before they should drive
  public model claims.
- ONI and MEI.v2 ETL/model joins are implemented as separate lagged global
  climate context artifacts. The first ONI time-aware backtest did not improve
  the selected public branch, so RONI, MEI.v2, and composite
  ecological-pressure features still need separate evidence before any public
  model claim.
- Open-Meteo recent backfill is local under ignored `build/etl/open-meteo`.
  It currently covers 2020-2023 for all 24 Maryland jurisdictions and is a
  model-feature candidate, not the selected public weather source.
- Maryland 2024 Lyme outcomes now come from the MDH PDF because CDC public-use
  county outputs still stop at 2023. Those 2024 rows are flagged
  `mdh_probable_only_2024` and `state_source_not_cdc_public_use`; with Census
  2024 denominators now materialized, they enter the local model panel.
- Pennsylvania 2024 Lyme county rows can be appended to the Mid-Atlantic
  regional panel from the official PA DOH workbook. They are state-source
  regional research rows, not public Maryland defaults; suppressed county
  values are represented as zero with explicit suppression flags.
- Census 2024-2025 county population denominators come from the official
  keyless `CO-EST2025-alldata` CSV, while older rows currently remain from the
  prior API-era pulls.
- The annual forecast artifact is a target-year forecast output, not a
  rolling-origin evaluation. Current 2026 rows are trained through the declared
  2024 origin and use flagged projected 2026 population denominators; they do
  not contain observed 2026 Lyme outcomes, actuals, residuals, or error
  columns. Runs and predictions preserve as-of date, data cutoff, source
  vintage, and update mode.
- The regional annual forecast artifact applies the same no-observed-target
  boundary to the DE/DC/MD/PA/VA/WV incidence panel. Current 2026 rows are
  trained through the latest coverage-complete regional incidence origin year,
  2023, for the target-year forecast geography and use projected 2026 regional
  population denominators. Partial state-source overlays and stale
  boundary-change geographies are diagnostic unless an origin is explicitly
  requested. Regional forecast runs and predictions carry the same
  as-of/cutoff/source-vintage/update-mode contract, and analog rows preserve
  matched origin/outcome years plus match distance.
- The regional forecast-capacity artifact compares 2026 forecast branch totals
  with historical reported-case and incidence ranges using only years at or
  before the forecast origin and complete historical rows for the same forecast
  county set. It is a control-limit review tool, not an observed 2026 outcome
  or latent true disease-capacity estimate.
- The regional county adjacency artifact uses current Census TIGERweb county
  geometry for DE/DC/MD/PA/VA/WV. It treats state as display/rollup metadata
  and keeps cross-border neighbors, but it is still a county-aggregation
  support graph rather than a continuous measured risk surface.

Last updated: 2026-05-29.
