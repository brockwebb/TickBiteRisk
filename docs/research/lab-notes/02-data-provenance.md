# Data Provenance

Status: draft
Primary sources: docs/data-sources.md; docs/data-manifest.md; docs/etl-pipeline.md; public/data/source_catalog.json; public/research-data/regional/source_catalog.json
Reviewer focus: documentation inventory
Last checked against commit: 45e3f7f

This chapter will collect the source inventory behind TickBiteRisk, distinguish raw inputs from derived public artifacts, and preserve the provenance details needed for reproducible review without expanding redistribution beyond documented permissions.

## Source Families

Current source families:

- CDC and state Lyme surveillance
- Census population and geography
- CDC national Lyme onset seasonality
- Weather, drought, ecology, host, and exposure candidates
- Regional research sidecars and overlays
- Public model cards and source catalogs

The public product uses these families conservatively. CDC and state Lyme
surveillance provide reported-case and reported-incidence context, not stable
latent true disease burden. Census sources provide denominators, geography,
county names, land area, and related context. CDC national seasonality
allocates annual forecasts across weeks for display. Weather, drought,
ecology, host, and exposure sources are candidate features or diagnostics
unless a reviewed public branch explicitly selects them.

## Raw Files And Derived Public Artifacts

Raw files and private warehouse-style outputs stay out of the public site
unless a source-specific review clearly allows redistribution. The public site
should publish derived artifacts such as risk scores, model cards, source
catalogs, static export manifests, selected county metadata, public-safe
GeoJSON, quality flags, and methodology notes.

The current Maryland runtime reads derived forecast artifacts and exports
public-safe JSON files under `public/data`. The regional research runtime does
the same under `public/research-data/regional`, with an explicit research-only
status. Neither public surface should require raw data files, database
credentials, local secrets, or private ETL outputs.

State overlays and provisional sidecars are derived review artifacts. They may
help compare sources or inspect regional stress tests, but they are not
confirmed disease truth and should not silently replace canonical forecast
inputs.

## Source Vintages And Forecast Origins

Annual forecast artifacts and regional forecast artifacts preserve their
origin and vintage metadata so reviewers can tell what evidence existed when a
forecast was generated. The fields include `forecast_origin_year`,
`as_of_date`, `data_cutoff_date`, `source_vintage`, and `update_mode`; regional
and public source catalogs also preserve selected run IDs and input hashes.

The Maryland public catalog currently frames the selected forecast as a
no-observed-target annual forecast allocated to weeks by CDC national
seasonality. The regional catalog uses the same temporal contract but is
marked research-only and not the Maryland public default. Forecast rows should
not contain or imply target-year actuals, residuals, errors, or observed weekly
truth unless the artifact is explicitly a post-forecast diagnostic.

## Public Redistribution Boundary

The redistribution boundary is derived-first. Public federal sources are often
reusable, but TickBiteRisk still publishes compact derived artifacts by
default. State reports, dashboards, restricted or terms-unclear workbooks,
large raw files, source tables, credentials, database dumps, and private ETL
outputs should not be redistributed without source-specific review.

Allowed public outputs include selected scores, aggregated or transformed
county/week summaries, model and source metadata, checksums, public guidance
links, caveats, quality flags, and public-safe geometry. Raw surveillance rows,
restricted tick-status workbooks, ambiguous branch outputs, and deliberately
untracked local files remain outside the public release boundary.

## Provenance And Audit Trail

The provenance trail is documented in source manifests, data manifests, public
source catalogs, model cards, static export manifests, and ETL
`acquisition_provenance.csv` files. The ETL provenance contract records source
URLs or API endpoints, citation URLs, rerunnable commands or acquisition
procedures, local raw paths, checksums, retrieval timestamps, parser methods,
extraction quality, redistribution notes, and modeling caveats.

`tickbiterisk etl provenance-audit --root-dir build/etl` is the review command
for scanning `acquisition_provenance.csv` and `source_manifest.csv` files
before new data are promoted into model features or public artifacts. The audit
trail should remain secret-free: request URLs that include credentials must be
sanitized, and secrets must stay in the local environment.

Public source catalogs should preserve artifact hashes, selected forecast run
IDs, source prediction hashes, seasonality hashes, selected branch metadata,
temporal-grain contracts, update policies, and medical boundaries. Those
fields make the public JSON explainable without redistributing the raw inputs.

## Known Data Gaps

Known gaps and review items include:

- NSSP tick-bite data are absent from the current model. The materialized NSSP
  table is a coverage feasibility artifact, not a tick-bite feed or disease
  outcome.
- Observed county-week and county-month Lyme truth are absent. Current weekly
  rows are seasonal allocations of annual forecasts, not observed weekly
  cases.
- Ecology extraction remains uneven. Mast/acorn extraction is low-confidence,
  land-cover and forest-composition features need deeper review, and ecology
  candidates should not drive public claims without validation.
- Official future population denominators are not yet available for forecast
  years such as 2026. Current forecast denominators may use flagged
  projections until Census publishes official estimates.
- Regional sidecars and state overlays have different geographies, definitions,
  report dates, suppression rules, and provisional-status caveats. They support
  diagnostics, not automatic public promotion.
- Bibliography and source URL cleanup is still needed before a release-ready
  whitepaper or public methodology publication.
