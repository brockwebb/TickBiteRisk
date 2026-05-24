from pathlib import Path

from tickbiterisk.etl.sources import compute_sha256, load_sources_from_markdown


def test_load_sources_from_markdown_table() -> None:
    sources = load_sources_from_markdown(Path("tests/fixtures/manifest-mini.md"))
    assert [source.source_id for source in sources] == ["fixture_csv", "remote_candidate"]
    assert sources[0].format == "CSV"
    assert sources[0].is_local is True
    assert sources[1].is_local is False


def test_compute_sha256_for_local_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("tick risk\n", encoding="utf-8")
    assert compute_sha256(file_path) == "952085cb1f514d1814cab4821b26563f88fa4a65a1a57a240afb7e69a89b2762"
