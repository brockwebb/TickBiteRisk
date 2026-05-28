import csv
from pathlib import Path

from tickbiterisk.etl.enso import (
    build_mei_v2_model_year_features,
    build_oni_model_year_features,
    parse_mei_v2_csv_text,
    parse_oni_ascii_text,
)
from tickbiterisk.etl.enso_build import (
    MEI_V2_MODEL_YEAR_COLUMNS,
    MEI_V2_MONTHLY_COLUMNS,
    ONI_MODEL_YEAR_COLUMNS,
    ONI_SEASON_COLUMNS,
    write_mei_v2_model_year_output,
    write_mei_v2_monthly_output,
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

MEI_V2_CSV = """Date, Multivariate ENSO Index Version 2 (MEI.v2)  missing value -999 https://psl.noaa.gov/data/timeseries/month/
2020-01-01,    0.400
2020-02-01,    0.600
2020-03-01,   -0.700
2020-04-01,    0.000
2020-05-01,    0.800
2020-06-01,   -0.500
2020-07-01,    1.000
2020-08-01,   -0.200
2020-09-01,   -0.900
2020-10-01,    0.200
2020-11-01,    0.600
2020-12-01,   -1.100
2021-01-01,   -0.700
2021-02-01, -999.000
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


def test_parse_mei_v2_csv_text_assigns_month_phase_and_source_metadata() -> None:
    rows = parse_mei_v2_csv_text(
        MEI_V2_CSV,
        source_url="https://example.test/meiv2.csv",
    )

    assert len(rows) == 14
    assert rows[0].month_start_date == "2020-01-01"
    assert rows[0].year == 2020
    assert rows[0].month == 1
    assert rows[0].mei_v2_value == 0.4
    assert rows[0].mei_v2_phase == "neutral"
    assert rows[1].mei_v2_phase == "positive"
    assert rows[2].mei_v2_phase == "negative"
    assert rows[-1].mei_v2_value is None
    assert rows[-1].mei_v2_phase == "missing"
    assert rows[0].source_id == "noaa_psl_mei_v2"
    assert len(rows[0].source_url_hash) == 64
    assert rows[0].feature_quality_flags == (
        "global_climate_index,not_maryland_specific,mei_v2_index"
    )
    assert "missing_value" in rows[-1].feature_quality_flags


def test_build_mei_v2_model_year_features_uses_complete_prior_year_only() -> None:
    rows = parse_mei_v2_csv_text(
        MEI_V2_CSV,
        source_url="https://example.test/meiv2.csv",
    )

    features = build_mei_v2_model_year_features(rows)

    feature_2021 = next(row for row in features if row.model_year == 2021)
    assert feature_2021.mei_v2_prior_year_month_count == 12
    assert feature_2021.mei_v2_prior_year_mean == round(0.2 / 12, 6)
    assert feature_2021.mei_v2_prior_year_max == 1.0
    assert feature_2021.mei_v2_prior_year_min == -1.1
    assert feature_2021.mei_v2_prior_year_positive_month_count == 4
    assert feature_2021.mei_v2_prior_year_negative_month_count == 4
    assert feature_2021.source_ids == "noaa_psl_mei_v2"
    assert feature_2021.feature_quality_flags == (
        "global_climate_index,not_maryland_specific,mei_v2_index,prior_year_signal"
    )

    assert all(row.model_year != 2020 for row in features)
    assert all(row.model_year != 2022 for row in features)


def test_write_mei_v2_outputs_order_and_dedupe(tmp_path: Path) -> None:
    rows = parse_mei_v2_csv_text(
        MEI_V2_CSV,
        source_url="https://example.test/meiv2.csv",
    )
    features = build_mei_v2_model_year_features(rows)

    monthly_path = write_mei_v2_monthly_output(rows, tmp_path)
    feature_path = write_mei_v2_model_year_output(features, tmp_path)
    feature_path = write_mei_v2_model_year_output(features, tmp_path, append=True)

    with monthly_path.open("r", encoding="utf-8", newline="") as handle:
        monthly_records = list(csv.DictReader(handle))
    assert list(monthly_records[0].keys()) == MEI_V2_MONTHLY_COLUMNS
    assert monthly_records[0]["month_start_date"] == "2020-01-01"
    assert monthly_records[0]["mei_v2_value"] == "0.4"

    with feature_path.open("r", encoding="utf-8", newline="") as handle:
        feature_records = list(csv.DictReader(handle))
    assert list(feature_records[0].keys()) == MEI_V2_MODEL_YEAR_COLUMNS
    assert len(feature_records) == 1
    assert feature_records[0]["model_year"] == "2021"
