from pathlib import Path


README = Path("README.md")
API_SPEC = Path("api/api-spec.md")
ARCHITECTURE = Path("docs/architecture.md")
RUNBOOK = Path("docs/operational-runbook.md")
USER_GUIDE = Path("docs/user-guide.md")
ROADMAP = Path("docs/roadmap.md")
VISION_SCOPE = Path("docs/vision-scope.md")
MODEL_SPEC = Path("docs/model-spec.md")
DATA_SOURCES = Path("docs/data-sources.md")
TESTING_CI_PLAN = Path("docs/testing-ci-plan.md")
ETL_PIPELINE = Path("docs/etl-pipeline.md")
MODEL_BACKGROUND = Path("docs/model-background.md")
SRS = Path("docs/software-requirements-spec.md")


def test_user_guide_matches_implemented_maryland_baseline_product() -> None:
    guide = USER_GUIDE.read_text(encoding="utf-8")

    for token in [
        "relative county-week seasonal Lyme baseline",
        "single-bite Lyme decision-support score",
        "not an absolute infection probability",
        "CDC MMWR week",
        "tickbiterisk risk lookup",
        "tickbiterisk risk single-bite",
        "tickbiterisk risk export-static",
        "Informational and educational only",
        "Follow CDC guidance",
    ]:
        assert token in guide


def test_user_guide_does_not_present_roadmap_api_as_live_medical_guidance() -> None:
    guide = USER_GUIDE.read_text(encoding="utf-8")

    forbidden_tokens = [
        "Posterior mean probability the bite transmits Lyme disease",
        "most physicians consider single-dose doxycycline prophylaxis reasonable",
        "Dashboard users simply pick county and drag the",
        "https://api.tickbiterisk.org/risk",
    ]
    for token in forbidden_tokens:
        assert token not in guide


def test_api_spec_documents_current_cli_json_contract_before_roadmap_http_api() -> None:
    spec = API_SPEC.read_text(encoding="utf-8")

    for token in [
        "Current implemented local contract",
        "tickbiterisk risk lookup",
        "Current Single-Bite Runtime",
        "tickbiterisk risk single-bite",
        "single_bite_risk_score",
        "pep_consideration",
        "county_fips",
        "query_date",
        "mmwr_year",
        "mmwr_week",
        "risk_score",
        "model_family",
        "feature_set",
        "evaluation_mode",
        "weather_mode",
        "source_metadata",
        "not an absolute infection probability",
        "Roadmap HTTP API",
    ]:
        assert token in spec


def test_api_spec_has_ordered_unique_current_runtime_sections() -> None:
    spec = API_SPEC.read_text(encoding="utf-8")

    assert spec.count("Current Static Runtime") == 1
    assert spec.count("Current Single-Bite Runtime") == 1
    _assert_in_order = [
        "## 2. Current Local Runtime",
        "## 3. Current Single-Bite Runtime",
        "## 4. Current Static Runtime",
        "## 5. Roadmap HTTP API",
    ]
    position = -1
    for token in _assert_in_order:
        next_position = spec.find(token, position + 1)
        assert next_position > position, token
        position = next_position


def test_readme_quick_start_leads_with_implemented_cli_not_unwired_http_api() -> None:
    readme = README.read_text(encoding="utf-8")
    quick_start = readme.split("## data sources", maxsplit=1)[0]

    assert "## quick start (current cli)" in quick_start
    assert "## quick start (static dashboard)" in quick_start
    assert "tickbiterisk risk lookup" in quick_start
    assert "tickbiterisk risk single-bite" in quick_start
    assert "tickbiterisk risk export-static" in quick_start
    assert "python -m http.server 8000 --directory public" in quick_start
    assert "quick start (docker)" not in quick_start
    assert "docker compose up -d" not in quick_start
    assert "curl 'http://localhost:8000/risk" not in quick_start


def test_readme_data_sources_match_current_catalog_not_old_source_wishlist() -> None:
    readme = README.read_text(encoding="utf-8")
    data_sources = readme.split("## data sources", maxsplit=1)[1].split(
        "## maryland ETL", maxsplit=1
    )[0]

    for token in [
        "CDC Lyme public-use geography",
        "CDC Lyme seasonality",
        "NOAA GHCND daily observations",
        "Maryland DNR deer harvest",
        "Census population and geography",
    ]:
        assert token in data_sources

    for token in [
        "FARS deer collisions",
        "NSSP ED tick",
        "CAPC dog serology",
    ]:
        assert token not in data_sources


def test_operational_runbook_documents_static_pages_v0_not_live_api_stack() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")

    for token in [
        "V0 static dashboard",
        "GitHub Pages",
        "public/data",
        ".github/workflows/pages.yml",
        "no runtime secrets",
        "tickbiterisk risk export-static",
        "python -m http.server",
        "attached tick calculator",
        "CDC criteria breakdown",
    ]:
        assert token in runbook

    forbidden_tokens = [
        "FastAPI",
        "PagerDuty",
        "Prometheus",
        "pg_restore",
        "posterior NetCDF",
        "GET /risk?fips=24003&tau=24",
    ]
    for token in forbidden_tokens:
        assert token not in runbook


def test_architecture_doc_leads_with_static_first_v0_pipeline() -> None:
    architecture = ARCHITECTURE.read_text(encoding="utf-8")

    for token in [
        "Static-first v0 architecture",
        "model_comparison_predictions.csv",
        "county_week_seasonal_risk_baseline.csv",
        "public/data",
        "public/app.js",
        "GitHub Pages",
        "no raw data",
        "Future service architecture",
    ]:
        assert token in architecture

    first_section = architecture.split("## Future service architecture", maxsplit=1)[0]
    for token in ["FastAPI", "PostGIS", "PyMC"]:
        assert token not in first_section


def test_public_modeling_docs_do_not_overclaim_unimplemented_model_lanes() -> None:
    docs_text = "\n".join(
        [
            README.read_text(encoding="utf-8"),
            Path("docs/data-manifest.md").read_text(encoding="utf-8"),
            Path("docs/etl-pipeline.md").read_text(encoding="utf-8"),
        ]
    )

    forbidden_tokens = [
        "consumed by the Bayesian model",
        "for Bayesian, linear, random forest, and ensemble lanes",
        "for Bayesian, linear, random-forest, or ensemble modeling",
    ]
    for token in forbidden_tokens:
        assert token not in docs_text

    for token in [
        "stdlib baselines, ridge profiles, empirical-Bayes shrinkage, and future model lanes",
        "current v0 model comparison",
    ]:
        assert token in docs_text


def test_roadmap_starts_from_shipped_static_maryland_v0() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for token in [
        "Current v0 baseline",
        "Maryland static dashboard",
        "county-week seasonal Lyme baseline",
        "single-bite Lyme decision-support overlay",
        "GitHub Pages",
        "model comparison",
        "Roadmap",
    ]:
        assert token in roadmap

    current_section = roadmap.split("## Roadmap", maxsplit=1)[0]
    for token in [
        "docker compose up downloads sample DB",
        "Full CONUS priors 2025 season",
        "/risk API; React+D3 dashboard",
        "Per-bite research model that combines geography",
    ]:
        assert token not in current_section


def test_vision_scope_includes_single_bite_score_without_absolute_probability_claim() -> None:
    vision = VISION_SCOPE.read_text(encoding="utf-8")

    for token in [
        "Current v0 scope",
        "relative county-week seasonal Lyme baseline",
        "single-bite Lyme decision-support score",
        "not an absolute infection probability",
        "Future research scope",
    ]:
        assert token in vision

    current_section = vision.split("## Future research scope", maxsplit=1)[0]
    for token in [
        "FastAPI",
        "Dockerised",
        "posterior",
        "tau_hours",
        "probability + CI",
        "Bite-specific calculations using tick attachment duration",
    ]:
        assert token not in current_section


def test_model_spec_leads_with_implemented_comparison_model_before_research_model() -> None:
    model_spec = MODEL_SPEC.read_text(encoding="utf-8")

    for token in [
        "Current implemented model",
        "Single-bite decision-support overlay",
        "model_comparison_predictions.csv",
        "model_features_county_year.csv",
        "model_design_matrix_county_year.csv",
        "md_county_risk_weekly.json",
        "linear_blend_baseline",
        "ridge_forecast_safe",
        "not weather-adjusted",
        "Research roadmap model",
    ]:
        assert token in model_spec

    current_section = model_spec.split("## Research roadmap model", maxsplit=1)[0]
    for token in [
        "PyMC",
        "NUTS",
        "p(τ)",
        "posterior probability",
        "risk_baseline.json",
        "model_feature_matrix.csv",
        "model_design_matrix.csv",
    ]:
        assert token not in current_section


def test_srs_documents_single_bite_runtime_as_current_nonmedical_feature() -> None:
    srs = SRS.read_text(encoding="utf-8")

    for token in [
        "Single-Bite Runtime",
        "tickbiterisk risk single-bite",
        "single-bite Lyme decision-support score",
        "CDC prophylaxis consideration criteria",
        "not an absolute infection probability",
    ]:
        assert token in srs


def test_data_sources_catalog_matches_current_v0_artifacts() -> None:
    catalog = DATA_SOURCES.read_text(encoding="utf-8")

    for token in [
        "Current source catalog",
        "Current v0 derived artifacts",
        "Status",
        "model_features_county_year.csv",
        "model_comparison_predictions",
        "county_week_seasonal_risk_baseline",
        "md_county_risk_weekly.json",
        "md_county_metadata.json",
    ]:
        assert token in catalog

    for token in [
        "theta_{year}.parquet",
        "lambda_weekly.parquet",
        "Posterior draws per season",
        "pipelines/fetch_ed.sh",
        "risk_baseline.json",
        "model_feature_matrix.csv",
        "model_design_matrix.csv",
    ]:
        assert token not in catalog


def test_testing_ci_plan_documents_current_static_pipeline_not_future_model_service() -> None:
    ci_plan = TESTING_CI_PLAN.read_text(encoding="utf-8")

    for token in [
        "Current CI plan",
        "ruff check .",
        "pytest -q",
        "node --check public/app.js",
        "public data JSON parses",
        "GitHub Pages",
    ]:
        assert token in ci_plan

    for token in [
        "PyMC fit",
        "Docker image",
        "OpenAPI JSON",
        "NetCDF",
        "OpenAPI schema diff clean",
    ]:
        assert token not in ci_plan


def test_etl_pipeline_doc_has_current_cli_flow_without_unimplemented_lambda_stack() -> None:
    etl = ETL_PIPELINE.read_text(encoding="utf-8")

    for token in [
        "Current v0 ETL pipeline",
        "tickbiterisk etl lyme-outcomes",
        "tickbiterisk etl model-features",
        "tickbiterisk etl model-compare",
        "tickbiterisk etl county-week-risk",
        "model_features_county_year.csv",
        "model_design_matrix_county_year.csv",
        "tickbiterisk risk export-static",
        "No live weekly ED scaler is wired into the current product",
    ]:
        assert token in etl

    for token in [
        "derive_lambda_inputs.py",
        "lambda_input.parquet",
        "PyMC incremental ADVI",
        "triggers full PyMC MCMC",
        "cron/annual.sh",
        "model_feature_matrix.csv",
        "model_design_matrix.csv",
    ]:
        assert token not in etl


def test_model_background_frames_bayesian_work_as_future_research_not_current_runtime() -> None:
    background = MODEL_BACKGROUND.read_text(encoding="utf-8")

    for token in [
        "Current rationale",
        "ensemble-ready comparison",
        "Bayesian modeling remains a research lane",
        "not the current runtime",
        "plain-language public product",
    ]:
        assert token in background

    current_section = background.split("## Future Bayesian research", maxsplit=1)[0]
    for token in [
        "FastAPI",
        "NetCDF",
        "incremental ADVI",
        "built on a Bayesian state-space framework",
    ]:
        assert token not in current_section
