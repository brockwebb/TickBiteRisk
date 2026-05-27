from __future__ import annotations

import tomllib
import json
from pathlib import Path


PYPROJECT = Path("pyproject.toml")
PACKAGE_JSON = Path("package.json")


def test_dev_extra_stays_light_for_github_pages_ci() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]

    assert "docling>=2.0" not in extras["dev"]
    assert "pytest>=8.2" in extras["dev"]
    assert "ruff>=0.5" in extras["dev"]


def test_ocr_extra_keeps_docling_available_for_pdf_review() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]

    assert extras["ocr"] == ["docling>=2.0"]


def test_dashboard_smoke_script_is_declared_for_ci() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    assert package["private"] is True
    assert package["scripts"]["test:dashboard"] == "playwright test"
    assert "@playwright/test" in package["devDependencies"]
