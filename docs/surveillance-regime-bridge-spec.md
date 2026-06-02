# Reporting-Basis Adjustment — Specification

Status: draft (keystone, pre-implementation)
Supersedes: the earlier "surveillance-regime bridge / deflator" draft at this
same path. Filename retained for stable references; title and scope changed.

What changed from the prior draft (so the reasoning trail is not lost):

- **Scope is regional-first.** Maryland was the proof-of-concept; the region
  (DE/DC/MD/PA/VA/WV, 283 county-equivalents) is the actual object. MD is one
  consumer of a regional artifact, not a special case.
- **Name is "reporting-basis adjustment," never "deflator" or "bridge."** A
  deflator implies recovering a true latent quantity; we are not. We never
  rewrite the historical record. Raw counts are always preserved and displayed.
  Adjusted views are a clearly-labeled derived lens shown as
  "Estimate adjusted to 2022 CDC reporting guidelines based on …".
- **The 2022 change was national in date but split in effect.** It is NOT a
  uniform nationwide multiplier. CSTE/CDC changed the definition for all
  jurisdictions effective 2022-01-01, but high-incidence jurisdictions report on
  laboratory evidence alone (reported cases rose ~72.9% vs 2017–2019) while
  low-incidence jurisdictions still require clinical information (rose ~10.0%).
  This split is the identification lever, not a nuisance.
- **Difference-in-differences is primary and self-identifying.** Treatment
  assignment is CDC's own rule (a jurisdiction reporting >=10 confirmed cases
  per 100k for 3 years), computable from the pre-window panel. The region
  straddles the treatment/control line internally, so controls live inside the
  panel.
- **Continuous county surface, no state-line discontinuity.** Treatment is
  assigned at the state reporting level (the state health dept is what changed
  practice), but the adjustment factor is estimated on the county adjacency
  surface and smoothed across it, so no artificial step appears at state borders.
- **PA 2024 real data is an uncertainty-calibration anchor, not a correction
  multiplier.** PA DOH has real 2024 county data. It calibrates step-1 forward
  forecast error; it must never be applied as a point-correction to other
  jurisdictions.
- **Nothing is hard-coded.** The clean pre-window (default 2017–2019, COVID
  years excluded) is a declared, documented, overridable parameter with its
  rationale carried in row-level provenance — matching the existing
  source_vintage / data_cutoff_date convention.
- **Present-year within-season weather is tracked as a FUTURE lane, not assumed
  built.** The current public weekly score has no live-weather term; this spec
  records that honestly rather than implying it exists.

Author hand-off: written to be handed to Claude Code for implementation.

---

## 1. Problem statement (why this is a precondition, not an enhancement)

CDC/CSTE revised the national Lyme surveillance case definition effective
2022-01-01. The policy was national; the effect on the reported series was
jurisdiction-dependent:

- High-incidence jurisdictions may report on laboratory evidence alone, without
  collecting clinical information. Reported cases there rose ~72.9% vs the
  2017–2019 average.
- Low-incidence jurisdictions still require supporting clinical information
  (with updated probable-case criteria). Reported cases there rose ~10.0%.
- Nationally, 2022 reported counts were ~1.7x the 2017–2019 average, and CDC
  states the increase reflects surveillance method change rather than disease
  risk, and "precludes detailed comparison with historical data."

Source: CDC MMWR 73(6), 2024-02-15,
https://www.cdc.gov/mmwr/volumes/73/wr/mm7306a1.htm

Consequence for modeling: a level shift of ~73% in high-incidence jurisdictions,
with no change in underlying disease, swamps the few-percent variance that
ecology/weather features could plausibly explain in true incidence. Therefore:

- Any model fit across an uncorrected 2022 boundary using raw counts is partly
  fitting the instrument change.
- Persistence baselines (`prior_year_incidence`) win the current backtest partly
  because last-year≈this-year absorbs the regime *level* in every year except
  the break. That is an artifact of regime-blind evaluation on raw counts, not
  evidence that ecology is uninformative.
- The feature-evaluation program (does weather/ecology/RF/Bayes help?) is not
  runnable on raw counts. It must run on basis-adjusted targets.

The adjustment is therefore step 1. Re-running model comparison on raw vs.
adjusted targets side-by-side (step 5/6) is the experiment that confirms or
refutes the "persistence-wins-is-an-artifact" hypothesis.

## 1a. Why this product exists at all (forecasting as a response to data lag)

Official surveillance lags ~2 years (2022 data published 2024-02; nothing newer
than 2023 publicly available as of this writing). Households, clinicians, parks,
and public-health teams need in-season risk context now. This product forecasts
the interim with explicit, growing uncertainty. The honest pitch: official data
lag ~2 years; this is a transparent forecast of the gap, with uncertainty that
grows the further we project past the last real data. It is not a claim of
precision and not a substitute for confirmed surveillance.

---

## 2. Scope and non-goals

In scope:

1. A new ETL artifact: `reporting_basis_adjustment.csv` (factors + uncertainty +
   provenance), regional.
2. A high-incidence treatment-assignment artifact derived from the panel itself.
3. Parallel basis-adjusted target columns joined into the design matrix (raw
   columns preserved untouched).
4. A hard cross-regime training guard in `model_compare.run_model_comparison`.
5. A PA-2024 step-1 forecast-skill anchor used for uncertainty calibration only.
6. Uncertainty propagation from factor CI -> adjusted target -> annual forecast
   -> public 1–10 score and single-bite score, with band shape reflecting where
   ground truth exists.

Explicit non-goals:

- Does NOT estimate latent true Lyme burden. It re-expresses reported counts on
  a common reporting basis.
- Does NOT rewrite historical data. Raw counts are preserved and displayable;
  adjusted values are a labeled derived view.
- Does NOT change the selected public branch on its own. Promotion stays a
  separate human decision after step-6 evidence.
- Does NOT apply one jurisdiction's observed residual as a point correction to
  another jurisdiction.
- Does NOT retro-fix the single-bite transmission constants (separate work).

---

## 3. The continuous-surface principle (governs everything below)

Ticks do not read state lines. Counties with similar ecology trend together
regardless of jurisdiction. State aggregation is a *display* constraint, not a
modeling unit. The repo already commits to this: the regional adjacency graph
with cross-state edges and the spatial-regime lanes treat counties as cells of a
continuous regional surface.

Two things must stay distinct and are easy to conflate:

- **Treatment assignment = state reporting policy.** Whether a county's reported
  series jumped in 2022 depends on whether *its state health department* adopted
  lab-only reporting, which depends on CDC's high-incidence classification of
  that jurisdiction. This is a state-level property the county inherits.
- **Factor estimation surface = continuous county field.** The adjustment factor
  is estimated and smoothed across the county adjacency graph so that similar
  neighboring counties (including cross-state neighbors) receive similar factors.
  No artificial discontinuity may appear at a state border in the adjusted view.

A naive per-state factor would re-impose the state lines we are dissolving and is
prohibited.

---

## 4. Identification strategy (CDC anchor final)

The current regional incidence panel classifies all six regional jurisdictions
(DE/DC/MD/PA/VA/WV) as high-incidence in the declared 2017-2019 pre-window. That
falsifies the old in-region low-incidence DiD path. The out-of-region
low-incidence DiD path was then checked against CDC dataset `qtbi-xd4i`
(2008-2021 annual county-FIPS Lyme public-use data with confirmed/probable
split) and is empirically foreclosed: across the full 2017-2019 pre-window the
candidate states do not provide a usable unsuppressed annual county panel.

The out-of-region control panel is a walled-off, NON-FORECAST identification
instrument. It is written separately as `did_control_panel.csv`; the forecast
design matrix MUST fail if any control-panel county FIPS appears in forecast
rows. A Georgia/Oklahoma/etc. county must never become a pseudo-neighbor or
ecological training row for the regional surface.

Recorded decision, 2026-05-31:

- `cdc_published_anchor` is the earned identification method for the 2022
  reporting-basis adjustment.
- `did_control_evaluated=true`.
- `did_control_passed=false`.
- `did_control_failure_reason=insufficient_unsuppressed_county_panel_2017_2019`.
- Evidence is retained in
  `docs/research/lab-notes/08-reporting-basis-identification.md` and
  `docs/research/source-materials/did-control-verification-2017-2019.csv`.
- ITS remains diagnostic-only and does not produce adjustment rows.

The CDC anchor is a national fixed-prior scalar, not a jurisdiction-specific DiD
estimate. It unblocks step 6 under the gate, but if step-6 ranking is sensitive
to the adjustment magnitude, that sensitivity is the weakest joint in the chain
and must be discussed plainly.

Method validation: the 2008 and 2017 CDC reporting boundaries are historical
checkpoints for the selected adjustment method. They are NOT 2022 controls
because they are the same treated series at different times, stacked with real
range expansion and multiple regime changes. Before trusting the 2022 adjustment,
record whether the method recovers the known direction and rough documented
magnitude for 2008 and 2017 (`method_validation_2008_status`,
`method_validation_2017_status`, observed ratios, pass/fail).

---

## 5. Treatment-assignment artifact: `high_incidence_classification.csv`

Reproduce CDC's classification from the panel rather than hand-listing states.

Rule: a jurisdiction is high-incidence if it reported >=10 confirmed cases per
100k population for 3 years (CDC's stated threshold). Compute per jurisdiction
from the regional incidence panel using only years inside the declared
pre-window (§6) so the assignment is itself pre-2022 and not contaminated by the
break it is used to estimate.

Columns: `jurisdiction_fips` (state), `classification`
(`high_incidence`/`low_incidence`), `qualifying_years`, `threshold_per_100k`
(default 10.0, parameter), `consecutive_years_required` (default 3, parameter),
`pre_window`, `source_panel_sha256`, `source_citation_url`, `notes`.

Caveat to encode: the high/low split is CDC's *jurisdiction* (state)
classification, but we model counties. A low-incidence state may contain a
high-incidence county. Treatment is assigned at the state reporting level because
the state is what changed reporting practice; the continuous factor surface
(§3, §7) handles spatial variation within and across states.

---

## 6. Declared pre-window parameter (nothing hard-coded)

`reporting_basis_pre_window` — declared parameter, surfaced at CLI and function
signature, default `2017-2019`, overridable.

Documented rationale (carried in spec AND as a row-level provenance field on
every adjustment output): this window matches CDC's own MMWR comparison baseline
and deliberately excludes the COVID-disrupted 2020–2021 years to avoid stacking
two surveillance regimes in the baseline. It is a defensible declared choice, not
a silent literal; changing the parameter updates provenance rather than editing
estimation code.

---

## 7. Adjustment artifact schemas

### 7.1. Non-forecast control instrument: `did_control_panel.csv`

When out-of-region DiD candidates are evaluated, write a separate control-panel
artifact. This artifact is provenance for identification only and is structurally
excluded from all forecast features, adjacency, ecology, model fitting, and
public forecast surfaces.

| column | type | notes |
| --- | --- | --- |
| `candidate_state_fips` | str | out-of-region candidate state |
| `candidate_state_name` | str | source label when available |
| `county_fips` | str | candidate county; used by the contamination guard |
| `county_name` | str | source label when available |
| `instrument_role` | str | `non_forecast_identification_instrument` |
| `forecast_exclusion` | str | `must_not_enter_forecast_design_matrix` |
| `candidate_pre_window` | str | default `2017-2019` |
| `candidate_low_incidence_status` | str | CDC-style classification from the candidate panel |
| `parallel_trends_status` | str | `passed`/`violated`/`not_applicable` |
| `parallel_trends_*` | float | treatment slope, control slope, absolute difference |
| `inclusion_decision` | str | `included` only if low-incidence and parallel-trends passed |
| `failure_reason` | str | e.g. `did_parallel_trends_violated` |
| `source_panel_sha256` | str | candidate panel provenance |
| `source_vintage` | str | matches repo convention |
| `assumption_flags` | str | comma-joined |
| `notes` | str | free text |

Guard: `build_model_design_matrix` must read sibling `did_control_panel.csv`
when a reporting-basis adjustment is supplied and fail if any listed
`county_fips` appears in the forecast design matrix.

### 7.2. Public adjustment factors: `reporting_basis_adjustment.csv`

Default reference basis: `case_definition_change_2022_plus` (express comparisons
on the 2022 basis, since the forward forecast targets 2024–2026, which are
already on that basis). Raw history is never modified; this is the basis used for
the labeled adjusted view and for cross-regime model training on adjusted
targets.

| column | type | notes |
| --- | --- | --- |
| `adjustment_id` | str | deterministic slug of scope+boundary+method |
| `jurisdiction_scope` | str | `county_XXXXX` primary; `state_XX` / `national` only for anchors |
| `boundary_year` | int | the case-definition change year spanned |
| `source_regime` | str | from shared classifier (§9) |
| `target_reference_basis` | str | default `case_definition_change_2022_plus` |
| `adjustment_method` | str | enum from §4 |
| `multiplicative_factor` | float | reported(source)->reference scale; reference rows = 1.0 |
| `factor_se_log` | float | SE on the log scale |
| `factor_ci80_low/high` | float | 80% CI (exp of log-scale bounds) |
| `factor_ci95_low/high` | float | 95% CI |
| `treatment_status` | str | `high_incidence`/`low_incidence` from §5 |
| `n_control_jurisdictions` | int | DiD only |
| `n_observations_used` | int | rows feeding the estimate |
| `identification_quality` | str | `strong`/`moderate`/`weak_identification` |
| `smoothed_on_adjacency` | bool | true when borrowed strength across neighbors |
| `displayed_as` | str | label string, e.g. "Estimate adjusted to 2022 CDC reporting guidelines based on difference-in-differences vs out-of-region low-incidence controls" |
| `pre_window` | str | from §6 |
| `source_citation_url` | str | CDC MMWR / CSTE URL |
| `source_panel_sha256` | str | provenance |
| `source_vintage` | str | matches repo convention |
| `assumption_flags` | str | comma-joined |
| `notes` | str | free text |

Rules:
- Reference-basis rows have factor 1.0 and zero-width CI.
- CI computed on the log scale then exponentiated (positive, asymmetric — correct
  for a ratio).
- Factor surface smoothed across the county adjacency graph (§3); record
  `smoothed_on_adjacency`.
- Acquisition provenance + source sha written alongside, per existing ETL
  pattern.
- Every row records the `adjustment_method` that actually produced it and its
  `identification_quality`, so downstream consumers can distinguish
  out-of-region DiD from the CDC fixed-prior fallback.

### 7.3. Run manifest: `reporting_basis_adjustment_runs.csv`

The run manifest records the closed DiD decision explicitly:

- `identification_method=cdc_published_anchor`
- `did_control_evaluated=true`
- `did_control_passed=false`
- `did_control_failure_reason=insufficient_unsuppressed_county_panel_2017_2019`
- `did_control_decision_reference` contains
  `docs/research/lab-notes/08-reporting-basis-identification.md` and
  `docs/research/source-materials/did-control-verification-2017-2019.csv`

This is the provenance that distinguishes an anchor-identified adjustment from a
silent skipped-control implementation.

---

## 8. Adjusted targets in the design matrix (raw preserved)

`model_compare` requires (`REQUIRED_MODEL_COMPARISON_COLUMNS`): `county_fips,
year, target_total_cases, target_population, target_lyme_incidence_per_100k`.

Add PARALLEL adjusted columns; never overwrite raw:

| new column | definition |
| --- | --- |
| `source_regime` | from §9 classifier |
| `basis_factor_applied` | factor joined from §7 |
| `basis_factor_ci95_low/high` | joined CI bounds |
| `target_total_cases_basis_adjusted` | raw cases × factor |
| `target_lyme_incidence_per_100k_basis_adjusted` | raw incidence × factor |
| `target_is_reference_basis` | bool; factor == 1.0 |
| `missing_basis_factor` | bool; when no factor found (adjusted == raw; guard treats row as raw) |
| `displayed_as` | label string carried for display |

Keeping both sets side by side enables step-6 (raw vs adjusted) without a second
pipeline.

---

## 9. Regime classification: single source of truth

Exactly one classifier. It exists as `_classify_surveillance_regime(quality_flags,
test_year)` in `model_diagnostics.py`, returning `mdh_probable_only_2024`,
`covid_reporting_disruption`, `case_definition_change_2022_plus`,
`pre_2020_baseline`, `other_surveillance_regime`; reporting-break set is
`REPORTING_BREAK_REGIMES`.

Requirement: promote the classifier and boundary constants into a shared module
(`tickbiterisk/modeling/regimes.py`); have `model_diagnostics.py` and the new
adjustment ETL import it. Do not fork a second copy. The adjustment artifact's
`source_regime` values must be drawn from this enum so the §8 join is total.

(Note: a `regimes.py` shared module may already be in progress on the working
branch from earlier old-spec work. Reuse/extend it; do not create a second.)

---

## 10. Hard cross-regime training guard (keystone mechanism)

Leakage is already structurally impossible (`feature_*` whitelist +
`EXCLUDED_FEATURE_PREFIXES`). Regime-blind fitting is only discouraged downstream.
Close the asymmetry.

In `run_model_comparison`, the rolling-origin loop builds
`train_rows = [row for row in rows if row.year < test_year]`. Add a guard:

1. Determine the regime of `test_year` and the regimes present in `train_rows`
   via the shared classifier.
2. If training on RAW targets AND `train_rows` span more than one regime (or a
   different regime than `test_year`): refuse by default, raise
   `CrossRegimeTrainingError` naming the offending regimes and the override.
3. Bypass only via explicit `--allow-cross-regime-raw-targets` /
   `allow_cross_regime_raw_targets=True`. When bypassed, every emitted row carries
   assumption flag `cross_regime_raw_training_allowed` (never silent).
4. When training on basis-adjusted targets (`target_*_basis_adjusted`),
   cross-regime training is permitted without override (common scale), but rows
   carry `regime_basis_adjusted_targets`; any county-year with
   `missing_basis_factor == True` is treated as raw for guard purposes so a
   missing factor cannot quietly re-open the leak.

Run-level `target_scale ∈ {raw, basis_adjusted}` selects the column set; default
`raw` to preserve current behavior until step-6 evidence justifies a switch.

Intent: make the stupid thing impossible by accident. No model — human or agent —
can fit across 2022 on raw counts without typing the override and leaving a flag
in the output. Structural analogue of the leakage whitelist.

---

## 11. PA 2024 step-1 forecast-skill anchor: `step1_forecast_skill_anchor.csv`

PA DOH has real 2024 county data (the `pennsylvania_doh_official_lyme_by_report_2024`
overlay). 2023 and 2024 are both on the 2022 basis, so this is a clean forward
check with no reporting-regime confound — the one place with a real answer key
for a forward step.

Procedure: forecast 2024 from a 2023 origin for all counties; join PA observed
2024 where available; compute residuals as a PA-only validation panel.

USE — uncertainty calibration only:
- Characterize step-1 forward forecast error magnitude and direction for
  similar (high-incidence) counties on the 2022 basis.
- Feed that into 2024 interval width/centering for other counties, weighted by
  ecological similarity on the adjacency surface with continuous spatial decay
  (NOT a state-boundary stop).

PROHIBITED — and enforced structurally:
- The PA residual MUST NOT be applied as a multiplicative point-correction to any
  other jurisdiction's 2024 point forecast. That repeats the cross-regime
  correction error that already worsened MAE. Add a guard in the §10 family:
  observed-truth residuals from one jurisdiction may adjust *intervals* for
  similar counties (similarity-weighted, continuously decaying) but may never
  multiply another jurisdiction's point estimate.

Caveat to encode: the PA "by report 2024" workbook is a state-source overlay with
provisional caveats and is not reconciled to an eventual CDC count. Treat the PA
residual as a real-but-noisy measurement with its own uncertainty; do not present
it as a perfect answer key.

MA 2025 investigation gate: investigate whether Massachusetts has published
official 2025 county-level Lyme data. Do not assume it exists. If official,
county-level 2025 data are verified, add MA as a second forward answer key for
the 2024->2025 step and record its source/vintage. MA is high-incidence, so it
calibrates forward forecast skill and interval shape only; it is NOT a DiD
control. The same structural rule applies: observed residuals may adjust
intervals for ecologically similar counties with continuous decay, never multiply
another jurisdiction's point forecast.

---

## 12. Uncertainty propagation (CI/MOE on everything user-facing)

Every public-facing number ships with a plausible range. The adjustment forces
this: the factor has a CI that must flow through to the displayed score.

1. **Adjusted target uncertainty.** On the log scale,
   `var(log adjusted) = var(log raw_estimate) + var(log factor)`; factor
   uncertainty adds in quadrature with model predictive uncertainty rather than
   replacing it. Note: the forward forecast (2024–2026) is already on the 2022
   basis, so factor uncertainty mostly enters where pre-2022 years are used as
   training signal, not in the displayed forward number.
2. **Annual forecast interval.** Existing machinery
   (`regional_annual_forecast_intervals`, rolling-origin residual bands;
   Maryland analog-bootstrap intervals) produces empirical bands. When
   `target_scale == basis_adjusted`, combine residual predictive variance with
   factor variance in quadrature on the log scale. Record components separately
   (`predictive_var_component`, `basis_var_component`) so the band is
   decomposable and auditable.
3. **Public 1–10 score.** The 1–10 scale is an intentional abstraction — "good
   enough, better than nothing if the data support it" — not a precision claim.
   That stance is only honest if the band travels with it. Extend the score
   transform (annual incidence × CDC weekly seasonality share -> 1–10 via
   benchmark, in `risk_score.py`) to map the lower/upper interval bounds through
   the same transform, emitting `score_low` / `score_high` beside `score`. A bare
   1–10 point implies precision the product disclaims and is not acceptable on
   public surfaces. Public wording: "plausible range for the relative
   reported-Lyme pressure score," never "confidence interval for infection risk."
4. **Single-bite score.** The location/season modifier reads
   `baseline.risk_score`; once the baseline carries a band, the single-bite
   output exposes a banded score. Keep `single_bite_risk_score_raw` for one
   release only as a DEPRECATED alias of `single_bite_risk_score`, with a
   removal-next-version note in `api/api-spec.md`; the banded fields are primary.

Band SHAPE reflects where ground truth exists (the data-lag honesty rule):
- 2024 is PARTIALLY ANCHORED by the PA step-1 check (§11) — its band should be
  tighter than a pure-extrapolation 2024 would be, because there is one real
  check.
- 2025 and 2026 are UNANCHORED multi-step extrapolation — bands widen sharply
  and monotonically per step, and widen further for sparse-history counties and
  missing-feature years.
- If the band does not grow across the 2024->2025->2026 steps, the product is
  understating what the CDC data gap costs. Growth is the honest signal of that
  cost.

---

## 13. Present-year within-season weather lane (FUTURE — not yet built)

Honest status: the current public weekly score has NO live-weather term. It is
`annual forecast × CDC national onset-seasonality share`. A warm in-season week
does not currently move the score. Weather exists only as a retrospective annual
feature in the comparison harness (`ridge_lag_weather_ecology`), which ranks near
the bottom.

If present-year weather should modulate weekly risk (ecologically defensible — a
warm, humid stretch can lift nymphal questing activity), that is a NEW forecast
lane, not a tweak: a within-season weather-activity multiplier applied on top of
the annual×seasonality base, with its own validation gate against whatever
within-season signal can be obtained. It must not be smuggled into the public
path without that gate. Tracked here so the capability is honestly marked
not-yet-built rather than assumed.

---

## 14. Build order (the controlled experiment)

1. Promote regime classifier + boundaries into shared `regimes.py` (§9); reuse
   any in-progress module on the working branch rather than forking.
2. Build `high_incidence_classification.csv` from the panel (§5) using the
   declared pre-window (§6).
3. Build `did_control_panel.csv` and `reporting_basis_adjustment.csv` —
   CDC fixed-prior anchor identified, out-of-region DiD recorded as evaluated
   and foreclosed, ITS diagnostic-only, 2008/2017 method validation recorded,
   adjacency-smoothed factor surface, CI + provenance + `displayed_as` (§4,§7).
4. Join parallel adjusted targets into the design matrix (§8).
5. Add the hard cross-regime guard + `target_scale` switch + override flag (§10).
5a. Gate before step 6: the reporting-basis adjustment artifact is produced by
   `cdc_published_anchor`, which passes the gate and unblocks step 6. If ITS is
   the only available driver, stop: adjustment remains diagnostic-only and step 6
   stays blocked.
6. Re-run `model_compare` twice — `target_scale=raw` (guarded/override) and
   `target_scale=basis_adjusted` — write both into the validation record side by
   side. THIS is the deliverable that tests the hypothesis.
7. Build `step1_forecast_skill_anchor.csv` (PA 2024, and MA 2025 only if
   officially verified county-level data exist) as interval-calibration input
   with the no-cross-correction guard (§11).
8. Add interval propagation + band-shape rules through annual forecast -> public
   score (§12).
9. Only then revisit weather/ecology/RF/Bayesian promotion claims on the
   adjusted scale; consider the §13 weather lane.

Interpreting step 6:
- If ecology/weather/RF beat persistence on ADJUSTED targets but not raw, that
  confirms persistence's raw-target win was a regime-blind artifact.
- If they still lose on adjusted targets, that is a real, publishable finding: at
  county-year grain the regional Lyme series is close to a persistence process
  and the ecological signal is not recoverable at that resolution. Either outcome
  advances the science; neither is a failure of the experiment.

Governing principle (the user's, and correct): do good-enough modeling, do not
overfit. Reality is too complex to capture fully. With almost no forward answer
keys (one state, one year), any model flexible enough to fit them well is fitting
noise. Prefer rigid, transparent models whose errors are explainable from source
limitations — which is exactly the validation question `model-spec.md` already
poses.

---

## 15. Testing requirements

- Classifier parity: `regimes.py` returns identical results to the prior in-place
  classifier over a fixed (flags, year) battery.
- High-incidence classification reproduces expected in-region split from the
  panel; threshold + consecutive-years are parameters, not literals.
- Out-of-region DiD closure is recorded in run metadata:
  `did_control_evaluated=true`, `did_control_passed=false`,
  `did_control_failure_reason=insufficient_unsuppressed_county_panel_2017_2019`,
  with references to the retained lab note and source-material CSV.
- Guard: a `did_control_panel.csv` county FIPS appearing in the forecast design
  matrix raises before model features are built.
- Method validation: 2008 and 2017 checkpoint statuses and observed ratios are
  written to run provenance.
- Reference-basis rows: factor 1.0, zero-width CI; adjusted == raw when
  `missing_basis_factor`.
- Adjacency smoothing: no discontinuity at a state border for two similar
  neighboring counties across a state line (bounded factor difference).
- Guard: raw-target run crossing 2022 RAISES `CrossRegimeTrainingError`; same run
  with override succeeds and every row carries `cross_regime_raw_training_allowed`.
- Guard: basis-adjusted run crossing 2022 succeeds without override, carries
  `regime_basis_adjusted_targets`; a basis-adjusted run containing a
  `missing_basis_factor` row crossing a boundary still RAISES without override.
- PA anchor: residuals computed only where PA observed 2024 exists; a test
  asserts the anchor cannot produce a point-correction to a non-PA forecast
  (only interval changes), enforced structurally.
- MA 2025: official-source investigation records whether county-level 2025 data
  exist before adding MA as a second forward answer key.
- Propagation: `score_low <= score <= score_high` for every public row; band
  widens under `basis_adjusted` vs a zero-variance-factor control; band grows
  monotonically 2024->2025->2026 and is tighter at 2024 when the PA anchor is
  present vs absent.
- Provenance: adjustment + classification artifacts write acquisition provenance
  + source sha consistent with existing ETL.

Note for the implementing agent: the repo has ignored `tests/* 2.py`
Finder-conflict duplicates that pytest still collects, with a known failing
subset. Resolve them (delete or add a collection ignore) before trusting the
local test signal for this work.

---

## 16. One-line summary for README/changelog

> Added a regional reporting-basis adjustment that re-expresses reported Lyme
> counts on the 2022 CDC reporting definition (difference-in-differences vs
> out-of-region low-incidence controls when they pass parallel trends, otherwise
> the CDC fixed-prior anchor, estimated on a continuous county surface),
> a hard guard refusing cross-regime training on raw targets without explicit
> override, a PA-2024 step-1 skill anchor used only to calibrate forecast
> uncertainty, and interval propagation so public 1–10 scores ship with a
> plausible range that grows the further the forecast projects past the last
> real data.

Last updated: 2026-05-31.
