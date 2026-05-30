# Regional Research Evidence Pack

This evidence pack summarizes the current regional research artifacts that are
safe to inspect before a human product decision. It is not a public promotion
memo, not a medical guidance document, and not a change to the Maryland public
default.

## spatial-regime evidence pack

Primary artifacts:

- `build/etl/regional-spatial-regimes/regional_spatial_regime_runs.csv`
- `build/etl/regional-spatial-regimes/regional_spatial_regime_summary.csv`
- `build/etl/regional-annual-forecast/regional_spatial_regime_forecast_interval_summary.csv`
- `public/research-data/regional/regional_spatial_regime_overlays.json`

Run facts from the current derived build:

- run id:
  `regional_spatial_regimes_start2007_end2024_mintrain3_lookback3_mean25p0_prior25p0_trend25p0`
- start year: 2007
- end year: 2024
- minimum training years: 3
- lookback years: 3
- n_input_rows: 6,599
- n_county_years: 5,098
- n_summary_rows: 1,224
- 2024 regime count: 127
- 2024 county-equivalent coverage: 283
- largest 2024 regime: `2024_regime_03`, with 109 county-equivalents
- comparison flags include `observational_not_causal`,
  `reported_cases_not_stable_true_incidence`,
  `localized_spatial_regime_research`, and `not_public_maryland_default`

The interval summary is a planning aggregate. The current
`regional_spatial_regime_forecast_interval_summary.csv` has 762 rows using
summed county empirical residual intervals, not posterior draws and not a joint
spatial probability model. For 2026 forecasts from origin year 2023, Spatial
regime 3 has 109 county-equivalents, predicted incidence 16.302663 per 100k,
an 80% empirical range from 4.120999 to 59.680319 per 100k, and a 95% empirical
range from 0.559834 to 144.352597 per 100k.

The public regional research page may use these artifacts to explain local
forecast-region context. It should not use them to declare causal tick ecology,
personal infection probability, or a replacement public model.

## Observed-fit context

Observed-fit artifact:

- `build/etl/regional-forecast-observed-fit/regional_forecast_observed_fit_summary.csv`

The Pennsylvania 2024 partial overlay is post-forecast diagnostic evidence
only. The current empirical-Bayes spatial-regime branch forecast for the
Pennsylvania 2024 partial overlay covered 67 county rows.

- predicted 9,415.098301 cases
- observed 16,620 cases
- case MAE: 123.037986
- incidence MAE per 100k: 84.387219
- direction: 48 under-predictions and 19 over-predictions

This row is useful because it shows where the branch missed after forecast
origin, but the flags remain decisive: `partial_state_overlay`,
`not_training_feature`, `not_public_default`, `reported_cases_not_stable_true_incidence`,
and `not_public_maryland_default`.

## forecast update evidence pack

Primary artifacts:

- `build/etl/forecast-calibration-backtest/forecast_calibration_backtest_metrics.csv`
- `build/etl/forecast-bayesian-update-backtest/forecast_bayesian_update_backtest_metrics.csv`

The calibration backtest has 288 metric rows: 12 overall rows and 276
diagnostic subgroup rows. All 12 overall rows are gated
`do_not_apply_to_public_forecast`. Selected overall incidence MAE checks:

| branch | original MAE | calibrated MAE | improvement |
| --- | ---: | ---: | ---: |
| `linear_blend_baseline` | 18.47245 | 22.19535 | -3.7229 |
| `forecast_safe_top4_ensemble` | 17.971574 | 20.913327 | -2.941753 |
| `prior_year_incidence` | 18.21318 | 22.045798 | -3.832618 |

The Gamma-Poisson Bayesian update backtest also has 288 metric rows: 12
overall rows and 276 diagnostic subgroup rows. All 12 overall rows are gated
`do_not_apply_to_public_forecast`. Selected overall incidence MAE checks:

| branch | original MAE | updated MAE | improvement |
| --- | ---: | ---: | ---: |
| `linear_blend_baseline` | 18.47245 | 23.192087 | -4.719637 |
| `forecast_safe_top4_ensemble` | 17.971574 | 22.169329 | -4.197755 |
| `prior_year_incidence` | 18.21318 | 23.266222 | -5.053042 |

These results are research backtests and not automatic public score corrections.
Subgroup improvements can guide future model design, but they are diagnostic
evidence only until an overall rolling-origin gate improves both incidence and
case MAE.

## Public boundary

The public Maryland dashboard remains the committed default. Public branch promotion remains HITL.
Risk color scale or top-coding changes, medical or CDC guidance wording
changes, default map or chart scope changes, and any decision to commit,
delete, or normalize deliberate untracked local files remain HITL too.
