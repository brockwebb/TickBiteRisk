# Research Lab Notes And Whitepaper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an internal chaptered research lab-notes dossier first, then derive a draft public technical whitepaper from it.

**Architecture:** Treat the lab notes as the source-of-truth synthesis layer and the whitepaper as a later extraction. Add a lightweight documentation test so required chapters, front matter, source references, and overclaim caveats stay visible as the dossier evolves. Use reviewer agents for methods/statistics and scientific/data-quality passes before creating the public whitepaper draft.

**Tech Stack:** Markdown documentation, Python pytest docs checks, existing repo docs/public JSON/modeling source files, multi-agent read-only review passes.

---

## File Structure

- Create: `tests/test_research_docs.py`  
  Validates the required research documentation files, chapter front matter, source-map references, and review-register overclaim entries.
- Create: `docs/research/lab-notes/README.md`  
  Entry point for the internal research dossier.
- Create: `docs/research/lab-notes/01-product-boundary.md`  
  Current product/research/medical boundary and current estimate vs non-estimates.
- Create: `docs/research/lab-notes/02-data-provenance.md`  
  Source families, raw-vs-derived rule, artifact vintages, provenance, and redistribution boundaries.
- Create: `docs/research/lab-notes/03-methods-modeling.md`  
  Annual forecast, model comparison, forecast-safe design, regional branches, and update policy.
- Create: `docs/research/lab-notes/04-plain-language-stats.md`  
  Definitions for per-100k, score, percentile, intervals, average/worse-than-average language, and chart marks.
- Create: `docs/research/lab-notes/05-validation-results.md`  
  Rolling-origin validation, branch comparison, failed update lanes, observed-fit overlays, and promotion gates.
- Create: `docs/research/lab-notes/06-regional-research.md`  
  Mid-Atlantic research scope, county-equivalents, spatial regimes, intervals, and public-default boundary.
- Create: `docs/research/lab-notes/07-limitations-review-register.md`  
  Known overclaim risks, stale/conflicting docs, HITL gates, reviewer findings, and follow-up decisions.
- Create: `docs/research/lab-notes/appendix-source-map.md`  
  Claims-to-sources map across docs, public artifacts, code modules, and tests.
- Create: `docs/research/whitepaper/README.md`  
  Draft public whitepaper entry point after lab-note reviewer passes.
- Create: `docs/research/whitepaper/01-executive-summary.md`
- Create: `docs/research/whitepaper/02-background-related-work.md`
- Create: `docs/research/whitepaper/03-data-and-provenance.md`
- Create: `docs/research/whitepaper/04-methods.md`
- Create: `docs/research/whitepaper/05-results-and-validation.md`
- Create: `docs/research/whitepaper/06-limitations-and-ethics.md`
- Create: `docs/research/whitepaper/07-reproducibility.md`
- Create: `docs/research/whitepaper/references.md`

## Task 1: Add Research Docs Guard Test

**Files:**
- Create: `tests/test_research_docs.py`

- [ ] **Step 1: Write the failing docs test**

Create `tests/test_research_docs.py` with:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAB_NOTES = ROOT / "docs" / "research" / "lab-notes"
WHITEPAPER = ROOT / "docs" / "research" / "whitepaper"

LAB_NOTE_FILES = [
    "README.md",
    "01-product-boundary.md",
    "02-data-provenance.md",
    "03-methods-modeling.md",
    "04-plain-language-stats.md",
    "05-validation-results.md",
    "06-regional-research.md",
    "07-limitations-review-register.md",
    "appendix-source-map.md",
]

WHITEPAPER_FILES = [
    "README.md",
    "01-executive-summary.md",
    "02-background-related-work.md",
    "03-data-and-provenance.md",
    "04-methods.md",
    "05-results-and-validation.md",
    "06-limitations-and-ethics.md",
    "07-reproducibility.md",
    "references.md",
]

REQUIRED_SOURCE_REFERENCES = [
    "README.md",
    "docs/model-spec.md",
    "docs/data-sources.md",
    "docs/data-manifest.md",
    "docs/public-product-boundary.md",
    "docs/regional-research-evidence.md",
    "public/data/model_card.json",
    "public/research-data/regional/model_card.json",
    "tickbiterisk/modeling/risk_score.py",
    "tickbiterisk/modeling/regional_forecast_typicality.py",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lab_note_chapters_exist_with_review_front_matter() -> None:
    for filename in LAB_NOTE_FILES:
        path = LAB_NOTES / filename
        assert path.exists(), f"Missing lab-note chapter: {path}"
        content = read(path)
        assert content.startswith("# "), f"{path} must start with a title"
        assert "Status:" in content, f"{path} must declare review status"
        assert "Primary sources:" in content, f"{path} must declare primary sources"
        assert "Reviewer focus:" in content, f"{path} must declare reviewer focus"
        assert "Last checked against commit:" in content, (
            f"{path} must record the source commit"
        )


def test_lab_notes_define_core_statistical_contracts() -> None:
    stats = read(LAB_NOTES / "04-plain-language-stats.md")
    required_terms = [
        "reported incidence per 100k",
        "Predicted score",
        "Forecast percentile",
        "Forecast interval",
        "not a probability",
        "not observed county-week truth",
        "not a medical confidence interval",
    ]
    for term in required_terms:
        assert term in stats


def test_review_register_tracks_overclaim_and_hitl_risks() -> None:
    register = read(LAB_NOTES / "07-limitations-review-register.md")
    required_terms = [
        "CITATION.cff",
        "Bayesian per-bite",
        "personal infection probability",
        "true Lyme burden",
        "medical advice",
        "HITL",
        "regional research branch",
    ]
    for term in required_terms:
        assert term in register


def test_source_map_references_backing_docs_code_and_artifacts() -> None:
    source_map = read(LAB_NOTES / "appendix-source-map.md")
    for reference in REQUIRED_SOURCE_REFERENCES:
        assert reference in source_map


def test_whitepaper_draft_exists_and_points_back_to_lab_notes() -> None:
    for filename in WHITEPAPER_FILES:
        path = WHITEPAPER / filename
        assert path.exists(), f"Missing whitepaper chapter: {path}"
        content = read(path)
        assert content.startswith("# "), f"{path} must start with a title"
        assert "docs/research/lab-notes" in content, (
            f"{path} must link back to the internal lab notes"
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: FAIL because `docs/research/lab-notes` and `docs/research/whitepaper`
do not exist yet.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/test_research_docs.py
git commit -m "test: require research documentation dossier"
```

## Task 2: Create Lab Notes Skeleton And Index

**Files:**
- Create: all `docs/research/lab-notes/*.md`

- [ ] **Step 1: Capture the current commit**

Run:

```bash
git rev-parse --short HEAD
```

Use that value in every `Last checked against commit:` line for this task.

- [ ] **Step 2: Create the lab-notes directory and chapter files**

Create each lab-note file listed in the File Structure section. Use this
front-matter pattern at the top of every file after the title:

```markdown
Status: draft
Primary sources: README.md; docs/model-spec.md
Reviewer focus: documentation inventory
Last checked against commit: the short commit printed by `git rev-parse --short HEAD`
```

Use the specific primary sources and reviewer focus from the approved spec for
each chapter. Use the actual short commit captured in Step 1.

- [ ] **Step 3: Draft `docs/research/lab-notes/README.md`**

The README must include:

```markdown
# TickBiteRisk Research Lab Notes

Status: draft
Primary sources: README.md; docs/model-spec.md; docs/data-sources.md; docs/regional-research-evidence.md
Reviewer focus: documentation inventory
Last checked against commit: the short commit printed by `git rev-parse --short HEAD`

These lab notes are the internal synthesis layer for TickBiteRisk research.
They organize the current product boundary, sources, methods, statistical
language, validation evidence, regional research findings, and known review
risks before any public whitepaper is promoted as release-ready.

The current TickBiteRisk product is a relative reported Lyme disease
pressure forecast and risk-context tool. It is not a diagnosis, treatment
recommendation, or calibrated personal infection probability.
```

Include a reading-order table linking all seven chapters and the source map.

- [ ] **Step 4: Run the docs test**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: FAIL only on content not yet drafted or the missing whitepaper draft.

## Task 3: Draft Product Boundary And Data Provenance Chapters

**Files:**
- Modify: `docs/research/lab-notes/01-product-boundary.md`
- Modify: `docs/research/lab-notes/02-data-provenance.md`

- [ ] **Step 1: Draft product boundary chapter**

Include these sections:

```markdown
## Current Product Boundary
## Public Maryland Surface
## Regional Research Surface
## Bite Guidance Overlay
## Medical And Public-Health Boundary
## What The Product Does Not Estimate
## Human Decisions Required Before Promotion
```

Required wording:

```markdown
TickBiteRisk currently forecasts relative reported Lyme disease pressure. It
does not estimate whether a specific person is infected, does not diagnose
disease, and does not recommend treatment.
```

- [ ] **Step 2: Draft data provenance chapter**

Include these sections:

```markdown
## Source Families
## Raw Files And Derived Public Artifacts
## Source Vintages And Forecast Origins
## Public Redistribution Boundary
## Provenance And Audit Trail
## Known Data Gaps
```

Required source families:

```markdown
- CDC and state Lyme surveillance
- Census population and geography
- CDC national Lyme onset seasonality
- Weather, drought, ecology, host, and exposure candidates
- Regional research sidecars and overlays
- Public model cards and source catalogs
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: still FAIL only on undrafted later chapters or the missing whitepaper
draft.

- [ ] **Step 4: Commit the first lab-note chapters**

```bash
git add docs/research/lab-notes tests/test_research_docs.py
git commit -m "docs: draft research lab notes boundary and provenance"
```

## Task 4: Draft Methods And Plain-Language Statistics Chapters

**Files:**
- Modify: `docs/research/lab-notes/03-methods-modeling.md`
- Modify: `docs/research/lab-notes/04-plain-language-stats.md`

- [ ] **Step 1: Draft methods-modeling chapter**

Include these sections:

```markdown
## Forecast Target
## Maryland Public Forecast Branches
## Regional Research Branches
## Forecast-Safe Rules
## Seasonal Allocation
## Score Construction
## Forecast Typicality
## Forecast Intervals
## Update Policy
## Research Lanes Not Promoted
```

Required claim:

```markdown
Observed county Lyme truth is annual in the current public data stack.
Weekly values are seasonal allocations of annual forecasts, not observed
county-week Lyme outcomes.
```

- [ ] **Step 2: Draft plain-language statistics chapter**

Define each term with a short technical definition and a plain-language
sentence:

```markdown
## Reported Incidence Per 100k
## Annual Forecast
## Weekly Seasonal Risk
## Predicted Score
## Forecast Percentile
## Forecast Interval
## Average, Worse Than Average, And Much Higher Than Typical
## Chart Marks And Bands
## Language To Avoid
```

Required language:

```markdown
The predicted score is not a probability. It is a relative 1-10 display score
derived from predicted weekly reported-incidence pressure and the selected
scale denominator.
```

```markdown
The forecast interval is not a medical confidence interval. It is an empirical
range from historical forecast errors around reported-incidence forecasts.
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: still FAIL only on undrafted later chapters or the missing whitepaper
draft.

- [ ] **Step 4: Commit methods and statistics chapters**

```bash
git add docs/research/lab-notes tests/test_research_docs.py
git commit -m "docs: draft research methods and statistics notes"
```

## Task 5: Draft Validation, Regional Research, And Review Register

**Files:**
- Modify: `docs/research/lab-notes/05-validation-results.md`
- Modify: `docs/research/lab-notes/06-regional-research.md`
- Modify: `docs/research/lab-notes/07-limitations-review-register.md`

- [ ] **Step 1: Draft validation chapter**

Include:

```markdown
## Rolling-Origin Validation
## Branch Comparison Metrics
## Maryland Public Branch Evidence
## Regional Research Diagnostics
## Forecast Calibration Backtest
## Gamma-Poisson Bayesian Update Backtest
## Observed-Fit Overlays
## Promotion Gates
```

Record that calibration and Bayesian update backtests are research-only unless
rolling-origin gates improve error or calibration.

- [ ] **Step 2: Draft regional research chapter**

Include:

```markdown
## Scope
## County-Equivalent Geography
## Cross-Border Adjacency
## Localized Spatial Regimes
## Regional Annual Forecasts
## Regional Forecast Intervals
## Research-Only Boundary
```

Required language:

```markdown
The regional research page is not the Maryland public default. It is a
research surface for inspecting Mid-Atlantic reported-incidence forecast
methods, intervals, and localized spatial-regime context.
```

- [ ] **Step 3: Draft review register**

Include these entries:

```markdown
## Highest-Risk Overclaims
## Stale Or Conflicting Documentation
## Source And Citation Gaps
## Human-In-The-Loop Gates
## Reviewer Findings
## Follow-Up Decisions
```

Required entries:

```markdown
- `CITATION.cff` appears to overclaim Bayesian per-bite Lyme risk and national
  personal-risk coverage compared with the current relative reported-incidence
  forecast boundary.
- Do not claim personal infection probability, true Lyme burden, medical
  advice, diagnosis, or treatment recommendation.
- Do not promote a regional research branch as public default without HITL
  approval.
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: still FAIL only on missing source-map references or missing
whitepaper draft.

- [ ] **Step 5: Commit validation and review chapters**

```bash
git add docs/research/lab-notes tests/test_research_docs.py
git commit -m "docs: draft validation and review lab notes"
```

## Task 6: Build Source Map And Run Reviewer Passes

**Files:**
- Modify: `docs/research/lab-notes/appendix-source-map.md`
- Modify: lab-note chapters as needed from reviewer findings

- [ ] **Step 1: Draft source map**

For each claim family, include the claim, primary docs, public artifacts, code,
and tests. Required claim families:

```markdown
## Product Boundary
## Data Provenance
## Annual Forecast Methods
## Seasonal Allocation
## Score Scale
## Forecast Percentile And Typicality
## Forecast Intervals
## Validation And Backtests
## Regional Research
## Medical And Risk-Communication Boundary
```

- [ ] **Step 2: Dispatch reviewer agents**

Spawn three read-only reviewer agents:

```text
Reviewer 1: documentation inventory. Review docs/research/lab-notes for source
coverage, stale conflicts, and missing source references. Do not edit files.
Return exact findings by chapter.

Reviewer 2: methods/statistics. Review score, percentile, interval, validation,
and forecast-safe wording in docs/research/lab-notes. Do not edit files.
Return exact findings by chapter.

Reviewer 3: scientific/data-quality. Review surveillance caveats, medical
boundary, overclaim risks, and public-default claims. Do not edit files.
Return exact findings by chapter.
```

- [ ] **Step 3: Integrate reviewer findings**

Add findings and resolutions to `07-limitations-review-register.md`. Fix
chapter wording where reviewers identify contradictions, missing caveats, or
unsupported claims.

- [ ] **Step 4: Run focused tests and risky-phrase scan**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
rg -n "true incidence|infection probability|diagnosis|treatment recommendation|confidence interval" docs/research/lab-notes
```

Expected: pytest still FAILS only because the public whitepaper draft has not
been created. The `rg` output is acceptable only when the term appears inside a
caveat or "not ..." statement.

- [ ] **Step 5: Commit reviewed lab notes**

```bash
git add docs/research/lab-notes tests/test_research_docs.py
git commit -m "docs: review research lab notes"
```

## Task 7: Create Draft Public Technical Whitepaper

**Files:**
- Create: all `docs/research/whitepaper/*.md`

- [ ] **Step 1: Create whitepaper chapter files**

Use lab notes as the source and include a link back to
`docs/research/lab-notes` in every file. Each whitepaper file must state:

```markdown
Draft status: working draft derived from internal lab notes; not release-ready.
```

- [ ] **Step 2: Draft whitepaper README**

Include:

```markdown
# TickBiteRisk Technical Whitepaper

Draft status: working draft derived from internal lab notes; not release-ready.

TickBiteRisk is an open-source Lyme risk forecasting research product. The
current implementation estimates relative reported Lyme disease pressure from
county-year surveillance history, population denominators, CDC national Lyme
onset seasonality, and documented model branches. It is informational only and
does not diagnose disease, estimate personal infection probability, or
recommend treatment.

Internal evidence record: docs/research/lab-notes
```

- [ ] **Step 3: Draft seven concise chapters**

Keep the whitepaper concise. Each chapter should summarize the corresponding
lab-note evidence and link back to the lab-note chapter. Do not claim the
whitepaper is release-ready.

- [ ] **Step 4: Draft references status**

In `references.md`, record:

```markdown
The prior literature review references `paper/refs.bib`, but that file is not
present in the current repository. Formal bibliography reconstruction remains
needed before a publication-ready whitepaper.
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: PASS.

- [ ] **Step 6: Commit whitepaper draft**

```bash
git add docs/research/whitepaper tests/test_research_docs.py
git commit -m "docs: draft technical whitepaper skeleton"
```

## Task 8: Final Verification And Push

**Files:**
- Verify all documentation and test files changed in this plan.

- [ ] **Step 1: Run focused docs test**

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_research_docs.py
```

Expected: PASS.

- [ ] **Step 2: Run standard repository verification**

```bash
env PYTHONPATH=. ./.venv/bin/python -m pytest -q $(git ls-files 'tests/test*.py')
PYTHONPATH=. ./.venv/bin/python -m ruff check .
node --check public/app.js && node --check public/regional-research.js && git diff --check
```

Expected: all pass.

- [ ] **Step 3: Confirm no deliberate untracked local files were staged**

```bash
git status --short
git diff --cached --name-only
```

Expected: staged files are only the new research docs and `tests/test_research_docs.py`.

- [ ] **Step 4: Push branch**

```bash
git push origin codex/mast-acorn-modeling-layer
```

Expected: push succeeds.

## Self-Review

Spec coverage:

- Lab notes first: Tasks 1-6 create and review the internal dossier before the
  whitepaper draft.
- Public whitepaper second: Task 7 derives the draft from the lab notes and
  labels it not release-ready.
- Plain-language statistics: Task 4 requires definitions for score,
  percentile, intervals, per-100k, and chart language.
- Reviewer workflow: Task 6 dispatches documentation, methods/statistics, and
  scientific/data-quality reviewers and records findings.
- HITL gates: Task 5 records gates, and no task promotes regional branches,
  changes medical guidance, deletes local duplicates, or publishes the
  whitepaper as release-ready.

Plan completeness scan:

- The plan contains no `TODO`, `TBD`, or "fill in" instructions.
- The only runtime-specific value is the short commit captured during
  implementation, and the plan explicitly tells the implementer how to compute
  and use it.

Type and path consistency:

- All planned files live under `docs/research/lab-notes`,
  `docs/research/whitepaper`, or `tests/test_research_docs.py`.
- Test constants match the planned filenames.
