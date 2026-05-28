from pathlib import Path

from typer.testing import CliRunner

from tests.test_provenance_audit import (
    _write_bad_acquisition_manifest,
    _write_good_acquisition_manifest,
    _write_good_source_manifest,
)
from tickbiterisk.cli import app


runner = CliRunner()


def test_provenance_audit_command_reports_clean_manifest_set(tmp_path: Path) -> None:
    root = tmp_path / "build" / "etl"
    _write_good_acquisition_manifest(root / "population")
    _write_good_source_manifest(root / "ecology")

    result = runner.invoke(
        app,
        [
            "etl",
            "provenance-audit",
            "--root-dir",
            str(root),
        ],
    )

    assert result.exit_code == 0
    assert "Audited 2 provenance manifest(s), 2 row(s), 0 issue(s)." in result.stdout


def test_provenance_audit_command_fails_when_required_evidence_is_missing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "build" / "etl"
    _write_bad_acquisition_manifest(root / "bad")

    result = runner.invoke(
        app,
        [
            "etl",
            "provenance-audit",
            "--root-dir",
            str(root),
        ],
    )

    assert result.exit_code == 1
    assert "Provenance audit found" in result.stdout
    assert "bad_source" in result.stdout
    assert "citation_url" in result.stdout
    assert "acquisition_command" in result.stdout
