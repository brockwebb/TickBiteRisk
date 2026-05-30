# Regional Spatial Forecast Design

## Decision

TickBiteRisk forecasts reported Lyme risk for every county-equivalent in
Delaware, District of Columbia, Maryland, Pennsylvania, Virginia, and West
Virginia. Counties are observation units and public reporting units, not
ecological boundaries. State is retained for source caveats, rollups, labels,
and display, but state borders do not constrain model features.

The ultimate product abstraction is **risk**: a transparent, open-source,
plain-language score built from real data and expressed on a well-defined
scale. Intermediate artifacts can expose reported incidence, population
denominators, adjacency, clusters, regimes, model comparisons, and caveats so
the score remains auditable. Public language must avoid claiming individual
infection probability or medical advice. Internally, "baseline infection rate"
is treated as shorthand for reported-incidence or relative disease-pressure
baselines because the available surveillance data are reported cases, not true
infection prevalence.

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

Immediate-neighbor averages are only a first diagnostic. The more important
modeling idea is **localized spatial regimes**: contiguous or near-contiguous
sets of counties whose prior reported-incidence histories move together more
strongly than they move with the broader state or region. Western Maryland and
surrounding Appalachian counties in Pennsylvania and West Virginia may form a
more meaningful prior-risk regime than all of Maryland. Coastal and southeast
Virginia localities may form a different low-baseline or differently timed
regime than northern or western Virginia. These regimes should compete with
state-level empirical-Bayes baselines rather than being forced into state
boundaries.

Localized regimes should be learned from adjacency plus forecast-safe prior
history. County pairs should be connected only when they are spatially adjacent
or otherwise explicitly supported by a regional geography rule and have similar
prior incidence level/trend, ecology, or surveillance-context signals. The
first implementation lane can use prior reported-incidence level and trend
similarity because those data are already available; later lanes can add habitat,
weather, host, population, and exposure context.

## Forecast-Safe Rules

Spatial forecast features must be based only on information available at the
forecast origin. Neighbor incidence for forecast year Y is built from origin
year Y-1 or earlier outcomes, never same-year target outcomes and never
validation-row artifacts copied forward.

Spatial-regime assignment for a held-out year Y must also be learned only from
years before Y. If a regime appears to move together in 2021, that fact cannot
be used to forecast 2021 unless it was already visible from 2020 and earlier
history. Diagnostic outputs may include same-year held-out outcomes for
evaluation, but model feature columns and forecast branches must keep those
diagnostics separated from forecast-safe features.

Uncertainty should be preserved around risk estimates. Confidence or prediction
intervals are expected to start wide because official county surveillance lags
and reporting regimes are noisy; they can narrow and update as newer official,
state-source, or near-real-time proxy data become available. Late-arriving data
should update the forecast with provenance and caveats rather than rewriting
history as if the late data had been known at the original forecast origin.

Claims that a year is "bad," "typical," or "unusual" must be tied to a named
comparison set and metric. The first public/research implementation compares
forecast annual reported Lyme incidence with that same county's prior reported
annual incidence through the forecast origin, then reports an empirical
percentile and an interval percentile range. Plain-language labels should use
the percentile contract: below typical under the 25th percentile, typical from
the 25th through 75th percentile, above typical above the 75th and below the
90th percentile, and much higher than typical at or above the 90th percentile.
This is a reported Lyme disease pressure comparison, not a direct claim about
tick abundance, infected tick prevalence, or individual infection probability.
The artifact must retain the raw numeric forecast, the percentile basis,
the uncertainty range, and the surveillance protocol caveat so later data can
recalibrate the estimate rather than erase the original forecast.

Observed state-source overlays, such as Pennsylvania 2024, are valuable
partial-pooling evidence for later updates. They should be used to update
similar localized regimes, source vintages, and surveillance regimes when
backtests support doing so. They are not a blanket regional multiplier. A high
or low residual in one observed state should not automatically scale every
county in DE/DC/MD/PA/VA/WV, especially when the residual may reflect reporting
mechanics as much as ecology.

Known Lyme surveillance case-definition years, currently 1996, 2008, 2011,
2017, and 2022 in CDC/NNDSS case-definition records, must be treated as
change-point or source-regime terms in Bayesian, calibration, random-forest,
analog, and empirical-Bayes lanes. Forecast models should distinguish
ecological movement from surveillance definition changes, state-source overlays,
probable-only rows, laboratory-based surveillance changes, and other reporting
breaks. A Bayesian update that ignores those regime switches can learn the
wrong base rate with impressive-looking arithmetic.

Protocol-era normalization is a valid research lane, but it should be framed as
harmonization for comparability rather than truth correction. The analogy is
constant-dollar inflation adjustment: older surveillance eras can be transformed
onto a present-era dimensionless scale or modeled with era offsets so the model
can compare patterns across time. The output should remain explicitly labeled as
a harmonized index or source-regime-adjusted estimate, because the transform
assumes the underlying bias process is stable enough to estimate and does not
recover unobserved true infections.

The regional public/product default remains separate from research branches.
Cross-border spatial features are research diagnostics until rolling-origin
tests show stable improvement and a separate public branch decision is made.

Promotion criteria should be about the risk product, not about a model sounding
sophisticated. A localized spatial-regime branch is valuable when it improves
or clarifies risk estimates against county-only, state, Mid-Atlantic, analog,
Bayesian/shrinkage, and random-forest lanes while remaining explainable and
forecast-safe.

## Visualization Implications

The primary public interaction remains county-first. A user should be able to
click any DE/DC/MD/PA/VA/WV county-equivalent and receive the specific forecast
risk information for that county, including forecast year/window, score,
source caveats, and uncertainty bands when available.

States are useful visualization, reporting, and aggregation boundaries because
official statistics are released that way, but they should not be the only
baseline layer. Custom localized regimes are model-created regions based on
shared prior history, adjacency, and later ecological or exposure
characteristics. The map should be able to show these regimes as optional
overlays without replacing the county click target.

Forecast UX should make uncertainty visible rather than hiding it. A time
slider can show weekly or seasonal risk changing through the forecast window,
while charts can show county, state, Mid-Atlantic, and localized-regime
trajectories with prediction intervals or margins of error. Exploratory EDA
views may live below the main map or in a separate product surface, but the
central product question remains the same: "What is the forecast risk here?"

Map colors are a display layer over the risk score, not the risk score itself.
Visual top-coding can be used for the darkest color when extreme counties make
the rest of the map unreadable, but it must be explicit: the legend should show
the top-code threshold or percentile, preserve the underlying numeric value in
county detail panels, and describe the choice as a display transform, not a
score transform. Category colors may also map to fixed risk thresholds, but the
threshold contract must be documented and stable enough for users to compare
counties and years.

After the 2026-05-29 data-grain audit, the temporal display contract is locked:
observed historical truth is annual county reported Lyme data, not observed
weekly or monthly county risk. Forecast targets are also annual county disease
pressure. Weekly or monthly views are seasonal allocations of an annual forecast
using national Lyme onset seasonality, and they must be labeled that way. The
default UI should therefore be annual; historical years should keep time
controls locked to annual unless true county-month or county-week observed data
are acquired.

## Source And Provenance

The regional county graph uses the Census TIGERweb `State_County` county layer
queried as GeoJSON for state FIPS `10`, `11`, `24`, `42`, `51`, and `54`.
Raw or normalized geometry is stored under ignored ETL build output, and the
adjacency CSV records source URL hash, method, and quality flags.

## Current Slice

The current regional research lane now materializes the county adjacency graph,
forecast-safe localized spatial regimes, a spatial-regime empirical-Bayes
annual forecast branch, and empirical prediction intervals around regional
annual forecast rows. These outputs do not yet promote a public forecast branch,
and they do not change the Maryland static dashboard score.

A separate regional research GUI can consume the generated regional bundle
without committing the large derived assets or changing the public Maryland
default. The research map should keep county selection first, then layer on
MMWR week changes, county-level empirical intervals, and the selected localized
spatial regime so users can see where custom regimes modify the baseline
without treating state boundaries as ecological model boundaries.
The GUI bundle may simplify regional county geometry for browser rendering, but
it must preserve county identifiers, state display metadata, source caveats, and
the full county-equivalent feature count.

Regional annual forecast intervals are calibrated from rolling-origin regional
incidence stress residuals. They must use only residuals whose held-out test
year is at or before the forecast origin, must match the annual forecast source
incidence hash, and must avoid `actual_*`, residual, error, or coverage fields
in pre-update forecast artifacts. The interval output is an uncertainty band
around reported-incidence proxy risk pressure, not a claim about individual
infection probability.

Spatial-regime interval summaries join county forecast intervals to localized
regime membership using the same forecast-safe feature-year convention as the
annual spatial-regime branch. They are planning and visualization aggregates:
county empirical intervals are summed within each custom region, and the result
is not a full joint posterior. The artifact should fail rather than silently
drop counties with missing regime membership so the eventual map layer stays
complete and auditable. The current live research artifact summarizes 283
county-equivalents into 127 localized spatial regimes for the 2026 forecast
from the 2023 origin year.

The next modeling slices should compare whether localized regime priors and
their uncertainty bands are more useful than state-level shrinkage for reported
incidence and risk estimation, especially in cross-border ecological areas such
as Western Maryland/Pennsylvania/West Virginia versus coastal and southeast
Virginia/Delmarva areas. Aggregate state/Mid-Atlantic interval summaries can be
built from the row-level interval artifact, but public promotion still requires
rolling-origin evidence and a separate branch decision.
