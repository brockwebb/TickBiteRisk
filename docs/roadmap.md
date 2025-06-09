# tickbiterisk – roadmap

> **File location:** `/docs/roadmap.md`

---

## milestone tracking

We use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

* **MAJOR** – new disease modules or breaking API changes
* **MINOR** – new features (ML covariates, dashboards) backward‑compatible with `/risk`
* **PATCH** – bug fixes, doc tweaks, CI plumbing

---

## release ladder

| Version                          | Target date | Scope                                                                           | Success metric                                          |
| -------------------------------- | ----------- | ------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **v0.1.0** *(repo scaffold)*     | 2025‑06‑15  | Vision, docs, CI lint/unit pipeline, sample data; no full model yet             | CI green on push; docker compose up downloads sample DB |
| **v0.2.0** *(etl prototype)*     | 2025‑07‑01  | All fetch scripts functional; PostGIS loads raw + processed tables              | `make etl-mini` completes on fresh clone                |
| **v0.3.0** *(core Bayesian fit)* | 2025‑07‑15  | Annual MCMC for θ + p(τ) logistic; CLI risk calc on two counties                | Spearman ρ > 0.4 vs 2023 CDC cases (mini set)           |
| **v1.0.0** *(MVP release)*       | 2025‑08‑31  | Full CONUS priors 2025 season; /risk API; React+D3 dashboard; nightly/weekly CI | Public Docker image; Zenodo DOI; arXiv paper posted     |
| **v1.1.0** *(ML extension)*      | 2025‑Q4     | Gradient‑boosted λ covariates: trail density, night‑lights trend, WUI growth    | ΔRMSE ≥ 10 % over v1.0 baseline; SHAP report published  |
| **v1.2.0** *(multi‑pathogen)*    | 2026‑Q1     | Extend model to *Anaplasma* & *Babesia*; multi‑label p(τ) curves                | Joint risk API `/risk?pathogen=bb,ap` returns array     |
| **v2.0.0** *(mobile & offline)*  | 2026‑Q3     | React‑Native app using SQlite snapshot; offline per‑bite calc at campsites      | App beta in TestFlight/Play; <30 MB APK                 |

---

## kanban columns (github projects)

* **Backlog** – ideas w/o assignee
* **Next up** – slated for next sprint
* **In progress** – PR open
* **Review** – awaiting maintainer review
* **Done** – merged to `main`

---

## good‑first‑issue queue

| Issue                                                                          | Label              | Est. effort |
| ------------------------------------------------------------------------------ | ------------------ | ----------- |
| Add unit test for `validate_fips` util                                         | `good first issue` | <½ hr       |
| Write `fetch_snow.sh` to sum NOAA IMS snow‑days                                | `help wanted`      | 2 hrs       |
| Add county lookup CLI (`tickbiterisk fips --state MD --county "Anne Arundel"`) | `good first issue` | 1 hr        |

---

*Last updated: 2025‑06‑08 (draft v0.1)*
