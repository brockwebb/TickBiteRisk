# TickBiteRisk – ETL Pipeline Specification

> **File location:** `/docs/ETL_PIPELINE.md`

The ETL layer converts raw public datasets into tidy county tables and covariates consumed by the Bayesian model.  Each feed is 100 % reproducible from public URLs—no credentials required except where noted.

---

## 1  Directory layout

```
/data-pipelines/
    ├── fetch_cdc_ticks.sh
    ├── fetch_fars.sh
    ├── fetch_ed.sh
    ├── fetch_nlcd.sh
    ├── fetch_acs.sh
    ├── fetch_capc.sh        # requires CC‑BY‑NC click‑through
    ├── transform_nlcd_edge.py
    ├── derive_theta_inputs.py
    └── derive_lambda_inputs.py
```

All scripts are POSIX‑shell or Python 3.11; run inside the Docker image so dependency versions are pinned.

---

## 2  Per‑feed details

### 2.1  CDC Tick Surveillance (`fetch_cdc_ticks.sh`)

| Step     | Command                                                        | Notes                                                          |
| -------- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Download | `curl -L $CDC_URL -o cdc_ticks.csv`                            | \$CDC\_URL is version‑stamped; script aborts if MD5 unchanged. |
| Cleanup  | `csvcut -c state,county,fips,n_nymphs,n_pos > ticks_trim.csv`  | Remove adult tick rows.                                        |
| Load     | `psql -c "\copy raw_cdc_ticks FROM ticks_trim.csv CSV HEADER"` | Raw table partitioned by year.                                 |

### 2.2  FARS Deer Collisions (`fetch_fars.sh`)

1. `wget https://static.nhtsa.gov/.../NationalCSV.zip` – unzip.
2. Filter `ACCIDENT.CSV` where `ANIMALS=5` (deer).
3. Aggregate: `group by fips, year count(*) as deer_crashes`.
4. Upsert into `raw_fars_deer`.

### 2.3  NSSP ED Tick‑Bite Visits (`fetch_ed.sh`)

* Pull weekly CSV via CDC GitHub raw link.
* Convert HHS region → county join using fixed mapping table (`hhs_to_county.csv`).
* Store in `raw_ed_visits (fips, epiweek, visits)`.

### 2.4  NLCD Land‑Cover & Edge Metrics

```
fetch_nlcd.sh  # downloads GeoTIFF once
transform_nlcd_edge.py  # rasterio windowed read
```

* Calculates `%forest`, `%pasture`, and **edge density** (m of forest‑nonforest boundary / km²) for each county.
* Writes to `cov_nlcd_edge`.

### 2.5  ACS Population (`fetch_acs.sh`)

* Uses Census API: `https://api.census.gov/data/2023/acs/acs5?get=B01003_001E&for=county:*`.
* Loads into `cov_pop_density`.

### 2.6  CAPC Dog Serology (`fetch_capc.sh` – optional)

* Scrapes county JSON; user must set `CAPC_OK=1` env var acknowledging CC‑BY‑NC.
* Writes to `cov_dog_lyme`; not redistributed.

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

* **Annual job** (`cron/annual.sh`): runs `fetch_cdc_ticks.sh`, `fetch_fars.sh`, `fetch_nlcd.sh`, `fetch_acs.sh`, then transformation scripts, then triggers full PyMC MCMC.
* **Weekly job** (`cron/weekly.sh`): runs `fetch_ed.sh`, `derive_lambda_inputs.py`, incremental ADVI fit.

All cron scripts exit non‑zero on failure, surfacing errors in GitHub Actions logs.

---

## 5  Data lineage checksum

Every script appends SHA‑256 of raw file to `etl_log` table (`fips='00000'`) so model fits are traceable to exact input snapshots.

---

*Last updated: 2025‑06‑08 (draft v0.1)*
