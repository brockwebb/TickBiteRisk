# CC Task — deliberate v2 bundle promote (the one step that changes the deployed bundle)

Date: 2026-06-05
Author: desktop session (spec only)
Posture: THIS IS THE SHIP. Every prior task this arc proved the bundle byte-identical;
this one intentionally changes it. Armed-but-manual by design. Single deliberate
promote, full TEVV review, no shortcuts. Prerequisite: session-closeout `89473d7d`
complete and main clean/pushed first.

## Preconditions (verify before doing anything; STOP if any fails)
- session-closeout `89473d7d` is `completed` and its RESULTS exist on disk.
- `git status` clean; `main == origin/main` at the post-closeout sha.
- The clamp is live in `public/regional-research.js` on main (merged `5cd3f11`).
- `public/research-data/` currently still byte-identical to origin (i.e. nothing has
  pre-promoted the bundle). Confirm, then proceed.

## What v2 changes (EXPECTED deltas — these are intended, not surprises)
The deployed bundle is still v1 (risk_score_low/high NULL). v2 populates them. The
TEVV dry-run SHOULD flag exactly these three, and only these:
1. Schema version bump v1 → v2.
2. `risk_score_low` / `risk_score_high` field population 0% → ~100%.
3. Serialized-size / reformat delta (~28 MB class), deterministic compact writer.
These are the intended v2 surface. The clamp is DISPLAY-only (already live in JS) and
does NOT change the bundle — the bundle carries raw low/high; the clamp renders them.
So the bundle's low/high are the unclamped values; that is correct and intended.

## Step 1 — dry run, and READ the TEVV summary
- `python -m <the rebuild_and_publish entrypoint> --dry-run` (use the actual
  console-script / module path; do not guess — grep `pyproject.toml`/`cli.py` for
  the rebuild_and_publish command if unsure).
- Capture the TEVV materiality summary VERBATIM into the RESULTS file. This one-page
  summary is the entire reason the pipeline is manual — it must be read, not skipped.
- GATE on the summary:
  - If TEVV flags ONLY the three expected deltas above → proceed to Step 2.
  - If TEVV flags ANYTHING ELSE (record-count change, unexpected FIPS set, caveat-text
    change, field changes beyond low/high, REVIEW_RECOMMENDED reasons not in the list
    above) → STOP. Do not promote. Report the unexpected delta and await Brock. An
    unexpected delta here is exactly the near-miss class this gate exists to catch.
  - Confirm the dry run reports the structural checks (B1–B5: schema version, field
    population rate, caveat text, serialized size, record counts) — not value-only.
    A value-only TEVV pass is insufficient (proven by the prior near-miss).

## Step 2 — promote the 11 files
- Only after Step 1 gate passes: run the real promote (drop `--dry-run`).
- It should promote the documented 11-file set (explicit copy list + fail-loud
  readiness gate — the deploy-hint fix). Report the exact files promoted and confirm
  the count is the expected 11. If the count differs, STOP and report.
- Re-render the four verification counties from the NOW-PROMOTED public bundle to
  confirm the live display is correct end-to-end: Henrico/VA Beach 1-2/10,
  Tucker 6-10/10, Cecil 4-8/10. The clamp must produce these from the promoted raw
  low/high. If any differs, STOP — the bundle and the renderer disagree.

## Step 3 — commit + push the bundle
- Single-scope commit of the promoted bundle (the 11 files + schema/version metadata):
  `git commit -m "feat: promote v2 regional bundle — populate score-range low/high (display clamp live)"`.
- `git push origin main`. Confirm the Pages deploy run triggers; report run id + status.
- After deploy success, fetch the live deployed bundle and confirm v2 is actually
  serving (schema version v2, low/high populated) — not a cache of v1. Ground-truth
  the deploy, don't trust the run-green alone.

## Gate
- `ruff check .`, `python -m pytest -q`, `node --check public/regional-research.js`,
  `npm run test:dashboard`, `seldon verify` — all green.
- TEVV dry-run flagged only the three expected deltas (Step 1).
- Promoted file count == 11; four-county live re-render correct; deploy serving v2.
- main == origin/main at the new bundle sha.

## Output
`cc_tasks/results/2026-06-05_v2-bundle-promote_RESULTS.md`:
- verbatim TEVV materiality summary + the expected-vs-actual delta check,
- promoted file list (count 11),
- four-county live re-render strings,
- commit sha, push, deploy run id + status, live-bundle-is-v2 confirmation,
- bottom line: "v2 live and serving" or "STOPPED at step N — <reason>".

## Persist / close
`seldon cc complete` only after RESULTS exists on disk AND the live bundle is
confirmed serving v2. This is the ship; the completion mark must be backed by a
deployed-and-verified artifact, not a green run.

## Scope guard
- This task DOES change the bundle — that is its purpose. It is the ONLY task
  permitted to promote/push a bundle.
- Promote the v2 regional bundle ONLY. No model refit, no score recompute, no schema
  changes beyond the intended v1→v2 bump, no scope expansion.
- Do NOT apply a0ab3cbe (9–10 band fix) during this ship session — explicitly
  out of scope per its own capture note.
- If the dry-run TEVV gate trips on anything unexpected, STOP and report — do not
  promote through a surprise. The manual gate is the point.
