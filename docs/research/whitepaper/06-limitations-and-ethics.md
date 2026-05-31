# Limitations And Ethics

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Highest-Risk Overclaims

Current review should guard against language that turns a relative reported
Lyme pressure forecast into Bayesian per-bite risk, personal infection
probability, true Lyme burden, medical advice, or a guarantee about individual
exposure outcomes.

This whitepaper must not claim personal infection probability, true Lyme
burden, medical advice, diagnosis, or treatment recommendation. It must not
promote a regional research branch as a public default without HITL approval.

Additional high-risk language to avoid includes:

- describing reported cases as stable true Lyme incidence;
- treating CDC seasonality allocation as observed county-week truth;
- treating regional forecast intervals as clinical intervals or posterior
  draws;
- applying calibration or Gamma-Poisson Bayesian update factors to public
  forecasts while all overall rows remain gated
  `do_not_apply_to_public_forecast`.

## Medical And Public-Health Boundary

TickBiteRisk may provide informational context and link to official guidance,
but medical decisions belong to qualified healthcare professionals and public
health authorities. Product language must not override clinician judgment,
diagnose disease, recommend treatment, or imply that a low score makes symptoms
safe to ignore.

The single-bite overlay may organize user-supplied tick evidence and explain
CDC prophylaxis-consideration criteria. It remains decision-support context,
not a medication instruction, diagnosis, or absolute infection-probability
estimate.

## Data And Evidence Gaps

Important data and evidence gaps remain:

- observed county-week and county-month Lyme outcomes are absent;
- reported surveillance is not complete latent Lyme burden;
- regional sidecars and state overlays have different geographies, report
  dates, definitions, suppression rules, and provisional caveats;
- forecast-year population denominators may use flagged projections until
  official estimates are available;
- ecology, exposure, host, weather, and syndromic signals are candidate
  features or diagnostics unless a reviewed branch explicitly selects them;
- formal bibliography reconstruction is incomplete because `paper/refs.bib` is
  missing.

Regional interval summaries can be useful planning aggregates, but they are
not posterior draws or a joint spatial probability model. Forecast intervals
describe uncertainty around the modeled reported-incidence proxy, not medical
certainty for a person or a bite.

## Reviewer Findings

Current reviewer findings that remain controlling for public interpretation:

- calibration backtest rows include 288 metric rows, with all 12 overall rows
  gated `do_not_apply_to_public_forecast`;
- Gamma-Poisson Bayesian update rows include 288 metric rows, with all 12
  overall rows gated `do_not_apply_to_public_forecast`;
- PA 2024 observed-fit overlay evidence remains partial and diagnostic, with
  `partial_state_overlay`, `not_training_feature`, `not_public_default`,
  `reported_cases_not_stable_true_incidence`, and
  `not_public_maryland_default` caveats;
- regional interval summaries are planning aggregates, not posterior draws or
  a joint spatial probability model;
- stale public metadata, install, and buildability docs were corrected to the
  current Maryland-first relative reported-incidence forecast boundary.

## Human-In-The-Loop Gates

HITL review is required before promoting regional research branch findings,
changing medical boundary language, or treating exploratory diagnostics as
public product evidence.

Current HITL gates include:

- public promotion of any regional research branch or non-default Maryland
  branch;
- risk color scale, top-coding, default map scope, or chart-scope changes;
- medical, CDC guidance, diagnosis, treatment, prophylaxis, or clinician-facing
  wording changes;
- source and license review for required inputs and public redistributable
  artifacts;
- public whitepaper claims about model validity, uncertainty, personal risk, or
  coverage;
- committing, deleting, staging, or normalizing deliberate untracked local
  files.

Backtests, model cards, and source catalogs can support these decisions, but
they do not replace human review.

## Publication Boundary

This chapter records limitations for a working whitepaper draft. It is not a
release approval. Before public whitepaper promotion, the project still needs
formal bibliography reconstruction, source/license review, public-health or
clinician wording review where appropriate, and a decision about whether
regional research artifacts remain internal review material or receive a
separately approved public research framing.
