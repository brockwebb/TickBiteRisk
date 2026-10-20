# CC Task: Seldon Init + Reporting-Basis Remediation Verification

Date: 2026-05-31
Author: Desktop session (planning/verification)
Branch context: codex/surveillance-regime-bridge (Codex's remediation work; confirm actual branch state with git before acting)
Status: ready for CC execution

---

## Purpose

Two jobs, in order:

1. **Bring the project under Seldon configuration control** (it is not yet — no `seldon.yaml`, no graph state, no registered artifacts, no handoffs in the graph).
2. **Verify Codex's reporting-basis remediation against ground truth WITH TEETH** — i.e. by running the test suite and reading guard test bodies, not by trusting Codex's reported pass counts or reading manifests. A prior desktop verification pass confirmed the *identification decision* against disk artifacts but could NOT run the test suite (bash was container-side, not the repo). This task does the part that requires actually executing things on the user's machine.

DO NOT start step 6 (raw-vs-adjusted model ranking), weather/ecology/RF/Bayes work, or any new modeling. This is config + verification only.

---

## Operating Constraints

- The graph is the source of truth; files are projections. Codex's `reporting_basis_adjustment_runs.csv` manifest is a FILE artifact — useful provenance, but under Seldon the identification decision must also exist as GRAPH state (a closed ResearchTask or an Issue with resolved state). Reconcile the two; do not treat the CSV as sufficient on its own.
- Do NOT trust any "X passed" / "N tests passed" claim from the prior Codex thread. Re-run everything. Two prior agents made confident claims that were false (a file write that never landed, an in-region control that did not exist in the data). Re-run, read test bodies, report evidence.
- If something is broken, name it and open a Seldon Issue. Fixing is a separate task unless the fix is trivial and you note it explicitly.

---

## Part A — Seldon Initialization & Config Control

A1. Orient: run `seldon go` (CLI, on the user's machine) and read whatever it reports. Note that as of this writing it reports no `seldon.yaml`, no CLAUDE.md, no handoffs, no graph state.

A2. **Discover the correct bootstrap procedure — do not assume.** There is no `seldon init` in the MCP command list and the desktop session that wrote this task did not have the CLI. Before initializing, read the Seldon convention docs (look under `docs/conventions/` if present) and run `seldon --help` / `seldon status` / any `seldon` subcommand help to find the actual project-bootstrap command. If a convention doc describes init, follow it verbatim. If you cannot determine the correct procedure, STOP and report — do not guess at a command that may corrupt state.

A3. Initialize the project under Seldon per the discovered procedure. Expected outcomes (verify each actually happened, do not assume):
   - `seldon.yaml` exists and is valid.
   - The graph backend is reachable (the desktop session confirmed Neo4j MCP servers exist in the environment: `neo4j-mcp`, `neo4j-pragmatics`, `neo4j-quarry` — confirm which one Seldon is wired to, if any, via the config; do not assume).
   - `seldon status` returns project state without error.

A4. Register the already-existing decision artifacts so they are under config control:
   - `docs/research/lab-notes/08-reporting-basis-identification.md`
   - `docs/research/source-materials/did-control-verification-2017-2019.csv`
   - `docs/research/source-materials/README.md`
   - `docs/surveillance-regime-bridge-spec.md` (if not already tracked)
   - The reporting-basis artifacts under `build/etl/reporting-basis-adjustment/` — decide with the user whether build outputs are registered artifacts or projections; do not register large regenerable build outputs as source artifacts without reason.

A5. Record the identification decision as GRAPH state, not just the CSV manifest:
   - Create (or confirm) a ResearchTask representing "identify reporting-basis adjustment factor," walked to a CLOSED/completed state, with a note that the out-of-region DiD path was evaluated and failed (`insufficient_unsuppressed_county_panel_2017_2019`) and the CDC published anchor is the earned identification.
   - If the raw-vs-adjusted ranking gate (step 6) is tracked, confirm it is represented in the graph as unblocked-by-CDC-anchor, with ITS diagnostic-only.
   - Link these to the lab note and verification CSV artifacts.

A6. Commit the Seldon config and registrations on the working branch. Run `seldon verify` before commit; resolve what `--fix` can, report the rest.

---

## Part B — Verification With Teeth (the part the desktop session could not do)

For EACH item below report PASS / FAIL / UNCERTAIN, the specific evidence (test name, file path, line, actual run output), and any gap. Do not soften.

B1. **Re-run the suite. Do not trust the reported count.**
   - Run `pytest` fully. Codex claimed 795 passed. Report the actual number and any skips/xfails.
   - Run `ruff check .`. Report.
   - Run `git diff --check`. Report.
   - Run `npm run test:dashboard` (Playwright). Codex claimed 2 passed. Report.
   - Confirm NO `* 2.py` Finder-conflict duplicates are being collected by pytest (the desktop session confirmed 0 on disk via Filesystem search, but pytest collection is the signal that matters — a gitignored-but-present file can still corrupt local collection). Report the collected-item count and confirm no `* 2` files appear in collection.

B2. **Contamination guard — item 2 (data-assembly surface).** This is a SEPARATE guard from B3. Find the test that asserts the forecast design matrix build FAILS when any `did_control_panel.csv` county FIPS appears in forecast rows. READ THE TEST BODY. Confirm it injects a control FIPS and asserts the pipeline raises/fails — confirm it tests the FAILURE path, not a trivially-true assertion on clean data. Name the test. Note: `did_control_panel.csv` is currently header-only (no control was constructible), so the guard must be tested with a synthetic/injected control FIPS, not the empty live panel. Confirm the test does this.

B3. **Cross-jurisdiction residual guard — item 7 (post-forecast calibration surface).** This is a SEPARATE guard from B2 and guards a DIFFERENT failure path: one jurisdiction's residual must not multiply another jurisdiction's POINT forecast (intervals-only is the allowed path). Find the test, READ THE BODY, confirm it exercises the cross-jurisdiction point-correction path and asserts it is blocked.
   - **CRITICAL:** If B2 and B3 are covered by a SINGLE test, that is a FAIL on B3 unless the single test demonstrably asserts BOTH failure paths. Determine this by reading what the test actually asserts, not its name or docstring. If it only checks design-matrix membership, report item 7 as UNGUARDED and name it as the missing tripwire. Two independent failure paths require two independent assertions.

B4. **Cross-regime guard.** Raw-target training crossing the 2022 boundary must raise `CrossRegimeTrainingError` by default; the `--allow-cross-regime-raw-targets` override must stamp `cross_regime_raw_training_allowed` on every output row. Read the tests; confirm they assert the RAISE, not just the happy path. Name them.

B5. **Shared classifier not forked.** Confirm `regimes.py` (or the actual regime-classification module) is ONE shared module imported by BOTH `model_diagnostics.py` and the adjustment ETL. Grep for duplicate/forked copies. A forked second copy silently reintroduces divergent-logic risk. Report the import graph.

B6. **`did_ratio=0.0` placeholder is inert.** The live run manifest carries `did_ratio=0.0`, `did_control_shift=0.0`, `parallel_trends_control_slope=0.0` — these are placeholders for "no control existed," NOT computed adjustment values. READ THE CODE PATH that consumes the manifest and confirm the applied adjustment factor comes from the CDC anchor (`identification_method=cdc_published_anchor`) and that the `0.0` did_ratio CANNOT leak in as a real multiplicative factor anywhere downstream. This is the highest-value correctness check in Part B. Report the consuming function and the guard that prevents the leak.

B7. **Gate state.** Confirm step 6 (raw vs adjusted ranking) is unblocked specifically by the CDC fixed-prior anchor, ITS remains diagnostic-only, and the regenerated `reporting_basis_adjustment.csv` has 0 ITS rows. Verify the 0-ITS claim by actually filtering the file, not by trusting the manifest. Confirm no step-6 ranking was actually executed.

B8. **API alias.** Confirm `single_bite_risk_score_raw` exists as a DEPRECATED alias of the banded `single_bite_risk_score` (not hard-removed), documented in `api/api-spec.md` with a removal-next-version note. Banded fields (low/score/high) primary.

B9. **Uncertainty bands.** Spot-check actual output rows: `score_low <= score <= score_high` for every public row; bands widen on basis_adjusted vs a zero-variance-factor control; grow monotonically 2024->2025->2026; tighter at 2024 when the PA anchor is present. Confirm via the tests AND by reading real output rows.

---

## Reporting

Findings go into the GRAPH as Issues/ResearchTasks (per Seldon convention), not only as prose. For each Part B item, also give the PASS/FAIL/UNCERTAIN + evidence in the closeout. End with a single judgment: is the reporting-basis remediation VERIFIED (config under control, guards proven independent and firing, gate correct, anchor inert-placeholder confirmed) or NOT. Do not soften it.

Run `seldon closeout` then `seldon verify` before commit.
