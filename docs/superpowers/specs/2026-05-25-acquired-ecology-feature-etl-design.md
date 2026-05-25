# Acquired Ecology Feature ETL Design

Date: 2026-05-25  
Status: Approved design, pre-implementation  
Scope: Maryland contact-pressure and mast/acorn feature ETL from already acquired source data

## Purpose

This slice converts acquired ecology/contact source data into model-ready or near-model-ready CSV features. The immediate goal is to turn data we already have into reproducible covariates without waiting for heavier GIS/raster work.

The slice covers two practical outputs:

1. County-year construction/contact-pressure features derived from Census Building Permits Survey output.
2. A cautious Maryland DNR mast/acorn extraction scaffold for the acquired 2017, 2020, and 2021 Western Maryland mast survey PDFs.

Annual NLCD/MRLC and USDA CDL remain catalogued source families, but this slice does not process raster land-cover products. Those require a later GIS/service decision.

## Design Decision

Use a CSV-first feature layer before adding warehouse tables. The repository already follows this pattern for weather, population, deer harvest, and building permits. CSV-first keeps the extraction testable, reviewable, and easy to compare before deciding the final SQL table shape.

True OCR is allowed if needed, but it is not the default path. The first mast implementation should use the existing PDF pattern:

- `pypdfium2` for lightweight text extraction.
- Docling as an optional parser/converter path.
- Injected extractor/converter functions in tests so test runs do not depend on live OCR tooling.
- Quality flags when text extraction is incomplete, regional, inferred, or parser-dependent.

If the acquired mast PDFs are image-based or fail table extraction, the implementation should catalog the failure and mark the rows or source as OCR-pending rather than silently producing low-confidence numeric features.

## Data Inputs

### Census Building Permits

Input file:

```text
build/etl/building-permits/maryland_building_permits_county_year.csv
```

Current observed coverage:

- 435 deduped Maryland county-year rows.
- Years 2000-2025.
- 2022-2025 have all 24 Maryland jurisdictions.
- 2000-2004 have 16 jurisdictions.
- 2005-2014 have 14 jurisdictions.
- 2015-2021 have 17 jurisdictions.

This data is already normalized but not yet converted into denominator-adjusted contact-pressure features.

### County Reference

Input file:

```text
build/etl/county-reference/county_reference.csv
```

Used for:

- `land_area_sqmi`
- county FIPS/name validation
- units authorized per square mile

### Population Denominators

Input file:

```text
build/etl/census-population/county_population_year.csv
```

Used for:

- units authorized per 100,000 population

If a BPS year has no matching population denominator, the row should still be emitted with a null population-normalized feature and a quality flag.

### Maryland DNR Mast Reports

Input files:

```text
data/raw/ecology/mast/maryland_dnr_wmd_mast_survey_2017.pdf
data/raw/ecology/mast/maryland_dnr_wmd_mast_survey_2020.pdf
data/raw/ecology/mast/maryland_dnr_wmd_mast_survey_2021.pdf
```

These are localized Western Maryland mast/acorn reports. They must not be generalized statewide without explicit quality flags.

### Manual Or Local Mast Observations

Official mast/acorn data may be regional, sparse, or unavailable for central Maryland counties. The ETL design should allow a local manual-observation input as a separate staging lane, not as an official data substitute.

Example observation to preserve outside committed source data:

```text
county_fips=24003
county_name=Anne Arundel County
year=2025
mast_rating=bumper
observation_basis=local resident observation of unusually heavy acorn fall
feature_quality_flags=manual_observation,anecdotal,not_official,not_model_default
```

Manual observations can inform product notes, exploratory priors, or future validation prompts. They must not be mixed with Maryland DNR survey rows or used as calibrated model inputs unless a later review process validates them against official or repeatable sources.

## Output 1: Contact Pressure Features

Output file:

```text
build/etl/contact-pressure/contact_pressure_features_county_year.csv
```

Columns:

```text
county_fips
county_name
year
residential_units_authorized
units_authorized_per_sqmi
units_authorized_per_100k
total_value_dollars
land_area_sqmi
population
source_id
source_url_hash
feature_quality_flags
```

Natural key:

```text
county_fips, year
```

Feature rules:

- `residential_units_authorized` equals BPS `total_units_authorized`.
- `units_authorized_per_sqmi = residential_units_authorized / land_area_sqmi`.
- `units_authorized_per_100k = residential_units_authorized / population * 100000`.
- `feature_quality_flags` is comma-separated and empty when no flags apply.

Required quality flags:

- `missing_population` when no denominator exists for that county/year.
- `missing_land_area` when no land-area denominator exists.
- `historical_partial_jurisdiction_coverage` for BPS years with fewer than 24 Maryland jurisdictions.
- `construction_proxy_only` on every row, because this is a contact/land-use proxy rather than direct evidence of tick, deer, or pathogen movement.

## Output 2: Mast/Acorn Normalized Rows

Output file:

```text
build/etl/mast/maryland_dnr_mast_acorn_county_year.csv
```

Columns:

```text
county_fips
county_name
year
region
mast_category
mast_index
mast_rating
acorn_index
hard_mast_index
soft_mast_index
plots_observed
expected_plots
coverage_complete
source_id
source_url_hash
feature_quality_flags
extracted_text_excerpt
```

Natural key:

```text
county_fips, year, mast_category, source_id
```

Accepted first-pass behavior:

- Emit structured rows only when the report text supports the values.
- Do not invent county assignments if the report only supports a regional value.
- Use nulls for unavailable numeric measures rather than placeholders.

Required quality flags:

- `western_maryland_only` for mast rows sourced from WMD reports.
- `regional_context_only` when no defensible county assignment exists.
- `county_assignment_inferred` when county mapping is derived from report locations rather than explicit county fields.
- `parser_low_confidence` when extraction requires fuzzy text matching.
- `ocr_pending` when pypdfium/Docling text extraction cannot support structured values.

## Output 3: Mast/Acorn Extraction Summary

Output file:

```text
build/etl/mast/maryland_dnr_mast_acorn_extraction_summary.csv
```

Columns:

```text
source_id
source_url_hash
year
parser
source_path
extraction_status
structured_row_count
feature_quality_flags
notes
extracted_text_excerpt
```

Natural key:

```text
source_id, parser
```

The summary file is required for every mast/acorn run. It records whether each PDF produced structured rows, no supported table values, parser failure, or OCR-pending status. This keeps failed or low-confidence document extraction visible without fabricating county-year feature rows.

## Optional Output 4: Manual Mast Observations

Output file:

```text
build/etl/mast/manual_mast_observations_county_year.csv
```

Columns:

```text
county_fips
county_name
year
mast_rating
observation_basis
observer_scope
source_id
feature_quality_flags
notes
```

Natural key:

```text
county_fips, year, source_id
```

This output is optional and should be generated only when a local manual-observation input file is provided. It exists to preserve potentially useful field observations without laundering them into official ecology data. Every row must carry `manual_observation`, `anecdotal`, `not_official`, and `not_model_default` unless a future validation process defines stronger evidence levels.

## CLI Design

Add two ETL commands:

```bash
tickbiterisk etl contact-pressure --output-dir build/etl/contact-pressure
tickbiterisk etl mast-acorn --raw-dir data/raw/ecology/mast --output-dir build/etl/mast
```

`contact-pressure` should accept optional paths for BPS, county reference, and population inputs so tests and future workflows can point at fixtures.

`mast-acorn` should accept a parser option:

```text
--parser pypdfium
--parser docling
```

The default is `pypdfium`. Docling remains an optional heavier parser path. A future `--parser ocr` option can be added only after a specific OCR dependency and validation workflow are selected.

## Error Handling

Contact-pressure ETL should fail clearly when required input CSVs are missing or malformed.

Mast/acorn ETL should distinguish:

- source file missing
- parser unavailable
- text extracted but no supported table values found
- parser failed entirely

Parser failures should not produce silently fabricated rows. If a source cannot be structured, the command should write an extraction-summary row with `extraction_status` and quality flags such as `ocr_pending` or `parser_low_confidence`, then continue to the next source. The command should fail only for missing required input paths, unsupported parser names, or an inability to write outputs.

## Testing Strategy

Contact-pressure tests should cover:

- per-square-mile calculation
- per-100k calculation
- missing population flag
- partial historical coverage flag
- stable sort and append/dedupe behavior
- CLI invocation with fixture input paths

Mast/acorn tests should cover:

- parsing a small text fixture into structured mast rows
- pypdfium extraction through an injected extractor
- Docling extraction through an injected converter
- no-table/low-confidence behavior
- extraction summary output for every source
- quality flags for Western Maryland/regional-only rows
- optional manual-observation input with noncanonical quality flags
- CLI invocation without requiring real OCR

## Documentation Updates

Update these docs in the implementation slice:

- `README.md` command list.
- `docs/data-manifest.md` source/status rows.
- `docs/etl-pipeline.md` feed sections.
- `docs/software-requirements-spec.md` only if accepted scope changes.

Docs must say plainly that:

- Construction pressure is a proxy, not a causal claim.
- Mast/acorn data is localized and sparse.
- Manual mast observations are anecdotal and excluded from calibrated model inputs by default.
- NLCD/CDL raster feature extraction remains pending.
- OCR may be used later, but low-confidence OCR values should not enter model features without review.

## Non-Goals

- No risk-score or model-fitting changes.
- No Postgres load in this slice unless a later implementation plan explicitly adds schema.
- No NLCD/CDL raster processing.
- No county adjacency/spillover modeling.
- No forced OCR of scanned or low-quality PDFs into numeric features.
- No promotion of anecdotal mast observations into calibrated model features.
- No redistribution of raw acquired source files through git.

## Acceptance Criteria

The implementation is complete when:

- Contact-pressure feature CSV is generated from existing BPS, county reference, and population outputs.
- Contact-pressure rows carry denominator-derived features and quality flags.
- Mast/acorn parser scaffolding exists and writes defensible structured rows when supported plus extraction-summary rows for every source.
- CLI commands exist and are tested.
- Docs and manifest reflect outputs and remaining caveats.
- Full test suite and lint pass.
