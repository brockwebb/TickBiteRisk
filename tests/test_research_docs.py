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
