#!/usr/bin/env python3
"""Within-segment weather->incidence signal check (exploratory, rank-normalized).

cc_tasks/2026-06-01_within-segment-weather-signal-check.md. Read-only w.r.t. the
model: inspects the weather->incidence relationship within each definition-stable
segment on the ordinal (rank-normalized, protocol-invariant) scale and reports
evidence. Does NOT build a forecaster or any cross-segment blend.

Inputs (located, not rebuilt):
  - Incidence: build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv
    (Option-A CDC-dashboard zero-suppression basis; incidence_per_100k + population
    already present).
  - Weather: build/etl/noaa-regional-1992-2026-validated/noaa_ghcnd_daily_observations.csv
  - Feature/lag definitions: config/signal_check.toml

Usage:
  python scripts/within_segment_signal_check.py [--out cc_tasks/..._RESULTS.md]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import tomllib
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INCIDENCE = REPO / "build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"
WEATHER = REPO / "build/etl/noaa-regional-1992-2026-validated/noaa_ghcnd_daily_observations.csv"
CONFIG = REPO / "config/signal_check.toml"
STATE_OF = {"10": "DE", "11": "DC", "24": "MD", "42": "PA", "51": "VA", "54": "WV"}


def load_config():
    with CONFIG.open("rb") as f:
        return tomllib.load(f)["signal_check"]


# ---- incidence (Option-A) ---------------------------------------------------

def load_incidence(states):
    inc = {}  # (fips, year) -> incidence_per_100k
    missing = []
    with INCIDENCE.open() as f:
        for r in csv.DictReader(f):
            fips = str(r["county_fips"]).zfill(5)
            if STATE_OF.get(fips[:2]) not in states:
                continue
            year = int(r["year"])
            if not (2016 <= year <= 2023):
                continue
            flags = r.get("feature_quality_flags", "")
            if "cdc_dashboard_total_cases" not in flags:
                raise SystemExit(f"FAIL: non-Option-A incidence row {fips}/{year}")
            val = r.get("incidence_per_100k")
            if val in (None, "") or not r.get("population"):
                missing.append((fips, year))
                continue
            inc[(fips, year)] = float(val)
    return inc, missing


# ---- weather features (config-driven) ---------------------------------------

def build_weather_features(cfg):
    feats = cfg["features"]
    gdd_base = feats["gdd_base_f"]
    warm_months = set(feats["warm_season_months"])
    onset_thr = feats["spring_onset_mean_f"]
    onset_run = feats["spring_onset_run_days"]
    freeze_thr = feats["hard_freeze_tmin_f"]
    cold_months = set(feats["cold_season_months"])
    include_precip = feats["include_precip"]

    # (fips, year) -> ordered dict day->(mean_temp, tmin, prcp)
    daily: dict[tuple[str, int], dict[date, tuple]] = defaultdict(dict)
    with WEATHER.open() as f:
        for r in csv.DictReader(f):
            y = int(r["date"][:4])
            if not (2016 <= y <= 2023):
                continue
            fips = str(r["county_fips"]).zfill(5)
            d = date.fromisoformat(r["date"][:10])
            tmax = r["tmax_f"]
            tmin = r["tmin_f"]
            prcp = r["prcp_inches"]
            mean = None
            if tmax not in (None, "") and tmin not in (None, ""):
                mean = (float(tmax) + float(tmin)) / 2.0
            tmin_v = float(tmin) if tmin not in (None, "") else None
            prcp_v = float(prcp) if prcp not in (None, "") else None
            daily[(fips, y)][d] = (mean, tmin_v, prcp_v)

    out = {}  # (fips, year) -> feature dict
    for key, series in daily.items():
        days = sorted(series)
        gdd = 0.0
        warm_precip = 0.0
        freeze_days = 0
        for d in days:
            mean, tmin_v, prcp_v = series[d]
            if d.month in warm_months and mean is not None:
                gdd += max(mean - gdd_base, 0.0)
            if include_precip and d.month in warm_months and prcp_v is not None:
                warm_precip += prcp_v
            if d.month in cold_months and tmin_v is not None and tmin_v <= freeze_thr:
                freeze_days += 1
        # spring onset: first day starting a run of >= onset_run days with mean >= thr
        onset_doy = None
        run = 0
        for d in days:
            mean = series[d][0]
            if mean is not None and mean >= onset_thr:
                run += 1
                if run >= onset_run:
                    onset_doy = (d - date(d.year, 1, 1)).days + 1 - (onset_run - 1)
                    break
            else:
                run = 0
        f = {
            "gdd_base50_warm": gdd,
            "winter_hard_freeze_days": float(freeze_days),
            "spring_onset_doy": float(onset_doy) if onset_doy is not None else None,
        }
        if include_precip:
            f["warm_season_precip_in"] = warm_precip
        out[key] = f
    return out


# ---- stats ------------------------------------------------------------------

def _rank(values):
    # average ranks (1..n), ties averaged
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def within_county_rank_pairs(panel):
    """panel: {county: [(feature, incidence), ...]} -> pooled within-county ranks."""
    fx, fy, county_of = [], [], []
    for county, pairs in panel.items():
        if len(pairs) < 2:
            continue
        feats = [p[0] for p in pairs]
        incs = [p[1] for p in pairs]
        fr = _rank(feats)
        ir = _rank(incs)
        fx.extend(fr)
        fy.extend(ir)
        county_of.extend([county] * len(pairs))
    return fx, fy, county_of


def pooled_spearman(panel):
    fx, fy, _ = within_county_rank_pairs(panel)
    return _pearson(fx, fy), len(fx)


def bootstrap_ci(panel, n_boot=1000, seed_stride=2654435761):
    """Bootstrap over counties (deterministic LCG, no Math.random) for a 90% CI."""
    counties = list(panel.keys())
    if not counties:
        return (float("nan"), float("nan"))
    estimates = []
    state = 12345
    for _ in range(n_boot):
        sample = {}
        for i in range(len(counties)):
            state = (1103515245 * state + 12345) % (2**31)
            c = counties[state % len(counties)]
            # allow same county multiple times under a synthetic key
            sample[f"{c}#{i}"] = panel[c]
        rho, _n = pooled_spearman(sample)
        if not math.isnan(rho):
            estimates.append(rho)
    if not estimates:
        return (float("nan"), float("nan"))
    estimates.sort()
    lo = estimates[int(0.05 * len(estimates))]
    hi = estimates[min(len(estimates) - 1, int(0.95 * len(estimates)))]
    return (lo, hi)


def loo_year_stability(inc, wx, feature, lag, seg):
    """Leave-one-year-out pooled-Spearman per dropped year + sign-stability verdict.

    Reusable across signal-check scripts. Only meaningful for segments with >= 5
    years; callers gate on segment length.
    """
    loo = []
    for drop in range(seg["start_year"], seg["end_year"] + 1):
        p2 = defaultdict(list)
        for yy in range(seg["start_year"], seg["end_year"] + 1):
            if yy == drop:
                continue
            for (fips, iy), incidence in inc.items():
                if iy != yy:
                    continue
                fv = wx.get((fips, yy - lag), {}).get(feature)
                if fv is not None:
                    p2[fips].append((fv, incidence))
        r2, _ = pooled_spearman(dict(p2))
        loo.append(None if math.isnan(r2) else round(r2, 4))
    signs = {(-1 if v < 0 else 1) for v in loo if v is not None}
    stability = "stable_sign" if len(signs) == 1 else "sign_flips"
    return loo, stability


def build_panel(inc, wx, feature, lag, seg):
    """{county: [(feature_value(year-lag), incidence(year)), ...]} over segment years."""
    panel = defaultdict(list)
    for year in range(seg["start_year"], seg["end_year"] + 1):
        for (fips, iy), incidence in inc.items():
            if iy != year:
                continue
            fkey = (fips, year - lag)
            fv = wx.get(fkey, {}).get(feature)
            if fv is None:
                continue
            panel[fips].append((fv, incidence))
    return dict(panel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=REPO / "cc_tasks/2026-06-01_within-segment-weather-signal-check_RESULTS.md")
    ap.add_argument("--json-out", type=Path,
                    default=REPO / "build/signal_check_results.json")
    args = ap.parse_args()

    cfg = load_config()
    states = cfg["states"]
    inc, inc_missing = load_incidence(states)
    wx = build_weather_features(cfg)

    # ---- join coverage (fail loud, do not silent inner-join) ----
    inc_counties = {f for (f, y) in inc}
    wx_counties = {f for (f, y) in wx}
    inc_no_weather = sorted(inc_counties - wx_counties)
    weather_no_inc = sorted(wx_counties - inc_counties)

    results = {
        "segments": {},
        "join": {
            "incidence_counties": len(inc_counties),
            "weather_counties": len(wx_counties),
            "incidence_without_weather": inc_no_weather,
            "weather_without_incidence": weather_no_inc,
            "incidence_missing_value_county_years": [f"{f}/{y}" for f, y in inc_missing],
        },
        "feature_coverage": {},
    }

    features = ["gdd_base50_warm", "spring_onset_doy", "winter_hard_freeze_days"]
    if cfg["features"]["include_precip"]:
        features.append("warm_season_precip_in")

    for seg in cfg["segments"]:
        sname = seg["name"]
        results["segments"][sname] = {"n_years": seg["end_year"] - seg["start_year"] + 1, "lags": {}}
        for lag in cfg["lags"]:
            lag_block = {}
            for feature in features:
                panel = build_panel(inc, wx, feature, lag, seg)
                rho, n_pairs = pooled_spearman(panel)
                lo, hi = bootstrap_ci(panel)
                entry = {
                    "spearman_rho": None if math.isnan(rho) else round(rho, 4),
                    "n_county_year_pairs": n_pairs,
                    "n_counties": len(panel),
                    "ci90": [None if math.isnan(lo) else round(lo, 4),
                             None if math.isnan(hi) else round(hi, 4)],
                }
                # within-segment stability
                if seg["end_year"] - seg["start_year"] + 1 >= 5:
                    loo, stability = loo_year_stability(inc, wx, feature, lag, seg)
                    entry["loo_year_rho"] = loo
                    entry["stability"] = stability
                else:
                    entry["stability"] = "INDETERMINATE_n2"  # n=2: cannot support a stability claim
                lag_block[feature] = entry
            results["segments"][sname]["lags"][f"lag{lag}"] = lag_block

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    main()
