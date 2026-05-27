# TickBiteRisk Model Specification

## Current implemented model

The implemented v0 model is a Maryland county-year Lyme incidence comparison
framework that produces a county-week seasonal baseline for the static
dashboard. It predicts annual Lyme incidence per 100,000 residents, compares
several transparent branches, then distributes the selected annual branch across
CDC Lyme onset seasonality to make a week-level public score.

Primary artifacts:

- `build/etl/model/model_features_county_year.csv`
- `build/etl/model/model_design_matrix_county_year.csv`
- `build/etl/model/model_design_matrix_schema.json`
- `build/etl/model-comparison/model_comparison_predictions.csv`
- `build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv`
- `public/data/md_county_risk_weekly.json`

The current public score is not weather-adjusted. Weather features are present
in the feature matrix for model comparison and future branches, but the shipped
public baseline intentionally uses the selected annual prediction plus static
seasonality until validation supports a more dynamic forecast.

## Model branches

The comparison harness supports these current branches:

| Branch | Purpose |
| --- | --- |
| `prior_year_incidence` | Simple persistence baseline using the prior observed year |
| `trailing_mean_incidence` | Smooth historical baseline over recent years |
| `linear_blend_baseline` | Selected v0 branch combining persistence and trailing mean behavior |
| `empirical_bayes_shrinkage` | County estimates shrunk toward broader Maryland behavior when data are sparse |
| `ridge_forecast_safe` | Regularized annual model using conservative non-leaky features |
| `ridge_forecast_ecology` | Regularized model including ecological feature candidates |
| `ridge_lag_weather_ecology` | Experimental lagged weather/ecology branch for comparison |

The selected dashboard branch is currently `linear_blend_baseline` because it
is transparent, stable, and defensible for a first public baseline.

## Feature families

Current model-ready feature groups include:

- Historical Lyme incidence and population-normalized rates.
- NOAA weekly weather aggregates rolled to county-year predictors.
- CDC Lyme seasonality shares by week and month of onset.
- Maryland deer harvest density proxy.
- Maryland DNR Western Maryland mast/acorn study-plot observations, joined only
  as prior-year ecology features.
- Land-cover and habitat proxy fields where acquired data support them.
- CDC tick vector and pathogen surveillance status fields.
- Data quality and assumption flags for missingness, source vintage, and
  non-comparable years.

## Validation approach

Backtests use time-aware validation: a branch can only train on information
available before the held-out year. The current comparison table reports
standard forecast diagnostics such as mean absolute error, root mean squared
error, and rank/correlation behavior across held-out county-years.

The practical questions for v0 are:

- Does the branch rank Maryland counties better than a naive statewide average?
- Does it avoid false precision when a county has sparse or unstable history?
- Are errors explainable from source limitations, reporting changes, or
  missing ecological features?
- Does adding weather or ecology improve held-out performance enough to justify
  the extra explanation burden?

Prior-year mast/acorn features are available only for Garrett, Allegany,
Washington, and Frederick from Western Maryland DNR study plots. They are
included in ecology comparison lanes, not in the conservative forecast-safe
baseline, and should be read as localized ecological context rather than
countywide or statewide mast production.

## Public score transform

The selected annual predicted incidence is multiplied by the selected CDC
weekly seasonality share. The resulting county-week predicted incidence is then
mapped to a 1-10 Maryland-relative score using a benchmark with headroom above
the high historical range. This keeps the scale stable while still allowing
unusually high county-weeks to register near the top.

The scale is relative to the current Maryland data product. It should not be
read as an absolute probability of infection.

## Single-bite decision-support overlay

The implemented `tickbiterisk risk single-bite` runtime uses the county-week
seasonal baseline as the local/seasonal prior and applies transparent
bite-evidence modifiers:

- tick species identity, with blacklegged/Ixodes ticks treated as the Lyme
  vector of concern,
- tick life stage,
- estimated attachment duration,
- engorgement,
- number of attached ticks,
- time since removal, and
- whether doxycycline safety is known or unknown.

The output is a single-bite Lyme decision-support score plus a
criterion-by-criterion CDC prophylaxis consideration summary. It is deliberately
not an absolute infection probability, diagnosis, or treatment recommendation.

## Research roadmap model

A later research branch may calibrate absolute bite-specific disease
probabilities by combining county context, tick species or life stage,
attachment duration, pathogen prevalence, and uncertainty from sparse
surveillance. That branch may use Bayesian hierarchical modeling, posterior
draws, or ensemble combinations if the data and validation justify it.

That future work must remain separate from the v0 public score until it has:

- validation against held-out surveillance and documented clinical evidence,
- clinician/public-health review of wording,
- uncertainty intervals that are meaningful for the modeled quantity,
- source and license review for all required inputs,
- plain-language warnings that users should follow CDC guidance and consult
  healthcare professionals about personal medical situations.

Last updated: 2026-05-27.
