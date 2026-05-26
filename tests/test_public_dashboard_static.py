from pathlib import Path


PUBLIC_DIR = Path("public")


def test_dashboard_html_has_accessible_landmarks_and_data_hooks() -> None:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")

    assert '<a class="skip-link" href="#county-panel">' in html
    assert "<main" in html
    assert 'id="risk-map"' in html
    assert 'id="county-list"' in html
    assert 'id="county-panel"' in html
    assert 'id="date-input"' in html
    assert "Informational only. Not medical advice." in html
    assert "app.js" in html


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
        "function riskClass",
        "function indexWeeklyRecords",
        "function renderCountyList",
        "function renderMap",
        "function selectCounty",
        "function renderSources",
        "function renderLoadError",
        "fetchJson",
    ]:
        assert token in js


def test_dashboard_javascript_renders_one_accessible_svg_path_map() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "<svg",
        "<path",
        "role=\"button\"",
        "tabindex=\"0\"",
        "aria-pressed",
        "keydown",
        "event.key === \"Enter\"",
        "event.key === \" \"",
    ]:
        assert token in js
