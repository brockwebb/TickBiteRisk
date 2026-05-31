# Limitations Review Register

Status: draft
Primary sources: docs/public-product-boundary.md; docs/regional-research-evidence.md; CITATION.cff; docs/install-local.md; review/2026-buildability-review.md
Reviewer focus: scientific/data-quality
Last checked against commit: 28d23f9

This chapter tracks the highest-risk overclaims, stale or conflicting documentation, source and citation gaps, HITL gates, reviewer findings, and follow-up decisions that must be resolved before public whitepaper promotion.

## Highest-Risk Overclaims

Current review should guard against language that turns a relative reported Lyme pressure forecast into Bayesian per-bite risk, personal infection probability, true Lyme burden, medical advice, or a guarantee about individual exposure outcomes.

- Do not claim personal infection probability, true Lyme burden, medical
  advice, diagnosis, or treatment recommendation.
- Do not promote a regional research branch as public default without HITL
  approval.

Additional high-risk language to avoid:

- describing reported cases as stable true Lyme incidence;
- treating CDC seasonality allocation as observed county-week truth;
- treating regional forecast intervals as clinical intervals or posterior draws;
- applying calibration or Gamma-Poisson Bayesian update factors to public forecasts while all overall rows remain gated `do_not_apply_to_public_forecast`.

## Prior Resolved Documentation Findings

`CITATION.cff` previously overclaimed Bayesian per-bite Lyme risk and national
personal-risk coverage compared with the current relative reported-incidence
forecast boundary. Task 9 replaced that metadata with Maryland-first relative
reported Lyme pressure wording and explicit non-medical, non-probability
caveats.

`docs/install-local.md` previously described a FastAPI/PyMC/Postgres laptop
stack as the main setup path. Task 9 replaced it with the current maintained
CLI/static-dashboard quick start and moved the older stack to a historical
install path.

`review/2026-buildability-review.md` remains historical feasibility context.
Task 9 marked it as superseded by the current ETL/modeling/CLI/static-dashboard
implementation so it is not cited as current product status.

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
- Task 6 documentation-inventory review found stale source-map references to old runtime/test paths. Resolution: source-map references were updated to `tickbiterisk/runtime/risk_lookup.py`, `tickbiterisk/runtime/static_export.py`, `tests/test_runtime_risk_lookup.py`, `tests/test_cli_risk_lookup.py`, `tests/test_seasonality.py`, `tests/test_cli_seasonality.py`, and `tests/test_single_bite_risk.py`.
- Task 6 methods/statistics review found no blocking issues after checking score, percentile, interval, validation, and forecast-safe wording against `risk_score.py`, `regional_forecast_typicality.py`, and regional interval code.
- Task 6 scientific/data-quality review found no blocking issues in surveillance caveats, medical boundary, regional research framing, or public-default guardrails.
- Task 9 public-doc alignment resolved stale metadata/docs: `CITATION.cff` now describes the current Maryland-first relative reported-incidence forecast; `docs/install-local.md` now leads with the implemented CLI/static quick start; and `review/2026-buildability-review.md` is marked historical rather than current product status.

## Follow-Up Decisions

Follow-up decisions before public whitepaper promotion:

- keep `CITATION.cff`, `docs/install-local.md`, and `review/2026-buildability-review.md` aligned with the current relative reported-incidence forecast boundary if product scope changes;
- reconstruct `paper/refs.bib` and connect bibliography entries to the source map;
- decide whether regional research artifacts remain internal review material or receive a separately approved public research framing;
- keep calibration and Bayesian update methods research-only until rolling-origin gates improve error or calibration.
