# TickBiteRisk API And Runtime Specification

> **File location:** `/api/api-spec.md`

---

## 1. Overview

Current implemented local contract: `tickbiterisk risk lookup` reads the derived
Maryland county-week seasonal risk baseline CSV and returns local JSON for a
county/date query.

That response is a relative 1-10 Lyme seasonality baseline for Maryland
counties. It is not a per-bite infection probability, diagnosis, treatment
recommendation, or weather-adjusted forecast.

The future HTTP API described later in this document is roadmap behavior. The
repository does not currently ship a FastAPI app, Docker API service, or
`openapi.yaml`.

---

## 2. Current Local Runtime: `tickbiterisk risk lookup`

### 2.1. Command

```bash
tickbiterisk risk lookup \
  --county-fips 24003 \
  --date 2026-05-26 \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --pretty
```

### 2.2. Parameters

| Name | Required | Example | Description |
| --- | --- | --- | --- |
| `--county-fips` | yes | `24003` | Five-digit Maryland county FIPS code. |
| `--date` | no | `2026-05-26` | Calendar date converted to CDC MMWR year/week. Defaults to today. |
| `--scores-path` | no | `build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv` | Derived county-week score CSV. |
| `--model-name` | no | `linear_blend_baseline` | Annual prediction model branch. |
| `--seasonality-source-id` | no | `cdc_seasonality_week_2023` | Weekly seasonality branch. |
| `--benchmark-quantile` | no | `0.95` | Optional score-scale selector when multiple scale branches coexist. |
| `--headroom-multiplier` | no | `1.2` | Optional score-scale selector when multiple scale branches coexist. |
| `--score-denominator` | no | `3.659725` | Optional exact score-scale denominator selector. |
| `--source-prediction-run-id` | no | `model_compare_start2007_end2023_mintrain5_ridge1p0_shrink5p0` | Optional annual prediction source selector. |
| `--source-prediction-sha256` | no | SHA-256 string | Optional annual prediction artifact selector. |
| `--source-seasonality-sha256` | no | SHA-256 string | Optional seasonality artifact selector. |
| `--pretty` | no | `--pretty` | Pretty-print JSON output. |

### 2.3. Successful Response Shape

```json
{
  "county_fips": "24003",
  "county_name": "Anne Arundel County",
  "query_date": "2026-05-26",
  "mmwr_year": 2026,
  "mmwr_week": 21,
  "data_year": 2023,
  "model_name": "linear_blend_baseline",
  "model_family": "ensemble",
  "target_definition": "lyme_incidence_per_100k",
  "feature_set": "historical_outcome_baselines",
  "evaluation_mode": "rolling_origin_prior_years",
  "weather_mode": "not_used_by_lagged_model",
  "seasonality_source_id": "cdc_seasonality_week_2023",
  "period_label": "MMWR Week 21",
  "risk_score": 1,
  "risk_category": "very_low",
  "risk_score_raw": 1.23,
  "predicted_weekly_incidence_per_100k": 0.45,
  "predicted_weekly_incidence_80_interval": [0.33, 0.51],
  "predicted_weekly_incidence_95_interval": [0.28, 0.55],
  "predicted_weekly_cases": 2.67,
  "predicted_annual_incidence_per_100k": 78.0,
  "score_scale": {
    "benchmark_quantile": 0.95,
    "headroom_multiplier": 1.2,
    "score_denominator": 3.659725
  },
  "source_metadata": {
    "source_prediction_run_id": "model_compare_start2007_end2023_mintrain5_ridge1p0_shrink5p0",
    "source_prediction_sha256": "0f4cfc8ba65722e09da63dbc7eecd61d010b3cf8a298515451ba6b31d6787250",
    "source_seasonality_sha256": "1c8fe90325eba9110b0d5d9aab355bfc1750311033f0c1ba87d64a12a5ba9a74"
  },
  "feature_quality_flags": [
    "relative_seasonal_baseline",
    "static_seasonality_prior",
    "not_weather_adjusted"
  ],
  "backtest_assumption_flags": [
    "observational_not_causal",
    "intervention_history_unmodeled",
    "surveillance_reporting_sensitive"
  ],
  "data_quality_flags": [
    "relative_seasonal_baseline",
    "requested_year_unavailable",
    "using_latest_available_year"
  ],
  "score_interpretation": "Relative seasonal Lyme baseline on a 1-10 scale. This is not a per-bite infection probability, diagnosis, treatment recommendation, or weather-adjusted forecast.",
  "clinical_disclaimer": "TickBiteRisk is for informational and educational purposes only...",
  "guidance_links": [
    {
      "title": "CDC: What to do after a tick bite",
      "url": "https://www.cdc.gov/ticks/after-a-tick-bite/index.html"
    }
  ]
}
```

### 2.4. Runtime Behavior

- Dates use CDC MMWR week boundaries.
- If the query MMWR year exists in the selected derived artifact, the response
  uses that year and includes `exact_baseline_year`.
- If the query MMWR year is unavailable, the response uses the latest available
  baseline for the same county/week and includes `requested_year_unavailable`
  and `using_latest_available_year`.
- If multiple score-scale branches overlap, callers must provide score-scale
  selectors.
- If multiple source branches overlap, callers must provide source run/hash
  selectors.
- Errors are raised as CLI parameter errors with no traceback in normal use.

---

## 3. Current Static Runtime: `tickbiterisk risk export-static`

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --output-dir public/data
```

The static export writes:

- `md_county_risk_weekly.json`
- `md_county_metadata.json`
- `model_card.json`
- `source_catalog.json`
- `static_export_manifest.json`

The static bundle publishes one selected model/source/scale branch, one latest
available row per county/MMWR week, CDC guidance links, model/source metadata,
and plain-language caveats. It does not publish raw data, private warehouse
tables, credentials, or ambiguous branches.

---

## 4. Roadmap HTTP API

The roadmap HTTP API may eventually expose per-bite Lyme probability estimates
using location, attachment duration, tick species/stage, and calibrated
ecological features. This is not implemented in v0.

Possible future endpoint:

```text
GET /risk?fips=24003&tau=24
```

Possible future parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `fips` | string | yes | County FIPS code. |
| `tau` | number or repeated number | yes | Attachment duration in hours. |
| `k` | integer | no | Number of attached ticks. |
| `date` | `YYYY-MM-DD` | no | Calendar date for MMWR week and seasonal context. |
| `pretty` | boolean | no | Pretty-print JSON output. |

Possible future response concepts:

- per-bite infection probability,
- uncertainty or credible interval,
- model/source metadata,
- explicit clinical caveats and CDC guidance links.

Before this HTTP API is built, it needs separate implementation, validation,
security review, dependency wiring, OpenAPI generation, and product wording
review.

*Last updated: 2026-05-27*
