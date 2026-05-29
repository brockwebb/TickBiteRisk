# Annual Truth And Seasonal Forecast Contract

## Decision

TickBiteRisk's observed truth layer is annual county reported Lyme data. The
current public and regional sources do not provide observed county-month or
county-week tick abundance, tick infection prevalence, tick-bite counts, or Lyme
case counts. Monthly and MMWR-week values are derived seasonal allocations of
annual county totals or annual county forecasts.

This contract supersedes any UI or artifact language that implies observed
historical weekly or monthly county risk.

## Data Grain Contract

Historical county data through the latest complete official source year are
annual. For the current regional public-use lane, complete CDC county data are
available through 2023. Historical rows should be displayed as observed annual
reported cases and incidence only.

Forecast rows are also annual at the model target layer. A 2024, 2025, or 2026
forecast is a county-year estimate until a complete official county-year source
is available and reviewed. Partial state-source overlays can inform diagnostics
or candidate updates, but they do not become regional observed truth unless the
coverage and caveats are explicit.

Seasonal views are allocation layers. A monthly or MMWR-week map answers:
"Given this county's annual disease-pressure estimate, how does risk usually
distribute through the year based on CDC national Lyme onset seasonality?" It
does not answer: "How many infected ticks were observed in this county this
month?"

## Product Rules

The default map state should be annual. County click details should first show
annual reported incidence/cases for observed years or annual forecast
incidence/cases for forecast years.

Historical years must not expose a monthly or weekly slider unless a real
county-month or county-week observed source is acquired. If a user selects a
historical year, the time control should be locked to annual.

Forecast years can expose seasonal allocation. The control can use month for a
plain-language product experience; MMWR-week rows may remain an internal or API
artifact if needed for lookup precision. The UI must label this as seasonal
estimate or seasonal allocation, not observed monthly risk.

The public language should use "risk" as the product abstraction, but the model
card and source notes must preserve the underlying target: reported annual Lyme
incidence or disease pressure per county, with uncertainty and caveats. The
score is not an individual infection probability, a diagnosis, or medical
advice.

## Update Rules

When complete official 2024 county annual data arrive, 2024 can move from
forecast to observed after ETL reconciliation and provenance review. Forecast
origins can then roll forward, and 2025/2026 estimates should be regenerated
with the new observed annual layer.

When partial 2024 or later state data arrive, those rows remain overlays or
diagnostics unless they cover the forecast geography completely enough for the
intended product view. Mixed coverage must be labeled as partial and must not
silently change the regional truth layer.

If true county-month or county-week tick, exposure, or disease data are later
acquired, they should enter as a new observed temporal layer with explicit
source permissions, grain, caveats, and validation tests. Until then, seasonal
allocations remain derived planning estimates.

## Guardrails

Static public exports must include a temporal contract declaring:

- observed truth spatial grain: county
- observed truth temporal grain: year
- forecast truth spatial grain: county
- forecast truth temporal grain: year
- display temporal grain: MMWR week for current lookup artifacts
- display time role: seasonal allocation of annual forecast
- seasonality scope: national
- county-month or county-week observed truth available: false

Tests should fail when model cards, source catalogs, manifests, or committed
public data omit this contract. Dashboard tests should also reject copy that
labels derived seasonal allocations as observed historical weekly or monthly
risk.
