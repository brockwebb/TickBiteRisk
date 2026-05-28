import csv

from typer.testing import CliRunner

from tickbiterisk.cli import app


runner = CliRunner()


def test_enso_oni_command_writes_season_and_model_year_outputs(
    tmp_path,
    monkeypatch,
) -> None:
    oni_text = """ SEAS  YR   TOTAL   ANOM
 DJF 2020  26.10   0.40
 JFM 2020  26.20   0.50
 FMA 2020  26.30  -0.60
 MAM 2020  26.40   0.00
 AMJ 2020  26.50   0.80
 MJJ 2020  26.60  -0.50
 JJA 2020  26.70   1.00
 JAS 2020  26.80  -0.20
 ASO 2020  26.90  -0.90
 SON 2020  27.00   0.20
 OND 2020  27.10   0.60
 NDJ 2020  27.20  -1.10
"""

    monkeypatch.setattr("tickbiterisk.cli.fetch_oni_text", lambda url: oni_text)

    result = runner.invoke(
        app,
        [
            "etl",
            "enso-oni",
            "--source-url",
            "https://example.test/oni.ascii.txt",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote 12 NOAA CPC ONI season row(s)" in result.stdout
    assert "Wrote 1 NOAA CPC ONI model-year feature row(s)" in result.stdout
    assert (tmp_path / "out" / "noaa_cpc_oni_seasons.csv").exists()
    assert (tmp_path / "out" / "noaa_cpc_oni_model_year_features.csv").exists()
    manifest_path = tmp_path / "out" / "acquisition_provenance.csv"
    assert manifest_path.exists()
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_id"] == "noaa_cpc_oni"
    assert rows[0]["source_url"] == "https://example.test/oni.ascii.txt"
    assert rows[0]["citation_url"] == "https://example.test/oni.ascii.txt"
    assert rows[0]["request_method"] == "GET"
    assert rows[0]["parser_method"] == "parse_oni_ascii_text"
    assert rows[0]["extraction_quality"] == "accepted"
    assert rows[0]["row_count"] == "12"
    assert "tickbiterisk etl enso-oni" in rows[0]["acquisition_command"]
    assert "noaa_cpc_oni_seasons.csv=" in rows[0]["derived_artifact_sha256s"]


def test_enso_oni_command_sanitizes_credential_like_source_url_in_manifest(
    tmp_path,
    monkeypatch,
) -> None:
    oni_text = """ SEAS  YR   TOTAL   ANOM
 DJF 2020  26.10   0.40
"""

    monkeypatch.setattr("tickbiterisk.cli.fetch_oni_text", lambda url: oni_text)

    result = runner.invoke(
        app,
        [
            "etl",
            "enso-oni",
            "--source-url",
            (
                "https://example.test/oni.ascii.txt?"
                "token=secret-token&client_secret=secret-client&"
                "x-api-key=secret-api-key&year=2020"
            ),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0
    manifest_path = tmp_path / "out" / "acquisition_provenance.csv"
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert "secret-token" not in row["source_url"]
    assert "secret-client" not in row["source_url"]
    assert "secret-api-key" not in row["source_url"]
    assert "secret-token" not in row["citation_url"]
    assert "secret-client" not in row["citation_url"]
    assert "secret-api-key" not in row["citation_url"]
    assert "secret-token" not in row["acquisition_command"]
    assert "secret-client" not in row["acquisition_command"]
    assert "secret-api-key" not in row["acquisition_command"]
    assert "token=%3Credacted%3E" in row["source_url"]
    assert "client_secret=%3Credacted%3E" in row["source_url"]
    assert "x-api-key=%3Credacted%3E" in row["source_url"]
    assert "year=2020" in row["source_url"]
