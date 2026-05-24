# TickBiteRisk Data Manifest

Version: 0.1 draft  
Date: 2026-05-24  
Scope: Maryland-first tick-risk warehouse and modeling inputs

## Status Legend

- `acquired`: local file exists.
- `etl_supported`: this ETL slice has parser/schema support.
- `needs_etl`: source is acquired but not normalized.
- `needs_reconciliation`: source conflicts with another source or requires canonical selection.
- `candidate`: useful but not yet acquired or validated.
- `needs_acquisition`: source is identified but not saved locally.
- `missing`: needed for planned model but not acquired.
- `optional`: useful if access/licensing can be resolved.

## Source Catalog

| ID | Source | Local path / URL | Format | Geography | Time coverage | Role | Status | Redistribution | SHA-256 / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cdc_lyme_public_1992_2007` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_1992-2007_20260523.csv` | CSV | State, county FIPS with suppressed rows | 1992-2007 | Outcome, provenance | acquired, needs_etl, etl_supported | Public CDC data; keep source metadata | `c28452bf97ee88a133bd8530b55db1718e77f25f6899d4d504a6bb2e290b4877` |
| `cdc_lyme_public_2008_2021` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_2008-2021_20260523.csv` | CSV | State, county FIPS with suppressed rows | 2008-2021 | Outcome, provenance | acquired, needs_etl, etl_supported | Public CDC data; keep source metadata | `1e609716eb0b059731899f6be1927dbb2cd6caacb82a73bcc8ab4fc5afbd7714` |
| `cdc_lyme_public_2022_2023` | CDC Lyme public-use aggregated geography | `/Users/brock/Downloads/Lyme_disease_public_use_aggregated_data_with_geography,_2022-2023_20260523.csv` | CSV | State, county FIPS with suppressed/unknown rows | 2022-2023 | Outcome, provenance | acquired, needs_etl, etl_supported | Public CDC data; case definition changed | `635ea73cbdf8b376544b8e29ae4395a433e693b064c79de53c7a173b4f645562` |
| `cdc_lyme_county_dashboard_2023` | CDC Lyme county counts dashboard export | `/Users/brock/Downloads/LD_Case_Counts_by_County_2023_updated.csv` | CSV, latin1 | County | 2001-2023 | Outcome, reconciliation | acquired, needs_etl, needs_reconciliation, etl_supported | Public CDC dashboard export | `e2fe2d71dbce065d7c89430bc3c9fede9392831d9856b636339aac00655fae45`; requires non-UTF-8 read |
| `cdc_lyme_county_geodata_2000_2021` | CDC county Lyme geodata | `/Users/brock/Downloads/Lyme_Diseases_Cases_by_US_County_2000_2021_Geodata.csv` | CSV | County FIPS plus geometry attributes | 2000-2021 | Outcome, geography, reconciliation | acquired, needs_etl, needs_reconciliation, etl_supported | Public CDC/dashboard geodata | `cf650fb867dfbfbafb02b9e2a40a7690bd33b8d80003630f95c6fffe0d06e7a6` |
| `cdc_lyme_county_geodata_geojson` | CDC county Lyme geodata geometry | `/Users/brock/Downloads/Lyme_Diseases_Cases_by_US_County_2000_2021_Geodata.geojson` | GeoJSON | County geometry | 2000-2021 | Geometry, optional map output | acquired, needs_etl | Large local geodata; do not commit | 89 MB; checksum not captured yet |
| `mdh_lyme_2013_2024_pdf` | Maryland DHMH/MDH Lyme Disease Data 2013 to 2024 | `https://health.maryland.gov/phpa/OIDEOR/CZVBD/Shared%20Documents/Lyme%20Disease%20Data%202013%20to%202024.pdf` | PDF | Maryland jurisdictions | 2013-2024 | Outcome, state-specific validation | candidate, needs_acquisition, needs_etl | Public state PDF | Important for 2024; 2024 probable-only caveat |
| `cdc_caseincid_cases_state_2023` | CDC Lyme cases by state/locality | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Cases-by-State-or-Locality.csv` | CSV, latin1 | State/locality | 2008-2023 | State validation | acquired, needs_etl | Public CDC dashboard export | `ecc6b60823cb32c7c0b9c0522817beca967a771f29cf29a11f970d5bb19e8e61` |
| `cdc_caseincid_rates_state_2023` | CDC Lyme rates by state/locality | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Rates-by-State-or-Locality.csv` | CSV | State/locality | 2010-2023 | State validation, population-implied checks | acquired, needs_etl | Public CDC dashboard export | `1b12baba495bc96d412ac96fa6176b265de26e65106681b74ab29cc3d4dc0488` |
| `cdc_caseincid_overall_cases_2023` | CDC overall Lyme cases by year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Overall-Cases-by-Year.csv` | CSV | United States | 1996-2023 | National validation | acquired, needs_etl | Public CDC dashboard export | `521879552c7d30bc881435adfd95223ac06a2777749027233329384dc592d4c5` |
| `cdc_caseincid_overall_rate_2023` | CDC overall Lyme incidence by year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Overall-Rate-by-Year.csv` | CSV | United States | 1996-2023 | National validation | acquired, needs_etl | Public CDC dashboard export | `b876a9050e292a2b9491fd967552a0ec35b9acced5bab8c33cb3cd21019b2a8e` |
| `cdc_caseincid_cases_region_2023` | CDC Lyme cases by region/year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Cases-by-Year-and-Region.csv` | CSV | Census/CDC region | 2010-2023 | Regional validation | acquired, needs_etl | Public CDC dashboard export | `29d769b3994df220a53e28a3f06abc8b0d6836d9145912f5bcde0379cb9994e5` |
| `cdc_caseincid_rates_region_2023` | CDC Lyme rates by region/year | `/Users/brock/Downloads/2023_CaseIncid-Lyme-Disease-Rates-by-Year-and-Region.csv` | CSV | Census/CDC region | 2010-2023 | Regional validation | acquired, needs_etl | Public CDC dashboard export | `225d0c8218bb20b7c4580edec7142c6c1443076af32294f5a6273396499b9af0` |
| `cdc_seasonality_week_2023` | CDC Lyme cases by week of disease onset | `/Users/brock/Downloads/2023_Seasonality-Lyme-Disease-Cases-by-Week-of-Disease-Onset.csv` | CSV | United States | 2010-2023 | Seasonality prior | acquired, needs_etl | Public CDC dashboard export | `2a04e4d7dfab5e69d94111db03edda299740942aa66774710ef8172e379877da` |
| `cdc_seasonality_month_2023` | CDC Lyme cases by month of disease onset | `/Users/brock/Downloads/2023_Seasonality-Lyme-Disease-Cases-by-Month-of-Disease-Onset.csv` | CSV | United States | 2010-2023 | Seasonality prior | acquired, needs_etl | Public CDC dashboard export | `3eea52bca3bd892bc01a3c58a52a9b63d6d7db9751bf91ca4722209e2a5015e5` |
| `cdc_demographic_age_sex_rates_2023` | CDC Lyme rates by age group and sex | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Rates-Among-Cases-by-Age-Group-and-Sex.xlsx` | XLSX | United States | 2010-2023 | Reference, optional risk communication | acquired, optional | Public CDC dashboard export | `119d42a59a42450f6a728ea8bac3de1edb8c62aec7a97a018bead4e08fbe2bca` |
| `cdc_demographic_age_year_percent_2023` | CDC Lyme percent of total cases by age group/year | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Percent-of-Total-Cases-by-Age-Group-and-Year.xlsx` | XLSX | United States | 2010-2023 | Reference, optional risk communication | acquired, optional | Public CDC dashboard export | `87b3957734a7f179e9565e96a2f5c3d19bd5d90dc110d78699b4b0022484b727` |
| `cdc_demographic_race_cases_2023` | CDC Lyme cases by race | `/Users/brock/Downloads/2023_Demographic-Lyme-Disease-Number-of-Cases-by-Race.csv` | CSV | United States | 2010-2023 | Reference only | acquired, optional | Public CDC dashboard export | `79d614dd89e12d9827eb242b3d15fb784112f217a36e6299260a211861a182d0` |
| `cdc_ixodes_county_status_2025` | CDC ArboNET Ixodes county status | `/Users/brock/Downloads/Public_Use_Ixodes_County_Table_2026_03252026.xlsx` | XLSX | County | Through 2025 | Vector status predictor | acquired, needs_etl, etl_supported | Restricted data-use language; do not redistribute raw/derived full table without review | `e35a5066a7c77b2e79c50f315a18e042405ab7baa8a414a1a907792bb25d2adc` |
| `cdc_ixodes_pathogen_status_2025` | CDC ArboNET Ixodes pathogen status | `/Users/brock/Downloads/Public_Use_Ixodes_Pathogens_County_Table_2026_04292026.xlsx` | XLSX | County | Through 2025 | Pathogen status predictor | acquired, needs_etl, etl_supported | Restricted data-use language; status only, not prevalence | `68baef5f20b1e41821d0e6955cbb1809262e0f3624e387e88c04f6ddb0266f2f` |
| `cdc_lone_star_status_2024` | CDC Amblyomma americanum surveillance map data | `/Users/brock/Downloads/2024-A.americanum-Surveillance-Map-Data.xlsx` | XLSX | County | Through 2024 | Vector status predictor for ehrlichiosis/SFR/tularemia context | acquired, needs_etl, etl_supported | Public CDC workbook; verify terms | `6db7d7e40ca1ddd340edac762bab9d8e12b0b4ba8ecfbd6dd15991118de101d7` |
| `cdc_all_tbd_2022_public` | CDC all tickborne disease county counts 2022 | `/Users/brock/Downloads/AllTBD2022_Public.xlsx` | XLSX | County | 2022 | Noncanonical comparator, multi-disease context | acquired, needs_etl, needs_reconciliation | Public workbook but source definition needs verification | `2368973bae062df40e7815815917ed9311de52873e1e31820cb7d36d885e8584`; MD Lyme total conflicts with CDC/MDH Lyme public totals |
| `nssp_coverage_2024` | NSSP coverage map table | `/Users/brock/Downloads/Coverage_Map_Tbl_2024Jul01.csv` | CSV | County | 2024 coverage status | Data availability, ED tracker feasibility | acquired, needs_etl | Public coverage table | `8860232ead3606315678386b0e3917180b899f78567bbb661aa07f0cbb82704b`; all MD jurisdictions show recent NSSP data |
| `selected_tbd_monthly` | Selected tickborne disease cases by month | `/Users/brock/Downloads/Selected_Tickborne_Disease_Cases_by_Month.csv` | CSV | United States | 2016-2023 | National seasonality, multi-disease context | acquired, optional | Public CDC/dashboard export | `9d686c6d95671e071603d73c0c1e57772c7af7560f8c4b4ea9aafc0ff438a617` |
| `selected_tbd_us_year` | Selected tickborne diseases United States | `/Users/brock/Downloads/Selected_Tickborne_Diseases_United-States.csv` | CSV | United States | 2016-2023 | National validation, multi-disease context | acquired, optional | Public CDC/dashboard export | `a1991bf322ae3d94a81744dc92fa9b15c8017e5f8741f6c55658f7dd76a8de40` |
| `cdc_tick_disease_database_xlsx` | User-compiled CDC tick disease database | `/Users/brock/Downloads/CDC_Tick_Disease_Database.xlsx` | XLSX | United States, mostly state/year | 1992-2023 | Reference, source checklist | acquired, optional | Derived local workbook; not canonical | `29c5fa03dc8555844f0e82e8988f5b37ba5274689b871bb77e502e4c5a1d2f8b` |
| `noaa_cdo_ghcnd_daily` | NOAA CDO Daily Summaries / GHCND | `https://www.ncei.noaa.gov/cdo-web/webservices/v2` | API JSON | Station observations mapped to Maryland counties | 1992-2026 observed station coverage | Primary observed historical raw daily weather input for `noaa_ghcnd_daily_observations`; aggregate to weekly/monthly/seasonal modeling features | acquired, station_audited, fallback_supported, etl_supported, needs_weekly_transform | Public federal data; derived aggregates may be published with citation | Requires `NOAA_TOKEN` from environment only; strict 1992-current internal-station audit found 11/24 jurisdictions ready and 13/24 needing fallback. `--nearest-station-fallback` audit covered 24/24 jurisdictions on 2026-05-24; full Maryland pull completed 24/24 jurisdictions with 283,420 raw daily rows dated 1992-01-01 through 2026-05-21. Daily is not the modeling granularity |
| `open_meteo_archive_md_county_daily` | Open-Meteo historical weather archive | `https://archive-api.open-meteo.com/v1/archive` | API JSON/CSV | Maryland county internal points from Census Gazetteer | 1940-current available; 1992-current comparison planned | Secondary reanalysis/gap-fill weather source | candidate, etl_supported, backfill_pending | API terms apply; no key | Bounded county/date CLI path supported; archive endpoint timed out locally during smoke test |
| `census_county_reference` | Census county FIPS/reference | `https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt` | TXT/CSV | County | 2020 reference | Geography, FIPS validation | candidate, missing | Public federal data | Needed for robust county names/FIPS |
| `census_population` | Census PEP/intercensal county population | Census API | API JSON table | County | 1992-2023 | Incidence denominator | acquired, etl_supported, key_needed_for_live_refresh | Public federal data | ETL supports annual Maryland county denominators from 1990/2000 intercensal, 2019 PEP, and 2023 charv APIs. 2026-05-24 live pull with `CENSUS_API_KEY` wrote 768 rows covering 24 jurisdictions x 1992-2023; 2024+ API source still needs confirmation |
| `nlcd_habitat` | USGS/MRLC NLCD land cover | MRLC data portal | GeoTIFF/raster or summary CSV | Raster/county summary | 2021 or annual NLCD | Habitat predictor | candidate, missing | Public federal data | For MVP, precomputed county summaries are preferred over 15GB raw raster |
| `maryland_dnr_deer_harvest` | Maryland DNR deer harvest | Maryland DNR website | HTML/PDF/CSV unknown | County/year | Annual | Host ecology predictor | candidate, missing | Public state data likely | Needed as deer density proxy |
| `maryland_dnr_mast_survey` | Maryland DNR mast/acorn survey | Maryland DNR wildlife reports | PDF/HTML | Western MD plots/counties | Annual where available | Host/reservoir ecology predictor | candidate, missing | Public state data likely | Likely Western MD only; use lagged features carefully |
| `capc_canine_serology` | CAPC canine tickborne disease testing | CAPC maps/data | Unknown/API/scrape/license | County/year | Annual/monthly likely | Veterinary sentinel predictor | optional, missing | Licensing/access unresolved | Useful for undercount correction if legally available |
| `cdc_tick_bite_tracker` | CDC Tick Bite Data Tracker | Power BI dashboard | Dashboard, no bulk file found | HHS region/week | Current/historical dashboard | Activity overlay | candidate, missing | Public dashboard; backing data unknown | Scrape/FOIA/later; not needed for first county-year model |

## Acquisition Checklist

### Acquired And Ready For ETL

- CDC Lyme public-use CSVs for 1992-2023.
- CDC Lyme county dashboard export through 2023.
- CDC Lyme county geodata for 2000-2021.
- CDC dashboard seasonality exports.
- CDC Ixodes vector status workbook.
- CDC Ixodes pathogen status workbook.
- CDC lone star tick status workbook.
- NSSP coverage table.
- `AllTBD2022_Public` comparator workbook.
- Maryland weather county internal points from Census Gazetteer 2024.

### Needs Reconciliation Before Modeling

- CDC Lyme public-use county totals vs. CDC county dashboard export.
- CDC county geodata vs. public-use files.
- MDH 2013-2024 PDF vs. CDC public-use/dashboard values.
- `AllTBD2022_Public` vs. official CDC/MDH Lyme totals.
- 2022+ Lyme case-definition change.
- 2020 COVID reporting disruption.

### Still Needed

- Maryland county population denominators by year via the implemented Census API ETL after `CENSUS_API_KEY` is added locally.
- Maryland county boundary geometries from Census/TIGER or equivalent for maps and habitat joins.
- Full Maryland NOAA CDO/GHCND daily weather acquisition run using the audited strict-plus-nearest-station fallback plan.
- Open-Meteo reanalysis comparison/gap-fill backfill if archive endpoint is reliable.
- Deer harvest county-year data from Maryland DNR.
- Mast/acorn survey data where usable.
- Habitat county summaries from NLCD or an equivalent precomputed source.
- ZIP-to-county/ZCTA mapping for user lookup.

### Optional / Later

- CAPC canine serology.
- CDC tick-bite ED tracker backing data.
- National expansion sources outside Maryland.

## Canonical Source Rules Draft

For Maryland Lyme county-year modeling:

1. Prefer official CDC public-use aggregated geography files for raw case provenance.
2. Use CDC county dashboard/geodata files to simplify county-year extraction, but reconcile them back to public-use totals.
3. Use MDH PDF/table as Maryland-specific validation and likely canonical source for 2024.
4. Treat `AllTBD2022_Public` as a comparator until its source definition is verified.
5. Never use current cumulative vector/pathogen status as if it were known in earlier historical years unless the model run is labeled as retrospective reconstruction.

## First ETL Target

The implemented first ETL slice builds `lyme_county_year_reconciled.csv` with:

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

Then join model-ready fields:

```text
population
incidence_per_100k
weather_features_weekly
weather_features_monthly_context
tick_vector_status
tick_pathogen_status
lone_star_status
host_ecology_features
habitat_features
```
