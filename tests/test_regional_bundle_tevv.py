"""Unit tests for the TEVV materiality rules (exact thresholds per spec)."""

from __future__ import annotations

from tickbiterisk.runtime.regional_bundle_tevv import (
    EXPECTED_COUNTY_COUNT,
    BundleMetrics,
    CountyMetric,
    compare_bundle_metrics,
    render_markdown,
    score_to_category,
)

YEAR = 2026


def _metrics(rows, total=EXPECTED_COUNTY_COUNT):
    """rows: list of (fips, incidence, score). Builds a one-year BundleMetrics.

    total_counties defaults to the deploy-validator invariant (283) so the
    county-count banner does not fire incidentally; tests that need a different
    region size pass `total` explicitly.
    """
    counties = {}
    for fips, inc, score in rows:
        counties[(fips, YEAR)] = CountyMetric(
            county_fips=fips,
            county_name=f"County {fips}",
            state_abbr="VA",
            forecast_year=YEAR,
            predicted_incidence_per_100k=inc,
            peak_score=score,
        )
    return BundleMetrics(
        counties=counties,
        total_counties=total,
        forecast_years=(YEAR,),
        record_counts={"regional_forecast_typicality.json": len(rows)},
        commit="newsha",
        generated_at="2026-06-06T00:00:00+00:00",
    )


def _fips(i: int) -> str:
    return f"51{i:03d}"


def test_score_to_category_bands():
    assert score_to_category(1) == "very_low"
    assert score_to_category(2) == "very_low"
    assert score_to_category(4) == "low"
    assert score_to_category(6) == "moderate"
    assert score_to_category(8) == "high"
    assert score_to_category(10) == "very_high"


def test_rule_a_relative_mover_above_floor_flags():
    # 10.0 -> 13.0 = 30% move, new >= 1.0, score unchanged -> only (a).
    deployed = _metrics([(_fips(1), 10.0, 1)])
    new = _metrics([(_fips(1), 13.0, 1)])
    result = compare_bundle_metrics(deployed, new)
    assert len(result.flags) == 1
    assert "a" in result.flags[0].rules
    assert result.flags[0].rules == ("a",)


def test_rule_a_below_floor_does_not_flag():
    # 0.50 -> 0.70 = 40% move but new < 1.0 -> NO flag (noise floor), no cat change.
    deployed = _metrics([(_fips(1), 0.50, 1)])
    new = _metrics([(_fips(1), 0.70, 1)])
    result = compare_bundle_metrics(deployed, new)
    assert result.flags == []
    assert result.review_recommended is False


def test_rule_b_category_change_flags_any_magnitude():
    # score 2 (very_low) -> 3 (low): a 1-bin move that crosses a category.
    deployed = _metrics([(_fips(1), 5.0, 2)])
    new = _metrics([(_fips(1), 5.1, 3)])  # incidence move ~2% (sub-threshold)
    result = compare_bundle_metrics(deployed, new)
    assert len(result.flags) == 1
    assert "b" in result.flags[0].rules
    assert "a" not in result.flags[0].rules  # 2% move does not trip (a)
    assert result.flags[0].category_change == ("very_low", "low")


def test_rule_b_fires_for_subfloor_category_change():
    # Sub-floor county flags ONLY via (b): incidence stays < 1.0 but score crosses.
    deployed = _metrics([(_fips(1), 0.4, 2)])
    new = _metrics([(_fips(1), 0.9, 3)])  # 125% relative move but < 1.0 -> (a) suppressed
    result = compare_bundle_metrics(deployed, new)
    assert len(result.flags) == 1
    assert result.flags[0].rules == ("b",)


def test_rule_c_two_bin_score_move_flags():
    # score 4 -> 6 = 2 bins; incidence sub-threshold move.
    deployed = _metrics([(_fips(1), 20.0, 4)])
    new = _metrics([(_fips(1), 20.5, 6)])
    result = compare_bundle_metrics(deployed, new)
    assert len(result.flags) == 1
    assert "c" in result.flags[0].rules
    assert result.flags[0].score_bin_move == 2


def test_quiet_diff_is_no_material_change():
    deployed = _metrics([(_fips(i), 10.0, 5) for i in range(20)])
    new = _metrics([(_fips(i), 10.5, 5) for i in range(20)])  # 5% moves, no cat change
    result = compare_bundle_metrics(deployed, new)
    assert result.flags == []
    assert result.review_recommended is False
    assert "No material change" in render_markdown(result)


def test_banner_trips_above_15pct_flagged():
    # Full 283-county region; flag 50 (50/283 = 17.7% > 15%) via rule (a):
    # each a 30% move >= 1.0, no single move > 50% (so the big-mover trip is off).
    n = EXPECTED_COUNTY_COUNT
    deployed = _metrics([(_fips(i), 10.0, 5) for i in range(n)])
    new = _metrics([(_fips(i), 13.0 if i < 50 else 10.0, 5) for i in range(n)])
    result = compare_bundle_metrics(deployed, new)
    assert len({f.metric_new.county_fips for f in result.flags}) == 50
    assert result.review_recommended is True
    assert any("flagged" in r for r in result.review_reasons)
    assert not any("relative" in r for r in result.review_reasons)  # not the big-mover trip


def test_banner_does_not_trip_at_10pct_without_big_mover():
    # 28/283 = 9.9% flagged (< 15%); moves are 30% (< 50%) -> flagged but no banner.
    n = EXPECTED_COUNTY_COUNT
    deployed = _metrics([(_fips(i), 10.0, 5) for i in range(n)])
    new = _metrics([(_fips(i), 13.0 if i < 28 else 10.0, 5) for i in range(n)])
    result = compare_bundle_metrics(deployed, new)
    assert len({f.metric_new.county_fips for f in result.flags}) == 28
    assert result.review_recommended is False


def test_banner_big_mover_trips_above_50pct():
    # Single county >50% relative AND >= 1.0 -> banner even though only 1 flagged.
    deployed = _metrics([(_fips(i), 10.0, 5) for i in range(20)])
    new_rows = [(_fips(i), 20.0 if i == 0 else 10.0, 5) for i in range(20)]  # 100% move
    new = _metrics(new_rows)
    result = compare_bundle_metrics(deployed, new)
    assert result.review_recommended is True
    assert any(">50%" in r or "relative" in r for r in result.review_reasons)


def test_big_mover_below_floor_does_not_trip_banner():
    # 100% move but new < 1.0 -> not a big mover, no flag.
    deployed = _metrics([(_fips(1), 0.3, 1)])
    new = _metrics([(_fips(1), 0.7, 1)])
    result = compare_bundle_metrics(deployed, new)
    assert result.review_recommended is False
    assert result.flags == []


def test_county_count_mismatch_trips_review():
    deployed = _metrics([(_fips(1), 10.0, 5)], total=EXPECTED_COUNTY_COUNT)
    new = _metrics([(_fips(1), 10.0, 5)], total=EXPECTED_COUNTY_COUNT - 1)
    result = compare_bundle_metrics(deployed, new)
    assert result.county_count_ok is False
    assert result.review_recommended is True


def test_record_count_change_trips_review():
    deployed = _metrics([(_fips(1), 10.0, 5)])
    new = BundleMetrics(
        counties={(_fips(1), YEAR): CountyMetric(_fips(1), "c", "VA", YEAR, 10.0, 5)},
        total_counties=1,
        forecast_years=(YEAR,),
        record_counts={"regional_forecast_typicality.json": 999},
        commit="newsha",
        generated_at="x",
    )
    result = compare_bundle_metrics(deployed, new)
    assert result.record_count_changes
    assert result.review_recommended is True


def test_baseline_when_no_deployed_bundle():
    new = _metrics([(_fips(1), 10.0, 5)])
    result = compare_bundle_metrics(None, new)
    assert result.is_baseline is True
    assert result.review_recommended is False
    assert "Baseline" in render_markdown(result)
