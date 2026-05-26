from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/pages.yml")


def _workflow_text() -> str:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _job_block(workflow: str, job_name: str) -> str:
    marker = f"\n  {job_name}:\n"
    start = workflow.index(marker) + 1
    next_job_start = workflow.find("\n  ", start + len(marker))
    while next_job_start != -1:
        next_line = workflow[next_job_start + 1 :].splitlines()[0]
        if next_line.endswith(":") and not next_line.startswith("    "):
            return workflow[start:next_job_start]
        next_job_start = workflow.find("\n  ", next_job_start + 1)
    return workflow[start:]


def _assert_in_order(text: str, tokens: list[str]) -> None:
    position = -1
    for token in tokens:
        next_position = text.find(token, position + 1)
        assert next_position > position, token
        position = next_position


def test_github_pages_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_github_pages_workflow_has_expected_triggers_and_permissions() -> None:
    workflow = _workflow_text()

    _assert_in_order(
        workflow,
        [
            "on:",
            "push:",
            "branches: [main]",
            "workflow_dispatch:",
            "permissions:",
            "contents: read",
            "concurrency:",
            "group: pages",
        ],
    )

    deploy = _job_block(workflow, "deploy")
    for token in [
        "needs: validate",
        "pages: write",
        "id-token: write",
        "environment:",
        "name: github-pages",
        "url: ${{ steps.deployment.outputs.page_url }}",
    ]:
        assert token in deploy


def test_github_pages_workflow_validates_static_dashboard_before_deploy() -> None:
    validate = _job_block(_workflow_text(), "validate")

    _assert_in_order(
        validate,
        [
            "actions/checkout@v6",
            "actions/setup-python@v6",
            'python-version: "3.12"',
            "actions/setup-node@v6",
            'node-version: "24"',
            'python -m pip install -e ".[dev]"',
            "ruff check .",
            "pytest -q",
            "node --check public/app.js",
            "Validate committed dashboard data",
            'data_dir = Path("public/data")',
            '"md_counties.geojson"',
            '"static_export_manifest.json"',
        ],
    )


def test_github_pages_workflow_deploys_committed_public_directory_only() -> None:
    workflow = _workflow_text()
    deploy = _job_block(workflow, "deploy")

    _assert_in_order(
        deploy,
        [
            "actions/configure-pages@v6",
            "actions/upload-pages-artifact@v5",
            "path: public",
            "id: deployment",
            "actions/deploy-pages@v5",
        ],
    )

    forbidden_tokens = [
        "build/",
        "build/etl",
        "data/raw",
        "NOAA_TOKEN",
        "CENSUS_API_KEY",
        "secrets.",
        "tickbiterisk dashboard build-assets",
        "tickbiterisk risk export-static",
    ]
    for token in forbidden_tokens:
        assert token not in workflow
