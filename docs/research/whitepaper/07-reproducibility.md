# Reproducibility

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Source Map

The working source map in `docs/research/lab-notes` links draft claims to
project documents, generated artifacts, code paths, public JSON, and tests.
Release work should keep every substantive claim traceable to that map or a
new reviewed source.

## Commands And Artifacts

Reproducibility notes should identify the ETL commands, model commands,
generated CSV or JSON artifacts, source catalogs, model cards, and checksums
used for each public claim.

## Tests

The draft documentation contract is covered by `tests/test_research_docs.py`.
Model and ETL details should also point to the specific tests listed in the
lab-note source map.

## Review Status

This skeleton is not release-ready. Before publication, reviewers should check
source provenance, statistical language, medical boundaries, references,
redistribution terms, and whether any research branch has been promoted beyond
the evidence record.
