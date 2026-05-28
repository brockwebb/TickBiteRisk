import csv
from pathlib import Path

from tickbiterisk.etl.enso import (
    build_oni_model_year_features,
    parse_oni_ascii_text,
)
from tickbiterisk.etl.enso_build import (
    ONI_MODEL_YEAR_COLUMNS,
    ONI_SEASON_COLUMNS,
    write_oni_model_year_output,
    write_oni_season_output,
)


ONI_TEXT = """ SEAS  YR   TOTAL   ANOM
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
 DJF 2021  25.90  -0.70
 JFM 2021  26.00  -0.40
"""


def test_parse_oni_ascii_text_assigns_phase_and_source_metadata() -> None:
    rows = parse_oni_ascii_text(
        ONI_TEXT,
        source_url="https://example.test/oni.ascii.txt",
    )

    assert len(rows) == 14
    assert rows[0].season == "DJF"
    assert rows[0].year == 2020
    assert rows[0].total_sst_c == 26.1
    assert rows[0].oni_anomaly_c == 0.4
    assert rows[0].enso_phase == "neutral"
    assert rows[1].enso_phase == "el_nino"
    assert rows[2].enso_phase == "la_nina"
    assert rows[0].source_id == "noaa_cpc_oni"
    assert len(rows[0].source_url_hash) == 64
    assert rows[0].feature_quality_flags == "global_climate_index,not_maryland_specific"


def test_build_oni_model_year_features_uses_prior_year_without_future_leakage() -> None:
    rows = parse_oni_ascii_text(
        ONI_TEXT,
        source_url="https://example.test/oni.ascii.txt",
    )

    features = build_oni_model_year_features(rows)

    feature_2021 = next(row for row in features if row.model_year == 2021)
    assert feature_2021.oni_prior_year_season_count == 12
    assert feature_2021.oni_prior_year_mean_anomaly_c == round(0.2 / 12, 6)
    assert feature_2021.oni_prior_year_max_anomaly_c == 1.0
    assert feature_2021.oni_prior_year_min_anomaly_c == -1.1
    assert feature_2021.oni_prior_year_el_nino_season_count == 4
    assert feature_2021.oni_prior_year_la_nina_season_count == 4
    assert feature_2021.source_ids == "noaa_cpc_oni"
    assert feature_2021.feature_quality_flags == (
        "global_climate_index,not_maryland_specific,prior_year_signal"
    )

    assert all(row.model_year != 2020 for row in features)
    assert all(row.model_year != 2022 for row in features)


def test_write_oni_outputs_order_and_dedupe(tmp_path: Path) -> None:
    rows = parse_oni_ascii_text(
        ONI_TEXT,
        source_url="https://example.test/oni.ascii.txt",
    )
    features = build_oni_model_year_features(rows)

    season_path = write_oni_season_output(rows, tmp_path)
    feature_path = write_oni_model_year_output(features, tmp_path)
    feature_path = write_oni_model_year_output(features, tmp_path, append=True)

    with season_path.open("r", encoding="utf-8", newline="") as handle:
        season_records = list(csv.DictReader(handle))
    assert list(season_records[0].keys()) == ONI_SEASON_COLUMNS
    assert season_records[0]["season"] == "DJF"
    assert season_records[0]["year"] == "2020"

    with feature_path.open("r", encoding="utf-8", newline="") as handle:
        feature_records = list(csv.DictReader(handle))
    assert list(feature_records[0].keys()) == ONI_MODEL_YEAR_COLUMNS
    assert len(feature_records) == 1
    assert feature_records[0]["model_year"] == "2021"
