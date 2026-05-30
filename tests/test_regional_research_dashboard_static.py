import re
from pathlib import Path


PUBLIC_DIR = Path("public")


def test_regional_research_html_has_map_controls_and_research_boundaries() -> None:
    html = (PUBLIC_DIR / "regional-research.html").read_text(encoding="utf-8")

    for token in [
        "<title>TickBiteRisk Regional Research: Lyme Disease Forecasting and Risk Assessment</title>",
        "TickBiteRisk Regional Research: Lyme Disease Forecasting and Risk Assessment",
        "Mid-Atlantic annual Lyme risk forecast research",
        "Click a county to see its Lyme forecast, the predicted annual rate,",
        'id="regional-top"',
        'class="regional-jump-links"',
        'href="#regional-source-title"',
        'href="#regional-county-panel"',
        'href="#regional-top"',
        "Research notes",
        "Back to top",
        "Tick bite risk calculator",
        "Found a tick? Estimate your risk of disease",
        'id="regional-risk-map"',
        'id="regional-regime-layer-toggle"',
        'class="controls regional-controls regional-time-toolbar"',
        'id="year-select"',
        'id="year-label" class="muted" aria-live="polite"',
        'id="year-mode-label" class="mode-pill forecast-mode"',
        'class="forecast-view-radios"',
        'name="forecast-view"',
        'id="forecast-view-annual"',
        'id="forecast-view-weekly"',
        'id="forecast-view-label" class="muted" aria-live="polite"',
        'id="week-slider"',
        'class="week-scale"',
        'id="week-input"',
        'id="week-label" class="muted" aria-live="polite"',
        'id="regional-county-panel"',
        'id="regional-panel-content" aria-live="polite"',
        'id="regional-regime-panel"',
        'id="regional-forecast-chart"',
        'id="regional-chart-summary" aria-live="polite"',
        'class="forecast-scope-radios"',
        'name="forecast-scope"',
        'id="forecast-scope-region"',
        'id="forecast-scope-state"',
        'id="forecast-scope-regime"',
        'id="forecast-scope-county"',
        'id="forecast-state-select"',
        'id="forecast-county-select"',
        'id="state-filter"',
        'id="county-search"',
        'id="regional-county-picker"',
        'id="regional-list-status" aria-live="polite"',
        'id="regional-forecast-explainer"',
        'id="regional-bite-form"',
        'id="regional-bite-tick-species"',
        'id="regional-bite-tick-stage"',
        'id="regional-bite-attachment-hours"',
        'id="regional-bite-engorgement"',
        'id="regional-bite-hours-since-removal"',
        'id="regional-bite-doxycycline-safe"',
        'id="regional-bite-tick-count"',
        'id="regional-bite-result" class="bite-result" aria-live="polite"',
        'id="regional-forecast-provenance"',
        'id="regional-source-content"',
        "Forecast window",
        "Show local forecast region",
        "Estimate bite risk",
        "Informational only. Not medical advice.",
        "regional-research.js",
    ]:
        assert token in html

    assert 'id="regional-county-list"' not in html
    assert "Selected county weekly forecast with empirical intervals" not in html
    assert (
        'id="regional-forecast-chart"\n          class="forecast-chart"\n          role="img"'
        not in html
    )
    assert "Research-only regional outputs" not in html
    assert "public Maryland default" not in html


def test_regional_research_html_cache_busts_css_and_script_assets() -> None:
    html = (PUBLIC_DIR / "regional-research.html").read_text(encoding="utf-8")

    stylesheet = re.search(r'href="styles\.css\?v=([^"]+)"', html)
    script = re.search(r'src="regional-research\.js\?v=([^"]+)"', html)

    assert stylesheet is not None
    assert script is not None
    assert stylesheet.group(1) == script.group(1)
    assert "forecast-view-select" not in stylesheet.group(1)


def test_regional_research_javascript_uses_regional_bundle_without_maryland_default() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")

    for token in [
        "research-data/regional/regional_county_risk_weekly.json",
        "research-data/regional/regional_county_incidence_annual.json",
        "research-data/regional/regional_counties.geojson",
        "research-data/regional/regional_states.geojson",
        "research-data/regional/regional_county_metadata.json",
        "research-data/regional/regional_forecast_typicality.json",
        "research-data/regional/regional_spatial_regime_overlays.json",
        "function renderRegionalMap",
        "function regionalStateBoundaryPath",
        "function selectRegionalCounty",
        "function renderRegionalRegime",
        "function regionalRegimeCountyNames",
        "function renderRegionalForecastChart",
        "function renderRegionalObservedHistoryChart",
        "function renderRegionalScaleDiagnostics",
        "function renderRegionalForecastBasis",
        "function renderRegionalComparableYear",
        "function renderRegionalForecastTypicality",
        "function regionalForecastTypicalityForYear",
        "function regionalSelectedRegimeForYear",
        "function regionalSelectedRegimeOverlay",
        "function renderRegionalForecastCheck",
        "function getRegionalForecastObservedFit",
        "function renderRegionalProtocolNote",
        "function renderRegionalHistoricalRegimeNotice",
        "function regionalShowForecastRegimeContext",
        "function regionalSurveillanceProtocolForYear",
        "function regionalForecastBasisList",
        "function regionalWeekDateRange",
        "function formatRegionalDateRange",
        "function handleYearSelectChange",
        "function handleForecastViewChange",
        "function handleForecastScopeChange",
        "function handleForecastStateChange",
        "function handleForecastCountyChange",
        "function handleRegionalRegimeLayerToggle",
        "function selectedRegionalDataMode",
        "function selectedRegionalForecastView",
        "function syncRegionalForecastViewRadios",
        "function syncRegionalForecastScopeControls",
        "function renderRegionalForecastVisualization",
        "function renderRegionalForecastExplainer",
        "function regionalForecastScopeCountyFips",
        "function regionalRegimeScopeAvailable",
        "function regionalRegimeScopeOverlay",
        "function regionalAggregateAnnualForecastSummary",
        "function indexRegionalForecastTypicality",
        "function renderRegionalAnnualChartContext",
        "function regionalAnnualForecastComparison",
        "function regionalObservedComparisonStats",
        "function regionalAnnualPredictionInterval",
        "function regionalAggregateWeeklyForecastRecords",
        "function regionalAggregateObservedAnnualRecords",
        "function renderRegionalAnnualForecastCounty",
        "function regionalAnnualForecastSummary",
        "function regionalCountyWeekRecords",
        "function handleRegionalListFilterChange",
        "function handleRegionalCountyPickerChange",
        "function handleRegionalBiteSubmit",
        "function renderRegionalBiteResult",
        "function readRegionalBiteInputs",
        "function estimateRegionalSingleBiteRisk",
        "function regionalLocationSeasonModifier",
        "function regionalPepCriteria",
        "function regionalBiteRiskBand",
        "function filteredRegionalFeatures",
        "function renderRegionalForecastProvenance",
        "function handleWeekSliderInput",
        "function handleWeekInputChange",
        "function syncRegionalWeekControls",
        "function renderRegionalObservedAnnualContext",
        "function regionalRiskFillColor",
        "forecast_safe_prior_history_spatial_regime",
        "Forecast year",
        "Observed historical",
        "Forecast with observed comparison",
        "Annual forecast",
        "Weekly seasonal risk",
        "All states",
        "State",
        "County",
        "Regional annual forecast",
        "local region annual forecast",
        "in this chart",
        "Predicted annual incidence",
        "Predicted annual cases",
        "Observed annual context",
        "Surveillance protocol",
        "Protocol era",
        "1996 surveillance definition era",
        "2008 surveillance definition era",
        "2022 surveillance definition era",
        "Forecast regions are shown only for forecast years",
        "observed reported incidence",
        "Linear score",
        "Why this forecast?",
        "County level data are released as annual totals only",
        "most recent CDC county data available in this release",
        "The green line is the predicted weekly Lyme incidence",
        "Dark blue band",
        "Light blue band",
        "past forecast errors",
        "not medical confidence intervals",
        "The red dot marks the selected week",
        "The brown line is observed annual reported incidence",
        "The blue dot marks the selected annual forecast",
        "Annual target",
        "empirical forecast-error ranges",
        "Map colors are display categories",
        "not automatic public score corrections",
        "Bite concern score",
        "CDC consideration context",
        "Bite-specific caveats",
        "Nearest comparable history",
        "How unusual is this forecast?",
        "Compared with this county",
        "Forecast interval range",
        "not tick abundance",
        "PA 2024 forecast check",
        "forecast_observed_fit",
        "Artifact-backed partial state-source overlay",
        "post-forecast goodness-of-fit",
        "MMWR week",
        "Seasonal allocation",
        "Bayesian updates",
        "rounded and clamped",
        "score_denominator",
        "function renderRegionalForecastSeveritySummary",
        "function regionalPeakWeeklyScoreRecord",
        "function regionalForecastScoreFootnote",
        "How bad is it?",
        "Predicted score",
        "selected week score",
        "peak seasonal score",
        "Forecast percentile",
        "80% prediction range",
        "95% wider range",
        "Prior average",
        "Worst observed",
        "worse than average",
        "chart-y-axis-title",
        "chart-y-tick",
        "chart-x-axis-title",
        "chart-x-tick",
        "Predicted score footnote",
        "Annual view shows the peak weekly score",
        "not a personal infection probability",
        "observed-history-line",
        "county-forecast-line",
        "interval-band-95",
        "data-active-week",
        "95% empirical interval",
        "Local forecast region",
        "Region 95% interval",
        "Region counties",
        "regional-state-boundary",
    ]:
        assert token in js

    assert "data/md_county_risk_weekly.json" not in js
    assert "md_counties.geojson" not in js
    assert "forecast-view-select" not in js
    assert "regional-county-list" not in js
    assert "Maryland high-incidence context" not in js
    assert "Not used:" not in js
    assert "public Maryland default" not in js
    assert "Research only:" not in js


def test_regional_research_javascript_keeps_historical_years_annual_only() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")

    for token in [
        "Weekly seasonal risk is only available for the current forecast year",
        "Choose Weekly seasonal risk to use MMWR week controls",
        "selectedRegionalForecastView() === \"weekly\"",
        "Observed annual context",
        "observed annual incidence history",
    ]:
        assert token in js

    for token in [
        "historical weekly risk",
        "observed_historical_weekly",
    ]:
        assert token not in js


def test_regional_research_javascript_does_not_mix_forecast_regimes_into_observed_years() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")
    observed_body = js.split("function renderRegionalObservedCounty", maxsplit=1)[
        1
    ].split("function renderRegionalForecastCheck", maxsplit=1)[0]
    selected_regime_body = js.split("function selectedRegionalRegimeId", maxsplit=1)[
        1
    ].split("function updateRegionalSelectedControls", maxsplit=1)[0]

    assert "renderRegionalHistoricalRegimeNotice()" in observed_body
    assert "renderRegionalCountyRegime(metadata)" not in observed_body
    assert "renderRegionalProtocolNote(annualRecord.year)" in observed_body
    assert "regionalShowForecastRegimeContext()" in selected_regime_body


def test_regional_forecast_observed_fit_requires_matching_selected_year() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")
    function_body = js.split("function getRegionalForecastObservedFit", maxsplit=1)[
        1
    ].split("function renderRegionalObservedAnnualContext", maxsplit=1)[0]

    assert "Number(record.forecast_year) === selectedYear" in function_body
    assert "records[0]" not in function_body


def test_regional_forecast_typicality_requires_matching_selected_year() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")
    function_body = js.split("function regionalForecastTypicalityForYear", maxsplit=1)[
        1
    ].split("function renderRegionalForecastCheck", maxsplit=1)[0]

    assert "Number(record.forecast_year) === selectedYear" in function_body
    assert "records[0]" not in function_body


def test_regional_spatial_regime_context_requires_matching_selected_year() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")
    selected_regime_body = js.split("function regionalSelectedRegimeForYear", maxsplit=1)[
        1
    ].split("function regionalSelectedRegimeOverlay", maxsplit=1)[0]
    selected_overlay_body = js.split("function regionalSelectedRegimeOverlay", maxsplit=1)[
        1
    ].split("function renderRegionalHistoricalRegimeNotice", maxsplit=1)[0]

    assert "Number(regime.forecast_year) === selectedYear" in selected_regime_body
    assert "Number(overlay.forecast_year) === selectedYear" in selected_overlay_body
    assert "overlaysByRegime.get(regime.region_id)" not in selected_overlay_body


def test_regional_research_css_has_stable_map_slider_and_regime_styles() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".regional-dashboard",
        ".regional-controls",
        ".regional-time-toolbar",
        ".regional-time-grid",
        ".week-control",
        ".week-scale",
        ".regional-map-shell",
        ".regional-regime-strip",
        ".regional-county-shape.is-same-regime",
        ".regional-state-boundary",
        ".week-slider-row",
        ".mode-pill",
        ".observed-history-line",
    ]:
        assert token in css


def test_regional_research_javascript_computes_bounds_without_large_array_spread() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")

    for token in [
        "function expandRegionalBounds",
        "Number.POSITIVE_INFINITY",
        "Number.NEGATIVE_INFINITY",
        "for (const point of regionalCoordinates(feature.geometry))",
    ]:
        assert token in js

    assert "Math.min(...xs)" not in js
    assert "Math.max(...xs)" not in js
