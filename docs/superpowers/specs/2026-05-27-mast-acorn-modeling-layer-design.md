# Mast/Acorn Modeling Layer Design

Date: 2026-05-27
Status: Approved by expanded user direction
Scope: Maryland DNR mast/acorn extraction, lagged model features, model comparison refresh, and easy source catalog additions

## Goal

Use the defensible mast/acorn data already present in the Maryland DNR Western Maryland reports and carry it into the model comparison layer without leaking same-year information. Catalog easy official ecology sources that can be picked up next without starting raster or GIS work.

## Source Decision

The three local DNR PDFs are text-extractable with `pypdfium2`. Docling is installed but slow or hung during bounded probes, and OCR is not needed for these files. Keep `pypdfium` as the default parser and preserve Docling as an optional parser path for future documents that need it.

The reports contain rolling five-year tables, not only report-year values:

- 2017 report: 2013-2017
- 2020 report: 2016-2020
- 2021 report: 2017-2021

Extraction should preserve source-report lineage and allow overlapping values to remain visible in the raw mast output. Modeling should dedupe overlaps by choosing the newest source report for a given county observation year.

## Extraction Design

Parse three DNR table families when present:

- Table 1 quantitative acorn abundance by county, oak group, and year.
- Table 2 mast abundance ratings by county, oak group, and year.
- Table 3 subjective crown acorn percentage by county, oak group, and year.

Emit county-year rows for Garrett, Allegany, Washington, and Frederick only. Do not generalize to statewide Maryland counties.

Required lineage and quality fields:

- `source_report_year`
- `parser_method`
- `extraction_confidence`
- `black_oak_acorns_per_branch`
- `white_oak_acorns_per_branch`
- `unit_average_acorns_per_branch`
- `black_oak_mast_rating`
- `white_oak_mast_rating`
- `unit_average_mast_rating`
- `white_oak_subjective_crown_pct`
- `black_oak_subjective_crown_pct`
- `western_maryland_only`
- `study_plot_not_countywide`

Existing compatibility fields remain populated where defensible: `mast_index`, `hard_mast_index`, and `acorn_index` use the unit-average acorn abundance; `mast_rating` uses the unit-average rating label.

## Modeling Design

Add `--mast-acorn-path` to `tickbiterisk etl model-features`. When supplied or when the default mast output exists, join mast observations as prior-year features:

```text
mast observation year N -> Lyme model year N+1
```

This mirrors the existing deer prior-season pattern and avoids using same-year mast in forecast-oriented model lanes.

Model feature columns should include prior-year mast/acorn numeric fields, mast source IDs, parser/confidence lineage, and mast feature quality flags. Missing mast rows should add `missing_mast_acorn_prior_year` only when mast input is opted in.

Design matrix output should include mast numeric fields plus paired missing indicators. Model comparison should include prior-year mast fields in ecology lanes, not in the forecast-safe baseline lane. Scope and parser quality flags should remain caveats, not predictive shortcuts.

## Easy Source Additions

Catalog these official sources now, but do not process them in this slice unless a small direct CSV is trivial:

- EPA EnviroAtlas national county CSV batch downloads for static county habitat/environment indicators.
- USDA Forest Service FIA/EVALIDator and FIADB API source pages for future forest/oak-hickory context.
- Maryland DNR Archery Hunter Survey page/report for future wildlife-observation context.

Defer full Annual NLCD/CDL raster processing, NEON product joins, neighboring-state mast proxies, and sensitive Natural Heritage spatial data.

## Acceptance Criteria

- `tickbiterisk etl mast-acorn` writes structured DNR county-year rows from the three local PDFs.
- Raw mast rows preserve overlapping source-report lineage and Western Maryland study-plot caveats.
- `tickbiterisk etl model-features` joins official mast rows as prior-year predictors.
- `tickbiterisk etl model-design-matrix` emits numeric mast features and missing indicators.
- `tickbiterisk etl model-compare` includes mast features in ecology comparison lanes only.
- Docs and source catalog reflect the new extraction status and caveats.
- Tests, lint, dashboard smoke, and a live ETL/model rebuild pass.
