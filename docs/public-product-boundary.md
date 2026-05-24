# Public Product Boundary

Date: 2026-05-24

## Intent

TickBiteRisk is intended to be a free, open-source public information tool. The public product should help people understand relative tickborne disease risk and follow public-health guidance after a tick exposure.

It is not a diagnostic tool, clinical decision system, treatment recommendation engine, or substitute for professional medical care.

## Plain-Language Disclaimer

Use language close to this in public UI and generated reports:

```text
TickBiteRisk is for informational and educational purposes only. It does not diagnose disease, determine whether you are infected, or replace advice from a healthcare professional. Follow CDC guidance for tick removal, symptom monitoring, and prevention. If you have symptoms, are concerned about a tick bite, or have questions about treatment, contact a qualified healthcare professional.
```

Short UI variant:

```text
Informational only. Not medical advice. Follow CDC guidance and contact a healthcare professional about your situation.
```

## Data Publication Rule

The private warehouse may store raw files, normalized source tables, and restricted or terms-unclear source extracts. The public web product should publish only derived data products unless a source is clearly redistributable.

Allowed public artifacts:

- Derived risk scores.
- Aggregated county/month or county/week feature summaries.
- Model metadata and source citations.
- Data quality labels.
- Methodology notes.

Avoid publishing without a source-specific review:

- Raw downloaded spreadsheets, PDFs, or CSVs.
- Full restricted CDC vector/pathogen workbooks.
- Rows that reproduce source tables under unclear redistribution terms.
- Local credentials, database dumps, or private ETL outputs.

## Runtime Data Shape

For a static public web product, prefer compact derived files:

```text
public/data/md_county_risk_monthly.json
public/data/md_county_metadata.json
public/data/model_card.json
public/data/source_catalog.json
```

The public runtime should not need database credentials or raw data files.

## Guidance Links

Public outputs should link to authoritative guidance:

- CDC: What to do after a tick bite: `https://www.cdc.gov/ticks/after-a-tick-bite/index.html`
- CDC: Preventing tick bites: `https://www.cdc.gov/ticks/prevention/index.html`
- CDC: Lyme disease signs and symptoms: `https://www.cdc.gov/lyme/signs-symptoms/index.html`
- CDC: Clinician guidance after tick bite: `https://www.cdc.gov/lyme/media/pdfs/Caring-for-Patients-after-a-Tick-Bite.pdf`
