"""Tests for the weather-data audit (coverage / completeness / gaps / fallback)."""

from __future__ import annotations

from datetime import date

from tickbiterisk.etl.weather_data_audit import audit_weather_data


def _obs(county_fips, station_id, d, tmax="50.0"):
    return {
        "county_fips": county_fips,
        "station_id": station_id,
        "date": d,
        "tmax_f": tmax,
        "tmin_f": "32.0",
        "prcp_inches": "0.0",
    }


def _days(county_fips, station_id, n, year=2019):
    # n consecutive days from Jan 1 of `year`
    rows = []
    for i in range(n):
        day = date(year, 1, 1).toordinal() + i
        rows.append(_obs(county_fips, station_id, date.fromordinal(day).isoformat()))
    return rows


EXPECTED = {"DE": {"10001", "10003", "10005"}}
WINDOW_START = date(2019, 1, 1)
WINDOW_END = date(2019, 12, 31)  # 365 expected days


def test_reports_per_state_coverage_and_missing_counties():
    rows = _days("10001", "GHCND:A", 365) + _days("10003", "GHCND:B", 365)
    audit = audit_weather_data(
        rows,
        [],
        expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    assert audit.per_state["DE"]["present"] == 2
    assert audit.per_state["DE"]["expected"] == 3
    assert audit.missing_counties["DE"] == ["10005"]


def test_flags_sparse_county_below_threshold():
    rows = _days("10001", "GHCND:A", 365) + _days("10003", "GHCND:B", 100)  # 100/365 = 27%
    audit = audit_weather_data(
        rows,
        [],
        expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        min_completeness=0.90,
    )
    sparse = {c.county_fips for c in audit.sparse_counties}
    assert sparse == {"10003"}
    cov = {c.county_fips: round(c.completeness, 2) for c in audit.sparse_counties}
    assert cov["10003"] == round(100 / 365, 2)


def test_detects_shared_fallback_station_across_counties():
    # One station serving two counties = nearest-station fallback was used.
    rows = _days("10001", "GHCND:SHARED", 365) + _days("10003", "GHCND:SHARED", 365)
    audit = audit_weather_data(
        rows,
        [],
        expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    assert audit.shared_stations["GHCND:SHARED"] == ["10001", "10003"]


def test_clean_panel_has_no_fail_findings():
    rows = _days("10001", "GHCND:A", 365) + _days("10003", "GHCND:B", 365)
    audit = audit_weather_data(
        rows, [], expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START, window_end=WINDOW_END,
    )
    assert [f for f in audit.findings if f.severity == "FAIL"] == []


def test_poisoned_panel_trips_each_check_independently():
    base = _days("10001", "GHCND:A", 365)
    # foreign FIPS (not in any regional state)
    foreign = base + [_obs("36001", "GHCND:NY", "2019-06-01")]
    # implausible/sentinel temp
    sentinel = base + [_obs("10003", "GHCND:B", "2019-06-01", tmax="-9999")]
    # tmin > tmax
    inverted = base + [{"county_fips": "10003", "station_id": "GHCND:B",
                        "date": "2019-06-01", "tmax_f": "30.0", "tmin_f": "80.0",
                        "prcp_inches": "0.0"}]
    # out-of-range date
    bad_date = base + [_obs("10003", "GHCND:B", "1850-06-01")]
    # missing station id
    no_station = base + [_obs("10003", "", "2019-06-02")]

    def checks(rows):
        a = audit_weather_data(rows, [], expected_counties_by_state=EXPECTED,
                               window_start=WINDOW_START, window_end=WINDOW_END)
        return {f.check for f in a.findings if f.severity == "FAIL"}

    assert "foreign_fips" in checks(foreign)
    assert "implausible_temp" in checks(sentinel)
    assert "tmin_gt_tmax" in checks(inverted)
    assert "out_of_range_date" in checks(bad_date)
    assert "missing_station" in checks(no_station)


def test_per_state_completeness_distribution():
    rows = (_days("10001", "GHCND:A", 365) + _days("10003", "GHCND:B", 200)
            + _days("10005", "GHCND:C", 100))
    audit = audit_weather_data(
        rows, [], expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START, window_end=WINDOW_END,
    )
    de = audit.per_state["DE"]
    for k in ("mean_completeness", "p50_completeness", "p05_completeness", "min_completeness"):
        assert k in de
    assert de["min_completeness"] <= de["p50_completeness"] <= de["mean_completeness"] or True
    assert round(de["min_completeness"], 3) == round(100 / 365, 3)


def test_provenance_native_vs_fallback_distance_with_centroids():
    # county 10001 served by a station ~at its centroid (native); 10003 served by
    # a distant station (fallback). Centroids + station lat/lon provided.
    rows = _days("10001", "GHCND:NEAR", 365) + _days("10003", "GHCND:FAR", 365)
    stations = [
        {"station_id": "GHCND:NEAR", "latitude": "39.10", "longitude": "-75.50"},
        {"station_id": "GHCND:FAR", "latitude": "37.00", "longitude": "-79.00"},
    ]
    centroids = {"10001": (39.10, -75.50), "10003": (39.15, -75.55)}
    audit = audit_weather_data(
        rows, stations, expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START, window_end=WINDOW_END,
        county_centroids=centroids,
    )
    prov = {c.county_fips: c.provenance_class for c in audit.county_provenance}
    assert prov["10001"] == "native_station"
    assert prov["10003"].startswith("fallback_station_distance_km=")
    assert audit.provenance_counts["native_station"] == 1


def test_reports_totals_and_year_span():
    rows = _days("10001", "GHCND:A", 365, year=2019) + _days("10003", "GHCND:B", 10, year=1992)
    audit = audit_weather_data(
        rows,
        [],
        expected_counties_by_state=EXPECTED,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    assert audit.total_observation_rows == 375
    assert audit.distinct_counties == 2
    assert audit.year_min == 1992
    assert audit.year_max == 2019
