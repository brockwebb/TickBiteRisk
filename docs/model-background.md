# TickBiteRisk – Model Background & Design Rationale

> **File location:** `/docs/model-background.md`

This document explains **why** TickBiteRisk is built on a Bayesian state‑space framework, how each prior is constructed, and why alternatives (frequentist GLM, black‑box ML) were rejected for v1.

---

## 1 Why Bayesian?

| Requirement                                                     | Frequentist limitation                               | Bayesian advantage                                                                                                    |
| --------------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Sparse tick-testing data** (60 % of U.S. counties have n = 0) | GLM yields infinite SE or forces imputation          | Hierarchical **CAR prior** borrows strength from neighbors and covariates, giving finite θᵢ with wide—but honest—CrI. |
| **Irregular data feeds** (weekly ED visits may drop out)        | GLM must drop rows or carry last obs forward         | State‑space filter: when `y` missing, model falls back to process prior and automatically widens λᵢ,t uncertainty.    |
| **Need real-time updates without retraining**                   | Re‑estimate full model or refit GLM each week        | Posterior becomes new prior; incremental ADVI update <30 s.                                                           |
| **End‑user uncertainty communication**                          | CI often misinterpreted; p‑values irrelevant to risk | Credible interval directly states 95 % probability risk is within bounds; easy for clinicians.                        |
| **Composability with ML v2**                                    | Difficult to inject priors into XGBoost              | Bayesian λ layer can accept ML‑generated covariate priors seamlessly.                                                 |

---

## 2 Construction of the three priors

### 2.1 θᵢ : Infected‑nymph prevalence

1. **Likelihood** `yᵢ ∼ Binom(nᵢ, θᵢ)` from CDC tick CSV.
2. **Linear predictor** on logit scale with covariates: deer crashes, dog serology, forest‑edge density.
3. **Spatial smoothing** via BYM2/CAR random effect (`ρ`, `σ²`) on county adjacency graph.
4. **Priors** `α₀, αⱼ ∼ Normal(0,2)`, `ρ ∼ Uniform(0,1)`, `σ ∼ HalfNormal(1)`.

Outcome: even if `nᵢ = 0`, θᵢ draws center on ecologically plausible estimates with wide dispersion.

### 2.2 λᵢ,t : Human–tick encounter intensity

* **Seasonal backbone** `f_season(t)` = Fourier(2) fitted to historical ED scaler.
* **Observation model** `ED_visits ∼ NegBinom(g(λᵢ,t))` where `g` maps λ to expected visits.
* **Weekly scaler** `EDScaler = log(visits_this_week / baseline)`. When missing >14 d, variance inflated (`σ_miss`).

### 2.3 p(τ) : Attachment‑time transmission curve

* Logistic form pooled from Piesman 1988, Eisen 2018 meta‑analysis: `γ₀ ~ Normal(-7,1)`, `γ₁ ~ Normal(0.10,0.02)`.
* Gives median p(24h)=1 %, p(48h)=10 %, p(72h)=55 % in line with controlled studies.

---

## 3 Updating mechanics

1. **Annual** – full NUTS MCMC on θ; refresh Fourier coefficients for λ.
2. **Weekly** – incremental ADVI on β₁ (ED scaler) with latest visits; θ frozen.
3. **Query time** – FastAPI pulls latest NetCDF posterior and computes `P = 1 − (1−θp(τ))ᵏ` on the fly.

---

## 4 Why not ML‑only (v1)?

| Concern                         | ML‑only outcome                             | Bayesian outcome                                 |
| ------------------------------- | ------------------------------------------- | ------------------------------------------------ |
| Interpretability for clinicians | SHAP plots, but per‑bite math opaque        | Direct probability formula with traceable priors |
| Data hunger                     | Needs dense labels (county‑week Lyme cases) | Works with sparse tick + ED proxies              |
| Real‑time update cost           | Re‑train boosted model weekly               | ADVI update <30 s                                |

ML covariates will arrive in **v1.1** (λ prior enhancement) but Bayesian core remains unchanged.

---

## 5 Key references

* Gelman A. et al. *Bayesian Data Analysis* 4e (2021)
* Besag J., York J., Mollié A. (1991) “Bayesian image restoration”
* Piesman J. & Sinsky R. (1988) “Ability of nymphal Ixodes dammini to transmit Lyme disease after different attachment times.”
* Eisen R. & Eisen L. (2018) “Duration of tick attachment and Borrelia transmission.”

---

*Last updated: 2025-06-08 (draft v0.1)*
