# TickBiteRisk Model Background

## Current rationale

TickBiteRisk started with the bigger idea of estimating disease risk after a
specific tick encounter. The current shipped work is narrower: a Maryland
county-week seasonal Lyme forecast derived from historical surveillance,
seasonality, and model comparison.

That narrower scope is intentional. The data support a transparent public
forecast before they support a bite-specific disease calculator.

## Why the current model is comparison-first

The current model layer is an ensemble-ready comparison harness, not a single
black-box answer. It keeps several branches side by side so we can see whether
extra features actually improve held-out performance:

- prior-year persistence,
- trailing historical mean,
- `linear_blend_baseline`,
- empirical-Bayes shrinkage,
- forecast-safe ridge profiles,
- forecast-safe analog and random-forest research profiles,
- ecology/weather experimental profiles.

This makes the work useful for public-health timing questions without implying
personal medical precision. A simple branch that validates well is preferable
to a sophisticated branch that cannot be explained.

## Why not bite-specific yet

A bite-specific risk estimate needs more than county incidence:

- tick species and life stage,
- attachment duration or engorgement,
- pathogen prevalence in the local tick population,
- uncertainty from sparse tick testing,
- clinical guidance wording reviewed by appropriate experts.

Those inputs are uneven, and some are not observable for many users. The public
v0 product therefore stays with relative county-week context and official CDC
guidance links.

## Bayesian modeling remains a research lane

Bayesian modeling remains a research lane, not the current runtime. It may
become useful for combining sparse pathogen surveillance, geography, weather,
and bite-specific evidence while preserving uncertainty.

For this project, a future Bayesian branch must earn its way in by improving
validation, explainability, and public-health usefulness. It should not replace
the current plain-language public product just because the math is attractive.
The current calibration and Gamma-Poisson update backtests are useful design
evidence, but they worsened overall MAE under default settings, so they are not
automatic public corrections.

## Future Bayesian research

Future research may revisit:

- hierarchical county-level incidence models,
- spatial smoothing for sparse tick/pathogen observations,
- bite-specific probability models using attachment duration and tick stage,
- uncertainty intervals tied to the actual modeled quantity,
- ensemble combinations where multiple validated branches improve calibration.

Any future personal-risk interface must keep the same boundary: informational
and educational only, follow CDC guidance, and consult healthcare professionals
about personal medical situations.

Last updated: 2026-05-29.
