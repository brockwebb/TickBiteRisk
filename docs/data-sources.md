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
| `maryland_lyme_pdf` | Maryland Department of Health Lyme PDF, 2013-2024 | Maryland county-year | Latest Maryland 2024 outcome lane, with overlapping years kept as validation context | active_etl_latest_2024 |
| `cdc_lyme_seasonality` | CDC Lyme onset by MMWR week and month | National week/month | Static seasonal allocation from annual predictions to county-week baseline | active_etl |
| `noaa_ghcnd` | NOAA daily station observations | Station-day to county-week/year | Weather feature candidates and backtesting inputs | active_etl |
| `census_county_reference` | Census Gazetteer county file | County | County names, FIPS, land/water area, internal points | active_etl |
| `census_population` | Census PEP/intercensal population APIs and county totals CSV | County-year | Incidence denominators and per-capita feature normalization through 2025 | active_etl |
| `maryland_dnr_deer_harvest` | Maryland DNR deer harvest tables and annual reports | County-season | Host-pressure proxy; prior completed season maps into model year | active_etl |
| `cdc_tick_vector_status` | CDC public tick vector county table | County/species/status | Vector presence/status feature candidates | active_etl |
| `cdc_tick_pathogen_status` | CDC public Ixodes pathogen county table | County/pathogen/status | Pathogen detection feature candidates | active_etl |
| `nlcd_mrlc` | MRLC/NLCD land cover files | Raster/county summary candidate | Habitat and forest/edge proxy source | acquired_needs_feature_depth |
| `census_bps` | Census Building Permits Survey county files | County-year | Contact/land-use pressure proxy | active_etl |
| `maryland_mast_reports` | Maryland DNR mast/acorn reports | Region/report | Ecological food pulse candidate | acquired_low_confidence |
| `noaa_cpc_oni` | NOAA CPC Oceanic Nino Index | Global seasonal climate index | Lagged ENSO phase overtone candidate; materialized as complete prior-year model features, not joined into public model yet | active_etl_candidate_feature |
| `nssp_coverage` | NSSP coverage map table | County/status | Feasibility check for future ED tick-bite feed | acquired_not_model_input |
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
| `noaa_psl_mei_v2` | NOAA PSL Multivariate ENSO Index v2 | Global monthly climate index | Ocean-atmosphere ENSO strength companion to ONI/RONI, useful only as lagged broad climate context | candidate_needs_etl |
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

## Current v0 derived artifacts

| Artifact | Producer | Use |
| --- | --- | --- |
| `lyme_county_year_reconciled.csv` | `tickbiterisk etl lyme-outcomes` | Maryland Lyme outcome panel with source reconciliation flags |
| `county_population_year.csv` | `tickbiterisk etl census-population` | County-year population denominators |
| `county_reference.csv` | `tickbiterisk etl county-reference` | County FIPS, names, land area, and internal points |
| `weather_features_weekly.csv` | `tickbiterisk etl noaa-weather-features` | Weekly weather predictors and quality flags |
| `model_features_county_year.csv` | `tickbiterisk etl model-features` | Model-ready joined county-year panel |
| `model_design_matrix_county_year.csv` | `tickbiterisk etl model-design-matrix` | Numeric feature matrix |
| `model_design_matrix_schema.json` | `tickbiterisk etl model-design-matrix` | Design-matrix schema sidecar |
| `regional_outcome_stress_predictions.csv` | `tickbiterisk etl regional-outcome-stress` | Mid-Atlantic outcome-only capacity-share stress predictions |
| `regional_outcome_stress_metrics.csv` | `tickbiterisk etl regional-outcome-stress` | Case-count MAE/RMSE metrics for regional historical-range baselines |
| `model_comparison_predictions.csv` | `tickbiterisk etl model-compare` | Rolling-origin predictions from candidate model branches |
| `model_comparison_intervals.csv` | `tickbiterisk etl model-compare` | Bootstrap prediction intervals companion artifact for comparison branches |
| `noaa_cpc_oni_seasons.csv` | `tickbiterisk etl enso-oni` | NOAA CPC ONI seasonal anomalies and El Nino / La Nina phase labels |
| `noaa_cpc_oni_model_year_features.csv` | `tickbiterisk etl enso-oni` | Complete prior-year ONI model-year climate context features |
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

- NSSP tick-bite ED data is not wired into the current model. The acquired
  coverage table only tells us where future work may be feasible.
- Mast/acorn reports are currently low-confidence for structured county-year
  extraction and should be treated as notes until better extraction or manual
  review exists.
- Land-cover features need deeper county summarization before they should drive
  public model claims.
- ONI ETL and model joins are implemented as lagged global climate context
  artifacts. The first time-aware backtest did not improve the selected public
  branch, so RONI, MEI.v2, and composite ecological-pressure features still
  need separate evidence before any public model claim.
- Open-Meteo recent backfill is local under ignored `build/etl/open-meteo`.
  It currently covers 2020-2023 for all 24 Maryland jurisdictions and is a
  model-feature candidate, not the selected public weather source.
- Maryland 2024 Lyme outcomes now come from the MDH PDF because CDC public-use
  county outputs still stop at 2023. Those 2024 rows are flagged
  `mdh_probable_only_2024` and `state_source_not_cdc_public_use`; with Census
  2024 denominators now materialized, they enter the local model panel.
- Census 2024-2025 county population denominators come from the official
  keyless `CO-EST2025-alldata` CSV, while older rows currently remain from the
  prior API-era pulls.

Last updated: 2026-05-28.
