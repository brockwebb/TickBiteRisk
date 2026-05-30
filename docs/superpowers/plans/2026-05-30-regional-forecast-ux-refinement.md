# Regional Forecast UX Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the regional research dashboard easier to understand and use by clarifying forecast intervals, exposing view choices, adding graph scope controls, replacing the long county list, and restoring a tick-bite guidance tool.

**Architecture:** Keep the regional page as a static HTML/CSS/JS dashboard using the existing public regional JSON bundle. Add small UI controls and aggregation helpers inside `public/regional-research.js` rather than creating a new build system. Reuse the Maryland bite-calculator logic where possible, but keep regional wording informational and non-diagnostic.

**Tech Stack:** Static HTML, vanilla JavaScript, CSS, Playwright browser smoke tests, Python static contract tests.

---

### Task 1: Forecast View Buttons And Interval Copy

**Files:**
- Modify: `public/regional-research.html`
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Test: `tests/test_regional_research_dashboard_static.py`
- Test: `tests/browser/regional-research-smoke.spec.mjs`

- [ ] **Step 1: Write failing tests**

Require `forecast-view-radios`, two visible radio inputs named `forecast-view`, no `forecast-view-select`, and weekly chart copy that explains the dark and light blue bands as expected-error ranges instead of using unexplained "forecast interval" language.

- [ ] **Step 2: Run red tests**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_research_dashboard_static.py -q
npm run test:dashboard
```

Expected: tests fail because the current page still uses a hidden select/dropdown mental model and vague interval copy.

- [ ] **Step 3: Implement minimal green**

Replace the view `<select>` with two radio buttons. Update JS event handling to read/write checked radio state. Update weekly summary to explain:

```text
Dark blue band: narrower expected range from past forecast errors. Light blue band: wider expected range. Red dot: selected week. These ranges are uncertainty around reported-incidence forecasts, not medical confidence intervals.
```

- [ ] **Step 4: Verify and commit**

Run focused tests, `node --check public/regional-research.js`, and commit:

```bash
git commit -m "fix: clarify regional forecast controls"
```

### Task 2: Forecast Graph Scope Selector

**Files:**
- Modify: `public/regional-research.html`
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Test: `tests/test_regional_research_dashboard_static.py`
- Test: `tests/browser/regional-research-smoke.spec.mjs`

- [ ] **Step 1: Write failing tests**

Require graph scope controls with `Region`, `State`, and `County`; default graph scope should be region-wide, not an auto-selected county. Require state/county selectors to appear only when relevant. Require selecting a map county to switch graph scope to county.

- [ ] **Step 2: Run red tests**

Run focused static and Playwright tests. Expected: fail because the chart is still county-only.

- [ ] **Step 3: Implement aggregation helpers**

Add helpers that aggregate annual and weekly chart rows by scope:

```text
Region: all forecast counties.
State: counties whose state_abbr matches selected state.
County: selected or searched county.
```

For aggregate incidence, sum predicted/observed cases and divide by summed population denominators. For forecast rows, infer population from `predicted_annual_cases / predicted_annual_incidence_per_100k * 100000` when needed. Aggregate weekly uncertainty bands as population-weighted incidence ranges.

- [ ] **Step 4: Wire chart rendering**

Update chart summaries to name the selected scope. Keep map click behavior: clicking a county selects county details and switches graph scope to that county.

- [ ] **Step 5: Verify and commit**

Run focused tests plus `npm run test:dashboard`, then commit:

```bash
git commit -m "feat: add regional forecast graph scope"
```

### Task 3: Replace County List With Search And Bite Guidance

**Files:**
- Modify: `public/regional-research.html`
- Modify: `public/regional-research.js`
- Modify: `public/styles.css`
- Test: `tests/test_regional_research_dashboard_static.py`
- Test: `tests/browser/regional-research-smoke.spec.mjs`

- [ ] **Step 1: Write failing tests**

Require the long `#regional-county-list` button list to be removed. Require a compact county search/select control and a regional bite-guidance panel with fields for tick identity, stage, attachment hours, engorgement, hours since removal, doxycycline safety, and attached tick count.

- [ ] **Step 2: Run red tests**

Run focused tests. Expected: fail because the page still renders the huge list and lacks regional bite guidance.

- [ ] **Step 3: Implement county search**

Replace the county list with a single county search/select. Selecting a county should update the map, county panel, and graph scope.

- [ ] **Step 4: Restore bite guidance**

Adapt the Maryland `estimateSingleBiteRisk` logic to the regional page. Use the selected county and selected week/current 2026 weekly forecast when available. Keep language informational: "bite concern score" and "CDC consideration context," not infection probability or diagnosis.

- [ ] **Step 5: Verify and commit**

Run focused tests, `node --check`, and commit:

```bash
git commit -m "feat: restore regional bite guidance"
```

### Task 4: Full Verification And Deploy

**Files:**
- No new files expected.

- [ ] **Step 1: Run full verification**

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q $(git ls-files 'tests/test*.py')
PYTHONPATH=. ./.venv/bin/python -m ruff check .
npm run test:dashboard
node --check public/app.js && node --check public/regional-research.js && git diff --check
PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl
```

- [ ] **Step 2: Deploy**

Push branch and `main`, wait for GitHub Pages, and live-check the deployed regional page.

- [ ] **Step 3: Handoff**

Write a concise fresh-thread handoff describing final UX state, commits, verification, preview URL, and next product/modeling steps.
