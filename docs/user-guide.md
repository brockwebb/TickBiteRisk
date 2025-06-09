# TickBiteRisk – User Guide

> **File location:** `/docs/user-guide.md`

---

## 1 What does TickBiteRisk tell me?

When you plug a U.S. county FIPS code and a tick’s attachment time (τ) into the API or dashboard, TickBiteRisk returns:

| Field                            | Meaning                                                                                                         |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `risk`                           | Posterior mean probability the bite transmits Lyme disease.                                                     |
| `ci95`                           | 95 % credible interval—our uncertainty band.                                                                    |
| `theta_source` / `lambda_source` | Whether the model used **observed** data this week, a short **forecast**, or last season’s **static** baseline. |
| `last_*_update`                  | Dates when the infected‑tick prior (θ) and exposure scaler (λ) were last refreshed.                             |

> **Interpretation tip** If the upper CI is below 1 %, risk is very low. If the lower CI exceeds 3 %, most physicians consider single‑dose doxycycline prophylaxis reasonable.

---

## 2 Why attachment time matters (biology in 90 s)

* Lyme bacteria live in the tick’s mid‑gut.  They need **≈24 h of feeding** before migrating to the salivary glands.
* Lab studies (Piesman 1988; Eisen 2018) show <2 % transmission at 24 h, ≈10 % at 48 h, >50 % by 72 h.
* Prompt removal is therefore the single biggest risk‑reducer.  TickBiteRisk encodes this with a logistic p(τ) curve.

---

## 3 How is this different from other tools?

| Tool                             | What you get                    | Why it falls short for *per‑bite* questions                     |
| -------------------------------- | ------------------------------- | --------------------------------------------------------------- |
| **CDC County Lyme Map**          | Dots sized by human case counts | Tells *where* Lyme occurs but not your bite’s probability.      |
| **CDC Tick Surveillance Map**    | County % of infected ticks      | Lacks attachment time; no personal risk number.                 |
| **Johns Hopkins Lyme Dashboard** | Multi‑layer GIS overlays        | Descriptive only; no API, no bite factors.                      |
| **TickEncounter “TickSpotters”** | E‑mail risk rating after photo  | Manual expert advice, qualitative (“high”) and not open‑source. |
| **CAPC Dog Lyme Map**            | Canine seroprevalence heat map  | Dogs ≠ humans; no attachment time or weekly updates.            |

**TickBiteRisk** merges the *infection prevalence* information from maps with the *attachment‑time* science and updates weekly—then gives you a single probability + uncertainty.

---

## 4 API cheat‑sheet

```bash
# Basic query: one tick, 24 h, Anne Arundel County, MD
curl 'https://api.tickbiterisk.org/risk?fips=24003&tau=24'

# Two ticks (12 h and 36 h) from Pike County, PA, historical July baseline
curl 'https://api.tickbiterisk.org/risk?fips=42103&tau=12&tau=36&k=2&date=2024-07-15'
```

Dashboard users simply pick county and drag the τ slider; the CI band updates in real time.

---

## 5 Caveats & responsible use

* **Not medical advice.**  Probabilities guide discussion with your clinician; they do not diagnose or prescribe.
* Accuracy depends on feed freshness: check the `*_source` flags.
* Lone‑star or dog ticks transmit *other* diseases; TickBiteRisk currently covers only *Ixodes* and Lyme.

---

*Last updated: 2025‑06‑08 (draft v0.1)*
