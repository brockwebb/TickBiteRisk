# TickBiteRisk – System Overview

```mermaid
flowchart TB
    subgraph Data_Feeds
        A1[CDC Tick Surveillance CSV] -->|annual| ETL1
        A2[Deer Collisions (FARS)] -->|annual| ETL1
        A3[NSSP ED Tick‑Bite Visits] -->|weekly| ETL2
        A4[NLCD 30 m Land‑Cover] -->|static| ETL1
        A5[ACS Population Density] -->|annual| ETL1
    end

    ETL1[Annual ETL \n (fetch + clean)] --> DWH[(PostGIS Warehouse)]
    ETL2[Weekly ETL \n (fetch + clean)] --> DWH

    subgraph Model_Fitting[Bayesian Engine]
        F1[fit_theta.py \n(Beta–Binomial CAR)]
        F2[fit_lambda.py \n(Seasonal GP + scaler)]
    end
    DWH --> F1 --> PostTheta[(theta_{i})]
    DWH --> F2 --> PostLambda[(lambda_{i,t})]

    subgraph API
        API1[/risk?fips&tau] --> FastAPI
        FastAPI --> JSON[Probability + 95% CI]
    end
    PostTheta & PostLambda --> FastAPI

    subgraph Front_ends
        Dash[React+D3 Dashboard] --> User
        CLI[CLI \n tickbiterisk query] --> User
    end
    JSON --> Dash
    JSON --> CLI
```

*Legend*

* **ETL scripts** live in `/data-pipelines/` and run via cron or GitHub Actions.
* **PostGIS Warehouse** holds raw + cleaned tables; sizing \~500 MB/year.
* **Model‑Fitting container** (PyMC) re‑estimates priors annually (`fit_theta.py`) and weekly scalers (`fit_lambda.py`).
* **FastAPI** container serves `/risk` endpoint; hot‑reloads new priors on disk.
* **Front‑ends** consume JSON; no business logic outside API.

## Data Flow by Cadence

| Cadence            | Component          | Output table            |
| ------------------ | ------------------ | ----------------------- |
| Annual (Nov)       | `update_theta.sh`  | `theta_prior_YYYY`      |
| Weekly (Mon 02:00) | `update_lambda.sh` | `lambda_weekly_isoXXXX` |
| Real‑time          | API                | Prob & CI JSON          |

## Deployment Footprint

* **Docker‑Compose** orchestrates three services: `postgres`, `pymc_fit`, `fastapi_app`.
* **Storage:** <2 GB for 10‑year archive.
* **CPU:** Annual fit \~15 min on modern laptop; weekly scaler <30 s.
* **Memory:** 4 GB RAM sufficient for full MCMC.

## Security & Rate‑Limiting

* FastAPI served behind `uvicorn --limit-concurrency 10`.
* Optional Nginx reverse proxy enables TLS & IP throttling.

---

*Last updated: 2025‑06‑08 (draft v0.1)*
