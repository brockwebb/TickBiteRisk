# TickBiteRisk Roadmap

## Current v0 forecast

TickBiteRisk now ships a Maryland static dashboard and local CLI runtime built
from derived, public-safe artifacts. The current product is a county-week
seasonal Lyme forecast plus a single-bite Lyme decision-support overlay, not a
live clinical decision system.

The implemented flow is:

1. Normalize acquired CDC, Maryland, NOAA, Census, deer, habitat, tick
   surveillance, and seasonality inputs into reproducible ETL outputs.
2. Build a county-year feature matrix for Maryland.
3. Run model comparison across transparent baseline, ridge-style, analog, and
   random-forest research branches.
4. Select the current model comparison branch and apportion annual predictions
   across CDC Lyme onset seasonality.
5. Export a 1-10 Maryland-relative county-week seasonal Lyme forecast to
   `public/data`.
6. Combine the county-week forecast with tick identity, life stage, attachment,
   engorgement, removal timing, and CDC criteria for a transparent single-bite
   Lyme decision-support overlay.
7. Serve the static dashboard through GitHub Pages without runtime secrets or
   raw data redistribution.

The current v0 branch favors inspectability over cleverness. It is designed to
make the data lineage, assumptions, and limits legible before adding more model
complexity.

## Roadmap

| Version | Theme | Scope | Exit check |
| --- | --- | --- | --- |
| v0.1 | Public static forecast | Maryland dashboard, county-week risk JSON, single-bite Lyme decision-support overlay, CLI lookup/export, source metadata, plain-language caveats | Static site can be hosted from the repo and every public score carries provenance |
| v0.2 | Dashboard polish | 508-focused color/contrast pass, keyboard map interaction, browser smoke tests, improved source panel | County click and table lookup work on desktop and mobile without overlap |
| v0.3 | Validation report | Backtest writeup, model comparison summary, residual review by county/year, known intervention/data drift caveats, and explicit promotion gates for RF/Bayesian/analog branches | Public docs can explain when the score works, when it misses, and why |
| v0.4 | Ecological feature depth | Stronger NLCD/land-cover summaries, deer harvest normalization, acorn/mast notes where usable, optional park/activity proxy manifest | Each feature has source, grain, date span, license note, and missingness flags |
| v0.5 | Refresh automation | One-command data rebuild recipe, artifact checksums, CI validation of derived public JSON | A clean machine can reproduce public artifacts from acquired source files |
| v1.0 | Evidence-backed release | Stable Maryland public product with documented validation, source catalog, accessibility review, and conservative risk language | Release notes identify model version, data vintage, and non-medical boundary |
| v1.1 | Mid-Atlantic expansion | Extend the modeling and public data audit beyond Maryland into West Virginia, Virginia, Pennsylvania, Delaware, and the District of Columbia (Washington, DC) where county or county-equivalent data are available | Regional model comparison shows whether broader geography helps or challenges the Maryland-first model, and docs label every state/source coverage gap |
| v1.2 | Temporal exploration UI | Replace or augment the single date dropdown with a temporal slider for week/year exploration, year-over-year comparison, and inspection of apparent migratory or range-shift patterns | Users can scan changes over time without confusing surveillance/reporting shifts with proven tick migration or personal risk |

## Autonomous research queue before HITL

The current research branch can keep moving on implementation slices that make
existing evidence easier to inspect without changing the public Maryland
default. Safe autonomous work includes local forecast-region overlays,
local-region chart scope controls, forecast explanation panels, static asset
cache hardening, and documentation that keeps the research/public boundary
visible.

The next autonomous evidence tasks are:

- spatial-regime evidence pack: summarize localized regime membership,
  forecast-safe inputs, interval behavior, and backtest/fit caveats without
  promoting a new public model branch.
- forecast update evidence pack: summarize forecast calibration and
  Gamma-Poisson update backtests, including cases where update gates worsen
  MAE and therefore remain `do_not_apply_to_public_forecast`.
- Dashboard QA polish: tune chart and control layout where browser smoke tests
  or preview review show objective overlap, cramped controls, stale labels, or
  broken interactions.
- Provenance/status cleanup: keep docs, manifests, and public-safe artifact
  descriptions aligned with the current committed outputs.

## HITL gates

Stop for a human decision before any change that alters public defaults,
policy-sensitive wording, or workspace ownership. Current gates:

- public branch promotion
- risk color scale or top-coding
- medical or CDC guidance wording
- default map or chart scope
- committing, deleting, or normalizing deliberate untracked local files

## Future research lanes

These are not current product promises. They are candidate branches to test
against the same data and validation harness:

- Bayesian hierarchical incidence model with explicit uncertainty intervals and
  update rules that improve, rather than worsen, rolling-origin backtests.
- Random forest or gradient boosted model for feature interaction discovery;
  current RF lanes are research diagnostics only because they have not beaten
  the leading transparent baselines.
- Linear or ridge ensemble combining transparent branches when it improves
  held-out calibration.
- Calibrated per-bite probability research model that validates absolute risk
  against suitable evidence before any probability language appears in public
  output.
- Regional Mid-Atlantic model stress test across Maryland, West Virginia,
  Virginia, Pennsylvania, Delaware, and Washington, DC, using the same
  time-aware validation harness before changing public defaults.
- Temporal visualization for year-over-year movement and seasonal change,
  potentially with a slider, animation, or small multiples rather than only a
  date dropdown.
- Database-backed HTTP service if there is a clear need beyond static files.

## Product principles

- No raw acquired data in the public web product unless the source license and
  privacy boundary clearly permit redistribution.
- Every public score should carry source metadata, model version, and caveats.
- The dashboard must stay plain-language: informational and educational only,
  follow CDC guidance, and consult a healthcare professional for personal
  medical decisions.
- Model performance comes before model ambition. A simple branch that validates
  well beats a complex branch that cannot be explained or backtested.

Last updated: 2026-05-30.
