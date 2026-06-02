# Weather-as-Magnitude-Covariate Identification Decision

Status: draft
Primary sources: `cc_tasks/2026-06-01_within-segment-weather-signal-check_RESULTS.md`; `cc_tasks/2026-06-01_early-season-warmth-signal-check_RESULTS.md`; Seldon Result registry (40 registered pooled-Spearman values across both checks); Eisen, Eisen, Ogden & Beard 2016, *J Med Entomol* 53(2):250–61, DOI 10.1093/jme/tjv199
Reviewer focus: the scope of the negative result — magnitude vs. timing — and the vindication of `weather_mode=not_used`
Last checked against commit: working tree 2026-06-01 (commit `3670791`)

## Decision

Temperature is **excluded as a covariate for annual Lyme incidence *magnitude*** at county resolution on definition-stable segments. It is **retained as legitimate for *timing/phenology*** if and when a seasonal-timing component is built. This is a negative identification result, not an unattempted search, and it makes the shipped `model_card` `weather_mode=not_used` (for magnitude) a **correct scoping decision, not a limitation to apologize for**.

The scope is load-bearing: this note does **not** claim "weather does not matter for Lyme." It claims that, at annual county resolution on the raw/relative rank scale within a definition-stable segment, no tested temperature feature is a usable *magnitude* covariate.

## The question

Can weather/temperature serve as a covariate for annual Lyme incidence *magnitude* — the quantity this product forecasts — within definition-stable case-definition segments, evaluated on the protocol-invariant within-county rank scale?

## What was tested

Two within-segment signal checks on the validated six-state daily weather panel (1992–2026, 283/283 counties) joined to the Option-A CDC-dashboard zero-suppression incidence panel (re-derived from source, `cdc_dashboard_total_cases`-flagged; join reported fail-loud per state-year, with VA `51515` surfaced as a missing-value county-year rather than silently dropped):

- **Check 1** — four pre-committed annual features (warm-season GDD, spring-onset day, winter hard-freeze days, warm-season precipitation).
- **Check 2** — a literature-grounded early-season warmth family (cumulative GDD through ~week 20; sustained warm-run count and days) across a pre-committed onset-threshold grid (8/10/12/14 °C) × run-length grid (5/7/10 days), spanning the review's unresolved 4–15 °C activity-onset band.

Eight features in total, each at lags 0 and 1 (same-year vs. prior-year weather), on segments **2017–2021** (5 years, stability assessable by leave-one-year-out) and **2022–2023** (post-2022-CSTE-break; n=2, direction-only, stability indeterminate). Associations are pooled within-county Spearman with bootstrap CIs; the 2022 +72.9% definition break is never fit across.

## The finding (scoped)

**No usable magnitude signal.** In Check 1 only winter hard-freeze days produced a stable, zero-excluding association — and it carried the *wrong sign* for its overwinter-mortality mechanism (positive: ρ≈+0.19 to +0.24, 2017–2021), so it reads as a confound, not a driver. GDD, spring onset, and precipitation showed no coherent within-county annual rank signal.

Check 2's grid was decisive precisely because it was a grid. The literal "sustained solid runs" operationalization was **not grid-stable** — its sign flipped cell to cell (ρ from −0.24 to +0.15 across the count grid) — i.e. it existed only at cherry-pickable cells, the signature of noise. The one robust, correctly-signed, grid-stable and leave-one-year-out-stable association was **cumulative early-season GDD, ρ≈+0.30 to +0.33 (CIs exclude zero), but only at same-year lag 0 in 2017–2021.**

That surviving association sits at the **biologically wrong lag.** The spring questing cohort whose bites drive year-*t* reported cases was set by the *prior* year's larval feeding; same-year early warmth can shift questing *timing* but cannot have grown that cohort. The mechanism predicts the prior-year lag should carry the cohort-size signal — and at lag 1 the feature is weak, negative, and sign-unstable. A **warmth-as-place-proxy** explanation is therefore more parsimonious than a tick-exposure mechanism: cumulative early-season GDD co-varies with latitude, season length, and structurally higher-incidence southern counties, and the smooth GDD integral (unlike the run features) is exactly the quantity that tracks "generally warmer place/year." The within-county rank design removes a fixed cross-county gradient only if counties re-rank year to year on the feature; on five annual points that protection may be illusory. The lag-0 GDD result is **confound-suspect, not an established signal** — recorded as a graph Issue (`unsupported_claim`) against the Check 2 task so it cannot be read later as "the first real weather signal."

## Consistency with the literature

This **reproduces** Eisen et al. 2016. That CDC-authored review of *I. scapularis* finds temperature predicts Lyme *timing/phenology* — season onset, peak, and duration, best captured by cumulative growing-degree-days through ~calendar week 20 — but **not** annual case *magnitude*; for interannual incidence, precipitation has been the stronger predictor and geographic case-count studies show no clear or consistent temperature association, with host abundance (mice, deer) and habitat dominating at sub-state scale. Those host/habitat/moisture confounders are **unmeasured in this panel** (GHCND lacks soil/humidity/saturation-deficit in-window; they were omitted, not fabricated). That our one temperature association is a *timing* feature (early-season GDD) surfacing at the magnitude target — and at the timing-not-cohort lag — is exactly what the published prior predicts. A weak/confounded magnitude result is the expected outcome; a strong one would have run against the literature and warranted more skepticism, not less.

## Scoped conclusion (the earned decision)

1. **Excluded for magnitude.** Temperature is not carried as a covariate for the annual incidence-magnitude forecast. The signal checks exhausted the pre-committed and literature-grounded feature space and found no usable, mechanism-consistent magnitude association.
2. **Retained for timing.** Temperature — specifically early-season cumulative GDD through ~week 20 — remains the literature-backed lever for a seasonal-timing/phenology component, should one be built. The exclusion is about magnitude, not about temperature per se.
3. **`weather_mode=not_used` is vindicated.** The shipped model card's `weather_mode=not_used` (for magnitude) is the correct scoping given this evidence and the published prior — a deliberate, earned decision, not an unaddressed gap.

## What this does NOT close

This note addresses only the *weather/temperature* arm. It says nothing about the **ecology arm** (acorn-mast and deer signals at the ~2-year lag that the cohort-size mechanism actually predicts) — that is scoped in a separate task and must not be foreclosed here.
