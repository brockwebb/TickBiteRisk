# TickBiteRisk User Guide

> **File location:** `/docs/user-guide.md`

---

## 1. What TickBiteRisk Tells You Today

The implemented v0 product has two local runtime views:

- a Maryland relative county-week seasonal Lyme baseline on a 1-10 scale, and
- a single-bite Lyme decision-support score that combines that baseline with
  tick identity, life stage, attachment time, engorgement, removal timing, and
  CDC prophylaxis consideration criteria.

It answers a public-health context question:

```text
For this Maryland county and date, how high is the modeled seasonal Lyme
baseline compared with other Maryland county-week baselines?
```

It also answers a post-bite context question:

```text
Given this Maryland county/date and what I know about the attached tick, how
does the bite-specific evidence change the Lyme concern level, and which CDC
post-exposure prophylaxis consideration criteria are met, not met, or uncertain?
```

This is not an absolute infection probability, diagnosis, treatment
recommendation, or weather-adjusted forecast.

The date is converted to CDC MMWR week. If the requested year is not available
in the derived baseline artifact, the runtime uses the latest available
baseline year for that county and week and returns explicit quality flags.

---

## 2. How To Run The Implemented Lookup

Use the local CLI against the derived county-week risk artifact:

```bash
tickbiterisk risk lookup \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --pretty
```

Important response fields:

| Field | Meaning |
| --- | --- |
| `county_fips`, `county_name` | Maryland county returned by the lookup. |
| `query_date`, `mmwr_year`, `mmwr_week` | Calendar date and CDC MMWR week used for lookup. |
| `data_year` | Baseline year used; may differ from query year when current-year data is unavailable. |
| `risk_score`, `risk_category` | Relative 1-10 Maryland seasonal score and plain category. |
| `predicted_weekly_incidence_per_100k` | Model-derived weekly incidence baseline behind the score. |
| `predicted_weekly_incidence_95_interval` | Empirical model interval for the baseline, not clinical confidence for an individual bite. |
| `source_metadata` | Model-comparison and seasonality source run/hash metadata. |
| `feature_quality_flags`, `data_quality_flags` | Caveats such as static seasonality, not weather-adjusted, or latest-year fallback. |

---

## 3. How To Run The Single-Bite Score

Use the local CLI when you have an attached tick and want a structured,
plain-language risk context summary:

```bash
tickbiterisk risk single-bite \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --tick-species blacklegged \
  --tick-stage nymph \
  --attachment-hours 40 \
  --engorgement engorged \
  --hours-since-removal 24 \
  --doxycycline-safe \
  --pretty
```

Important response fields:

| Field | Meaning |
| --- | --- |
| `single_bite_risk_score`, `single_bite_risk_band` | Evidence-adjusted 1-10 Lyme concern score and category. |
| `baseline_context` | County-week seasonal prior used as local context. |
| `input_summary` | Normalized tick species, stage, attachment, engorgement, removal timing, doxycycline safety, and tick count inputs. |
| `evidence_modifiers` | Transparent modifiers applied to the county-week baseline. |
| `pep_consideration` | Whether the inputs meet, partially meet, or do not meet CDC prophylaxis consideration criteria. |
| `pep_criteria` | Criterion-by-criterion status for Lyme-common area, tick identity, attachment duration/engorgement, removal window, and doxycycline safety. |
| `caveats` | Limits such as not calibrated as an absolute probability or uncertain tick identification. |

Unknown values are allowed for several fields. Unknowns generally produce a
`partially_meets_cdc_consideration_criteria` result rather than false certainty.

---

## 4. Static Dashboard Data

For a static web product, export a public-safe derived JSON bundle:

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
  --output-dir public/data
```

The static dashboard reads only the committed `public/data` bundle, including
`public/data/md_counties.geojson`. It does not need raw data, Postgres
credentials, NOAA tokens, Census tokens, or private ETL extracts.
Including `--model-summary-path` publishes the selected model branch's
rolling-origin validation metrics in `model_card.json`.

Run the static dashboard locally:

```bash
python -m http.server 8000 --directory public
```

Open `http://localhost:8000`.

---

## 5. What To Do With The Score

Use these scores as context for prevention and awareness, not as personal
medical decision rules. A higher seasonal baseline can support public-health
messaging, prevention reminders, and clinical awareness that Lyme reports are
seasonally elevated in a county. A higher single-bite score can help organize
what you know about the tick and whether CDC prophylaxis consideration criteria
look met, not met, or uncertain.

If you found an attached tick, follow CDC guidance for removal and monitoring.
If you have symptoms, are concerned about a tick bite, or have questions about
treatment, contact a qualified healthcare professional.

Authoritative guidance:

- CDC: What to do after a tick bite: `https://www.cdc.gov/ticks/after-a-tick-bite/index.html`
- CDC: Preventing tick bites: `https://www.cdc.gov/ticks/prevention/index.html`
- CDC: Lyme disease signs and symptoms: `https://www.cdc.gov/lyme/signs-symptoms/index.html`

---

## 6. Responsible Use

Informational and educational only. Follow CDC guidance and consult a qualified
healthcare professional about your situation.

Known v0 caveats:

- Maryland-only county baseline.
- Lyme-only public score.
- Static CDC national onset seasonality, not county-specific seasonality.
- Not weather-adjusted in the current public score branch.
- Surveillance/reporting changes and interventions are not modeled.
- Empirical intervals describe baseline uncertainty, not clinical confidence for
  a specific tick bite.
- Single-bite scores are transparent decision-support estimates, not calibrated
  absolute infection probabilities.

---

## 7. Roadmap

A future HTTP API may expose the implemented local runtime contracts. Future
research may also test calibrated absolute infection-probability models using
pathogen prevalence, attachment duration, tick species/stage, and updated
ecological features.

*Last updated: 2026-05-27*
