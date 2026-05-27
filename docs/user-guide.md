# TickBiteRisk User Guide

> **File location:** `/docs/user-guide.md`

---

## 1. What TickBiteRisk Tells You Today

The implemented v0 product is a Maryland county-week Lyme baseline. It reports a
relative county-week seasonal Lyme baseline on a 1-10 Maryland scale.

It answers a public-health context question:

```text
For this Maryland county and date, how high is the modeled seasonal Lyme
baseline compared with other Maryland county-week baselines?
```

It does not answer whether a specific tick bite infected you. It is not a per-bite
infection probability, diagnosis, treatment recommendation, or weather-adjusted
forecast.

This is not a per-bite infection probability.

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

## 3. Static Dashboard Data

For a static web product, export a public-safe derived JSON bundle:

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --output-dir public/data
```

The static dashboard reads only the committed `public/data` bundle and
`public/md_counties.geojson`. It does not need raw data, Postgres credentials,
NOAA tokens, Census tokens, or private ETL extracts.

Run the static dashboard locally:

```bash
python -m http.server 8000 --directory public
```

Open `http://localhost:8000`.

---

## 4. What To Do With The Score

Use the score as context for prevention and awareness, not as a personal medical
decision rule. A higher seasonal baseline can support public-health messaging,
prevention reminders, and clinical awareness that Lyme reports are seasonally
elevated in a county.

If you found an attached tick, follow CDC guidance for removal and monitoring.
If you have symptoms, are concerned about a tick bite, or have questions about
treatment, contact a qualified healthcare professional.

Authoritative guidance:

- CDC: What to do after a tick bite: `https://www.cdc.gov/ticks/after-a-tick-bite/index.html`
- CDC: Preventing tick bites: `https://www.cdc.gov/ticks/prevention/index.html`
- CDC: Lyme disease signs and symptoms: `https://www.cdc.gov/lyme/signs-symptoms/index.html`

---

## 5. Responsible Use

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

---

## 6. Roadmap

A future HTTP API may expose per-bite probability models using location,
attachment duration, tick species/stage, and updated ecological features. That
roadmap API is not the implemented v0 public product.

*Last updated: 2026-05-27*
