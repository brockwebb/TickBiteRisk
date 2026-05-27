# Static Dashboard Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first static GitHub Pages-ready dashboard for Maryland county-week Lyme seasonal baseline risk.

**Architecture:** Add a small dashboard asset builder that writes public risk JSON and a public-safe Maryland county GeoJSON under `public/data/`. Build a plain HTML/CSS/JavaScript dashboard under `public/` that fetches those static assets, renders an accessible county map/list/detail panel, and preserves the non-medical relative-baseline framing.

**Tech Stack:** Python 3.12 stdlib + existing Typer CLI for asset generation; static HTML/CSS/JavaScript for the dashboard; Census TIGERweb GeoJSON for Maryland county geometry; existing `tickbiterisk risk export-static` output for public risk data.

---

## File Structure

Create:

- `tickbiterisk/dashboard_assets.py` - fetch and normalize Maryland county GeoJSON, then write dashboard data assets.
- `tests/test_dashboard_assets.py` - unit tests for GeoJSON normalization and asset writer behavior.
- `tests/test_cli_dashboard_assets.py` - CLI coverage for dashboard asset generation.
- `tests/test_public_dashboard_static.py` - static checks for the HTML/CSS/JS shell.
- `public/index.html` - static dashboard markup.
- `public/styles.css` - accessible responsive visual design.
- `public/app.js` - dashboard data loading, MMWR conversion, map/list/panel interactions.
- `public/data/md_county_risk_weekly.json` - generated public risk export.
- `public/data/md_county_metadata.json` - generated public county metadata.
- `public/data/model_card.json` - generated model card.
- `public/data/source_catalog.json` - generated source catalog.
- `public/data/static_export_manifest.json` - generated static export manifest.
- `public/data/md_counties.geojson` - generated Maryland county geometry from Census TIGERweb.

Modify:

- `tickbiterisk/cli.py` - add `dashboard` Typer app and `dashboard build-assets` command.
- `README.md` - add static dashboard local run and asset build command.
- `docs/public-product-boundary.md` - note `public/` dashboard root and `md_counties.geojson`.
- `docs/data-manifest.md` - add Census TIGERweb county geometry asset row.
- `docs/software-requirements-spec.md` - add static dashboard UI requirement.

Do not touch unrelated untracked local files.

## Task 1: Dashboard Asset Builder

**Files:**
- Create: `tickbiterisk/dashboard_assets.py`
- Test: `tests/test_dashboard_assets.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/test_dashboard_assets.py`:

```python
import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.dashboard_assets import (
    TIGERWEB_COUNTIES_URL,
    normalize_maryland_county_geojson,
    write_dashboard_assets,
)


def test_normalize_maryland_county_geojson_keeps_public_county_fields() -> None:
    source = _fixture_geojson()

    normalized = normalize_maryland_county_geojson(source)
    anne_arundel = next(
        feature
        for feature in normalized["features"]
        if feature["properties"]["county_fips"] == "24003"
    )

    assert normalized["type"] == "FeatureCollection"
    assert normalized["metadata"]["source_url"] == TIGERWEB_COUNTIES_URL
    assert normalized["metadata"]["state_fips"] == "24"
    assert normalized["metadata"]["feature_count"] == 24
    assert anne_arundel["properties"] == {
        "county_fips": "24003",
        "county_name": "Anne Arundel County",
    }
    assert anne_arundel["geometry"]["type"] == "Polygon"


def test_write_dashboard_assets_writes_risk_json_and_geojson(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "public" / "data"
    fake_geojson = _fixture_geojson()

    result = write_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        fetch_geojson=lambda: fake_geojson,
    )

    assert result.output_dir == output_dir
    assert result.weekly_risk_path.name == "md_county_risk_weekly.json"
    assert result.county_geojson_path.name == "md_counties.geojson"

    weekly = json.loads(result.weekly_risk_path.read_text(encoding="utf-8"))
    counties = json.loads(result.county_geojson_path.read_text(encoding="utf-8"))

    assert weekly["record_count"] == 2
    assert counties["metadata"]["feature_count"] == 24
    assert any(
        feature["properties"]["county_fips"] == "24003"
        for feature in counties["features"]
    )


def _fixture_geojson() -> dict:
    county_rows = [
        ("24001", "Allegany County"),
        ("24003", "Anne Arundel County"),
        ("24005", "Baltimore County"),
        ("24009", "Calvert County"),
        ("24011", "Caroline County"),
        ("24013", "Carroll County"),
        ("24015", "Cecil County"),
        ("24017", "Charles County"),
        ("24019", "Dorchester County"),
        ("24021", "Frederick County"),
        ("24023", "Garrett County"),
        ("24025", "Harford County"),
        ("24027", "Howard County"),
        ("24029", "Kent County"),
        ("24031", "Montgomery County"),
        ("24033", "Prince George's County"),
        ("24035", "Queen Anne's County"),
        ("24037", "St. Mary's County"),
        ("24039", "Somerset County"),
        ("24041", "Talbot County"),
        ("24043", "Washington County"),
        ("24045", "Wicomico County"),
        ("24047", "Worcester County"),
        ("24510", "Baltimore city"),
    ]
    return {
        "type": "FeatureCollection",
        "features": [
            _county_feature(county_fips, county_name, index)
            for index, (county_fips, county_name) in enumerate(county_rows)
        ],
    }


def _county_feature(county_fips: str, county_name: str, index: int) -> dict:
    lon = -79.5 + (index % 6) * 0.35
    lat = 37.9 + (index // 6) * 0.35
    return {
        "type": "Feature",
        "properties": {
            "GEOID": county_fips,
            "NAME": county_name,
            "STATE": "24",
            "COUNTY": county_fips[-3:],
            "EXTRA": "drop me",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon, lat],
                    [lon + 0.2, lat],
                    [lon + 0.2, lat + 0.2],
                    [lon, lat + 0.2],
                    [lon, lat],
                ]
            ],
        },
    }
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
./.venv/bin/pytest tests/test_dashboard_assets.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'tickbiterisk.dashboard_assets'`.

- [ ] **Step 3: Implement asset builder**

Create `tickbiterisk/dashboard_assets.py`:

```python
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tickbiterisk.runtime.static_export import (
    StaticRiskExportPaths,
    export_static_risk_data,
)


TIGERWEB_COUNTIES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/tigerWMS_Current/MapServer/82/query"
)


@dataclass(frozen=True)
class DashboardAssetPaths:
    output_dir: Path
    weekly_risk_path: Path
    county_metadata_path: Path
    model_card_path: Path
    source_catalog_path: Path
    export_manifest_path: Path
    county_geojson_path: Path


def write_dashboard_assets(
    *,
    scores_path: Path,
    output_dir: Path,
    model_name: str = "linear_blend_baseline",
    seasonality_source_id: str = "cdc_seasonality_week_2023",
    fetch_geojson: Callable[[], dict[str, Any]] | None = None,
) -> DashboardAssetPaths:
    static_paths = export_static_risk_data(
        scores_path=scores_path,
        output_dir=output_dir,
        model_name=model_name,
        seasonality_source_id=seasonality_source_id,
    )
    raw_geojson = fetch_geojson() if fetch_geojson else fetch_maryland_county_geojson()
    normalized_geojson = normalize_maryland_county_geojson(raw_geojson)
    county_geojson_path = output_dir / "md_counties.geojson"
    county_geojson_path.write_text(
        json.dumps(normalized_geojson, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _paths_from_static(output_dir, static_paths, county_geojson_path)


def fetch_maryland_county_geojson() -> dict[str, Any]:
    params = urlencode(
        {
            "where": "STATE='24'",
            "outFields": "GEOID,NAME,STATE,COUNTY",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        }
    )
    request = Request(
        f"{TIGERWEB_COUNTIES_URL}?{params}",
        headers={"User-Agent": "TickBiteRisk/0.1"},
    )
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Census TIGERweb response was not a GeoJSON FeatureCollection")
    return payload


def normalize_maryland_county_geojson(
    payload: dict[str, Any],
) -> dict[str, Any]:
    features = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        state_fips = str(properties.get("STATE", ""))
        county_fips = str(properties.get("GEOID", ""))
        county_name = str(properties.get("NAME", ""))
        geometry = feature.get("geometry")
        if state_fips != "24" or len(county_fips) != 5 or not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "county_fips": county_fips,
                    "county_name": county_name,
                },
                "geometry": geometry,
            }
        )
    features.sort(key=lambda item: item["properties"]["county_fips"])
    if len(features) != 24:
        raise ValueError(
            f"Expected 24 Maryland county features, found {len(features)}"
        )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "source": "US Census TIGERweb Counties",
            "source_url": TIGERWEB_COUNTIES_URL,
            "state_fips": "24",
            "feature_count": len(features),
        },
        "features": features,
    }


def _paths_from_static(
    output_dir: Path,
    static_paths: StaticRiskExportPaths,
    county_geojson_path: Path,
) -> DashboardAssetPaths:
    return DashboardAssetPaths(
        output_dir=output_dir,
        weekly_risk_path=static_paths.weekly_risk_path,
        county_metadata_path=static_paths.county_metadata_path,
        model_card_path=static_paths.model_card_path,
        source_catalog_path=static_paths.source_catalog_path,
        export_manifest_path=static_paths.export_manifest_path,
        county_geojson_path=county_geojson_path,
    )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
./.venv/bin/pytest tests/test_dashboard_assets.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add tickbiterisk/dashboard_assets.py tests/test_dashboard_assets.py
git commit -m "feat: add dashboard asset builder"
```

## Task 2: Dashboard CLI Command

**Files:**
- Modify: `tickbiterisk/cli.py`
- Test: `tests/test_cli_dashboard_assets.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli_dashboard_assets.py`:

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from tests.test_runtime_risk_lookup import _write_scores
from tickbiterisk.cli import app


runner = CliRunner()


def test_dashboard_build_assets_writes_public_data_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    output_dir = tmp_path / "public" / "data"

    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-assets",
            "--scores-path",
            str(scores_path),
            "--output-dir",
            str(output_dir),
            "--use-fixture-geometry",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote dashboard assets" in result.stdout
    assert (output_dir / "md_county_risk_weekly.json").exists()
    assert (output_dir / "md_counties.geojson").exists()
    geojson = json.loads(
        (output_dir / "md_counties.geojson").read_text(encoding="utf-8")
    )
    assert geojson["metadata"]["feature_count"] == 24


def test_dashboard_build_assets_fails_cleanly_when_scores_missing(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "dashboard",
            "build-assets",
            "--scores-path",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "public" / "data"),
        ],
    )

    assert result.exit_code != 0
    assert "Risk score file not found" in result.output
    assert "Traceback" not in result.output
```

The `--use-fixture-geometry` flag is test-only/dev-friendly and avoids live network calls in tests.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
./.venv/bin/pytest tests/test_cli_dashboard_assets.py -q
```

Expected: fail because the `dashboard` command does not exist.

- [ ] **Step 3: Add CLI command**

Modify `tickbiterisk/cli.py`:

```python
from tickbiterisk.dashboard_assets import write_dashboard_assets
```

Near the existing Typer app declarations:

```python
dashboard_app = typer.Typer(help="Static dashboard asset commands")
app.add_typer(dashboard_app, name="dashboard")
```

Add this helper and command:

```python
def _fixture_maryland_geojson() -> dict[str, object]:
    features = []
    for index in range(24):
        county_fips = f"24{index + 1:03d}"
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "GEOID": county_fips,
                    "NAME": f"Fixture County {index + 1}",
                    "STATE": "24",
                    "COUNTY": f"{index + 1:03d}",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-77.0 + index * 0.01, 39.0],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@dashboard_app.command("build-assets")
def dashboard_build_assets(
    scores_path: Path = typer.Option(
        Path("build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv"),
        help="County-week seasonal risk baseline CSV.",
    ),
    output_dir: Path = typer.Option(
        Path("public/data"),
        help="Output directory for dashboard static data assets.",
    ),
    use_fixture_geometry: bool = typer.Option(
        False,
        help="Use generated fixture geometry instead of Census TIGERweb.",
    ),
) -> None:
    if not scores_path.exists():
        raise typer.BadParameter(f"Risk score file not found: {scores_path}")
    fetcher = _fixture_maryland_geojson if use_fixture_geometry else None
    outputs = write_dashboard_assets(
        scores_path=scores_path,
        output_dir=output_dir,
        fetch_geojson=fetcher,
    )
    typer.echo(f"Wrote dashboard assets to {output_dir}")
    typer.echo(f"Wrote {outputs.weekly_risk_path}")
    typer.echo(f"Wrote {outputs.county_geojson_path}")
```

- [ ] **Step 4: Run CLI tests to verify GREEN**

Run:

```bash
./.venv/bin/pytest tests/test_cli_dashboard_assets.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add tickbiterisk/cli.py tests/test_cli_dashboard_assets.py
git commit -m "feat: add dashboard asset CLI"
```

## Task 3: Static Dashboard Shell

**Files:**
- Create: `public/index.html`
- Create: `public/styles.css`
- Test: `tests/test_public_dashboard_static.py`

- [ ] **Step 1: Write failing static file tests**

Create `tests/test_public_dashboard_static.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
./.venv/bin/pytest tests/test_public_dashboard_static.py -q
```

Expected: fail because `public/index.html` and `public/styles.css` do not exist.

- [ ] **Step 3: Create dashboard HTML**

Create `public/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TickBiteRisk Maryland Dashboard</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <a class="skip-link" href="#county-panel">Skip to county risk details</a>
    <header class="site-header">
      <div>
        <p class="eyebrow">Maryland county-week Lyme baseline</p>
        <h1>TickBiteRisk</h1>
        <p class="lede">
          Relative seasonal Lyme risk context by Maryland county.
        </p>
      </div>
      <p class="disclaimer">
        Informational only. Not medical advice. Follow CDC guidance and contact
        a healthcare professional about your situation.
      </p>
    </header>

    <main class="dashboard" aria-live="polite">
      <section class="controls" aria-labelledby="controls-title">
        <h2 id="controls-title">Choose a date and county</h2>
        <label for="date-input">Date</label>
        <input id="date-input" type="date" />
        <p id="week-label" class="muted">Loading week...</p>
      </section>

      <section class="map-section" aria-labelledby="map-title">
        <h2 id="map-title">Maryland county map</h2>
        <div id="risk-map" class="risk-map" role="group" aria-label="Maryland county risk map">
          <p class="loading">Loading map...</p>
        </div>
        <div class="legend" aria-label="Risk score legend">
          <span><b class="swatch risk-very-low"></b>1-2 very low</span>
          <span><b class="swatch risk-low"></b>3-4 low</span>
          <span><b class="swatch risk-moderate"></b>5-6 moderate</span>
          <span><b class="swatch risk-high"></b>7-8 high</span>
          <span><b class="swatch risk-very-high"></b>9-10 very high</span>
        </div>
      </section>

      <aside id="county-panel" class="county-panel" aria-labelledby="panel-title">
        <h2 id="panel-title">County risk details</h2>
        <div id="panel-content">
          <p>Select a county to see its relative seasonal Lyme baseline.</p>
        </div>
      </aside>

      <section class="county-list-section" aria-labelledby="county-list-title">
        <h2 id="county-list-title">County list</h2>
        <div id="county-list" class="county-list"></div>
      </section>

      <section class="sources" aria-labelledby="sources-title">
        <h2 id="sources-title">Sources and notes</h2>
        <details>
          <summary>Model and source details</summary>
          <div id="source-content">
            <p>Loading source notes...</p>
          </div>
        </details>
      </section>
    </main>

    <script src="app.js" defer></script>
  </body>
</html>
```

- [ ] **Step 4: Create dashboard CSS**

Create `public/styles.css` with the first accessible layout:

```css
:root {
  color-scheme: light;
  --bg: #f7f8f5;
  --panel: #ffffff;
  --ink: #17201b;
  --muted: #56635c;
  --line: #cbd5ce;
  --focus: #005fcc;
  --very-low: #eef7e7;
  --low: #cfe8b6;
  --moderate: #fed976;
  --high: #f1695b;
  --very-high: #9e1b32;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.5;
}

a {
  color: #064f8e;
}

button,
input,
summary {
  font: inherit;
}

:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 3px;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
  background: var(--ink);
  color: white;
  padding: 0.75rem 1rem;
  z-index: 10;
}

.skip-link:focus {
  top: 1rem;
}

.site-header {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr);
  padding: 1.25rem;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
}

.eyebrow,
.muted {
  color: var(--muted);
}

.eyebrow {
  margin: 0 0 0.25rem;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 0.25rem;
  font-size: clamp(2rem, 5vw, 3.4rem);
}

.lede,
.disclaimer {
  max-width: 68ch;
}

.disclaimer {
  margin: 0;
  padding: 0.75rem;
  border-left: 4px solid var(--focus);
  background: #eef5ff;
}

.dashboard {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
  padding: 1rem;
}

.controls,
.map-section,
.county-panel,
.county-list-section,
.sources {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 1rem;
}

.risk-map {
  min-height: 360px;
}

.risk-map svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 70vh;
}

.county-shape {
  stroke: #26352d;
  stroke-width: 0.7;
  cursor: pointer;
}

.county-shape[aria-pressed="true"] {
  stroke: #000;
  stroke-width: 2.25;
}

.risk-very-low {
  fill: var(--very-low);
  background: var(--very-low);
}

.risk-low {
  fill: var(--low);
  background: var(--low);
}

.risk-moderate {
  fill: var(--moderate);
  background: var(--moderate);
}

.risk-high {
  fill: var(--high);
  background: var(--high);
}

.risk-very-high {
  fill: var(--very-high);
  background: var(--very-high);
  color: #fff;
}

.legend,
.county-list {
  display: grid;
  gap: 0.5rem;
}

.legend {
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  margin-top: 1rem;
}

.swatch {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  margin-right: 0.35rem;
  border: 1px solid #333;
  vertical-align: -0.15rem;
}

.county-list button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  padding: 0.65rem 0.75rem;
  text-align: left;
}

.score-badge {
  display: inline-grid;
  min-width: 3.25rem;
  place-items: center;
  border-radius: 999px;
  border: 1px solid #333;
  padding: 0.2rem 0.5rem;
  font-weight: 700;
}

@media (min-width: 920px) {
  .dashboard {
    grid-template-columns: minmax(420px, 1.35fr) minmax(320px, 0.8fr);
    align-items: start;
  }

  .controls,
  .county-list-section,
  .sources {
    grid-column: 1 / -1;
  }
}
```

- [ ] **Step 5: Run static tests to verify GREEN**

Run:

```bash
./.venv/bin/pytest tests/test_public_dashboard_static.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add public/index.html public/styles.css tests/test_public_dashboard_static.py
git commit -m "feat: add static dashboard shell"
```

## Task 4: Dashboard JavaScript

**Files:**
- Create: `public/app.js`
- Modify: `tests/test_public_dashboard_static.py`

- [ ] **Step 1: Extend static tests for JavaScript contracts**

Append this test to `tests/test_public_dashboard_static.py`:

```python
def test_dashboard_javascript_has_expected_runtime_functions() -> None:
    js = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")

    for token in [
        "function mmwrYearWeek",
        "function riskClass",
        "function renderCountyList",
        "function renderMap",
        "function selectCounty",
        "fetchJson",
    ]:
        assert token in js
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
./.venv/bin/pytest tests/test_public_dashboard_static.py -q
```

Expected: fail because `public/app.js` does not exist.

- [ ] **Step 3: Create dashboard JavaScript**

Create `public/app.js`:

```javascript
const state = {
  weekly: null,
  counties: null,
  modelCard: null,
  sourceCatalog: null,
  selectedCounty: "24003",
  selectedWeek: 1,
  byCountyWeek: new Map(),
};

const dataPaths = {
  weekly: "data/md_county_risk_weekly.json",
  counties: "data/md_counties.geojson",
  modelCard: "data/model_card.json",
  sourceCatalog: "data/source_catalog.json",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setDefaultDate();
  document.getElementById("date-input").addEventListener("change", handleDateChange);
  try {
    const [weekly, counties, modelCard, sourceCatalog] = await Promise.all([
      fetchJson(dataPaths.weekly),
      fetchJson(dataPaths.counties),
      fetchJson(dataPaths.modelCard),
      fetchJson(dataPaths.sourceCatalog),
    ]);
    state.weekly = weekly;
    state.counties = counties;
    state.modelCard = modelCard;
    state.sourceCatalog = sourceCatalog;
    indexWeeklyRecords(weekly.records);
    renderMap();
    renderCountyList();
    renderSources();
    selectCounty(state.selectedCounty);
  } catch (error) {
    renderLoadError(error);
  }
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Could not load ${path}`);
  }
  return response.json();
}

function setDefaultDate() {
  const input = document.getElementById("date-input");
  const today = new Date();
  input.value = today.toISOString().slice(0, 10);
  const [, week] = mmwrYearWeek(input.value);
  state.selectedWeek = week;
  updateWeekLabel();
}

function handleDateChange(event) {
  const [, week] = mmwrYearWeek(event.target.value);
  state.selectedWeek = week;
  updateWeekLabel();
  renderMap();
  renderCountyList();
  selectCounty(state.selectedCounty);
}

function mmwrYearWeek(dateString) {
  const date = new Date(`${dateString}T12:00:00Z`);
  const day = date.getUTCDay();
  const sunday = new Date(date);
  sunday.setUTCDate(date.getUTCDate() - day);
  const thursday = new Date(sunday);
  thursday.setUTCDate(sunday.getUTCDate() + 4);
  const mmwrYear = thursday.getUTCFullYear();
  const jan4 = new Date(Date.UTC(mmwrYear, 0, 4, 12));
  const firstSunday = new Date(jan4);
  firstSunday.setUTCDate(jan4.getUTCDate() - jan4.getUTCDay());
  const week = Math.floor((sunday - firstSunday) / (7 * 24 * 60 * 60 * 1000)) + 1;
  return [mmwrYear, week];
}

function updateWeekLabel() {
  document.getElementById("week-label").textContent = `Using MMWR week ${state.selectedWeek}`;
}

function indexWeeklyRecords(records) {
  state.byCountyWeek.clear();
  for (const record of records) {
    state.byCountyWeek.set(`${record.county_fips}:${record.mmwr_week}`, record);
  }
}

function getRecord(countyFips) {
  return state.byCountyWeek.get(`${countyFips}:${state.selectedWeek}`);
}

function riskClass(score) {
  if (score >= 9) return "risk-very-high";
  if (score >= 7) return "risk-high";
  if (score >= 5) return "risk-moderate";
  if (score >= 3) return "risk-low";
  return "risk-very-low";
}

function renderMap() {
  const container = document.getElementById("risk-map");
  if (!state.counties) return;
  const bounds = geoBounds(state.counties.features);
  const width = 720;
  const height = 520;
  const paths = state.counties.features
    .map((feature) => {
      const props = feature.properties;
      const record = getRecord(props.county_fips);
      const score = record ? record.risk_score : 0;
      const label = record
        ? `${props.county_name}, ${record.risk_category}, ${score} of 10`
        : `${props.county_name}, no baseline available`;
      return `<path
        class="county-shape ${record ? riskClass(score) : ""}"
        d="${geometryPath(feature.geometry, bounds, width, height)}"
        data-county="${props.county_fips}"
        role="button"
        tabindex="0"
        aria-label="${escapeHtml(label)}"
        aria-pressed="${props.county_fips === state.selectedCounty ? "true" : "false"}">
        <title>${escapeHtml(label)}</title>
      </path>`;
    })
    .join("");
  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Maryland counties colored by relative Lyme seasonal baseline">${paths}</svg>`;
  container.querySelectorAll("[data-county]").forEach((shape) => {
    shape.addEventListener("click", () => selectCounty(shape.dataset.county));
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCounty(shape.dataset.county);
      }
    });
  });
}

function renderCountyList() {
  const list = document.getElementById("county-list");
  const features = state.counties ? state.counties.features : [];
  list.innerHTML = features
    .map((feature) => {
      const props = feature.properties;
      const record = getRecord(props.county_fips);
      const score = record ? record.risk_score : "NA";
      const category = record ? record.risk_category.replaceAll("_", " ") : "unavailable";
      const badgeClass = record ? riskClass(record.risk_score) : "";
      return `<button type="button" data-county="${props.county_fips}">
        <span>${escapeHtml(props.county_name)}<br><small>${category}</small></span>
        <span class="score-badge ${badgeClass}">${score}/10</span>
      </button>`;
    })
    .join("");
  list.querySelectorAll("button[data-county]").forEach((button) => {
    button.addEventListener("click", () => selectCounty(button.dataset.county));
  });
}

function selectCounty(countyFips) {
  state.selectedCounty = countyFips;
  const record = getRecord(countyFips);
  const feature = state.counties.features.find(
    (item) => item.properties.county_fips === countyFips
  );
  const countyName = feature ? feature.properties.county_name : countyFips;
  const panel = document.getElementById("panel-content");
  if (!record) {
    panel.innerHTML = `<p>No baseline row available for ${escapeHtml(countyName)} in week ${state.selectedWeek}.</p>`;
    updateSelectedControls();
    return;
  }
  panel.innerHTML = `<div class="score-card">
    <p class="muted">MMWR week ${record.mmwr_week}, data year ${record.data_year}</p>
    <h3>${escapeHtml(record.county_name)}</h3>
    <p><span class="score-badge ${riskClass(record.risk_score)}">${record.risk_score}/10</span> ${escapeHtml(record.risk_category.replaceAll("_", " "))}</p>
    <p>${escapeHtml(sentenceCase(record.risk_category))} relative seasonal baseline for Lyme reports in Maryland counties like this one during this week.</p>
    <p>Predicted weekly incidence: ${formatNumber(record.predicted_weekly_incidence_per_100k)} per 100k.</p>
    <p>95% empirical interval: ${formatNumber(record.predicted_weekly_incidence_95_interval[0])} to ${formatNumber(record.predicted_weekly_incidence_95_interval[1])} per 100k.</p>
    <p class="disclaimer">This is not a personal infection probability or medical advice.</p>
  </div>`;
  updateSelectedControls();
}

function updateSelectedControls() {
  document.querySelectorAll("[data-county]").forEach((element) => {
    const isSelected = element.dataset.county === state.selectedCounty;
    element.setAttribute("aria-pressed", String(isSelected));
    element.classList.toggle("is-selected", isSelected);
  });
}

function renderSources() {
  const target = document.getElementById("source-content");
  const links = state.weekly.guidance_links
    .map((link) => `<li><a href="${link.url}">${escapeHtml(link.title)}</a></li>`)
    .join("");
  target.innerHTML = `<p>${escapeHtml(state.modelCard.score_interpretation)}</p>
    <ul>${links}</ul>
    <p>Source branch: ${escapeHtml(state.weekly.model_name)} / ${escapeHtml(state.weekly.seasonality_source_id)}</p>`;
}

function renderLoadError(error) {
  document.getElementById("risk-map").innerHTML = `<p role="alert">${escapeHtml(error.message)}</p>`;
  document.getElementById("panel-content").innerHTML = "<p>Dashboard data bundle is unavailable.</p>";
}

function geoBounds(features) {
  const points = features.flatMap((feature) => coordinates(feature.geometry));
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function coordinates(geometry) {
  if (geometry.type === "Polygon") return geometry.coordinates.flat();
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(2);
  if (geometry.type === "Point") return [geometry.coordinates];
  return [];
}

function geometryPath(geometry, bounds, width, height) {
  if (geometry.type === "Polygon") {
    return polygonPath(geometry.coordinates, bounds, width, height);
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => polygonPath(polygon, bounds, width, height))
      .join(" ");
  }
  const [x, y] = projectPoint(geometry.coordinates, bounds, width, height);
  return `M ${x - 3} ${y - 3} h 6 v 6 h -6 Z`;
}

function polygonPath(rings, bounds, width, height) {
  return rings
    .map((ring) =>
      ring
        .map((point, index) => {
          const [x, y] = projectPoint(point, bounds, width, height);
          return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
        })
        .join(" ") + " Z"
    )
    .join(" ");
}

function projectPoint(point, bounds, width, height) {
  const padding = 20;
  const x =
    padding +
    ((point[0] - bounds.minX) / (bounds.maxX - bounds.minX)) *
      (width - padding * 2);
  const y =
    padding +
    ((bounds.maxY - point[1]) / (bounds.maxY - bounds.minY)) *
      (height - padding * 2);
  return [x, y];
}

function sentenceCase(value) {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function formatNumber(value) {
  return Number(value).toFixed(2);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return replacements[char];
  });
}
```

- [ ] **Step 4: Add CSS for selected map controls**

Append to `public/styles.css`:

```css
.score-card h3 {
  margin-bottom: 0.5rem;
}

.county-shape:hover,
.county-shape:focus-visible,
.county-shape.is-selected {
  stroke: #000;
  stroke-width: 2.4;
}
```

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
./.venv/bin/pytest tests/test_public_dashboard_static.py -q
```

Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add public/app.js public/styles.css tests/test_public_dashboard_static.py
git commit -m "feat: add static dashboard runtime"
```

## Task 5: Generate Public Dashboard Data

**Files:**
- Create/Update: `public/data/*.json`

- [ ] **Step 1: Generate dashboard assets from real derived data**

Run:

```bash
./.venv/bin/python -m tickbiterisk.cli dashboard build-assets \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --output-dir public/data
```

Expected output includes:

```text
Wrote dashboard assets to public/data
Wrote public/data/md_county_risk_weekly.json
Wrote public/data/md_counties.geojson
```

- [ ] **Step 2: Verify generated data shape**

Run:

```bash
./.venv/bin/python - <<'PY'
import json
from pathlib import Path
root = Path("public/data")
weekly = json.loads((root / "md_county_risk_weekly.json").read_text())
geo = json.loads((root / "md_counties.geojson").read_text())
print("weekly_records", weekly["record_count"])
print("geo_features", len(geo["features"]))
print("first_geo", geo["features"][0]["properties"])
PY
```

Expected:

```text
weekly_records 1272
geo_features 24
first_geo {'county_fips': '24001', 'county_name': 'Allegany County'}
```

- [ ] **Step 3: Commit generated public data**

```bash
git add public/data
git commit -m "data: add public dashboard assets"
```

## Task 6: Dashboard Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/public-product-boundary.md`
- Modify: `docs/data-manifest.md`
- Modify: `docs/software-requirements-spec.md`

- [ ] **Step 1: Update README**

Add to `README.md` under the static/dashboard command area:

````markdown
## static dashboard

Build public dashboard assets:

```bash
tickbiterisk dashboard build-assets --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv --output-dir public/data
```

Run locally:

```bash
python -m http.server 8000 --directory public
```

Open `http://localhost:8000`.
````

- [ ] **Step 2: Update public product boundary**

In `docs/public-product-boundary.md`, add `public/data/md_counties.geojson` to the runtime data shape and add this paragraph:

```markdown
The static dashboard root is `public/`. The dashboard may publish a simplified Maryland county GeoJSON derived from public Census TIGERweb geometry. Geometry must include only county FIPS, county name, and geometry; it must not include raw surveillance records.
```

- [ ] **Step 3: Update data manifest**

Add a source row to `docs/data-manifest.md`:

```markdown
| `census_tigerweb_md_counties_geojson` | Census TIGERweb Maryland county geometry | `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/82/query` | GeoJSON | Maryland counties | Current TIGERweb county layer | Public dashboard map geometry | acquired, etl_supported, static_export_supported | Public Census geography; publish simplified derived GeoJSON | `tickbiterisk dashboard build-assets` writes `public/data/md_counties.geojson` with `county_fips`, `county_name`, and geometry only. |
```

- [ ] **Step 4: Update SRS**

Add a short requirement after FR4D in `docs/software-requirements-spec.md`:

```markdown
### FR4E: Static Dashboard Prototype

The system must expose a static dashboard under `public/` that reads only `public/data` assets, requires no backend credentials, and presents the county-week Lyme baseline with accessible map, county list, detail panel, CDC guidance links, and plain-language caveats. The dashboard must not describe the score as diagnosis, treatment guidance, personal infection probability, or weather-adjusted forecast.
```

- [ ] **Step 5: Commit docs**

```bash
git add README.md docs/public-product-boundary.md docs/data-manifest.md docs/software-requirements-spec.md
git commit -m "docs: document static dashboard"
```

## Task 7: Verification And Local Browser Smoke

**Files:**
- No new files expected unless fixes are needed.

- [ ] **Step 1: Run Python verification**

Run:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest -q
git diff --check
```

Expected:

```text
All checks passed!
250+ passed
```

- [ ] **Step 2: Start local static server**

Run:

```bash
python -m http.server 8000 --directory public
```

Keep the server running until browser checks are done.

- [ ] **Step 3: Browser checks**

Open:

```text
http://localhost:8000
```

Verify:

- Dashboard loads without JavaScript console errors.
- Date input changes week label.
- County list renders 24 Maryland jurisdictions.
- Map area renders interactive county controls.
- Selecting Anne Arundel County updates the panel.
- CDC links are visible in the sources disclosure.
- Keyboard tab order reaches date input, map/list controls, panel, and links.
- Mobile viewport does not overlap text or controls.

- [ ] **Step 4: Stop local server**

Stop the server process.

- [ ] **Step 5: Final commit if verification fixes were needed**

If fixes were required:

```bash
git add public tickbiterisk tests README.md docs
git commit -m "fix: polish static dashboard prototype"
```

If no fixes were required, do not create an empty commit.

## Self-Review Notes

Spec coverage:

- Static GitHub Pages shape: Tasks 3, 5, and 7.
- Public `public/data` assets: Tasks 1, 2, and 5.
- Accessible map/list/panel: Tasks 3, 4, and 7.
- Plain-language caveats and CDC links: Tasks 3, 4, and 6.
- Geometry source decision: Tasks 1 and 5 use Census TIGERweb and avoid the large local CDC geodata.
- Future layers stay out of v0: no task implements weather, habitat, deer, vector/pathogen, or personal clinical scoring.

Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.

Type consistency:

- `DashboardAssetPaths` fields match CLI output and tests.
- `write_dashboard_assets` delegates risk JSON writing to `export_static_risk_data`.
- `public/app.js` data file names match the static export contract.
