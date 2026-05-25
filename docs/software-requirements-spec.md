# TickBiteRisk Software Requirements Specification

Version: 0.2 draft  
Date: 2026-05-24  
Scope: Maryland tick-risk data warehouse, model evaluation, and risk-score product

Implementation status: the first ETL slices are implemented through source parsing, Maryland Lyme reconciliation, tick-status normalization, Census county reference/area, Census population denominators, Maryland DNR deer harvest density features, NOAA station audit/backfill tooling, NOAA weekly/monthly feature generation, and Postgres-ready schema. Model feature assembly and backtesting are the next planned slices.

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
- `model_feature_matrix`
- `model_backtest_runs`
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

### FR5: Tick and Pathogen Status

The system must ingest county-level vector/pathogen status from local CDC workbooks:

- Ixodes status.
- Ixodes pathogen status.
- Lone star tick status.

These are static/cumulative stratification layers. They are not prevalence estimates.

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
- Normalize harvest seasons to `season_start_year` and `season_label`.
- Preserve species rows where DNR splits white-tailed deer and sika deer.
- Derive all-deer totals for split counties when the source table only provides species rows.
- Join Census land square miles and compute `harvest_per_sqmi`.
- Treat the result as a deer abundance/activity proxy, not a direct deer population estimate.

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
- At least one baseline backtest can run on a Maryland county-year panel.

## 10. Open Questions

- Which source should be canonical for 2024 county Lyme counts after MDH PDF extraction?
- Can Maryland DNR deer harvest be downloaded as structured county-year data?
- Can mast survey reports be converted into a useful Western Maryland feature without over-generalizing statewide?
- Can CAPC canine data be used legally and practically as a sentinel feature?
- Should the first user-facing score be county-week or date-with-seasonal-overlay?
- Should ZIP-code lookup use Census ZCTA crosswalks or a commercial/local geocoder?
