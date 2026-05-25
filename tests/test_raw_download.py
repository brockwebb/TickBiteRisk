from tickbiterisk.etl.ecology_sources import EcologySourceFile
from tickbiterisk.etl.raw_download import download_source_files


def test_download_source_files_writes_files_and_manifest(tmp_path) -> None:
    source = EcologySourceFile(
        source_id="example_html",
        family="example",
        url="https://example.test/page",
        raw_relative_path="example/page.html",
        description="Example HTML page",
        expected_format="html",
    )

    def fake_fetch(url: str) -> bytes:
        assert url == "https://example.test/page"
        return b"<html>ok</html>"

    result = download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )

    output_path = tmp_path / "raw" / "example" / "page.html"
    assert output_path.read_bytes() == b"<html>ok</html>"
    assert result.row_count == 1
    assert result.manifest_path == tmp_path / "manifest.csv"
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    assert "example_html" in manifest_text
    assert "sha256" in manifest_text
    assert "bytes" in manifest_text


def test_download_source_files_overwrites_idempotently(tmp_path) -> None:
    source = EcologySourceFile(
        source_id="example_pdf",
        family="example",
        url="https://example.test/file.pdf",
        raw_relative_path="example/file.pdf",
        description="Example PDF",
        expected_format="pdf",
    )
    calls = []
    payloads = iter([b"OLD", b"NEW"])

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        return next(payloads)

    download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )
    download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=fake_fetch,
    )

    assert calls == ["https://example.test/file.pdf", "https://example.test/file.pdf"]
    assert (tmp_path / "raw" / "example" / "file.pdf").read_bytes() == b"NEW"
