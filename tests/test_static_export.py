import json
from pathlib import Path

from tests.test_runtime_risk_lookup import _score_row, _write_csv, _write_scores
from tickbiterisk.runtime.static_export import (
    StaticExportInputError,
    export_static_risk_data,
)


def test_export_static_risk_data_writes_public_json_files(tmp_path: Path) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    model_summary_path = _write_model_summary(tmp_path / "model_summary.csv")

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        model_summary_path=model_summary_path,
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
    assert weekly["selected_forecast_metadata"] == {
        "forecast_origin_year": 2022,
        "as_of_date": "2026-05-28",
        "data_cutoff_date": "2024-12-31",
        "source_vintage": "mdh_2024_reviewed_v1",
        "update_mode": "pre_update",
    }
    assert (
        "Relative Maryland county-week Lyme forecast, not a per-bite infection probability."
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

    assert model_card["product_framing"] == (
        "Lyme risk forecasting tool for Maryland county-week conditions"
    )
    assert model_card["score_interpretation"].startswith(
        "Relative seasonal Lyme forecast"
    )
    assert "not medical advice" in model_card["clinical_disclaimer"].lower()
    assert "Not a personal infection probability." in model_card["caveats"]
    assert model_card["quality_flags"] == [
        "relative_seasonal_baseline",
        "static_seasonality_prior",
        "not_weather_adjusted",
    ]
    assert model_card["annual_prediction_source"]["artifact_type"] == (
        "annual_prediction_branch"
    )
    assert model_card["annual_prediction_source"]["run_id"] == "run1"
    assert model_card["annual_prediction_source"]["sha256"] == "a" * 64
    assert model_card["annual_prediction_source"]["model_family"] == "ensemble"
    assert model_card["annual_prediction_source"]["weather_mode"] == (
        "not_used_by_baseline"
    )
    assert model_card["annual_prediction_source"]["forecast_origin_year"] == 2022
    assert model_card["annual_prediction_source"]["as_of_date"] == "2026-05-28"
    assert model_card["annual_prediction_source"]["source_vintage"] == (
        "mdh_2024_reviewed_v1"
    )
    assert model_card["validation_summary"] == {
        "run_id": "run1",
        "model_name": "linear_blend_baseline",
        "rank_by_mae": 1,
        "n_predictions": 408,
        "mae_incidence_per_100k": 18.24,
        "rmse_incidence_per_100k": 29.54,
        "pearson_correlation": 0.76,
        "validation_role": "historical_model_comparison",
        "validation_match_type": "selected_prediction_run",
        "forecast_model_name": "linear_blend_baseline",
        "comparison_assumption_flags": [
            "observational_not_causal",
            "intervention_history_unmodeled",
        ],
    }
    assert "Selected annual forecast" in model_card["method_summary"]
    assert model_card["forecasting_status"] == {
        "status": "risk_forecasting_tool",
        "public_score_role": (
            "relative county-week Lyme risk forecast with source-lag and "
            "update diagnostics"
        ),
        "update_policy": (
            "New surveillance, ecology, exposure, and calibration evidence are "
            "reconciled against prior forecasts and backtests before they are "
            "considered for future reviewed estimates."
        ),
    }
    assert {item["topic"] for item in model_card["explainer_placeholders"]} == {
        "why_forecasting",
        "data_lag_and_reconciliation",
        "forecast_update_research",
        "regional_hotspot_patterns",
    }
    placeholder_text = json.dumps(model_card["explainer_placeholders"]).lower()
    assert "bayesian" not in placeholder_text
    assert "hierarchical" not in placeholder_text
    assert source_catalog["sources"][0]["artifact_type"] == "derived"
    assert "selected annual forecast rows" in source_catalog["sources"][0]["notes"]
    assert source_catalog["sources"][1]["source_id"] == "annual_prediction_branch"
    assert source_catalog["sources"][1]["run_id"] == "run1"
    assert source_catalog["sources"][1]["sha256"] == "a" * 64
    assert source_catalog["sources"][1]["model_name"] == "linear_blend_baseline"
    assert source_catalog["sources"][1]["forecast_origin_year"] == 2022
    assert source_catalog["sources"][1]["update_mode"] == "pre_update"
    assert "no-observed-target" in source_catalog["sources"][1]["notes"]
    assert "prior-year validation" not in source_catalog["sources"][1]["notes"]
    assert source_catalog["sources"][2]["artifact_type"] == "derived seasonality prior"
    public_notes = " ".join(source["notes"] for source in source_catalog["sources"])
    assert "model-comparison" not in public_notes
    assert source_catalog["data_lag_and_update_policy"]["summary"].startswith(
        "Official Lyme surveillance data lag"
    )
    assert source_catalog["data_lag_and_update_policy"]["why_forecasting"].startswith(
        "Forecasting gives timely"
    )
    assert source_catalog["data_lag_and_update_policy"][
        "reconciliation_policy"
    ].startswith("New observed reports are reconciled")
    assert "surveillance-regime diagnostics" in source_catalog[
        "data_lag_and_update_policy"
    ]["reconciliation_policy"]
    assert "source quality flags" in source_catalog["data_lag_and_update_policy"][
        "reconciliation_policy"
    ]
    assert source_catalog["data_lag_and_update_policy"]["forecast_boundary"] == (
        "Forecast-safe branches use prior-year and trailing data; nowcast or "
        "retrospective branches must be labeled separately."
    )
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


def test_export_static_risk_data_preserves_existing_county_geojson_manifest(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "public-data"
    output_dir.mkdir()
    (output_dir / "md_counties.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {"feature_count": 24},
                "features": [{"type": "Feature"} for _ in range(24)],
            }
        ),
        encoding="utf-8",
    )

    outputs = export_static_risk_data(
        scores_path=_write_scores(tmp_path / "scores.csv"),
        output_dir=output_dir,
    )

    manifest = _read_json(outputs.export_manifest_path)

    assert "md_counties.geojson" in manifest["files"]
    assert manifest["record_counts"]["county_geojson_features"] == 24


def test_export_static_risk_data_rejects_missing_model_summary_match(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    model_summary_path = _write_model_summary(
        tmp_path / "model_summary.csv",
        model_name="prior_year_incidence",
    )

    try:
        export_static_risk_data(
            scores_path=scores_path,
            output_dir=tmp_path / "public-data",
            model_summary_path=model_summary_path,
        )
    except StaticExportInputError as exc:
        assert "No model comparison summary row matched" in str(exc)
    else:
        raise AssertionError("Expected missing summary match export to fail")


def test_export_static_risk_data_uses_model_validation_for_true_forecast_source(
    tmp_path: Path,
) -> None:
    scores_path = _write_csv(
        tmp_path / "scores.csv",
        [
            {
                **_score_row("24003", "Anne Arundel County", "2026", "1", "7"),
                "source_prediction_run_id": (
                    "annual_forecast_target2026_origin2024_mintrain5_shrink5p0"
                ),
                "evaluation_mode": "annual_forecast_no_observed_target",
                "forecast_origin_year": "2024",
                "as_of_date": "2026-05-28",
                "data_cutoff_date": "2024-12-31",
                "source_vintage": "2024-inclusive-local",
            },
        ],
    )
    model_summary_path = _write_model_summary(tmp_path / "model_summary.csv")

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        model_summary_path=model_summary_path,
    )

    model_card = _read_json(outputs.model_card_path)

    assert model_card["annual_prediction_source"]["run_id"].startswith(
        "annual_forecast_target2026"
    )
    assert model_card["annual_prediction_source"]["forecast_origin_year"] == 2024
    assert model_card["annual_prediction_source"]["source_vintage"] == (
        "2024-inclusive-local"
    )
    assert model_card["validation_summary"]["run_id"] == "run1"
    assert model_card["validation_summary"]["model_name"] == "linear_blend_baseline"
    assert model_card["validation_summary"]["validation_match_type"] == (
        "annual_forecast_model_name"
    )
    assert model_card["validation_summary"]["forecast_model_name"] == (
        "linear_blend_baseline"
    )


def test_export_static_risk_data_reranks_public_validation_without_research_lanes(
    tmp_path: Path,
) -> None:
    scores_path = _write_csv(
        tmp_path / "scores.csv",
        [
            {
                **_score_row("24003", "Anne Arundel County", "2026", "1", "7"),
                "source_prediction_run_id": (
                    "annual_forecast_target2026_origin2024_mintrain5_shrink5p0"
                ),
                "evaluation_mode": "annual_forecast_no_observed_target",
            },
        ],
    )
    model_summary_path = _write_model_summary_with_research_winner(
        tmp_path / "model_summary.csv"
    )

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        model_summary_path=model_summary_path,
    )

    model_card = _read_json(outputs.model_card_path)

    assert model_card["validation_summary"]["model_name"] == "linear_blend_baseline"
    assert model_card["validation_summary"]["mae_incidence_per_100k"] == 18.47
    assert model_card["validation_summary"]["rank_by_mae"] == 2
    assert model_card["validation_summary"]["validation_match_type"] == (
        "annual_forecast_model_name"
    )


def test_export_static_risk_data_keeps_blank_optional_validation_metrics_null(
    tmp_path: Path,
) -> None:
    scores_path = _write_scores(tmp_path / "scores.csv")
    model_summary_path = _write_model_summary(
        tmp_path / "model_summary.csv",
        n_predictions="",
        mae_incidence_per_100k="",
        rmse_incidence_per_100k="",
        pearson_correlation="",
    )

    outputs = export_static_risk_data(
        scores_path=scores_path,
        output_dir=tmp_path / "public-data",
        model_summary_path=model_summary_path,
    )

    model_card = _read_json(outputs.model_card_path)
    validation = model_card["validation_summary"]

    assert validation["n_predictions"] is None
    assert validation["mae_incidence_per_100k"] is None
    assert validation["rmse_incidence_per_100k"] is None
    assert validation["pearson_correlation"] is None
    assert validation["validation_role"] == "historical_model_comparison"


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


def _write_model_summary(
    path: Path,
    *,
    model_name: str = "linear_blend_baseline",
    n_predictions: str = "408",
    mae_incidence_per_100k: str = "18.24",
    rmse_incidence_per_100k: str = "29.54",
    pearson_correlation: str = "0.76",
) -> Path:
    path.write_text(
        "\n".join(
            [
                (
                    "run_id,rank_by_mae,model_name,model_family,feature_profile,"
                    "n_predictions,mae_incidence_per_100k,rmse_incidence_per_100k,"
                    "pearson_correlation,comparison_assumption_flags"
                ),
                (
                    f"run1,1,{model_name},ensemble,lagged_outcome_blend,"
                    f"{n_predictions},"
                    f"{mae_incidence_per_100k},{rmse_incidence_per_100k},"
                    f"{pearson_correlation},"
                    "\"observational_not_causal,intervention_history_unmodeled\""
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_model_summary_with_research_winner(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                (
                    "run_id,rank_by_mae,model_name,model_family,feature_profile,"
                    "n_predictions,mae_incidence_per_100k,rmse_incidence_per_100k,"
                    "pearson_correlation,comparison_assumption_flags"
                ),
                (
                    "run1,1,forecast_safe_top4_ensemble,ensemble,"
                    "forecast_safe_top4_blend,432,17.97,29.0,0.78,"
                    "\"observational_not_causal\""
                ),
                (
                    "run1,2,prior_year_incidence,baseline,lagged_outcome,432,"
                    "18.21,30.0,0.77,\"observational_not_causal\""
                ),
                (
                    "run1,3,linear_blend_baseline,ensemble,lagged_outcome_blend,"
                    "432,18.47,31.0,0.76,\"observational_not_causal\""
                ),
                (
                    "run1,4,ridge_forecast_safe,regularized_linear,"
                    "forecast_safe_lagged,432,18.89,32.0,0.75,"
                    "\"observational_not_causal\""
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
