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
