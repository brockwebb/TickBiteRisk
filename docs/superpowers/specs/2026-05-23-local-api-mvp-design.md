# TickBiteRisk Local API MVP Design

Date: 2026-05-23

## Purpose

Build the first runnable TickBiteRisk product slice: a local FastAPI service that estimates per-bite Lyme disease risk from bundled sample county records and a transparent dose-response calculation.

The MVP must be useful for development, demos, tests, and future model work. It must not imply clinical-grade precision. Every response must expose data source quality and include a non-medical-advice disclaimer.

## Scope

In scope:

- A Python package named `tickbiterisk`.
- A FastAPI app serving `GET /risk`.
- Bundled sample data for a small set of counties.
- A CDC workbook importer that normalizes county tick/pathogen status records from a local file path or URL.
- Unit and API tests for the risk math, validation, data loading, importer, and response contract.
- Developer docs for installing, running, testing, and importing data.

Out of scope for this slice:

- PyMC/CAR modeling.
- Live scheduled ETL.
- PostGIS or Docker Compose.
- React dashboard.
- Clinical decision support or treatment recommendations.
- Bundling full CDC-derived datasets until redistribution terms are explicitly resolved.

## Build Approach

Use a small but real package layout:

```text
tickbiterisk/
  __init__.py
  api.py
  cli.py
  data.py
  schemas.py
  model/
    __init__.py
    risk.py
  importers/
    __init__.py
    cdc.py
  resources/
    sample_counties.csv
tests/
  test_api.py
  test_data.py
  test_importers_cdc.py
  test_risk.py
pyproject.toml
```

The package should be installable with `pip install -e ".[dev]"`. The API should run locally with:

```bash
uvicorn tickbiterisk.api:app --reload
```

## Data Model

The bundled county sample file is the canonical runtime data source for v0.1. Each row represents the best currently available local prior for a county.

Required normalized fields:

- `fips`: five-digit county FIPS code.
- `state`: two-letter postal abbreviation.
- `county`: county name.
- `ixodes_scapularis_status`: `established`, `reported`, or `no_records`.
- `ixodes_pacificus_status`: `established`, `reported`, or `no_records`.
- `borrelia_burgdorferi_status`: `present` or `no_records`.
- `theta_mean`: estimated probability that an Ixodes tick from the county carries *Borrelia burgdorferi*.
- `theta_lower`: lower uncertainty bound for `theta_mean`.
- `theta_upper`: upper uncertainty bound for `theta_mean`.
- `theta_source`: source label such as `sample_prior`, `status_imputed`, or `observed_prevalence`.
- `data_quality`: `sample`, `status_only`, `observed`, or `insufficient`.
- `source_updated`: source date if known.

The sample data should include at least:

- Anne Arundel County, MD (`24003`) as a moderate/high example.
- Fairfield County, CT (`09001`) as a high-endemic example.
- Autauga County, AL (`01001`) as a status-imputed or low-certainty example.
- A western example where `ixodes_pacificus` is relevant.
- One county with insufficient or no-records data.

## CDC Importer

The CDC importer reads the public CDC Ixodes county status workbook and, when supplied, the CDC Ixodes pathogen status workbook. It accepts local paths and HTTPS URLs.

Expected importer behavior:

- Parse county-level rows using FIPS codes when present.
- Normalize status strings to stable lowercase enum-like values.
- Preserve source metadata such as workbook path/URL and worksheet name.
- Produce normalized county records with `theta_source=status_imputed` unless explicit prevalence counts are available.
- Never infer that `no_records` means ticks or pathogens are absent.
- Never require an API key for the public workbook path.
- Avoid bundling downloaded CDC workbooks or full CDC-derived exports in the repo until the data-use and redistribution terms are explicitly cleared.

The implementation should use a structured Excel reader such as `openpyxl`. If CDC changes workbook columns, the importer should fail with a clear error naming the missing columns.

## Risk Model

The MVP risk calculation is deliberately simple:

```text
risk_single_tick = theta_county * p_transmission(attachment_hours)
risk_k_ticks = 1 - (1 - risk_single_tick) ^ k
```

`p_transmission(tau)` uses a logistic curve with configurable constants:

```text
p(tau) = 1 / (1 + exp(-(gamma0 + gamma1 * tau)))
```

Default constants:

- `gamma0 = -7.0`
- `gamma1 = 0.10`

These defaults match the existing project spec and are the v0.1 calibrated constants until a validation notebook replaces them. The API response must make clear that this is an estimate, not medical advice.

Uncertainty intervals are computed by applying the same formula to `theta_lower` and `theta_upper`. This is simple and transparent; later Bayesian posterior draws can replace it without changing the API shape.

## API Contract

Endpoint:

```text
GET /risk
```

Query parameters:

- `fips`: required five-digit county FIPS code.
- `tau`: required attachment duration in hours, repeatable for multiple durations.
- `k`: optional integer number of attached ticks, default `1`.
- `tick_species`: optional, default `ixodes_scapularis`.
- `tick_stage`: optional, default `nymph`; accepted and echoed in v0.1, reserved for calibrated stage-specific behavior in a later model.
- `date`: optional ISO date, accepted but used only for metadata in v0.1.

Validation rules:

- `fips` must match a known bundled county record.
- `tau` must be between 0 and 168 hours.
- `k` must be at least 1.
- `tick_species` must be one of `ixodes_scapularis`, `ixodes_pacificus`, `unknown_ixodes`, or `non_ixodes`.
- `tick_stage` must be one of `nymph`, `adult`, or `unknown`.

Response fields:

- `fips`
- `state`
- `county`
- `tau`
- `k`
- `tick_species`
- `tick_stage`
- `risk`
- `ci95`
- `risk_category`
- `theta_mean`
- `theta_source`
- `data_quality`
- `source_updated`
- `model_version`
- `warnings`
- `clinical_disclaimer`

If `tick_species=non_ixodes`, return `0.0` Lyme risk with a warning that non-Ixodes ticks are not expected to transmit Lyme disease, while still reminding users to consult CDC or a clinician for other tickborne disease concerns.

## Risk Categories

Categories are intended for communication only and must not be treatment recommendations.

- `very_low`: risk below `0.001`.
- `low`: risk from `0.001` to below `0.01`.
- `moderate`: risk from `0.01` to below `0.03`.
- `higher`: risk `0.03` or above.

The thresholds are MVP defaults and should be documented as configurable.

## Error Handling

API errors should use FastAPI-style JSON responses:

- `400`: invalid query parameters.
- `404`: unknown FIPS code.
- `422`: schema validation errors emitted by FastAPI/Pydantic.
- `503`: bundled data cannot be loaded.

Importer errors should be explicit:

- Missing workbook file or failed URL fetch.
- Missing required worksheet or columns.
- Invalid FIPS values.
- Empty parsed result.

## Testing

Required tests:

- `p_transmission` is monotonic and bounded between 0 and 1.
- Per-bite risk increases with `theta`, `tau`, and `k`.
- Input validation rejects invalid FIPS, tau, k, tick species, and tick stage values.
- Sample data loads into normalized county records.
- API returns the documented fields for known sample counties.
- API returns 404 for unknown FIPS.
- `tick_species=non_ixodes` returns `0.0` Lyme risk plus warning metadata.
- CDC importer parses fixture workbooks that mimic the current public CDC structures.
- CDC importer fails clearly when required columns are missing.

Use local fixture workbooks for tests. Tests must not depend on live CDC network calls.

## Agent-Based Execution Plan

After this design is approved and an implementation plan is written, use agents for independent work streams:

- Package/API agent: create project packaging, FastAPI app, schemas, and endpoint routing.
- Risk/data agent: implement pure risk math, sample data loading, and validation helpers.
- Importer agent: implement CDC workbook parsing and fixture-based importer tests.
- Docs/tests agent: update README/dev docs and strengthen test coverage.

The main thread integrates changes, resolves overlaps, runs verification commands, and keeps the scope aligned with this design.

## Acceptance Criteria

- `pip install -e ".[dev]"` succeeds in a fresh local environment.
- `pytest` passes.
- `uvicorn tickbiterisk.api:app --reload` starts the API.
- `GET /risk?fips=24003&tau=24` returns a JSON risk estimate with uncertainty, source labels, warnings, and disclaimer.
- CDC importer can parse local fixture workbooks and emit normalized records.
- No full CDC workbook or full CDC-derived county export is committed.
- README clearly distinguishes implemented v0.1 behavior from future roadmap behavior.

## Open Data Notes

The current public CDC tick surveillance workbooks inspected during design include county FIPS rows for Ixodes status and pathogen status. They are status-oriented, not a clean public county prevalence table with `n_tested` and `n_positive` fields. The importer must therefore label records derived from those files as `status_imputed` unless a later source provides true prevalence counts.

The public CDC pages do not require an API key for browser access to the workbook pages. The MVP should not assume a stable CDC API. It should accept a local file or URL and keep network access out of tests.

## References

- CDC Tick Surveillance Data Sets: https://www.cdc.gov/ticks/data-research/facts-stats/tick-surveillance-data-sets.html
- CDC Tick Bite Data Tracker: https://www.cdc.gov/ticks/data-research/facts-stats/tick-bite-data-tracker.html
- Existing project buildability review: `review/2026-buildability-review.md`
- Existing API spec: `api/api-spec.md`
- Existing model spec: `docs/model-spec.md`
