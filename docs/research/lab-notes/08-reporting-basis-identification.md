# Reporting-Basis Identification Decision

Status: draft
Primary sources: docs/surveillance-regime-bridge-spec.md; docs/research/source-materials/did-control-verification-2017-2019.csv; CDC dataset qtbi-xd4i
Reviewer focus: identification gate and adjustment provenance
Last checked against commit: working tree 2026-05-31

## Decision

CDC anchor stands.

The out-of-region DiD path was evaluated against the CDC county-FIPS Lyme public
use panel and is empirically foreclosed for this release. This is not an
unattempted control search. It is a negative identification result.

The reporting-basis run metadata must therefore carry:

- `did_control_evaluated=true`
- `did_control_passed=false`
- `did_control_failure_reason=insufficient_unsuppressed_county_panel_2017_2019`

The retained source-material artifact is
`docs/research/source-materials/did-control-verification-2017-2019.csv`.

## Evidence

The CDC dataset `qtbi-xd4i` covers 2008-2021 county-FIPS annual Lyme data with
confirmed/probable split fields. Across the full 2017-2019 pre-window, the
candidate low-incidence states do not provide enough unsuppressed annual
county-FIPS rows to estimate a parallel-trends control panel:

| State | Distinct resolved county FIPS across 2017-2019 |
| --- | ---: |
| GA | 0 |
| MO | 0 |
| CO | 0 |
| KS | 1 |
| NE | 1 |
| UT | 1 |
| KY | 1 |
| TN | 2 |
| SC | 3 |
| AL | 3 |

The best candidates resolve only three counties over three years. That is not a
usable annual control panel for a state-level reporting-basis DiD. The two
states with the most tempting resolved cells also fail substantive validity:
Kentucky is confounded by documented Appalachian Ixodes expansion, and Utah
includes travel-acquired Lyme cases. The multi-year aggregate XLSX products are
presence/absence maps rather than annual panels, so they cannot feed a
parallel-trends test either.

## Gate Consequence

The adjustment is anchor-identified by `cdc_published_anchor`. The 72.9% CDC
high-incidence level shift is a national fixed-prior scalar. Therefore, step 6
is unblocked by the CDC fixed-prior anchor because the gate explicitly permits
the CDC anchor when no valid out-of-region DiD control exists.

ITS remains diagnostic-only. No `interrupted_time_series` row may drive a public
adjustment number.

## Discussion Risk

The anchor is weaker than a local DiD would have been. It has no
jurisdiction-specific variance and no parallel-trends evidence. If the step 6
raw-vs-adjusted ranking is sensitive to the adjustment magnitude, this is the
weakest joint in the chain and the discussion must say so plainly.
