# Regional History Year Slider UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add clear state boundaries, observed historical annual context, year-mode controls, and risk-scale diagnostics to the regional research preview.

**Architecture:** Keep the 2026 forecast county-week bundle separate from an observed annual incidence bundle. The regional map chooses its visual metric from the selected year: observed historical incidence for years with surveillance outcomes, and forecasted weekly risk for forecast years. State boundaries are a separate derived public geography asset so county fills and state outlines do not fight each other.

**Tech Stack:** Python 3.12 stdlib ETL/export code, existing Typer CLI, static HTML/CSS/JavaScript, Playwright smoke tests, committed GitHub Pages JSON/GeoJSON preview assets.

---

### Task 1: Regional State Boundary Overlay

**Files:**
- Modify: `tickbiterisk/dashboard_assets.py`
- Modify: `tickbiterisk/cli.py`
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Modify: `tests/test_dashboard_assets.py`
- Modify: `tests/test_cli_dashboard_assets.py`
- Modify: `tests/test_regional_research_dashboard_static.py`
- Modify: `tests/browser/regional-research-smoke.spec.mjs`
- Modify: `tests/test_regional_research_public_data.py`

- [ ] Write failing tests that expect `regional_states.geojson` in regional dashboard outputs, public bundle validation, static JS paths, and browser-rendered `.regional-state-boundary` paths.
- [ ] Add Census TIGERweb state GeoJSON normalization and optional CLI input for regional state geometry.
- [ ] Write `regional_states.geojson` from `dashboard build-regional-research-assets` and include it in the static manifest.
- [ ] Load and draw state boundary paths in `public/regional-research.js` after county paths.
- [ ] Style `.regional-state-boundary` as thick, non-clickable outlines.
- [ ] Regenerate and commit the regional public preview asset.

### Task 2: Observed Regional Annual Incidence Export

**Files:**
- Modify: `tickbiterisk/dashboard_assets.py`
- Modify: `tickbiterisk/cli.py`
- Add or modify tests near `tests/test_dashboard_assets.py` and `tests/test_cli_dashboard_assets.py`
- Modify: `tests/test_regional_research_public_data.py`

- [ ] Write failing tests for `regional_county_incidence_annual.json` generated from `build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv`.
- [ ] Export only derived annual records with `data_role: "observed_historical"`, county/state identifiers, year, cases, population, incidence, diagnostic tier, and quality flags.
- [ ] Add research-only and not-public-default boundaries to the annual observed payload.
- [ ] Add the observed annual payload to the regional manifest and public validation.

### Task 3: Year Slider And Mode Boundary

**Files:**
- Modify: `public/regional-research.html`
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Modify: `tests/test_regional_research_dashboard_static.py`
- Modify: `tests/browser/regional-research-smoke.spec.mjs`

- [ ] Write failing tests that expect a year slider, mode label, historical observed mode text, and forecast mode text.
- [ ] Load `regional_county_incidence_annual.json` alongside the forecast bundle.
- [ ] In years `2001-2024`, color counties by observed annual incidence/tier and hide or disable forecast week controls.
- [ ] In `2026`, color counties by forecast risk, show week controls, and keep interval/provenance details visible.
- [ ] Make county detail panels explicitly say whether values are observed reported incidence or forecasted risk.

### Task 4: Risk Scale Diagnostics

**Files:**
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Modify: `tests/test_regional_research_dashboard_static.py`
- Modify: `tests/browser/regional-research-smoke.spec.mjs`

- [ ] Write failing tests for score scale text that explains the linear benchmark denominator and clamping.
- [ ] Surface raw score, score denominator, and annual/weekly incidence in county details.
- [ ] Add a small scale note that says the current public score is linear and that log/quantile alternatives are research diagnostics, not silently substituted defaults.

### Verification

- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m pytest -q`.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m ruff check .`.
- [ ] Run `npm run test:dashboard`.
- [ ] Run `node --check public/app.js && node --check public/regional-research.js`.
- [ ] Run `git diff --check`.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl`.
