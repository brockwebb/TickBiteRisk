# Ecology Host-Dynamics (Mast / Deer) Data Dead-End

Status: draft
Primary sources: `cc_tasks/2026-06-01_ecology-data-scoping_RESULTS.md` (LabNotebookEntry `22e63dd4`); `cc_tasks/2026-06-01_wv-mast-magnitude-diagnostic_RESULTS.md` (LabNotebookEntry `6d728f41`); on-disk inventory (`build/etl/mast/`, `build/etl/deer-harvest/`, `data/raw/ecology/`); the well-established eastern-US acorn-masting → rodent → infected-nymph Lyme literature
Reviewer focus: this is a DATA dead-end, not a biology refutation; and the scope (ecology excluded *as a usable covariate now*, not "ecology doesn't matter")
Last checked against commit: working tree 2026-06-02 (commit `21f4631`)

## Decision

The ecology arm — acorn mast and deer as covariates for the six-state annual Lyme forecast — is **closed for now as data-limited**. No usable ecology covariate exists at the resolution, coverage, and lag the fit needs, and none is cheaply acquirable in bounded effort. This is a documented dead-end with the same rigor as the out-of-region DiD-control foreclosure (lab note 08) — a *negative identification result*, not an unattempted search.

The scope is load-bearing: this note does **not** claim ecology is irrelevant to Lyme. The mast → mouse/chipmunk irruption → larval bloodmeal → infected-nymph (~2-year lag) pathway is the best-established multi-year driver of eastern-US Lyme incidence, and the ~2-year lag is exactly the pathway the weather checks (lags 0–1 only; lab note 10) could not test. The arm was worth checking. The finding is that **the available data lack the coverage and spatial resolution to detect it** — biology supported, signal undetectable here.

## The question

Can acorn mast (a proxy for the reservoir-host/rodent pathway that carries the *Borrelia* infection dynamics) — or deer — serve as a covariate for the six-state annual Lyme-incidence forecast at the ~2-year lag the masting mechanism predicts?

Deer was **scoped out by user decision**, and the framing is honest about why: deer is the adult-tick reproductive host (long-lived, mobile, buffered against single-year acorn swings), a *weak* proxy for the infection-amplifying step. Mast proxies the reservoir-host pathway — the step that actually carries infection — and was the primary candidate.

## What was tried (two investigations; re-derived from disk, not inherited)

1. **Six-state ecology-data scoping** (`22e63dd4`). On-disk inventory across all six states, plus a bounded acquisition desk-check. Both mast and deer are **Maryland-only** on disk (`build/etl/mast/` = 4 western-MD study-plot counties, flagged `western_maryland_only, study_plot_not_countywide`, 2013–2021; `build/etl/deer-harvest/` = 23/24 MD counties, 2011–2025). The five non-MD states have **zero** ecology data on disk. The acquisition machinery (`mast_acorn.py`, `deer_harvest.py`, …) was built and exercised for Maryland only.
2. **WV ecoregion mast→incidence diagnostic** (`6d728f41`). WV was the case study (it has the richest state mast survey: a numeric index by 6 ecoregions × elevation since 1971). The diagnostic was designed at the ecoregion-year grain (mast varies at region × year, not county) with a 2-year lag, single-digit effective region-years — explicitly a directional diagnostic, never an establishing fit.

## The finding (scoped): two independent data walls

**1. Resolution.** Mast is measured as a **qualitative regional/site index**, never county quantities — MD on disk (4 study plots), and PA/VA/WV by desk-check (VA ~33 hard-mast *sites* since the 1950s; WV "all regions"; PA regional ratings). A county annual incidence fit cannot take a regional index as a county covariate; mast could only ever enter as a *regional synchronous index*. Deer is at the right unit in some states (VA by county since 1947) but heterogeneous — **PA reports by Wildlife-Management-Unit, not county**; DC has no program — so a six-state county deer series would be a lossy, multi-source extraction.

**2. Coverage/acquisition.** The WV diagnostic could not even be **constructed**: the numeric ecoregion index tables are **image-based** in every report (text extraction yields footers only; OCR not installed), and only the 2020/2021/2024/2025 reports are web-accessible (inconsistent URLs; pre-2020 404s; pre-2019 needs a WVDNR data request). The 2-year lag into the assessable 2017–2021 incidence segment needs mast **2015–2019** — precisely the inaccessible pre-2020 reports → essentially one obtainable mast year → no diagnostic. The only segment with obtainable mast (2022–2023, via 2020–2021 mast) is **n=2, direction-only, indeterminate**. Verdict: **INDETERMINATE — data-limited at acquisition.**

**3. The n-ceiling (binds even with full data).** 6 ecoregions × ~5 annual points per definition-stable segment, with a 2-year lag, is single-digit effective region-years. Even a complete WV mast series could support only a *directional* diagnostic, never an establishing effect or a shippable covariate. County pooling would be pseudoreplication and was refused.

## Consistency with the broader picture

The masting → rodent → nymph mechanism is real and well-supported; nothing here refutes it. What the data foreclose is *using it as a covariate in this product at this resolution*. This mirrors lab note 10's weather conclusion from the other direction: weather was testable but null/confounded for annual magnitude; ecology has the mechanistically-right lag but is **untestable here for lack of county-resolution, fit-window-covering data**. Together they close the weather/ecology correlation arc with no validated covariate.

## Scoped conclusion (the earned decision)

1. **Ecology is excluded as a forecast covariate for now** — data-limited, not biology-limited. Mast is unavailable at county resolution anywhere; the WV ecoregion diagnostic is unconstructable without inaccessible pre-2020 reports; deer is scoped out and would be heterogeneous/lossy regardless.
2. **`weather_mode=not_used` and the absence of an ecology term are both earned scoping**, not gaps to apologize for. The forecast remains the seasonally-allocated lagged-incidence baseline.
3. **Revival path (recorded, not pursued):** a WVDNR data request for the 2013–2019 ecoregion mast index (or a machine-readable export of the long-term series) + an OCR pass on the image tables would enable the WV *directional* diagnostic; a multi-state county deer-harvest extraction (VA/WV/DE county, PA WMU→county apportionment) would enable a deer diagnostic. Both remain capped at directional by the n-ceiling. Until a data acquisition closes the resolution/coverage gap, the arm stays closed.

## What this does NOT close

Nothing about the biology of acorn masting, rodent reservoirs, or tick host dynamics — only their viability as covariates given the data available today. If county-resolution mast or a clean multi-state deer series is ever acquired, the directional diagnostic is worth revisiting; this note is the data dead-end, not a mechanism verdict.
