# Validation Results

Status: draft
Primary sources: docs/regional-research-evidence.md; docs/model-spec.md; tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/forecast_calibration_backtest.py; tickbiterisk/modeling/forecast_bayesian_update_backtest.py
Reviewer focus: methods/statistics
Last checked against commit: 375a818

This chapter gathers the evidence needed to judge forecast readiness: rolling-origin validation, branch comparison metrics, Maryland public branch performance, regional research diagnostics, calibration backtests, Bayesian update checks, observed-fit overlays, and promotion gates. The current evidence supports continued research inspection; it does not promote an exploratory branch as the public Maryland default.

## Rolling-Origin Validation

Rolling-origin validation remains the primary gate for forecast claims. The relevant tests compare annual county-year predictions against held-out reported Lyme outcomes at the same temporal grain. Weekly public-facing views are seasonal allocations of annual forecasts, not independently observed county-week truth.

The current validation boundary is intentionally conservative. A branch can be useful for diagnostics, subgroup review, or future model design without becoming eligible for public forecast use. Calibration, Bayesian updating, and regional spatial-regime methods must improve rolling-origin error or calibration before they can move out of research-only status.

## Branch Comparison Metrics

Branch comparisons should be read as reported-incidence forecast diagnostics. They compare model branches on held-out county-year reported incidence and case counts, while preserving surveillance caveats around case-definition changes, source vintages, and state-source overlays.

The current regional evidence pack records that the forecast calibration backtest and the Gamma-Poisson Bayesian update backtest each produced 288 metric rows: 12 overall rows and 276 diagnostic subgroup rows. In both backtests, all 12 overall rows are gated `do_not_apply_to_public_forecast`. That gate is the controlling interpretation for public use even when a subgroup result looks promising.

## Maryland Public Branch Evidence

The public Maryland dashboard remains tied to the committed public branch and public product boundary. Current research branches can be inspected beside it, but public promotion is a separate human-in-the-loop decision.

Maryland evidence should keep three quantities distinct:

- annual county-year reported incidence forecasts,
- seasonal county-week allocations derived from annual forecasts and CDC Lyme onset seasonality, and
- single-bite decision-support overlays that explain CDC prophylaxis considerations without claiming diagnosis, treatment advice, or absolute infection probability.

The validation record should therefore avoid treating any regional update factor, calibration multiplier, or observed-fit overlay as a direct correction to the public Maryland score.

## Regional Research Diagnostics

Regional diagnostics cover Mid-Atlantic reported-incidence methods and localized spatial context. They are useful for finding failure modes, comparing branch behavior across nearby jurisdictions, and checking whether forecast intervals are wide enough for planning conversations.

The regional artifacts are not a Maryland public default and not a causal tick-ecology model. They use reported cases and county-equivalent denominators, so source-regime caveats remain part of the evidence rather than footnotes.

## Forecast Calibration Backtest

The forecast calibration backtest has 288 metric rows: 12 overall rows and 276 diagnostic subgroup rows. All 12 overall rows are gated `do_not_apply_to_public_forecast`.

Selected overall incidence MAE checks worsened:

| Branch | Original MAE | Calibrated MAE | Improvement |
| --- | ---: | ---: | ---: |
| `linear_blend_baseline` | 18.47245 | 22.19535 | -3.7229 |
| `forecast_safe_top4_ensemble` | 17.971574 | 20.913327 | -2.941753 |
| `prior_year_incidence` | 18.21318 | 22.045798 | -3.832618 |

These calibration results are research-only unless future rolling-origin gates show improved error or calibration. Subgroup improvements can inform model design, but they should not be applied to the public forecast when overall performance worsens.

## Gamma-Poisson Bayesian Update Backtest

The Gamma-Poisson Bayesian update backtest also has 288 metric rows: 12 overall rows and 276 diagnostic subgroup rows. All 12 overall rows are gated `do_not_apply_to_public_forecast`.

Selected overall incidence MAE checks worsened:

| Branch | Original MAE | Updated MAE | Improvement |
| --- | ---: | ---: | ---: |
| `linear_blend_baseline` | 18.47245 | 23.192087 | -4.719637 |
| `forecast_safe_top4_ensemble` | 17.971574 | 22.169329 | -4.197755 |
| `prior_year_incidence` | 18.21318 | 23.266222 | -5.053042 |

The Bayesian update harness is therefore research-only under the current evidence. A Gamma-Poisson update may remain a useful design path for surveillance-regime reliability, but it should not be described as a public correction until rolling-origin gates improve both incidence and case MAE, or another predeclared calibration gate is met.

## Observed-Fit Overlays

Observed-fit overlays are post-forecast diagnostics. They can show where a branch missed once later reported data become available, but they are not training features and not public-default evidence by themselves.

The Pennsylvania 2024 partial overlay is the current example. For the empirical-Bayes spatial-regime branch, the overlay covered 67 county rows:

- predicted cases: 9,415.098301
- observed cases: 16,620
- case MAE: 123.037986
- incidence MAE: 84.387219 per 100k
- direction count: 48 under-predictions and 19 over-predictions

This is partial overlay diagnostic evidence only. The decisive caveats are `partial_state_overlay`, `not_training_feature`, `not_public_default`, `reported_cases_not_stable_true_incidence`, and `not_public_maryland_default`. The overlay should not be used to claim true incidence, a blanket regional multiplier, or Maryland public readiness.

## Promotion Gates

Public promotion requires evidence and review, not just an available artifact. The current gates are:

- rolling-origin validation must improve the relevant overall error or calibration metric before calibration or Bayesian updates can move beyond research-only status;
- mixed or worse overall backtest results remain `do_not_apply_to_public_forecast`;
- diagnostic subgroup gains remain `diagnostic_subgroup_only` until confirmed by an overall gate;
- regional research branches require HITL approval before public-default promotion;
- public language must preserve the boundary around reported incidence, relative risk scores, CDC guidance, and non-medical advice.

Under the current evidence, calibration backtests, Bayesian update backtests, regional spatial-regime forecasts, and PA 2024 observed-fit overlays remain research and review material rather than public Maryland forecast changes.
