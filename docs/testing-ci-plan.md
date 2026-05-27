# TickBiteRisk Testing And CI Plan

## Current CI plan

The current project is a Python ETL/modeling package plus a static dashboard.
The CI plan should prove that the local pipeline code, public JSON artifacts,
and static browser assets remain usable.

Required local verification before a release commit:

```bash
PYTHONPATH=. ./.venv/bin/python -m ruff check .
PYTHONPATH=. ./.venv/bin/python -m pytest -q
node --check public/app.js
```

Public artifact checks:

- public data JSON parses,
- `public/data/static_export_manifest.json` exists after export,
- `public/data/model_card.json` includes non-medical caveats,
- dashboard JavaScript passes syntax checks,
- GitHub Pages workflow references only public-safe files.

## Test tiers

| Tier | Scope | Trigger |
| --- | --- | --- |
| Lint | Ruff over package, tests, scripts, and docs-adjacent Python helpers | Every development slice and CI |
| Unit | Parsers, normalizers, model helpers, risk lookup/export logic | Every development slice and CI |
| ETL fixture | Small fixture-based ETL runs for each source family | CI and source-parser changes |
| Live smoke | Explicit local runs against acquired/raw files | Before refreshing derived artifacts |
| Static product | JSON parse, dashboard asset syntax, source/model-card caveat checks | Before public export commit |
| Accessibility/browser | Keyboard, contrast, map/panel smoke checks | Dashboard polish milestone |

## Current quality gates

| Gate | Required |
| --- | --- |
| `ruff check .` | yes |
| `pytest -q` | yes |
| Public JSON parse check | yes for dashboard data changes |
| `node --check public/app.js` | yes for dashboard changes |
| `git diff --check` | yes before commit |
| Raw data excluded from public artifacts | yes |

## GitHub Pages checks

The public product is static. CI should treat GitHub Pages as a file publishing
target, not as an application server:

- no runtime secrets,
- no private raw data paths,
- no generated files outside the public artifact boundary,
- model card and source catalog included with every score export,
- dashboard caveats visible without user interaction.

## Future validation jobs

Later releases can add scheduled data refresh and model-validation jobs once the
refresh recipe is stable. Those jobs should publish derived metrics and model
comparison reports, not raw acquired data.

Last updated: 2026-05-27.
