import csv
from pathlib import Path

import pytest

from tests.test_regional_forecast_observed_fit import (
    _write_forecast_predictions,
    _write_incidence_panel,
)
from tickbiterisk.modeling.forecast_skill_anchor import (
    ForecastSkillAnchorInputError,
    build_step1_forecast_skill_anchor,
    validate_step1_anchor_requested_use,
)
from tickbiterisk.modeling.forecast_skill_anchor_build import (
    STEP1_FORECAST_SKILL_ANCHOR_COLUMNS,
    write_step1_forecast_skill_anchor_outputs,
)
from tickbiterisk.modeling.regional_forecast_observed_fit import (
    build_regional_forecast_observed_fit,
)
from tickbiterisk.modeling.regional_forecast_observed_fit_build import (
    write_regional_forecast_observed_fit_outputs,
)


def test_step1_forecast_skill_anchor_uses_pa_2024_residuals_only_for_intervals(
    tmp_path: Path,
) -> None:
    comparisons = _write_observed_fit_comparisons(tmp_path)

    result = build_step1_forecast_skill_anchor(
        observed_fit_comparisons_path=comparisons,
        forecast_year=2024,
        state_abbr="PA",
    )

    assert result.run.forecast_year == 2024
    assert result.run.forecast_origin_year == 2023
    assert result.run.state_abbr == "PA"
    assert result.run.n_anchor_rows == 2
    assert result.run.permitted_use == "interval_calibration_only"
    assert result.run.prohibited_use == "point_correction_multiplier"

    adams = next(row for row in result.anchors if row.county_fips == "42001")
    assert adams.anchor_id == "pa_2024_step1_anchor_42001"
    assert adams.predicted_incidence_per_100k == 20.0
    assert adams.observed_incidence_per_100k == 30.0
    assert adams.incidence_residual_per_100k == 10.0
    assert adams.absolute_incidence_error_per_100k == 10.0
    assert adams.interval_calibration_weight == 1.0
    assert adams.point_correction_allowed is False
    assert adams.permitted_use == "interval_calibration_only"
    assert adams.prohibited_use == "point_correction_multiplier"
    assert "pa_2024_step1_anchor" in adams.anchor_assumption_flags
    assert "interval_calibration_only" in adams.anchor_assumption_flags


def test_step1_forecast_skill_anchor_writer_omits_point_correction_multiplier(
    tmp_path: Path,
) -> None:
    result = build_step1_forecast_skill_anchor(
        observed_fit_comparisons_path=_write_observed_fit_comparisons(tmp_path),
        forecast_year=2024,
        state_abbr="PA",
    )

    outputs = write_step1_forecast_skill_anchor_outputs(result, tmp_path / "out")

    with outputs.anchor_path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == STEP1_FORECAST_SKILL_ANCHOR_COLUMNS
    assert "point_correction_multiplier" not in header


def test_step1_forecast_skill_anchor_rejects_point_correction_use() -> None:
    with pytest.raises(ForecastSkillAnchorInputError) as excinfo:
        validate_step1_anchor_requested_use("point_correction_multiplier")

    assert "interval calibration only" in str(excinfo.value)


def _write_observed_fit_comparisons(tmp_path: Path) -> Path:
    result = build_regional_forecast_observed_fit(
        forecast_predictions_path=_write_forecast_predictions(tmp_path / "forecast.csv"),
        regional_incidence_path=_write_incidence_panel(tmp_path / "incidence.csv"),
        forecast_year=2024,
        state_abbr="PA",
        model_name="empirical_bayes_spatial_regime_incidence",
    )
    outputs = write_regional_forecast_observed_fit_outputs(result, tmp_path / "fit")
    return outputs.comparisons_path
