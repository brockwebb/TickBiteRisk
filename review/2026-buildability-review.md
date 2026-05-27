# TickBiteRisk 2026 Buildability Review

Assessed: 2026-05-23

Question: Given that this idea was roughly a 2024 thought experiment, could this system be easily built today?

## Short Answer

Yes, the system is much easier to build today as an open-source research MVP or educational demo.

No, it is still not "easy" if the goal is a clinically defensible, continuously updated decision-support system. The coding is now the tractable part. The hard parts are data provenance, county-level pathogen prevalence, validation against surveillance outcomes, licensing, and risk communication.

My practical read: a focused MVP could be built in weeks by one strong builder using modern geospatial Python, PyMC, FastAPI, and AI-assisted coding. A public-health-grade v1 would still be a multi-month effort because it needs careful data agreements, model validation, clinician-facing disclaimers, and ongoing maintenance.

## What Exists In This Repo Today

The project is currently a well-developed spec, not a runnable product. The README describes Docker, PyPI, API, and model behavior, but the repo only contains docs, an API spec, licensing, and project governance files. That is fine for a concept-stage repo, but the buildability review should treat those quick-start sections as intended product behavior rather than existing implementation.

Strong existing assets:

- Clear mission: county-level per-bite Lyme risk with uncertainty.
- Model framing: `theta_i` tick infection prevalence, `lambda_i,t` encounter intensity, `p(tau)` attachment-time dose response.
- API shape: a simple `/risk` endpoint with county FIPS, attachment duration, date, and credible intervals.
- Sensible architecture split: ETL, Bayesian model, API, dashboard.
- A data-source catalog that is close to the right ingredients.

Main spec gaps:

- The repo assumes county-level tick testing counts (`y_i`, `n_i`) are easy to obtain. The current public CDC county workbooks are more status-oriented than count/prevalence-oriented.
- The repo assumes weekly ED tick-bite data can be pulled into a county-level scaler. Current public CDC tracker data is presented by HHS region, week/month, age, and sex, so county-level allocation would be a model assumption unless another source is obtained.
- The README currently implies a working package and Docker stack that are not present in the repository.

## What Changed Since Around 2024

The basic ingredients are more consolidated now than they were two years ago.

- CDC now publishes tick surveillance data sets behind its tick dashboards, including county status for blacklegged and western blacklegged ticks through December 31, 2025 and county pathogen status for multiple Ixodes-borne pathogens.
- CDC's Tick Bite Data Tracker remains a public-facing weekly signal based on NSSP emergency department data.
- Annual NLCD has matured beyond static 2021 land cover: MRLC describes Annual NLCD products for CONUS spanning 1985-2024 at 30-meter resolution, with programmatic/cloud access paths.
- NHTSA's Crash API provides FARS access from 2010 onward in CSV/XLSX/JSON-like formats, making deer-collision proxy extraction less annoying than old bulk-file-only workflows.
- Census ACS 5-year data is available through 2024 via API, including geographies below county level.
- Bayesian tooling is better. PyMC stable docs now expose multiple NUTS backend options (`pymc`, `nutpie`, `blackjax`, `numpyro`), which makes model prototyping and performance tuning less fragile.
- AI-assisted development can now scaffold ETL, tests, API schemas, dashboards, and docs quickly. It does not remove the need for validation, but it compresses the boilerplate phase.

## Data Feasibility

| Data need | Current feasibility | Notes |
| --- | --- | --- |
| County tick presence | Good | CDC public county files classify Ixodes status. Good for map context and priors. |
| County pathogen presence | Good for status | CDC public files identify whether pathogens have been found in host-seeking Ixodes ticks by county. |
| County pathogen prevalence (`y_i / n_i`) | Mixed | The model wants counts or percent-positive nymphs. Current public dashboard datasets inspected from CDC are status fields, not straightforward county-level nymph-tested and nymph-positive counts. This is the biggest data reality check. |
| Weekly bite activity | Good at regional level | CDC Tick Bite Tracker uses NSSP data and is updated weekly, but public granularity is HHS region/week/month/age/sex, not every county. |
| Lyme case validation | Good but lagged | CDC NNDSS Lyme surveillance data is available for reported cases, with lag and known reporting limitations. |
| Land cover | Strong | Annual NLCD now provides annual CONUS 30 m land cover and tree/impervious products. |
| Population covariates | Strong | ACS API covers 5-year data through 2024. |
| Deer proxy | Usable but noisy | FARS is accessible, but fatal deer crashes are sparse and biased. It may be better as a weak covariate than a central exposure driver. |
| Canine serology | Useful but constrained | CAPC is highly relevant, but licensing and sampling bias make it better as optional local input or a non-redistributed covariate. |

## Is The Core Model Easy Now?

The MVP model is easy enough. A first version can compute:

```text
risk = theta_county * p_transmission(attachment_hours)
```

with uncertainty bands from a simple beta prior and a logistic dose-response curve.

The robust model is not easy. A county CAR model plus seasonal exposure layer is manageable in PyMC, but the model can become false precision if it invents county-level values from region-level ED data and status-only tick surveillance. The system should explicitly label each estimate with a `theta_source` and `lambda_source` such as:

- `observed_prevalence`
- `status_imputed`
- `regional_borrowed`
- `forecast`
- `insufficient_data`

That one design choice would make the system much more honest.

## Product Feasibility

A good first product should not try to replace clinical judgment. It should position itself as:

- an educational risk estimator,
- a transparent research model,
- a way to show uncertainty around local tick-bite risk,
- a companion to CDC/IDSA guidance, not a treatment recommendation engine.

Current CDC guidance still emphasizes prompt removal, symptoms follow-up, and caution around tick testing. IDSA/AAN/ACR guidance recommends prophylaxis only for identified high-risk Ixodes bites, within 72 hours of removal, using criteria that include endemic area and attachment for at least 36 hours. TickBiteRisk should reflect those guardrails rather than outputting a naked "take doxycycline" answer.

## Build Difficulty By Version

| Version | Time estimate | Difficulty | What it includes |
| --- | --- | --- | --- |
| Demo notebook | 2-5 days | Easy | Hard-coded counties, simple risk formula, public docs, sample outputs. |
| Local API MVP | 2-4 weeks | Moderate | ETL for stable sources, county lookup, static `theta`, logistic `p(tau)`, FastAPI endpoint, tests. |
| Research MVP | 4-8 weeks | Moderate-hard | Bayesian prevalence model, uncertainty propagation, validation notebook, reproducible mini-pipeline. |
| Public v1 | 3-6 months | Hard | Full ETL, source monitoring, defensible data provenance, dashboards, disclaimers, validation, release automation. |
| Clinical-grade decision support | 6-12+ months | Very hard | Expert review, prospective validation, governance, legal/privacy review, human-factors testing, clinical integration. |

## Recommended 2026 Build Strategy

1. Build the simple estimator first.

   Implement `/risk` with FIPS, date, attachment duration, and stage/species inputs. Return probability, interval, source labels, and a warning if a county is status-imputed rather than prevalence-observed.

2. Decouple prevalence from exposure.

   Treat `theta_i` as "probability this tick is infected if it is an Ixodes tick from this county." Treat `lambda_i,t` as "encounter intensity" only for dashboards and seasonal context. A person who already has a tick bite mostly needs `theta_i * p(tau)`, not ambient encounter rate.

3. Replace the CDC prevalence assumption.

   Update the data-source docs to say CDC public tick/pathogen files are status-first. If actual county `n_tested` and `n_positive` fields are available through a separate CDC, state, or research data path, document that source explicitly. Otherwise use hierarchical imputation and label it as such.

4. Keep CAPC optional.

   CAPC canine data is useful but should not be required for the open-source default path unless licensing is fully settled. Keep the fetch-local-only approach.

5. Add a validation notebook before a React dashboard.

   The project will be more credible if it first shows calibration against CDC reported Lyme cases and known prophylaxis trial baselines. The dashboard can come after the core estimate is honest.

6. Make the API conservative.

   Return both a numeric risk and a guideline-oriented category, but avoid direct treatment instructions. Include "not medical advice" and "consult a clinician" metadata in the response contract.

## What I Would Change In The Existing Specs

- `README.md`: mark Docker/PyPI quick starts as planned until code exists.
- `docs/data-sources.md`: revise CDC tick surveillance row from "% positive nymphs" to "county status; prevalence counts require separate source/confirmation."
- `docs/etl-pipeline.md`: replace "CDC GitHub raw link" for ED visits with a verified tracker endpoint or a manual export/derived-data plan.
- `docs/model-spec.md`: add source-quality flags and an explicit imputation layer for status-only pathogen surveillance.
- `api/api-spec.md`: add `tick_species`, `tick_stage`, `theta_source`, `data_quality`, and `clinical_disclaimer` fields.
- `docs/roadmap.md`: make v0.1 a runnable static estimator before committing to a full CAR/GP model.

## Bottom Line

This is more buildable today than it was in 2024. The combination of public federal dashboards, annual land-cover products, mature Bayesian tooling, and AI-assisted engineering makes the MVP very realistic.

But the honest version is not "press a button and ship." The key challenge is not writing FastAPI or fitting PyMC. It is converting incomplete surveillance signals into a trustworthy county-level probability without pretending the data are better than they are.

The best 2026 path is to build a transparent, source-labeled MVP first, then earn complexity only after the data inputs and validation prove they can support it.

## Sources Checked

- CDC Tick Surveillance Data Sets: https://www.cdc.gov/ticks/data-research/facts-stats/tick-surveillance-data-sets.html
- CDC Tick Bite Data Tracker: https://www.cdc.gov/ticks/data-research/facts-stats/tick-bite-data-tracker.html
- CDC NSSP dashboards overview: https://www.cdc.gov/nssp/php/data-research/dashboards/index.html
- CDC Lyme Disease Surveillance Data: https://www.cdc.gov/lyme/data-research/facts-stats/surveillance-data-1.html
- CDC How Lyme Disease Spreads: https://www.cdc.gov/lyme/causes/index.html
- CDC What to Do After a Tick Bite: https://www.cdc.gov/ticks/after-a-tick-bite/index.html
- IDSA/AAN/ACR Lyme disease guideline: https://www.idsociety.org/practice-guideline/lyme-disease/
- NHTSA Crash API: https://crashviewer.nhtsa.dot.gov/CrashAPI
- MRLC Annual NLCD FAQ: https://www.mrlc.gov/faq
- Census ACS data via API: https://www.census.gov/programs-surveys/acs/data/data-via-api.html
- PyMC sampling docs: https://www.pymc.io/projects/docs/en/stable/api/generated/pymc.sample.html
- Johns Hopkins Lyme and Tickborne Diseases Dashboard: https://www.hopkinslymetracker.org/about
- CAPC parasite prevalence maps context: https://capcvet.org/articles/parasite-prevalence-maps/
