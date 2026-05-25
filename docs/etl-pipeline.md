# TickBiteRisk – ETL Pipeline Specification

> **File location:** `docs/etl-pipeline.md`

The ETL layer converts raw public datasets into tidy county tables and covariates consumed by the Bayesian model.  Each feed is 100 % reproducible from public URLs—no credentials required except where noted.

---

## 1  Directory layout

```
/data-pipelines/
    ├── fetch_cdc_ticks.sh
    ├── fetch_fars.sh
    ├── fetch_ed.sh
    ├── fetch_nlcd.sh
    ├── fetch_census_population.py
    ├── fetch_noaa_weather.py
    ├── transform_noaa_weather_features.py
    ├── fetch_capc.sh        # requires CC‑BY‑NC click‑through
    ├── transform_nlcd_edge.py
    ├── derive_theta_inputs.py
    └── derive_lambda_inputs.py
```

All scripts are POSIX‑shell or Python 3.11; run inside the Docker image so dependency versions are pinned.

---

## 2  Per‑feed details

### 2.1  CDC Lyme Outcomes (`tickbiterisk etl lyme-outcomes`)

* Reads the ignored raw CDC Lyme source CSVs from `data/raw/lyme`.
* Requires the three CDC public-use aggregated geography files for 1992-2007, 2008-2021, and 2022-2023.
* Also reads the CDC county dashboard export through 2023 and CDC county geodata for 2000-2021 as reconciliation/comparison sources.
* Validates all five required files exist before parsing so missing-source errors are clean.
* Writes `lyme_county_year_reconciled.csv`; warehouse target is `lyme_county_year_reconciled`.
* Preserves `source_values_summary`, `reconciliation_status`, and `data_quality_flags` rather than smoothing source conflicts away.
* The 2026-05-25 live smoke wrote 700 Maryland county-year rows across 24 jurisdictions for 1992-2023: 667 matched rows, 33 conflict rows, 24 rows flagged `covid_reporting_disruption`, and 48 rows flagged `lyme_case_definition_change`.

### 2.2  Model Feature Matrix (`tickbiterisk etl model-features`)

* Reads reconciled Lyme outcomes, Census population denominators, weekly NOAA weather features, optional contact-pressure features, and optional Maryland DNR deer harvest.
* Writes `model_features_county_year.csv`; warehouse target is `model_features_county_year`.
* Uses Lyme county-years as the outcome spine and keeps rows only when required population and annual weather features exist.
* Computes Lyme incidence per 100,000 residents and a log population offset.
* Aggregates weekly NOAA weather to calendar-year features by apportioning boundary weeks across calendar years using `week_start_date` and `week_end_date`.
* Keeps contact pressure and deer harvest optional; missing optional rows are surfaced in `model_feature_quality_flags` instead of dropping the county-year.
* Maps deer harvest into the next model year as prior completed season evidence (`season_start_year + 1`) to avoid same-year leakage.
* The 2026-05-25 live smoke wrote 676 model feature rows for 24 Maryland jurisdictions from 1992-2023: 385 with contact pressure, 92 with prior-season deer harvest, and 36 flagged `partial_weather_year`.

### 2.3  CDC Lyme Seasonality Baseline (`tickbiterisk etl seasonality-baseline`)

* Reads ignored raw CDC Lyme disease-onset exports from `data/raw/seasonality`.
* Requires monthly and MMWR-week CSVs named `cdc_lyme_monthly_onset_2010_2023.csv` and `cdc_lyme_weekly_onset_2010_2023.csv`.
* Normalizes each period to an annual share within source year and grain, because dashboard onset totals are not the same thing as final annual surveillance totals.
* Writes `seasonality_observations.csv` and `seasonality_baseline.csv`; warehouse targets are `seasonality_observations` and `seasonality_baseline`.
* Baseline rows include empirical mean/median cases, mean/median shares, 80 and 95 percent share bands, peak rank, cumulative mean share, and quality flags.
* Carries `national_curve_not_county_specific`, `shares_normalized_by_annual_total`, and `empirical_prediction_band`.
* The 2026-05-25 live smoke wrote 910 seasonality observation rows and 65 baseline rows: 168 monthly observations, 742 weekly observations, 12 monthly baseline rows, and 53 weekly baseline rows.

### 2.4  CDC Tick Surveillance (`fetch_cdc_ticks.sh`)

| Step     | Command                                                        | Notes                                                          |
| -------- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Download | `curl -L $CDC_URL -o cdc_ticks.csv`                            | \$CDC\_URL is version‑stamped; script aborts if MD5 unchanged. |
| Cleanup  | `csvcut -c state,county,fips,n_nymphs,n_pos > ticks_trim.csv`  | Remove adult tick rows.                                        |
| Load     | `psql -c "\copy raw_cdc_ticks FROM ticks_trim.csv CSV HEADER"` | Raw table partitioned by year.                                 |

### 2.5  FARS Deer Collisions (`fetch_fars.sh`)

1. `wget https://static.nhtsa.gov/.../NationalCSV.zip` – unzip.
2. Filter `ACCIDENT.CSV` where `ANIMALS=5` (deer).
3. Aggregate: `group by fips, year count(*) as deer_crashes`.
4. Upsert into `raw_fars_deer`.

### 2.6  NSSP ED Tick‑Bite Visits (`fetch_ed.sh`)

* Pull weekly CSV via CDC GitHub raw link.
* Convert HHS region → county join using fixed mapping table (`hhs_to_county.csv`).
* Store in `raw_ed_visits (fips, epiweek, visits)`.

### 2.7  NLCD Land‑Cover & Edge Metrics

```
fetch_nlcd.sh  # downloads GeoTIFF once
transform_nlcd_edge.py  # rasterio windowed read
```

* Calculates `%forest`, `%pasture`, and **edge density** (m of forest‑nonforest boundary / km²) for each county.
* Writes to `cov_nlcd_edge`.

### 2.8  Census County Reference (`tickbiterisk etl county-reference`)

* Uses Census 2024 Gazetteer county ZIP.
* Filters Maryland jurisdictions and writes land/water area plus internal points.
* Writes `county_reference.csv`; warehouse target is `county_reference`.
* Provides land-area denominators for deer harvest density and other county-normalized ecology features.

### 2.9  Census Population (`tickbiterisk etl census-population`)

* Uses Census PEP/intercensal APIs for Maryland county-year denominators.
* Reads `CENSUS_API_KEY` from the environment for live refreshes.
* Writes `county_population_year.csv`; warehouse target is `county_population_year`.

### 2.10  NOAA Weather Features (`tickbiterisk etl noaa-weather-features`)

* Reads `noaa_ghcnd_daily_observations.csv` generated by the NOAA backfill commands.
* Converts daily station observations to `weather_features_weekly.csv` and `weather_features_monthly.csv`.
* Converts NOAA inches to millimeters for precipitation and snow features.
* Leaves unsupported NOAA humidity, soil, evapotranspiration, and rain-split fields null and records those limits in `feature_quality_flags`.

### 2.11  Maryland DNR Deer Harvest (`tickbiterisk etl deer-harvest`)

* Reads Maryland DNR harvest report HTML tables for recent hunting seasons.
* Optionally reads Maryland DNR annual report PDFs with `--include-annual-report-pdfs`.
* Uses `pypdfium2` as the default PDF text extractor; Docling is installed for heavier document parsing experiments and can be selected with `--annual-report-parser docling`.
* Normalizes county names to Maryland FIPS codes.
* Preserves `all_deer`, `white_tailed_deer`, and `sika_deer` rows.
* Derives all-deer totals for split Eastern Shore counties where the source table reports white-tailed deer and sika deer separately.
* Joins `county_reference.csv` land area and writes `harvest_per_sqmi`.
* Writes `maryland_dnr_deer_harvest.csv`; warehouse target is `maryland_dnr_deer_harvest`.
* The 2026-05-24 news-page live pull produced 231 rows for 2019-20 through 2025-26 across 23 Maryland counties. The annual-report PDF path extracted 460 rows for 2011-12 through 2024-25 in a live smoke run; 2007-08 through 2010-11 are catalogued but left OCR-pending because their table text is not reliably extractable. Baltimore City is not included in the DNR harvest tables.

### 2.12  CAPC Dog Serology (`fetch_capc.sh` - optional)

* Scrapes county JSON; user must set `CAPC_OK=1` env var acknowledging CC‑BY‑NC.
* Writes to `cov_dog_lyme`; not redistributed.

### 2.13  Ecology Source Acquisition (`tickbiterisk etl ecology-sources`)

* Downloads official source pages/files for Annual NLCD/MRLC, Census BPS, Maryland DNR mast reports, and USDA CDL.
* Writes raw files under ignored `data/raw/ecology`.
* Writes `source_manifest.csv` with source ID, URL, local path, byte count, SHA-256, and ingestion timestamp.
* Does not process full raster data in this slice.
* The 2026-05-25 smoke run wrote `Downloaded/catalogued 12 ecology source file(s) to build/etl/ecology/source_manifest.csv`; generated `data/raw/` and `build/` paths are ignored.

### 2.14  Census Building Permits (`tickbiterisk etl building-permits`)

* Downloads December year-to-date county ASCII files from the Census BPS county index.
* Filters Maryland jurisdictions and computes total residential units authorized from 1-unit, 2-unit, 3-4 unit, and 5+ unit columns.
* Writes `maryland_building_permits_county_year.csv`; no warehouse table exists yet, and the CSV feeds the downstream contact-pressure feature table or a future raw staging table.
* Treats construction as a contact/land-use pressure proxy, not direct evidence of tick or deer migration.
* Retries transient source fetch failures because `www2.census.gov` can intermittently stall before first byte.
* The 2024 smoke wrote 24 rows; the first sorted row was `24001`, 2024, 24 units and the last was `24510`, 2024, 1273 units. The 2000-2025 smoke wrote 435 deduped Maryland county-year rows: 2000-2004 have 16 jurisdictions, 2005-2014 have 14, 2015-2021 have 17, and 2022-2025 have 24. Census source files include duplicate St. Mary's rows in 2015 and 2016 with apostrophe spelling differences; the writer dedupes by `county_fips` and `year`.

### 2.15  Contact Pressure Features (`tickbiterisk etl contact-pressure`)

* Reads normalized Census BPS, county reference, and county population CSVs.
* Writes `contact_pressure_features_county_year.csv`.
* Computes residential units authorized per square mile and per 100,000 residents.
* Carries `construction_proxy_only`, `missing_population`, `missing_land_area`, and historical coverage flags.
* The 2026-05-25 live smoke wrote 435 feature rows with 48 rows flagged `missing_population`.

### 2.16  Mast/Acorn Features (`tickbiterisk etl mast-acorn`)

* Reads acquired Maryland DNR Western Maryland mast survey PDFs.
* Uses `pypdfium2` by default and Docling on request.
* Writes structured mast rows only when text supports them.
* Always writes an extraction summary so OCR-pending or low-confidence sources stay visible.
* Optional manual observations are stored separately and flagged anecdotal/not-model-default.
* The 2026-05-25 live smoke wrote 0 structured rows and 3 extraction-summary rows; all 3 summaries had `extraction_status=no_supported_values` and `feature_quality_flags=ocr_pending,parser_low_confidence`.

---

## 3  Transform stage

### 3.1  `derive_theta_inputs.py`

* Joins `raw_cdc_ticks`, `cov_deer`, `cov_dog_lyme`, `cov_nlcd_edge` on `fips`.
* Creates `theta_input.parquet` (columns: fips, y, n, deer\_km2, dog\_pct, edge\_km\_km2).

### 3.2  `derive_lambda_inputs.py`

* Joins `raw_ed_visits`, seasonal Fourier template, snow‑cover covariate.
* Outputs weekly `lambda_input.parquet` ready for PyMC incremental ADVI.

---

## 4  Orchestration

* **Annual job** (`cron/annual.sh`): runs `fetch_cdc_ticks.sh`, `fetch_fars.sh`, `fetch_nlcd.sh`, Census population refresh, then transformation scripts, then triggers full PyMC MCMC.
* **Weekly job** (`cron/weekly.sh`): runs `fetch_ed.sh`, `derive_lambda_inputs.py`, incremental ADVI fit.

All cron scripts exit non‑zero on failure, surfacing errors in GitHub Actions logs.

---

## 5  Data lineage checksum

Every script appends SHA‑256 of raw file to `etl_log` table (`fips='00000'`) so model fits are traceable to exact input snapshots.

---

*Last updated: 2025‑06‑08 (draft v0.1)*
