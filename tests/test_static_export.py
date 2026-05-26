import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _score_row, _write_csv, _write_scores
from tickbiterisk.runtime.static_export import (
    StaticExportInputError,
    export_static_risk_data,
)


def test_export_static_risk_data_writes_public_json_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
    )

    assert outputs.weekly_risk_path.name == "md_county_risk_weekly.json"
    assert outputs.county_metadata_path.name == "md_county_metadata.json"
    assert outputs.model_card_path.name == "model_card.json"
    assert outputs.source_catalog_path.name == "source_catalog.json"
    assert outputs.export_manifest_path.name == "static_export_manifest.json"

    weekly = _read_json(outputs.weekly_risk_path)
    counties = _read_json(outputs.county_metadata_path)
    model_card = _read_json(outputs.model_card_path)
    source_catalog = _read_json(outputs.source_catalog_path)
    manifest = _read_json(outputs.export_manifest_path)

    assert weekly["schema_version"] == "county-week-risk-static-v1"
    assert weekly["export_type"] == "md_county_risk_weekly"
    assert weekly["scope"] == "maryland_county_week"
    assert weekly["date_system"]["name"] == "CDC MMWR"
    assert weekly["record_count"] == 2
    assert weekly["model_name"] == "linear_blend_baseline"
    assert weekly["seasonality_source_id"] == "cdc_seasonality_week_2023"
    assert weekly["score_scale"]["range"] == [1, 10]
    assert weekly["selected_score_config"]["source_prediction_sha256"] == "a" * 64
    assert (
        "Relative Maryland county-week Lyme baseline, not a per-bite infection probability."
        in weekly["caveats"]
    )
    assert "Not a personal infection probability." in weekly["caveats"]
    assert weekly["records"][0]["county_fips"] == "24003"
    assert weekly["records"][0]["year"] == 2023
    assert weekly["records"][0]["risk_score"] == 7
    assert weekly["records"][0]["predicted_weekly_incidence_95_interval"] == [
        1.5,
        3.5,
    ]

    assert counties["county_count"] == 2
    anne_arundel = next(
        county
        for county in counties["counties"]
        if county["county_fips"] == "24003"
    )
    assert anne_arundel["available_years"] == [2023]
    assert anne_arundel["source_available_years"] == [2022, 2023]
    assert anne_arundel["max_risk_score"] == 7

    assert model_card["score_interpretation"].startswith(
        "Relative seasonal Lyme baseline"
    )
    assert "not medical advice" in model_card["clinical_disclaimer"].lower()
    assert "Not a personal infection probability." in model_card["caveats"]
    assert model_card["quality_flags"] == [
        "relative_seasonal_baseline",
        "static_seasonality_prior",
        "not_weather_adjusted",
    ]
    assert source_catalog["sources"][0]["artifact_type"] == "derived"
    assert any("CDC" in link["title"] for link in source_catalog["guidance_links"])
    assert manifest["files"] == [
        "md_county_risk_weekly.json",
        "md_county_metadata.json",
        "model_card.json",
        "source_catalog.json",
        "static_export_manifest.json",
    ]
    assert manifest["record_counts"]["weekly_risk"] == 2


def test_export_static_risk_data_requires_unambiguous_score_branch(
    tmp_path: Path,
) -> None:
    scores_path = _write_ambiguous_scores(tmp_path / "scores.csv")

    try:
        export_static_risk_data(
            scores_path=scores_path,
            output_dir=tmp_path / "public-data",
        )
    except StaticExportInputError as exc:
        assert "Multiple static export score branches found" in str(exc)
    else:
        raise AssertionError("Expected ambiguous static export to fail")


def test_export_static_risk_data_can_select_score_branch(tmp_path: Path) -> None:
    scores_path = _write_ambiguous_scores(tmp_path / "scores.csv")

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        source_prediction_sha256="c" * 64,
    )

    weekly = _read_json(outputs.weekly_risk_path)

    assert weekly["record_count"] == 1
    assert weekly["selected_score_config"]["source_prediction_sha256"] == "c" * 64
    assert weekly["records"][0]["risk_score"] == 8


def test_export_static_risk_data_rejects_ambiguous_score_denominator(
    tmp_path: Path,
) -> None:
    scores_path = _write_csv(
        tmp_path / "scores.csv",
        [
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "8"),
                "score_denominator": "4.5",
            },
        ],
    )

    try:
        export_static_risk_data(
            scores_path=scores_path,
            output_dir=tmp_path / "public-data",
        )
    except StaticExportInputError as exc:
        assert "Multiple static export score branches found" in str(exc)
    else:
        raise AssertionError("Expected ambiguous denominator export to fail")

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        score_denominator=4.5,
    )
    weekly = _read_json(outputs.weekly_risk_path)

    assert weekly["selected_score_config"]["score_denominator"] == 4.5
    assert weekly["records"][0]["risk_score"] == 8


def _write_ambiguous_scores(path: Path) -> Path:
    return _write_csv(
        path,
        [
            _score_row("24003", "Anne Arundel County", "2023", "1", "7"),
            {
                **_score_row("24003", "Anne Arundel County", "2023", "1", "8"),
                "source_prediction_run_id": "run2",
                "source_prediction_sha256": "c" * 64,
            },
        ],
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
