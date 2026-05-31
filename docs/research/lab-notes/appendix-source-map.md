# Source Map

Status: draft
Primary sources: README.md; docs/model-spec.md; docs/data-sources.md; docs/data-manifest.md; docs/public-product-boundary.md; docs/regional-research-evidence.md
Reviewer focus: documentation inventory
Last checked against commit: 28d23f9

This appendix maps lab-note and whitepaper claims back to governing documents, generated artifacts, code paths, and tests. It is meant to keep public wording auditable: if a claim cannot be tied to a source listed here, it should stay out of a release-ready whitepaper until reviewed.

## Product Boundary

Claim: TickBiteRisk is currently a Maryland-first public information and research product that forecasts relative reported Lyme disease pressure. It is not diagnosis, treatment advice, or a calibrated personal infection probability.

Primary docs: README.md; docs/public-product-boundary.md; docs/model-spec.md.

Public artifacts: public/data/model_card.json; public/data/source_catalog.json; public/data/static_export_manifest.json.

Code and tests: tickbiterisk/runtime/risk_lookup.py; tickbiterisk/runtime/static_export.py; tickbiterisk/modeling/risk_score.py; tests/test_runtime_risk_lookup.py; tests/test_cli_risk_lookup.py; tests/test_static_export.py; tests/test_research_docs.py.

Required caveat: public language must keep the score framed as relative reported-incidence context and must not say the product determines whether a person is infected.

## Data Provenance

Claim: The public site publishes compact derived artifacts and source metadata; raw files, terms-unclear extracts, private ETL outputs, credentials, and deliberately untracked local files stay outside the public release boundary unless separately reviewed.

Primary docs: docs/data-sources.md; docs/data-manifest.md; docs/public-product-boundary.md; README.md.

Public artifacts: public/data/source_catalog.json; public/data/model_card.json; public/research-data/regional/source_catalog.json; public/research-data/regional/static_export_manifest.json.

Code and tests: tickbiterisk/etl/acquisition_provenance.py; tickbiterisk/etl/provenance_audit.py; tests/test_provenance_audit.py; tests/test_regional_research_public_data.py.

Required caveat: state-source overlays, sidecars, and provisional rows are review evidence, not confirmed latent disease truth and not automatic public model inputs.

## Annual Forecast Methods

Claim: The implemented public forecast starts from an annual county reported-incidence forecast. The current Maryland public branch is `linear_blend_baseline`; regional research uses `empirical_bayes_spatial_regime_incidence` for the research page.

Primary docs: docs/model-spec.md; README.md; docs/data-manifest.md; docs/regional-research-evidence.md.

Generated artifacts: build/etl/annual-forecast/annual_forecast_predictions.csv; build/etl/regional-annual-forecast/regional_annual_forecast_predictions.csv; public/data/model_card.json; public/research-data/regional/model_card.json.

Code and tests: tickbiterisk/modeling/annual_forecast.py; tickbiterisk/modeling/regional_annual_forecast.py; tickbiterisk/modeling/model_compare.py; tests/test_annual_forecast.py; tests/test_regional_annual_forecast.py; tests/test_model_comparison.py.

Required caveat: branch availability is not public promotion. Changing the selected public branch is a HITL product decision.

## Seasonal Allocation

Claim: Weekly seasonal rows are display allocations of annual forecasts using CDC national Lyme onset seasonality. They are not observed county-week Lyme outcomes.

Primary docs: README.md; docs/model-spec.md; docs/data-sources.md; docs/data-manifest.md.

Generated artifacts: build/etl/seasonality/seasonality_baseline.csv; build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv; public/data/md_county_risk_weekly.json; public/data/model_card.json; public/research-data/regional/model_card.json.

Code and tests: tickbiterisk/etl/seasonality.py; tickbiterisk/modeling/risk_score.py; tests/test_seasonality.py; tests/test_cli_seasonality.py; tests/test_risk_score.py; tests/test_static_export.py.

Required caveat: CDC national seasonality is static and not county-specific; it does not measure weekly tick abundance, infected-tick prevalence, or observed county-week cases.

## Score Scale

Claim: The predicted score is a rounded 1-10 display value derived from predicted weekly reported-incidence pressure and the selected score denominator.

Primary docs: docs/model-spec.md; public/data/model_card.json; public/research-data/regional/model_card.json.

Generated artifacts: build/etl/county-week-risk/risk_score_scale.csv; build/etl/regional-county-week-risk/risk_score_scale.csv; public/data/md_county_risk_weekly.json; public/research-data/regional/regional_county_risk_weekly.json.

Code and tests: tickbiterisk/modeling/risk_score.py; tests/test_risk_score.py; tests/test_regional_research_public_data.py.

Implementation contract: tickbiterisk/modeling/risk_score.py computes the benchmark as the nearest-rank quantile of predicted weekly incidence, default `benchmark_quantile=0.95`, multiplies by `headroom_multiplier=1.2`, computes `10 * predicted_weekly_incidence_per_100k / score_denominator`, then rounds and clamps to `1..10`.

Required caveat: a score of `10` is a display cap, not infection probability, a clinical threshold, or a treatment trigger.

## Forecast Percentile And Typicality

Claim: Forecast percentile and severity labels compare a selected annual forecast with the same county's prior reported annual incidence history through the forecast origin.

Primary docs: docs/model-spec.md; docs/regional-research-evidence.md; public/research-data/regional/model_card.json.

Generated artifacts: build/etl/regional-forecast-typicality/regional_forecast_typicality.csv; public/research-data/regional/regional_forecast_typicality.json.

Code and tests: tickbiterisk/modeling/regional_forecast_typicality.py; tests/test_regional_forecast_typicality.py; tests/test_regional_research_public_data.py.

Implementation contract: tickbiterisk/modeling/regional_forecast_typicality.py uses `empirical_percentile_of_prior_county_history`, with baseline policy `county history years <= forecast_origin_year`, and labels forecasts as below typical, typical, above typical, or much higher than typical.

Required caveat: typicality is county-history context for reported incidence. It is not forecast-error uncertainty, not biological certainty, and not an individual risk classification.

## Forecast Intervals

Claim: Forecast intervals are empirical ranges around reported-incidence forecasts when the selected artifact provides interval rows.

Primary docs: docs/model-spec.md; docs/regional-research-evidence.md; public/data/model_card.json; public/research-data/regional/model_card.json.

Generated artifacts: build/etl/model-comparison/model_comparison_intervals.csv; build/etl/regional-annual-forecast/regional_annual_forecast_intervals.csv; build/etl/regional-annual-forecast/regional_spatial_regime_forecast_interval_summary.csv.

Code and tests: tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/regional_annual_forecast_intervals.py; tickbiterisk/modeling/risk_score.py; tests/test_model_comparison.py; tests/test_regional_annual_forecast_intervals.py; tests/test_risk_score.py.

Artifact distinction: public/data/model_card.json currently records Maryland interval method `not_available`; public/research-data/regional/model_card.json records regional interval method `empirical_rolling_origin_residual_quantile`.

Required caveat: interval examples must name the model branch and artifact. These are not medical confidence intervals, posterior draws, per-bite intervals, or a joint spatial probability model.

## Validation And Backtests

Claim: Rolling-origin validation and backtest gates control public promotion. Current calibration and Gamma-Poisson Bayesian update backtests remain research-only because overall rows are gated `do_not_apply_to_public_forecast`.

Primary docs: docs/model-spec.md; docs/regional-research-evidence.md; docs/data-manifest.md.

Generated artifacts: build/etl/model-comparison/model_comparison_summary.csv; build/etl/model-comparison/model_comparison_metrics.csv; build/etl/forecast-calibration-backtest/forecast_calibration_backtest_metrics.csv; build/etl/forecast-bayesian-update-backtest/forecast_bayesian_update_backtest_metrics.csv; build/etl/regional-forecast-observed-fit/regional_forecast_observed_fit_summary.csv.

Code and tests: tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/model_diagnostics.py; tickbiterisk/modeling/forecast_calibration_backtest.py; tickbiterisk/modeling/forecast_bayesian_update_backtest.py; tickbiterisk/modeling/regional_forecast_observed_fit.py; tests/test_model_comparison.py; tests/test_model_diagnostics.py; tests/test_forecast_calibration_backtest.py; tests/test_forecast_bayesian_update_backtest.py; tests/test_regional_forecast_observed_fit.py.

Required caveat: subgroup improvements and observed-fit overlays can guide future design, but they do not automatically correct the public Maryland score.

## Regional Research

Claim: The regional page is a research-only Mid-Atlantic surface for DE, DC, MD, PA, VA, and WV county-equivalents, with cross-border adjacency, localized spatial regimes, intervals, and observed-fit diagnostics.

Primary docs: README.md; docs/regional-research-evidence.md; docs/data-sources.md; docs/data-manifest.md.

Public artifacts: public/research-data/regional/model_card.json; public/research-data/regional/source_catalog.json; public/research-data/regional/static_export_manifest.json; public/research-data/regional/regional_spatial_regime_overlays.json.

Generated artifacts: build/etl/regional-county-adjacency/regional_county_adjacency.csv; build/etl/regional-spatial-regimes/regional_spatial_regime_county_year.csv; build/etl/regional-spatial-regimes/regional_spatial_regime_summary.csv; build/etl/regional-annual-forecast/regional_annual_forecast_predictions.csv; build/etl/regional-forecast-observed-fit/regional_forecast_observed_fit_summary.csv.

Code and tests: tickbiterisk/etl/regional_county_geometry.py; tickbiterisk/modeling/regional_spatial_regimes.py; tickbiterisk/modeling/regional_annual_forecast.py; tickbiterisk/modeling/regional_forecast_observed_fit.py; tests/test_regional_county_geometry.py; tests/test_regional_spatial_regimes.py; tests/test_regional_annual_forecast.py; tests/test_regional_research_public_data.py; tests/test_regional_research_dashboard_static.py.

Required caveat: regional research artifacts are not the Maryland public default and should not be described as causal tick ecology or public regional product claims without HITL approval.

## Medical And Risk-Communication Boundary

Claim: Public product language may link to CDC/public-health guidance and explain CDC prophylaxis consideration criteria, but it must not diagnose disease, recommend treatment, replace clinician judgment, or imply a low score makes symptoms safe to ignore.

Primary docs: docs/public-product-boundary.md; README.md; public/data/model_card.json; public/research-data/regional/model_card.json.

Public artifacts: public/data/model_card.json; public/data/source_catalog.json; public/research-data/regional/model_card.json.

Code and tests: tickbiterisk/runtime/risk_lookup.py; tickbiterisk/runtime/single_bite.py; tickbiterisk/modeling/risk_score.py; tests/test_runtime_risk_lookup.py; tests/test_cli_risk_lookup.py; tests/test_single_bite_risk.py; tests/test_research_docs.py.

Required caveat: cite official CDC guidance for tick removal, prevention, symptoms, and clinician guidance. Product copy remains informational and educational.
