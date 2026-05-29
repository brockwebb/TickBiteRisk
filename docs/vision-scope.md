# TickBiteRisk Vision And Scope

## Mission

TickBiteRisk turns messy tickborne disease and ecology data into a transparent
Maryland-first risk context product. The current system helps people compare
relative county-week seasonal Lyme risk and understand the evidence behind the
score. It also provides a single-bite Lyme decision-support score for organizing
post-bite evidence against CDC prophylaxis consideration criteria.

This is not an absolute infection probability, diagnosis, treatment
recommendation, or same-year weather-adjusted forecast.

## Current v0 scope

The current v0 scope is deliberately narrower than the long-term idea:

- Maryland county-level public dashboard.
- A relative county-week seasonal Lyme forecast on a 1-10 scale.
- A single-bite Lyme decision-support score that uses tick species/stage,
  attachment time, engorgement, removal timing, and doxycycline safety fields.
- Local CLI lookup and static JSON export from derived artifacts.
- Normalized ETL for CDC Lyme, Maryland surveillance, NOAA weather, Census
  population, deer harvest, land-cover/habitat proxies, tick vector/pathogen
  status, and CDC seasonality data.
- Model comparison across transparent baseline, empirical-Bayes shrinkage,
  analog, ridge-style, and random-forest research annual incidence branches.
- Plain-language risk interpretation, source links, and CDC guidance links.
- Public-safe GitHub Pages deployment with no runtime secrets and no raw data
  redistribution.

The v0 dashboard answers: "Compared with other Maryland county-weeks in the
data product, how elevated is the seasonal Lyme forecast here?"

The v0 single-bite CLI answers: "Given what I know about this attached tick,
how elevated is my Lyme concern score, and which CDC consideration criteria are
met, not met, or uncertain?"

The project is Maryland-first, not Maryland-only. A future regional iteration
should test WV, VA, PA, DE, and Washington, DC if data availability, county or
county-equivalent geography, and source terms support the same transparent
validation standard.

## Out of current scope

- Personal medical advice, diagnosis, prophylaxis decisions, or treatment
  recommendations.
- Determining whether a specific bite infected someone.
- Using tick testing or individual symptoms as model inputs.
- National county coverage.
- Live API service, user accounts, or server-side runtime.
- Claims that prevention campaigns or clinical behavior caused observed
  changes unless intervention data are explicitly modeled.

## Stakeholders

| Stakeholder | Current need |
| --- | --- |
| Outdoor residents and visitors | Plain-language local seasonal context and links to official guidance |
| County health educators | Evidence-backed timing and geography for prevention messaging |
| Clinicians and public health staff | A transparent situational-awareness artifact, not a clinical rule |
| Data collaborators | Reproducible ETL, source manifest, model comparison outputs, and caveats |

## Future research scope

The broader research question remains valuable: can geography, ecology,
weather, tick surveillance, and bite-specific evidence be combined into a
defensible estimate of disease risk after a tick encounter?

Future work may test:

- Bayesian hierarchical disease incidence models.
- Calibrated absolute infection probability models using tick species, stage,
  attachment duration, and pathogen prevalence.
- Live API or conversational interfaces that ask only medically relevant,
  plain-language questions.
- Multi-pathogen extensions for anaplasmosis, babesiosis, ehrlichiosis,
  spotted fever rickettsiosis, Powassan, and tularemia where data support it.
- Mid-Atlantic expansion into West Virginia, Virginia, Pennsylvania, Delaware,
  and the District of Columbia/Washington, DC, so a larger ecological and
  surveillance region can challenge the current Maryland-only model.
- Bayesian update and hierarchical branches that can ingest newly observed
  outcomes without leaking future data and must beat the transparent baselines
  in rolling-origin backtests before any public promotion.
- Temporal exploration views that let users compare year-over-year patterns,
  seasonal shifts, and apparent spatial movement without treating those
  patterns as proof of tick migration or individual exposure.
- Intervention-aware models for public health campaign planning.

Those ideas stay labeled as research until validation, clinical wording, and
public-health review support them.

## Guiding principles

1. Transparency before sophistication.
2. Conservative interpretation before scary precision.
3. Source provenance on every derived public artifact.
4. Accessibility and plain language in the first release, not as a later polish
   pass.
5. Clear separation between informational risk context and medical guidance.

Last updated: 2026-05-29.
