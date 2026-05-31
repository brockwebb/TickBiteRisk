# Executive Summary

Draft status: working draft derived from internal lab notes; not release-ready.

Internal evidence record: docs/research/lab-notes

## Product Boundary

TickBiteRisk is a research and information product for relative reported Lyme
disease pressure. The current public-facing Maryland surface uses derived
forecast artifacts and source metadata, not a live clinical service.

This draft should state the boundary plainly: the score is contextual,
surveillance-derived, and relative. It is not diagnosis, personal infection
probability, or treatment guidance.

## High-Level Methods

The current workflow starts from county-year reported Lyme surveillance and
population denominators, builds annual reported-incidence forecasts, allocates
selected annual forecasts across CDC national Lyme onset seasonality, and maps
weekly predicted reported-incidence pressure onto a relative display score.

The Maryland public branch and regional research branches must remain distinct.
Branch availability is not public promotion.

## Current Status

Rolling-origin validation, calibration gates, model cards, source catalogs, and
human-in-the-loop review determine whether a branch is eligible for public use.
Current exploratory regional, calibration, and Bayesian update materials remain
research review evidence unless later gates approve them.
