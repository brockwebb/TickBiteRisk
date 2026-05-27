# TickBiteRisk Data Manifest

Version: 0.1 draft  
Date: 2026-05-25
Scope: Maryland-first tick-risk warehouse and modeling inputs

## Status Legend

- `acquired`: local file exists.
- `etl_supported`: this ETL slice has parser/schema support.
- `etl_supported_limited`: this ETL slice is implemented but intentionally emits only supported structured values and summary diagnostics when extraction is low-confidence.
- `etl_materialized`: normalized output has been written by a live ETL smoke run.
- `needs_etl`: source is acquired but not normalized.
- `needs_reconciliation`: source conflicts with another source or requires canonical selection.
- `candidate`: useful but not yet acquired or validated.
- `needs_acquisition`: source is identified but not saved locally.
- `source_manifested`: raw source file/page is catalogued in an ETL source manifest.
- `feature_extraction_pending`: source is acquired but feature derivation is deferred.
- `parser_scaffolded`: parser and output contracts exist, but source text did not produce accepted structured values in the latest smoke.
- `parser_pending`: source is acquired but no normalized parser is accepted yet.
- `missing`: needed for planned model but not acquired.
- `optional`: useful if access/licensing can be resolved.

## Source Catalog

| ID | Source | Local path / URL | Format | Geography | Time coverage | Role | Status | Redistribution | SHA-256 / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cdc_lyme_public_1992_2007` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_1992-2007_20260523.csv` | CSV | State, county FIPS with suppressed rows | 1992-2007 | Outcome, provenance | acquired, etl_supported, etl_materialized | Public CDC data; keep source metadata | `c28452bf97ee88a133bd8530b55db1718e77f25f6899d4d504a6bb2e290b4877` |
| `cdc_lyme_public_2008_2021` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_2008-2021_20260523.csv` | CSV | State, county FIPS with suppressed rows | 2008-2021 | Outcome, provenance | acquired, etl_supported, etl_materialized | Public CDC data; keep source metadata | `1e609716eb0b059731899f6be1927dbb2cd6caacb82a73bcc8ab4fc5afbd7714` |
| `cdc_lyme_public_2022_2023` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_2022-2023_20260523.csv` | CSV | State, county FIPS with suppressed/unknown rows | 2022-2023 | Outcome, provenance | acquired, etl_supported, etl_materialized | Public CDC data; case definition changed | `635ea73cbdf8b376544b8e29ae4395a433e693b064c79de53c7a173b4f645562` |
| `cdc_lyme_county_dashboard_2023` | CDC Lyme county counts dashboard export | `/Users/brock/Downloads/LD_Case_Counts_by_County_2023_updated.csv` | CSV, latin1 | County | 2001-2023 | Outcome, reconciliation | acquired, etl_supported, etl_materialized | Public CDC dashboard export | `e2fe2d71dbce065d7c89430bc3c9fede9392831d9856b636339aac00655fae45`; requires non-UTF-8 read |
| `cdc_lyme_county_geodata_2000_2021` | CDC county Lyme geodata | `/Users/brock/Downloads/Lyme_Diseases_Cases_by_US_County_2000_2021_Geodata.csv` | CSV | County FIPS plus geometry attributes | 2000-2021 | Outcome, geography, reconciliation | acquired, etl_supported, etl_materialized | Public CDC/dashboard geodata | `cf650fb867dfbfbafb02b9e2a40a7690bd33b8d80003630f95c6fffe0d06e7a6` |
| `cdc_lyme_county_geodata_geojson` | CDC county Lyme geodata geometry | `/Users/brock/Downloads/Lyme_Diseases_Cases_by_US_County_2000_2021_Geodata.geojson` | GeoJSON | County geometry | 2000-2021 | Geometry, optional map output | acquired, needs_etl | Large local geodata; do not commit | 89 MB; checksum not captured yet |
| `mdh_lyme_2013_2024_pdf` | Maryland DHMH/MDH Lyme Disease Data 2013 to 2024 | `https://health.maryland.gov/phpa/OIDEOR/CZVBD/Shared%20Documents/Lyme%20Disease%20Data%202013%20to%202024.pdf` | PDF | Maryland jurisdictions | 2013-2024 | Outcome, state-specific validation | candidate, needs_acquisition, needs_etl | Public state PDF | Important for 2024; 2024 probable-only caveat |
| `cdc_caseincid_cases_state_2023` | CDC Lyme cases by state/locality | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Cases-by-State-or-Locality.csv` | CSV, latin1 | State/locality | 2008-2023 | State validation | acquired, needs_etl | Public CDC dashboard export | `ecc6b60823cb32c7c0b9c0522817beca967a771f29cf29a11f970d5bb19e8e61` |
| `cdc_caseincid_rates_state_2023` | CDC Lyme rates by state/locality | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Rates-by-State-or-Locality.csv` | CSV | State/locality | 2010-2023 | State validation, population-implied checks | acquired, needs_etl | Public CDC dashboard export | `1b12baba495bc96d412ac96fa6176b265de26e65106681b74ab29cc3d4dc0488` |
| `cdc_caseincid_overall_cases_2023` | CDC overall Lyme cases by year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Overall-Cases-by-Year.csv` | CSV | United States | 1996-2023 | National validation | acquired, needs_etl | Public CDC dashboard export | `521879552c7d30bc881435adfd95223ac06a2777749027233329384dc592d4c5` |
| `cdc_caseincid_overall_rate_2023` | CDC overall Lyme incidence by year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Overall-Rate-by-Year.csv` | CSV | United States | 1996-2023 | National validation | acquired, needs_etl | Public CDC dashboard export | `b876a9050e292a2b9491fd967552a0ec35b9acced5bab8c33cb3cd21019b2a8e` |
| `cdc_caseincid_cases_region_2023` | CDC Lyme cases by region/year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Cases-by-Year-and-Region.csv` | CSV | Census/CDC region | 2010-2023 | Regional validation | acquired, needs_etl | Public CDC dashboard export | `29d769b3994df220a53e28a3f06abc8b0d6836d9145912f5bcde0379cb9994e5` |
| `cdc_caseincid_rates_region_2023` | CDC Lyme rates by region/year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Rates-by-Year-and-Region.csv` | CSV | Census/CDC region | 2010-2023 | Regional validation | acquired, needs_etl | Public CDC dashboard export | `225d0c8218bb20b7c4580edec7142c6c1443076af32294f5a6273396499b9af0` |
| `cdc_seasonality_week_2023` | CDC Lyme cases by week of disease onset | `/Users/brock/Downloads/2023_Seasonality-Lyme-Disease-Cases-by-Week-of-Disease-Onset.csv` | CSV | United States | 2010-2023 | Seasonality prior | acquired, etl_supported, etl_materialized | Public CDC dashboard export | `2a04e4d7dfab5e69d94111db03edda299740942aa66774710ef8172e379877da`; live smoke wrote 742 weekly observation rows and 53 baseline rows |
| `cdc_seasonality_month_2023` | CDC Lyme cases by month of disease onset | `/Users/brock/Downloads/2023_Seasonality-Lyme-Disease-Cases-by-Month-of-Disease-Onset.csv` | CSV | United States | 2010-2023 | Seasonality prior | acquired, etl_supported, etl_materialized | Public CDC dashboard export | `3eea52bca3bd892bc01a3c58a52a9b63d6d7db9751bf91ca4722209e2a5015e5`; live smoke wrote 168 monthly observation rows and 12 baseline rows |
| `cdc_demographic_age_sex_rates_2023` | CDC Lyme rates by age group and sex | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Rates-Among-Cases-by-Age-Group-and-Sex.xlsx` | XLSX | United States | 2010-2023 | Reference, optional risk communication | acquired, optional | Public CDC dashboard export | `119d42a59a42450f6a728ea8bac3de1edb8c62aec7a97a018bead4e08fbe2bca` |
| `cdc_demographic_age_year_percent_2023` | CDC Lyme percent of total cases by age group/year | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Percent-of-Total-Cases-by-Age-Group-and-Year.xlsx` | XLSX | United States | 2010-2023 | Reference, optional risk communication | acquired, optional | Public CDC dashboard export | `87b3957734a7f179e9565e96a2f5c3d19bd5d90dc110d78699b4b0022484b727` |
| `cdc_demographic_race_cases_2023` | CDC Lyme cases by race | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Number-of-Cases-by-Race.csv` | CSV | United States | 2010-2023 | Reference only | acquired, optional | Public CDC dashboard export | `79d614dd89e12d9827eb242b3d15fb784112f217a36e6299260a211861a182d0` |
| `cdc_ixodes_county_status_2025` | CDC ArboNET Ixodes county status | `/Users/brock/Downloads/Public_Use_Ixodes_County_Table_2026_03252026.xlsx` | XLSX | County | Through 2025 | Vector status predictor | acquired, etl_supported, etl_materialized | Restricted data-use language; do not redistribute raw/derived full table without review | `e35a5066a7c77b2e79c50f315a18e042405ab7baa8a414a1a907792bb25d2adc`; live smoke wrote 24 Maryland rows |
| `cdc_ixodes_pathogen_status_2025` | CDC ArboNET Ixodes pathogen status | `/Users/brock/Downloads/Public_Use_Ixodes_Pathogens_County_Table_2026_04292026.xlsx` | XLSX | County | Through 2025 | Pathogen status predictor | acquired, etl_supported, etl_materialized | Restricted data-use language; status only, not prevalence | `68baef5f20b1e41821d0e6955cbb1809262e0f3624e387e88c04f6ddb0266f2f`; live smoke wrote 24 Maryland rows |
| `cdc_lone_star_status_2024` | CDC Amblyomma americanum surveillance map data | `/Users/brock/Downloads/2024-A.americanum-Surveillance-Map-Data.xlsx` | XLSX | County | Through 2024 | Vector status predictor for ehrlichiosis/SFR/tularemia context | acquired, etl_supported, etl_materialized | Public CDC workbook; verify terms | `6db7d7e40ca1ddd340edac762bab9d8e12b0b4ba8ecfbd6dd15991118de101d7`; live smoke wrote 24 Maryland rows |
| `cdc_all_tbd_2022_public` | CDC all tickborne disease county counts 2022 | `/Users/brock/Downloads/AllTBD2022_Public.xlsx` | XLSX | County | 2022 | Noncanonical comparator, multi-disease context | acquired, needs_etl, needs_reconciliation | Public workbook but source definition needs verification | `2368973bae062df40e7815815917ed9311de52873e1e31820cb7d36d885e8584`; MD Lyme total conflicts with CDC/MDH Lyme public totals |
| `nssp_coverage_2024` | NSSP coverage map table | `/Users/brock/Downloads/Coverage_Map_Tbl_2024Jul01.csv` | CSV | County | 2024 coverage status | Data availability, ED tracker feasibility | acquired, needs_etl | Public coverage table | `8860232ead3606315678386b0e3917180b899f78567bbb661aa07f0cbb82704b`; all MD jurisdictions show recent NSSP data |
| `selected_tbd_monthly` | Selected tickborne disease cases by month | `/Users/brock/Downloads/Selected_Tickborne_Disease_Cases_by_Month.csv` | CSV | United States | 2016-2019 | National seasonality, multi-disease context | acquired, optional | Public CDC/dashboard export | `9d686c6d95671e071603d73c0c1e57772c7af7560f8c4b4ea9aafc0ff438a617`; local file has 288 rows across six diseases |
| `selected_tbd_us_year` | Selected tickborne diseases United States | `/Users/brock/Downloads/Selected_Tickborne_Diseases_United-States.csv` | CSV | United States | 2016-2023 | National validation, multi-disease context | acquired, optional | Public CDC/dashboard export | `a1991bf322ae3d94a81744dc92fa9b15c8017e5f8741f6c55658f7dd76a8de40` |
| `cdc_tick_disease_database_xlsx` | User-compiled CDC tick disease database | `/Users/brock/Downloads/CDC_Tick_Disease_Database.xlsx` | XLSX | United States, mostly state/year | 1992-2023 | Reference, source checklist | acquired, optional | Derived local workbook; not canonical | `29c5fa03dc8555844f0e82e8988f5b37ba5274689b871bb77e502e4c5a1d2f8b` |
| `noaa_cdo_ghcnd_daily` | NOAA CDO Daily Summaries / GHCND | `https://www.ncei.noaa.gov/cdo-web/webservices/v2` | API JSON | Station observations mapped to Maryland counties | 1992-2026 observed station coverage | Primary observed historical raw daily weather input for `noaa_ghcnd_daily_observations`; aggregate to weekly/monthly modeling features | acquired, station_audited, fallback_supported, etl_supported, weekly_features_built | Public federal data; derived aggregates may be published with citation | Requires `NOAA_TOKEN` from environment only; strict 1992-current internal-station audit found 11/24 jurisdictions ready and 13/24 needing fallback. `--nearest-station-fallback` audit covered 24/24 jurisdictions on 2026-05-24; full Maryland pull completed 24/24 jurisdictions with 283,420 raw daily rows dated 1992-01-01 through 2026-05-21. `noaa-weather-features` produced 40,919 weekly rows and 9,421 monthly rows; humidity/soil/evapotranspiration/rain-split fields are null and quality-flagged for NOAA-derived rows |
| `open_meteo_archive_md_county_daily` | Open-Meteo historical weather archive | `https://archive-api.open-meteo.com/v1/archive` | API JSON/CSV | Maryland county internal points from Census Gazetteer | 1940-current available; 1992-current comparison planned | Secondary reanalysis/gap-fill weather source | candidate, etl_supported, backfill_pending | API terms apply; no key | Bounded county/date CLI path supported; archive endpoint timed out locally during smoke test |
| `census_county_reference` | Census Gazetteer county reference/area | `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip` | ZIP/TXT | County | 2024 reference | Geography, FIPS validation, land-area denominator for density features | acquired, etl_supported | Public federal data | 2026-05-24 live pull wrote 24 Maryland rows to `county_reference.csv` with land/water square miles and internal points |
| `census_tigerweb_md_counties_geojson` | Census TIGERweb Maryland county geometry | `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/82/query` | GeoJSON | Maryland counties | Current TIGERweb county layer | Public dashboard map geometry | acquired, etl_supported, static_export_supported | Public Census geography; publish simplified derived GeoJSON | `tickbiterisk dashboard build-assets` writes `public/data/md_counties.geojson` with `county_fips`, `county_name`, and geometry only. |
| `census_population` | Census PEP/intercensal county population | Census API | API JSON table | County | 1992-2023 | Incidence denominator | acquired, etl_supported, key_needed_for_live_refresh | Public federal data | ETL supports annual Maryland county denominators from 1990/2000 intercensal, 2019 PEP, and 2023 charv APIs. 2026-05-24 live pull with `CENSUS_API_KEY` wrote 768 rows covering 24 jurisdictions x 1992-2023; 2024+ API source still needs confirmation |
| `annual_nlcd_mrlc` | USGS Annual NLCD / MRLC | `https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access` plus MRLC data services | HTML/catalog now; raster/service extraction later | CONUS/Maryland county summaries targeted | 1985-2024 source coverage | Habitat, impervious, land-cover change | acquired, source_manifested, feature_extraction_pending | Public federal data | Raw source pages downloaded by `tickbiterisk etl ecology-sources`; 2026-05-25 smoke catalogued 12 ecology source files to `build/etl/ecology/source_manifest.csv`; county feature extraction waits on official summary/service decision |
| `census_bps_county` | Census Building Permits Survey county ASCII files | `https://www2.census.gov/econ/bps/County/coYY12y.txt` | TXT/CSV-like ASCII | County | 2000-2025 practical county annual files | Construction/contact pressure proxy feeding `contact_pressure_features_county_year.csv` | acquired, etl_supported | Public federal data | `tickbiterisk etl building-permits` writes Maryland county-year units authorized and valuation fields; `tickbiterisk etl contact-pressure` combines BPS rows with county reference and population denominators; 2024 smoke wrote 24 rows from `24001`/24 units to `24510`/1273 units; full 2000-2025 smoke wrote 435 deduped rows because 2000-2004 have 16 jurisdictions, 2005-2014 have 14, 2015-2021 have 17, and 2022-2025 have 24; 2026-05-25 contact-pressure smoke wrote 435 feature rows with 48 `missing_population` rows; Census files can stall before first byte and fetchers retry transient failures |
| `maryland_dnr_deer_harvest_news` | Maryland DNR deer harvest news reports | Maryland DNR News harvest pages, 2021-2026 | HTML tables | County/season/species | 2019-20 through 2025-26 | Host ecology predictor, deer-density proxy | acquired, etl_supported | Public state data; publish derived density features with citation | 2026-05-24 live pull wrote 231 county-season-species rows to `maryland_dnr_deer_harvest.csv`; covers 23 Maryland counties, excludes Baltimore City, derives all-deer totals for Caroline, Dorchester, Somerset, Wicomico, and Worcester from white-tailed deer + sika deer rows |
| `maryland_dnr_deer_annual_reports` | Maryland DNR deer/big game annual reports | `https://dnr.maryland.gov/wildlife/Pages/hunt_trap/Deer_AnnualReports.aspx` | PDF | County/season/species | 2011-12 through 2024-25 text-extractable; 2007-08 through 2010-11 OCR-pending | Host ecology predictor, deer-density proxy | acquired, etl_supported | Public state data; publish derived density features with citation | `tickbiterisk etl deer-harvest --include-annual-report-pdfs` uses `pypdfium2` by default and supports `--annual-report-parser docling`; live parser smoke extracted 460 rows for 2011-12 through 2024-25, while 2007-08 through 2010-11 did not expose reliable table text and should not be forced into the model without OCR review |
| `maryland_dnr_mast_survey` | Maryland DNR Western Maryland mast/acorn survey reports | Maryland DNR Game Mammals page plus known PDF reports | PDF/HTML | Western Maryland study plots/counties | 2017, 2020, 2021 known report PDFs acquired | Host/reservoir ecology context | acquired, source_manifested, parser_scaffolded, etl_supported_limited | Public state data likely | Localized public-land plot reports; do not generalize statewide without quality flags. The 2026-05-25 live smoke wrote 0 structured rows and 3 extraction-summary rows, all `no_supported_values` with `ocr_pending,parser_low_confidence`; optional manual mast observations are stored separately when supplied, flagged anecdotal, and are not model-default. |
| `model_features_county_year` | Maryland county-year model feature matrix | `build/etl/model/model_features_county_year.csv` | CSV | County-year | 1992-2023 | Auditable joined training panel | etl_materialized | Derived from public sources; publish with source citations and quality flags | Built by `tickbiterisk etl model-features`; refreshed 2026-05-26 run wrote 676 rows across 24 Maryland jurisdictions. Required joins: Lyme outcomes, population, calendar-apportioned weekly NOAA weather. Optional joins: contact pressure present for 385 rows, prior-season deer harvest present for 276 rows after annual-report PDFs were included; 36 rows flagged `partial_weather_year`. |
| `model_design_matrix_county_year` | Numeric Maryland county-year model design matrix | `build/etl/model/model_design_matrix_county_year.csv` and `build/etl/model/model_design_matrix_schema.json` | CSV + JSON schema | County-year | 1993-2023 rows with prior county history | Model-consumable feature matrix for stdlib baselines, ridge profiles, empirical-Bayes shrinkage, and future model lanes | etl_materialized | Derived from public sources; publish schema/caveats with model artifacts | Built by `tickbiterisk etl model-design-matrix`; 2026-05-26 live run with 5-year lookback wrote 652 rows. Keeps id/target/passthrough columns separate from numeric `feature_*` columns, adds lagged incidence features, one-hot tick status features, explicit optional-source missingness indicators, and expanded `feature_flag_*` quality indicators. |
| `model_comparison` | Rolling-origin annual model comparison | `build/etl/model-comparison/model_comparison_runs.csv`, `model_comparison_predictions.csv`, `model_comparison_metrics.csv`, `model_comparison_summary.csv` | CSV | County-year prediction/evaluation | Held-out years 2007-2023 | Model selection benchmark over normalized design matrix | etl_materialized | Derived evaluation artifact; publish with model caveats | Built by `tickbiterisk etl model-compare`; 2026-05-26 run wrote 1 run row, 2,856 prediction rows, 126 metric rows, and 7 summary rows. Summary MAE per 100k: `linear_blend_baseline` 18.240783, `prior_year_incidence` 18.32327, `ridge_forecast_safe` 19.094881, `ridge_forecast_ecology` 19.239029, `ridge_lag_weather_ecology` 19.846399, `empirical_bayes_shrinkage` 22.859609, `trailing_mean_incidence` 22.903909. Run-level `weather_mode` is `mixed_model_specific`; prediction and metric rows preserve the profile-specific weather mode. |
| `baseline_model_backtests` | Baseline annual Lyme incidence backtests | `build/etl/backtest/model_backtest_runs.csv`, `build/etl/backtest/model_backtest_predictions.csv`, and `build/etl/backtest/model_backtest_metrics.csv` | CSV | Run manifest, county-year prediction rows, and model/year metrics | Held-out years 2007-2023 from 1992-2023 model matrix | Model evaluation benchmark | etl_materialized | Derived evaluation artifact; publish with source citations and caveats | Built by `tickbiterisk etl model-backtest`; 2026-05-25 live smoke wrote 1 run row, 1,630 prediction rows, and 72 metric rows for four stdlib baselines. Overall MAE per 100k: `prior_year_incidence` 18.130652, `linear_blend_baseline` 18.203188, `state_trend_adjusted_county_mean` 18.826062, `county_trailing_mean_incidence` 20.790014. Backtest artifacts include input file SHA-256, `weather_mode=not_used_by_baseline`, and assumption flags `observational_not_causal`, `intervention_history_unmodeled`, `surveillance_reporting_sensitive`. |
| `seasonality_baseline` | CDC Lyme disease-onset seasonality baseline | `build/etl/seasonality/seasonality_observations.csv` and `build/etl/seasonality/seasonality_baseline.csv` | CSV | United States, monthly and MMWR week | 2010-2023 | Disease-onset seasonal prior and empirical prediction bands | etl_materialized | Derived from public CDC dashboard exports; publish with source citations and quality flags | Built by `tickbiterisk etl seasonality-baseline`; 2026-05-25 live smoke wrote 910 observation rows and 65 baseline rows. Baseline uses annual shares, not absolute case levels, and carries `national_curve_not_county_specific,shares_normalized_by_annual_total,empirical_prediction_band`. |
| `county_week_seasonal_risk_baseline` | Relative county-week Lyme seasonal risk baseline | `build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv` and `build/etl/county-week-risk/risk_score_scale.csv` | CSV | Maryland county-week | Held-out prediction years from annual model comparison | Product-shaped relative risk score baseline | etl_materialized, runtime_supported, static_export_supported | Derived artifact; publish with source citations, model version, and caveats | Built by `tickbiterisk etl county-week-risk`; refreshed 2026-05-27 run with `linear_blend_baseline` from `model_comparison_predictions.csv` wrote 21,624 county-week rows and 1 scale row. Combines a selected annual prediction branch with the selected weekly seasonality source, default `cdc_seasonality_week_2023`, then maps weekly predicted incidence to a 1-10 Maryland-relative scale using 95th percentile x 1.2 headroom. Rows preserve source SHA-256 values, seasonality source, benchmark quantile, headroom multiplier, and denominator so alternate scoring branches can coexist. Comparison assumption flags are preserved in the existing `backtest_assumption_flags` output column for runtime compatibility. `tickbiterisk risk lookup` consumes this derived file for county/date JSON lookup. `tickbiterisk risk export-static` writes public-safe derived JSON files with one selected score branch and the latest available baseline per county/MMWR week. Carries `relative_seasonal_baseline`, `static_seasonality_prior`, and `not_weather_adjusted`. |
| `usda_nass_maryland_cdl` | USDA NASS Maryland Cropland Data Layer | `https://data.nass.usda.gov/Statistics_by_State/Maryland/Publications/Cropland_Data_Layer/index.php` plus CropScape | HTML/catalog now; raster/service extraction later | Maryland/CONUS raster products | Annual CDL products, source page current snapshot | Agriculture/land-use context | acquired, source_manifested, feature_extraction_pending | Public federal data | Raw source pages downloaded by `tickbiterisk etl ecology-sources`; county agriculture feature extraction deferred until raster/service workflow is selected |
| `capc_canine_serology` | CAPC canine tickborne disease testing | CAPC maps/data | Unknown/API/scrape/license | County/year | Annual/monthly likely | Veterinary sentinel predictor | optional, missing | Licensing/access unresolved | Useful for undercount correction if legally available |
| `cdc_tick_bite_tracker` | CDC Tick Bite Data Tracker | Power BI dashboard | Dashboard, no bulk file found | HHS region/week | Current/historical dashboard | Activity overlay | candidate, missing | Public dashboard; backing data unknown | Scrape/FOIA/later; not needed for first county-year model |
| `park_attendance_county_year` | State/local/federal park attendance or trail-use records | Candidate source set not yet selected | CSV/PDF/API likely | Park, county, or managing agency | Unknown | Human outdoor activity/exposure denominator candidate | candidate, needs_acquisition, feature_extraction_pending, optional | Source-specific terms unknown | Parking lot only. Useful as an outdoor recreation proxy if available, but park visits do not prove tick exposure, and Lyme surveillance often reflects residence/reporting county rather than the county where a tick was acquired. |

## Acquisition Checklist

### Acquired, Materialized, Or Ready For ETL

- CDC Lyme public-use CSVs for 1992-2023; materialized into `build/etl/lyme/lyme_county_year_reconciled.csv`.
- CDC Lyme county dashboard export through 2023; materialized into `build/etl/lyme/lyme_county_year_reconciled.csv`.
- CDC Lyme county geodata for 2000-2021; materialized into `build/etl/lyme/lyme_county_year_reconciled.csv`.
- CDC dashboard seasonality exports; materialized into `build/etl/seasonality/seasonality_observations.csv` and `build/etl/seasonality/seasonality_baseline.csv`.
- County-week seasonal risk baseline; materialized into `build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv` after model comparison predictions and seasonality ETL are available.
- CDC Ixodes vector status workbook; materialized into `build/etl/tick-status/tick_vector_status.csv`.
- CDC Ixodes pathogen status workbook; materialized into `build/etl/tick-status/tick_pathogen_status.csv`.
- CDC lone star tick status workbook; materialized into `build/etl/tick-status/lone_star_status.csv`.
- Combined tick status feature table; materialized into `build/etl/tick-status/tick_status_county_features.csv`.
- NSSP coverage table.
- `AllTBD2022_Public` comparator workbook.
- Maryland weather county internal points from Census Gazetteer 2024.
- Maryland DNR deer harvest news tables for 2019-20 through 2025-26.
- Maryland DNR annual deer/big-game report PDFs for text-extractable 2011-12 through 2024-25.

### Needs Review Before Modeling

- 33 CDC Lyme outcome rows where public-use, county dashboard, or geodata sources disagree; `lyme_county_year_reconciled.csv` preserves these as `reconciliation_status=conflict`.
- MDH 2013-2024 PDF vs. CDC public-use/dashboard values.
- `AllTBD2022_Public` vs. official CDC/MDH Lyme totals.
- 2022+ Lyme case-definition change.
- 2020 COVID reporting disruption.

### Still Needed

- Maryland county population denominators for 2024+ once a newer Census PEP API source is confirmed.
- Maryland county boundary geometries from Census/TIGER or equivalent for maps and habitat joins.
- Open-Meteo reanalysis comparison/gap-fill backfill if archive endpoint is reliable.
- OCR or manual review for Maryland DNR annual deer reports from 2007-08 through 2010-11 if those older host-proxy years become worth the effort.
- Mast/acorn survey data where usable.
- Habitat county summaries from NLCD or an equivalent precomputed source.
- ZIP-to-county/ZCTA mapping for user lookup.

### Optional / Later

- CAPC canine serology.
- CDC tick-bite ED tracker backing data.
- Park attendance or trail-use data as a possible human outdoor activity proxy.
- National expansion sources outside Maryland.

## Canonical Source Rules Draft

For Maryland Lyme county-year modeling:

1. Prefer official CDC public-use aggregated geography files for raw case provenance.
2. Use CDC county dashboard/geodata files to simplify county-year extraction, but reconcile them back to public-use totals.
3. Use MDH PDF/table as Maryland-specific validation and likely canonical source for 2024.
4. Treat `AllTBD2022_Public` as a comparator until its source definition is verified.
5. Never use current cumulative vector/pathogen status as if it were known in earlier historical years unless the model run is labeled as retrospective reconstruction.

## Lyme Outcome ETL Target

The Lyme outcome ETL slice builds `lyme_county_year_reconciled.csv` with `tickbiterisk etl lyme-outcomes --raw-dir data/raw/lyme --output-dir build/etl/lyme`.

The 2026-05-25 live smoke wrote 700 Maryland county-year rows for 24 jurisdictions from 1992-2023: 667 matched rows, 33 conflict rows, 24 rows flagged `covid_reporting_disruption`, and 48 rows flagged `lyme_case_definition_change`.

Columns:

```text
county_fips
year
confirmed_cases
probable_cases
total_cases
canonical_source_id
source_values_summary
data_quality_flags
reconciliation_status
```

`county_name` remains a later geography/reference join field and is not emitted by the current `lyme_county_year_reconciled.csv`. In the warehouse, `data_quality_flags` may be empty or nullable; use `COALESCE(data_quality_flags, '')` where string behavior is required.

The first model-ready join now materializes these fields in `model_features_county_year.csv`:

```text
population
incidence_per_100k
calendar-year weather features from weekly NOAA
optional contact-pressure features
optional prior-season deer harvest features
optional current cumulative tick vector/pathogen status features
model_feature_quality_flags
```

When `--tick-status-path` is supplied, the feature matrix appends static/cumulative vector and pathogen statuses by county and flags rows with `current_status_retrospective_proxy`, `status_only_not_prevalence`, and `no_records_not_absence` as applicable. The 2026-05-25 tick-status smoke wrote 24 county feature rows; the explicit model-feature smoke joined these fields into 676 county-year rows.

The downstream model-consumption layer now materializes:

```text
model_design_matrix_county_year.csv
model_design_matrix_schema.json
```

This design matrix is the recommended handoff for fitted models. It separates identifiers, targets, feature columns, and passthrough quality flags; one-hot encodes tick status values; adds prior-year and trailing-window Lyme incidence features; and turns optional-source gaps and quality flags into explicit numeric indicators. The 2026-05-26 live run with a 5-year lookback wrote 652 rows because county-years without any prior county history are excluded from lagged-feature modeling.

The first feature-aware comparison layer now materializes:

```text
model_comparison_runs.csv
model_comparison_predictions.csv
model_comparison_metrics.csv
model_comparison_summary.csv
```

The v0 comparison uses rolling-origin validation from the numeric design matrix and compares seven stdlib model profiles: prior-year incidence, trailing mean incidence, linear blend baseline, empirical-Bayes shrinkage, forecast-safe ridge over lag/history features, forecast-safe ridge with prior-season deer ecology, and retrospective ridge with same-year weather/ecology. Current cumulative tick-status features and surveillance-era flags are excluded from the ridge profiles. Forecast-safe profiles do not use same-year observed weather or same-year construction/contact pressure; same-year weather/ecology features are treated as retrospective reconstruction, not prospective forecast inputs. The 2026-05-26 live run ranked the linear blend baseline first by MAE.

The first baseline backtest artifact now materializes:

```text
model_backtest_runs.csv
model_backtest_predictions.csv
model_backtest_metrics.csv
```

The v0 backtest compares four annual historical baselines: prior-year incidence, county trailing mean incidence, state-trend-adjusted county mean, and a simple linear blend of prior-year and trailing mean. The live 2026-05-25 smoke used default held-out years 2007-2023 and a 5-year lookback, producing 1,630 model prediction rows and 72 metric rows. These are benchmark forecasts, not causal policy estimates; outputs carry intervention and surveillance caveat flags.

Still pending for later feature matrix versions: habitat/NLCD summaries, mast/acorn features where usable, 2024+ population denominators, and ZIP/ZCTA lookup.
