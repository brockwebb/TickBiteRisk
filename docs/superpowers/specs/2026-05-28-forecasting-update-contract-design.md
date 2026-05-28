# Forecasting Update Contract Design

Date: 2026-05-28
Status: Approved design, pre-implementation
Scope: Forecasting model contract, Bayesian-ready update audit, and public explainer placeholders

## Goal

Reframe TickBiteRisk as a transparent risk forecasting tool, not only a
retrospective county-week baseline. The immediate slice should make forecasting
auditable before changing public claims:

- define what was knowable at forecast time;
- record how each model branch performed when later outcome data arrived;
- separate real disease-pressure updates from surveillance/reporting artifacts;
- preserve a path toward Bayesian or hierarchical Bayesian updating without
  jumping straight to full MCMC.

The public dashboard and README should eventually explain this forecasting
purpose plainly: disease and tick surveillance data lag by months to years, but
people and public health programs need actionable estimates before final case
counts are available.

## Position On Bayesian Forecasting

Bayesian modeling is directionally well suited to this project because Lyme risk
forecasting has sparse county histories, noisy observed outcomes, regional
dependence, lagged ecology, and changing surveillance regimes. A Bayesian or
Bayesian-like update layer can express:

- a prior forecast from historical county, regional, weather, habitat, exposure,
  and surveillance context;
- an observation model for newly arrived case, tick, exposure, or state-total
  data;
- posterior updates that carry uncertainty forward rather than overwriting the
  model with one noisy new source.

The important caveat is that Bayesian updating is only as good as the
observation model. New data are not automatically better data. A provisional
2025 count, a 2024 probable-only state source, a revised case definition, or a
syndromic tick-bite feed can update the model in the wrong direction if it is
treated as stable truth. The next slice should therefore implement the update
contract first, then decide whether a full MCMC model is justified.

## Forecasting Contract

Each forecastable artifact should make these fields explicit:

- `forecast_year`: the calendar year being predicted;
- `forecast_origin_year`: the latest outcome year allowed in training;
- `as_of_date`: the date the forecast artifact was produced;
- `data_cutoff_date`: the latest source vintage intentionally included;
- `target_definition`: the observed outcome being predicted;
- `evaluation_mode`: `forecast`, `nowcast`, `retrospective`,
  `rolling_origin_backtest`, or an existing legacy backtest label such as
  `rolling_origin_prior_years` when preserving source artifact provenance;
- `update_mode`: `pre_update`, `post_observed_outcome`,
  `post_provisional_signal`, or `post_anchor_signal`;
- `source_vintage`: the source release or artifact hash used;
- `surveillance_regime`: the reporting context for observed or newly arrived
  outcome rows;
- `assumption_flags`: caveats that should travel with downstream products.

Forecast-safe model lanes may use prior-year and trailing information only.
Nowcast lanes may use partial or contemporaneous signals only when labeled as
nowcast. Retrospective lanes may use observed current-year context for model
diagnosis, not public forecast claims.

## Forecast Update Audit

Add a research artifact that treats each held-out historical year as if it were
newly arrived real data. It should compare the pre-update forecast to the
observed outcome and classify what kind of update signal the new data appear to
represent.

Expected row-level artifact:

```text
build/etl/model-diagnostics/forecast_update_audit.csv
```

Core fields:

- run and provenance: `run_id`, `source_file_sha256`, `model_name`,
  `model_family`, `feature_profile`, `source_vintage`;
- target context: `county_fips`, `county_name`, `forecast_year`,
  `forecast_origin_year`, `as_of_date`, `data_cutoff_date`,
  `target_definition`, `evaluation_mode`, `update_mode`,
  `surveillance_regime`;
- pre-update forecast: predicted incidence, predicted cases, and any available
  interval bounds;
- observed outcome: actual incidence and actual cases;
- update diagnostics: residual, absolute error, interval coverage,
  signed percent error where denominators are safe, and direction of update;
- interpretation: `forecast_signal`, `surveillance_regime_signal`,
  `ambiguous_signal`, or `insufficient_signal`;
- caveats: model feature quality flags and comparison assumption flags.

The implementation plan must define deterministic v0 interpretation rules. At
minimum, known reporting-break regimes should not be classified as clean disease
pressure simply because residuals are large, and missing interval or provenance
fields should produce explicit `insufficient_signal` or caveat values rather
than silent blanks.

Expected summary artifact:

```text
build/etl/model-diagnostics/forecast_update_summary.csv
```

Summary groups should include model, year, surveillance regime, and optionally
region when regional data are available. Metrics should include row count, mean
residual, MAE/RMSE, interval coverage, and share of rows classified by update
interpretation.

## Bayesian-Ready Update Layer

The first implementation should be Bayesian-ready without requiring full MCMC.
A defensible v0 can use closed-form or empirical-Bayes-style updates:

```text
prior county/region forecast + observed signal reliability -> posterior forecast
```

Candidate update inputs:

- rolling-origin prediction residuals;
- analog/bootstrap intervals;
- empirical Bayes county/state shrinkage residuals;
- surveillance-regime residual summaries;
- state or regional total anchors, only in explicit nowcast mode;
- later, partial-year exposure or tick-encounter signals with reliability
  weights.

This update layer should be evaluated as a model branch, not silently applied to
all public outputs. Full hierarchical Bayesian modeling remains a later lane
once the forecast contract, regional panel, and observation-model assumptions are
stable.

## Public README And Dashboard Explainers

Capture documentation and dashboard tasks now, but implement them as the final
steps of the increment after the forecast-update artifacts exist.

README updates should explain:

- TickBiteRisk is becoming a risk forecasting tool for Maryland-first Lyme
  disease pressure, with regional expansion planned.
- Official disease surveillance data often lag final real-world conditions, so
  forecasts help fill the time gap between exposure risk and final case counts.
- Forecasts are informational estimates for personal awareness and public health
  planning, not diagnosis, treatment advice, or certainty about an individual
  bite.
- The model combines historical Lyme incidence, seasonality, weather/ecology,
  host and habitat proxies, human exposure proxies where available, regional
  patterns, and surveillance caveats.
- New information is reconciled against prior forecasts, classified by source
  quality and surveillance regime, and fed forward into future model updates.

Dashboard updates should add a plain-language explainer panel or section:

- why forecasting is needed when public data lag;
- what the current score is and is not;
- how forecast-safe versus retrospective/nowcast signals differ;
- how new data improve the model over time;
- what uncertainty and intervals mean;
- where CDC guidance remains the authority for medical decisions.

Suggested placeholders before copy is finalized:

- README section: `Why Forecast Lyme Risk?`
- README section: `How Forecast Updates Work`
- Dashboard section or panel: `Why This Is A Forecast`
- Dashboard section or panel: `How New Data Updates The Model`
- Dashboard model-card field: `forecasting_status`
- Dashboard/source-catalog field: `data_lag_and_update_policy`

The dashboard wording should not overclaim. It should use "risk forecast" only
for model branches that obey forecast-time data rules, and it should continue to
avoid absolute personal infection probability claims unless a future validated
model supports that language.

## Non-Goals

- No public dashboard wording change before the update audit exists.
- No full PyMC, Stan, or MCMC implementation in this slice.
- No claim that Bayesian updating instantly fixes biased or provisional data.
- No use of same-year observed weather, same-year neighbor outcomes, same-year
  state totals, or partial surveillance signals in forecast-safe lanes.
- No diagnosis, treatment recommendation, or individual infection-probability
  language.
- No replacement of current CDC/MDH observed outcome rows with calibrated latent
  "truth" in this slice.

## Testing And Validation

Implementation should follow TDD and prove:

- forecast-update audit rows join predictions to intervals by run, model, year,
  and county without cross-branch leakage;
- years with no interval rows are handled explicitly;
- surveillance-regime labels match existing diagnostics;
- forecast-origin fields prove the model did not train on held-out outcomes;
- interval coverage is computed only when interval bounds exist;
- update interpretation is deterministic and documented;
- provenance, hashes, model names, feature profiles, and assumption flags are
  preserved;
- README/dashboard placeholder tasks are documented before final public copy
  changes.

Live validation should report:

- current best branch versus forecast-safe ridge, spatial, ecology,
  empirical-Bayes, and analog lanes;
- which surveillance regimes produce the largest update deltas;
- whether analog intervals are calibrated enough to be used in public wording;
- whether regional capacity/hotspot summaries explain update deltas better than
  county-only views.

## Acceptance Criteria

- A committed design spec captures the forecasting scope change, the Bayesian
  stance, and the forecast-update audit contract.
- The next implementation plan includes a TDD task for
  `forecast_update_audit.csv` and `forecast_update_summary.csv`.
- README and dashboard explainer placeholders are included as explicit final
  increment tasks.
- Existing public dashboard outputs remain unchanged until the forecast-update
  artifacts and public wording pass review.
- A later Bayesian/MCMC lane needs an explicit go/no-go review based on whether
  the update audit shows stable residual structure, useful interval calibration,
  and enough regional panel depth to justify a heavier probabilistic model.
