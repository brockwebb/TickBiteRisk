# County-Level Lyme Disease Case Data: Availability, Sources, and Data Request Procedures for Ten Low-Incidence States

## Executive Summary

For all ten target states (Georgia, South Carolina, Tennessee, Alabama, Kansas, Nebraska, Colorado, Utah, Missouri, Kentucky), county-level confirmed and probable Lyme disease case counts meeting CDC surveillance case definitions are **publicly available for 2017, 2018, 2019, and 2022–2023** via federal CDC datasets. No finalized public county-level dataset covers **2024** from any federal or state source as of May 2026. The primary federal sources have undergone a structural change: the 2016–2019 county XLSX has been **replaced** on the CDC geographic distribution page by a new **2019–2022 XLSX**, and the data.cdc.gov public-use FIPS datasets now extend through 2023.[^1][^2][^3][^4][^5][^6]

All ten states are classified as **low-incidence** by CDC (no state has ever met the ≥10 confirmed cases per 100,000 threshold for 3 consecutive years). Because these are low-incidence states, the post-2022 revised case definition has meaningful methodological consequences: high-incidence states may now report on lab evidence alone, while low-incidence states retain the clinical+lab requirement. This creates a pre/post-2022 comparability break, most dramatically illustrated by Kentucky (20–22 cases/year → 72–120 cases/year) and Kansas (30–40 cases/year → 9–12 cases/year).[^7][^8]

For suppressed county cells — the dominant problem for all ten states at their low case volumes — the appropriate remediation is a formal state DOH data request. Each state has a distinct procedure, detailed below.

***

## Part I: Federal CDC County-Level Data Infrastructure

### Current Dataset Architecture (as of May 2026)

Four federal datasets provide the county-level backbone for all ten states. Understanding which dataset is current — and what replaced what — is operationally essential.

#### Dataset A — Reported Tickborne Disease Cases by County of Residence, 2016–2019 (XLSX)
- **URL:** `https://www.cdc.gov/ticks/resources/Reported-Tickborne-Disease-Cases-by-County-of-Residence_2016-2019.xlsx`[^5]
- **Geographic level:** County (FIPS code)
- **Years:** 2016, 2017, 2018, 2019 (4-year aggregate totals per county, **not** year-by-year within the file)[^5]
- **Content:** Confirmed + probable combined counts; covers Lyme disease, SFR, babesiosis, ehrlichiosis, anaplasmosis, tularemia, undetermined ehrlichiosis/anaplasmosis[^5]
- **Status:** Still accessible at the URL above but **no longer listed as the primary download** on CDC's Geographic Distribution page[^2][^3]

#### Dataset B — Reported Tickborne Disease Cases by County of Residence, 2019–2022 (XLSX)
- **URL:** Listed on CDC's [Geographic Distribution of Tickborne Disease Cases](https://www.cdc.gov/ticks/data-research/facts-stats/geographic-distribution-of-tickborne-disease-cases.html) page as the current download[^2]
- **Geographic level:** County (FIPS code)
- **Years:** 2019, 2020, 2021, 2022 (4-year aggregate per county)
- **Content:** Same disease list as Dataset A; confirmed + probable combined
- **Critical note:** This file replaced Dataset A on the CDC geographic distribution page. It provides 2022 county data (the first year under the revised case definition) but aggregates all four years — discrete annual county counts for 2019–2022 individually are **not** separable from this file alone[^3][^2]
- **Companion file:** `AllTBD2022_Public.xlsx` (URL: `https://www.cdc.gov/ticks/media/files/2024/05/AllTBD2022_Public.xlsx`) provides **2022-only** county counts, supporting year-specific extraction for 2022[^9]

#### Dataset C — Lyme Disease Public Use Aggregated Data with Geography, 2008–2021 (data.cdc.gov)
- **URL:** `https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/qtbi-xd4i`[^4]
- **Geographic level:** County (5-digit FIPS), with demographic stratification (sex, age group, case status)
- **Years:** 2008–2021; covers target years **2017, 2018, 2019** (does not cover 2022–2024)[^4]
- **Case type:** Separate rows for **confirmed** and **probable** (Case_status column) — most analytically useful for pre-2022 years
- **Suppression:** Small cell counts suppressed per CDC privacy methodology (Lee et al., 2021) — most relevant limitation for the low-case states in this review[^4]

#### Dataset D — Lyme Disease Public Use Aggregated Data with Geography, 2022–2023 (data.cdc.gov)
- **URL:** `https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/x5j9-wybp`[^6]
- **Geographic level:** County (5-digit FIPS), same schema as Dataset C
- **Years:** 2022 and 2023[^6]
- **Case type:** Confirmed and probable (separate rows)
- **Last modified:** January 25, 2026[^6]
- **Same suppression rules** apply — county cells below the privacy threshold appear as "Suppressed"

### What Is NOT Available at County Level

| Gap | Details |
|-----|---------|
| **2024 county-level data** | No finalized public county-level dataset from CDC or any state covers 2024. CDC's most recently published surveillance data cover 2023[^1][^10]. The CDC Lyme surveillance page reports over 89,000 cases nationally in 2023 but no 2024 finalized data[^1] |
| **NNDSS/CDC WONDER county dimension** | State-level only for Lyme disease in the public WONDER interface; county is not queryable[^11][^12] |
| **Year-by-year breakdown in XLSX files** | Datasets A and B are multi-year aggregates; for discrete annual counts use Datasets C and D |
| **2020–2021 data quality** | CDC flags incomplete 2019 and 2020 data from some jurisdictions due to COVID-19 pandemic disruptions[^1][^13] |

***

## Part II: State-by-State Assessment

### 2.1 Georgia

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7][^8] |
| **State-level totals (CDC)** | 2017: 8 / 2018: 19 / 2019: 18 / 2022: 31 / 2023: 18 |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not publicly available |
| **Data type** | True reportable-disease case counts (confirmed + probable per CDC NNDSS case definitions)[^5] |
| **State DOH public source** | [Georgia DPH Lyme Disease page](https://dph.georgia.gov/epidemiology/zvbd/tbd/lyme) — informational only; no county dataset published[^14][^15] |
| **Suppression risk** | **Very high** — with 8–31 statewide cases/year, nearly all county cells in Datasets C and D will be suppressed |

**State data request procedure:** Georgia DPH operates the [Public Health Information Portal (PHIP)](https://dph.georgia.gov/phip-data-request), an online system requiring account creation and a structured data request form. Notifiable disease data including Lyme are captured in Georgia's SendSS (State Electronic Notifiable Disease Surveillance System). For unsuppressed county-level annual Lyme counts, submit a PHIP request specifying confirmed and probable Lyme cases by county of residence, 2017–2019 and 2022–2024. Contact: Georgia DPH Epidemiology Program, 1-866-PUB-HLTH (1-866-782-4584).[^16][^17][^18]

***

### 2.2 South Carolina

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 21 / 2018: 39 / 2019: 47 / 2022: 44 / 2023: 55 |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets; SC DPH dashboard updated through 2024[^19][^20] |
| **Data type** | True reportable-disease case counts (confirmed + probable) from SCION database[^20] |
| **State DOH source** | [SC DPH Lyme Disease Dashboard](https://dph.sc.gov/professionals/public-health-data/sc-tracking/tracking-lyme-disease-dashboard)[^21][^19] |
| **Suppression rule** | Cells <5 cases suppressed; rates also suppressed for cells <5[^20] |

**SC dashboard structure (important clarification):** The SC DPH metadata document clarifies the dashboard has two distinct data layers:[^20]
1. **Confirmed and probable Lyme case rates** — displayed at the **region level** (not individual county) from 2014–2024, aggregated into **5-year rolling rates**. The "Select Year" filter described on the navigation page controls the 5-year period displayed, not a single-year view.[^21]
2. **ED visits and hospitalizations** — from SC Revenue and Fiscal Affairs Office (ICD-10 code A69.2); this is **syndromic/administrative** data, not reportable disease case counts.[^20]

The dashboard does **not** expose discrete annual county-level case counts. For annual county Lyme counts, use federal Datasets C and D, or submit a state data request.

**State data request procedure:** Contact SC DPH Communicable Disease Epidemiology Section directly at **sctracking@dph.sc.gov**. Data are held in SCION (SCIONx). Request confirmed + probable Lyme cases by county of residence for 2017–2019 and 2022–2024. Reference CDES as the data owner; cite that the PHIP data request alternative is available for public health researchers.[^22][^23][^20]

***

### 2.3 Tennessee

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals** | 2017: 47 / 2018: 29 / 2019: 45 / 2022: 32 / 2023: 39 (TDH) / 50 (CDC)[^24] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets; TDH dashboard covers through most recent reported year |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^25][^24] |
| **State DOH source** | [TDH Interactive Disease Data Dashboard](https://www.tn.gov/health/ceds-weeklyreports/interactive-disease-data.html)[^25][^26] |
| **Suppression risk** | **Lower** than peer states — 29–50 statewide cases/year enables more county cells to remain unsuppressed |

**TDH dashboard capabilities:** The TDH Interactive Disease Data Dashboard allows county or regional-level views for selected diseases reported since 1995. The TDH vector-borne disease page confirms Lyme disease is tracked at county level and publishes a named top-15 county incidence list and an average annual incidence map (2013–2023). The TDH 2023 Lyme page notes 39 cases in 2023 and explicitly states expansion of blacklegged ticks into northeast and northern Tennessee. This state-level dashboard is the most operationally accessible for county-level annual counts among the ten target states.[^25][^26][^24]

**TDH data note (case count discrepancy):** The TDH 2023 total (39 cases) differs from the CDC-reported total (50 cases). This reflects the standard timing issue: states close their annual dataset at a different time than CDC, so final CDC counts may include additional late-arriving reports.[^10][^24]

**State data request procedure:** Contact TDH Division of Communicable and Environmental Diseases and Emergency Preparedness (CEDEP): **tn.health@tn.gov** or **(615) 741-7247**. Additional data or data elements not visible in the public dashboard may be requested by email or phone. TDH may require completion of a data release agreement for suppressed cell-level data.[^27][^28][^25]

***

### 2.4 Alabama

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^29] |
| **State-level totals (CDC)** | 2017: 41 / 2018: 36 / 2019: 66 / 2022: 32 / 2023: 36; 2024: 38 (ADPH dot map)[^30][^31] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets; ADPH 2024 dot map available[^30] |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^31] |
| **State DOH source** | ADPH [Tick-Borne Disease Data page](https://www.alabamapublichealth.gov/tick/data.html) — statewide case-by-year table (1988–2024) and annual dot-density maps by year (2007–2024)[^31][^32] |
| **State geographic granularity** | **Regional** (8 ADPH regions), not individual county, in dot maps[^30][^32] |
| **Suppression risk** | **Moderate** — 32–66 statewide cases/year; Dataset A shows county-level data is available for 2016–2019 aggregate with meaningful values for some counties[^5] |

**ADPH 2024 dot map confirmation:** The 2024 ADPH dot map confirms 38 Lyme disease cases statewide in 2024, displayed as single dots placed randomly within county of residence — this provides presence/absence at county resolution but not case counts. The maps are organized by ADPH administrative region (Jefferson, Mobile, Northeastern, Northern, Southeastern, Southwestern, West Central), not individual counties.[^30]

**State data request procedure:** ADPH provides a specific [Infectious Diseases and Outbreaks Data Request Form](https://www.alabamapublichealth.gov/data/requests.html). Submit this form requesting confirmed + probable Lyme disease cases by county of residence by year for 2017–2019, 2022, 2023, and 2024. ADPH also accepts public records requests via the [NextRequest portal](https://adph.nextrequest.com) under Alabama Code §36-12-40. For infectious disease data specifically, the dedicated data request form is the faster pathway.[^33][^34]

***

### 2.5 Kansas

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 40 / 2018: 30 / 2019: 35 / 2022: 9 / 2023: 12 |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^35] |
| **State DOH source** | [KDHE KEAP Tickborne Disease Portal](https://keap.kdhe.ks.gov/Ephtm/PortalPages/ContentData)[^36][^37] — interactive data story and EPHT map at county level |
| **KEAP data years** | KDHE EPHT metadata confirms the dataset covers **2016–2021**; no confirmation of post-2022 data in the portal[^35] |
| **Suppression risk** | **Very high post-2022** (9–12 statewide cases); moderate pre-2022 (30–40 statewide) |

**Post-2022 case definition impact:** The sharp drop from 35 cases (2019) to 9 cases (2022) in Kansas almost certainly reflects the revised 2022 case definition's differential impact on probable case classification in low-incidence states. Pre/post-2022 trend analysis for Kansas should flag this break.[^8][^7]

**KEAP portal limitation:** The KDHE EPHT Data Explorer URL (`maps.kdhe.ks.gov/ksepht`) does display Lyme disease at the county level with confirmed + probable cases but the underlying metadata confirms the dataset covers only **2016–2021**. Post-2021 county data are not publicly available via KEAP.[^36][^35][^38]

**State data request procedure:** KDHE Vital and Health Statistics team accepts special data requests. Requests involving programming and data analysis may incur a fee, and requests are subject to small-number suppression rules. Contact: **Email Health Statistics** (link at `www.kdhe.ks.gov/1348/Data-Requests`). Request confirmed + probable Lyme cases by county of residence for 2017–2019 and 2022–2024, citing NNDSS as the data source and referencing EpiTrax as the state surveillance system.[^39][^40]

***

### 2.6 Nebraska

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 14 / 2018: 15 / 2019: 10 / 2022: 9 / 2023: 5[^41] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets |
| **Data type** | True reportable-disease case counts[^41] |
| **State DOH source** | NDHHS publishes [statewide bar chart 2010–2023](https://dhhs.ne.gov/WNV%20Documents/Lyme%20Cases%20by%20Year%202010-2023.pdf)[^41] and [2023 Nebraska Tickborne Disease Report](https://dhhs.ne.gov/WNV%20Documents/Tick-borne%20Disease%20Report.pdf)[^42] — both statewide aggregate only |
| **State geographic granularity** | **State-level only** from NDHHS; no county public table |
| **Suppression risk** | **Extreme** — 5–15 statewide cases/year; virtually all county cells will be suppressed in Datasets C and D. Dataset A/B may show presence in 1–2 counties for higher-count years |

**Nebraska is the most data-constrained state in this review.** With statewide totals of 5–15 cases annually, county-level data in the federal FIPS aggregated datasets will be almost entirely suppressed. The AllTBD XLSX files (Datasets A and B) may provide county presence/absence for the few counties with ≥1 case, but will not recover suppressed cells.[^9][^5]

**State data request procedure:** Nebraska DHHS Office of Epidemiology: **dhhs.epi@nebraska.gov**, phone (402) 471-2937. NDHHS does not maintain an online data request portal equivalent to Missouri or Alabama — a direct email request to the Epidemiology office is the appropriate first contact. At case volumes of 5–15/year, a formal data use agreement (DUA) may be required due to re-identification risk. Researcher credentialing and IRB documentation may be requested before county-level annual counts are released.[^43][^44]

***

### 2.7 Colorado

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 4 / 2018: 3 / 2019: 8 / 2022: 10 / 2023: 32[^45] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | CDPHE open data layer includes 2024; 40 cases statewide reported[^45] |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^46] |
| **State DOH source** | [CDPHE Reportable Disease Data dashboard](https://cdphe.colorado.gov/colorado-reportable-disease-data) and open ArcGIS layer[^47][^46] |
| **ArcGIS service URL** | `https://www.cohealthmaps.dphe.state.co.us/arcgis/rest/services/OPEN_DATA/cdphe_reportable_disease_dataset/MapServer`[^46] |
| **Years in CDPHE open data** | 2015–2024[^46] |
| **Suppression risk** | **Very high** (3–32 statewide 2017–2022; rising to 40 in 2024)[^45] |

**Colorado is the only state in this review with a publicly accessible open-data ArcGIS layer that nominally covers 2015–2024 at the county level**. However, at statewide counts of 3–10 cases in 2017–2019, most county cells will be suppressed or absent. CDPHE also noted that pre-2022 Lyme investigations were "on hold due to limited capacity during the pandemic," and that essentially all pre-2022 cases were travel-acquired (cases assigned to county of residence, not exposure).[^46][^45]

**State data request procedure:** CDPHE open data is downloadable via the ArcGIS REST API. For suppressed cells, contact CDPHE Communicable Disease Branch directly; the open data layer documentation at `data-cdphe.opendata.arcgis.com` identifies the program contact. Colorado does not have a formal online data request portal for infectious disease data comparable to Georgia PHIP or Alabama NextRequest.[^47][^46]

***

### 2.8 Utah

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 25 / 2018: 27 / 2019: 19 / 2022: 16 / 2023: 16[^48][^49] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets; DHHS 2024 tick surveillance report available[^48] |
| **Data type** | True reportable-disease case counts[^49] |
| **State DOH source** | Utah DHHS annual [tick surveillance reports](https://epi.utah.gov/data-reports/) — statewide only[^49][^48] |
| **State geographic granularity** | **State-level only** from Utah DHHS public reports |
| **Suppression risk** | **High** (16–27 statewide); some county cells may survive in Dataset A for higher-count years |

**Critical endemic vs. travel-acquired caveat:** Utah DHHS 2023 tick surveillance report explicitly notes that 14 of 16 Lyme cases had confirmed out-of-state travel history, and DHHS states there is "no current evidence of tickborne Lyme disease transmission in the state". County-of-residence data for Utah carries particularly limited epidemiological meaning for endemic-risk applications.[^48][^49]

**State data request procedure:** Utah DHHS Division of Epidemiology: **epi@utah.gov**, phone 801-538-6191 or 1-888-EPI-UTAH. For suppressed county-level Lyme counts, submit a data request via email to the Epidemiology office, referencing the state's reportable disease database. Given Utah's very low endemic Lyme case burden, DHHS may note that county-of-residence data has limited utility but should still be able to provide annual case counts by county.[^50][^51]

***

### 2.9 Missouri

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence[^7] |
| **State-level totals (CDC)** | 2017: 12 / 2018: 11 / 2019: 17 / 2022: 7 / 2023: 16 |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^52] |
| **State DOH source** | Missouri DHSS [ArcGIS Lyme Disease Dashboard](https://experience.arcgis.com/experience/87baeccdda954f809c8a8607c02f683c)[^53][^54] and separate [LymeDisease 2023 Layer](https://www.arcgis.com/home/item.html?id=7f536fa7a4884fd69a09202bfec04477)[^55] — county-level choropleth maps |
| **State geographic granularity** | County (ArcGIS), but map-based visualization, not downloadable case count tables |
| **Suppression risk** | **Extreme** (7–17 statewide cases/year); virtually all county cells suppressed in Datasets C and D |

**Missouri DHSS contested epidemiology note:** Missouri DHSS has published a formal [Lyme disease position paper](https://health.mo.gov/living/healthcondiseases/communicable/tickscarrydisease/ldpositionpaper.php) cautioning that EM-like rashes in Missouri may not represent true *B. burgdorferi* infection. Both confirmed and probable cases are nonetheless reported to CDC via NNDSS and appear in the federal datasets.[^56]

**State data request procedure — formal route required:** With statewide totals of 7–17 cases/year, county-level unsuppressed data are not obtainable from public sources. The formal procedure is:[^57]
1. Submit a **Missouri Data Request Submission Form** via `health.mo.gov/data/surv-policies.php`[^57]
2. Allow at minimum two weeks for processing; fees may apply for programming/data analysis time[^57]
3. Contact: Bureau of Communicable Disease Control and Prevention, Missouri DHSS, PO Box 570, Jefferson City, MO 65102; phone (573) 751-6113[^52][^58]
4. For ESSENCE/syndromic access, contact Bureau of Reportable Disease Informatics: (573) 526-5271[^59]

A DUA and researcher/institution credentialing will likely be required at Missouri case volumes.

***

### 2.10 Kentucky

| Element | Details |
|---------|---------|
| **CDC incidence tier** | Low-incidence (currently; sustained trajectory may trigger reclassification)[^7] |
| **State-level totals (CDC)** | 2017: 20 / 2018: 22 / 2019: 22 / 2022: 72 / 2023: 120[^60] |
| **County-level federal data available?** | Yes — Datasets A, B, C, D[^5][^9][^4][^6] |
| **Years covered at county level** | 2017, 2018, 2019 (Datasets A, C); 2022 (Datasets B, D); 2023 (Dataset D) |
| **2024 county data** | Not in federal datasets; KY DPH storymap may have preliminary data |
| **Data type** | True reportable-disease case counts (confirmed + probable)[^61] |
| **State DOH source** | [KY DPH Tickborne Disease Storymap](https://storymaps.arcgis.com/stories/d6d2533ab2cf4e30b037eb4e9e3838c4) and [linked ArcGIS dashboard](https://www.arcgis.com/apps/dashboards/447f0300dab344049ddc19a5ba53bfe9)[^62][^63][^61] |
| **KY dashboard content** | County-level Lyme incidence rates (confirmed + probable per 100,000), 2011–2023 pooled; 2022-specific county map included; small-count counties flagged as unreliable[^61] |
| **Suppression risk** | **Lower post-2022** (72–120 statewide) — most counties will be unsuppressed for 2022–2023 |

**Kentucky trajectory flag:** Kentucky's post-2022 surge (20–22 → 72–120 cases/year) represents the most dramatic change in this cohort. Kentucky now ranks among the top states nationally for Lyme disease incidence growth, with approximately 275% increase during the post-2022 period. This reflects both genuine geographic expansion of blacklegged ticks and the impact of the revised probable case definition. If the current trend continues (120 confirmed+probable in 2023), Kentucky may approach the 10/100,000 threshold in coming years.[^64][^60]

**State data request procedure:** KY KDPH Infectious Disease Branch (Reportable Disease Section): phone **(502) 564-3261**, fax (502) 564-0542, address 275 E. Main St., HS2E-A, Frankfort, KY 40621. For suppressed county cells or annual discrete counts (as opposed to the multi-year pooled rates on the storymap), contact the IDB directly. Kentucky also accepts general disease reports/data requests by phone at 502-564-3418 or 888-9REPORT.[^65][^66]

***

## Part III: Consolidated Source Matrix

| State | CDC Tier | Federal County Data (CDC) | Years at County Level | State DOH County Source | State Geographic Granularity | Suppression Risk | 2024 County Public? |
|-------|----------|--------------------------|----------------------|-------------------------|------------------------------|-----------------|---------------------|
| Georgia | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | None (PHIP data request) | N/A — state page informational only | Very High (8–31/yr) | No |
| South Carolina | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [SC DPH Dashboard](https://dph.sc.gov/professionals/public-health-data/sc-tracking/tracking-lyme-disease-dashboard)[^21] | Region-level, 5-yr rolling rates | Moderate (21–55/yr) | Dashboard updated 2024[^19] |
| Tennessee | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [TDH Interactive Dashboard](https://www.tn.gov/health/ceds-weeklyreports/interactive-disease-data.html)[^25] | County or regional, annual | Lower (29–50/yr) | Dashboard; no county download |
| Alabama | Low[^29] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [ADPH Data page](https://www.alabamapublichealth.gov/tick/data.html)[^32] | Statewide table + 8-region dot maps | Moderate (32–66/yr) | Dot map 2024 (38 cases)[^30] |
| Kansas | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [KEAP EPHT](https://keap.kdhe.ks.gov/Ephtm/PortalPages/ContentData)[^36][^37] | County (EPHT, 2016–2021 only) | Very High post-2022 (9–12/yr) | No |
| Nebraska | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [NDHHS bar chart](https://dhhs.ne.gov/WNV%20Documents/Lyme%20Cases%20by%20Year%202010-2023.pdf)[^41] | State-level only | Extreme (5–15/yr) | No |
| Colorado | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [CDPHE ArcGIS open layer](https://data-cdphe.opendata.arcgis.com/datasets/cdphe-colorado-reportable-disease-dataset)[^47][^46] | County, annual, 2015–2024 | Very High (3–32/yr) | CDPHE layer includes 2024[^45] |
| Utah | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [DHHS tick surveillance reports](https://epi.utah.gov/data-reports/)[^49] | State-level only | High (16–27/yr) | No |
| Missouri | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [ArcGIS Lyme Dashboard](https://experience.arcgis.com/experience/87baeccdda954f809c8a8607c02f683c)[^53][^54][^55] | County choropleth (map only) | Extreme (7–17/yr) | No |
| Kentucky | Low[^7] | Datasets A, B, C, D | 2017–2019, 2022–2023 | [KY DPH Storymap](https://storymaps.arcgis.com/stories/d6d2533ab2cf4e30b037eb4e9e3838c4)[^62][^61] | County incidence rates, 2011–2023 pooled | Lower post-2022 (72–120/yr) | No |

***

## Part IV: State DOH Data Request Procedures

For all ten states, unsuppressed county-level annual Lyme case counts require a formal data request when federal datasets contain suppressed cells. The following table provides the primary contact point for each state.

| State | Request Mechanism | Contact |
|-------|------------------|---------|
| Georgia | [PHIP online portal](https://dph.georgia.gov/phip-data-request)[^16] | 1-866-782-4584; SendSS data[^18] |
| South Carolina | Email CDES directly[^20] | sctracking@dph.sc.gov; SCION database[^20][^22] |
| Tennessee | Email or phone CEDEP[^25][^27] | tn.health@tn.gov; (615) 741-7247[^27][^28] |
| Alabama | [Infectious Diseases Data Request Form](https://www.alabamapublichealth.gov/data/requests.html)[^33] or NextRequest[^34] | adph.nextrequest.com[^34] |
| Kansas | Email KDHE Vital & Health Statistics[^39] | kdhe.ks.gov/1348/Data-Requests; EpiTrax data[^39][^40] |
| Nebraska | Email NDHHS Epidemiology[^43][^44] | dhhs.epi@nebraska.gov; (402) 471-2937[^44] |
| Colorado | CDPHE open data or Communicable Disease Branch | data-cdphe.opendata.arcgis.com[^47] |
| Utah | Email DHHS Epidemiology[^50] | epi@utah.gov; (801) 538-6191[^50] |
| Missouri | [Formal data request form](https://health.mo.gov/data/surv-policies.php)[^57] | (573) 751-6113; health.mo.gov/data[^57][^52] |
| Kentucky | KDPH Infectious Disease Branch[^66] | (502) 564-3261; 275 E. Main St., Frankfort, KY[^66] |

**Cross-cutting procedural notes:**
- Missouri and Nebraska have the highest re-identification risk at their case volumes; both will likely require researcher credentialing, IRB documentation, or a formal Data Use Agreement before releasing unsuppressed county-year cells[^44][^57]
- Kansas KDHE advises that data request fees may apply for programming time[^39]
- Alabama offers the most streamlined pathway via its dedicated Infectious Diseases and Outbreaks request form[^33]
- Tennessee offers the most directly accessible state-level dashboard and may provide county data without a formal request for publicly visible data years[^25]
- Georgia PHIP requires account creation but is fully online[^16]

***

## Part V: Key Analytical Caveats

### 2022 Case Definition Discontinuity
The single most consequential methodological issue for any analysis spanning 2017–2019 and 2022–2024 is the 2022 CSTE/CDC revised surveillance case definition. High-incidence states may now report based on laboratory evidence alone; low-incidence states (all ten states in this review) still require clinical + laboratory criteria. The practical consequence is that probable case capture in low-incidence states changed substantially — some states report fewer probable cases (Kansas: 35 → 9) while others report more (Kentucky: 22 → 120), partly reflecting how the new definition interacts with local clinical and laboratory reporting practices.[^60][^7][^8]

### County of Residence ≠ County of Exposure
All CDC datasets and all state DOH datasets assign cases to county of **residence**, not county of tick exposure. This is particularly consequential for Colorado and Utah, where most cases are travel-acquired. In all ten states, a case in a metropolitan county may reflect exposure anywhere in the country; this limits the use of county-of-residence data for endemic-risk spatial analysis without exposure location filtering.[^45][^49][^10][^48][^2]

### Dataset Architecture Change (XLSX Files)
The older 2016–2019 XLSX (Dataset A) provides a 4-year aggregate useful for 2017, 2018, and 2019 combined. The new 2019–2022 XLSX (Dataset B) on the CDC geographic distribution page similarly aggregates 4 years. Neither XLSX provides single-year county counts. For discrete annual county-level counts, use Datasets C and D (data.cdc.gov FIPS-level aggregated files), accepting that suppressed cells will be common in low-incidence states.[^3][^2][^4][^5][^6]

### No 2024 Public County Data
No finalized public county-level dataset from CDC covers 2024 as of May 2026. The most recent CDC national summary reports 89,000+ cases in 2023; 2024 data finalization is expected later in 2026. State health departments may hold provisional 2024 data, but none of the ten target states have posted downloadable county-level 2024 Lyme case counts. ADPH and CDPHE provide statewide 2024 case indicators (dot map and open data layer, respectively) but not downloadable county tables.[^1][^10][^45][^30]

---

## References

1. [Lyme Disease Surveillance Data](https://www.cdc.gov/lyme/data-research/facts-stats/surveillance-data-1.html) - Explore reported Lyme disease cases by year, including case counts, seasonality, and demographics.

2. [Geographic Distribution of Tickborne Disease Cases](https://www.cdc.gov/ticks/data-research/facts-stats/geographic-distribution-of-tickborne-disease-cases.html) - Reported cases of selected tickborne diseases by county of residence in the United States.

3. [Geographic Distribution of Tickborne Disease Cases - Actuarial News](https://www.actuarial.news/2025/08/01/geographic-distribution-of-tickborne-disease-cases/) - Reported Tickborne Disease Cases by County of Residence 2019-2022.xlsx. To download a static map for...

4. [Lyme disease public use aggregated data with geography, 2008-2021](https://data.cdc.gov/National-Center-for-Emerging-and-Zoonotic-Infectio/Lyme-disease-public-use-aggregated-data-with-geogr/qtbi-xd4i)

5. [Reported-Tickborne-Disease-Cases-by-County-of-Residence_2016-2019.xlsx](https://www.cdc.gov/ticks/resources/Reported-Tickborne-Disease-Cases-by-County-of-Residence_2016-2019.xlsx)

6. [Lyme disease public use aggregated data with geography, 2022-2023](https://portal.datarescueproject.org/datasets/lyme-disease-public-use-aggregated-data-with-geography-2022-2023/) - Links to public data archived through combined efforts and coordinated by the Data Rescue Project.

7. [Surveillance for Lyme Disease After Implementation of a Revised ... - CDCwww.cdc.gov › mmwr › volumes](https://www.cdc.gov/mmwr/volumes/73/wr/mm7306a1.htm) - This report describes the first year of Lyme disease surveillance data collected using the 2022 case...

8. [Surveillance for Lyme Disease After Implementation of a Revised ...](https://pubmed.ncbi.nlm.nih.gov/38358952/) - Lyme disease, a tickborne zoonosis caused by certain species of Borrelia spirochetes, is the most co...

9. [AllTBD2022_Public.xlsx](https://www.cdc.gov/ticks/media/files/2024/05/AllTBD2022_Public.xlsx)

10. [Lyme Disease Surveillance and Data](https://www.cdc.gov/lyme/data-research/facts-stats/index.html) - Lyme disease is a nationally notifiable condition. Health departments report cases to CDC.

11. [Lyme disease surveillance and available data | CDC](https://www.cdc.gov/lyme/stats/survfaq.html) - Includes background on Lyme disease surveillance, limitations of surveillance data, and a public use...

12. [National Notifiable Diseases Surveillance System (NNDSS) Data](https://wonder.cdc.gov/nndss.html)

13. [Lyme Disease Case Maps - CDC](https://www.cdc.gov/lyme/data-research/facts-stats/lyme-disease-case-map.html) - Data maps showing reported cases of Lyme disease over time and by state of residence.

14. [Lyme Disease - Georgia Department of Public Health](https://dph.georgia.gov/epidemiology/zvbd/tbd/lyme) - Although rare in Georgia, Lyme disease is the most common vector-borne disease in the United States.

15. [Tick-borne Diseases - Georgia Department of Public Health](https://dph.georgia.gov/epidemiology/zvbd/tbd) - Ticks can carry disease and transmit the disease organisms while feeding. Most tick bites do not res...

16. [PHIP Data Request - Georgia Department of Public Health](https://dph.georgia.gov/phip-data-request) - The Public Health Information Portal (PHIP) is an online system where you can request public health ...

17. [Disease Reporting | Georgia Department of Public Health](https://dph.georgia.gov/epidemiology/disease-reporting) - Notifiable diseases and health conditions can be reported through our electronic disease surveillanc...

18. [Notifiable Disease Condition Reporting — Accessible Text and Tables](https://dph.georgia.gov/notifiable-disease-condition-reporting-accessible-text-and-tables) - Report Immediately - Call District Health Office or 1-866-PUB-HLTH (1-866-782-4584). Condition, Lege...

19. [Tracking Lyme Disease Dashboard | South Carolina Department of ...](https://dph.sc.gov/professionals/public-health-data/sc-tracking/tracking-lyme-disease-dashboard) - Rate of Hospitalizations for Lyme Disease in South Carolina from 2019-2023, By Month. Confirmed Lyme...

20. [[PDF] Lyme Disease | SC Tracking](https://dph.sc.gov/sites/scdph/files/2025-09/Lyme_Disease_Metadata_202509.pdf)

21. [Navigating the Lyme Disease Dashboard](https://dph.sc.gov/professionals/public-health-data/sc-environmental-public-health-tracking/tracking-lyme-disease-0) - The South Carolina Department of Public Health has developed an interactive Lyme Disease Dashboard. ...

22. [Current SCIONx Users | South Carolina Department of Public Health](https://dph.sc.gov/professionals/health-professionals/health-services-facilities/current-scionx-users) - SCIONx is currently operating at NORMAL levelsIf you need assistance, please contact us Help Desk 1-...

23. [What is SCIONx? - South Carolina Department of Public Health](https://dph.sc.gov/professionals/health-professionals/health-services-facilities/online-reporting-tool-scionx/what) - SCIONx is a web-based system that allows physicians, nurses, and lab professionals to notify DPH whe...

24. [Lyme Disease - TN.gov](https://www.tn.gov/health/cedep/vector-borne-diseases/tick-borne-diseases/tick-borne-diseases-of-concern/lyme-disease.html)

25. [Interactive Disease Data - TN.gov](https://www.tn.gov/health/ceds-weeklyreports/interactive-disease-data.html)

26. [Tennessee Public Health Dashboards - TN.gov](https://www.tn.gov/health/dashboards.html) - Tennessee public health dashboards and visualizations that show trends in diseases, health outcomes,...

27. [Tennessee Department of Health Contact - TN.gov](https://www.tn.gov/health/contact.html) - Certified Nursing Assistant License, (615) 532-5171 ; Communicable & Environmental Disease, (615) 74...

28. [Tennessee Department of Health | National Prevention Information ...](https://npin.cdc.gov/organization/tennessee-department-health-51) - Nashville, TN 37243. United States. County: Davidson. Visit Main Website (tn.gov/health.html) · Call...

29. [Lyme Disease | Alabama Department of Public Health (ADPH)](https://www.alabamapublichealth.gov/tick/lyme-disease.html) - This page provides information on Lyme disease ... However, in Alabama, there are not many cases of ...

30. [[PDF] Reported Tickborne Disease Cases Alabama 2024](https://www.alabamapublichealth.gov/tick/assets/tick_map2024.pdf)

31. [[PDF] Reported Cases* of Tickborne Diseases by Year, Alabama (1988 ...](https://www.alabamapublichealth.gov/tick/assets/altickbornecasetable.pdf)

32. [Data | Alabama Department of Public Health (ADPH)](https://www.alabamapublichealth.gov/tick/data.html) - This page provides data on tick-borne diseases in Alabama.

33. [Data Requests | Alabama Department of Public Health (ADPH)](https://www.alabamapublichealth.gov/data/requests.html) - If you are looking for data not provided on this website or in any of our reports, please submit one...

34. [Public Record RequestsNextRequest - Modern FOIA & Public ...](https://adph.nextrequest.com) - Under Ala. Code § 36-12-40, Alabama citizens may inspect and take a copy of any public record mainta...

35. [[PDF] DATA NOTES: LYME DISEASE](https://keap.kdhe.ks.gov/EPHTM/EphtContent/documents/Metadata/TBD_DataNotes_LymeDisease.pdf)

36. [EPHT Data Explorer - KDHE Public GIS Web Maps](https://maps.kdhe.ks.gov/ksepht/?ContentAreaID=999&GeoLayer=2&IndicatorID=9995&MeasureID=99995&StratFieldName=None&StratLocalId=None&Year=2022&dlg=Advanced-Download) - Content Area. Tickborne Disease ; Geography. County ; Indicator. Lyme Disease ; Measure. Number of r...

37. [Data Stories - - Kansas Environmental Public Health Tracking](https://keap.kdhe.ks.gov/Ephtm/PortalPages/ContentData) - This interactive data story gives an in-depth overview of the most common tickborne diseases in the ...

38. [EPHT Data Explorer - KDHE Public GIS Web Maps](https://maps.kdhe.ks.gov/ksepht/?ContentAreaID=999&GeoLayer=2&IndicatorID=9995&MeasureID=99995&StratFieldName=None&StratLocalId=None&Year=2022) - Content Area. Tickborne Disease ; Geography. County ; Indicator. Lyme Disease ; Measure. Number of r...

39. [Data Requests | KDHE, KS - Kansas.gov](https://www.kdhe.ks.gov/1348/Data-Requests) - The Vital and Health Statistics Data Analysis team prepares public reports and data queries, and upd...

40. [[PDF] Lyme Disease Investigation Guideline - KDHE](https://www.kdhe.ks.gov/DocumentCenter/View/7289/Lyme-Disease-Investigation-Guideline-PDF) - . • Verify that all data requested on the Lyme Disease Form has been recorded on an appropriate EpiT...

41. [[PDF] Reported Cases of Lyme Disease in Nebraska by Year, 2010-2023 ...](https://dhhs.ne.gov/WNV%20Documents/Lyme%20Cases%20by%20Year%202010-2023.pdf) - 2022. 2023. Nu mb e. r o f Ca s e s. Year. Reported Cases of Lyme Disease in Nebraska by Year, 2010-...

42. [[PDF] 2023 NEBRASKA TICKBORNE DISEASE REPORT - DHHS](https://dhhs.ne.gov/WNV%20Documents/Tick-borne%20Disease%20Report.pdf) - 24 tickborne disease cases have been reported. • 10 of the ... includes Rocky Mountain Spotted Fever...

43. [Epidemiology and Surveillance - DHHS - Nebraska.gov](https://dhhs.ne.gov/Pages/Epidemiology.aspx) - The Nebraska Department of Health and Human Services Office of Epidemiology works to protect the hea...

44. [Reportable Conditions - DHHS - Nebraska.gov](https://dhhs.ne.gov/Pages/Reportable-Conditions.aspx) - Reportable Disease Forms ; Phone Number. (402) 471-2937 ; Fax Number. (402) 471-3601 ; Email Address...

45. [Colorado State Reportable Tick-Borne Diseases](https://coloradoticks.org/colorado-reportable-tick-borne-diseases/) - CDPHE shows only 10 cases of Lyme disease between 2018-2023, stating ... Colorado, and this data sho...

46. [OPEN_DATA/cdphe_reportable_disease_dataset (MapServer)](https://www.cohealthmaps.dphe.state.co.us/arcgis/rest/services/OPEN_DATA/cdphe_reportable_disease_dataset/MapServer) - Description: The Colorado Reportable Disease dataset contains yearly case count and rate data for re...

47. [CDPHE Colorado Reportable Disease Dataset](https://data-cdphe.opendata.arcgis.com/datasets/cdphe-colorado-reportable-disease-dataset) - The Colorado reportable disease dataset contains yearly case count and rate data for reportable dise...

48. [Our 2024 tick surveillance annual report is out! Swipe to ... - Instagram](https://www.instagram.com/p/DK2J5PcuC8D/?hl=en) - Our 2024 tick surveillance annual report is out! Swipe to see what we found in 2024 as we collected ...

49. [[PDF] Tick surveillance annual report 2023 - epi@utah.gov](https://epi.utah.gov/wp-content/uploads/Tick-Surveillance-Annual-Report_2023.pdf) - DHHS tick surveillance efforts are conducted to learn more about Lyme disease risk in. Utah. We also...

50. [Contact us | Communicable Diseases – Utah DHHS](https://epi.utah.gov/contact-us/) - These diseases may be reported to a local health department or the Utah Department of Health and Hum...

51. [Disease Reporting | Communicable Diseases – Utah DHHS](https://epi.utah.gov/disease-reporting/) - Reports can be submitted by: · Fax: 801-538-9923 · Email: reporting@utah.gov · Phone: 1-888-EPI-UTAH...

52. [Tickborne Disease | Health & Senior Services](https://health.mo.gov/living/healthcondiseases/communicable/tickscarrydisease/index.php) - Contact. Bureau of Communicable Disease Control and Prevention Missouri Department of Health and Sen...

53. [Lyme Disease Dashboard - Overview - ArcGIS Online](https://www.arcgis.com/home/item.html?id=87baeccdda954f809c8a8607c02f683c) - This dashboard shows lyme disease cases in Missouri counties and the local public health agencies of...

54. [Lyme Disease Dashboard - ArcGIS Experience Builder](https://experience.arcgis.com/experience/87baeccdda954f809c8a8607c02f683c) - This dashboard shows lyme disease cases in Missouri counties and the local public health agencies of...

55. [LymeDisease 2023 Layer - Overview - ArcGIS Online](https://www.arcgis.com/home/item.html?id=7f536fa7a4884fd69a09202bfec04477) - This map shows Lyme disease cases in Missouri counties and the local public health agencies of Indep...

56. [Lyme Disease Position Paper | Health & Senior Services](https://health.mo.gov/living/healthcondiseases/communicable/tickscarrydisease/ldpositionpaper.php) - Rocky Mountain spotted fever, ehrlichiosis, and tularemia are found in Missouri. DHSS believes that ...

57. [Surveillance Data Release Policies, Procedures & Guidelines](https://health.mo.gov/data/surv-policies.php) - To request public health surveillance data, a requestor must submit a complete a Missouri Data Reque...

58. [[PDF] Prevention and Control of Communicable Diseases - Springfield, MO](https://www.springfieldmo.gov/DocumentCenter/View/67348/CD-Daycare-Manual) - For more information, call Missouri Department of Health and Senior Services (DHSS) at. 573-751-6113...

59. [Information for Public Health Agencies | ESSENCE](https://health.mo.gov/data/essence/infolphas.php) - Bureau of Reportable Disease Informatics Missouri Department of Health and Senior Services PO Box 57...

60. [Is KY seeing more Lyme disease & deer ticks? Check these maps](https://www.kentucky.com/news/state/kentucky/article292697664.html) - Probable and confirmed cases of Lyme disease in the commonwealth have been on the rise since 2020 (a...

61. [Tickborne Disease in Kentucky - ArcGIS StoryMaps](https://storymaps.arcgis.com/stories/d6d2533ab2cf4e30b037eb4e9e3838c4) - The following map shows reported cases of Lyme disease reported to the CDC for 2022. ... Lyme Diseas...

62. [Tickborne Diseases - Cabinet for Health and Family Services](https://chfs.ky.gov/agencies/dph/dehp/idb/Pages/tick-borne.aspx) - When infected blood-sucking arthropods, such as ticks, bite a person, they can spread tickborne illn...

63. [Lyme Disease Dashboard 2022 - ArcGIS Online](https://www.arcgis.com/apps/dashboards/447f0300dab344049ddc19a5ba53bfe9) - ArcGIS Dashboards.

64. [Kentucky Office of the State Entomologist - Facebook](https://www.facebook.com/KyStateEnt/posts/according-to-research-from-the-kentucky-department-for-public-health-kdph-report/1375228097970758/) - Most notably, cases of Lyme disease skyrocketed by approximately 275% during that same three-year pe...

65. [[PDF] Kentucky Reportable Disease Form](https://stage.lfchd.org/wp-content/uploads/2022/08/2020-EPID-200-Fillable-Form-v2.pdf)

66. [Infectious Disease Branch - Cabinet for Health and Family Services](https://chfs.ky.gov/agencies/dph/dehp/idb/Pages/default.aspx) - Contact Information. 38. Reportable Disease Section. Mailing Address. 275 E. Main St. HS2E-A Frankfo...

