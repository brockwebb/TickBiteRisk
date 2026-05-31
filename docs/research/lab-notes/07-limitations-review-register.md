# Limitations Review Register

Status: draft
Primary sources: docs/public-product-boundary.md; docs/regional-research-evidence.md; CITATION.cff; docs/install-local.md; review/2026-buildability-review.md
Reviewer focus: scientific/data-quality
Last checked against commit: 375a818

This chapter tracks the highest-risk overclaims, stale or conflicting documentation, source and citation gaps, HITL gates, reviewer findings, and follow-up decisions that must be resolved before public whitepaper promotion.

## Highest-Risk Overclaims

Current review should guard against language that turns a relative reported Lyme pressure forecast into Bayesian per-bite risk, personal infection probability, true Lyme burden, medical advice, or a guarantee about individual exposure outcomes.

- `CITATION.cff` appears to overclaim Bayesian per-bite Lyme risk and national
  personal-risk coverage compared with the current relative reported-incidence
  forecast boundary.
- Do not claim personal infection probability, true Lyme burden, medical
  advice, diagnosis, or treatment recommendation.
- Do not promote a regional research branch as public default without HITL
  approval.

Additional high-risk language to avoid:

- describing reported cases as stable true Lyme incidence;
- treating CDC seasonality allocation as observed county-week truth;
- treating regional forecast intervals as clinical intervals or posterior draws;
- applying calibration or Gamma-Poisson Bayesian update factors to public forecasts while all overall rows remain gated `do_not_apply_to_public_forecast`.

## Stale Or Conflicting Documentation

`docs/install-local.md` may mention older FastAPI and PyMC assumptions that do not match the current implemented ETL/modeling/CLI/static-artifact workflow. It should be checked before public installation instructions or architecture claims are copied into the whitepaper.

`review/2026-buildability-review.md` says the repository is a well-developed specification rather than a runnable product. That conflicts with the current implemented ETL, modeling, CLI, and static-dashboard artifacts. The buildability review may still be useful historical review context, but it needs a dated note or replacement before being cited as current status.

Older docs may also predate the current distinction between the Maryland public default, regional research page, single-bite decision-support overlay, calibration backtests, and Bayesian update backtests. Public-facing summaries should cite the current boundary docs instead of relying on stale overview language.

## Source And Citation Gaps

CITATION.cff and the source documentation should remain aligned with the datasets, code paths, and artifacts cited by any public-facing research narrative.

The bibliography is incomplete: `paper/refs.bib` is missing and needs reconstruction before a formal paper or whitepaper claims complete literature support. Any citation list should be rebuilt from the actual source inventory, CDC/public-health links, model-method references, and data-provenance documents used by the current artifacts.

Source and citation review should also verify redistribution boundaries for raw data, state-source overlays, derived public artifacts, CDC guidance links, and any generated static files included in the public dashboard.

## Human-In-The-Loop Gates

HITL review is required before promoting regional research branch findings, changing medical boundary language, or treating exploratory diagnostics as public product evidence.

Current HITL gates include:

- public promotion of any regional research branch or non-default Maryland branch;
- risk color scale, top-coding, default map scope, or chart-scope changes;
- medical, CDC guidance, diagnosis, treatment, prophylaxis, or clinician-facing wording changes;
- source and license review for all required inputs and public redistributable artifacts;
- public whitepaper claims about model validity, uncertainty, personal risk, or coverage;
- committing, deleting, staging, or normalizing deliberate untracked local files.

The research roadmap also requires validation against held-out surveillance, clinician or public-health review of wording, meaningful uncertainty intervals for the modeled quantity, source/license review, and plain-language warnings before future bite-specific probability work can move toward public use.

## Reviewer Findings

Open reviewer findings:

- Calibration backtest: 288 metric rows, all 12 overall rows gated `do_not_apply_to_public_forecast`; selected overall MAE rows worsened for `linear_blend_baseline`, `forecast_safe_top4_ensemble`, and `prior_year_incidence`.
- Gamma-Poisson Bayesian update backtest: 288 metric rows, all 12 overall rows gated `do_not_apply_to_public_forecast`; selected overall MAE rows worsened for the same branches.
- PA 2024 observed-fit overlay: useful partial diagnostic evidence, but caveated as `partial_state_overlay`, `not_training_feature`, `not_public_default`, `reported_cases_not_stable_true_incidence`, and `not_public_maryland_default`.
- Regional interval summaries: useful planning aggregates, but not posterior draws or a joint spatial probability model.

## Follow-Up Decisions

Follow-up decisions before public whitepaper promotion:

- revise or annotate `CITATION.cff` so it does not overstate Bayesian per-bite risk or national personal-risk coverage;
- refresh `docs/install-local.md` or clearly mark outdated FastAPI/PyMC assumptions;
- update or supersede `review/2026-buildability-review.md` with current runnable ETL/modeling/CLI/static-artifact status;
- reconstruct `paper/refs.bib` and connect bibliography entries to the source map;
- decide whether regional research artifacts remain internal review material or receive a separately approved public research framing;
- keep calibration and Bayesian update methods research-only until rolling-origin gates improve error or calibration.
