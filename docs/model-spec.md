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
- `build/etl/regional-population/midatlantic_county_population_year.csv`
- `build/etl/regional-hotspots/midatlantic_hotspot_county_year.csv`
- `build/etl/regional-hotspots/midatlantic_hotspot_summary.csv`
- `build/etl/regional-outcome-stress/regional_outcome_stress_predictions.csv`
- `build/etl/regional-outcome-stress/regional_outcome_stress_metrics.csv`
- `build/etl/model-comparison/model_comparison_predictions.csv`
- `build/etl/model-comparison/model_comparison_intervals.csv`
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
| `ridge_forecast_spatial` | Regularized model adding timing-safe prior-year neighbor incidence |
| `ridge_forecast_regional` | Regularized model adding timing-safe prior-year/trailing Mid-Atlantic reported-case signals |
| `analog_year_forecast` | Forecast-safe analog-year lane with matched historical conditions and bootstrap interval diagnostics |
| `ridge_forecast_ecology` | Regularized model including timing-safe ecology candidates |
| `ridge_lag_weather_ecology` | Experimental retrospective weather/drought/ecology branch for comparison |

The selected dashboard branch is currently `linear_blend_baseline` because it
is transparent, stable, and defensible for a first public baseline.

## Feature families

Current model-ready feature groups include:

- Historical Lyme incidence and population-normalized rates.
- Census denominator-derived prior-year population growth, used only as a
  timing-safe demographic/contact-pressure proxy.
- NOAA weekly weather aggregates rolled to county-year predictors.
- CDC Lyme seasonality shares by week and month of onset.
- Prior-year Lyme incidence in counties sharing a land boundary.
- Maryland deer harvest density proxy.
- Maryland DNR Western Maryland mast/acorn study-plot observations, joined only
  as prior-year ecology features.
- U.S. Drought Monitor county-year summaries, labeled as same-year
  retrospective observed drought context plus prior-year ecology candidates.
- EPA EnviroAtlas static county habitat fields.
- Census BPS construction/contact pressure, including prior-year and trailing
  construction lags.
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

The 2026-05-28 expanded feature comparison now includes prior-year population
growth, USDM drought, EnviroAtlas habitat, construction-lag features, prior-year
USDM drought, complete prior-year ONI, and a transparent ecological pressure
composite in the timing-safe ecology/exposure lane. Held-out MAE still ranks
`prior_year_incidence` first; these features remain available for research
lanes but are not promoted into the public score.

The next spatial-lag comparison added county adjacency from public Census
geometry and a `ridge_forecast_spatial` lane using only prior-year neighbor
incidence. It ranked behind the simple blend and conservative safe ridge, with
MAE 19.005867 per 100k in the current 2024-inclusive run, so it remains a
diagnostic research lane. The regional and population-growth additions also
remain research lanes unless a future validation slice shows stable improvement.
The ecological pressure composite nudged `ridge_forecast_ecology` to 21.946949
MAE per 100k in the same run, which is useful as a research signal but still
behind simpler lagged baselines.

## Research lanes and diagnostics

The comparison layer may carry research-only lanes that do not change the
public dashboard branch. The `analog_year_forecast` lane is intended to match
county-years to historically similar lagged conditions and report transparent
nearest-analog behavior alongside the simpler baselines. Bootstrap intervals
are written as `model_comparison_intervals.csv` so each branch can expose
empirical uncertainty without implying clinical precision.

The `regional-outcome-stress` diagnostic is separate from the Maryland
incidence comparison. It tests whether state or Mid-Atlantic capacity-share
baselines improve county reported-case forecasts across DE, DC, MD, PA, VA,
and WV, including empirical-Bayes share shrinkage toward geography-level
equal-share priors. The first materialized shrinkage run slightly improved the
capacity-share lanes, but prior-year county cases still ranked first on
overall case MAE, so the capacity idea remains a useful stress test rather
than an accepted public model assumption.

Surveillance-regime diagnostics should remain separate from disease truth
labels. They may flag case-definition eras, ED or inquiry coverage, reporting
capacity, or other surveillance artifacts that help explain model error.
Regional hotspot and capacity diagnostics may summarize where errors cluster
or where public-health reporting changes appear to dominate signal, but those
diagnostics are research context. They do not promote exposure candidates or
calibration indicators into the selected public dashboard branch.

The Mid-Atlantic hotspot diagnostic uses only same-year reported case counts
to classify county rank tiers and year-over-year movement. Its fields are
intentionally named `diagnostic_*` because they can reveal regional movement or
surveillance-regime disruptions, but they are not forecast-safe model features.
Regional Census population denominators are now materialized so a later slice
can convert those count-only diagnostics into incidence-rate diagnostics; the
population table itself is denominator evidence, not exposure evidence.

## Forecast Update Contract

Forecast-safe lanes use only prior-year and trailing information available
before the target year. Update-audit artifacts compare those prior forecasts
with later observed outcomes and preserve `forecast_year`,
`forecast_origin_year`, `as_of_date`, `data_cutoff_date`, `source_vintage`,
`evaluation_mode`, `update_mode`, and `surveillance_regime`.

Update interpretations are diagnostic labels. They do not convert observed
reported cases into latent true disease burden. Known reporting-break regimes
are kept separate from clean disease-pressure signals so future Bayesian or
hierarchical models can assign reliability to incoming evidence.

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
