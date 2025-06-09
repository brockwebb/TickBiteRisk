# TickBiteRisk – Literature Review & Gap Analysis

> **File location:** `/docs/literature-review.md`

This document records the peer‑reviewed and public‑health work surveyed while designing **TickBiteRisk**.  It demonstrates that—despite abundant research on Lyme ecology and mapping—**no existing system quantitatively fuses county‑level infected‑tick prevalence with bite‑specific attachment‑time factors in a live, openly reproducible tool**.  References are stored in `paper/refs.bib` using the citation keys shown below.

---

## 1 Search strategy

* **Databases:** PubMed, Scopus, Google Scholar (Jan‑2000 → Mar‑2025)
* **Strings:** `("Lyme" OR "Borrelia") AND ("risk model" OR "Bayesian" OR "spatial" OR "tick bite" OR "per‑bite" OR "attachment time")`
* **Grey literature:** CDC, USGS, Johns Hopkins Lyme Dashboard, CAPC maps, TickEncounter program
* **Inclusion:** U.S. data (or methods generalisable to U.S.), quantitative model or dashboard, English.
* **Exclusion:** purely clinical symptom predictors, European *Ixodes ricinus*–only studies unless model transferable.

---

## 2 Key classes of prior work

### 2.1 Geospatial incidence or hazard models (population‑level)

| Year | Citation key       | Scale              | Data streams                | Method                   | Key finding                                       |
| ---- | ------------------ | ------------------ | --------------------------- | ------------------------ | ------------------------------------------------- |
| 2006 | chen2006\_bayesNY  | New York counties  | CDC cases + land‑cover      | Bayesian Poisson CAR     | Forest edge & deer density raise incidence        |
| 2017 | watson2017\_canine | CONUS counties     | 11.9 M dog tests + env.     | Bayesian spatio‑temporal | Canine serology predicts emerging human hot spots |
| 2021 | curriero2021\_jhu  | National dashboard | CDC cases + ticks + climate | Descriptive GIS          | First One‑Health Lyme map but no bite calc        |
| 2024 | kulisz2024\_poland | Polish poviats     | Cases + verts + climate     | BYM2                     | Forest & host density drivers                     |

*Gaps:* models stop at environmental hazard; none output per‑bite probability; code seldom OSS.

### 2.2 Per‑bite outcome studies

| Year | Citation key         | N bites | Predictors                  | Model                     | Result                              |
| ---- | -------------------- | ------- | --------------------------- | ------------------------- | ----------------------------------- |
| 1992 | costeffect1992\_nejm | 587     | Tick engorgement            | Cost‑effect + frequentist | \~1‑5 % risk in endemic areas       |
| 1997 | sood1997\_longisland | 37      | Attachment hrs, engorgement | Observational             | 0/37 <36 h bites infected           |
| 2017 | hofhuis2017\_plos    | 3 531   | PCR status, τ, engorgement  | Structural eq.            | High engorgement × +PCR → 14 % risk |

*Gaps:* great bite‑level signal but no geography; European *I. ricinus* rather than U.S. *I. scapularis*.

### 2.3 Integrated / One‑Health pilots

| Year | Citation key         | Region    | Integration                    | Public tool?      | Limitation                    |
| ---- | -------------------- | --------- | ------------------------------ | ----------------- | ----------------------------- |
| 2023 | bouchard2023\_quebec | S. Quebec | Behaviour survey + tick hazard | Internal web tool | No per‑bite calc; Canada only |

### 2.4 Real‑time public dashboards

| Platform                           | Owner    | Data                       | Output          | Shortcoming                |
| ---------------------------------- | -------- | -------------------------- | --------------- | -------------------------- |
| CDC Tick Surveillance              | CDC      | County tick & pathogen CSV | Interactive map | No bite‑level risk         |
| Johns Hopkins Lyme & TBD Dashboard | JHU      | Cases + env rasters        | Map overlays    | Descriptive only           |
| TickEncounter “TickSpotters”       | Univ. RI | User‑submitted photos      | Email advice    | Not open; qualitative risk |

---

## 3 Synthesis of gaps

| Requirement for TickBiteRisk                                      | Status in prior art                                              |
| ----------------------------------------------------------------- | ---------------------------------------------------------------- |
| County‑level **θ** (infected‑nymph prevalence) with uncertainty   | Only raw CDC counts; no hierarchical smoothing                   |
| Weekly **λ** (human–tick exposure)                                | Absent; first attempt uses NSSP ED feeds                         |
| Bite‑specific **p(τ)** logistic integrated with geographic priors | Not present anywhere                                             |
| OSS code + reproducible builds                                    | Rare (Watson 2017 shares code privately; most dashboards closed) |
| Live cron‑driven updates                                          | None outside flu/COVID domains                                   |

Therefore, TickBiteRisk occupies an untouched intersection: **Bayesian fusion of live ecological priors and dose‑response bite factors, delivered as open, reproducible software.**

---

## 4 Reference list (ordered by citation key)

```bibtex
@article{chen2006_bayesNY,
  title={Spatio‑temporal analysis of Lyme disease},
  author={Chen, X. and others},
  journal={Epidemiology},
  year={2006}
}
@article{hofhuis2017_plos,
  title={Predicting Borrelia infection after tick bites},
  journal={PLOS ONE},
  year={2017}
}
@article{watson2017_canine,
  title={Bayesian mapping of canine Lyme seroprevalence},
  journal={PLOS ONE},
  year={2017}
}
@article{curriero2021_jhu,
  title={A One‑Health dashboard for tick‑borne diseases},
  journal={Prev Chronic Dis},
  year={2021}
}
@article{bouchard2023_quebec,
  title={Integrating behaviour into Lyme risk maps},
  journal={Ticks Tick‑borne Dis},
  year={2023}
}
```

(Full BibTeX in `paper/refs.bib`.)

---

*Last updated: 2025‑06‑08 (draft v0.1)*
