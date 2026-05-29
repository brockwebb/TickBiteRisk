# TickBiteRisk ETL Pipeline

## Current v0 ETL pipeline

The ETL layer turns acquired source files into reproducible Maryland county-year
and county-week artifacts. This pipeline builds research-grade static forecast
artifacts and a static public dashboard. It does not run a live backend forecast
service.

No live weekly ED scaler is wired into the current product. Weather, ecology,
deer, construction, and tick surveillance fields are model features or research
candidates until backtesting shows they improve the public score.

## Acquisition provenance contract

Every new acquired source should leave a saved, secret-free acquisition trail
before it feeds model features or public artifacts. At minimum, the trail should
record the source URL or API endpoint, a rerunnable command or procedure, the
citation URL or official evidence page, local raw path, checksum, retrieval timestamp,
parser method, extraction quality, redistribution/access notes, and modeling
caveats. Query URLs that include credentials must be logged only in
sanitized form; secrets stay in the local environment and never in manifests,
docs, or public JSON.

`tickbiterisk etl ecology-sources` now writes this contract into its raw source
manifest for catalog-style acquisitions. Because that command only acquires raw
files/pages, parser method and extraction quality are recorded as explicit
not-yet-evaluated placeholders until a downstream parser writes source-specific
extraction summaries. Direct API and raw-source ETL run manifests use
`acquisition_provenance.csv`; ENSO, EnviroAtlas, USDM drought, Census population, regional population, regional demographics, ACS exposure, building permits, county reference, deer harvest, Open-Meteo weather backfill, NOAA weather primitives, NOAA weather backfill, Lyme outcomes, aggregate Lyme validation, regional Lyme outcomes, regional signals, Massachusetts DPH syndromic ED, New Jersey DOH reportable tickborne, Maine JMMC tickborne county rates, NSSP coverage, seasonality baseline, tick status, and mast/acorn
are wired to that pattern,
preserving request URL, rerunnable command, parser/extraction status, derived
artifact checksums, and source caveats. Other API ETLs may still keep lineage in
source URL hashes and output fields, but this is the target shape for future
request/run manifests as those sources graduate into the modeling lane.
Run `tickbiterisk etl provenance-audit --root-dir build/etl` to scan
`acquisition_provenance.csv` and `source_manifest.csv` files for source URLs,
citation URLs, rerunnable commands, secret-free requests, derived-artifact
checksums, retrieval timestamps, parser methods, extraction quality, and
source caveats before promoting new data into model features or public
artifacts.

## Main flow

1. `tickbiterisk etl lyme-outcomes`
   - Reads ignored raw CDC Lyme source files and, when present, the official
     MDH 2013-2024 Lyme PDF.
   - Reconciles Maryland county-year Lyme counts across CDC public-use,
     dashboard, and geodata sources.
   - Includes MDH 2024 rows only, preserving CDC as canonical for overlapping
     2013-2023 history and flagging the 2024 state/probable-only caveats.
   - Writes `lyme_county_year_reconciled.csv` and
     `acquisition_provenance.csv` with official CDC/MDH source URLs, local
     raw-file checksums, parser method, contributed row count, and the
     surveillance-regime caveats needed by forecasting models.

1b. `tickbiterisk etl lyme-aggregate-validation`
   - Normalizes CDC dashboard exports for state/locality, U.S. Census region,
     and national Lyme cases/rates.
   - Writes `cdc_lyme_state_year.csv`, `cdc_lyme_region_year.csv`,
     `cdc_lyme_national_year.csv`, and `acquisition_provenance.csv`.
   - These rows are aggregate validation and regional-capacity anchors only;
     they are not county outcomes or direct exposure observations.

1b2. `tickbiterisk etl wv-vectorborne-summary`
   - Reads ignored local West Virginia OEPS Vectorborne Disease Summary PDFs
     downloaded from the official Arboviral Diseases page.
   - Extracts text from Table 3 for provisional confirmed/probable tickborne
     disease counts and counties-reported coverage.
   - Writes `wv_vectorborne_state_summary.csv` and
     `acquisition_provenance.csv`.
   - These rows are West Virginia state aggregate validation/context only.
     They do not provide county rows; county maps are not digitized.

1b3. `tickbiterisk etl mass-dph-syndromic-ed`
   - Reads ignored local Massachusetts DPH DOCX reports downloaded from the
     official Monthly Tick-borne Disease Reports page.
   - Extracts Table 1 county residence emergency-department visit totals,
     tickborne-disease diagnosis visit counts, and rates per 10,000 visits.
   - Writes `mass_dph_syndromic_ed_county_summary.csv` and
     `acquisition_provenance.csv`.
   - These rows are Massachusetts DPH syndromic ED exposure/surveillance
     context only. They are not Lyme incidence, not tick-bite counts, not a
     confirmed disease truth label, and not model input in this slice.
   - The source combines Dukes and Nantucket in one row; the ETL preserves that
     combined geography instead of assigning it to one county FIPS.

1b4. `tickbiterisk etl nj-doh-reportable-tickborne`
   - Reads ignored local New Jersey DOH 2024 Reportable Communicable Disease
     Report and Technical Notes PDFs downloaded from the official Reportable
     Disease Statistics page.
   - Extracts supported tickborne rows for state total and New Jersey counties:
     alpha-gal syndrome, babesiosis, ehrlichiosis/anaplasmosis subcategories,
     Lyme disease, Powassan, spotted fever group rickettsiosis, and tularemia.
   - Writes `nj_doh_reportable_tickborne_county_year.csv` and
     `acquisition_provenance.csv`.
   - These rows are Northeast extension state-source context only. They are not
     a confirmed disease truth label, not public-default, and not model input in
     this slice.
   - The Technical Notes are preserved in provenance because they document 2022
     Lyme laboratory-based surveillance, 2024 anaplasmosis/ehrlichiosis
     reporting changes, alpha-gal undercount caveats, and low-count
     interpretation limits.

1b5. `tickbiterisk etl maine-jmmc-tickborne-rates`
   - Reads the ignored local Journal of Maine Medical Center review PDF,
     downloaded from the open article page and cross-referenced to Maine
     Tracking Network as the underlying surveillance lead.
   - Extracts Table 2 county/state 2024 rates per 100,000 persons for
     anaplasmosis, babesiosis, hard tick relapsing fever, Lyme disease, and
     Powassan virus disease.
   - Writes `maine_jmmc_tickborne_county_rates_2024.csv` and
     `acquisition_provenance.csv`.
   - These rows are Maine JMMC tickborne county rates for external comparator
     context only. Maine is outside the active forecast footprint. Values are
     preliminary rates only as of 2025-01-20, not case counts, not a confirmed
     disease truth label, not public-default, and not model input in this
     slice.

1c. `tickbiterisk etl regional-population`
   - Pulls keyless static Census county population CSVs for DE, DC, MD, PA,
     VA, and WV, including the official Vintage 2025 county totals.
   - Writes `midatlantic_county_population_year.csv` and
     `acquisition_provenance.csv`.
   - These rows are denominator estimates for regional incidence/rate
     diagnostics, not exposure evidence. Boundary changes can create gaps; the
     first live run lacks Bedford city, VA denominators for 2010-2023.
   - For 2026 forecasts, the ETL derives county denominators with a simple
     trailing linear projection from official Census estimates. Rows are flagged
     `simple_linear_population_projection` and
     `no_official_2026_census_denominator` so they can be replaced when Census
     publishes observed 2026 estimates.

1c-2. `tickbiterisk etl regional-demographics`
   - Pulls keyless static Census PEP county age/sex CSVs for DE, DC, MD, PA,
     VA, and WV.
   - Writes `midatlantic_age_demographics_county_year.csv` and
     `acquisition_provenance.csv`.
   - These rows are age-structure context for human-exposure research only;
     they are not tick-bite counts, direct exposure evidence, or Lyme outcomes.

1c-3. `tickbiterisk etl acs-exposure`
   - Pulls or reads cached keyless ACS 5-year table-based summary files for
     `B01001`, `B25024`, `B25003`, and `Geos{year}5YR.txt`, plus Census
     Gazetteer county land area.
   - Writes `midatlantic_acs_exposure_county_year.csv` and
     `acquisition_provenance.csv`.
   - Supported vintages are 2023 and 2024. Use `--append` to accumulate both
     vintages into one county-year panel with key-based replacement on rerun.
   - These rows are rolling-survey residential-form, tenure, age, and density
     exposure-context proxies only. They are not tick-bite counts, direct
     exposure observations, Lyme outcomes, or public-default model inputs.
   - Raw ACS files are large and should remain cached under ignored raw storage
     after acquisition.

1d. `tickbiterisk etl regional-lyme-outcomes`
   - Reshapes the CDC county dashboard export into DE, DC, MD, PA, VA, and WV
     county/county-equivalent annual Lyme totals for 2001-2023.
   - Can append the Pennsylvania DOH official 2024 Lyme county workbook with
     `--pa-2024-workbook-path`; those rows remain flagged state-source regional
     research overlays, with suppressed county values represented as zero plus
     suppression flags.
   - Can append the Virginia VDH 2024 reportable-disease geography CSV with
     `--va-vdh-locality-csv-path`; those rows remain flagged state 2024 locality
     overlay records. Virginia localities include counties and independent
     cities, so FIPS is the canonical join key.
   - Can read the Delaware DHSS 2019-2023 Lyme HTML page with
     `--de-lyme-html-path` and write
     `regional_lyme_state_source_validation.csv` as a state-source validation
     sidecar. Those rows overlap CDC regional years and are not appended to the
     model input panel.
   - Writes `midatlantic_lyme_county_year.csv` and
     `acquisition_provenance.csv`.
   - This panel is a regional expansion/stress-test artifact for hotspot,
     spatial-neighbor, and capacity diagnostics; it does not replace the
     reconciled Maryland outcome target or the public Maryland default.

1e. `tickbiterisk etl regional-signals`
   - Derives Mid-Atlantic reported-case structure from
     `midatlantic_lyme_county_year.csv`.
   - Writes `midatlantic_regional_signals.csv`.
   - `diagnostic_*` columns describe same-year regional totals and county
     shares for retrospective hotspot/capacity review. `feature_*` columns use
     prior-year or trailing regional history and are the only columns intended
     for forecast-time model experiments.

1f. `tickbiterisk etl regional-hotspots`
   - Summarizes same-year Mid-Atlantic reported-case rank, share, hotspot
     tier, prior-year movement, and top-quintile entry/exit diagnostics.
   - Writes `midatlantic_hotspot_county_year.csv` and
     `midatlantic_hotspot_summary.csv`.
   - Every hotspot field is `diagnostic_*`; these outputs are for regional
     movement review and surveillance-regime inspection, not forecast-time
     public scoring.

1g. `tickbiterisk etl regional-incidence`
   - Joins the Mid-Atlantic reported-case panel to the Mid-Atlantic
     population denominator panel and computes county-year incidence per 100k.
   - Writes `midatlantic_lyme_incidence_county_year.csv` and
     `midatlantic_lyme_incidence_summary.csv`.
   - Missing denominators stay explicit. The first live run preserves missing
     Bedford city, VA rates for 2010-2023 rather than filling across a boundary
     change.

1h. `tickbiterisk etl regional-outcome-stress`
   - Runs rolling-origin, outcome-only stress tests against the Mid-Atlantic
     county panel.
   - Writes `regional_outcome_stress_runs.csv`,
     `regional_outcome_stress_predictions.csv`, and
     `regional_outcome_stress_metrics.csv`.
   - Compares prior-year county cases, trailing county cases, state capacity
     shares, Mid-Atlantic capacity shares, and empirical-Bayes shrunken share
     variants as transparent historical-range baselines. These are research
     diagnostics over reported case counts, not population-normalized public
     forecasts or latent true disease estimates.

1i. `tickbiterisk etl regional-incidence-stress`
   - Runs rolling-origin, incidence-rate stress tests against the Mid-Atlantic
     county incidence panel.
   - Writes `regional_incidence_stress_runs.csv`,
     `regional_incidence_stress_predictions.csv`, and
     `regional_incidence_stress_metrics.csv`.
   - Compares prior-year county incidence, trailing county incidence,
     forecast-safe analog/like-year incidence, and state/Mid-Atlantic
     empirical-Bayes shrinkage baselines as transparent historical-range tests.
     These are research diagnostics over reported incidence per 100k, not
     public forecasts or latent true disease estimates.

1i-2. `tickbiterisk etl regional-annual-forecast`
   - Typical 2026 run:
     `tickbiterisk etl regional-annual-forecast --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv --regional-population-path build/etl/regional-population/midatlantic_county_population_year.csv --target-year 2026 --as-of-date 2026-05-28 --data-cutoff-date 2023-12-31 --source-vintage cdc_lyme_county_dashboard_2023 --update-mode pre_update --output-dir build/etl/regional-annual-forecast`.
   - Projects the Mid-Atlantic reported-incidence panel into a target year
     without observed target-year Lyme outcomes.
   - Defaults the forecast origin to the latest coverage-complete incidence
     year covering the target-year forecast geography, currently 2023 for the
     CDC dashboard-based regional panel. Partial state-source overlay years and
     stale boundary-change geographies are retained for diagnostics without
     becoming the default origin unless explicitly requested.
   - Uses target-year regional population denominators. Current 2026 runs use
     projected Census denominators and preserve projection flags.
   - Writes `regional_annual_forecast_runs.csv` and
     `regional_annual_forecast_predictions.csv`.
   - Includes a horizon-matched `analog_year_county_incidence` branch. Analog
     rows preserve the matched origin year, observed outcome year, and match
     distance, and require the matched outcome to have been observed by the
     forecast origin.
   - Run and prediction rows preserve `forecast_origin_year`, `as_of_date`,
     `data_cutoff_date`, `source_vintage`, and `update_mode`; when
     `source_vintage` is omitted it falls back to the regional incidence input
     SHA-256.
   - Prediction rows intentionally omit actual, residual, error, and metrics
     columns. This is a regional forecast scaffold, not the public Maryland
     dashboard default.

1i-3. `tickbiterisk etl regional-forecast-capacity`
   - Typical 2026 run:
     `tickbiterisk etl regional-forecast-capacity --regional-incidence-path build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv --forecast-predictions-path build/etl/regional-annual-forecast/regional_annual_forecast_predictions.csv --output-dir build/etl/regional-forecast-capacity`.
   - Compares each regional annual forecast branch against historical state and
     Mid-Atlantic reported-case and incidence ranges using only rows at or
     before the forecast origin.
   - Uses the forecast branch county set for each comparison; historical years
     are counted only when every forecast county has a supported historical
     row.
   - Writes `regional_forecast_capacity_runs.csv` and
     `regional_forecast_capacity_summary.csv`.
   - This is a control-limit diagnostic for forecast review, not an observed
     target-year outcome, public Maryland branch, or latent true disease
     capacity estimate.

1j. `tickbiterisk etl regional-incidence-clusters`
   - Assigns county-years to low, moderate, high, and very-high regional
     incidence-pressure bands using only prior-year/trailing county incidence.
   - Writes `regional_incidence_cluster_runs.csv`,
     `regional_incidence_cluster_county_year.csv`, and
     `regional_incidence_cluster_summary.csv`.
   - The summary rows keep prior cluster min/mean/max incidence bands and
     same-year held-out actual incidence for diagnostics. These cluster bands
     are regional forecasting research artifacts, not selected public score
     inputs.

2. `tickbiterisk etl county-reference`
   - Builds Maryland county FIPS, names, area, and internal point reference.
   - Writes `county_reference.csv`.

3. `tickbiterisk etl census-population`
   - Fetches or refreshes county-year population denominators.
   - Use `--latest-only --append` to refresh the official Census 2024-2025
     county totals CSV without requiring a Census API key.
   - Writes `county_population_year.csv`.

4. `tickbiterisk etl noaa-weather-features`
   - Converts NOAA daily observations into weekly and monthly weather features.
   - Writes `weather_features_weekly.csv` and `weather_features_monthly.csv`.

4b. `tickbiterisk etl noaa-stations` and `tickbiterisk etl noaa-daily`
   - Pull NOAA CDO GHCND station discovery and daily station observations.
   - Write `acquisition_provenance.csv` with secret-free request URLs; the
     local `NOAA_TOKEN` request header is not logged.

4c. `tickbiterisk etl noaa-backfill-county` and
   `tickbiterisk etl noaa-backfill-maryland`
   - Orchestrate station selection plus daily station-observation pulls.
   - Write `acquisition_provenance.csv` for successful station-discovery and
     daily-observation records, using canonical NOAA CDO URLs and preserving
     selected-station IDs.

4a. `tickbiterisk etl weather-backfill-open-meteo-maryland`
   - Pulls chunked Open-Meteo archive weather at Maryland county internal
     points as a secondary reanalysis/gap-fill source.
   - Writes `weather_daily.csv`, `weather_features_weekly.csv`, and
     `weather_features_monthly.csv` under the chosen Open-Meteo output
     directory.
   - Writes `acquisition_provenance.csv` with saved chunk request URLs and
     artifact checksums.
   - `tickbiterisk etl open-meteo-weather-features` can rebuild weekly/monthly
     features from an existing Open-Meteo daily CSV without another API call.

5. `tickbiterisk etl deer-harvest`
   - Normalizes Maryland DNR deer harvest tables and text-extractable annual
     reports.
   - Writes `maryland_dnr_deer_harvest.csv` and
     `acquisition_provenance.csv`.

6. `tickbiterisk etl ecology-sources`
   - Catalogs NLCD/MRLC, Census BPS, mast/acorn, and related ecological source
     files.
   - Writes `source_manifest.csv`.

7. `tickbiterisk etl building-permits`
   - Normalizes Census county building permit data as a contact/land-use
     pressure proxy.
   - Writes `maryland_building_permits_county_year.csv`.

8. `tickbiterisk etl contact-pressure`
   - Combines building permits, population, and county area into per-capita and
     per-square-mile features, including prior-year and trailing construction
     pressure lags for modeling.
   - Writes `contact_pressure_features_county_year.csv`.

9. `tickbiterisk etl mast-acorn`
   - Extracts text-supported Western Maryland DNR rolling mast/acorn tables.
   - Writes source-report rows, extraction summaries, and
     `acquisition_provenance.csv` with PDF source URLs, parser method,
     extraction status, raw/output checksums, and study-plot caveats.
   - Optional manual observations remain separate, anecdotal, and
     not-public-default.

10. `tickbiterisk etl usdm-drought`
    - Pulls U.S. Drought Monitor county weekly DSCI and severity statistics.
    - Writes `usdm_drought_weekly.csv` and `usdm_drought_county_year.csv`.

11. `tickbiterisk etl enviroatlas-habitat`
    - Pulls EPA EnviroAtlas county landscape habitat fields for Maryland.
    - Writes `enviroatlas_county_habitat.csv`.

11a. `tickbiterisk etl enso-oni`
    - Pulls the NOAA CPC ONI ASCII table as a global ENSO climate context
      source.
    - Writes `noaa_cpc_oni_seasons.csv` and
      `noaa_cpc_oni_model_year_features.csv`.
    - Model-year rows use only complete 12-season prior years and remain
      optional; ONI is not Maryland-specific and is not a public-default input.

11b. `tickbiterisk etl enso-mei-v2`
    - Pulls the NOAA PSL MEI.v2 CSV table as a global ocean-atmosphere ENSO
      climate context source.
    - Writes `noaa_psl_mei_v2_monthly.csv` and
      `noaa_psl_mei_v2_model_year_features.csv`.
    - Monthly NOAA `-999` placeholders are retained as missing-value rows, but
      model-year rows use only complete 12-month prior years. MEI.v2 is not
      Maryland-specific, not an official CPC phase classification, and not a
      public-default input.

11c. `tickbiterisk etl tick-status`
    - Normalizes local CDC Ixodes, pathogen, and lone-star tick status
      workbooks into county status features. The default region is Maryland;
      `--region midatlantic --output-dir build/etl/tick-status-midatlantic`
      materializes DE, DC, MD, PA, VA, and WV rows for regional research.
      The current default metadata targets CDC May 2026 workbook files
      covering status through 2025 for Ixodes/pathogens and the 2025 lone-star
      map data.
    - Writes `tick_vector_status.csv`, `tick_pathogen_status.csv`,
      `lone_star_status.csv`, `tick_status_county_features.csv`, and
      `acquisition_provenance.csv` with workbook checksums, parser methods,
      row counts, and status-only/not-prevalence caveats.

11d. `tickbiterisk etl nssp-coverage`
    - Downloads or reads the public CDC NSSP county coverage table and
      normalizes Maryland emergency-care participation status.
    - Writes `nssp_coverage_county_status.csv` and
      `acquisition_provenance.csv`.
    - This is coverage feasibility only: it is not a tick-bite ED feed, not
      a Lyme outcome, and not a current public model input.

12. `tickbiterisk etl seasonality-baseline`
    - Normalizes CDC Lyme onset exports by month and MMWR week.
    - Writes `seasonality_observations.csv`, `seasonality_baseline.csv`, and
      `acquisition_provenance.csv` with official CDC source citation, raw-file
      checksums, parser method, row counts, and national-curve caveats.

13. `tickbiterisk etl model-features`
    - Joins Lyme outcomes, population, timing-safe prior-year population
      growth, prior-year Census PEP age-structure context, weather, deer,
      contact-pressure, construction lags, prior-year mast/acorn, USDM
      drought, EnviroAtlas habitat, complete prior-year ONI and MEI.v2, and
      optional surveillance features into the county-year feature matrix.
    - Age-structure values are human-exposure context proxies only; they carry
      source/vintage/hash fields and are joined from observation year N into
      model year N+1.
    - Writes `model_features_county_year.csv`.

14. `tickbiterisk etl county-adjacency`
    - Derives directed Maryland county-neighbor pairs from public county
      GeoJSON using shared boundary segments.
    - Writes `md_county_adjacency.csv`.

15. `tickbiterisk etl model-design-matrix`
    - Converts the feature panel into numeric model inputs with missingness
      indicators, optional prior-year neighbor incidence features, optional
      regional signal features, optional regional prior-incidence cluster
      features, optional prior-year age-structure features, a fixed-scale
      ecological pressure composite, and a schema sidecar.
    - Regional cluster joins use only prior-history assignment and incidence
      summary fields from `regional_incidence_cluster_county_year.csv`;
      same-year actual incidence, cases, population, run metadata, cluster IDs,
      and diagnostic summary rows are excluded from model inputs.
    - Writes `model_design_matrix_county_year.csv` and
      `model_design_matrix_schema.json`.

16. `tickbiterisk etl model-compare`
    - Runs rolling-origin comparisons across transparent baseline and ridge
      branches, including forecast spatial and forecast-safe regional
      signal/cluster lanes when those optional feature columns are present.
      Prior-year age structure is only in the ecology/exposure research lane,
      not the conservative public-safe baseline.
    - Writes `model_comparison_runs.csv`,
      `model_comparison_predictions.csv`,
      `model_comparison_intervals.csv`, `model_comparison_metrics.csv`, and
      `model_comparison_summary.csv`.

16b. `tickbiterisk etl annual-forecast`
    - Typical 2026 run:
      `tickbiterisk etl annual-forecast --design-matrix-path build/etl/model/model_design_matrix_county_year.csv --population-path build/etl/regional-population/midatlantic_county_population_year.csv --target-year 2026 --forecast-origin-year 2024 --as-of-date 2026-05-28 --data-cutoff-date 2024-12-31 --source-vintage 2024-inclusive-local --update-mode pre_update --output-dir build/etl/annual-forecast`.
    - Trains transparent annual forecast branches through the declared
      `forecast_origin_year` and scores a later `target_year` without
      requiring observed target-year Lyme outcomes. The branch set includes
      lagged outcome, empirical-Bayes shrinkage, and a forecast-safe
      `analog_year_forecast` like-years hedge based only on lagged incidence
      history features.
    - Uses a target-year population panel for the forecast denominator. Current
      2026 runs use projected denominators from official Vintage 2025 Census
      rows and preserve explicit forecast/projection flags.
    - Writes `annual_forecast_runs.csv` and
      `annual_forecast_predictions.csv`.
    - Run and prediction rows preserve `forecast_origin_year`, `as_of_date`,
      `data_cutoff_date`, `source_vintage`, and `update_mode`; when
      `source_vintage` is omitted it falls back to the design matrix SHA-256.
    - Prediction rows intentionally omit observed target, actual, residual,
      error, and coverage columns because this artifact is a true forecast, not
      a rolling-origin evaluation table.
    - Current branches are transparent lagged-outcome baselines:
      `latest_observed_incidence`, `trailing_mean_incidence`,
      `linear_blend_baseline`, and `empirical_bayes_shrinkage`. The artifact is
      the current public annual source after the county-week seasonality
      transform; rolling-origin model comparison remains the historical
      validation source for the selected branch.

17. `tickbiterisk etl model-diagnostics`
    - Summarizes comparison predictions and bootstrap intervals into research
      diagnostics for branch uncertainty, surveillance-regime checks, regional
      hotspot patterns, and capacity-sensitive error review.
    - Also writes `forecast_update_audit.csv`,
      `forecast_update_summary.csv`, and
      `forecast_calibration_summary.csv`, which compare pre-update
      rolling-origin forecasts with newly observed held-out outcomes using
      explicit as-of, data-cutoff, source-vintage, and surveillance-regime
      fields.
    - The calibration summary records empirical observed-to-predicted case
      ratios and additive incidence offsets for later Bayesian or hierarchical
      update research; it is not a public score correction.
    - Writes diagnostics under the chosen model-diagnostics output directory.

17b. `tickbiterisk etl forecast-calibration-backtest`
    - Applies forecast-safe shrunken calibration multipliers learned only from
      prior update rows for the same model branch.
    - Writes `forecast_calibration_backtest_runs.csv`,
      `forecast_calibration_backtest_predictions.csv`, and
      `forecast_calibration_backtest_metrics.csv`.
    - This is a falsification harness for calibration/update ideas. A
      calibration multiplier can remain useful as a research prior even when it
      does not improve held-out MAE enough to become a public correction.
    - Metric rows include `calibration_gate_decision` and
      `calibration_gate_reason`: only overall improvements in both incidence
      and case MAE become `candidate_review_required`; worsening or mixed
      overall results become `do_not_apply_to_public_forecast`; subgroup/year
      results remain `diagnostic_subgroup_only`.

17c. `tickbiterisk etl forecast-bayesian-update-backtest`
    - Applies a forecast-safe Gamma-Poisson Bayesian update backtest using only
      prior model-branch forecast errors as evidence.
    - Typical run:
      `tickbiterisk etl forecast-bayesian-update-backtest --predictions-path build/etl/model-comparison/model_comparison_predictions.csv --output-dir build/etl/forecast-bayesian-update-backtest`.
    - Treats predicted cases as model exposure and observed cases as evidence
      for a posterior case multiplier. The posterior is centered on a neutral
      multiplier of 1.0 before prior updates arrive.
    - Writes `forecast_bayesian_update_backtest_runs.csv`,
      `forecast_bayesian_update_backtest_predictions.csv`, and
      `forecast_bayesian_update_backtest_metrics.csv`.
    - Metric rows include `update_gate_decision` and `update_gate_reason`.
      Overall improvements in both incidence and case MAE become
      `candidate_review_required`; worsening or mixed overall results become
      `do_not_apply_to_public_forecast`; subgroup/year results remain
      `diagnostic_subgroup_only`.
    - Current live results are evidence against automatic public use: default
      Bayesian updating worsened overall MAE for all branches, while preserving
      useful posterior audit fields for future hierarchical update design.

18. `tickbiterisk etl county-week-risk`
    - Current public 2026 run:
      `tickbiterisk etl county-week-risk --predictions-path build/etl/annual-forecast/annual_forecast_predictions.csv --seasonality-baseline-path build/etl/seasonality/seasonality_baseline.csv --model-name linear_blend_baseline --output-dir build/etl/county-week-risk --replace`.
    - Applies CDC weekly Lyme seasonality to the selected annual model branch.
      The input can be a rolling-origin model-comparison prediction table or a
      true annual forecast table with `forecast_year`.
    - Carries forecast-vintage metadata into the county-week artifact. Legacy
      model-comparison inputs default to `train_end_year` as
      `forecast_origin_year`, `unspecified` as-of/cutoff dates, the source or
      design-matrix SHA carried by the prediction row as `source_vintage`, and
      `pre_update` as `update_mode`.
    - Writes `county_week_seasonal_risk_baseline.csv` and
      `risk_score_scale.csv`.

19. `tickbiterisk risk export-static`
    - Selects one unambiguous model/source/scale branch for public use.
    - Exposes the selected forecast metadata in `md_county_risk_weekly.json`,
      `model_card.json`, and `source_catalog.json` so public static bundles are
      auditable by forecast origin and source vintage.
    - Writes dashboard JSON files under `public/data`.

## Runtime lookup

The local lookup command reads the derived county-week forecast:

```bash
tickbiterisk risk lookup --county-fips 24003 --date 2026-05-26 --pretty
```

It converts the date to CDC MMWR week and returns the relative Maryland Lyme
forecast for that county-week. The value is not a personal infection
probability or a treatment recommendation.

## Idempotency and lineage

- Writers use stable keys and append/dedupe behavior or explicit replacement.
- Each derived artifact keeps source IDs, source SHA-256 values, branch labels,
  quality flags, or sidecar metadata where practical.
- Raw files live under ignored data paths.
- Public exports include model and source metadata so a static site can explain
  what produced each score.

## Source limitations kept visible

- Deer harvest is a host-pressure proxy, not direct deer population.
- Building permits are a contact/land-use pressure proxy, not proof of
  migration or exposure.
- Prior-year population growth is a demographic/contact-pressure proxy derived
  from Census denominators, not proof of exposure or new construction.
- ACS residential-form and density fields are rolling 5-year survey context,
  not annual observed exposure, tick-bite counts, Lyme outcomes, or disease
  truth. Density fields use static 2024 Census Gazetteer county land area for
  both currently materialized ACS vintages.
- The ecological pressure composite is a transparent fixed-scale average of
  timing-safe component proxies; component columns stay visible and should be
  reviewed alongside the index.
- Mast/acorn values are Western Maryland study-plot observations, not statewide
  countywide mast production; model joins use only prior-year values.
- USDM drought values are same-year retrospective observed conditions in the
  retrospective comparison, not a forecast-time drought forecast. Prior-year
  USDM drought summaries are also joined as timing-safe ecology candidates.
- EnviroAtlas habitat fields are static county context, not annual land-cover
  change.
- Same-year weather branches are retrospective comparisons unless replaced by a
  true forecast-time feature set.
- Spatial lag features use prior-year neighbor outcomes only; same-year
  neighbor outcomes are not forecast-safe.
- MDH 2024 Lyme rows are latest-outcome context, not a CDC public-use update.
  They join into local model features only because matching Census 2024
  population denominators and NOAA 2024 weather aggregates are now present.
- The current population output mixes Census API-era 2020-2023 rows with
  Vintage 2025 CSV rows for 2024-2025; use source IDs and vintages when
  comparing denominators across vintages. The regional population output also
  includes forecast-only 2026 projected denominators.

Last updated: 2026-05-29.
