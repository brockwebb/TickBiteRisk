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
| `maryland_lyme_pdf` | Maryland Department of Health Lyme PDF, 2013-2024 | Maryland county-year | Maryland cross-check and source context | acquired |
| `cdc_lyme_seasonality` | CDC Lyme onset by MMWR week and month | National week/month | Static seasonal allocation from annual predictions to county-week baseline | active_etl |
| `noaa_ghcnd` | NOAA daily station observations | Station-day to county-week/year | Weather feature candidates and backtesting inputs | active_etl |
| `census_county_reference` | Census Gazetteer county file | County | County names, FIPS, land/water area, internal points | active_etl |
| `census_population` | Census PEP/intercensal population APIs | County-year | Incidence denominators and per-capita feature normalization | active_etl |
| `maryland_dnr_deer_harvest` | Maryland DNR deer harvest tables and annual reports | County-season | Host-pressure proxy; prior completed season maps into model year | active_etl |
| `cdc_tick_vector_status` | CDC public tick vector county table | County/species/status | Vector presence/status feature candidates | active_etl |
| `cdc_tick_pathogen_status` | CDC public Ixodes pathogen county table | County/pathogen/status | Pathogen detection feature candidates | active_etl |
| `nlcd_mrlc` | MRLC/NLCD land cover files | Raster/county summary candidate | Habitat and forest/edge proxy source | acquired_needs_feature_depth |
| `census_bps` | Census Building Permits Survey county files | County-year | Contact/land-use pressure proxy | active_etl |
| `maryland_mast_reports` | Maryland DNR mast/acorn reports | Region/report | Ecological food pulse candidate | acquired_low_confidence |
| `nssp_coverage` | NSSP coverage map table | County/status | Feasibility check for future ED tick-bite feed | acquired_not_model_input |
| `capc_dog_serology` | CAPC canine Lyme data | County/month | Possible veterinary sentinel source | not_redistributed_license_sensitive |

## Potential source and feature candidates

These are not current public-runtime inputs. They are candidate feeds or derived
feature ideas to test in time-aware backtests before any public model claim.

| Source ID | Candidate | Grain | Why try it | Status |
| --- | --- | --- | --- | --- |
| `open_meteo_archive_md_county_daily` | Open-Meteo historical/reanalysis weather | County-day | Humidity, dew point, soil moisture, soil temperature, evapotranspiration, and wind fields that NOAA GHCND does not currently populate | candidate_etl_supported_backfill_pending |
| `usda_fia_fiadb` | USDA Forest Service FIA / FIADB / EVALIDator | Forest inventory estimate | Oak-hickory and forest-composition context that may be more biologically meaningful than generic forest percent | source_manifested_needs_feature_extraction |
| `maryland_dnr_archery_hunter_survey` | Maryland DNR Archery Hunter / Bowhunter Survey | Hunter report / county-season if extractable | Host and wildlife observation proxy, potentially lighter than raster GIS if report tables are defensible | source_manifested_needs_review |
| `usda_nass_maryland_cdl` | USDA NASS Cropland Data Layer / CropScape | Raster/county summary candidate | Annual crop, pasture, hay, and open-land change context around land-use and edge habitat | source_manifested_needs_feature_extraction |
| `noaa_cpc_enso_index` | NOAA CPC ENSO index, ONI/RONI | Global seasonal climate index | El Nino / La Nina phase as a lagged climate-regime overtone, likely prior winter/spring only | candidate_needs_etl |
| `noaa_psl_mei_v2` | NOAA PSL Multivariate ENSO Index v2 | Global bimonthly climate index | Ocean-atmosphere ENSO strength companion to ONI/RONI, useful only as lagged broad climate context | candidate_needs_etl |
| `cdc_tick_bite_tracker` | CDC Tick Bite Data Tracker | HHS region/week dashboard | Activity overlay if backing data becomes available; current public dashboard grain is not county-year | candidate_missing_bulk_data |
| `inaturalist_tick_observations` | iNaturalist tick observations | Point observation | Experimental tick-observation activity proxy if normalized by observer effort and license terms | candidate_bias_sensitive |
| `gbif_tick_occurrences` | GBIF tick occurrence records | Point occurrence | Comparator for public tick observations and museum/citizen-science records, with per-record license review | candidate_bias_sensitive |
| `park_attendance_county_year` | Park attendance or trail-use records | Park/county/agency-year | Outdoor exposure denominator proxy if a reliable Maryland source can be found | candidate_needs_source_selection |
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
| `model_comparison_predictions.csv` | `tickbiterisk etl model-compare` | Rolling-origin predictions from candidate model branches |
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
- ENSO and composite ecological-pressure features are not implemented yet. If
  tested, they should use timing-safe lags and preserve component values rather
  than hiding source uncertainty inside a single score.

Last updated: 2026-05-27.
