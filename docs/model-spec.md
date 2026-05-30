# TickBiteRisk Model Specification

## Current implemented model

The implemented v0 model is a Maryland county-year Lyme incidence forecasting
and comparison framework. The public score starts from an annual county
reported-incidence forecast, currently
`build/etl/annual-forecast/annual_forecast_predictions.csv` selecting
`linear_blend_baseline`, then distributes the selected annual branch across CDC
national Lyme onset seasonality to make a week-level public score.

Primary artifacts:

- `build/etl/model/model_features_county_year.csv`
- `build/etl/model/model_design_matrix_county_year.csv`
- `build/etl/model/model_design_matrix_schema.json`
- `build/etl/regional-population/midatlantic_county_population_year.csv`
- `build/etl/regional-demographics/midatlantic_age_demographics_county_year.csv`
- `build/etl/acs-exposure/midatlantic_acs_exposure_county_year.csv`
- `build/etl/regional-hotspots/midatlantic_hotspot_county_year.csv`
- `build/etl/regional-hotspots/midatlantic_hotspot_summary.csv`
- `build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv`
- `build/etl/regional-incidence/midatlantic_lyme_incidence_summary.csv`
- `build/etl/regional-outcome-stress/regional_outcome_stress_predictions.csv`
- `build/etl/regional-outcome-stress/regional_outcome_stress_metrics.csv`
- `build/etl/regional-incidence-stress/regional_incidence_stress_predictions.csv`
- `build/etl/regional-incidence-stress/regional_incidence_stress_metrics.csv`
- `build/etl/regional-incidence-clusters/regional_incidence_cluster_county_year.csv`
- `build/etl/regional-incidence-clusters/regional_incidence_cluster_summary.csv`
- `build/etl/model-comparison/model_comparison_predictions.csv`
- `build/etl/model-comparison/model_comparison_intervals.csv`
- `build/etl/annual-forecast/annual_forecast_predictions.csv`
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
| `ridge_forecast_regional` | Regularized model adding timing-safe prior-year/trailing Mid-Atlantic reported-case signals and prior-incidence cluster bands |
| `analog_year_forecast` | Forecast-safe analog-year lane with matched historical conditions and bootstrap interval diagnostics |
| `random_forest_forecast_research` | Research-only nonlinear lane using forecast-safe lagged, ecology/exposure, spatial, and regional features |
| `forecast_safe_top4_ensemble` | Research-only equal-weight blend of prior-year incidence, the simple blend, safe ridge, and spatial ridge when spatial features exist |
| `ridge_forecast_ecology` | Regularized model including timing-safe ecology candidates |
| `ridge_lag_weather_ecology` | Experimental retrospective weather/drought/ecology branch for comparison |

The selected dashboard branch is currently `linear_blend_baseline` because it
is transparent, stable, and defensible for a first public forecast. Public
promotion remains a separate product decision even when a research branch ranks
higher on a backtest.

## Feature families

Current model-ready feature groups include:

- Historical Lyme incidence and population-normalized rates.
- Census denominator-derived prior-year population growth, used only as a
  timing-safe demographic/contact-pressure proxy.
- Census PEP regional age-structure context through 2024, joined only as
  prior-year population-structure context and currently a research-only human
  exposure proxy, not a public default model input.
- ACS 2023-2024 residential form, tenure, age, and density context, currently a
  research-only human exposure proxy and not a public default model input.
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
growth, prior-year Census PEP age structure, USDM drought, EnviroAtlas habitat,
construction-lag features, prior-year USDM drought, complete prior-year ONI,
complete prior-year MEI.v2, and a transparent ecological pressure composite in
the timing-safe ecology/exposure lane. ONI and MEI.v2 stay as separate global
climate-context predictors because MEI.v2 is a dimensionless ocean-atmosphere
index rather than a CPC seasonal temperature anomaly. Held-out MAE still ranks
`prior_year_incidence` first; these features remain available for research
lanes but are not promoted into the public score.

The next spatial-lag comparison added county adjacency from public Census
geometry and a `ridge_forecast_spatial` lane using only prior-year neighbor
incidence. It ranked behind the simple blend and conservative safe ridge, with
MAE 19.005867 per 100k in the current 2024-inclusive run, so it remains a
diagnostic research lane. The regional and population-growth additions also
remain research lanes unless a future validation slice shows stable improvement.
After adding MEI.v2, regional prior-incidence clusters, prior-year age
structure, and a simple top-4 comparison ensemble to the research lanes,
`forecast_safe_top4_ensemble` ranked first at 17.971574 MAE per 100k, ahead of
`prior_year_incidence` at 18.21318 and `linear_blend_baseline` at 18.47245.
The ensemble is now reproduced by `annual-forecast` as a true target-year
research branch when Maryland county adjacency is supplied, using refreshed
origin-year lag and neighbor features rather than validation-only rows.
`random_forest_forecast_research` ranked at 20.378557 MAE per 100k,
`analog_year_forecast` ranked at 21.778584,
`ridge_forecast_ecology` ranked at 23.763644, `ridge_forecast_regional` ranked
at 24.728232, and `ridge_lag_weather_ecology` ranked at 25.233508 in the same
run. The random-forest lane is deterministic (`random_state=1337`) and uses
200 trees, minimum leaf size 3, and `max_features=sqrt`. It is intentionally
restricted to forecast-safe lagged, ecology/exposure, spatial, and regional
features; same-year weather, same-year drought, diagnostic regional totals,
cluster IDs, actual cluster outcomes, tick-status proxies, and source/caveat
flags stay out. That is useful mixed evidence: the nonlinear lane beats several
research branches but does not currently justify public promotion.

## Research lanes and diagnostics

The comparison layer may carry research-only lanes that do not change the
public dashboard branch. The `analog_year_forecast` lane is intended to match
county-years to historically similar lagged conditions and report transparent
nearest-analog behavior alongside the simpler baselines. Bootstrap intervals
are written as `model_comparison_intervals.csv` so each branch can expose
empirical uncertainty without implying clinical precision.

The `random_forest_forecast_research` lane tests whether nonlinear interactions
among lagged outcome, ecology/exposure, neighbor, regional signal, and
prior-incidence band features improve rolling-origin forecasts. It remains a
model-comparison lane only; it is not part of `annual-forecast` or the public
county-week score until later validation shows a stable gain and the model can
be explained plainly enough for the dashboard.

The `analog_year_forecast` Maryland lane is a like-year forecast branch whose
current matching basis is lagged reported-incidence history; its
`model_comparison_intervals.csv` diagnostics use `weighted_analog_bootstrap`.
The regional `analog_year_county_incidence` branch is distinct: it is
horizon-matched, preserves the matched origin, matched outcome, and distance,
and requires that matched outcome to have been observed by the forecast origin.

The `forecast_safe_top4_ensemble` lane tests whether a small equal-weight blend
can reduce variance across the strongest forecast-safe comparison branches.
`annual-forecast` can now emit it as a target-year research branch when county
adjacency is supplied. Public promotion remains a separate product decision:
the current public county-week forecast still selects `linear_blend_baseline`.

The `regional-outcome-stress` diagnostic is separate from the Maryland
incidence comparison. It tests whether state or Mid-Atlantic capacity-share
baselines improve county reported-case forecasts across DE, DC, MD, PA, VA,
and WV, including empirical-Bayes share shrinkage toward geography-level
equal-share priors. The first materialized shrinkage run slightly improved the
capacity-share lanes, but prior-year county cases still ranked first on
overall case MAE, so the capacity idea remains a useful stress test rather
than an accepted public model assumption.

The `regional-incidence-stress` diagnostic is the population-normalized
companion to `regional-outcome-stress`. It uses the Mid-Atlantic reported
incidence panel, preserves denominator gaps rather than filling them, and tests
whether analog/like-year matching, deterministic random forests over prior
incidence history, or state/Mid-Atlantic shrinkage baselines improve county
incidence forecasts. The analog lane matches the prior-year forecast origin to
earlier county histories only when the matched origin's next-year outcome was
already observed before the held-out test year. The regional RF lane trains
only on target years before the held-out year and features derived from prior
county, state, and Mid-Atlantic incidence history. The latest materialized run
still ranked prior-year county incidence best on overall incidence MAE, with
regional RF second, so these branches remain research diagnostics rather than
selected public Maryland branches or latent disease-burden estimates.

The `regional-incidence-clusters` diagnostic turns the regional pressure idea
into forecast-safe low/moderate/high/very-high bands. Each held-out year is
clustered from prior trailing county incidence only, then checked against the
same-year reported incidence. The output is useful for inspecting regional
capacity intervals and movement between lighter and heavier pressure areas,
but it is not a public score input. When supplied to the design matrix, only the
county-year assignment, prior-history incidence summaries, and band one-hots are
joined; same-year actual incidence, cases, population, cluster IDs, run
metadata, and diagnostic summary rows are excluded to avoid outcome leakage.

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
Regional Census population denominators and incidence-rate stress diagnostics
are now materialized so the count-only regional diagnostics have a
population-normalized companion; the population table itself is denominator
evidence, not exposure evidence. The regional incidence diagnostic performs
that join while preserving missing denominator rows, and the cluster diagnostic
summarizes prior-history pressure bands. They remain diagnostic panels, not
public Maryland forecast branches.

Regional Census age/sex demographics and 2023-2024 ACS residential-form summaries
are also materialized as candidate human-exposure context layers. Age mix may
help explain who is more likely to be diagnosed, exposed, or represented in
reported incidence, and ACS single-family/owner-occupied/density fields may
proxy residential edge contact. Neither source is a tick-encounter measure,
annual observed exposure, or public-default model input; ACS density fields use
static 2024 Census Gazetteer county land area for both currently materialized
vintages.

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

Known Lyme surveillance case-definition years include 1996, 2008, 2011, 2017,
and 2022 in CDC/NNDSS case-definition records. These years, plus state-source
overlays and probable-only or laboratory-based surveillance rows, should be
explicit source-regime or change-point covariates before an update model is
allowed to move a public forecast. A Pennsylvania 2024 overlay can provide
partial evidence for comparable counties and localized regimes, but it is not a
blanket regional multiplier.

`forecast_calibration_summary.csv` is the bridge artifact for that future
update model. It summarizes observed-to-predicted case ratios and additive
incidence offsets by model branch, source vintage, surveillance regime, and
forecast year. These factors are empirical calibration priors for research,
not automatic public score corrections.

`forecast-calibration-backtest` tests whether those priors would have improved
held-out predictions when learned only from earlier update rows. The first
materialized shrunken-ratio calibration worsened overall MAE for all current
branches, even though it helped some surveillance-regime subsets. That argues
for a cautious hierarchical/Bayesian update design with explicit regime
reliability rather than a blanket multiplier.

Calibration metrics now carry a gate decision. Only an overall improvement in
both incidence and case MAE can become `candidate_review_required`; mixed or
worse overall results are labeled `do_not_apply_to_public_forecast`, and
year/regime subsets remain `diagnostic_subgroup_only`.

`forecast-bayesian-update-backtest` is the parallel Bayesian update harness. It
uses a Gamma-Poisson case-multiplier posterior, reports
`update_gate_decision`, and currently remains research-only because the default
update worsened overall MAE. Bayesian or calibration outputs are therefore not
automatic public score corrections.

Forecast uncertainty terms are deliberately plain: Maryland
`model_comparison_intervals.csv` contains analog/bootstrap diagnostics, while
regional `regional_annual_forecast_intervals.csv` contains residual-calibrated
empirical prediction bands from rolling-origin regional stress residuals.
Neither artifact is a clinical interval, per-bite estimate, or proof of
causality.

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
