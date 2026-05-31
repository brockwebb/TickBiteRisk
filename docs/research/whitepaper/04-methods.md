# Methods

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Annual Forecast

The primary modeled quantity is county-year reported Lyme incidence per 100,000
people. Forecast-safe branches use information available at or before the
forecast origin and avoid target-year outcomes as features.

## Seasonal Allocation

Weekly rows are display allocations of selected annual forecasts using CDC
national Lyme onset seasonality. They are not observed county-week Lyme
outcomes and do not measure weekly tick abundance.

## Predicted Score

The predicted score maps predicted weekly reported-incidence pressure onto a
relative 1-10 display scale using the selected branch, geography, benchmark
quantile, and headroom multiplier. A capped score is a display value, not a
clinical threshold.

## Forecast Percentile

Forecast percentile or typicality compares an annual forecast with the same
county's prior reported-incidence history through the forecast origin. It is
county-history context for the modeled quantity.

## Forecast Intervals

Forecast intervals, where available, summarize historical forecast residuals
around reported-incidence forecasts. They are branch- and artifact-specific
and should not be described as medical or per-bite intervals.
