# Data And Provenance

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Source Families

Current source families include CDC and state Lyme surveillance, Census
population and geography, CDC national Lyme onset seasonality, weather and
ecology candidate features, regional research sidecars, model cards, and public
source catalogs.

## Derived Artifacts

The public product should publish compact derived artifacts such as scores,
selected county-week summaries, model metadata, source catalogs, quality flags,
and public-safe geometry. Raw files, private ETL outputs, credentials,
terms-unclear extracts, and deliberately untracked local files remain outside
the public release boundary unless separately reviewed.

## Provenance Boundary

Forecast artifacts preserve fields such as forecast origin, data cutoff,
source vintage, update mode, selected branch, and artifact hashes. These fields
make the public JSON auditable without redistributing raw input tables.

The public whitepaper should map each data claim back to `docs/research/lab-notes`
and the source catalogs before release.
