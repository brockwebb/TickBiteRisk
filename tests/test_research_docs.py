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


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


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


def test_whitepaper_references_are_working_project_register() -> None:
    references = read(WHITEPAPER / "references.md")
    normalized_references = " ".join(references.split())
    required_phrases = [
        "Formal bibliography status",
        "not publication-ready",
        "does not claim a complete literature review",
        "`paper/refs.bib`",
        "Project evidence record",
        "docs/research/lab-notes/appendix-source-map.md",
        "docs/data-sources.md",
        "docs/data-manifest.md",
        "docs/public-product-boundary.md",
        "docs/model-spec.md",
        "docs/regional-research-evidence.md",
        "public/data/model_card.json",
        "public/research-data/regional/model_card.json",
        "Official public-health and surveillance sources",
        "Population, geography, and environmental sources",
        "State and regional source leads",
        "Method and validation source needs",
        "CDC Lyme public-use aggregated geography files and CDC Lyme dashboard "
        "exports that provide county/state/region reported Lyme surveillance "
        "counts and rates",
        "CDC national Lyme onset seasonality source material, represented "
        "locally by `cdc_lyme_seasonality`, used to allocate annual forecasts "
        "into MMWR-week display rows",
        "CDC tick guidance for post-bite action, prevention, symptoms, and "
        "clinician prophylaxis-consideration context",
        "Maryland Department of Health Lyme disease data, currently used for "
        "the 2024 Maryland outcome lane with explicit `mdh_probable_only_2024` "
        "and `state_source_not_cdc_public_use` caveats",
        "Census population estimates, Census county reference files, and "
        "Census TIGERweb county geometry used for population denominators, "
        "county metadata, boundary support, and regional adjacency",
        "NOAA daily weather, NOAA CPC ONI, NOAA PSL MEI.v2, Open-Meteo recent "
        "backfill, and U.S. Drought Monitor artifacts, all treated as weather "
        "or climate context candidates unless a branch is explicitly promoted",
        "Sources for rolling-origin validation and leakage control for "
        "county-year forecasts",
        "Plain-language explanation of empirical Bayes methods, especially "
        "when a county forecast is partially pulled toward a broader prior",
        "Forecast interval construction from historical residuals, with "
        "language that distinguishes a forecast interval from a medical "
        "confidence interval or per-bite infection probability",
        "publication-facing citations still need human review",
    ]
    for phrase in required_phrases:
        assert " ".join(phrase.split()) in normalized_references


def test_whitepaper_methods_explain_forecast_score_and_update_contracts() -> None:
    methods = read(WHITEPAPER / "04-methods.md")
    normalized_methods = " ".join(methods.split())
    required_phrases = [
        "docs/research/lab-notes",
        "county-year reported Lyme incidence per 100,000 people",
        "surveillance-derived proxy for relative Lyme disease pressure",
        "linear_blend_baseline",
        "selected for transparency, stability, and plain-language defensibility",
        "empirical_bayes_spatial_regime_incidence",
        "not the public Maryland default",
        "Forecast-safe means a target-year forecast can use only information "
        "available at or before the forecast origin",
        "same-year diagnostic fields cannot be promoted into forecast inputs",
        "CDC national Lyme onset seasonality shares for MMWR weeks",
        "not county-specific",
        "not observed county-week Lyme cases",
        "nearest-rank benchmark quantile",
        "default benchmark quantile is `0.95`",
        "headroom multiplier is `1.2`",
        "rounded raw score clamped to `1..10`",
        "not a probability, infection chance, clinical threshold, or treatment "
        "trigger",
        "Forecast typicality compares the selected annual forecast with the "
        "same county's prior reported annual incidence",
        "Forecast intervals are empirical ranges from historical forecast "
        "residuals",
        "Maryland public model card lists interval method `not_available`",
        "regional research artifact includes intervals using "
        "`empirical_rolling_origin_residual_quantile`",
        "New surveillance, denominator, ecology, exposure, or regional evidence "
        "is not allowed to automatically move the public score",
        "default calibration and Bayesian update backtests worsened overall MAE",
        "Promotion requires improved held-out behavior, forecast-safe inputs, "
        "stable uncertainty language, and public-health wording",
    ]
    for phrase in required_phrases:
        assert " ".join(phrase.split()) in normalized_methods


def test_whitepaper_results_document_validation_gates_and_current_findings() -> None:
    results = read(WHITEPAPER / "05-results-and-validation.md")
    source_notes = read(LAB_NOTES / "05-validation-results.md")
    normalized_results = normalize_whitespace(results)
    normalized_source = normalize_whitespace(source_notes)

    for heading in [
        "## Rolling-Origin Validation",
        "## Branch Comparison Interpretation",
        "## Forecast Calibration Backtest",
        "## Gamma-Poisson Bayesian Update Backtest",
        "## Regional Research Diagnostics",
        "## Observed-Fit Overlay",
        "## Promotion Gates",
    ]:
        assert heading in results

    required_boundary_terms = [
        "docs/research/lab-notes",
        "rolling-origin",
        "not independently observed county-week truth",
        "reported-incidence forecast diagnostics",
        "`do_not_apply_to_public_forecast`",
        "research-only",
        "`partial_state_overlay`",
        "`not_training_feature`",
        "`not_public_default`",
        "`reported_cases_not_stable_true_incidence`",
        "`not_public_maryland_default`",
        "not be applied to the public forecast when overall performance worsens",
        "rather than public Maryland forecast changes",
    ]
    for term in required_boundary_terms:
        assert normalize_whitespace(term) in normalized_results

    for term in [
        "12 overall rows and 276 diagnostic subgroup rows",
        "predicted cases: 9,415.098301",
        "observed cases: 16,620",
        "case MAE: 123.037986",
        "incidence MAE: 84.387219 per 100k",
        "48 under-predictions and 19 over-predictions",
    ]:
        assert normalize_whitespace(term) in normalized_source
        assert normalize_whitespace(term) in normalized_results

    for row_key in [
        "linear_blend_baseline",
        "forecast_safe_top4_ensemble",
        "prior_year_incidence",
    ]:
        source_rows = [
            line.strip()
            for line in source_notes.splitlines()
            if line.strip().startswith(f"| `{row_key}` |")
        ]
        result_rows = [
            line.strip()
            for line in results.splitlines()
            if line.strip().startswith(f"| `{row_key}` |")
        ]
        assert len(source_rows) == 2
        assert result_rows == source_rows


def test_whitepaper_data_provenance_preserves_source_and_publication_boundaries() -> None:
    chapter = read(WHITEPAPER / "03-data-and-provenance.md")
    source_notes = read(LAB_NOTES / "02-data-provenance.md")
    normalized_chapter = normalize_whitespace(chapter)
    normalized_source = normalize_whitespace(source_notes)

    for heading in [
        "## Source Families",
        "## Raw Files And Derived Public Artifacts",
        "## Source Vintages And Forecast Origins",
        "## Public Redistribution Boundary",
        "## Provenance And Audit Trail",
        "## Known Data Gaps",
    ]:
        assert heading in chapter

    for term in [
        "CDC and state Lyme surveillance",
        "Census population and geography",
        "CDC national Lyme onset seasonality",
        "Weather, drought, ecology, host, and exposure sources are candidate "
        "features or diagnostics unless a reviewed public branch explicitly "
        "selects them",
        "`public/data`",
        "`public/research-data/regional`",
        "Neither public surface should require raw data files, database "
        "credentials, local secrets, or private ETL outputs",
        "`forecast_origin_year`",
        "`as_of_date`",
        "`data_cutoff_date`",
        "`source_vintage`",
        "`update_mode`",
        "Forecast rows should not contain or imply target-year actuals, "
        "residuals, errors, or observed weekly truth",
        "The redistribution boundary is derived-first",
        "Raw surveillance rows, restricted tick-status workbooks, ambiguous "
        "branch outputs, and deliberately untracked local files remain outside "
        "the public release boundary",
        "`acquisition_provenance.csv`",
        "`tickbiterisk etl provenance-audit --root-dir build/etl`",
        "request URLs that include credentials must be sanitized",
    ]:
        assert normalize_whitespace(term) in normalized_source
        assert normalize_whitespace(term) in normalized_chapter

    for source_gap in [
        "NSSP tick-bite data are absent from the current model",
        "Observed county-week and county-month Lyme truth are absent",
        "Ecology extraction remains uneven",
        "Official future population denominators are not yet available",
        "Regional sidecars and state overlays have different geographies",
        "Bibliography and source URL cleanup is still needed",
    ]:
        assert source_gap in source_notes
        assert source_gap in chapter
