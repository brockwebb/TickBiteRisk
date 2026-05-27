# Mast/Acorn Modeling Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract usable Maryland DNR mast/acorn table data and include prior-year mast features in the model comparison layer.

**Architecture:** Keep raw mast extraction separate from model feature joins. The mast ETL emits source-report lineage and cautious quality flags; the model layer consumes only official mast rows as prior-year ecology predictors.

**Tech Stack:** Python stdlib CSV/regex dataclasses, existing `pypdfium2` extraction, Typer CLI, pytest, ruff.

---

### Task 1: DNR Table Parser

**Files:**
- Modify: `tickbiterisk/etl/mast_acorn.py`
- Modify: `tickbiterisk/etl/mast_acorn_build.py`
- Test: `tests/test_mast_acorn.py`

- [ ] Add failing tests for rolling DNR Table 1, Table 2, and Table 3 parsing from text.
- [ ] Verify the tests fail because the current parser only supports explicit `County:` blocks.
- [ ] Implement table-aware parsing for Garrett, Allegany, Washington, and Frederick.
- [ ] Preserve source-report year, parser method, extraction confidence, and Western Maryland study-plot flags.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_mast_acorn.py -q`.
- [ ] Commit parser and mast writer changes.

### Task 2: CLI And Live Mast Output

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_mast_acorn.py`

- [ ] Add or update CLI tests to expect structured rows from the mast command.
- [ ] Ensure `build_mast_acorn_from_pdf` annotates rows with the selected parser method.
- [ ] Run `tickbiterisk etl mast-acorn --raw-dir data/raw/ecology/mast --output-dir build/etl/mast`.
- [ ] Confirm the raw mast CSV is no longer header-only.
- [ ] Commit CLI/live output changes if generated artifacts are tracked or required by tests.

### Task 3: Prior-Year Mast Model Features

**Files:**
- Modify: `tickbiterisk/etl/model_features.py`
- Modify: `tickbiterisk/etl/model_features_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_model_features.py`

- [ ] Add failing tests proving mast observation year 2021 joins Lyme model year 2022, not 2021.
- [ ] Add failing tests for overlap dedupe by newest source-report year.
- [ ] Implement optional `mast_acorn_path` reading and prior-year joins.
- [ ] Add model-level missingness and source quality flags.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_model_features.py -q`.
- [ ] Commit model feature changes.

### Task 4: Design Matrix And Model Comparison

**Files:**
- Modify: `tickbiterisk/modeling/design_matrix.py`
- Modify: `tickbiterisk/modeling/model_compare.py`
- Test: `tests/test_model_design_matrix.py`
- Test: `tests/test_model_comparison.py`

- [ ] Add failing tests for mast numeric feature columns and missing indicators.
- [ ] Add failing tests showing mast features enter forecast ecology but not forecast safe selectors.
- [ ] Add mast numeric columns to design matrix source and optional numeric sets.
- [ ] Add mast feature names to the forecast ecology selector and exclude mast caveat flags as predictors.
- [ ] Run focused model tests.
- [ ] Commit modeling changes.

### Task 5: Source Catalog And Docs

**Files:**
- Modify: `tickbiterisk/etl/ecology_sources.py`
- Modify: `tests/test_ecology_sources.py`
- Modify: `docs/data-manifest.md`
- Modify: `docs/etl-pipeline.md`
- Modify: `docs/model-spec.md`
- Modify: `README.md`

- [ ] Add source-manifest entries for easy official future sources: EPA EnviroAtlas, USDA FIA/EVALIDator, and Maryland DNR Archery Hunter Survey.
- [ ] Update docs to say mast/acorn is structured for Western Maryland study plots and used only as prior-year ecology context.
- [ ] Run source/docs tests.
- [ ] Commit docs and catalog changes.

### Task 6: Full Rebuild And Verification

**Files:**
- Generated under `build/etl/**` and `public/data/**` as appropriate.

- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m pytest -q`.
- [ ] Run `PYTHONPATH=. ./.venv/bin/python -m ruff check .`.
- [ ] Run `npm run test:dashboard`.
- [ ] Rebuild mast, model features, design matrix, and model comparison with mast enabled.
- [ ] Inspect model comparison summary for whether ecology lanes improve.
- [ ] Commit generated tracked artifacts if any changed.
