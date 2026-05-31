# Regional Research

Status: draft
Primary sources: README.md; docs/regional-research-evidence.md; public/research-data/regional/model_card.json; public/research-data/regional/static_export_manifest.json
Reviewer focus: scientific/data-quality
Last checked against commit: 375a818

This chapter documents the research-only regional surface, including its county-equivalent geography, cross-border adjacency logic, localized spatial regimes, annual forecasts, intervals, and boundaries that keep exploratory regional findings separate from the public Maryland product.

## Scope

The regional research page is not the Maryland public default. It is a
research surface for inspecting Mid-Atlantic reported-incidence forecast
methods, intervals, and localized spatial-regime context.

The current regional scope includes Delaware, District of Columbia, Maryland, Pennsylvania, Virginia, and West Virginia (`DE`, `DC`, `MD`, `PA`, `VA`, and `WV`). It is meant to support scientific and data-quality review of reported-incidence forecast behavior, not personal infection probability, diagnosis, or treatment guidance.

## County-Equivalent Geography

The current regional build covers 283 county-equivalent geographies. Virginia independent cities and other county-equivalent units are part of the same forecast geography so the regional panel can preserve source geography instead of forcing everything into Maryland-style counties.

Coverage counts are evidence about the current derived build, not a guarantee that every state-source overlay is complete for every year. Rows still carry reported-case, source-vintage, suppression, population-denominator, and surveillance-regime caveats.

## Cross-Border Adjacency

Cross-border adjacency supports regional context for neighboring county-equivalents across state lines. It is useful for inspecting whether nearby jurisdictions share reported-incidence movement or localized forecast regimes.

Adjacency should not be described as proof of causal tick ecology or personal exposure. It is a structural geography feature for research diagnostics, branch comparison, and future model design.

## Localized Spatial Regimes

The current spatial-regime run id is `regional_spatial_regimes_start2007_end2024_mintrain3_lookback3_mean25p0_prior25p0_trend25p0`. The run starts in 2007, ends in 2024, uses a minimum of 3 training years, and uses a 3-year lookback.

The 2024 spatial-regime summary has 127 regimes across 283 county-equivalents. The largest 2024 regime is `2024_regime_03`, with 109 county-equivalents.

These localized regimes are research context. They can help reviewers inspect regional structure and branch errors, but they should not be presented as causal clusters, clinical risk groups, or public Maryland defaults.

## Regional Annual Forecasts

Regional annual forecasts project reported incidence for the Mid-Atlantic county-equivalent panel. They are annual reported-incidence forecast branches; downstream county-week views allocate the annual forecast over time using seasonality rather than observing county-week outcome truth.

Regional forecast rows may include branches that are useful for research inspection, such as spatial-regime or empirical-Bayes variants. A research branch can be visible on the regional page without becoming the public Maryland branch.

## Regional Forecast Intervals

The regional spatial-regime forecast interval summary artifact, `build/etl/regional-annual-forecast/regional_spatial_regime_forecast_interval_summary.csv`, has 762 rows. These interval summaries are planning aggregates, not posterior draws or a joint spatial probability model.

For 2026 forecasts from origin year 2023, the `analog_year_county_incidence` row for `2024_regime_03` (Spatial regime 3) has predicted incidence of 16.302663 per 100k. Its 80% empirical range is 4.120999 to 59.680319 per 100k, and its 95% empirical range is 0.559834 to 144.352597 per 100k.

Interval examples must always name the model branch because the same regime, forecast year, and forecast origin can have multiple branch rows.

Those intervals should be framed as empirical residual summaries for planning and review. They are not medical confidence intervals, not per-bite uncertainty, and not proof that county outcomes move jointly inside the displayed band.

## Research-Only Boundary

The regional research page may expose forecast methods, intervals, observed-fit overlays, and localized spatial-regime context for inspection. It should also preserve the caveats that regional artifacts are observational, reported-case based, and not stable true-incidence measures.

The public Maryland dashboard remains the default product. Any decision to make a regional branch public-default evidence, change map scope, revise risk color scales, or change medical/CDC guidance language requires HITL approval.
