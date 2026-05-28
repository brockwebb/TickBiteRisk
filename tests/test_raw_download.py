import csv

from tickbiterisk.etl.ecology_sources import EcologySourceFile
from tickbiterisk.etl import raw_download
from tickbiterisk.etl.raw_download import download_source_files, fetch_url_bytes


class FakeBytesResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> "FakeBytesResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.content


def test_fetch_url_bytes_retries_transient_oserror_then_returns_bytes(
    monkeypatch,
) -> None:
    calls = []

    def flaky_urlopen(request, *, timeout: int):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise TimeoutError("timed out before first byte")
        return FakeBytesResponse(b"ok")

    monkeypatch.setattr(raw_download, "urlopen", flaky_urlopen)

    content = fetch_url_bytes(
        "https://example.test/file",
        retry_delay_seconds=0,
    )

    assert content == b"ok"
    assert len(calls) == 2
    assert calls[0][0].headers["User-agent"] == "tickbiterisk-etl/0.1"
    assert calls[0][1] == 60


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


def test_download_source_files_manifest_preserves_acquisition_evidence(tmp_path) -> None:
    source = EcologySourceFile(
        source_id="example_api",
        family="example",
        url="https://example.test/api?format=csv",
        raw_relative_path="example/page.csv",
        description="Example API export",
        expected_format="csv",
        citation_url="https://example.test/citation",
        acquisition_procedure="Fetch the official API export for offline ETL review.",
        access_notes="No API key in test fixture.",
    )

    result = download_source_files(
        [source],
        raw_dir=tmp_path / "raw",
        manifest_path=tmp_path / "manifest.csv",
        fetcher=lambda url: b"county,value\n24001,1\n",
    )

    with result.manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "source_id": "example_api",
            "family": "example",
            "description": "Example API export",
            "url": "https://example.test/api?format=csv",
            "citation_url": "https://example.test/citation",
            "raw_relative_path": "example/page.csv",
            "local_path": str(tmp_path / "raw" / "example" / "page.csv"),
            "expected_format": "csv",
            "parser_method": "not_run_raw_acquisition_only",
            "extraction_quality": "not_evaluated_at_raw_acquisition",
            "bytes": "21",
            "sha256": "8337e4f116df78434e93be37cd70bbec0b4b1d576eb5c75ea43164a13fd344c5",
            "ingested_at": rows[0]["ingested_at"],
            "acquisition_command": (
                f"tickbiterisk etl ecology-sources --raw-dir {tmp_path / 'raw'} "
                f"--manifest-path {tmp_path / 'manifest.csv'}"
            ),
            "acquisition_procedure": "Fetch the official API export for offline ETL review.",
            "access_notes": "No API key in test fixture.",
            "modeling_caveats": "not_model_input_until_parser_and_backtest_acceptance",
        }
    ]


def test_download_source_files_quotes_default_acquisition_command_paths(tmp_path) -> None:
    raw_dir = tmp_path / "raw data"
    manifest_path = tmp_path / "manifest files" / "source manifest.csv"
    source = EcologySourceFile(
        source_id="example_pdf",
        family="example",
        url="https://example.test/file.pdf",
        raw_relative_path="example/file.pdf",
        description="Example PDF",
        expected_format="pdf",
    )

    result = download_source_files(
        [source],
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        fetcher=lambda url: b"PDF",
    )

    with result.manifest_path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["acquisition_command"] == (
        "tickbiterisk etl ecology-sources "
        f"--raw-dir '{raw_dir}' --manifest-path '{manifest_path}'"
    )


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
