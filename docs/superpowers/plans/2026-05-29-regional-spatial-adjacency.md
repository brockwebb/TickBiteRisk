# Regional Spatial Adjacency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize a cross-border county-equivalent adjacency graph for DE, DC, MD, PA, VA, and WV from official Census TIGERweb GeoJSON.

**Architecture:** Reuse `tickbiterisk/modeling/spatial_neighbors.py` for shared-boundary graph construction, extend it with regional filtering/writing, and add a small Census TIGERweb acquisition helper. The CLI gets one new ETL command that can either fetch the normalized six-state county GeoJSON or read a saved GeoJSON path, then writes `regional_county_adjacency.csv` and acquisition provenance.

**Tech Stack:** Python stdlib, Typer CLI, pytest, existing CSV/GeoJSON ETL patterns.

---

### Task 1: Regional Geometry Acquisition Helper

**Files:**
- Create: `tickbiterisk/etl/regional_county_geometry.py`
- Test: `tests/test_regional_county_geometry.py`

- [ ] **Step 1: Write failing tests**

Create tests that verify `build_tigerweb_county_query_url()` includes state FIPS `10,11,24,42,51,54`, `f=geojson`, and `returnGeometry=true`, and that `normalize_tigerweb_county_geojson()` maps TIGERweb `GEOID`/`NAME` properties to `county_fips`/`county_name`.

- [ ] **Step 2: Run RED**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_county_geometry.py -q`. Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement helper**

Add constants for the official TIGERweb query endpoint, target state FIPS, query URL builder, fetch function using `urllib.request`, normalizer, and provenance row builder with source URL hash and fetch timestamp parameter.

- [ ] **Step 4: Run GREEN**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_regional_county_geometry.py -q`. Expected: tests pass.

### Task 2: Regional Adjacency Writer

**Files:**
- Modify: `tickbiterisk/modeling/spatial_neighbors.py`
- Test: `tests/test_spatial_neighbors.py`

- [ ] **Step 1: Write failing tests**

Add a test with counties from two state FIPS values sharing an edge. Assert the writer outputs `regional_county_adjacency.csv`, keeps the cross-border pair, and records `regional_county_adjacency_from_geojson` in `feature_quality_flags`.

- [ ] **Step 2: Run RED**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_spatial_neighbors.py -q`. Expected: failure because the regional writer does not exist.

- [ ] **Step 3: Implement writer**

Add `write_regional_county_adjacency_output(rows, output_dir)` and keep the Maryland writer behavior unchanged. Use the same CSV schema and deterministic ordering.

- [ ] **Step 4: Run GREEN**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_spatial_neighbors.py -q`. Expected: tests pass.

### Task 3: CLI Command

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_regional_county_adjacency.py`

- [ ] **Step 1: Write failing tests**

Add one CLI test that passes a fixture GeoJSON path and asserts `regional_county_adjacency.csv` is written with cross-border rows. Add one missing-file clean-failure test.

- [ ] **Step 2: Run RED**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_regional_county_adjacency.py -q`. Expected: command missing.

- [ ] **Step 3: Implement command**

Add `tickbiterisk etl regional-county-adjacency` with `--county-geojson-path`, `--fetch-census-geojson`, and `--output-dir`. It reads or fetches normalized GeoJSON, calls the regional writer, and writes `regional_county_geojson_source_manifest.csv` when fetching.

- [ ] **Step 4: Run GREEN**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_cli_regional_county_adjacency.py tests/test_regional_county_geometry.py tests/test_spatial_neighbors.py -q`. Expected: tests pass.

### Task 4: Docs, Live ETL, And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `docs/data-sources.md`

- [ ] **Step 1: Update docs**

Document the official Census TIGERweb GeoJSON source, the new command, the output files, and the design rule that state borders are display/rollup metadata rather than model boundaries.

- [ ] **Step 2: Run focused docs/tests**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_public_docs.py tests/test_cli_regional_county_adjacency.py tests/test_regional_county_geometry.py tests/test_spatial_neighbors.py -q`.

- [ ] **Step 3: Run live ETL**

Run `PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl regional-county-adjacency --fetch-census-geojson --output-dir build/etl/regional-county-adjacency`.

- [ ] **Step 4: Full verification**

Run `PYTHONPATH=. ./.venv/bin/python -m pytest -q`, `PYTHONPATH=. ./.venv/bin/python -m ruff check .`, `PYTHONPATH=. ./.venv/bin/python -m tickbiterisk.cli etl provenance-audit --root-dir build/etl`, `npm run test:dashboard`, and `node --check public/app.js && git diff --check`.

- [ ] **Step 5: Commit**

Commit with `feat: add regional county adjacency graph`.

## Self-Review

The plan covers acquisition, normalized geometry, cross-border adjacency output,
CLI access, provenance, docs, live ETL, and verification. It does not change
public forecast branch selection or add a regional spatial model lane; those are
separate follow-up slices after the graph exists.
