# Score–Percentile Coherence, Forecast-Interval Display, and the Stop Decisions

Status: draft
Primary sources: `cc_tasks/results/2026-06-03_henrico-score-floor-rederivation-RESULTS.md` (graph Results under diagnostic task `b8b53c75`); `cc_tasks/2026-06-03_optionA-headline-demote-percentile-ci-incidence-range.md` (task `c90eb575`, shipped @ 28ef7a6); `cc_tasks/2026-06-03_cleanup-deadcode-and-regional-scale-wording.md` (`0adc9bee`); `cc_tasks/2026-06-03_automate-rebuild-and-tevv-materiality-report.md` (`f977df8a`); `cc_tasks/2026-06-04_fix-tevv-structural-blindspot-and-minification.md` (`ce582259`); `cc_tasks/2026-06-04_v2-finish-provenance-render-capture-handoff.md` (`fc6b0c5e`)
Reviewer focus: the decisions here are mostly about WHAT NOT TO BUILD. The score was never wrong; the defect was presentational. Read the "stop decisions" section as the load-bearing content.
Last checked against commit: Option A live @ `28ef7a6`; v2 bundle ready-but-unshipped at time of writing (2026-06-05)

## Decision (summary)

Three coupled decisions, all resolved toward *less mechanism, not more*:

1. **The regional risk score stays regional-relative and unchanged.** Henrico's `risk_score = 1/10` is correct and means low. The score–percentile incoherence on screen was a **display** defect, not a scoring bug. Fixed by demoting the self-relative percentile out of the headline (Option A), not by rescaling the score or adding an absolute-threshold scale.
2. **The forecast interval is shown as an incidence range, never as own-history percentile ranks.** The percentile-rank interval saturates uselessly (4.35→100 on small n) and misleads; the incidence band ([0, 61.12] / [0, 148.70] for Henrico 2026) is the honest quantity. The interval carries **no weather/ecology term** — it is an empirical rolling-origin residual quantile band, consistent with lab notes 10/11.
3. **The v2 "plausible score range" UI is honest for lo-fi data and is the more defensible presentation than a bare point score** — decided on the reasoning that a 3-year-out, national-emergence-rate forecast is low-fidelity by construction, so the point score *overclaims* precision and the range corrects it. Ship is gated only on one render check (how high the band reaches on a floored county; see "open").

## The incoherence (what was actually wrong)

The regional dashboard showed a floored county (Henrico, score 1/10, very low) with a self-relative headline "much higher than typical" / "100th percentile". Both halves were **individually correct** and the on-screen contradiction was the bug:

- **Score** is regional-relative: 1/10 means low *vs the six-state distribution* (Henrico verified rank 41/283 ascending — near the regional floor; 119/283 = 42% of counties also floor at score 1).
- **Percentile** is self-relative: 100th means the 2026 forecast (7.94/100k) exceeds Henrico's own 23-year history (prior max 5.96/100k in 2013). Verified `n=23`, NOT degenerate — H2 (typicality bug) was killed. The interval's 4.35% lower bound is the legitimate 1/23 rank floor, not a math error.

Two true statements about different baselines, displayed as if comparable. The one-glance reader stops at "much higher than typical" and reads alarm into a county whose absolute risk (~8/100k) is low.

## The key reframe (the decision that prevented a rebuild)

Initial framing reached for Option B (surface the self-relative signal prominently) and then Option C (absolute-threshold rescale). Both were **rejected on the user's reasoning**: 7.94/100k is low in absolute public-health terms regardless of regional rank or self-relative history. Surfacing the self-relative percentile prominently (B) would *manufacture false alarm*; building a new absolute scale (C) collides with the 2022 CSTE +72.9% reporting break and the score already encodes "low" via its `very_low` band.

→ Collapsed to **Option A**: the score's own absolute-low category drives the headline; the self-relative percentile is demoted to a muted paired note (or cut); the interval renders as incidence range. No scoring change, no new scale. This is the "don't build more instrument than the decision needs" discipline — the mirror of lab notes 10/11's "don't claim more signal than you have."

## Transfer assumption (surfaced, not hidden)

The interval is built from residuals **pooled per model across all counties**, so a low-incidence county inherits the region's absolute residual spread. This is a real transfer assumption and is surfaced two ways: a muted panel footnote (live) and a model_card caveat (in source; ships with v2). **Open risk** carried to the v2 ship decision: pooled residuals could blow a floored county's upper band up toward "moderate/high," which would re-introduce via the *range* exactly the alarm Option A removed from the *headline*. The `fc6b0c5e` render check exists to catch this.

## STOP DECISIONS (the load-bearing content)

This conversation's main output is a sequence of refusals to expand scope. Recorded because the temptation each time was to keep building.

1. **Did not rescale the score.** The score works; the defect was display. Rescaling would have been a modeling change with a new silent-error surface, under launch pressure, to solve a problem that was presentational.

2. **Did not surface the self-relative signal prominently (rejected B).** "More honest" prominence would have been less honest in effect — false alarm on a low-risk county. Honesty of *presentation* ≠ honesty of *each statistic in isolation*.

3. **Did not auto-wire the publish trigger.** The rebuild automation builds/validates/promotes/commits but the **publish/deploy trigger was deliberately never wired**. The pipeline stays *armed-but-manual*. This single restraint is why the v2-schema near-miss (below) was caught instead of shipped.

4. **The v2 near-miss — the validation of restraint.** A dry-run rebuild would have shipped a v1→v2 schema bump + populated score-range UI + caveat change + a 28 MB reformat, and the first TEVV implementation reported **REVIEW_RECOMMENDED=no** on all of it. The by-exception safety net was BLIND to structural change because materiality was scoped to *values* (incidence/category/score-bin) only. Had publish been auto-wired, a UI change ships silently to a public health site. It was caught by CC inspecting the diff, NOT by TEVV. Lesson, now encoded (TEVV B1–B5): **materiality of a data-product change is in its SHAPE (schema, field population, caveats, serialized size, record counts), not only its values.**

5. **Did not let "fix and re-run" become "and now it's shippable."** Teaching TEVV to *detect* the schema/UI change was held strictly separate from *approving* it. Post-fix, a rebuild correctly returns REVIEW_RECOMMENDED=YES and stops — the system working, not a green light.

6. **Did not ship v2 to "finish fast"; did not cut it short either.** User's terminal-state bar: finish to the state the data permits, then stop — not minimal-launch, not endless polish. "Finished" = the product honestly presents AS a conservative lower-bound, lo-fi, annual-validation-only, no-earned-covariate forecast. Adding signal would be the failure; presenting the limitation accurately is the deliverable.

## Verification discipline that held

- Henrico numbers were **unpersisted handoff prose** (prior session) — no RESULTS file, no graph node. Re-derived from source (CC, since the 79 MB weekly file is unreadable through the desktop MCP), persisted as both a RESULTS file AND 9 queryable graph Result nodes. The handoff's "rank 243/283" was a direction artifact of 41/283 ascending — caught only by re-derivation.
- Desktop verified the Option A *test logic* directly (the floored-county Playwright test is adversarial — injects the alarm string, asserts suppression) but trusted the *runner* on pass/fail. Calibration made explicit mid-session: re-derive claims-about-data/state with no execution behind them; trust the runner on green; reserve loud flags for genuine design defects, not verification theater.
- The cleanup task exposed that Option A's "green" suite had a **presence-assertion pointed at dead code** (three phrases asserted-present existed only in the never-called `renderRegionalForecastTypicality`). The suite was green for the wrong reason. Standing lesson: presence-in-source ≠ rendered-to-user.

## Provenance hole found (carry forward)

The deployed `regional_county_risk_weekly.json` was minified by an **external, non-Python, undocumented tool** (deployed bytes show `0.00003` where Python json emits `3e-05`, divergence at byte ~99600). The deployed v1 weekly artifact was therefore **not fully reproducible from the codebase**. An in-repo deterministic compact writer now closes this going forward. Unknown whether the same external tool historically touched other files — flagged for capture as a graph observation (`fc6b0c5e` OBS-1).

## Scoped conclusion

1. Score stays regional-relative and unchanged; the fix was presentational (Option A, live @ 28ef7a6).
2. Interval shows incidence range, no weather/ecology term — consistent with the closed weather (10) and ecology (11) arcs.
3. v2 plausible-range UI is the honest presentation for low-fidelity data; ship gated only on the floored-county upper-band render check.
4. The rebuild pipeline is armed-but-manual by design; structural materiality (TEVV B1–B5) is a necessary axis distinct from value materiality.
5. The product's contribution is its conservatism and its honesty about fidelity — *the restraint is the result.*
