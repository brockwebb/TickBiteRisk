# TickBiteRisk Operational Runbook

**The following deployment instructions assume you (or a third-party sponsor) want to host TickBiteRisk for others. Skip this file if you’re using the toolkit solely on your own machine.**

> **File location:** `/docs/operational-runbook.md`

---

## 1. V0 static dashboard

The implemented public product is a static dashboard deployed from the committed
`public/` directory to GitHub Pages. It serves derived JSON artifacts from
`public/data` plus static HTML, CSS, JavaScript, and county geometry.

V0 has no runtime secrets, database connection, server process, API container,
or scheduled production job. Raw data and private ETL outputs stay outside the
public runtime.

The Python package is tooling for ETL, model comparison, export, and local
lookup. The public/ directory is the deployable site artifact for GitHub
Pages; the static dashboard is not packaged into the Python wheel.

## 2. Public files

The deployed site should contain:

```text
public/index.html
public/app.js
public/styles.css
public/data/md_counties.geojson
public/data/md_county_metadata.json
public/data/md_county_risk_weekly.json
public/data/model_card.json
public/data/source_catalog.json
public/data/static_export_manifest.json
```

The `public/data` JSON bundle is a public-safe derived data product. It should
not include raw surveillance extracts, API keys, database dumps, or private
warehouse tables.

## 3. Regenerate public data

When the derived county-week risk CSV changes, rebuild the static data bundle:

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir public/data

tickbiterisk dashboard build-assets \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir public/data
```

Use selectors such as `--source-prediction-sha256`, `--source-prediction-run-id`,
`--benchmark-quantile`, or `--score-denominator` if multiple model/source/scale
branches coexist.

## 4. Local validation

Run the same checks used by the Pages workflow:

```bash
ruff check .
pytest -q
node --check public/app.js
python -m json.tool public/data/md_county_risk_weekly.json >/dev/null
python -m json.tool public/data/md_county_metadata.json >/dev/null
python -m json.tool public/data/model_card.json >/dev/null
python -m json.tool public/data/source_catalog.json >/dev/null
python -m json.tool public/data/static_export_manifest.json >/dev/null
```

Run the dashboard locally:

```bash
python -m http.server 8000 --directory public
```

Open `http://localhost:8000` and confirm:

- the Maryland map renders,
- county list buttons render,
- selecting a county updates the detail panel,
- the model source strip appears,
- the attached tick calculator returns a single-bite score,
- the CDC criteria breakdown appears for the attached tick calculator,
- sources and CDC guidance links appear,
- public caveats say informational only and not medical advice.

## 5. Deployment

GitHub Pages deployment is handled by `.github/workflows/pages.yml`.

The workflow:

- validates on pull requests,
- validates and deploys on pushes to `main` and manual dispatch,
- installs Python and Node,
- runs lint, tests, JavaScript syntax checks, and public-data JSON validation,
- uploads the committed `public/` directory,
- deploys that artifact to GitHub Pages.

Repository Settings > Pages should use GitHub Actions as the source. No GitHub
Actions secrets are required for deployment because the site uses committed
derived data.

## 6. Failure response

If GitHub Pages deployment fails:

1. Open the failed workflow run.
2. Check whether failure happened in validation or deployment.
3. For validation failures, reproduce locally with the commands in section 4.
4. For missing JSON files, regenerate `public/data` from the selected derived
   score branch.
5. For dashboard JavaScript errors, run `node --check public/app.js` and a local
   browser smoke test.
6. For deployment-only failures, retry the workflow after confirming GitHub
   Pages is enabled for the repository.

## 7. Future service runbook

A database-backed HTTP API may be added later. That would require a separate
runbook covering service inventory, secrets, backups, monitoring, incident
response, and disaster recovery. Those service operations are not part of the
implemented v0 static dashboard.

*Last updated: 2026-05-27*
