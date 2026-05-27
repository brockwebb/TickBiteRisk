# TickBiteRisk – Local‑Laptop Install Guide

> **File location:** `/docs/install-local.md`

This guide walks you through spinning up TickBiteRisk entirely on your **personal laptop**—no Docker, no cloud.  Tested on macOS 14 and Ubuntu 22.04.

---

## 1 Prerequisites

| Component     | macOS command                                | Ubuntu/Debian command                              |
| ------------- | -------------------------------------------- | -------------------------------------------------- |
| PostgreSQL 17 | `brew install postgresql@17`                 | `sudo apt install postgresql-17`                   |
| PostGIS 3     | `brew install postgis`                       | `sudo apt install postgis postgresql-17-postgis-3` |
| GDAL ≥3.6     | installed with PostGIS                       | `sudo apt install gdal-bin libgdal-dev`            |
| csvkit        | `brew install csvkit`                        | `sudo apt install csvkit`                          |
| Python 3.11   | `brew install pyenv && pyenv install 3.11.8` | `sudo apt install python3.11 python3.11-venv`      |
| Build tools   | `xcode-select --install`                     | `sudo apt install build-essential`                 |

---

## 2 Clone repo & set up Python

```bash
# clone
git clone https://github.com/yourhandle/tickbiterisk.git
cd tickbiterisk

# create venv (replace with pyenv or conda if preferred)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]   # pulls PyMC, FastAPI, rasterio, etc.
```

---

## 3 Bootstrap PostgreSQL

```bash
# start postgres (macOS brew service or systemctl for Linux)
brew services start postgresql@17          # macOS
# sudo systemctl start postgresql          # Ubuntu

# create db
override_user="$(whoami)"        # adjust if needed
psql -U "$override_user" -d postgres -c 'CREATE DATABASE tickrisk;'
psql -U "$override_user" -d tickrisk <<'SQL'
CREATE EXTENSION postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE etl_log (
  id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
  source text,
  fetched_at timestamptz,
  md5 char(32)
);
SQL
```

Export basic env‑vars (append to `~/.bash_profile`):

```bash
export POSTGRES_USER=$(whoami)
export POSTGRES_PASSWORD=""      # blank if using peer auth
export POSTGRES_DB=tickrisk
export PGHOST=localhost
export PGPORT=5432
```

`source ~/.bash_profile` to reload.

---

## 4 Run a first ETL & model smoke‑test

```bash
./data-pipelines/fetch_cdc_ticks.sh --year 2023
psql -d tickrisk -c 'SELECT COUNT(*) FROM raw_cdc_ticks LIMIT 5;'

make test-mini      # runs mini-model fit & unit tests (<2 min)
```

If all tests pass, your local environment is wired.

---

## 5 Start the API

```bash
uvicorn api.app:app --reload --port 8000
# visit http://localhost:8000/docs
```

Example query:

```bash
curl 'http://localhost:8000/risk?fips=24003&tau=24'
```

---

## 6 Schedule weekly & annual ETL (optional)

Edit your crontab (`crontab -e`):

```
0 6 * * MON  /path/to/repo/cron/weekly.sh >> ~/tickrisk_weekly.log 2>&1
30 5 15 11 *  /path/to/repo/cron/annual.sh >> ~/tickrisk_annual.log 2>&1
```

Both scripts will skip gracefully if dependencies are missing or MD5 unchanged.

---

### Troubleshooting

| Symptom                                   | Likely cause                 | Fix                                                                      |
| ----------------------------------------- | ---------------------------- | ------------------------------------------------------------------------ |
| `psql: connection refused`                | Postgres service not running | `brew services start postgresql@17` or `sudo systemctl start postgresql` |
| `relation "raw_cdc_ticks" does not exist` | ETL didn’t run or failed     | Check `etl_log` and rerun `fetch_cdc_ticks.sh`                           |
| `GDAL_LIBRARY not found` import error     | GDAL missing in Python env   | Ensure `brew install gdal` then `pip reinstall rasterio`                 |

---

*Last updated: 2025-06-08 (draft v0.1)*
