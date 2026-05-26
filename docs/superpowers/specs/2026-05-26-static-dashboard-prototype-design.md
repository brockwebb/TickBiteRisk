# Static Dashboard Prototype Design

Date: 2026-05-26  
Status: Draft design, awaiting review  
Scope: Static GitHub Pages prototype for Maryland county-week Lyme risk baseline

## Purpose

Build the first public-facing TickBiteRisk viewer as a static, accessible web dashboard. The prototype should make the derived Maryland county-week Lyme seasonal baseline understandable without requiring Postgres, raw data, API servers, credentials, or a live network call beyond loading static files from the deployed site.

The first prototype answers one narrow question:

```text
For this Maryland county and week, what is the relative Lyme disease seasonal baseline?
```

It does not yet answer:

- How likely am I to pick up a tick today?
- What is my personal probability of disease after a specific attached tick?
- Should I seek treatment?

Those are later layers once weather, habitat, host/vector, tick status, and individual exposure inputs are modeled and reviewed.

## Product Framing

The dashboard must preserve the same language as the public data export:

- Relative Maryland county-week Lyme baseline.
- 1-10 score with category labels.
- Informational and educational only.
- Not medical advice.
- Not a diagnosis.
- Not a per-bite infection probability.
- Not a weather-adjusted forecast.

The page should still be useful after a person finds a tick, but the wording should be "risk context" and "CDC guidance," not "your disease probability."

## Recommended Approach

Use a lightweight static web app committed in this repository and deploy it with GitHub Pages. Put the first app under `public/` so it matches the existing `tickbiterisk risk export-static` default output shape.

Recommended source layout:

```text
public/
  index.html
  styles.css
  app.js
  vendor/              # only if a small vendored map helper is chosen
  data/
    md_county_risk_weekly.json
    md_county_metadata.json
    model_card.json
    source_catalog.json
    static_export_manifest.json
    md_counties.geojson
```

The `public/data/*.json` files should be generated or copied from `tickbiterisk risk export-static`. The dashboard should not read from ignored `build/` files in production. A later automation can refresh `public/data` from the derived artifact.

GitHub Pages can publish static HTML, CSS, JavaScript, and JSON directly from a repository folder or a GitHub Actions build artifact. Use Pages as static hosting only; do not introduce server-side code.

## Data Inputs

### Risk JSON

Input files:

```text
md_county_risk_weekly.json
md_county_metadata.json
model_card.json
source_catalog.json
static_export_manifest.json
```

These files come from:

```bash
tickbiterisk risk export-static \
  --scores-path build/etl/county-week-risk/county_week_seasonal_risk_baseline.csv \
  --output-dir public/data
```

The dashboard should load the weekly file once at startup and index it by:

```text
county_fips, mmwr_week
```

The first version may use a simple week selector instead of full calendar date conversion. If a calendar date picker is included, the date-to-MMWR conversion must match the runtime lookup implementation.

### County Geometry

Add a small Maryland county GeoJSON file:

```text
public/data/md_counties.geojson
```

Preferred source:

- Census cartographic boundary county GeoJSON or shapefile filtered to Maryland and simplified for the web.

Fallback source:

- Existing local CDC county geodata only if redistribution is reviewed and the file is simplified to Maryland county boundaries.

The committed geometry should include only public geography fields needed by the dashboard:

```text
county_fips
county_name
geometry
```

Do not commit the large local 89 MB CDC geodata file.

## User Interface

First viewport:

- Header with product name and short disclaimer.
- Maryland county map.
- Week selector.
- Selected county detail panel.
- County list/table fallback below or beside the map.

County interaction:

- Click or keyboard-select a county.
- Hover may show a tooltip, but hover must not be required.
- Selecting a county updates the panel and the county list focus state.

County panel:

- County name.
- Selected MMWR week.
- Risk score, category, and short plain-language explanation.
- Predicted weekly incidence per 100k and 95 percent empirical interval.
- Quality flags translated into readable labels.
- CDC guidance links.
- Expandable "Sources and model notes" section.

Plain-language score copy should be compact:

```text
High relative seasonal baseline for Lyme reports in Maryland counties like this one during this week.
```

Follow with caveat text:

```text
This is not a personal infection probability or medical advice.
```

## Accessibility And 508 Target

The dashboard should target Section 508-compatible behavior by building toward WCAG Level AA expectations. Section 508 incorporates WCAG 2.0 Level AA for web content; we should aim for WCAG 2.1 AA where practical.

Accessibility requirements:

- Color is never the only risk signal.
- Every risk area has a numeric score and category label.
- Map counties are keyboard selectable.
- The county list/table provides a complete non-map path.
- Focus states are visible.
- Interactive elements are real buttons, links, selects, or inputs.
- County shapes have accessible labels, such as "Anne Arundel County, high, 7 of 10."
- All source/caveat disclosures use semantic disclosure buttons.
- Text contrast meets AA contrast targets.
- The page has a skip link and sensible heading order.
- The dashboard works at desktop and mobile widths.

Color approach:

- Use a sequential risk palette with red as the high-risk end.
- Avoid relying on red alone; include labels, score badges, and table values.
- Keep map border and selected-county focus contrast strong.
- Prefer five category classes over a continuous gradient for readability and legend clarity.

Suggested category classes:

```text
1-2  very low
3-4  low
5-6  moderate
7-8  high
9-10 very high
```

## Architecture

The first dashboard can be plain HTML/CSS/JavaScript.

Rationale:

- No front-end stack exists in the repo yet.
- The data is static JSON.
- GitHub Pages can serve the app without a build step.
- Plain files reduce deployment and maintenance friction.

If a map library is needed, prefer a small dependency path:

1. Inline SVG generated from GeoJSON if the geometry can be converted cleanly.
2. Leaflet only if pan/zoom and GeoJSON rendering save meaningful time.

Do not add React/Vite for v0 unless the UI complexity grows beyond map, panel, selector, and disclosures.

## Data Flow

```text
derived CSV
  -> tickbiterisk risk export-static
  -> public/data/*.json
  -> dashboard fetch()
  -> in-memory county/week index
  -> map fill + panel + table
```

The browser never receives raw CDC/NOAA/DNR files. It receives only derived public artifacts and public county geometry.

## Error Handling

Startup failures:

- If any JSON file fails to load, show a plain error panel with the missing file name.
- Keep the page navigable and explain that the dashboard data bundle is unavailable.

Missing county/week:

- Show "No baseline row available for this county/week."
- Do not infer or interpolate in the browser.

Geometry mismatch:

- If a county is in the risk JSON but not the GeoJSON, list it in the table with a warning flag.
- If a county is in the GeoJSON but not the risk JSON, render it as unavailable.

## Testing And Verification

Implementation should include:

- Unit tests for MMWR week/date conversion if date picker is implemented.
- Unit tests for risk category lookup and missing data behavior.
- Static smoke test that loads the generated JSON and confirms 24 Maryland jurisdictions and 53 weeks.
- Browser verification on desktop and mobile widths.
- Accessibility checks with keyboard-only navigation.
- Automated accessibility scan if the repo adds a browser test dependency.

Manual acceptance checklist:

- User can select Anne Arundel County with mouse and keyboard.
- User can change week and see the panel update.
- User can get the same information from the table/list without using the map.
- CDC links are visible and usable.
- Disclaimer is visible before detailed risk interpretation.
- No UI text claims diagnosis, treatment, per-bite probability, or weather-adjusted forecast.

## Deployment

Use GitHub Pages for the first public prototype.

Two acceptable deployment paths:

1. Publish `public/` directly as the Pages source.
2. Use GitHub Actions to copy/generate `public/data`, then publish a static artifact.

The first implementation can run locally from a small static server:

```bash
python -m http.server 8000 --directory public
```

The app should not require private environment variables.

## Future Layers

After the first dashboard works, add layers in this order:

1. Weather-adjusted weekly modifier using NOAA/Open-Meteo-derived features.
2. Habitat/land-cover layer using NLCD or derived county summaries.
3. Deer/host pressure layer using DNR harvest density and possibly mast/acorn context.
4. Tick/vector/pathogen status layer with careful terms review and status-only caveats.
5. Personal tick-found guidance flow that asks simple questions and links to CDC guidance, without producing unsupported clinical probabilities.

The UI can later expose separate tabs:

- County seasonal disease baseline.
- Environmental exposure context.
- After finding a tick.
- Sources and methods.

Do not show disabled or speculative score layers in v0.

## Open Decisions

These decisions should be made before implementation:

1. Whether v0 uses a week selector only or a calendar date picker with MMWR conversion.
2. Whether v0 uses inline SVG or Leaflet for the county map.
3. Whether `public/data` should be committed immediately or generated by a Pages workflow.

Recommended defaults:

1. Calendar date picker, because users think in dates rather than MMWR weeks.
2. Inline SVG if practical; Leaflet only if geometry rendering takes too long.
3. Commit generated `public/data` for the first prototype, then automate refresh later.
