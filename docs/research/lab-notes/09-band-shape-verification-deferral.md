# Band-Shape Verification Deferral

Status: draft
Primary sources: public/data/md_county_risk_weekly.json; tickbiterisk/modeling/regional_annual_forecast_intervals.py; tests/test_regional_annual_forecast_intervals.py
Reviewer focus: uncertainty-interval validation scope and forecast-horizon claims
Last checked against commit: 338ea5c
Tracking: Issue c05124e3 (B9 band-shape test gap)

## Decision

Cross-horizon band-shape verification is deferred, not missed. The row-level
interval invariants are verified; the band-SHAPE properties are explicitly
unvalidated for this release and are blocked on data that does not yet exist on
disk. Deferral here is the correct scientific posture, not a shortfall.

## What Is Verified

The interval row-level invariants hold across every published row:

- `score_low <= score <= score_high` for all 1272 public rows;
- the 95% interval contains and is at least as wide as the 80% interval for all
  rows (nested coverage);
- pytest suite green (795 passed) including the structural interval-construction
  tests (`empirical_rolling_origin_residual_quantile`, schema, hash-mismatch and
  branch-mismatch rejection).

These are internal-consistency guarantees on the intervals as published. They do
not speak to how interval width behaves across forecast years.

## What Is Deferred And Why

Three band-shape properties remain unverified:

1. monotonic interval widening across forecast years 2024 -> 2025 -> 2026;
2. tighter intervals at 2024 when the PA step-1 anchor is present;
3. wider bands on `basis_adjusted` targets versus a zero-variance-factor control.

They cannot be tested now because the published weekly file holds only forecast
year 2026, and the multi-year `public/data/regional/` artifact is not on disk.
Testing a cross-year property against single-year data leaves only two bad
options: mock the missing years (which tests the fixture, not the pipeline), or
assert against rows that do not exist (vacuously true, worse than no test).

Governing epistemic rule, identical to the out-of-region DiD dead-end in
[08-reporting-basis-identification.md](08-reporting-basis-identification.md): do
not fake a test against absent data. A test that cannot fail proves nothing and
falsely signals coverage.

## Design Property, Not Just A Gap

This is a defined re-fit path, not an open hole. The interval methodology is
built to incorporate multi-year and historical county-level data on arrival.
When that data lands, it flows into the interval estimates AND the band-shape
tests become writable and meaningful at the same time. Data arrival is the
single trigger for both. The deferral is therefore a property of the staged
data-availability plan, not an oversight.

## Load-Bearing Boundary (critical)

The band-shape properties are NOT load-bearing for the public forecast as long
as no published claim depends on them. The forecast ships a relative reported
Lyme pressure proxy with 2026 intervals derived by the stated empirical
rolling-origin residual method. That is self-contained and honest.

The moment the paper or dashboard asserts any of "uncertainty grows with
forecast horizon," "intervals widen into the future," or "near-term forecasts
are tighter," that sentence becomes load-bearing — and Issue c05124e3 graduates
from a test-gap to a correctness-gap. Until the properties are empirically
validated, public and whitepaper language must state that they are UNVALIDATED
and must not claim that they hold.

## Project Framing

TickBiteRisk is a first-of-kind product; no existing defensible tick-bite risk
forecast exists to inherit validation from. The correct bar is "modestly
defensible and honest about limits," not "complete." A clearly stated deferred
verification is consistent with that bar; an unstated assumption that the bands
behave well would not be.

## Blocked-By

Blocked on generation of the multi-year `public/data/regional/` county-level
artifact (multi-forecast-year interval rows). That generation is out of scope
for this release.

The dependency is encoded in the graph as a three-node chain (the type system
permits `blocked_by` only between two Issues, so the missing artifact is itself
modeled as an Issue):

- Issue c05124e3 (band-shape test gap) `blocked_by` Issue "multi-year
  public/data/regional/ artifact does not exist on disk";
- that blocker Issue `remediated_by` a placeholder ResearchTask that generates
  the artifact.

So the deferral reason and its single unblocking trigger live in the graph, not
only on disk.

## Tracking

Issue c05124e3 (B9 band-shape test gap) remains open. When the multi-year
artifact exists, write the three band-shape tests, and only if they confirm the
properties may any "intervals widen with horizon" claim be made public.
