# TickBiteRisk – Data‑Source Catalog

| ID              | Dataset (link)                                                                                                     | Content & Granularity                                                 | Update cadence                      | Up‑stream licence                  | Fetch script                   |
| --------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- | ----------------------------------- | ---------------------------------- | ------------------------------ |
| **CDC\_TICK**   | [CDC Tick Surveillance](https://www.cdc.gov/ticks/surveillance/index.html) CSV                                     | County‑level *Ixodes* presence & % **B. burgdorferi**‑positive nymphs | ~~Annual (Oct–Nov)~~ *ad hoc 2023→* | US Public Domain (17 U.S.C. § 105) | `pipelines/fetch_cdc_ticks.sh` |
| **FARS\_DEER**  | [FARS + CRSS](https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars) animal‑collision tables | Crash records with deer flag; county FIPS                             | Annual (Sept)                       | US Public Domain                   | `pipelines/fetch_fars.sh`      |
| **NSSP\_ED**    | [NSSP Tick‑Bite Visit Indicator](https://www.cdc.gov/nssp/)                                                        | Weekly ED visits coded “tick bite” by state/HHS region                | Weekly (Mon)                        | US Public Domain                   | `pipelines/fetch_ed.sh`        |
| **NLCD**        | [NLCD 2021 Land‑Cover 30 m](https://www.mrlc.gov/) GeoTIFF                                                         | Raster land‑cover classes; forest/pasture edge metrics                | Static (updated \~5 yr)             | US Public Domain                   | `pipelines/fetch_nlcd.sh`      |
| **ACS\_POP**    | [American Community Survey 5‑yr](https://api.census.gov/)                                                          | Population density, rural %, housing units (county)                   | Annual (Dec)                        | US Public Domain                   | `pipelines/fetch_acs.sh`       |
| **DOG\_CAPC**\* | [CAPC Canine Lyme Seroprevalence](https://capcvet.org/) county map JSON                                            | % positive Lyme tests in dogs                                         | Monthly                             | **CC‑BY‑NC 4.0** (non‑commercial)  | `pipelines/fetch_capc.sh` †    |
| **SNOW\_IMS**   | [NOAA IMS Snow‑Cover 4 km](https://www.ncei.noaa.gov/products/snow-and-ice/ims)                                    | Daily binary snow/ice; summed to “snow‑days per winter”               | Daily                               | US Public Domain                   | `pipelines/fetch_snow.sh`      |

† Not redistributed in repo; users fetch locally to respect CC‑BY‑NC terms.

## Derived Tables & Licence

All processed/derived tables (`theta_{year}.parquet`, `lambda_weekly.parquet`) are released under **CC‑BY 4.0** to ensure attribution while allowing broad reuse.

## Data Footprint

| Layer                           | Size (compressed) |
| ------------------------------- | ----------------- |
| Raw federal CSV/GeoTIFF (10 yr) | \~1.5 GB          |
| Processed county tables (10 yr) | \~120 MB          |
| Posterior draws per season      | \~25 MB           |

---

*Last updated: 2025‑06‑08 (draft v0.1)*

