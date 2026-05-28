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
