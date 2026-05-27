from typer.testing import CliRunner

from tickbiterisk.cli import app
from tickbiterisk.etl.ecology_sources import EcologySourceFile


runner = CliRunner()


def test_ecology_sources_command_writes_raw_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "tickbiterisk.cli.ECOLOGY_SOURCE_FILES",
        [
            EcologySourceFile(
                source_id="example",
                family="example",
                url="https://example.test/page",
                raw_relative_path="example/page.html",
                description="Example page",
                expected_format="html",
            )
        ],
    )
    monkeypatch.setattr(
        "tickbiterisk.cli.download_source_files",
        lambda sources, raw_dir, manifest_path: type(
            "Result",
            (),
            {"row_count": 1, "manifest_path": manifest_path},
        )(),
    )

    result = runner.invoke(
        app,
        [
            "etl",
            "ecology-sources",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--manifest-path",
            str(tmp_path / "manifest.csv"),
        ],
    )

    assert result.exit_code == 0
    assert "Downloaded/catalogued 1 ecology source file(s)" in result.stdout
