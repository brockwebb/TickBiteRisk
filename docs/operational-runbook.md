# TickBiteRisk – Operational Runbook

**The following deployment instructions assume you (or a third-party sponsor) want to host TickBiteRisk for others. Skip this file if you’re using the toolkit solely on your own machine.**

> **File location:** `/docs/operational-runbook.md`

---

## 1 Service inventory

| Component        | Docker service | Port            | Responsibilities                                                  |
| ---------------- | -------------- | --------------- | ----------------------------------------------------------------- |
| PostGIS          | `postgres`     | 5432 (internal) | Stores raw/processed data, posterior tables, audit logs.          |
| PyMC Fit         | `pymc_fit`     | —               | Runs annual MCMC & weekly ADVI; mounts `/data` and writes NetCDF. |
| FastAPI          | `fastapi_app`  | 8000            | Serves `/risk` endpoint and OpenAPI docs.                         |
| Nginx (optional) | `nginx`        | 443             | TLS termination, rate‑limiting, static dashboard.                 |

## 2 Environments & secrets

| Variable            | Service                           | Default           | Description                             |
| ------------------- | --------------------------------- | ----------------- | --------------------------------------- |
| `POSTGRES_PASSWORD` | postgres, pymc\_fit, fastapi\_app | **set in `.env`** | DB auth.                                |
| `FASTAPI_WORKERS`   | fastapi\_app                      | 2                 | Gunicorn worker count.                  |
| `CAPC_OK`           | pymc\_fit                         | *unset*           | Must be `1` to fetch CC‑BY‑NC dog data. |
| `TZ`                | all                               | `UTC`             | Ensure cron jobs run on UTC.            |

Secrets live **only** in `.env` (git‑ignored).  GitHub Actions test pipeline uses throw‑away passwords.

## 3 Cron schedules (UTC)

| Script           | Schedule       | Action                                                               |
| ---------------- | -------------- | -------------------------------------------------------------------- |
| `cron/weekly.sh` | `0 6 * * MON`  | Pull NSSP ED CSV → ADVI update → reload FastAPI in‑place (`SIGHUP`). |
| `cron/annual.sh` | `30 5 15 11 *` | Fetch CDC tick, FARS deer, ACS pop, run full MCMC, tag release.      |

Cron runs inside the **pymc\_fit** container via supervisord.  All logs pipe to stdout → Docker log driver.

## 4 Deployment commands

### Local dev

```bash
docker compose up --build           # first‑time setup
docker compose exec postgres psql -U postgres -c '\dt'
```

### Production (systemd unit)

```ini
[Service]
Restart=always
ExecStart=/usr/local/bin/docker-compose -f /opt/tickbiterisk/docker-compose.yml up
WorkingDirectory=/opt/tickbiterisk
EnvironmentFile=/opt/tickbiterisk/.env
```

`systemctl enable tickbiterisk && systemctl start tickbiterisk`

## 5 Backup & restore

* **Database:** nightly `pg_dump -Fc tickrisk > backups/db_$(date +%F).dump.zst` (
  15 MB for 10‑year archive).  Retention: 30 days.
* **Posterior NetCDF:** stored in `/data/posteriors/`; backed up via same script.

## 6 Monitoring & alerts

| Metric              | Threshold                          | Action          |
| ------------------- | ---------------------------------- | --------------- |
| API 5xx rate        | >1% over 5 min                     | PagerDuty ‑ LOW |
| Cron weekly job lag | >2 days since `last_lambda_update` | PagerDuty ‑ MED |
| DB size growth      | >100 MB/day                        | Slack alert     |

Prometheus sidecar scrapes FastAPI `/metrics` and Postgres exporter; Grafana dashboard JSON lives in `/ops/grafana/`.

## 7 Disaster recovery drill

1. Provision fresh host; install Docker/Docker‑compose.
2. `scp` latest DB dump + `posterior_*.nc` to `/restore`.
3. `docker compose up --build` (runs empty).
4. `pg_restore -d tickrisk /restore/db_latest.dump.zst`.
5. Copy NetCDF into `/data/posteriors/`; restart `fastapi_app`.
6. `GET /risk?fips=24003&tau=24` should return HTTP 200 within CI95 bounds.

---

*Last updated: 2025-06-08 (draft v0.1)*

