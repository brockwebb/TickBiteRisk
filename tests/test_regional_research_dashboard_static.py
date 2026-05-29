from pathlib import Path


PUBLIC_DIR = Path("public")


def test_regional_research_html_has_map_controls_and_research_boundaries() -> None:
    html = (PUBLIC_DIR / "regional-research.html").read_text(encoding="utf-8")

    for token in [
        "<title>TickBiteRisk Regional Research Forecast</title>",
        "TickBiteRisk Regional Research",
        "Mid-Atlantic county-week Lyme risk forecast research",
        'id="regional-risk-map"',
        'id="week-slider"',
        'id="week-label" class="muted" aria-live="polite"',
        'id="regional-county-panel"',
        'id="regional-panel-content" aria-live="polite"',
        'id="regional-regime-panel"',
        'id="regional-forecast-chart"',
        'id="regional-chart-summary" aria-live="polite"',
        'id="state-filter"',
        'id="county-search"',
        'id="regional-list-status" aria-live="polite"',
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
        "research-data/regional/regional_counties.geojson",
        "research-data/regional/regional_county_metadata.json",
        "research-data/regional/regional_spatial_regime_overlays.json",
        "function renderRegionalMap",
        "function selectRegionalCounty",
        "function renderRegionalRegime",
        "function regionalRegimeCountyNames",
        "function renderRegionalForecastChart",
        "function regionalCountyWeekRecords",
        "function handleRegionalListFilterChange",
        "function filteredRegionalFeatures",
        "function handleWeekSliderInput",
        "forecast_safe_prior_history_spatial_regime",
        "county-forecast-line",
        "interval-band-95",
        "data-active-week",
        "Research only",
        "not public Maryland default",
        "95% empirical interval",
        "Regime 95% interval",
        "Regime counties",
    ]:
        assert token in js

    assert "data/md_county_risk_weekly.json" not in js
    assert "md_counties.geojson" not in js


def test_regional_research_css_has_stable_map_slider_and_regime_styles() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".regional-dashboard",
        ".regional-controls",
        ".regional-map-shell",
        ".regional-regime-strip",
        ".regional-county-shape.is-same-regime",
        ".week-slider-row",
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
