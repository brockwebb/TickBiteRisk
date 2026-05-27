# TickBiteRisk API And Runtime Specification

> **File location:** `/api/api-spec.md`

---

## 1. Overview

Current implemented local contracts:

- `tickbiterisk risk lookup` reads the derived Maryland county-week seasonal
  risk baseline CSV and returns local JSON for a county/date query.
- `tickbiterisk risk single-bite` uses that county-week baseline as context and
  combines it with bite-specific evidence.

The baseline lookup is a relative 1-10 Lyme seasonality baseline for Maryland
counties. The single-bite runtime is a decision-support score and CDC criteria
summary. Neither response is an absolute infection probability, diagnosis,
treatment recommendation, or weather-adjusted forecast.

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

## 3. Current Single-Bite Runtime: `tickbiterisk risk single-bite`

### 3.1. Command

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

### 3.2. Parameters

| Name | Required | Example | Description |
| --- | --- | --- | --- |
| `--county-fips` | yes | `24003` | Five-digit Maryland county FIPS code used for the county-week prior. |
| `--date` | no | `2026-05-26` | Calendar date converted to CDC MMWR year/week. Defaults to today. |
| `--scores-path` | no | `build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv` | Derived county-week score CSV. |
| `--tick-species` | yes | `blacklegged` | Tick identity. Supported examples include `blacklegged`, `ixodes_scapularis`, `possible_ixodes`, `unknown`, and `not_ixodes`. |
| `--tick-stage` | no | `nymph` | Tick life stage: `nymph`, `adult`, `larva`, or `unknown`. |
| `--attachment-hours` | no | `40` | Estimated attachment duration in hours. |
| `--engorgement` | no | `engorged` | Observed engorgement: `flat`, `slightly_engorged`, `engorged`, or `unknown`. |
| `--hours-since-removal` | no | `24` | Hours since the tick was removed. |
| `--doxycycline-safe` / `--doxycycline-unsafe` | no | `--doxycycline-safe` | Optional known safety flag; omit when unknown. |
| `--tick-count` | no | `1` | Number of attached ticks represented by the estimate. |
| `--model-name` | no | `linear_blend_baseline` | County-week prior model branch. |
| `--seasonality-source-id` | no | `cdc_seasonality_week_2023` | Weekly seasonality source used for the prior. |
| `--pretty` | no | `--pretty` | Pretty-print JSON output. |

### 3.3. Successful Response Shape

```json
{
  "county_fips": "24003",
  "county_name": "Anne Arundel County",
  "query_date": "2026-05-26",
  "mmwr_year": 2026,
  "mmwr_week": 21,
  "disease": "lyme",
  "single_bite_risk_score": 8,
  "single_bite_risk_band": "elevated",
  "single_bite_risk_score_raw": 8.05,
  "pep_consideration": "meets_cdc_consideration_criteria",
  "pep_criteria": [
    {
      "criterion": "attachment_duration",
      "status": "meets",
      "explanation": "CDC clinician guidance uses estimated attachment of at least 36 hours or engorgement as a key Lyme prophylaxis consideration."
    }
  ],
  "baseline_context": {
    "county_week_risk_score": 7,
    "county_week_risk_category": "high",
    "model_name": "linear_blend_baseline"
  },
  "input_summary": {
    "tick_species": "ixodes_scapularis",
    "tick_stage": "nymph",
    "attachment_hours": 40.0,
    "engorgement": "engorged",
    "hours_since_removal": 24.0,
    "doxycycline_safe": true,
    "tick_count": 1
  },
  "evidence_modifiers": {
    "location_season": 0.7,
    "tick_species": 1.0,
    "tick_stage": 1.0,
    "attachment": 1.15
  },
  "caveats": [
    "not_calibrated_absolute_probability",
    "not_diagnosis_or_treatment_recommendation",
    "symptoms_override_model_seek_care"
  ],
  "risk_interpretation": "Single-bite Lyme decision-support score on a 1-10 scale...",
  "clinical_disclaimer": "TickBiteRisk is for informational and educational purposes only...",
  "guidance_links": [
    {
      "title": "CDC: What to do after a tick bite",
      "url": "https://www.cdc.gov/ticks/after-a-tick-bite/index.html"
    }
  ]
}
```

### 3.4. Runtime Behavior

- The county-week baseline is used as local/seasonal context.
- The score adjusts that context with tick identity, life stage, attachment
  duration, engorgement, and tick count.
- The response separately reports CDC prophylaxis consideration criteria as
  `meets`, `not_met`, or `uncertain`.
- Unknown inputs are allowed and generally produce uncertain criteria rather
  than false certainty.
- The response is not an absolute infection probability.
- Symptoms are not model inputs; symptoms should prompt medical care regardless
  of score.

---

## 4. Current Static Runtime: `tickbiterisk risk export-static`

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --model-summary-path build/etl/model-comparison/model_comparison_summary.csv \
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

## 5. Roadmap HTTP API

The roadmap HTTP API may eventually expose the current local runtime contracts
over HTTP. That service is not implemented in v0.

Possible future endpoint:

```text
GET /risk/bite?fips=24003&date=2026-05-26&tick_species=blacklegged&attachment_hours=40
```

Possible future parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `fips` | string | yes | County FIPS code. |
| `attachment_hours` | number | no | Attachment duration in hours. |
| `k` | integer | no | Number of attached ticks. |
| `date` | `YYYY-MM-DD` | no | Calendar date for MMWR week and seasonal context. |
| `pretty` | boolean | no | Pretty-print JSON output. |

Possible future response concepts:

- same fields as the local `risk lookup` and `risk single-bite` JSON contracts,
- uncertainty or credible interval,
- model/source metadata,
- explicit clinical caveats and CDC guidance links.

Before this HTTP API is built, it needs separate implementation, validation,
security review, dependency wiring, OpenAPI generation, and product wording
review.

*Last updated: 2026-05-27*
