# Surveillance, Analog, Exposure, and Regional Systems Design

Date: 2026-05-28
Status: Approved design, pre-implementation
Scope: Surveillance-regime diagnostics, analog-year forecasting, bootstrap intervals, exposure-source registry, and regional hotspot/capacity model design

## Goal

Improve the annual Lyme modeling layer by separating four ideas that are currently tangled together:

- ecological hazard: weather, habitat, mast/acorn, deer, drought, and tick/vector context;
- human exposure: the chance people actually encounter ticks;
- surveillance measurement: the difference between true disease pressure and observed/reportable case counts;
- regional systems behavior: neighboring counties and ecological regions sharing pressure across county and state borders.

The near-term implementation should run on the current Maryland design matrix, but the interfaces should be regional-ready so Pennsylvania and other Mid-Atlantic counties can be added without rewriting the model comparison harness.

## Evidence Direction

The human-tick-encounter paper in `cdc_150318_DS1.pdf` supports a direct exposure feature family. Household tick encounters were associated with verified tickborne disease risk (`RR = 2.60`), and attached ticks had stronger association (`RR = 3.77`). That does not turn tick encounters into a clinical probability model, but it strongly suggests that habitat alone is missing a human-contact layer.

The surveillance papers point in the other direction: observed Lyme counts are not stable truth. The lab-based surveillance paper suggests high-incidence states may see reported counts shift by about `1.2x` under revised laboratory-based surveillance. The New York underreporting study found roughly `20%` more cases after accounting for underreporting and misclassification. The Maryland ICD-code paper found administrative codes too unreliable as standalone surveillance labels.

The modeling implication is:

```text
latent disease pressure + human exposure + surveillance regime -> observed cases
```

Do not ask one more ecology covariate to explain a surveillance-regime break.

## Slice Components

### Surveillance-Regime Diagnostics

Add diagnostic outputs that report residuals and error metrics by known or likely surveillance regimes:

- pre-2020 baseline;
- 2020 COVID reporting disruption;
- 2022+ Lyme case-definition change;
- 2024 MDH state-source/probable-only row set;
- state-source rows versus CDC canonical rows where both exist.

These diagnostics should not become default predictors. They are first a way to show whether the current model is systematically biased across reporting regimes. A separate sensitivity lane may later adjust targets or predictions, but the first implementation should make the problem visible.

Required metrics:

- count of prediction rows;
- mean residual incidence per 100k;
- MAE and RMSE per 100k;
- mean residual cases and MAE cases;
- year and regime labels;
- model name.

### Analog-Year Forecast Lane

Add an interpretable forecast lane that treats history as a hedge. For held-out year `Y`, compare county or county-region initial conditions from `Y-1` against prior historical years available before `Y`, then use the next-year outcomes from similar historical years as the prediction set.

Candidate similarity features must be timing-safe:

- prior-year county Lyme incidence;
- trailing incidence mean and volatility;
- prior-year state or cluster incidence;
- prior-year neighbor incidence mean/max;
- prior-year drought summaries;
- complete prior-year ONI/El Nino/La Nina features;
- lagged/trailing construction/contact pressure;
- lagged/trailing population growth;
- static habitat fields.

The first implementation should keep this auditable:

- standardize features using training rows only;
- compute weighted nearest analogs by distance;
- emit the matched analog years/counties and weights;
- predict the weighted next-year incidence change or next-year incidence;
- fall back to prior-year/trailing mean when analog depth is insufficient.

### Bootstrap Intervals

Add bootstrap uncertainty around eligible forecast lanes. This is not a new truth model; it is an interval around fragile historical evidence.

Initial bootstrap behavior:

- resample analog matches or training residuals with a deterministic seed;
- produce lower, median, upper interval values, such as 10th/50th/90th percentiles;
- report interval width and whether the observed held-out value landed inside the interval;
- summarize interval coverage by model, year, and surveillance regime.

The public dashboard should not display these intervals until validation and wording are ready.

### Regional Hotspot and Capacity Diagnostics

Design the model around regions, not political boundaries. County/state lines are reporting containers, while ticks, hosts, forests, construction, and human recreation cross those lines.

The first regional-ready layer should be diagnostic, not a hard biological cap:

- build cluster or region summaries from county predictions and observed outcomes;
- support adjacency-based hotspot groups where neighboring counties have persistently high incidence or high residuals;
- report cluster-level annual totals, rates, shares of state/region total, and year-over-year movement;
- estimate historical lower/upper envelopes for cluster totals and shares;
- compare county predictions before and after optional state/cluster anchoring.

Capacity language should be careful. A cluster may show a historical disease-output envelope, but that is an empirical surveillance-and-ecology range, not proof of a fixed natural maximum. Escalation outside historical envelopes should be flagged as a trend/regime warning, not automatically treated as model error.

K-means or similar clustering can be tested once regional data are present, but the first implementation should prefer transparent clusters:

- county adjacency;
- high/medium/low historical incidence bands;
- persistent residual/hotspot groups;
- later, standardized feature-space clusters if they improve validation.

Any learned or history-derived cluster membership used in validation must be fit inside each rolling-origin training window. A held-out year cannot inherit cluster labels, hotspot weights, scaling constants, or disease-producing-region definitions learned from future years.

### State or Cluster Anchoring

Add an optional calibration lane that reconciles county forecasts to a state or regional total envelope.

Two modes are allowed:

- forecast envelope: use only prior historical data to estimate plausible state/cluster totals for held-out year `Y`;
- nowcast anchor: use a known state total for `Y` only when explicitly labeled as nowcast/calibration, never as a forecast-safe model.

Anchoring should preserve county ranking as much as possible. It should be evaluated separately for:

- county-level MAE/RMSE;
- state/cluster total case error;
- rank/correlation;
- calibration slope/intercept;
- whether anchoring hides local hotspot errors.

### Exposure Source Registry

Expand the potential-source documentation for human exposure pressure. Candidate families:

- ED, urgent-care, or syndromic tick-bite/tick-encounter signals;
- CDC Tick Bite Data Tracker backing data if obtainable;
- poison center or state/local tick-bite inquiry aggregates;
- park/trail/campground attendance or reservation data;
- hunting, fishing, and outdoor recreation participation proxies;
- pet ownership, dog-license, or veterinary encounter proxies;
- property-size, low-density residential, parcel, or housing-density proxies;
- age mix and household composition;
- interactions such as `low_density_residential * forest_pct` or `large_lot_proxy * natural_land_cover_index`;
- tick submission volume, kept separate from pathogen positivity.

Claims, ICD, and administrative code data must not become standalone truth labels. They can be catalogued as weak auxiliary signals with explicit sensitivity/specificity caveats.

## Non-Goals

- No public dashboard branch change in this slice.
- No random forest default branch yet. Flexible learners should wait until the regional panel is materially larger.
- No full Bayesian/MCMC implementation yet. The design should preserve a path toward hierarchical Bayesian modeling, but first needs explicit county/state/source/regime structure.
- No claim that historical capacity envelopes are fixed ecological limits.
- No use of same-year state totals, ED signals, lab signals, or neighbor outcomes in forecast-safe lanes.
- No broad regional ETL in this slice unless a source is already clean and implementation-safe. Pennsylvania remains the best next regional outcome ETL, but this design focuses the modeling layer.

## Data Products

Expected new or extended artifacts:

- `build/etl/model-diagnostics/surveillance_regime_residuals.csv`
- `build/etl/model-diagnostics/surveillance_regime_summary.csv`
- `build/etl/model-diagnostics/regional_hotspot_summary.csv`
- `build/etl/model-diagnostics/regional_capacity_intervals.csv`
- `build/etl/model-comparison/model_comparison_predictions.csv` with analog/bootstrap model rows or companion interval rows;
- `build/etl/model-comparison/model_comparison_intervals.csv` if interval columns do not fit the current prediction schema;
- source-catalog updates for human exposure and surveillance-calibration candidates.

The exact artifact split can change during implementation if tests show a cleaner boundary, but diagnostics should remain separate from public static data.

## Leakage Rules

Forecast-safe lanes may use only information available before the target year:

- prior-year or trailing human exposure proxies only;
- prior-year or trailing population growth only;
- prior-year drought/ONI/contact pressure only;
- prior-year neighbor incidence only;
- historical state/cluster total envelopes only.

Retrospective or nowcast lanes may use contemporaneous data only when their labels make that explicit. These lanes are useful for understanding what happened; they are not eligible for the public forecast baseline.

## Testing and Validation

The implementation should follow TDD with small fixtures that prove:

- residual diagnostics group rows by surveillance regime correctly;
- analog matching never uses rows from the held-out year or future years;
- feature standardization uses training rows only;
- analog output preserves matched years/counties and weights;
- bootstrap intervals are deterministic for a fixed seed;
- state/cluster anchoring does not use held-out totals in forecast mode;
- cluster membership and hotspot weights are fit from training rows only;
- county-share allocation uses prior/trailing history only;
- missing analog depth falls back to an existing transparent baseline;
- new artifacts preserve source hashes, model names, and assumption flags.

Live validation should report:

- current baseline versus analog-year lane;
- interval coverage and interval width;
- surveillance-regime residual bias;
- Maryland-only metrics even after regional data are added;
- cluster/state total error before and after anchoring;
- hotspot persistence and year-over-year cluster movement;
- top-k hotspot hit rate, such as whether true top 3 or top 5 counties appear in predicted top-k sets;
- rank correlation by year;
- county share error within state or cluster totals;
- predicted versus observed case concentration, such as Gini or Herfindahl-style concentration;
- boundary-county error versus interior-county error once regional states are available.

## Acceptance Criteria

- A committed design spec documents surveillance diagnostics, analog/bootstrap modeling, exposure-source candidates, and regional hotspot/capacity design.
- The implementation plan after this spec splits diagnostics, analog/bootstrap forecasting, and source-registry updates into testable steps.
- Initial code changes keep public static dashboard outputs unchanged.
- Any new model branch is compared through rolling-origin validation and must be labeled forecast-safe, retrospective, or nowcast.
- Regional concepts are represented in artifacts and tests without requiring all surrounding-state ETL to land in the same slice.
