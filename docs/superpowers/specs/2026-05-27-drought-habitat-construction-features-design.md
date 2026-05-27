# Drought, Habitat, and Construction Feature Design

Date: 2026-05-27
Status: Approved design, pre-implementation
Scope: Defensible next feature layer for Maryland county-year Lyme model comparison

## Goal

Add three defensible feature families that may improve county-year Lyme disease risk modeling without starting a raster, park-attendance, or bespoke geospatial workflow:

- U.S. Drought Monitor county drought features.
- EPA EnviroAtlas static county habitat features.
- Lagged and trailing construction pressure features derived from existing Census BPS outputs.

Mast/acorn remains preserved as prior-year ecology data, but the latest comparison showed it did not improve the current ecology ridge lanes. That result should remain visible rather than forcing mast into the public branch.

## Source Decisions

### U.S. Drought Monitor

Use the U.S. Drought Monitor county statistics REST endpoints:

```text
https://usdmdataservices.unl.edu/api/CountyStatistics/GetDSCI
https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent
```

The county DSCI endpoint returns weekly rows keyed by state, county, FIPS, map date, and DSCI. The drought severity endpoint returns percent county area in `None`, `D0`, `D1`, `D2`, `D3`, and `D4`.

Build county-year aggregates for Maryland from 2000 through the latest Lyme model year:

- `usdm_dsci_mean`
- `usdm_dsci_max`
- `usdm_weeks_d0_or_worse`
- `usdm_weeks_d1_or_worse`
- `usdm_weeks_d2_or_worse`
- `usdm_tick_season_dsci_mean`
- `usdm_tick_season_weeks_d1_or_worse`

Same-year drought features are retrospective reconstruction features. Forecast-safe model lanes can use prior-year or pre-season drought summaries later, but this slice should first materialize the auditable county-year panel and let model comparison decide whether the signal helps.

### EPA EnviroAtlas

Use the EPA EnviroAtlas county landscape ArcGIS REST layer:

```text
https://enviroatlas.epa.gov/arcgis/rest/services/Other/CMA_Landscape/MapServer/1
```

Query Maryland county rows without geometry. Keep a static county-level habitat table with direct FIPS joins. Initial fields:

- `forest_pct`
- `forest_woody_wetland_pct`
- `wetland_pct`
- `emergent_wetland_pct`
- `developed_pct`
- `impervious_pct`
- `agriculture_pct`
- `pasture_hay_pct`
- `cultivated_crop_pct`
- `riparian_natural_45m_pct`
- `riparian_forest_45m_pct`
- `riparian_forest_woody_wetland_45m_pct`
- `natural_land_cover_index`

Treat these as static habitat suitability/context features, not annual land-cover-change features.

### Construction Pressure Lags

Use existing `contact_pressure_features_county_year.csv` rather than acquiring new data. Add derived prior/trailing construction features:

- prior-year units per square mile
- prior-year units per 100k population
- trailing 3-year mean units per square mile
- trailing 3-year mean units per 100k population
- year-over-year units-per-square-mile change

These are more forecast-safe than same-year construction pressure and may capture recent land-use/contact changes.

## Non-Goals

- No park attendance model feature in this slice. NPS and Maryland DNR park data are official but too partial, spatially mismatched, or residence-vs-visit ambiguous for current county-year Lyme modeling.
- No NLCD/CDL raster processing.
- No FIA forest-type estimates in this slice. FIA remains a future forest-composition candidate.
- No public dashboard branch change unless model comparison supports it and wording remains informational, not medical advice.

## Modeling Integration

Add optional feature joins to `model-features`:

- same-year USDM drought summaries as retrospective comparison features;
- static EnviroAtlas habitat features for every county-year;
- lagged/trailing construction pressure derived from existing contact-pressure rows.

The design matrix should include numeric fields and missingness indicators for optional source families. Model comparison should include drought, habitat, and construction-lag fields in ecology/retrospective lanes. Forecast-safe lanes should include only features whose timing is defensible before the prediction year.

Quality flags must distinguish:

- `drought_monitor_retro_observed`
- `static_enviroatlas_2011`
- `construction_proxy_only`
- `missing_usdm_drought`
- `missing_enviroatlas_habitat`
- `missing_construction_lag`

## Acceptance Criteria

- USDM ETL writes Maryland county-week raw/normalized rows and county-year drought features.
- EnviroAtlas ETL writes 24 Maryland static habitat rows.
- Construction lag features are generated from existing contact-pressure artifacts.
- `model-features`, `model-design-matrix`, and `model-compare` include the new features with leakage-aware selector behavior.
- Model comparison is rebuilt and the summary is reported honestly, including if the new features do not improve held-out MAE.
- Tests, ruff, and dashboard smoke pass.
