# RESULTS — Early-season sustained-warmth signal check (new-hypothesis follow-on)

Date: 2026-06-01
Branch: `codex/surveillance-regime-bridge`
Mode honored: exploratory, read-only w.r.t. the model. No forecaster, no blend, no weighting. Reused the accepted machinery from the first signal check (`scripts/within_segment_signal_check.py`: rank-normalization, pooled Spearman, bootstrap CI, LOO stability, join-coverage, Option-A incidence load) via import; added ONLY the early-season feature family + threshold grid (`scripts/early_season_signal_check.py`, config `config/signal_check.toml [signal_check.early_season]`).

This is a **new-hypothesis test**, not a re-run for a better number. The first check found the annual weather→incidence signal weak; it identified a blind spot — no feature captured *sustained early-season warmth*. This tests that. A weak result is a real finding.

## Literature prior (stated up front, per task; Eisen, Eisen, Ogden & Beard 2016, *J Med Entomol* 53(2):250–61, DOI 10.1093/jme/tjv199, *I. scapularis*)

- Nymphal activity-onset is a **range** (~4–15 °C / 39–59 °F, unresolved) → the feature is evaluated across a pre-committed threshold grid, never one value.
- Cumulative GDD through ~**calendar week 20** is the best-evidenced temperature predictor of Lyme-season **timing**.
- **Load-bearing caveat:** for *interannual incidence magnitude* (what this annual panel measures), the review reports **precipitation has been a stronger predictor than temperature**, and case-count studies show **no clear/consistent temperature association**; host abundance and habitat dominate at sub-state scale and are **unmeasured confounders here**. ⇒ Temperature is well-supported for phenology/timing, weakly supported for annual magnitude. **A weak result is consistent with this prior; a strong result runs against it and must be treated with extra skepticism.**

---

## Headline

**A suggestive — NOT established — early-season warmth signal. Do not read this as a usable predictor.** Early-season cumulative GDD through week 20 (`early_season_gdd`, the literature-preferred feature) shows a within-county association with annual incidence that is grid-stable, LOO-stable, and correctly signed (ρ ≈ **+0.30 to +0.33** across all four 8–14 °C thresholds, CIs exclude zero) — **but only at same-year lag 0 in the 2017–2021 segment.** Four reasons it must not be promoted to "the first real weather signal" without these caveats attached (graph Issue `unsupported_claim` filed against this task):

1. **Lag-0 only.** At lag 1 (prior-year weather → next-year cohort) the same feature is weak/negative and sign-unstable. The robust cell is same-year-specific.
2. **It runs against the published prior** (Eisen et al. 2016): temperature predicts Lyme *timing* more than annual *magnitude*; precipitation/host/habitat dominate interannual incidence and are **unmeasured confounders here**. A signal against the prior earns *more* skepticism.
3. **It is generic early-season warmth, not a specific mechanism.** The literal "sustained solid runs" form of the *same* hypothesis (`early_warm_run_count`/`_days`) is **NOT grid-robust** (signs flip cell-to-cell) — so what survives is the smooth GDD integral, confoundable with latitude / season length / host / habitat.
4. **Thin / unvalidated elsewhere.** 2022–2023 is indeterminate (n=2); the weather panel is internally but not externally validated.

Net: across two signal checks this is the first feature with a robust, correctly-signed, stable within-county association — a real, modest (ρ≈0.32), **same-year** signal — yet it remains **suggestive, not established, and a cross-segment blend is not warranted on this evidence alone.** No blend/forecaster proposed.

---

## Step 0 — Panel & join (re-derived, Option-A, fail-loud)

Same verified inputs as the first check. Join: incidence counties **283**, weather counties **283**, incidence-without-weather **none**, weather-without-incidence **none**. VA `51515` (Bedford City, dissolved 2013) again surfaced as a missing-value county-year (8 yrs), excluded explicitly — not silently inner-joined away.

## Steps 1–2 — Features + pre-committed grid (config-driven; every cell reported)

- **`early_season_gdd` (PRIMARY):** cumulative GDD Jan 1 → DOY 140 (week 20), base = each grid threshold.
- **`early_warm_run_count` / `early_warm_run_days` (SECONDARY):** within DOY 60–180, number of runs of ≥ `run_days` consecutive days with daily-mean ≥ threshold, and total days in such runs.
- **Grid (fixed in config before inspection):** threshold ∈ {8, 10, 12, 14} °C; `run_days` ∈ {5, 7, 10}. Soil/humidity/saturation-deficit deliberately omitted (absent in GHCND; not fabricated).

## Step 3 — Grid surface (every cell; full grid in `build/early_season_signal_check_results.json`, 112 cells; 24 results registered in the graph)

### `early_season_gdd` — PRIMARY (4 thresholds)

| Segment | lag | ρ across thresholds (min…max) | CI excludes 0? | grid+LOO stable | sign |
|---|---|---|---|---|---|
| 2017–2021 | 0 | **+0.301 … +0.333** (b8 +0.301, b10 +0.333, b12 +0.328, b14 +0.321) | yes, all 4 | **4/4 stable_sign** | + (expected) |
| 2017–2021 | 1 | −0.096 … −0.070 | yes (small) | 0/4 (LOO sign-flips) | − |
| 2022–2023 | 0 | −0.081 … +0.221 | mixed | INDETERMINATE (n=2) | — |
| 2022–2023 | 1 | +0.293 … +0.402 | — | INDETERMINATE (n=2) | — |

The 2017–2021 lag-0 result is robust to threshold choice (all four agree) and to leave-one-year-out (sign-stable in all 5 folds, e.g. b10 LOO = [0.25, 0.35, 0.33, 0.29, 0.39]). It is **same-year specific** — lag 1 is weak/negative and sign-unstable.

### `early_warm_run_count` / `early_warm_run_days` — SECONDARY (12 cells each), 2017–2021 lag 0

NOT grid-robust. `early_warm_run_count` ranges ρ = **−0.240 (t8,r5) … +0.153 (t14,r7)** — it flips sign across the grid. `early_warm_run_days` is mostly positive (ρ ≈ +0.07 … +0.23) and stable at higher thresholds but threshold-sensitive and contradicted by the count variant. **A hypothesis that only appears at some cells of its own grid is not a signal.** (lag 1 and 2022–2023: weaker / INDETERMINATE; full grid in JSON.)

### 2022–2023 (all features): DIRECTION ONLY — stability INDETERMINATE (n=2)

n=2 forces within-county ranks to {1,2} (inflated |ρ|); no stability statistic is manufactured. `early_season_gdd` lag1 is +0.29…+0.40 here but cannot be compared to the 5-year segment (sampling vs real change unresolvable).

---

## Interpretation (against the prior — extra skepticism, per task)

The robust cell is **same-year (lag 0) early-season cumulative warmth → annual incidence, ρ ≈ +0.32, 2017–2021**. Same-year is biologically coherent (nymphs quest spring–summer of year *t*; warmer early seasons → more questing activity → more bites reported in *t*) and is correctly signed. **But it should not be over-read:**

1. **It runs against the published prior** that temperature predicts Lyme *timing* more than annual *magnitude*, and that precipitation/host/habitat dominate interannual incidence. Per the task, a strong result against the prior gets *more* skepticism, not less.
2. **The signal lives only in the smooth cumulative-GDD integral, not the literal "sustained runs" form** (which is cell-dependent). That means what's detected is closer to "generally warmer early season" than a specific run mechanism — hard to separate from generic early-season temperature and its unmeasured correlates (host/habitat/landscape, latitude/season length across the region).
3. **Confounders are unmeasured** (mouse/deer abundance, habitat, moisture) and could drive a same-year temperature–incidence correlation non-causally.
4. **n=2 post-break segment is indeterminate**; the panel is internally but **not externally** validated against NOAA records.

Net: across two signal checks, this is the **first weather feature with a robust, correctly-signed, grid- and LOO-stable within-county association** — a real, modest (ρ≈0.32) same-year signal — but the prior, the run/GDD divergence, and the unmeasured confounders mean it is **suggestive, not established**. Whether it warrants inclusion in a blended estimate remains the downstream modeling decision, now informed by two checks.

## Housekeeping
24 results registered (proposed Result artifacts; 40 total with the first check); `seldon verify` run (clean); `seldon cc complete` run on this task file. `ee145bc3` still `proposed` in graph (separate reconciliation). Out of scope and not done: blend/weighting/forecaster, best-cell selection, 72.9% arm, 2024 incidence, `public/`/bundles, humidity/soil features.
