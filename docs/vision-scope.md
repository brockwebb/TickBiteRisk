# TickBiteRisk – Vision & Scope

## 1  Mission

Provide an open‑source, evidence‑based engine that translates complex tick‑borne disease surveillance data into an intuitive **per‑bite risk estimate** for Lyme disease (and, eventually, other pathogens), helping individuals, educators, and public‑health practitioners make informed decisions.

## 2  Problem Statement

*Existing tools either map regional Lyme incidence **or** offer qualitative bite advice; none combine live ecological data with bite‑specific factors to yield a quantified probability.*  This leaves clinicians guessing, outdoor enthusiasts confused, and educators without reproducible demos.

## 3  Project Goals

| Goal                                                        | Success metric                                                                           |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Accurate** per‑bite probability within credible intervals |  Validated against CDC county case counts (ρ > 0.6) and published prophylaxis trial data |
| **Live** weekly updates                                     |  Automated ETL refreshes 95 % of counties without manual intervention                    |
| **Open & reproducible**                                     |  Build + fit + serve risk API with a single `docker compose up`                          |
| **Educational**                                             |  High‑school notebook tutorial completes in < 15 min on free Colab                       |
| **Extensible**                                              |  Modular design allows drop‑in of new pathogens or ML covariates                         |

## 4  Scope

### In Scope

* Bayesian state‑space model for Lyme disease (U.S. counties)
* Data feeds: CDC Tick Surveillance, FARS deer collisions, NSSP tick‑bite ED visits, NLCD land‑cover, population from ACS
* FastAPI JSON API and minimal React/D3 demo site
* Dockerised ETL + model pipeline; nightly/weekly cron scripts
* Documentation, notebooks, and permissive licensing (MIT code, CC‑BY data)

### Out of Scope (v1)

* Pathogens other than *Borrelia burgdorferi*
* Sub‑county (census‑tract) resolution
* Advanced ML (GNN, boosted trees) – reserved for v2 paper
* Smartphone apps or offline mobile bundles

## 5  Stakeholders & Personas

| Persona                     | Key need                                                     |
| --------------------------- | ------------------------------------------------------------ |
| **Outdoor Adult**           | “Tick bit me yesterday—do I need doxycycline?”               |
| **Scout Leader / Educator** | Hands‑on STEM activity analysing local tick risk             |
| **County Health Officer**   | Weekly bulletin on rising tick activity to inform advisories |
| **Data Scientist**          | Transparent code & data to extend or replicate findings      |

## 6  Guiding Principles

1. **Transparency over performance.** Readable Bayesian modelling choices trump marginal speed gains.
2. **Public‑domain first.** Use U.S. federal datasets wherever possible; keep external sources clearly licensed.
3. **Defensive uncertainty.** Always show credible intervals and flag forecast vs observed inputs.
4. **Modularity.** Separate ETL, model fitting, and API layers so each can evolve independently.
5. **Education usability.** Every component should run on a free cloud notebook within classroom time limits.

## 7  MVP Definition

Deliver county‑level posterior θ & λ tables for the 2025 season, a `/risk` endpoint that accepts `fips`, `tau_hours`, and returns probability + CI, along with one HTML dashboard and one tutorial notebook.

## 8  Roadmap Snapshot (v1 → v1.1)

1. **v1.0** – Core Bayesian model, Lyme only, weekly ED scaler.
2. **v1.1** – Add ML deer/land‑use covariates, extend to Babesia.

## 9  Risks & Mitigations

| Risk                                | Mitigation                                                                   |
| ----------------------------------- | ---------------------------------------------------------------------------- |
| Data feed outages (NSSP)            | Seasonal GP fallback + uncertainty inflation                                 |
| Misinterpretation as medical advice | Prominent disclaimers; encourage consultation with clinicians                |
| Licensing conflicts (dog serology)  | Fetch but do **not** redistribute CC‑BY‑NC data; instruct users to self‑pull |

---

*Last updated: 2025‑06‑08 (draft v0.1)*
