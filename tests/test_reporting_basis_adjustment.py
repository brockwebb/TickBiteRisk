import csv
from pathlib import Path

from tickbiterisk.modeling.regimes import (
    CASE_DEFINITION_2022_PLUS,
    COVID_REPORTING_DISRUPTION,
    PRE_2020_BASELINE,
)
from tickbiterisk.modeling.reporting_basis_adjustment import (
    build_high_incidence_classification,
    build_reporting_basis_adjustment,
    read_reporting_basis_adjustment,
)
from tickbiterisk.modeling.reporting_basis_adjustment_build import (
    DID_CONTROL_PANEL_COLUMNS,
    HIGH_INCIDENCE_CLASSIFICATION_COLUMNS,
    REPORTING_BASIS_ADJUSTMENT_COLUMNS,
    REPORTING_BASIS_ADJUSTMENT_RUN_COLUMNS,
    write_reporting_basis_adjustment_outputs,
)


def test_high_incidence_classification_is_computed_from_pre_window_panel(
    tmp_path: Path,
) -> None:
    incidence = _write_regional_incidence(tmp_path / "regional_incidence.csv")

    result = build_high_incidence_classification(
        regional_incidence_path=incidence,
        pre_window_start=2017,
        pre_window_end=2019,
        threshold_per_100k=10.0,
        consecutive_years_required=3,
    )

    by_state = {row.jurisdiction_fips: row for row in result.rows}
    assert by_state["24"].classification == "high_incidence"
    assert by_state["24"].qualifying_years == "2017;2018;2019"
    assert by_state["54"].classification == "low_incidence"
    assert by_state["54"].qualifying_years == ""
    assert by_state["11"].classification == "excluded_insufficient_pre_window"
    assert by_state["11"].assumption_flags == "insufficient_pre_window_years"
    assert result.pre_window == "2017-2019"
    assert len(result.source_panel_sha256) == 64


def test_reporting_basis_adjustment_uses_did_and_smooths_across_adjacency(
    tmp_path: Path,
) -> None:
    incidence = _write_regional_incidence(
        tmp_path / "regional_incidence.csv",
        no_low_incidence_controls=True,
    )
    adjacency = _write_adjacency(tmp_path / "adjacency.csv")
    control_panel = _write_did_control_panel(tmp_path / "did_control_candidates.csv")

    result = build_reporting_basis_adjustment(
        regional_incidence_path=incidence,
        county_adjacency_path=adjacency,
        did_control_panel_path=control_panel,
        pre_window_start=2017,
        pre_window_end=2019,
        boundary_year=2022,
    )

    by_county = {
        (row.jurisdiction_scope, row.source_regime): row
        for row in result.adjustments
    }
    md = by_county[("county_24001", PRE_2020_BASELINE)]
    md_covid = by_county[("county_24001", COVID_REPORTING_DISRUPTION)]
    md_reference = by_county[("county_24001", CASE_DEFINITION_2022_PLUS)]
    wv = by_county[("county_54001", PRE_2020_BASELINE)]
    assert md.source_regime == PRE_2020_BASELINE
    assert md.target_reference_basis == CASE_DEFINITION_2022_PLUS
    assert md.adjustment_method == "out_of_region_low_incidence_did"
    assert md.treatment_status == "high_incidence"
    assert md.multiplicative_factor == 1.818182
    assert md.smoothed_on_adjacency is False
    assert "did_parallel_trends_passed" in md.assumption_flags
    assert "Estimate adjusted to 2022 CDC reporting guidelines" in md.displayed_as
    assert md_covid.multiplicative_factor == md.multiplicative_factor
    assert md_covid.source_regime == COVID_REPORTING_DISRUPTION
    assert md_reference.multiplicative_factor == 1.0
    assert md_reference.adjustment_method == "reference_basis_no_adjustment"
    assert md_reference.factor_ci95_low == 1.0
    assert md_reference.factor_ci95_high == 1.0
    assert wv.treatment_status == "high_incidence"
    assert wv.multiplicative_factor == 1.818182
    assert abs(md.multiplicative_factor - wv.multiplicative_factor) <= 0.1
    assert result.run.identification_method == "out_of_region_low_incidence_did"
    assert result.run.did_treatment_shift == 2.0
    assert result.run.did_control_shift == 1.1
    assert result.run.did_ratio == 1.818182
    assert result.run.candidate_control_states_passed == "13"
    assert result.run.candidate_control_states_failed == "40:did_parallel_trends_violated"
    assert result.run.method_validation_2008_status in {"passed", "insufficient_data"}
    assert result.run.method_validation_2017_status in {"passed", "insufficient_data"}
    assert {
        (row.candidate_state_fips, row.parallel_trends_status)
        for row in result.did_control_panel
    } == {
        ("13", "passed"),
        ("40", "violated"),
    }
    assert all(
        row.instrument_role == "non_forecast_identification_instrument"
        for row in result.did_control_panel
    )
    assert all(row.forecast_exclusion == "must_not_enter_forecast_design_matrix" for row in result.did_control_panel)


def test_reporting_basis_adjustment_records_parallel_trends_violations(
    tmp_path: Path,
) -> None:
    incidence = _write_regional_incidence(
        tmp_path / "regional_incidence.csv",
        no_low_incidence_controls=True,
    )
    control_panel = _write_did_control_panel(
        tmp_path / "did_control_candidates.csv",
        all_controls_fail=True,
    )

    result = build_reporting_basis_adjustment(
        regional_incidence_path=incidence,
        did_control_panel_path=control_panel,
        pre_window_start=2017,
        pre_window_end=2019,
        boundary_year=2022,
        parallel_trend_tolerance=0.25,
    )

    assert result.run.identification_method == "cdc_published_anchor"
    assert result.run.parallel_trends_status == "violated"
    assert result.run.candidate_control_states_passed == ""
    assert result.run.candidate_control_states_failed == "40:did_parallel_trends_violated"
    assert any(row.parallel_trends_status == "violated" for row in result.did_control_panel)
    assert not any(
        row.adjustment_method == "interrupted_time_series"
        for row in result.adjustments
    )


def test_reporting_basis_adjustment_uses_cdc_fixed_prior_when_no_control_passes(
    tmp_path: Path,
) -> None:
    incidence = _write_regional_incidence(
        tmp_path / "regional_incidence.csv",
        no_low_incidence_controls=True,
    )

    result = build_reporting_basis_adjustment(
        regional_incidence_path=incidence,
        pre_window_start=2017,
        pre_window_end=2019,
        boundary_year=2022,
    )

    by_county = {
        (row.jurisdiction_scope, row.source_regime): row
        for row in result.adjustments
    }
    assert result.run.n_control_jurisdictions == 0
    assert result.run.identification_method == "cdc_published_anchor"
    assert result.run.did_control_evaluated is True
    assert result.run.did_control_passed is False
    assert (
        result.run.did_control_failure_reason
        == "insufficient_unsuppressed_county_panel_2017_2019"
    )
    assert (
        "docs/research/lab-notes/08-reporting-basis-identification.md"
        in result.run.did_control_decision_reference
    )
    assert (
        "docs/research/source-materials/did-control-verification-2017-2019.csv"
        in result.run.did_control_decision_reference
    )
    assert result.run.parallel_trends_status == "not_applicable"
    md = by_county[("county_24001", PRE_2020_BASELINE)]
    md_covid = by_county[("county_24001", COVID_REPORTING_DISRUPTION)]
    assert md.adjustment_method == "cdc_published_anchor"
    assert md.identification_quality == "moderate"
    assert md.multiplicative_factor == 1.729
    assert md_covid.multiplicative_factor == 1.729
    assert by_county[("county_54003", PRE_2020_BASELINE)].multiplicative_factor == 1.729
    assert "cdc_published_anchor_prior" in md.assumption_flags
    assert "did_control_group_unavailable" in md.assumption_flags
    assert "interrupted_time_series_diagnostic_only" in md.assumption_flags
    assert not any(
        row.adjustment_method == "interrupted_time_series"
        for row in result.adjustments
    )


def test_reporting_basis_adjustment_writer_round_trips(tmp_path: Path) -> None:
    incidence = _write_regional_incidence(
        tmp_path / "regional_incidence.csv",
        no_low_incidence_controls=True,
    )
    control_panel = _write_did_control_panel(tmp_path / "did_control_candidates.csv")
    result = build_reporting_basis_adjustment(
        regional_incidence_path=incidence,
        did_control_panel_path=control_panel,
        pre_window_start=2017,
        pre_window_end=2019,
        boundary_year=2022,
    )

    outputs = write_reporting_basis_adjustment_outputs(result, tmp_path / "out")

    with outputs.classification_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == HIGH_INCIDENCE_CLASSIFICATION_COLUMNS
    with outputs.run_path.open(newline="", encoding="utf-8") as handle:
        run_rows = list(csv.DictReader(handle))
    assert run_rows[0]["did_control_evaluated"] == "true"
    assert run_rows[0]["did_control_passed"] == "true"
    with outputs.run_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REPORTING_BASIS_ADJUSTMENT_RUN_COLUMNS
    with outputs.adjustment_path.open(newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == REPORTING_BASIS_ADJUSTMENT_COLUMNS
    with outputs.did_control_panel_path.open(newline="", encoding="utf-8") as handle:
        control_rows = list(csv.reader(handle))
    assert control_rows[0] == DID_CONTROL_PANEL_COLUMNS
    assert len(control_rows) == len(result.did_control_panel) + 1
    assert read_reporting_basis_adjustment(outputs.adjustment_path) == result.adjustments


def _write_regional_incidence(
    path: Path,
    *,
    divergent_pre_trends: bool = False,
    no_low_incidence_controls: bool = False,
) -> Path:
    rows = []
    series = {
        ("24", "MD", "Maryland", "24001", "Allegany County"): (
            [20, 20, 20, 40]
            if not divergent_pre_trends
            else [10, 20, 30, 60]
        ),
        ("24", "MD", "Maryland", "24003", "Anne Arundel County"): (
            [20, 20, 20, 40]
            if not divergent_pre_trends
            else [10, 20, 30, 60]
        ),
        ("54", "WV", "West Virginia", "54001", "Barbour County"): (
            [12, 12, 12, 24] if no_low_incidence_controls else [5, 5, 5, 5.5]
        ),
        ("54", "WV", "West Virginia", "54003", "Berkeley County"): (
            [12, 12, 12, 24] if no_low_incidence_controls else [5, 5, 5, 5.5]
        ),
        ("11", "DC", "District of Columbia", "11001", "District of Columbia"): [
            None,
            8,
            None,
            None,
        ],
    }
    for key, incidences in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for year, incidence in zip([2017, 2018, 2019, 2022], incidences):
            if incidence is None:
                continue
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(int(float(incidence))),
                    "population": "100000",
                    "incidence_per_100k": str(float(incidence)),
                    "diagnostic_midatlantic_incidence_rank": "",
                    "diagnostic_midatlantic_incidence_percentile": "",
                    "diagnostic_midatlantic_incidence_tier": "",
                    "diagnostic_prior_year_midatlantic_incidence_rank": "",
                    "diagnostic_midatlantic_incidence_rank_change": "",
                    "lyme_panel_sha256": "a" * 64,
                    "population_panel_sha256": "b" * 64,
                    "feature_quality_flags": "regional_incidence_diagnostic",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_adjacency(path: Path) -> Path:
    rows = [
        {"county_fips": "24001", "neighbor_county_fips": "54001"},
        {"county_fips": "54001", "neighbor_county_fips": "24001"},
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_did_control_panel(
    path: Path,
    *,
    all_controls_fail: bool = False,
) -> Path:
    rows = []
    series = {
        ("40", "OK", "Oklahoma", "40001", "Adair County"): [1, 5, 9, 9.9],
        ("40", "OK", "Oklahoma", "40003", "Alfalfa County"): [1, 5, 9, 9.9],
    }
    if not all_controls_fail:
        series.update(
            {
                ("13", "GA", "Georgia", "13001", "Appling County"): [5, 5, 5, 5.5],
                ("13", "GA", "Georgia", "13003", "Atkinson County"): [5, 5, 5, 5.5],
            }
        )
    for key, incidences in series.items():
        state_fips, state_abbr, state_name, county_fips, county_name = key
        for year, incidence in zip([2017, 2018, 2019, 2022], incidences):
            rows.append(
                {
                    "state_fips": state_fips,
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "year": str(year),
                    "total_cases": str(int(float(incidence))),
                    "population": "100000",
                    "incidence_per_100k": str(float(incidence)),
                    "feature_quality_flags": "non_forecast_identification_instrument",
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
