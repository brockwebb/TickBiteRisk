from pathlib import Path


PUBLIC_DIR = Path("public")


def test_dashboard_html_has_accessible_landmarks_and_data_hooks() -> None:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")

    assert '<a class="skip-link" href="#county-panel">' in html
    assert '<main class="dashboard">' in html
    assert '<main class="dashboard" aria-live=' not in html
    assert 'id="risk-map"' in html
    assert 'id="county-list"' in html
    assert 'id="county-panel"' in html
    assert 'id="panel-content" aria-live="polite"' in html
    assert 'id="date-input"' in html
    assert 'id="bite-form"' in html
    assert 'id="bite-result"' in html
    assert 'id="validation-summary"' in html
    assert 'id="validation-content"' in html
    assert "<details open>" in html
    assert 'id="week-label" class="muted" aria-live="polite"' in html
    assert "Informational only. Not medical advice." in html
    assert "app.js" in html


def test_dashboard_html_has_single_bite_calculator_controls() -> None:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")

    for token in [
        "Attached tick check",
        'id="bite-tick-species"',
        'id="bite-tick-stage"',
        'id="bite-attachment-hours"',
        'id="bite-engorgement"',
        'id="bite-hours-since-removal"',
        'id="bite-doxycycline-safe"',
        'id="bite-tick-count"',
        "Calculate bite score",
    ]:
        assert token in html


def test_dashboard_css_defines_risk_classes_and_focus_styles() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for class_name in [
        ".risk-very-low",
        ".risk-low",
        ".risk-moderate",
        ".risk-high",
        ".risk-very-high",
        ":focus-visible",
    ]:
        assert class_name in css


def test_dashboard_javascript_has_expected_runtime_functions() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "function mmwrYearWeek",
        "function firstMmwrSunday",
        "function riskClass",
        "function indexWeeklyRecords",
        "function renderCountyList",
        "function renderMap",
        "function selectCounty",
        "function renderModelLineage",
        "function readableModelName",
        "function readableWeatherMode",
        "function renderSources",
        "function sourceChainItems",
        "function readableSourceTitle",
        "function renderValidationSummary",
        "function validationOutcomeItems",
        "function validationLimitItems",
        "function renderLoadError",
        "function safeUrl",
        "function handleBiteSubmit",
        "function estimateSingleBiteRisk",
        "function renderBiteResult",
        "function renderBiteCaveats",
        "function readableBiteCaveat",
        "fetchJson",
    ]:
        assert token in js


def test_dashboard_javascript_renders_visible_plain_language_source_chain() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "Public source chain",
        "CDC Lyme onset seasonality",
        "Selected model-comparison predictions",
        "Derived county-week risk baseline",
        "US Census TIGERweb county geometry",
        "source-chain",
        "source-detail-list",
    ]:
        assert token in js


def test_dashboard_javascript_has_single_bite_scoring_logic() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "single_bite_risk_score",
        "pep_consideration",
        "meets_cdc_consideration_criteria",
        "does_not_meet_cdc_consideration_criteria",
        "partially_meets_cdc_consideration_criteria",
        "maryland_high_incidence_geography_floor",
        "not an absolute infection probability",
        "function locationSeasonModifier",
        "function pepCriteria",
        "function pepConsideration",
        "non ixodes Lyme vector unlikely",
        "not calibrated as an absolute infection probability",
        "Bite-specific caveats",
    ]:
        assert token in js


def test_dashboard_javascript_renders_validation_and_limits_summary() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "Validation and limits",
        "rolling-origin prior-years validation",
        "selected model branch",
        "mae_incidence_per_100k",
        "rank_by_mae",
        "n_predictions",
        "prevention timing",
        "not weather-adjusted",
        "not a diagnosis",
        "not an absolute infection probability",
        "renderValidationSummary()",
        "function publishedMetricValue",
        "value === null",
    ]:
        assert token in js


def test_dashboard_explains_forecasting_and_update_policy() -> None:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "Why this is a forecast",
        "Official Lyme surveillance data lag",
        "How new data updates the model",
        "future reviewed estimates",
    ]:
        assert token in html

    for token in [
        "function renderForecastExplainer",
        "forecasting_status",
        "update_policy",
        "data_lag_and_update_policy",
        "Forecast-safe branches",
        "future reviewed estimates",
        "not diagnosis, treatment advice, or certainty about an individual bite",
    ]:
        assert token in js


def test_dashboard_javascript_mmwr_logic_handles_year_boundaries() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "const yearStart = firstMmwrSunday(calendarYear)",
        "const nextYearStart = firstMmwrSunday(calendarYear + 1)",
        "if (date < yearStart)",
        "mmwrYear = calendarYear - 1",
        "date >= nextYearStart",
        "mmwrYear = calendarYear + 1",
    ]:
        assert token in js


def test_dashboard_javascript_renders_one_accessible_svg_path_map() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "<svg",
        "<path",
        "role=\"group\"",
        "role=\"button\"",
        "tabindex=\"0\"",
        "aria-pressed",
        "keydown",
        "event.key === \"Enter\"",
        "event.key === \" \"",
    ]:
        assert token in js


def test_dashboard_javascript_translates_quality_flags_to_readable_caveats() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "const flagLabels",
        "relative_seasonal_baseline",
        "Relative seasonal baseline",
        "static_seasonality_prior",
        "static CDC onset seasonality",
        "not county-specific",
        "not_weather_adjusted",
        "not a weather-adjusted forecast",
        "intervention_caveat",
        "Prevention and intervention effects are not modeled",
        "surveillance_change_caveat",
        "Surveillance and reporting changes can affect comparisons",
        "surveillance_reporting_sensitive",
        "lyme_case_definition_change",
        "Lyme case definitions changed over time",
        "national_curve_not_county_specific",
        "CDC national onset seasonality is not county-specific",
        "empirical_prediction_band",
        "not clinical confidence for an individual bite",
        "observational_not_causal",
        "This observational baseline does not prove causes",
    ]:
        assert token in js


def test_dashboard_javascript_renders_deduplicated_flag_caveats_in_county_panel() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "function readableFlagLabel",
        "function renderFlagCaveats",
        "feature_quality_flags",
        "backtest_assumption_flags",
        "new Set",
        "replaceAll(\"_\", \" \")",
        "What to know about this score",
        "<ul class=\"flag-list\">",
        "${renderFlagCaveats(record)}",
        "not a per-bite infection probability, diagnosis, or medical advice",
    ]:
        assert token in js


def test_dashboard_javascript_renders_model_lineage_in_county_panel() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "function renderModelLineage",
        "annual_prediction_source",
        "Model source",
        "model-comparison run",
        "model_family",
        "evaluation_mode",
        "weather_mode",
        "not weather-adjusted",
        "<dl class=\"lineage-grid\">",
        "${renderModelLineage(record)}",
    ]:
        assert token in js


def test_dashboard_javascript_escapes_panel_values_and_sanitizes_links() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "escapeHtml(record.mmwr_week)",
        "escapeHtml(record.data_year)",
        "escapeHtml(record.risk_score)",
        "escapeHtml(score)",
        "escapeAttribute(safeUrl(link.url))",
        "function safeUrl",
        "http:",
        "https:",
        "startsWith(\"/\")",
        "startsWith(\"./\")",
        "about:blank",
    ]:
        assert token in js


def test_dashboard_css_styles_flag_caveats_without_visual_noise() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".flag-caveats",
        ".flag-caveats h4",
        ".flag-list",
        ".flag-list li",
    ]:
        assert token in css


def test_dashboard_css_styles_model_lineage_strip_compactly() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".lineage-strip",
        ".lineage-strip h4",
        ".lineage-grid",
        ".lineage-grid dt",
        ".lineage-grid dd",
    ]:
        assert token in css


def test_dashboard_css_styles_single_bite_calculator() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".bite-calculator",
        ".bite-form-grid",
        ".bite-result",
        ".bite-caveats",
        ".criteria-list",
        ".criteria-status",
    ]:
        assert token in css


def test_dashboard_css_styles_validation_summary() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".validation-summary",
        ".validation-grid",
        ".validation-list",
        ".validation-note",
    ]:
        assert token in css


def test_dashboard_css_styles_forecast_explainer_panel() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".forecast-explainer",
        ".forecast-explainer h3",
        ".controls,\n  .forecast-explainer,",
    ]:
        assert token in css


def test_dashboard_css_styles_visible_source_chain() -> None:
    css = (PUBLIC_DIR / "styles.css").read_text(encoding="utf-8")

    for token in [
        ".source-chain",
        ".source-chain h3",
        ".source-chain ol",
        ".source-detail-list",
    ]:
        assert token in css
