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

## Current v0 derived artifacts

| Artifact | Producer | Use |
| --- | --- | --- |
| `lyme_county_year_reconciled.csv` | `tickbiterisk etl lyme-outcomes` | Maryland Lyme outcome panel with source reconciliation flags |
| `county_population_year.csv` | `tickbiterisk etl census-population` | County-year population denominators |
| `county_reference.csv` | `tickbiterisk etl county-reference` | County FIPS, names, land area, and internal points |
| `weather_features_weekly.csv` | `tickbiterisk etl noaa-weather-features` | Weekly weather predictors and quality flags |
| `model_feature_matrix.csv` | `tickbiterisk etl model-features` | Model-ready joined county-year panel |
| `model_design_matrix.csv` | `tickbiterisk etl model-design-matrix` | Numeric feature matrix and schema sidecar |
| `model_comparison_predictions.csv` | `tickbiterisk etl model-compare` | Rolling-origin predictions from candidate model branches |
| `seasonality_baseline.csv` | `tickbiterisk etl seasonality-baseline` | CDC weekly/monthly Lyme onset share baseline |
| `county_week_seasonal_risk_baseline.csv` | `tickbiterisk etl county-week-risk` | Product-shaped county-week relative risk rows |
| `risk_baseline.json` | `tickbiterisk risk export-static` | Public dashboard score payload |
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

Last updated: 2026-05-27.
