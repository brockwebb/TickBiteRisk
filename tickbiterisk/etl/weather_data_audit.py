"""Audit acquired NOAA weather data: coverage, fit-window completeness, gaps.

Programmatic, re-runnable audit of a weather observations file (and optional
stations file) against the six-state regional county universe. Reports per-state
coverage, daily completeness within a fit window, sparse counties (a risk for
rank-normalization), missing counties, and stations shared across counties
(an indicator that the nearest-station fallback was used).

Run:
    python -m tickbiterisk.etl.weather_data_audit \
        --observations build/etl/noaa-regional-1992-present/noaa_ghcnd_daily_observations.csv \
        --stations    build/etl/noaa-regional-1992-present/noaa_ghcnd_stations.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from tickbiterisk.etl.weather_config import REGIONAL_STATES
from tickbiterisk.etl.weather_locations import load_weather_locations

# State FIPS prefix -> abbreviation (regional product).
_PREFIX_TO_STATE = {"10": "DE", "11": "DC", "24": "MD", "42": "PA", "51": "VA", "54": "WV"}


_MIN_PLAUSIBLE_F = -60.0
_MAX_PLAUSIBLE_F = 130.0
_MIN_YEAR = 1900
_MAX_YEAR = 2100
_NATIVE_STATION_KM = 40.0  # station within ~county scale of the centroid


@dataclass(frozen=True)
class CountyCoverage:
    county_fips: str
    state: str
    observed_days_in_window: int
    expected_days_in_window: int
    completeness: float
    is_sparse: bool


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str  # "FAIL" | "WARN"
    count: int
    examples: list[str]


@dataclass(frozen=True)
class CountyProvenance:
    county_fips: str
    state: str
    station_id: str
    provenance_class: str  # native_station | fallback_station_distance_km=N | interpolated_from_neighbors


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(q * (len(ordered) - 1)))))
    return ordered[idx]


@dataclass
class WeatherDataAudit:
    total_observation_rows: int
    distinct_counties: int
    year_min: int | None
    year_max: int | None
    window_start: str
    window_end: str
    expected_days_in_window: int
    min_completeness: float
    per_state: dict[str, dict[str, float]] = field(default_factory=dict)
    missing_counties: dict[str, list[str]] = field(default_factory=dict)
    sparse_counties: list[CountyCoverage] = field(default_factory=list)
    shared_stations: dict[str, list[str]] = field(default_factory=dict)
    duplicate_county_date_rows: int = 0
    findings: list[Finding] = field(default_factory=list)
    county_provenance: list[CountyProvenance] = field(default_factory=list)
    provenance_counts: dict[str, int] = field(default_factory=dict)
    zero_in_window_counties: list[str] = field(default_factory=list)


def _state_of(county_fips: str) -> str:
    return _PREFIX_TO_STATE.get(county_fips[:2], county_fips[:2])


def audit_weather_data(
    observation_rows,
    station_rows,
    *,
    expected_counties_by_state: dict[str, set[str]],
    window_start: date,
    window_end: date,
    min_completeness: float = 0.90,
    county_centroids: dict[str, tuple[float, float]] | None = None,
) -> WeatherDataAudit:
    expected_days = (window_end - window_start).days + 1

    total = 0
    counties: set[str] = set()
    year_min: int | None = None
    year_max: int | None = None
    window_days: dict[str, set[date]] = defaultdict(set)
    station_counties: dict[str, set[str]] = defaultdict(set)
    county_station_rows: dict[str, Counter] = defaultdict(Counter)  # county -> station -> n
    seen_county_date: set[tuple[str, date]] = set()
    duplicates = 0
    fail_examples: dict[str, list[str]] = defaultdict(list)
    fail_counts: Counter = Counter()

    def _flag(check: str, example: str) -> None:
        fail_counts[check] += 1
        if len(fail_examples[check]) < 5:
            fail_examples[check].append(example)

    def _temp(value) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    for row in observation_rows:
        total += 1
        fips = str(row["county_fips"]).zfill(5)
        counties.add(fips)
        station_id = (row.get("station_id") or "").strip()

        # --- FAIL checks (data integrity / plausibility) ---
        if fips[:2] not in _PREFIX_TO_STATE:
            _flag("foreign_fips", fips)
        if not station_id:
            _flag("missing_station", f"{fips}@{row.get('date')}")
        try:
            observed = date.fromisoformat(row["date"][:10])
        except ValueError:
            _flag("out_of_range_date", str(row.get("date")))
            continue
        if not (_MIN_YEAR <= observed.year <= _MAX_YEAR):
            _flag("out_of_range_date", observed.isoformat())
        tmax, tmin = _temp(row.get("tmax_f")), _temp(row.get("tmin_f"))
        for label, t in (("tmax", tmax), ("tmin", tmin)):
            if t is not None and not (_MIN_PLAUSIBLE_F <= t <= _MAX_PLAUSIBLE_F):
                _flag("implausible_temp", f"{fips}@{observed} {label}={t}")
        if (
            tmax is not None and tmin is not None
            and _MIN_PLAUSIBLE_F <= tmax <= _MAX_PLAUSIBLE_F
            and _MIN_PLAUSIBLE_F <= tmin <= _MAX_PLAUSIBLE_F
            and tmin > tmax
        ):
            _flag("tmin_gt_tmax", f"{fips}@{observed} tmin={tmin}>tmax={tmax}")

        year_min = observed.year if year_min is None else min(year_min, observed.year)
        year_max = observed.year if year_max is None else max(year_max, observed.year)
        if station_id:
            station_counties[station_id].add(fips)
            county_station_rows[fips][station_id] += 1
        key = (fips, observed)
        if key in seen_county_date:
            duplicates += 1
        else:
            seen_county_date.add(key)
        if window_start <= observed <= window_end and (tmax is not None or tmin is not None):
            window_days[fips].add(observed)

    # Per-county coverage in the window.
    coverages: list[CountyCoverage] = []
    for fips in sorted(counties):
        observed_days = len(window_days.get(fips, set()))
        completeness = observed_days / expected_days if expected_days else 0.0
        coverages.append(
            CountyCoverage(
                county_fips=fips,
                state=_state_of(fips),
                observed_days_in_window=observed_days,
                expected_days_in_window=expected_days,
                completeness=completeness,
                is_sparse=completeness < min_completeness,
            )
        )

    # Per-state rollup + missing counties (only for states present in the data).
    states_present = {_state_of(f) for f in counties}
    per_state: dict[str, dict[str, float]] = {}
    missing: dict[str, list[str]] = {}
    for state in sorted(states_present):
        state_cov = [c for c in coverages if c.state == state]
        expected_fips = expected_counties_by_state.get(state, set())
        present_fips = {c.county_fips for c in state_cov}
        completes = [c.completeness for c in state_cov]
        per_state[state] = {
            "present": len(present_fips),
            "expected": len(expected_fips) if expected_fips else len(present_fips),
            "mean_completeness": (sum(completes) / len(completes)) if completes else 0.0,
            "p50_completeness": _percentile(completes, 0.50),
            "p05_completeness": _percentile(completes, 0.05),
            "min_completeness": min(completes) if completes else 0.0,
            "sparse_count": sum(1 for c in state_cov if c.is_sparse),
        }
        if expected_fips:
            missing[state] = sorted(expected_fips - present_fips)

    shared = {
        station_id: sorted(fips_set)
        for station_id, fips_set in sorted(station_counties.items())
        if len(fips_set) > 1
    }

    # Coverage provenance per county (native vs fallback distance) when centroids
    # + station coordinates are supplied.
    county_provenance: list[CountyProvenance] = []
    provenance_counts: Counter = Counter()
    station_coords = {
        str(s.get("station_id")): (float(s["latitude"]), float(s["longitude"]))
        for s in station_rows
        if s.get("latitude") not in (None, "") and s.get("longitude") not in (None, "")
    }
    if county_centroids:
        for fips in sorted(counties):
            if not county_station_rows[fips]:
                cls = "interpolated_from_neighbors"
                station_id = ""
            else:
                station_id = county_station_rows[fips].most_common(1)[0][0]
                centroid = county_centroids.get(fips)
                coord = station_coords.get(station_id)
                if centroid and coord:
                    km = _haversine_km(centroid[0], centroid[1], coord[0], coord[1])
                    cls = (
                        "native_station"
                        if km <= _NATIVE_STATION_KM
                        else f"fallback_station_distance_km={round(km)}"
                    )
                else:
                    cls = "native_station"  # no coords to refute; treat as native
            provenance_counts[cls.split("=")[0]] += 1
            county_provenance.append(
                CountyProvenance(fips, _state_of(fips), station_id, cls)
            )

    findings = [
        Finding(check=check, severity="FAIL", count=count,
                examples=fail_examples[check])
        for check, count in sorted(fail_counts.items())
    ]
    zero_in_window = sorted(
        c.county_fips for c in coverages if c.observed_days_in_window == 0
    )

    return WeatherDataAudit(
        total_observation_rows=total,
        distinct_counties=len(counties),
        year_min=year_min,
        year_max=year_max,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        expected_days_in_window=expected_days,
        min_completeness=min_completeness,
        per_state=per_state,
        missing_counties=missing,
        sparse_counties=sorted(
            (c for c in coverages if c.is_sparse), key=lambda c: c.completeness
        ),
        shared_stations=shared,
        duplicate_county_date_rows=duplicates,
        findings=findings,
        county_provenance=county_provenance,
        provenance_counts=dict(provenance_counts),
        zero_in_window_counties=zero_in_window,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _expected_counties_by_state() -> dict[str, set[str]]:
    by_state: dict[str, set[str]] = {state: set() for state in REGIONAL_STATES}
    for location in load_weather_locations():
        by_state[location.state].add(location.county_fips)
    return by_state


def _county_centroids_from_resource() -> dict[str, tuple[float, float]]:
    return {
        loc.county_fips: (loc.centroid_lat, loc.centroid_lon)
        for loc in load_weather_locations()
    }


def _county_centroids_from_csv(path: Path) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for row in _read_csv(path):
        fips = str(row.get("county_fips", "")).zfill(5)
        lat = row.get("centroid_lat") or row.get("intptlat") or row.get("latitude")
        lon = row.get("centroid_lon") or row.get("intptlon") or row.get("longitude")
        if fips and lat and lon:
            out[fips] = (float(lat), float(lon))
    return out


def _roster_from_csv(path: Path) -> dict[str, set[str]]:
    by_state: dict[str, set[str]] = defaultdict(set)
    for row in _read_csv(path):
        fips = str(row.get("county_fips", "")).zfill(5)
        state = row.get("state") or _state_of(fips)
        if fips:
            by_state[state].add(fips)
    return dict(by_state)


def _render(audit: WeatherDataAudit) -> str:
    lines = [
        "NOAA weather data audit",
        f"  observation rows : {audit.total_observation_rows:,}",
        f"  distinct counties: {audit.distinct_counties}",
        f"  year span        : {audit.year_min}..{audit.year_max}",
        f"  fit window       : {audit.window_start}..{audit.window_end} "
        f"({audit.expected_days_in_window} days)",
        f"  duplicate (county,date) rows: {audit.duplicate_county_date_rows}",
        "",
        f"Per-state coverage + mean day-completeness in window "
        f"(sparse = <{audit.min_completeness:.0%}):",
    ]
    for state, stats in audit.per_state.items():
        lines.append(
            f"  {state}: {int(stats['present'])}/{int(stats['expected'])} counties | "
            f"completeness mean {stats['mean_completeness'] * 100:.1f}% "
            f"p50 {stats['p50_completeness'] * 100:.1f}% "
            f"p05 {stats['p05_completeness'] * 100:.1f}% "
            f"min {stats['min_completeness'] * 100:.1f}% | "
            f"sparse {int(stats['sparse_count'])}"
        )
    lines.append("")
    lines.append(f"GATE: counties with ZERO in-window temp: {len(audit.zero_in_window_counties)}")
    if audit.zero_in_window_counties:
        lines.append(f"  {audit.zero_in_window_counties}")
    fails = [f for f in audit.findings if f.severity == "FAIL"]
    lines.append(f"GATE: FAIL findings: {len(fails)}")
    for f in fails:
        lines.append(f"  [FAIL] {f.check}: {f.count} (e.g. {f.examples[:3]})")
    if audit.provenance_counts:
        lines.append("")
        lines.append("Coverage provenance (per county):")
        for cls, n in sorted(audit.provenance_counts.items()):
            lines.append(f"  {cls}: {n}")
    missing_total = sum(len(v) for v in audit.missing_counties.values())
    lines.append("")
    lines.append(f"Missing counties (vs six-state universe): {missing_total}")
    for state, fips in audit.missing_counties.items():
        if fips:
            lines.append(f"  {state}: {fips}")
    lines.append("")
    lines.append(f"Sparse counties (<{audit.min_completeness:.0%} day-complete): "
                 f"{len(audit.sparse_counties)}")
    for c in audit.sparse_counties:
        lines.append(f"  {c.county_fips} ({c.state}): {c.completeness * 100:.1f}%")
    lines.append("")
    lines.append(f"Stations shared across counties (fallback indicator): "
                 f"{len(audit.shared_stations)}")
    for station_id, fips in audit.shared_stations.items():
        lines.append(f"  {station_id}: {fips}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tickbiterisk.etl.weather_data_audit",
        description="Audit acquired NOAA weather observations against the "
        "six-state regional county universe.",
    )
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--stations", type=Path, default=None)
    parser.add_argument("--roster", type=Path, default=None,
                        help="County roster CSV (default: six-state weather resource).")
    parser.add_argument("--centroids", type=Path, default=None,
                        help="County centroid CSV (default: six-state weather resource).")
    parser.add_argument("--window-start", type=date.fromisoformat, default=date(2017, 1, 1),
                        help="Fit-window start (data-driven; set from incidence availability).")
    parser.add_argument("--window-end", type=date.fromisoformat, default=date(2021, 12, 31),
                        help="Fit-window end (data-driven; set from incidence availability).")
    parser.add_argument("--min-completeness", type=float, default=0.90)
    parser.add_argument("--gate", action="store_true",
                        help="Exit non-zero if any FAIL finding or zero-in-window county.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    if not args.observations.is_file():
        parser.error(f"observations file not found: {args.observations}")

    observation_rows = _read_csv(args.observations)
    station_rows = _read_csv(args.stations) if args.stations and args.stations.is_file() else []
    expected = _roster_from_csv(args.roster) if args.roster else _expected_counties_by_state()
    centroids = (
        _county_centroids_from_csv(args.centroids)
        if args.centroids
        else _county_centroids_from_resource()
    )

    audit = audit_weather_data(
        observation_rows,
        station_rows,
        expected_counties_by_state=expected,
        window_start=args.window_start,
        window_end=args.window_end,
        min_completeness=args.min_completeness,
        county_centroids=centroids,
    )

    if args.json:
        payload = asdict(audit)
        payload["sparse_counties"] = [asdict(c) for c in audit.sparse_counties]
        payload["county_provenance"] = [asdict(c) for c in audit.county_provenance]
        payload["findings"] = [asdict(f) for f in audit.findings]
        print(json.dumps(payload, indent=2))
    else:
        print(_render(audit))

    if args.gate:
        fails = [f for f in audit.findings if f.severity == "FAIL"]
        if fails or audit.zero_in_window_counties:
            print(
                f"\nGATE FAILED: {len(fails)} FAIL finding(s), "
                f"{len(audit.zero_in_window_counties)} zero-in-window county(ies).",
                file=sys.stderr,
            )
            return 1
        print("\nGATE PASSED: no FAIL findings, zero 0%-in-window counties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
