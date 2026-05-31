# Research Lab Notes And Whitepaper Design

## Decision

TickBiteRisk needs two documentation layers:

1. An internal research dossier that acts like organized lab notes.
2. A later public technical whitepaper distilled from those notes.

The lab notes come first. They should be candid, traceable, and useful to the
project team while the research surface is still moving. The public whitepaper
should not become the first place where methods, caveats, failed lanes,
statistics, or source boundaries are reconciled. It should be a polished
extraction from a reviewed internal record.

The initial authoring target is therefore a chaptered internal dossier under
`docs/research/lab-notes/`. After that dossier is coherent, the second target
is a hybrid public technical whitepaper under `docs/research/whitepaper/`.

## Goals

The research dossier must make the current project understandable without
requiring a reader to reconstruct the story from the SRS, model specs, public
dashboard copy, source catalogs, test files, and recent implementation plans.
It should answer:

- What is TickBiteRisk currently estimating?
- What is it explicitly not estimating?
- What data sources and derived artifacts support the estimate?
- How do the annual forecast, weekly seasonal allocation, score, percentile,
  and uncertainty ranges work?
- Which modeling branches are public defaults, regional research lanes,
  diagnostics, or rejected/promoted candidates?
- What evidence exists from backtests and observed-fit checks?
- What caveats are required to avoid overstating reported surveillance data as
  true infection burden, personal infection probability, or medical guidance?
- What decisions remain human-in-the-loop?

The later public whitepaper should preserve the same technical truth but in a
more polished form. It should be readable by a motivated public user,
collaborator, reviewer, or public-health stakeholder. It should front-load plain
language, then provide methods, source provenance, validation, limitations, and
reproducibility details.

## Non-Goals

The lab notes are not a marketing page, publication-ready manuscript, or
replacement for source-specific documentation. They should cite and summarize
existing source docs instead of copying whole source catalogs into prose.

The public whitepaper must not present the regional research page as the
Maryland public default, and it must not present TickBiteRisk as a calibrated
per-bite infection probability engine. The current product is a relative Lyme
reported-incidence forecasting and risk-context tool with a bite guidance
overlay, not a diagnostic or treatment system.

The first documentation pass does not need to solve every citation or figure.
It should create the structure, capture the known evidence, and mark the exact
places where bibliography cleanup, source URLs, generated tables, or reviewer
decisions are still needed.

## Lab Notes Structure

Create `docs/research/lab-notes/README.md` as the entry point. It should state
the current status, reading order, source-of-truth boundaries, and review
status for each chapter.

Create chapter files with stable numeric prefixes:

- `01-product-boundary.md`: project purpose, public/research surfaces, medical
  boundary, current estimate, and non-estimates.
- `02-data-provenance.md`: source families, raw-vs-derived publication rules,
  artifact vintages, source caveats, checksums/provenance audit role, and
  redistribution boundaries.
- `03-methods-modeling.md`: annual forecast branches, model comparison,
  forecast-safe rules, regional research branches, spatial regimes, and update
  policy.
- `04-plain-language-stats.md`: "reported incidence per 100k", predicted
  score, forecast percentile, typical/worse-than-average language, empirical
  intervals, and how to explain the chart marks.
- `05-validation-results.md`: rolling-origin validation, MAE/RMSE/bias,
  branch comparison, calibration backtests, Bayesian update backtests,
  observed-fit overlays, and promotion gates.
- `06-regional-research.md`: Mid-Atlantic research scope, county-equivalent
  geography, cross-border adjacency, spatial-regime summaries, regional
  forecast intervals, and public-default caveats.
- `07-limitations-review-register.md`: overclaim risks, known stale docs,
  source gaps, HITL decisions, and reviewer findings.
- `appendix-source-map.md`: map each chapter claim to existing docs, public
  data artifacts, code modules, tests, and evidence packs.

The dossier should use short front-matter blocks for each chapter:

```markdown
Status: draft | reviewed | needs update
Primary sources: docs/model-spec.md; public/research-data/regional/model_card.json
Reviewer focus: methods/statistics | scientific/data-quality | product-boundary
Last checked against commit: actual git commit at chapter authoring time
```

The commit hash must be filled by the implementation slice using the actual
repository state at authoring time.

## Public Whitepaper Structure

After the lab notes exist and receive at least one reviewer pass, create a
public whitepaper folder with:

- `README.md`: title, abstract, audience, status, and link to the live product.
- `01-executive-summary.md`: plain-language project summary and boundaries.
- `02-background-related-work.md`: Lyme risk mapping, surveillance lag,
  per-bite literature, and prior public tools.
- `03-data-and-provenance.md`: source families, artifact vintages, data
  quality, and public/private redistribution boundary.
- `04-methods.md`: annual forecast target, seasonal allocation, score scale,
  percentile/typicality, uncertainty, and update policy.
- `05-results-and-validation.md`: branch comparisons, validation diagnostics,
  and regional research evidence.
- `06-limitations-and-ethics.md`: medical boundary, surveillance caveats,
  source limitations, privacy, and communication risk.
- `07-reproducibility.md`: commit, commands, public artifacts, and verification.
- `references.md`: citation list and bibliography status.

The public whitepaper should be written only after the corresponding lab-note
chapters exist, so the polished document does not drift away from the internal
evidence record.

## Source Material

The first lab-note pass should synthesize, not duplicate, these existing files:

- `README.md`
- `docs/vision-scope.md`
- `docs/software-requirements-spec.md`
- `docs/model-background.md`
- `docs/model-spec.md`
- `docs/data-sources.md`
- `docs/data-manifest.md`
- `docs/etl-pipeline.md`
- `docs/architecture.md`
- `docs/public-product-boundary.md`
- `docs/regional-research-evidence.md`
- `docs/literature-review.md`
- `docs/research-report-tools-assessment.md`
- `api/api-spec.md`
- `public/data/model_card.json`
- `public/data/source_catalog.json`
- `public/data/static_export_manifest.json`
- `public/research-data/regional/model_card.json`
- `public/research-data/regional/source_catalog.json`
- `public/research-data/regional/static_export_manifest.json`

The source map appendix should also point to code and tests for method claims,
including the model comparison, annual forecast, regional forecast, risk score,
forecast typicality, forecast interval, seasonality, and provenance modules.

## Reviewer Workflow

Use a multiagent authoring workflow when chapters can be reviewed
independently. Reviewer roles:

- Documentation inventory reviewer: checks that the chapter cites the relevant
  existing docs and avoids stale duplicates.
- Methods/statistics reviewer: checks score, percentile, interval, validation,
  and model wording.
- Scientific/data-quality reviewer: checks surveillance caveats, source
  limitations, medical boundary, and overclaim risk.
- Synthesis editor: resolves reviewer comments into coherent prose and keeps
  chapter language consistent.

Reviewer outputs should be captured in `07-limitations-review-register.md` or
inline review notes inside each chapter. Reviewers should not silently rewrite
methods or promote research branches. Promotion decisions remain HITL.

## Plain-Language Statistical Contracts

The lab notes must define these terms before the public whitepaper uses them:

- Reported incidence per 100k: reported Lyme case counts divided by population,
  scaled per 100,000 residents. It is a surveillance proxy, not true infections.
- Annual forecast: predicted county-year reported-incidence pressure from a
  named model branch and forecast origin.
- Weekly seasonal risk: annual forecast allocated across MMWR weeks using CDC
  national Lyme onset seasonality. It is not observed county-week truth.
- Predicted score: a 1-10 relative display score derived from predicted weekly
  incidence and the selected scale denominator, rounded and clamped. It is not
  a probability.
- Forecast percentile: where the annual forecast falls relative to the same
  county's prior reported annual incidence history through the forecast origin.
- Forecast interval: an empirical range based on historical forecast residuals
  for reported-incidence forecasts. It is not a medical confidence interval,
  posterior infection interval, or certainty about an individual bite.

These contracts should appear in lab notes before being reused in public page
copy or the whitepaper.

## Documentation Hygiene

The first lab-note slice should record known documentation conflicts rather
than hiding them. Current known issues include:

- `CITATION.cff` appears to describe a Bayesian per-bite Lyme-risk engine for
  the United States, which conflicts with the current Maryland-first relative
  reported-incidence forecast boundary.
- `docs/install-local.md` may mention older FastAPI/PyMC assumptions that do
  not match the current static/CLI product.
- `review/2026-buildability-review.md` appears stale compared with the current
  implemented ETL, modeling, CLI, and public artifacts.
- Several deliberate local duplicate files with `" 2"` suffixes are untracked
  and should not be normalized or committed without explicit human approval.

Fixing documentation metadata such as `CITATION.cff` can be a later
implementation task, but the lab-note review register should capture the risk
immediately so no public whitepaper inherits the old claim.

## HITL Gates

Human approval is required before:

- Promoting a regional research branch as public default.
- Changing medical or CDC guidance wording beyond source-backed public-health
  guidance.
- Claiming personal infection probability, true Lyme burden, or treatment
  recommendations.
- Deleting, normalizing, or committing deliberate local duplicate/untracked
  files.
- Publishing the public whitepaper as release-ready.
- Changing citation metadata in a way that implies a new product claim.

The agent can continue autonomously on internal organization, drafting,
source-map construction, and reviewer passes until it reaches one of these
gates.

## Verification

Documentation slices should be verified with:

- Markdown presence/static checks where already available.
- Link/path checks for referenced local files.
- Grep checks for forbidden or risky phrases such as "true incidence",
  "infection probability", "diagnosis", "treatment recommendation", and
  "confidence interval" when they are not explicitly negated or caveated.
- Reviewer passes for methods/statistics and scientific/data-quality caveats.
- Existing full test/lint workflow when documentation changes are combined with
  code, public data, or citation metadata changes.

The lab notes do not need a running web server. The public whitepaper may later
need rendered preview checks if it is exposed through the static site.
