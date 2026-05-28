# TickBiteRisk Software Requirements Specification

Version: 0.2 draft  
Date: 2026-05-24  
Scope: Maryland tick-risk data warehouse, model evaluation, and risk-score product

Implementation status: the first ETL slices are implemented through source parsing, Maryland Lyme reconciliation, CDC disease-onset seasonality baselines, tick-status normalization and feature materialization, Census county reference/area, Census population denominators, Maryland DNR deer harvest density features, NOAA station audit/backfill tooling, NOAA weekly/monthly feature generation, model feature assembly, baseline backtesting, county-week seasonal risk forecasts, runtime lookup/static export, and Postgres-ready schema.

## 1. Purpose

TickBiteRisk will produce a Maryland-focused tickborne disease risk score that translates messy surveillance, ecology, weather, and vector data into a transparent 1-10 relative risk signal.

The product is informational and educational. It is not medical advice, diagnosis, or a treatment recommendation system.

## 2. Product Goal

For a Maryland location and date or season, return:

- A 1-10 tick risk score.
- A plain-language risk category.
- A short explanation of the strongest drivers.
- Source-quality labels.
- A methodology trail that explains what data were used and where uncertainty remains.

The first modeled disease target is Lyme disease. Other tickborne diseases are stored and analyzed as supporting context until their source continuity and geography are good enough for separate scores.

## 3. Initial Geographic Scope

The MVP is Maryland-only:

- 23 counties.
- Baltimore City.
- ZIP codes are mapped to county/jurisdiction where possible.
- For ZIP codes spanning multiple counties, the system may return a weighted or multi-county result only after ZIP-to-county crosswalk data is added.

The immediate user test case is ZIP `21146`, which maps primarily to Anne Arundel County.

A future regional iteration should treat the current scope as Maryland-first,
not Maryland-only. Candidate expansion jurisdictions are West Virginia,
Virginia, Pennsylvania, Delaware, and Washington, DC / the District of
Columbia, gated by county or county-equivalent outcome data, population
denominators, geography, source terms, and time-aware validation.

## 4. Users

Primary users:

- Maryland residents deciding how cautious to be outdoors.
- Hikers, parents, scout leaders, coaches, and camp planners.
- Data-science learners reviewing a transparent public-health model.

Secondary users:

- Public-health analysts.
- Clinicians or educators who need source-backed local context.

## 5. Data Principles

The system must:

- Preserve raw source files with checksums and retrieval metadata.
- Normalize sources into a warehouse rather than relying on ad hoc spreadsheets.
- Separate raw observations from reconciled model inputs.
- Label every derived feature with source and transformation lineage.
- Avoid redistributing restricted source data when terms are unclear.
- Prefer derived risk scores and aggregate features for product output.
- Keep raw/private data, credentials, and warehouse dumps out of git.
- Publish only derived public data products unless a source is clearly redistributable.
- Never imply that `no records` means absence of ticks or pathogens.

## 6. Functional Requirements

### FR1: Source Manifest

The system must maintain a source manifest with:

- Source ID.
- Owner/publisher.
- Local file path or acquisition URL.
- Format.
- Geography.
- Time coverage.
- Model role.
- Acquisition status.
- ETL status.
- Redistribution status.
- Known limitations.
- SHA-256 checksum for local files.

### FR2: Raw Vault

The system must support a raw-file vault. Raw inputs are preserved unchanged and registered in the manifest.

### FR3: Warehouse

The system must load normalized data into Postgres/PostGIS or an equivalent local warehouse.

Initial normalized tables:

- `source_files`
- `md_jurisdictions`
- `lyme_public_use_raw`
- `lyme_county_year_source_values`
- `lyme_county_year_reconciled`
- `tick_vector_status`
- `tick_pathogen_status`
- `lone_star_status`
- `all_tbd_2022_county`
- `nssp_coverage`
- `county_reference`
- `maryland_dnr_deer_harvest`
- `county_population_year`
- `weather_locations`
- `weather_daily`
- `weather_features_weekly`
- `weather_features_monthly`
- `weather_features_seasonal`
- `seasonality_observations`
- `seasonality_baseline`
- `model_feature_matrix`
- `model_backtest_runs`
- `county_week_seasonal_risk_baseline`
- `risk_score_scale`
- `risk_scores`

### FR4: Lyme Outcome Reconciliation

The system must reconcile Maryland county-year Lyme values across:

- CDC public-use aggregated geography files.
- CDC county geodata file.
- CDC Lyme dashboard county-count export.
- Maryland Department of Health PDF/table sources when parsed.
- `AllTBD2022_Public` as noncanonical comparator.

The reconciliation output must include:

- `county_fips`
- `year`
- source values
- selected canonical value
- selection rule
- flags for conflicts and source discontinuities

### FR4A: Disease-Onset Seasonality

The system must ingest CDC Lyme disease-onset seasonality exports:

- Monthly onset cases by year.
- MMWR-week onset cases by year.

The seasonality ETL must normalize each period to an annual share within year and grain, because dashboard onset totals may not equal final annual surveillance totals.

The seasonality baseline output must include empirical period summaries and prediction bands:

- mean, median, minimum, and maximum cases.
- mean and median annual share.
- 80 percent and 95 percent empirical share bands.
- peak rank.
- cumulative mean share.
- feature quality flags.

The baseline is a national disease-onset prior, not a county-specific predictor. Outputs must carry `national_curve_not_county_specific`, `shares_normalized_by_annual_total`, and `empirical_prediction_band`.

### FR4B: County-Week Seasonal Risk Forecast

The system must convert annual held-out Lyme prediction rows into a product-shaped county-week risk forecast by combining:

- one selected annual model branch from `model_comparison_predictions.csv` or a legacy `model_backtest_predictions.csv` artifact.
- one selected weekly seasonality branch from `seasonality_baseline.csv`.
- an explicit relative score scale defined by benchmark quantile and headroom multiplier.

The county-week output must include predicted weekly incidence, empirical seasonality bands, predicted weekly cases, a bounded 1-10 relative risk score, risk category, seasonality source id, scale denominator, and feature quality flags.

The scale output must preserve the selected model name, seasonality source id, benchmark quantile, headroom multiplier, input file SHA-256 values, benchmark weekly incidence, denominator, and score-row count. Distinct model/source/scale configurations must be able to coexist without overwriting each other.

This forecast is not weather-adjusted. Outputs must carry `relative_seasonal_baseline`, `static_seasonality_prior`, and `not_weather_adjusted`.

### FR4C: Runtime Risk Lookup

The system must expose a local runtime lookup over the derived county-week risk forecast before the full HTTP API is implemented.

The lookup must:

- read `county_week_seasonal_risk_baseline.csv` without requiring raw source files, Postgres credentials, or live network access.
- accept `county_fips` and calendar date, convert the date to CDC MMWR year/week, and return the matching county-week forecast row.
- use the requested MMWR year when present and otherwise fall back to the latest available forecast year for that county/week with explicit quality flags.
- require explicit score-scale selectors when multiple benchmark/headroom configurations overlap for the same county/week.
- return JSON-friendly fields for risk score, category, weekly incidence bands, model/source metadata, feature quality flags, backtest assumption flags, CDC guidance links, and a plain-language medical disclaimer.

The lookup output must not be presented as per-bite infection probability, diagnosis, treatment guidance, or weather-adjusted forecast.

### FR4D: Single-Bite Runtime

The system must expose a local single-bite runtime over the derived county-week
risk forecast before a full HTTP API is implemented.

The single-bite runtime must:

- be callable as `tickbiterisk risk single-bite`.
- read `county_week_seasonal_risk_baseline.csv` without requiring raw source
  files, Postgres credentials, or live network access.
- accept `county_fips`, calendar date, tick species, tick stage, attachment
  hours, engorgement, optional hours since removal, optional doxycycline safety,
  and tick count.
- use the county/date lookup result as the local and seasonal context.
- return a single-bite Lyme decision-support score on a 1-10 scale.
- return CDC prophylaxis consideration criteria as separate `meets`, `not_met`,
  or `uncertain` statuses.
- include CDC guidance links, a clinical disclaimer, caveats, normalized inputs,
  evidence modifiers, and forecast context.

The single-bite runtime must not be presented as an absolute infection
probability, diagnosis, treatment recommendation, or substitute for a healthcare
professional. Symptoms must remain outside the model and should prompt medical
care regardless of score.

Plain-language public wording should say: this is not an absolute infection probability.

### FR4E: Static Public Risk Export

The system must expose a static export command over the derived county-week risk forecast for a public web/runtime bundle.

The export must:

- read `county_week_seasonal_risk_baseline.csv` without requiring raw source files, Postgres credentials, or live network access.
- require one unambiguous score branch across model name, seasonality source, score-scale settings, and source artifact versions.
- publish the latest available forecast row per county/MMWR week rather than all historical held-out rows.
- write `md_county_risk_weekly.json`, `md_county_metadata.json`, `model_card.json`, `source_catalog.json`, and `static_export_manifest.json`.
- include CDC guidance links, plain-language caveats, source SHA-256 provenance, score-scale metadata, quality flags, and a clinical disclaimer.
- avoid raw source tables, private warehouse rows, credentials, and terms-unclear source extracts.

The static export must be framed as a relative Maryland county-week Lyme forecast, not a per-bite infection probability, diagnosis, treatment recommendation, or weather-adjusted forecast.

### FR4F: Static Dashboard Prototype

The system must expose a static dashboard under `public/` that reads only
`public/data` assets, requires no backend credentials, and presents the
county-week Lyme forecast with accessible map, county list, detail panel, CDC
guidance links, and plain-language caveats. The dashboard must not describe the
score as diagnosis, treatment guidance, personal infection probability, or
weather-adjusted forecast.

Future dashboard iterations should revisit the time control. The current date
dropdown is sufficient for lookup, but a temporal slider, year-over-year
comparison mode, or small-multiple view may better show seasonal dynamics and
apparent spatial shifts. Any animation or change map must distinguish observed
surveillance/reporting patterns from proven tick migration, pathogen migration,
or individual exposure.

### FR5: Tick and Pathogen Status

The system must ingest county-level vector/pathogen status from local CDC workbooks:

- Ixodes status.
- Ixodes pathogen status.
- Lone star tick status.

These are static/cumulative stratification layers. They are not prevalence estimates.

The model feature assembly must treat these layers as opt-in historical proxies. If current cumulative tick status is joined into county-year training rows, the output must flag `current_status_retrospective_proxy`, `status_only_not_prevalence`, and `no_records_not_absence` where applicable.

### FR6: Weather Acquisition

The system must support Maryland daily weather acquisition and feature generation:

- Build Maryland county weather locations from Census Gazetteer county internal points.
- Use NOAA CDO/GHCND daily station observations as the primary observed historical weather backfill source.
- Retain Open-Meteo historical weather/reanalysis as a secondary comparison or gap-fill source where useful.
- Support bounded county/date backfills before full Maryland range runs.
- Plan full NOAA historical weather coverage for at least 1992-01-01 through the current year.
- Provide a NOAA station coverage audit command that checks Maryland county station candidates against the requested historical range and records `ok`, `needs_fallback`, or `error` before a large daily pull.
- Provide a bounded NOAA county backfill command that discovers county stations, selects long-coverage stations, fetches daily observations for selected stations, and writes both `noaa_ghcnd_stations` and `noaa_ghcnd_daily_observations` CSV outputs.
- Provide a Maryland NOAA orchestration command that runs the county backfill for all Maryland jurisdictions or an explicit county subset, reports county failures, and supports small smoke runs before the full historical acquisition.
- Support an explicit nearest eligible Maryland station fallback for station audit and Maryland backfill when a county lacks an internal station with enough coverage for the requested range.
- Preserve the target county FIPS in fallback outputs while retaining the source NOAA station ID and station metadata for provenance.
- Split NOAA CDO daily requests into calendar-year windows and paginate station/daily responses before pivoting daily datatypes, so long historical backfills respect API date limits and do not silently stop at the first API page.
- Write raw NOAA GHCND station observations to `noaa_ghcnd_daily_observations`; daily is not the modeling granularity.
- Aggregate daily weather to weekly, monthly, and seasonal features. `weather_features_weekly` is the primary weather modeling grain because warm, humid, or wet spells can matter inside a month.
- Retain `weather_features_monthly` and seasonal features as slower climate/context features, not the primary tick-activity driver.
- Preserve NOAA unavailable fields as null rather than imputing unsupported humidity, soil, evapotranspiration, or rain-split values.
- Label source-specific limitations with `feature_quality_flags`, including `no_humidity`, `no_soil_data`, `no_evapotranspiration`, and `no_rain_split` for NOAA-derived feature rows.
- Include `days_observed`, `expected_days`, and completeness flags on weekly/monthly features so partial smoke/backfill ranges cannot be mistaken for complete periods.
- Compute trailing 10-year weather normals and anomalies without future leakage; a feature for ISO week or month `T` may only use weather observations available before `T`.

NOAA CDO must read credentials from environment variables such as `NOAA_TOKEN` only.

### FR7: County Reference And Area

The system must acquire Maryland county reference geography for density denominators and stable joins:

- Use the Census 2024 Gazetteer county file as the primary lightweight reference.
- Store `county_reference` keyed by `county_fips`.
- Preserve county/state FIPS, county name, land area, water area, internal-point latitude/longitude, source label, and source URL hash.
- Use land square miles for later deer harvest density and other county-normalized ecology features.

### FR8: Population Denominators

The system must acquire Maryland county-year population denominators for incidence-rate modeling:

- Use Census PEP/intercensal APIs as the primary county-year population source.
- Cover Lyme outcome years starting in 1992 where Census API support is available.
- Store denominators in `county_population_year` keyed by `county_fips, year`.
- Preserve Census dataset, source ID, vintage, and source URL hash for provenance.
- Read `CENSUS_API_KEY` from the environment when required; never print or commit the key.

### FR9: Host Ecology Features

The system must include host/ecology feature slots for:

- Maryland deer harvest by county/year.
- Maryland mast/acorn survey indicators where available.
- Optional canine sentinel data if licensing/access can be resolved.

Maryland deer harvest ETL must:

- Pull published Maryland DNR harvest report tables.
- Pull text-extractable Maryland DNR annual report PDFs where they add practical history.
- Normalize harvest seasons to `season_start_year` and `season_label`.
- Preserve species rows where DNR splits white-tailed deer and sika deer.
- Derive all-deer totals for split counties when the source table only provides species rows.
- Join Census land square miles and compute `harvest_per_sqmi`.
- Treat the result as a deer abundance/activity proxy, not a direct deer population estimate.
- Catalogue older scanned/image-heavy annual reports separately instead of forcing unreliable OCR output into the model.

Mast/acorn and veterinary sentinel sources may be missing in the first ETL slice, but the schema and manifest must track them.

### FR10: Risk Score

The product risk score is 1-10.

Internally, models may produce continuous risk or incidence estimates. The display score should map to a robust Maryland historical benchmark:

```text
score_raw = 10 * modeled_risk / (1.2 * historical_high_benchmark)
score = clamp(round(score_raw), 1, 10)
```

The benchmark should initially be the 95th percentile of modeled Maryland county-week risk, with monthly or county-year benchmarks retained for slower retrospective summaries. The 20 percent headroom prevents a single historical maximum from saturating the scale.

Display categories:

- `1-2`: very low
- `3-4`: low
- `5-6`: moderate
- `7-8`: high
- `9-10`: very high

The first product-shaped risk artifact is a relative county-week seasonal forecast. It combines a selected annual prediction branch, currently from the model-comparison artifact by default, with the CDC national MMWR-week disease-onset curve and maps the resulting weekly incidence estimate to the 1-10 scale. It must be labeled as `relative_seasonal_baseline`, `static_seasonality_prior`, and `not_weather_adjusted` until weather, habitat, host, and intervention modifiers are explicitly added.

The first runtime surfaces for this score are the local `tickbiterisk risk lookup` command and the `tickbiterisk risk export-static` public JSON bundle. Both preserve the non-medical, relative-forecast framing.

### FR11: Model Backtesting

Every candidate model must be evaluated through time-aware backtests.

For prediction year `Y`, training data must only include data available through `Y-1` unless the run is explicitly labeled as retrospective reconstruction.

Backtests must report:

- Train years.
- Test year.
- Feature set.
- Model family.
- Target definition.
- Metrics.
- Source version/checksums.
- Whether weather is reconstruction mode or forecast mode.

The first backtest lane is an annual county-year baseline benchmark. It does not prove causal effects or intervention impact. Outputs must flag that results are observational, intervention history is unmodeled, and surveillance/reporting changes can alter the target.

### FR12: Model Bake-Off

The system must support multiple modeling lanes before choosing a product model:

- Historical baseline.
- Poisson or negative-binomial GLM.
- Regularized linear model.
- Bayesian hierarchical model.
- PCA-assisted model.
- Random forest or gradient boosting.
- Ensemble model.

No model family is accepted because it is fashionable or intuitive. Product use requires backtest evidence.

### FR13: User Explanation

For any generated score, the system must provide a compact explanation:

- Historical disease pressure.
- Seasonality.
- Weather/climate contribution.
- Tick/vector status.
- Habitat/host contribution when available.
- Source-quality warnings.

### FR14: Export

The system must export model-ready tables as Parquet or CSV for analysis and reproducibility.

## 7. Non-Functional Requirements

### NFR1: Reproducibility

ETL must be idempotent. Re-running an ingest should not create duplicate facts.

### NFR2: Provenance

Every normalized row must trace to a source ID, dataset ID or file checksum, and ingest timestamp.

### NFR3: Secret Handling

Tokens and credentials must not be committed to git. NOAA credentials are local-only and read from environment variables such as `NOAA_TOKEN`.

Raw data directories, private warehouse outputs, and local database dumps must be ignored by git.

### NFR4: Performance

The Maryland MVP may run locally. ETL jobs should be acceptable on a laptop. Heavy national geodata processing is optional unless needed for Maryland extraction.

### NFR5: Transparency

The product must prefer honest source-quality labels over false precision.

The public web product must use a derived data product with source citations and methodology notes. Raw source files, local warehouse dumps, and terms-unclear source extracts remain private.

### NFR6: Safety

The product must display plain language that it is informational and educational only, not medical advice, diagnosis, or treatment guidance. It must recommend following CDC guidance and consulting a qualified healthcare professional about individual situations.

## 8. Modeling Guidance

### Baseline Model

Start with county historical average, lagged incidence, and seasonality. This is the minimum benchmark all other models must beat.

### GLM

Use Poisson or negative-binomial models for count outcomes with population offsets when population data is available. These provide interpretable coefficients and help detect obvious feature issues.

### Bayesian Hierarchical Model

Use Bayesian partial pooling when sparse counties, missing years, or uncertainty intervals matter. It is a strong candidate for final score generation, but only after ETL and reconciliation are stable.

### PCA

Use PCA after weather/habitat feature generation to inspect correlated predictors and optionally reduce feature space. PCA is exploratory first, not the first production model.

### Random Forest / Gradient Boosting

Use tree models as nonlinear benchmarks. They may capture interactions among weather, habitat, and host features but must use time-split validation. They should not be trusted for extrapolation outside observed climate/source regimes.

### Ensemble

An ensemble is allowed if model branches show complementary backtest strengths. A simple linear/blended ensemble is preferred before complex stacking.

## 9. Acceptance Criteria For The Next Build Slice

The next build slice is accepted when:

- `docs/data-manifest.md` catalogs all known local and missing sources.
- A raw source manifest can be generated from local files.
- Postgres schema or equivalent local warehouse schema is defined.
- Maryland county-year Lyme canonical table can be produced for available years.
- Reconciliation checks identify mismatches between CDC, MDH, geodata, and `AllTBD2022_Public`.
- Weather acquisition has a runnable small-range fixture path.
- CDC Lyme seasonality baselines can be materialized for monthly and MMWR-week disease-onset curves.
- At least one baseline backtest can run on a Maryland county-year panel.
- A county-week seasonal risk forecast can be materialized from model-comparison predictions and CDC MMWR-week seasonality.

## 10. Open Questions

- Which source should be canonical for 2024 county Lyme counts after MDH PDF extraction?
- Are 2007-08 through 2010-11 Maryland DNR deer annual report tables worth OCR/manual extraction, given older tick outcome years are less reliable and land-use/ecology may have shifted?
- Can mast survey reports be converted into a useful Western Maryland feature without over-generalizing statewide?
- Can CAPC canine data be used legally and practically as a sentinel feature?
- Can park attendance or trail-use records become a useful exposure denominator, despite the gap between recreation location and Lyme residence/reporting county?
- Should the first user-facing score be county-week or date-with-seasonal-overlay?
- Should the dashboard keep a date dropdown, move to a temporal slider, or
  support both for year-over-year comparison and apparent spatial shifts?
- Should ZIP-code lookup use Census ZCTA crosswalks or a commercial/local geocoder?
