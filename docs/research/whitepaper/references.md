# References

Draft status: working draft derived from internal lab notes in
`docs/research/lab-notes`; not publication-ready.

## Formal bibliography status

This is a working reference register, not a final bibliography.
This page does not claim a complete literature review. It should not be
treated as publication-ready until a human reviewer reconstructs formal
citations, confirms source versions, checks licenses, and restores the missing
`paper/refs.bib` bibliography referenced by older project notes.

The current purpose is narrower: keep every whitepaper claim tied to a local
evidence record, source family, artifact, or review-needed method area.

## Project evidence record

Primary internal evidence is maintained in:

- `docs/research/lab-notes/appendix-source-map.md`: claim-to-source map for
  product boundary, data provenance, annual forecasts, seasonal allocation,
  score scale, forecast percentile, forecast intervals, validation, regional
  research, and medical-risk communication boundaries.
- `docs/data-sources.md`: current source catalog, candidate source inventory,
  redistribution boundary, and known data gaps.
- `docs/data-manifest.md`: source-level acquisition, ETL, materialization,
  checksum, redistribution, and caveat register.
- `docs/public-product-boundary.md`: public-safe data publication rule,
  runtime data shape, CDC guidance links, and clinical-disclaimer boundary.
- `docs/model-spec.md`: selected public branch, research lanes, feature
  families, validation approach, and forecast update contract.
- `docs/regional-research-evidence.md`: Mid-Atlantic spatial-regime,
  interval, observed-fit, and update-backtest evidence pack with HITL
  promotion boundary.
- `public/data/model_card.json`: public Maryland model card for the selected
  `linear_blend_baseline` county-week seasonal forecast.
- `public/research-data/regional/model_card.json`: regional research model
  card for the Mid-Atlantic `empirical_bayes_spatial_regime_incidence` branch.

## Official public-health and surveillance sources

The formal bibliography should cite, at minimum, the official source families
already tracked in the local manifest:

- CDC Lyme public-use aggregated geography files and CDC Lyme dashboard exports
  that provide county/state/region reported Lyme surveillance counts and
  rates. These are the main reported-outcome spine and reconciliation sources.
- CDC national Lyme onset seasonality source material, represented locally by
  `cdc_lyme_seasonality`, used to allocate annual forecasts into MMWR-week
  display rows. This is a static national seasonality prior, not county-week
  observed Lyme truth.
- CDC tick guidance for post-bite action, prevention, symptoms, and clinician
  prophylaxis-consideration context. Public copy may link to CDC guidance but
  must not diagnose disease or recommend treatment.
- CDC tick vector and pathogen county status workbooks, currently treated as
  feature candidates and source-status context rather than direct disease
  truth.
- Maryland Department of Health Lyme disease data, currently used for the
  2024 Maryland outcome lane with explicit `mdh_probable_only_2024` and
  `state_source_not_cdc_public_use` caveats.

## Population, geography, and environmental sources

The formal bibliography should cover these denominator, boundary, weather, and
ecological source families before any release-ready methods claim:

- Census population estimates, Census county reference files, and Census
  TIGERweb county geometry used for population denominators, county metadata,
  boundary support, and regional adjacency.
- Census PEP age/sex and ACS residential-form exposure-context summaries,
  currently research-only human-exposure proxies rather than tick-bite counts.
- NOAA daily weather, NOAA CPC ONI, NOAA PSL MEI.v2, Open-Meteo recent
  backfill, and U.S. Drought Monitor artifacts, all treated as weather or
  climate context candidates unless a branch is explicitly promoted.
- EPA EnviroAtlas, NLCD/MRLC land cover, Census Building Permits Survey, and
  Maryland DNR deer harvest and mast/acorn reports, each requiring careful
  source-version and feature-meaning review before plain-language claims.

## State and regional source leads

The Mid-Atlantic research branch has sidecar and validation sources that should
be cited only with their role clearly stated:

- Pennsylvania DOH 2024 county Lyme workbook, used as an optional state-source
  overlay and observed-fit diagnostic, not the public Maryland default.
- Virginia VDH reportable disease locality data, Delaware DHSS Lyme county
  table, West Virginia OEPS vectorborne summaries, New Jersey DOH reportable
  tickborne statistics, Massachusetts DPH monthly tickborne reports, and Maine
  JMMC tickborne trend review, each tracked as a validation sidecar, regional
  stress-test input, or external comparator rather than a selected public model
  truth source.
- NSSP coverage artifacts and future ED/tick-bite feed candidates, which are
  feasibility or acquisition leads and not current tick-bite counts.

## Method and validation source needs

The methods bibliography remains HITL work. It should include sources for the
statistical and communication choices currently documented in code and lab
notes:

- Sources for rolling-origin validation and leakage control for county-year
  forecasts.
- Empirical Bayes shrinkage and spatial or regional prior models for sparse
  county surveillance data.
- Plain-language explanation of empirical Bayes methods, especially when a
  county forecast is partially pulled toward a broader prior.
- Forecast interval construction from historical residuals, with language that
  distinguishes a forecast interval from a medical confidence interval or
  per-bite infection probability.
- Forecast percentile and typicality communication: the percentile compares a
  selected annual forecast with prior county reported-incidence history, not
  with biological certainty or individual infection risk.
- Risk-scale communication for a capped 1-10 predicted score, including why a
  display cap is not a clinical threshold.
- Surveillance-regime and case-definition-change handling, including why
  reported Lyme incidence is a proxy for relative disease pressure rather than
  complete latent Lyme burden.

## Current Citation Boundary

Whitepaper chapters may cite this register as an internal evidence index, but
publication-facing citations still need human review. Until that review is
complete, the research whitepaper should continue to say that it is a working
draft built from `docs/research/lab-notes`, model cards, source catalogs, and
generated manifests.
