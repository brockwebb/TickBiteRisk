# Reporting Basis Adjustment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the regional-first reporting-basis adjustment core from `docs/surveillance-regime-bridge-spec.md`.

**Architecture:** Reuse the shared `regimes.py` classifier, build regional high-incidence classification and reporting-basis adjustment artifacts from the regional incidence panel, join basis-adjusted targets beside raw design-matrix targets, and make raw cross-regime model comparison fail unless explicitly overridden.

**Tech Stack:** Python 3.12 stdlib, CSV/dataclass ETL style, pytest, Typer CLI.

---

### Task 1: Shared Regime Classifier

**Files:**
- Create/keep: `tickbiterisk/modeling/regimes.py`
- Modify: `tickbiterisk/modeling/model_diagnostics.py`
- Test: `tests/test_surveillance_regimes.py`

- [x] Write RED tests for the shared classifier.
- [x] Implement `regimes.py` and delegate `model_diagnostics._classify_surveillance_regime`.
- [x] Verify focused tests pass.

### Task 2: Reporting-Basis Adjustment Artifact

**Files:**
- Create: `tickbiterisk/modeling/reporting_basis_adjustment.py`
- Create: `tickbiterisk/modeling/reporting_basis_adjustment_build.py`
- Test: `tests/test_reporting_basis_adjustment.py`

- [x] RED tests for high-incidence classification from the panel.
- [x] RED tests for DiD factor estimation with required parallel-trends check.
- [x] RED test for `did_parallel_trends_violated`.
- [x] RED test that adjacency smoothing avoids a state-line factor cliff.
- [x] Implement artifact dataclasses, builders, reader, writer, and source sha provenance.

### Task 3: Basis-Adjusted Design-Matrix Targets

**Files:**
- Modify: `tickbiterisk/modeling/design_matrix.py`
- Modify: `tickbiterisk/modeling/design_matrix_build.py`
- Test: `tests/test_model_design_matrix.py`

- [x] RED test for `source_regime`, `basis_factor_applied`, CI bounds, `target_*_basis_adjusted`, `target_is_reference_basis`, `missing_basis_factor`, and `displayed_as`.
- [x] Implement optional `reporting_basis_adjustment_path` support.
- [x] Verify focused design-matrix tests.

### Task 4: Model-Comparison Target Scale And Guard

**Files:**
- Modify: `tickbiterisk/modeling/model_compare.py`
- Modify: `tickbiterisk/modeling/model_compare_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_model_comparison.py`

- [x] RED tests: raw cross-regime training raises; override succeeds and flags rows; basis-adjusted target scale succeeds and flags rows; missing basis factors still raise.
- [x] Implement `target_scale={raw,basis_adjusted}`, `allow_cross_regime_raw_targets`, and `CrossRegimeTrainingError`.
- [x] Expose CLI options.
- [x] Verify focused model comparison and CLI tests.

### Task 5: PA Step-1 Forecast Skill Anchor

**Files:**
- Create: `tickbiterisk/modeling/forecast_skill_anchor.py`
- Create: `tickbiterisk/modeling/forecast_skill_anchor_build.py`
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_step1_forecast_skill_anchor.py`
- Test: `tests/test_cli_step1_forecast_skill_anchor.py`

- [x] RED test for PA 2024 residual anchor rows from observed-fit comparisons.
- [x] RED test that the anchor cannot expose a point-correction multiplier.
- [x] Implement interval-calibration-only anchor dataclasses, writer, and CLI.

### Task 6: Verification

- [x] Run focused pytest for new/modified modeling tests.
- [x] Run ruff on touched Python files.
- [x] Remove untracked Finder-conflict `* 2.py` files from source, tests, and `.venv`.
- [x] Verify the full pytest suite collects without an ignore glob.

### Task 7: Public Score-Band Runtime Contract

**Files:**
- Modify: `tickbiterisk/modeling/risk_score.py`
- Modify: `tickbiterisk/modeling/risk_score_build.py`
- Modify: `tickbiterisk/runtime/risk_lookup.py`
- Modify: `tickbiterisk/runtime/single_bite.py`
- Modify: `tickbiterisk/runtime/static_export.py`
- Modify: `public/app.js`
- Modify: `public/regional-research.js`
- Modify: `api/api-spec.md`, `docs/user-guide.md`, README
- Update: `public/data/*.json`
- Test: risk-score, lookup, single-bite, CLI, static export, public dashboard docs/data

- [x] Update `api/api-spec.md` with the score-band contract gate and downstream dependency catalog before payload changes.
- [x] RED tests for county-week `risk_score_low/high`, static schema v2, single-bite score bands, the deprecated `single_bite_risk_score_raw` alias, dashboard JS, and committed public data.
- [x] Implement score-band propagation through generated score CSVs, runtime lookup, static export, and single-bite payloads.
- [x] Regenerate committed public static data with schema v2 fields.

### Task 8: Identification Remediation And Gate

**Files:**
- Modify: `tickbiterisk/modeling/reporting_basis_adjustment.py`
- Modify: `tests/test_reporting_basis_adjustment.py`
- Update: `docs/surveillance-regime-bridge-spec.md`
- Runtime artifacts: `build/etl/reporting-basis-adjustment`

- [x] Run reporting-basis adjustment on the live regional panel and record that all six jurisdictions classify high-incidence in 2017-2019.
- [x] Demote `interrupted_time_series` to diagnostic-only; public adjustment rows use the CDC fixed-prior anchor.
- [x] Add `did_control_panel.csv` as a walled-off non-forecast identification instrument.
- [x] Record the out-of-region DiD path as evaluated and foreclosed with `did_control_evaluated=true`, `did_control_passed=false`, and `did_control_failure_reason=insufficient_unsuppressed_county_panel_2017_2019`.
- [x] Add design-matrix contamination guard: any control county FIPS in forecast rows raises.
- [x] Add 2008/2017 method-validation provenance fields.
- [x] Restore `single_bite_risk_score_raw` as a deprecated alias for one release and document removal-next-version in `api/api-spec.md`.
- [x] Emit adjustment rows for every surveillance regime used by the design-matrix join, including neutral reference-basis rows.
- [x] Investigate official MA 2025 county-level Lyme data before adding any MA forward answer key; 2025 statewide annual data exist, but county-level Lyme case data were not verified from official sources, so MA is not added.
- [x] Rebuild reporting-basis adjustment artifact and verify the gate method is `cdc_published_anchor`.
- [x] Confirm step 6 is unblocked by the CDC fixed-prior anchor, with sensitivity to the national scalar carried forward as a discussion risk.
- [x] STOP before starting step 6 or any weather/ecology/RF/Bayes work.
