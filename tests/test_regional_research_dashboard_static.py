from pathlib import Path


PUBLIC_DIR = Path("public")


def test_regional_research_html_has_map_controls_and_research_boundaries() -> None:
    html = (PUBLIC_DIR / "regional-research.html").read_text(encoding="utf-8")

    for token in [
        "<title>TickBiteRisk Regional Research Forecast</title>",
        "TickBiteRisk Regional Research",
        "Mid-Atlantic annual Lyme risk forecast research",
        "Click a county to see its Lyme forecast, the predicted annual rate,",
        'id="regional-risk-map"',
        'class="controls regional-controls regional-time-toolbar"',
        'id="year-select"',
        'id="year-label" class="muted" aria-live="polite"',
        'id="year-mode-label" class="mode-pill forecast-mode"',
        'id="forecast-view-select"',
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
        'id="state-filter"',
        'id="county-search"',
        'id="regional-list-status" aria-live="polite"',
        'id="regional-forecast-provenance"',
        'id="regional-source-content"',
        "Forecast window",
        "Informational only. Not medical advice.",
        "regional-research.js",
    ]:
        assert token in html


def test_regional_research_javascript_uses_regional_bundle_without_maryland_default() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")

    for token in [
        "research-data/regional/regional_county_risk_weekly.json",
        "research-data/regional/regional_county_incidence_annual.json",
        "research-data/regional/regional_counties.geojson",
        "research-data/regional/regional_states.geojson",
        "research-data/regional/regional_county_metadata.json",
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
        "function renderRegionalForecastCheck",
        "function getRegionalForecastObservedFit",
        "function regionalForecastBasisList",
        "function regionalWeekDateRange",
        "function formatRegionalDateRange",
        "function handleYearSelectChange",
        "function handleForecastViewChange",
        "function selectedRegionalDataMode",
        "function selectedRegionalForecastView",
        "function renderRegionalAnnualForecastCounty",
        "function regionalAnnualForecastSummary",
        "function regionalCountyWeekRecords",
        "function handleRegionalListFilterChange",
        "function filteredRegionalFeatures",
        "function renderRegionalForecastProvenance",
        "function handleWeekSliderInput",
        "function handleWeekInputChange",
        "function syncRegionalWeekControls",
        "function renderRegionalObservedAnnualContext",
        "function regionalRiskFillColor",
        "forecast_safe_prior_history_spatial_regime",
        "Forecast origin",
        "Forecast year",
        "Observed historical",
        "Forecast with observed comparison",
        "Annual forecast",
        "Weekly seasonal risk",
        "Predicted annual incidence",
        "Predicted annual cases",
        "Observed annual context",
        "observed reported incidence",
        "Linear score",
        "Why this forecast?",
        "Forecast basis",
        "Nearest comparable history",
        "PA 2024 forecast check",
        "forecast_observed_fit",
        "Artifact-backed partial state-source overlay",
        "post-forecast goodness-of-fit",
        "MMWR week",
        "Seasonal allocation",
        "Bayesian updates",
        "rounded and clamped",
        "score_denominator",
        "observed-history-line",
        "county-forecast-line",
        "interval-band-95",
        "data-active-week",
        "Research only",
        "not public Maryland default",
        "95% empirical interval",
        "Regime 95% interval",
        "Regime counties",
        "regional-state-boundary",
    ]:
        assert token in js

    assert "data/md_county_risk_weekly.json" not in js
    assert "md_counties.geojson" not in js


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


def test_regional_forecast_observed_fit_requires_matching_selected_year() -> None:
    js = (PUBLIC_DIR / "regional-research.js").read_text(encoding="utf-8")
    function_body = js.split("function getRegionalForecastObservedFit", maxsplit=1)[
        1
    ].split("function renderRegionalObservedAnnualContext", maxsplit=1)[0]

    assert "Number(record.forecast_year) === selectedYear" in function_body
    assert "records[0]" not in function_body


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
