# TickBiteRisk Local Install Guide

> **File location:** `/docs/install-local.md`

## Current status

This guide describes the current maintained quick start for the implemented
TickBiteRisk product: local Python tooling, derived ETL artifacts, CLI lookup,
single-bite context, static export, and a static dashboard served from
`public/`.

The current product is a Maryland-first relative reported Lyme disease
pressure forecast and risk-context tool. It is informational only, not medical
advice, not diagnosis or treatment guidance, and not a per-bite infection
probability.

FastAPI/PyMC/Postgres path is historical. The repository keeps warehouse and
future service design notes, but the public v0 runtime does not require a live
database, API server, raw source files, or cloud service.

## Current maintained quick start

```bash
python -m pip install -e ".[dev]"
```

Run a county/date lookup against a derived county-week forecast artifact:

```bash
tickbiterisk risk lookup \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --pretty
```

Run the single-bite context command:

```bash
tickbiterisk risk single-bite \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --tick-species blacklegged \
  --tick-stage nymph \
  --attachment-hours 40 \
  --engorgement engorged \
  --hours-since-removal 24 \
  --doxycycline-safe \
  --pretty
```

Export public-safe static dashboard data:

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir build/public-risk
```

Serve the committed static dashboard locally:

```bash
python -m http.server 8000 --directory public
```

Then open `http://localhost:8000`.

## Current verification commands

Run the same families of checks used for the current branch:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q $(git ls-files 'tests/test*.py')
PYTHONPATH=. ./.venv/bin/python -m ruff check .
node --check public/app.js
node --check public/regional-research.js
npm run test:dashboard
```

## Optional ETL context

The README and operational runbook contain the current ETL command sequence for
refreshing derived artifacts. Raw source files remain local or ignored unless a
source-specific review allows redistribution. Public dashboard files should be
derived, source-attributed, and free of credentials.

## Historical install path

Older drafts of this guide described a laptop stack built around PostgreSQL,
PostGIS, FastAPI, PyMC, cron jobs, and a live `/risk` HTTP endpoint. That path
was useful as a concept-stage architecture note, but it is not the maintained
quick start for the current static v0 product.

Use the current CLI/static commands above unless a future plan explicitly
revives the database-backed HTTP service and validates its runtime, security,
and public wording.

Last updated: 2026-05-30.
