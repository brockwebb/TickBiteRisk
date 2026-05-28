# TickBiteRisk Roadmap

## Current v0 baseline

TickBiteRisk now ships a Maryland static dashboard and local CLI runtime built
from derived, public-safe artifacts. The current product is a county-week
seasonal Lyme baseline plus a single-bite Lyme decision-support overlay, not a
live clinical decision system.

The implemented flow is:

1. Normalize acquired CDC, Maryland, NOAA, Census, deer, habitat, tick
   surveillance, and seasonality inputs into reproducible ETL outputs.
2. Build a county-year feature matrix for Maryland.
3. Run model comparison across transparent baseline and ridge-style branches.
4. Select the current model comparison branch and apportion annual predictions
   across CDC Lyme onset seasonality.
5. Export a 1-10 Maryland-relative county-week seasonal Lyme baseline to
   `public/data`.
6. Combine the county-week baseline with tick identity, life stage, attachment,
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
| v0.1 | Public static baseline | Maryland dashboard, county-week risk JSON, single-bite Lyme decision-support overlay, CLI lookup/export, source metadata, plain-language caveats | Static site can be hosted from the repo and every public score carries provenance |
| v0.2 | Dashboard polish | 508-focused color/contrast pass, keyboard map interaction, browser smoke tests, improved source panel | County click and table lookup work on desktop and mobile without overlap |
| v0.3 | Validation report | Backtest writeup, model comparison summary, residual review by county/year, known intervention/data drift caveats | Public docs can explain when the score works, when it misses, and why |
| v0.4 | Ecological feature depth | Stronger NLCD/land-cover summaries, deer harvest normalization, acorn/mast notes where usable, optional park/activity proxy manifest | Each feature has source, grain, date span, license note, and missingness flags |
| v0.5 | Refresh automation | One-command data rebuild recipe, artifact checksums, CI validation of derived public JSON | A clean machine can reproduce public artifacts from acquired source files |
| v1.0 | Evidence-backed release | Stable Maryland public product with documented validation, source catalog, accessibility review, and conservative risk language | Release notes identify model version, data vintage, and non-medical boundary |
| v1.1 | Mid-Atlantic expansion | Extend the modeling and public data audit beyond Maryland into West Virginia, Virginia, Pennsylvania, Delaware, and the District of Columbia (Washington, DC) where county or county-equivalent data are available | Regional model comparison shows whether broader geography helps or challenges the Maryland-first model, and docs label every state/source coverage gap |
| v1.2 | Temporal exploration UI | Replace or augment the single date dropdown with a temporal slider for week/year exploration, year-over-year comparison, and inspection of apparent migratory or range-shift patterns | Users can scan changes over time without confusing surveillance/reporting shifts with proven tick migration or personal risk |

## Future research lanes

These are not current product promises. They are candidate branches to test
against the same data and validation harness:

- Bayesian hierarchical incidence model with explicit uncertainty intervals.
- Random forest or gradient boosted model for feature interaction discovery.
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

Last updated: 2026-05-28.
