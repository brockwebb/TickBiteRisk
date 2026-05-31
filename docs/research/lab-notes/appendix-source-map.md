# Source Map

Status: draft
Primary sources: README.md; docs/model-spec.md; docs/data-sources.md; docs/data-manifest.md; docs/public-product-boundary.md; docs/regional-research-evidence.md
Reviewer focus: documentation inventory
Last checked against commit: 3456791

This appendix will map lab-note and whitepaper claims back to the governing documents, generated artifacts, and modeling code so reviewers can audit each public statement against a specific source.

## Product Boundary

Primary references: README.md; docs/public-product-boundary.md.

## Data Provenance

Primary references: docs/data-sources.md; docs/data-manifest.md.

## Annual Forecast Methods

Primary references: docs/model-spec.md; tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/annual_forecast.py.

## Seasonal Allocation

Primary references: docs/model-spec.md; public/data/model_card.json.

## Score Scale

Primary references: docs/model-spec.md; public/data/model_card.json; tickbiterisk/modeling/risk_score.py.

## Forecast Percentile And Typicality

Primary references: docs/model-spec.md; public/research-data/regional/model_card.json; tickbiterisk/modeling/regional_forecast_typicality.py.

## Forecast Intervals

Primary references: docs/model-spec.md; public/research-data/regional/model_card.json.

## Validation And Backtests

Primary references: docs/regional-research-evidence.md; tickbiterisk/modeling/model_compare.py; tickbiterisk/modeling/forecast_calibration_backtest.py; tickbiterisk/modeling/forecast_bayesian_update_backtest.py.

## Regional Research

Primary references: README.md; docs/regional-research-evidence.md; public/research-data/regional/model_card.json; public/research-data/regional/static_export_manifest.json.

## Medical And Risk-Communication Boundary

Primary references: docs/public-product-boundary.md; docs/model-spec.md; public/data/model_card.json.
