# CC Task — County-level 70 °F unseasonable-early-warmth feature: magnitude signal check (pre-committed, three forms)

Date: 2026-06-01
Branch: `codex/surveillance-regime-bridge`
Author: desktop session (spec only)
Register in graph as: proposed ResearchTask (via `seldon_cc_register` on this file)

---

## Purpose & honest framing (read before building)

Test whether a **rare, high-threshold, unseasonable early-season warm spell (≥70 °F)**
associates with annual Lyme-incidence MAGNITUDE, on the existing six-state county panel,
using the existing within-county rank machinery. Motivated by a field-experience
hypothesis: unseasonably warm early weeks drive early tick activity/bites.

**This feature is aimed at the magnitude outcome, and that carries a KNOWN structural
risk the interpretation MUST encode (do not soften it):**
- Early-season warmth is mechanically a **timing/phenology** signal. The spring questing
  nymph cohort's SIZE was set the PRIOR year (larvae fed in year t−1). Same-year (lag-0)
  warmth can shift WHEN that fixed cohort quests/bites, not HOW MANY ticks exist.
- Therefore a **lag-0 association is confound-suspect by construction** (early warmth
  co-varying with latitude / season-length / structurally higher-incidence places, or
  with same-year reporting). Only a **lag-1** association would be mechanically coherent
  for magnitude, and even then it is thin on 5 annual points.
- The ONE thing genuinely new vs. the prior early-season GDD check: a ≥70 °F sustained
  spell captures *anomalous* early heat (a weather EVENT), not "generally warmer spring"
  (a place-proxy). So its confound profile differs from the GDD integral — a March heat
  wave is more plausibly an event than a latitude proxy. This is the honest case FOR
  running it. It does NOT remove the lag mismatch.

A lag-0 hit must NOT be reported as "70 °F found the signal." It is confound-suspect.
Say so in RESULTS, up front.

## Pre-committed design (FIXED before any result is seen — this is what keeps it clean)

- Threshold: **70 °F**, single committed value (user decision). NOT a grid. Not tuned.
- Three feature FORMS, all pre-committed, **ALL reported regardless of which (if any)
  lights up** — three declared forms is a small fixed set, not a search, ONLY if every
  form's result is reported. Reporting only the form that hits = cherry-pick = invalid.
  1. `warm70_onset_doy` — day-of-year of the FIRST day starting a sustained run of
     `run_days` consecutive days with **daily-max** temp ≥ 70 °F, within the early-season
     window. (Closest to the "unseasonably warm week early" hypothesis. Most exposed to
     the lag mismatch.) Expected sign: **−** (earlier hot spell → earlier season → ?).
  2. `warm70_spell_count` — number of distinct ≥`run_days`-day ≥70 °F spells in the
     window. (Anomaly-magnitude; a lag-1 hit here is the most mechanically arguable.)
     Expected sign: **+**.
  3. `warm70_presence` — binary: did any sustained ≥70 °F spell occur in the window.
     (Weakest; near-binary on a 5-pt panel → likely null by construction. Reported anyway
     so its weakness is on the record, not hidden.) Expected sign: **+**.
- Use **daily-max** (tmax_f), not daily-mean: a 70 °F MEAN is a very hot day; the
  hypothesis is about warm days, so a ≥70 °F max sustained for several days is the
  biologically intended "unseasonable early warm spell." State this choice explicitly.
- `run_days` = **5** (a sustained spell ≈ a warm work-week; single committed value, not a
  grid). Window = early season, DOY 60–151 (Mar 1 – ~May 31); committed, not tuned.
- Both **lags 0 and 1** reported (never just one). Held fixed across both segments.
- All thresholds/windows/run-length live in `config/signal_check.toml` under a new
  `[signal_check.warm70]` table. Nothing hardcoded (constitution §2).

## Machinery — REUSE, do not reinvent

Reuse `scripts/within_segment_signal_check.py` functions by import (same as the
early-season check did): `_rank`, `pooled_spearman`, `bootstrap_ci`,
`loo_year_stability`, the within-county/within-segment panel build, the fail-loud
join-coverage logic, and the n=2 gate. The ONLY new code is the three feature
definitions + the config block. Re-verify the imported functions produce identical
output (they are accepted from prior checks).

## Procedure

For each form × each lag {0,1} × each segment {2017-2021, 2022-2023}:
- within-county, within-segment rank-normalize feature and incidence (Option-A basis);
- pooled Spearman ρ + bootstrapped 90% CI over counties;
- 2017–2021 (assessable): LOO-year sign-stability;
- 2022–2023: **direction only, stability INDETERMINATE (n=2)** — same hard rule; no
  manufactured stability statistic;
- fail-loud join coverage per state per year; surface (do not drop) any incidence-
  without-weather county (e.g. VA 51515).

## RESULTS (`cc_tasks/2026-06-01_warm70-county-magnitude-check_RESULTS.md`)

- Report ALL THREE forms × both lags × both segments — the full surface, no winner.
- Interpretation section MUST state, up front: lag-0 hits are confound-suspect (timing-
  vs-magnitude mismatch); only lag-1 is mechanically coherent for magnitude; the ≥70 °F
  anomaly-event framing is the one thing distinguishing this from the GDD place-proxy.
- If everything is null/weak (the honest prior given two prior null checks + Eisen 2016):
  report it plainly as the third converging null. A null here is a real result, not a
  failure, and should feed the weather-magnitude finding (lab note 10) as corroboration.
- Register results in the graph (no bare numbers). Cite the prior two checks.

## Success criteria

- [ ] 70 °F single threshold, daily-MAX, run_days=5, window DOY 60–151 — all in config.
- [ ] Three forms implemented; EVERY form × lag × segment reported (no form omitted).
- [ ] Existing rank/Spearman/bootstrap/LOO/join machinery reused via import, re-verified.
- [ ] Both lags reported; 2022–2023 direction-only, stability INDETERMINATE (n=2).
- [ ] Interpretation encodes lag-0-confound-suspect + timing-vs-magnitude up front.
- [ ] No tuning, no threshold search, no form cherry-picked.
- [ ] RESULTS written on real repo path; results registered; `seldon verify` clean;
      `seldon cc complete <this-task-file>` run.

## Out of scope

- Any blend / forecaster / model change.
- A timing/phenology test (the mechanically-correct home for this feature) — BLOCKED:
  sub-national case-onset timing data does not exist on disk (`data/raw/seasonality/`
  onset files are NATIONAL only). Note this in RESULTS as deferred-pending-data, NOT
  refuted. Do not substitute a national-grain timing test here.
- The 72.9% adjusted-scale arm; 2024 incidence; touching `public/`/bundles/live forecast.
- Re-running checks 1 or 2 (accepted).
