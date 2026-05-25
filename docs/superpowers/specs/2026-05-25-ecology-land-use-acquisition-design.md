# Ecology And Land-Use Acquisition Design

Date: 2026-05-25  
Status: Approved design, pre-implementation  
Scope: Maryland habitat, host, and human-contact covariates for tickborne disease risk modeling

## Purpose

The next acquisition bundle collects the data needed to represent the ecology/contact side of Maryland tick risk, not only deer harvest. This layer supports features for habitat suitability, host pressure, and human land-use/contact change while avoiding overclaiming unproven mechanisms such as construction directly forcing disease migration.

The output of this slice is source acquisition and cataloging plus enough parser scaffolding to make the data reproducible. Feature engineering and modeling remain separate follow-up slices.

## Design Summary

Acquire four source families in priority order:

1. Annual NLCD / MRLC habitat and land-cover change.
2. Census Building Permits Survey county-year construction pressure.
3. Maryland DNR mast/acorn production reports.
4. USDA NASS Cropland Data Layer as a secondary field/agriculture habitat source.

The bundle extends the existing data manifest and ETL conventions: all raw/source files stay out of git, every source gets a stable source ID, local paths and URLs are catalogued, and any credentials remain environment-only.

## Source Family 1: Annual NLCD / MRLC

Annual NLCD is the primary habitat source because it provides annual CONUS land-cover and impervious products back to 1985, covering the Lyme outcome period from 1992 onward. For Maryland, the desired derived county-year variables are:

- `forest_pct`
- `deciduous_forest_pct`
- `mixed_forest_pct`
- `woody_wetlands_pct`
- `grassland_pct`
- `pasture_hay_pct`
- `cultivated_crop_pct`
- `developed_pct`
- `impervious_pct`
- `forest_to_developed_change`
- `wetland_or_forest_loss_pct`
- `habitat_quality_flag`

Implementation must first try county-level summaries, MRLC tooling/services, or Maryland/clipped downloads. Full CONUS raster downloads are acceptable only if smaller official paths are unavailable. Raster processing is a separate implementation decision and should only enter this acquisition slice if it is the only practical way to obtain Maryland county features.

## Source Family 2: Census Building Permits

The Census Building Permits Survey is the construction/development pressure proxy. It should be treated as a contact and land-use-change indicator, not proof of animal movement.

Target variables:

- `new_residential_units_authorized`
- `new_units_per_sqmi`
- `new_units_per_1000_population`
- `construction_pressure_zscore`
- `construction_quality_flag`

Target geography is Maryland county/year. Target time coverage is 1992-current when county-level files support it. If older county-level BPS files require a different ASCII parser, the first implementation may acquire and manifest those files while deferring parser support to a later focused task.

## Source Family 3: Maryland DNR Mast / Acorn Production

Mast/acorn production should be acquired and catalogued, but modeled cautiously. The Maryland DNR Western Maryland mast reports are localized to public-land study plots and must not be generalized statewide without a clear quality flag.

Target variables:

- `mast_region`
- `survey_year`
- `county_fips` when defensible
- `oak_mast_rank`
- `overall_mast_rank`
- `mast_failure_flag`
- `mast_quality_flag`

Initial status allows partial/manual extraction. If reports are sparse or inconsistent, they remain a regional context layer rather than a county-year model feature.

## Source Family 4: USDA NASS Cropland Data Layer

CDL is a secondary habitat source for agricultural/open-field context. It is useful for pasture, hay, crop, and field-edge proxies when NLCD does not provide enough agricultural detail or when CDL summaries are easier to obtain for Maryland counties.

Target variables:

- `crop_pct`
- `pasture_hay_pct`
- `open_field_pct`
- `agriculture_change_pct`
- `cdl_quality_flag`

CDL must not block NLCD acquisition. It is an enrichment path, not the primary habitat source.

## Construction And Spillover Framing

The model must not claim construction causes migration or disease transfer. Instead, it represents testable proxies:

- Intra-county contact pressure: construction intensity, developed land, impervious surface, forest edge, and habitat fragmentation.
- Adjacent-county spillover: neighbor incidence and neighbor land-use change as lagged covariates.

Potential future features:

- `neighbor_incidence_lag1`
- `neighbor_developed_change_lag1`
- `neighbor_forest_loss_lag1`
- `adjacency_quality_flag`

These are introduced only after county adjacency/boundary data is available.

## Data Products

This acquisition slice prepares for two later normalized feature outputs:

```text
habitat_features
  county_fips
  year
  forest_pct
  deciduous_forest_pct
  mixed_forest_pct
  woody_wetlands_pct
  grassland_pct
  developed_pct
  impervious_pct
  forest_to_developed_change
  source_id
  source_url_hash
  feature_quality_flags

contact_pressure_features
  county_fips
  year
  new_residential_units_authorized
  new_units_per_sqmi
  new_units_per_1000_population
  construction_pressure_zscore
  source_id
  source_url_hash
  feature_quality_flags
```

Mast and CDL may initially land in raw/staging tables until their reliability is clearer.

## Non-Goals

- No modeling or risk-score changes in this slice.
- No claim that construction directly moves infected animals.
- No full CONUS raster processing unless Maryland-specific acquisition fails.
- No redistribution of raw raster/PDF/downloaded source data through git.
- No attempt to force sparse mast reports into a statewide feature without quality flags.

## Acceptance Criteria

This design is ready for implementation when the plan includes:

- Acquisition commands or scripts for Annual NLCD/MRLC and Census BPS.
- Manifest updates for NLCD, BPS, mast, and CDL.
- Raw data download locations under ignored directories.
- A clear decision record for sources acquired vs. deferred.
- Tests for any parser or manifest generation logic added in the implementation slice.

## Open Questions To Resolve During Implementation

- Does MRLC provide a practical official county-summary export for Annual NLCD, or do we need Maryland raster clipping/zonal statistics?
- Which BPS file layout gives the cleanest county-year Maryland history back toward 1992?
- How many Maryland mast reports are available, and are they consistent enough for structured extraction?
- Is CDL redundant after Annual NLCD, or does it add useful pasture/hay/open-field detail?
