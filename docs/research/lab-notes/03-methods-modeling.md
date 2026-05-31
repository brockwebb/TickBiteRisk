# Methods And Modeling

Status: draft
Primary sources: docs/model-spec.md; docs/model-background.md; tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/annual_forecast.py; tickbiterisk/modeling/regional_annual_forecast.py
Reviewer focus: methods/statistics
Last checked against commit: 7a83b4e

This chapter will summarize the modeling contract for annual reported Lyme pressure, including the public Maryland branches, regional research branches, forecast-safe feature rules, seasonal allocation, score construction, typicality, intervals, and update policy.

## Forecast Target

The current target is county-year reported Lyme incidence per 100,000 people.
It is a surveillance-derived proxy for relative Lyme disease pressure, not a
latent estimate of every infection, tick encounter, or personal clinical risk.
Annual forecast rows carry predicted reported cases and predicted reported
incidence using projected or selected population denominators.

Observed county Lyme truth is annual in the current public data stack.
Weekly values are seasonal allocations of annual forecasts, not observed
county-week Lyme outcomes.

## Maryland Public Forecast Branches

The public Maryland county-week product currently selects
`linear_blend_baseline` from the annual forecast output. That branch averages
latest observed county incidence with trailing county history. It is selected
for transparency, stability, and plain-language defensibility, not because it
is the most sophisticated branch in the comparison harness.

Other Maryland annual branches remain available for comparison or research,
including latest-observed, trailing-mean, empirical-Bayes shrinkage,
forecast-safe ridge, spatial ridge, analog-year, random-forest research, and
small ensemble variants. Public promotion is a separate product decision and
requires rolling-origin validation, explainability, and review.

## Regional Research Branches

The regional research page uses
`empirical_bayes_spatial_regime_incidence` for the Mid-Atlantic research
forecast. That branch combines prior reported county history with empirical
Bayes shrinkage and localized spatial-regime prior-history features. It is
explicitly marked as a regional research branch and is not the public Maryland
default.

Regional forecasts cover DE, DC, MD, PA, VA, and WV county or
county-equivalent rows, use reported-incidence denominators where available,
and carry `not_public_maryland_default` caveats. They are useful for stress
testing regional patterns, intervals, and typicality language, but they should
not be described as replacing the Maryland public branch.

## Forecast-Safe Rules

Forecast-safe means a target-year forecast can use only information available
at or before the forecast origin. Held-out or target-year outcomes cannot be
used as features, and same-year diagnostic fields cannot be promoted into
forecast inputs. This includes same-year reported cases, same-year reported
incidence, county-week or county-month observed Lyme values, diagnostic
regional totals, realized cluster outcomes, and source caveat fields that
would reveal the outcome being predicted.

Timing-safe examples include prior reported incidence, trailing county
history, prior-year state or regional context, prior-year neighbor incidence,
and prior-history spatial-regime features. Same-year weather, drought, hotspot,
capacity, or surveillance diagnostics can explain errors after the fact but do
not belong in the public forecast feature set unless a future design proves
they are available before the target year and improve validation.

## Seasonal Allocation

Seasonality is a display allocation step. The selected annual county forecast
is multiplied by CDC national Lyme onset seasonality shares for MMWR weeks.
The resulting weekly values preserve the annual forecast basis while showing
where reported Lyme onset has tended to fall within a year.

The seasonal curve is national, not county-specific, and is marked as a static
seasonality prior. It does not use observed county-week Lyme cases, observed
county-week tick counts, infected tick prevalence, or weather-adjusted
near-term dynamics.

## Score Construction

The public score maps predicted weekly reported-incidence pressure onto a
relative 1-10 display scale. In `risk_score.py`, each selected annual forecast
is allocated to MMWR weeks and scored against the rows in the selected branch,
geography, and forecast artifact. The benchmark weekly incidence is the
nearest-rank benchmark quantile of predicted weekly incidence; the default
benchmark quantile is `0.95`. The score denominator is that benchmark weekly
incidence multiplied by the headroom multiplier; the default headroom
multiplier is `1.2`. Raw score is computed as:

```text
10 * predicted_weekly_incidence_per_100k / score_denominator
```

The displayed score is the rounded raw score clamped to `1..10`. The value
`10` is a scale cap, not a probability, infection chance, clinical threshold,
or treatment trigger. Because the denominator is derived from the selected
branch, geography, forecast rows, benchmark quantile, and headroom multiplier,
changing any of those inputs changes the display scale interpretation.

## Forecast Typicality

Forecast typicality compares the selected annual forecast with the same
county's prior reported annual incidence through the forecast origin. The
regional typicality layer uses an empirical percentile of prior county history
and records baseline years, quartiles, a median, percentile labels, and the
margin outside the typical band.

Typicality is about reported-incidence history, not biological certainty. A
forecast can be "typical", "above typical", or "much higher than typical" for
that county's reporting history without implying an individual person's chance
of infection. These prior-history bands provide county-history context; they
do not describe model forecast error.

## Forecast Intervals

Forecast intervals are empirical ranges from historical forecast residuals
around reported-incidence proxy forecasts. They are available only when the
selected artifact includes interval rows. The current Maryland public model
card lists interval method `not_available`, so Maryland public score rows
should not be described as if forecast intervals are currently available for
every public score. The regional research artifact includes intervals using
`empirical_rolling_origin_residual_quantile`.

These intervals are not clinical intervals, per-bite risk intervals, or
medical confidence intervals. They summarize historical model error for the
forecasted reported-incidence quantity and must keep the surveillance and
reporting caveats attached. Interval bands answer a different question than
typicality bands: intervals describe forecast-error uncertainty around the
modeled quantity, while typicality bands describe whether a forecast is high
or low relative to that county's own prior reported history.

## Update Policy

New surveillance, denominator, ecology, exposure, or regional evidence is not
allowed to automatically move the public score. The update process is to ingest
reviewed county-year data with source caveats, compare prior forecasts with
later observed reported-incidence outcomes, record residuals by county, branch,
surveillance regime, and region, then rerun eligible branches only when
coverage and timing rules are satisfied.

Known surveillance-regime changes and state-source overlays are diagnostic
evidence. They can explain forecast residuals or support future update design,
but they do not convert reported cases into latent true burden and do not
create a blanket multiplier for public Maryland forecasts.

## Research Lanes Not Promoted

Calibration and Gamma-Poisson Bayesian update lanes are research-only until
rolling-origin gates improve. Current documentation records that default
calibration and Bayesian update backtests worsened overall MAE, even if some
subgroups looked useful diagnostically. Their outputs are therefore not
automatic public corrections.

Other research lanes, including random forests, analog-year branches,
forecast-safe ensembles, ecology/weather comparisons, regional stress tests,
hotspot diagnostics, and spatial-regime regional forecasts, remain candidates
for evidence gathering. Promotion requires improved held-out behavior,
forecast-safe inputs, stable uncertainty language, and public-health wording
that does not overclaim personal or clinical risk.
