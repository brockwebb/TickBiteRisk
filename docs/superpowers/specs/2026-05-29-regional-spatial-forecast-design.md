# Regional Spatial Forecast Design

## Decision

TickBiteRisk forecasts reported Lyme risk for every county-equivalent in
Delaware, District of Columbia, Maryland, Pennsylvania, Virginia, and West
Virginia. Counties are observation units and public reporting units, not
ecological boundaries. State is retained for source caveats, rollups, labels,
and display, but state borders do not constrain model features.

## Spatial Model Concept

The ecological process is treated as a continuous regional surface observed
through county-level aggregates. County rows are independent records in the
data panel, but neighboring records are expected to have spatially correlated
errors because counties share habitat, weather, host ecology, human exposure
patterns, and surveillance regimes.

The first spatial layer is a cross-border county adjacency graph derived from
official Census TIGERweb county geometry. Neighbor features can use counties
across state lines. For example, a Maryland county can have Pennsylvania,
Delaware, Virginia, West Virginia, or District of Columbia neighbors when the
geometry shares a boundary segment.

## Forecast-Safe Rules

Spatial forecast features must be based only on information available at the
forecast origin. Neighbor incidence for forecast year Y is built from origin
year Y-1 or earlier outcomes, never same-year target outcomes and never
validation-row artifacts copied forward.

The regional public/product default remains separate from research branches.
Cross-border spatial features are research diagnostics until rolling-origin
tests show stable improvement and a separate public branch decision is made.

## Source And Provenance

The regional county graph uses the Census TIGERweb `State_County` county layer
queried as GeoJSON for state FIPS `10`, `11`, `24`, `42`, `51`, and `54`.
Raw or normalized geometry is stored under ignored ETL build output, and the
adjacency CSV records source URL hash, method, and quality flags.

## Current Slice

The current build slice materializes the regional county adjacency graph. It
does not yet promote a public forecast branch, and it does not change the
Maryland static dashboard score. Later slices can join this graph into regional
incidence stress tests, regional annual forecasts, and cluster/capacity
diagnostics.
