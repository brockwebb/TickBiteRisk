# Reproducibility

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Claim-To-Source Map

The working claim-to-source map is
`docs/research/lab-notes/appendix-source-map.md`. It links draft claims to
project documents, generated artifacts, code paths, public JSON, and tests.
Release work should keep every substantive claim traceable to that map or to a
new reviewed source.

Core source references for this draft include:

- README.md
- docs/model-spec.md
- docs/data-sources.md
- docs/data-manifest.md
- docs/public-product-boundary.md
- docs/regional-research-evidence.md
- public/data/model_card.json
- public/research-data/regional/model_card.json
- tickbiterisk/modeling/risk_score.py
- tickbiterisk/modeling/regional_forecast_typicality.py

## Required Public Artifacts

Reproducibility depends on preserving the derived public artifacts and the
source metadata that explain them. Current required public artifacts include:

- public/data/model_card.json
- public/data/source_catalog.json
- public/data/static_export_manifest.json
- public/research-data/regional/model_card.json
- public/research-data/regional/static_export_manifest.json

Current generated forecast and review artifacts named by this whitepaper
include:

- build/etl/annual-forecast/annual_forecast_predictions.csv
- build/etl/regional-annual-forecast/regional_annual_forecast_predictions.csv
- build/etl/regional-forecast-typicality/regional_forecast_typicality.csv
- build/etl/regional-annual-forecast/regional_annual_forecast_intervals.csv
- build/etl/regional-forecast-observed-fit/regional_forecast_observed_fit_summary.csv
- build/etl/forecast-calibration-backtest/forecast_calibration_backtest_metrics.csv
- build/etl/forecast-bayesian-update-backtest/forecast_bayesian_update_backtest_metrics.csv

Public copies should remain derived, source-attributed, checksum-backed, and
free of raw source rows, private warehouse dumps, local secrets, or
terms-unclear extracts.

## Commands And Provenance

Reproducibility notes should identify the ETL commands, model commands,
generated CSV or JSON artifacts, source catalogs, model cards, and checksums
used for each public claim. Acquisition and source manifests should capture
source URLs or API endpoints, citation URLs, rerunnable commands or acquisition
procedures, local raw paths, checksums, retrieval timestamps, parser methods,
extraction quality, redistribution notes, and modeling caveats.

Before new data are promoted into model features or public artifacts, run:

```bash
tickbiterisk etl provenance-audit --root-dir build/etl
```

The audit trail must remain secret-free. Request URLs that include credentials
must be sanitized, and credentials must stay in the local environment.

## Tests And Verification

The draft documentation contract is covered by tests/test_research_docs.py and
tests/test_public_docs.py. Model and ETL details should also point to the
specific tests listed in the lab-note source map, including:

- tests/test_regional_research_public_data.py
- tests/test_regional_research_dashboard_static.py
- tests/test_risk_score.py
- tests/test_regional_forecast_typicality.py
- tests/test_regional_annual_forecast_intervals.py
- tests/test_forecast_calibration_backtest.py
- tests/test_forecast_bayesian_update_backtest.py
- tests/test_provenance_audit.py

For a release-candidate documentation branch, the minimum verification set is
the research/public documentation tests, Python linting, JavaScript syntax
checks for public dashboard files, `git diff --check`, and the full tracked
Python test suite.

## Release Review Checklist

This whitepaper is not release-ready. Before publication, reviewers should
check source provenance, statistical language, medical boundaries, references,
redistribution terms, and whether any research branch has been promoted beyond
the evidence record.

Reviewers should also verify that:

- source catalogs and model cards match the selected artifacts;
- score, percentile, and interval language matches the lab-note statistical
  contract;
- regional research branches remain marked research-only unless HITL approval
  changes that status;
- raw files, credentials, deliberately untracked local files, and
  terms-unclear extracts remain outside the public release boundary;
- formal bibliography reconstruction is complete before the whitepaper is
  described as publication-ready.
