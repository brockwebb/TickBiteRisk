# Product Boundary

Status: draft
Primary sources: README.md; docs/vision-scope.md; docs/public-product-boundary.md; api/api-spec.md
Reviewer focus: product-boundary
Last checked against commit: 45e3f7f

This chapter will define the current TickBiteRisk product boundary before public promotion: what the Maryland public surface supports, what the regional research surface is allowed to show, and which decisions require human review before any broader claims are made.

## Current Product Boundary

TickBiteRisk is a Maryland-first public information and research product. The
current implemented surface combines a relative Maryland county-week Lyme
forecast, plain-language model/source context, and a local single-bite
decision-support command. It is built from derived artifacts, not from a live
clinical service or a public API.

TickBiteRisk currently forecasts relative reported Lyme disease pressure. It
does not estimate whether a specific person is infected, does not diagnose
disease, and does not recommend treatment.

The current public score answers a narrow question: compared with other
Maryland county-weeks in the product, how elevated is the seasonal Lyme
forecast for this county and week? It should be described as informational risk
context and as a reported-incidence proxy, not as direct tick abundance,
infected tick prevalence, or individual exposure history.

## Public Maryland Surface

The public Maryland surface is the dashboard and static JSON bundle under
`public/`, plus the local runtime commands that read the same derived risk
files. Its public default is a relative county-week Lyme forecast for Maryland
counties. The weekly view allocates an annual county forecast across CDC MMWR
weeks with CDC national Lyme onset seasonality; it is not observed
county-week Lyme truth.

The public static export selects one explicit forecast branch, score scale, and
seasonality source. Current source catalogs identify the selected branch as a
derived annual forecast with preserved `forecast_origin_year`,
`data_cutoff_date`, `source_vintage`, and `update_mode`. Public files may carry
forecast intervals, quality flags, source citations, model cards, and county
metadata, but they should not imply that the model observed weekly county cases
or measured current-year weather-adjusted risk.

The Maryland dashboard remains the public default until a human review decides
otherwise. Stronger research branches, regional branches, or Bayesian update
lanes do not promote themselves into the public surface only because they rank
well in a backtest.

## Regional Research Surface

The regional research page and `public/research-data/regional/` artifacts are
research-only. They are useful for stress testing Mid-Atlantic data coverage,
spatial-regime ideas, forecast typicality, interval displays, and neighboring
county context. They are not the Maryland public default.

Regional rows may include DE, DC, MD, PA, VA, and WV county or
county-equivalent artifacts, plus state-source overlays and sidecars. Those
overlays are diagnostic context, not confirmed latent disease truth. They do
not replace the reconciled Maryland outcome target, and they do not justify
public regional claims without separate review of source terms, geography,
case definitions, suppression, and validation performance.

## Bite Guidance Overlay

The single-bite command uses the county-week forecast as local and seasonal
context, then organizes tick-specific evidence such as tick species, stage,
attachment duration, engorgement, removal timing, doxycycline safety, and tick
count. It may report a single-bite Lyme decision-support score and a summary of
CDC prophylaxis consideration criteria.

This overlay is context and criteria explanation. It is not diagnosis,
treatment advice, or an instruction to take or avoid medication. Unknown inputs
should remain uncertain instead of being converted into false certainty. The
score does not prove that a bite caused infection, and symptoms are not model
inputs.

## Medical And Public-Health Boundary

Medical decisions belong to qualified healthcare professionals and to official
CDC and public-health guidance. TickBiteRisk may link to CDC tick removal,
prevention, Lyme symptoms, and clinician guidance resources, but the product's
own language must stay informational and educational.

If a person has symptoms, is worried about a tick bite, or has questions about
prophylaxis or treatment, the product should direct them to CDC guidance and a
qualified healthcare professional. Product wording should not create a
clinical rule, override professional judgment, or imply that a low score makes
symptoms safe to ignore.

## What The Product Does Not Estimate

TickBiteRisk does not currently estimate:

- Whether a specific person is infected.
- Whether a specific tick transmitted Lyme disease.
- A calibrated absolute infection probability for an individual bite.
- A diagnosis, prognosis, treatment choice, or prophylaxis decision.
- Observed county-week or county-month Lyme cases.
- Observed county-week tick abundance or infected tick prevalence.
- Same-year weather-adjusted public risk.
- The causal effect of prevention campaigns, reporting changes, clinical
  behavior, or surveillance protocol changes unless those interventions are
  explicitly modeled and reviewed.

## Human Decisions Required Before Promotion

HITL review is required before any change that expands the product boundary or
changes public interpretation. At minimum, human review is required for:

- Promoting a branch into the public Maryland default.
- Promoting any regional research branch into a public regional product.
- Changing medical, symptom, prophylaxis, treatment, or clinician-facing
  wording.
- Adding or implying personal infection probability claims.
- Normalizing, publishing, staging, or committing raw or deliberately untracked
  local files.
- Publishing a release-ready whitepaper or public methodology narrative.
- Replacing the selected public branch with Bayesian, calibration, spatial,
  regional, weather, ecology, host, or exposure branches.

Backtests, model cards, and source catalogs can support those decisions, but
they do not replace them.
