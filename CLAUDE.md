# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The repo-wide engineering constitution lives at `~/Documents/GitHub/CLAUDE.md` and governs this project too (TDD, config-over-hardcode, fail-loud, CLI-over-MCP, Seldon protocol). This file adds only the project-specific context that constitution does not cover.

## Commands

Dev install (provides `ruff` + `pytest`, and the `tickbiterisk` console script):
```bash
python -m pip install -e ".[dev]"
```

- Full test suite: `python -m pytest -q`  (config in `pyproject.toml`: `testpaths=["tests"]`, `pythonpath=["."]`)
- Single test: `python -m pytest tests/test_risk_score.py::test_name -q`
- Lint: `ruff check .`  (if not on PATH, it is installed in the project venv: `.venv/bin/ruff check .`)
- Dashboard browser smoke (Playwright, serves `public/`): `npm ci` then `npm run test:dashboard`
- JS syntax gate: `node --check public/regional-research.js`
- Serve the dashboard locally: `python3 -m http.server 8000 --directory public` → open `/` (redirects to the six-state regional product) or `/regional-research.html` directly. (The former Maryland POC is archived at `archive/md-poc/`, out of the deploy path.)

The CLI is the entry point for everything: `tickbiterisk <subapp> <command>` (`cli.py:app`, sub-apps `etl`, `risk`, `dashboard`). Internal tooling is CLI commands by design (AD-003), not MCP. `cli.py` is large and thin — logic lives in the packages below.

## Pipeline architecture

Data flows in one direction through four stages; each stage is a layer of `tickbiterisk/` plus a directory on disk:

1. **`data/raw/`** (committed) — source files: CDC Lyme (`data/raw/lyme/`), state DOH exports, NOAA, seasonality, etc.
2. **`tickbiterisk/etl/*`** (~70 modules) — parse + reconcile sources. Pattern: a parser module (e.g. `lyme.py`, `regional_lyme.py`, `noaa.py`, `weather_features.py`) paired with a `*_build.py` writer that emits CSV/GeoJSON into **`build/etl/<stage>/`** (gitignored intermediate artifacts).
3. **`tickbiterisk/modeling/*`** (~40 modules) — forecasts and scores over the ETL outputs: `annual_forecast.py`, `risk_score.py` (county-week seasonal risk on a 1–10 scale), `model_compare.py`, `regimes.py`, `reporting_basis_adjustment.py`.
4. **`tickbiterisk/runtime/*`** + **`tickbiterisk/dashboard_assets.py`** — `risk_lookup.py` / `single_bite.py` answer queries over derived files; `static_export.py` and `dashboard_assets.py` emit the public web bundles into **`public/`** (committed, deployed).

`build/` is gitignored — never commit ETL outputs or acquired data there. `data/raw/` (source) and `public/` (derived, public-safe bundles) ARE committed. `cc_tasks/`, `handoffs/`, and `.env` are gitignored.

## The product is the six-state regional dashboard (MD was POC only)

The shipped, public product is the **regional research dashboard** (six-state: DE, DC, MD, PA, VA, WV): `regional-research.html` + `regional-research.js` + `public/research-data/regional/*` (11-file JSON/GeoJSON bundle), built by `dashboard build-regional-research-assets` → `dashboard_assets.write_regional_research_dashboard_assets` (same `static_export` path). `public/index.html` is a thin redirect to `regional-research.html`, so `/` lands on the product. The regional bundle carries `research_status` metadata (display/metadata only; does NOT gate visibility — anything in `public/` is published).

**Maryland was the POC/MVP and is NOT the product.** It is archived at `archive/md-poc/` (out of the deploy path), retained for posterity only. It is not deployed, not maintained, and carries a known band-collapse display defect that will NOT be fixed (POC, not product). Do not treat MD as a live product, do not reintroduce it to `public/`, and do not let any forecast claim derive from it.

`.github/workflows/pages.yml` is the deploy gate: on push to `main` it runs ruff + pytest + JS checks + the Playwright smoke, then validates the exact committed regional bundle (11-file set, county/state counts 283/6, schema, `research_status`), then deploys `public/`. Any edit to the committed bundle must keep that validator green.

## Domain landmines (these have cost repeat effort)

- **Incidence has two incompatible bases.** County Lyme incidence comes from either the **CDC county dashboard** (zero-suppression, the basis the shipped panel uses — every row flagged `cdc_dashboard_total_cases`) OR the **CDC public-use** files (`qtbi-xd4i` 2008–2021, `x5j9-wybp` 2022–2023), which are heavily suppressed (~50% of county-years overall, ~70% in VA/WV). They are NOT interchangeable; "re-derive from `qtbi-xd4i`" yields a far sparser panel than what's live. A consistent six-state basis extends through **2023**; 2024 exists only via heterogeneous state-DOH sources.
- **The 2022 CSTE case-definition change (CSTE 21-ID-05, effective 2022-01-01) is a large discontinuity** (+72.9% reported cases in high-incidence jurisdictions) unrelated to true disease change. Models fit across it without accounting for the regime break will attribute the artifact to the covariate. The longest definition-stable window ending 2021 is 2017–2021.
- **The central forecast is a seasonally-allocated lagged-incidence baseline; `model_card` reports `weather_mode=not_used`.** Do not let the product claim weather/ecology/Bayesian adjustment it does not have. Track-2 investigated weather and ecology covariates and found them non-identifying/null at annual county resolution (three converging weather nulls + a data-limited ecology dead-end; see lab notes 10 and 11). `weather_mode=not_used` is the **earned scoping decision from that investigation, not a placeholder** — the negative-result trail (signal-check scripts, `config/signal_check.toml`) is on `main` as evidence, not as a wired feature.

## Weather acquisition (config-driven)

Six-state weather is acquired via `tickbiterisk etl noaa-backfill-regional --config-path config/weather.toml`. Parameters (states, GHCND variables, date range, `validate_temp_through`, station-selection knobs) live in `config/weather.toml` (read by `etl/weather_config.py` via stdlib `tomllib`); the **`NOAA_TOKEN`** secret is read from the env (gitignored `.env`), never config. The acquisition uses the GHCND `.dly` bulk path (one request per station = full period of record) and validates that a station's **actual in-window TMAX/TMIN density** is sufficient — not CDO's all-element `maxdate`, which a precip-only station inflates. Audit any acquired panel with `python -m tickbiterisk.etl.weather_data_audit --observations <daily.csv> --stations <stations.csv> --gate` (fails on any 0%-in-window county or integrity FAIL).

## Seldon

Research artifacts (tasks, results, issues) are tracked in a Seldon graph (DB `seldon-tickbiterisk`; Seldon derives the DB name from the project, ignoring `NEO4J_DB`). Use `seldon verify` (7 integrity checks) and `seldon cc complete <task-file>` per the constitution's session protocol. CC task specs live in `cc_tasks/` and session handoffs in `handoffs/` (both gitignored).

## Multi-agent working agreement (environment-specific — not in the parent constitution)

This project is worked by multiple agents: Claude Code (grunt work, code, acquisition, runs CLI tools directly on this machine), desktop Claude sessions (orientation, verification framing, decision support — does NOT author scripts or run audits directly per the Seldon contract), and Codex (implementation; treated as unreliable for complex or direction-sensitive work). Resolve role explicitly at session start.

- **Orient before acting.** A session reads the latest `handoffs/` entry and runs `seldon go` (or `seldon_go`) BEFORE creating files or running tools. The project conventions live in the graph and the orientation, not only in this file.
- **Two filesystems (desktop sessions).** A desktop session has both its own container filesystem and the user's real machine via the Filesystem MCP. `create_file` / container paths write to the CONTAINER, not the repo — the write silently never reaches disk. Always write repo files via the Filesystem MCP and confirm the write landed on the real path before reporting done. (This is the classic "file write that never landed" failure.)
- **No agent's "done" is trusted without ground-truth.** Re-derive counts/results from source, not from a prior agent's artifact. Confirm graph claims (edges, registrations, states) by querying the graph — a RESULTS file or handoff that attests to its own completion gets the SAME skepticism as any other agent claim. (This session: a RESULTS file claimed a `blocks` edge and an artifact registration that graph queries showed did not exist.)
- **`blocks` edges between ResearchTasks** are not creatable via the current desktop `seldon_task_create` path (errors on a missing-arg/ontology constraint). Record a blocking relationship in the task description and enforce the gate by evidence (a passing check), not by graph topology, unless/until the edge mechanism is confirmed.
- **Verification is structural, not aspirational.** Reading a test body is not running it; a green checkpoint is not a verified artifact. Re-run the gate / re-derive from source.

