# TickBiteRisk Vision And Scope

## Mission

TickBiteRisk turns messy tickborne disease and ecology data into a transparent
Maryland-first risk context product. The current system helps people compare
relative county-week seasonal Lyme risk and understand the evidence behind the
score.

This is not a per-bite infection probability, diagnosis, treatment
recommendation, or weather-adjusted forecast.

## Current v0 scope

The current v0 scope is deliberately narrower than the long-term idea:

- Maryland county-level public dashboard.
- A relative county-week seasonal Lyme baseline on a 1-10 scale.
- Local CLI lookup and static JSON export from derived artifacts.
- Normalized ETL for CDC Lyme, Maryland surveillance, NOAA weather, Census
  population, deer harvest, land-cover/habitat proxies, tick vector/pathogen
  status, and CDC seasonality data.
- Model comparison across transparent baseline, empirical-Bayes shrinkage, and
  ridge-style annual incidence branches.
- Plain-language risk interpretation, source links, and CDC guidance links.
- Public-safe GitHub Pages deployment with no runtime secrets and no raw data
  redistribution.

The v0 dashboard answers: "Compared with other Maryland county-weeks in the
data product, how elevated is the seasonal Lyme baseline here?"

It does not answer: "Did this specific tick bite infect me?"

## Out of current scope

- Personal medical advice, diagnosis, prophylaxis decisions, or treatment
  recommendations.
- Bite-specific calculations using tick attachment duration, tick testing, or
  individual symptoms.
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
- Per-bite infection probability models using tick species, stage, attachment
  duration, and pathogen prevalence.
- Live API or conversational interfaces that ask only medically relevant,
  plain-language questions.
- Multi-pathogen extensions for anaplasmosis, babesiosis, ehrlichiosis,
  spotted fever rickettsiosis, Powassan, and tularemia where data support it.
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

Last updated: 2026-05-27.
