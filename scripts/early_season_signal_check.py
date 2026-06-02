#!/usr/bin/env python3
"""Early-season sustained-warmth signal check (follow-on hypothesis test).

cc_tasks/2026-06-01_early-season-warmth-signal-check.md. Tests whether sustained
early-season warmth (a blind spot of the first signal check) rank-associates with
annual Lyme incidence within definition-stable segments. NEW-HYPOTHESIS test, not
a re-run for a better number — a weak result is a real finding.

Grounding: Eisen, Eisen, Ogden & Beard 2016, J Med Entomol 53(2):250-61,
DOI 10.1093/jme/tjv199 (I. scapularis). Nymphal activity-onset is a RANGE, so the
feature is evaluated across a pre-committed threshold grid (NOT one value), and
EVERY grid cell is reported — never the max-correlation cell.

REUSES the accepted machinery from within_segment_signal_check.py (rank,
pooled Spearman, bootstrap CI, LOO stability, join-coverage, Option-A incidence
load). Adds ONLY the early-season feature family + the grid loop.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from within_segment_signal_check import (  # noqa: E402  (sibling-script reuse)
    REPO,
    WEATHER,
    bootstrap_ci,
    build_panel,
    load_config,
    load_incidence,
    loo_year_stability,
    pooled_spearman,
)


def build_early_season_features(cfg):
    es = cfg["early_season"]
    cutoff = es["cutoff_doy"]
    win0, win1 = es["run_window_start_doy"], es["run_window_end_doy"]
    thr_grid_c = es["threshold_grid_c"]
    run_days_grid = es["run_days_grid"]
    thr_grid_f = {c: c * 9.0 / 5.0 + 32.0 for c in thr_grid_c}
    max_doy = max(cutoff, win1)

    # (fips, year) -> {doy: mean_f}, only days up to max_doy
    daily: dict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    with WEATHER.open() as f:
        import csv
        for r in csv.DictReader(f):
            y = int(r["date"][:4])
            if not (2016 <= y <= 2023):
                continue
            tmax, tmin = r["tmax_f"], r["tmin_f"]
            if tmax in (None, "") or tmin in (None, ""):
                continue
            d = date.fromisoformat(r["date"][:10])
            doy = (d - date(y, 1, 1)).days + 1
            if doy > max_doy:
                continue
            daily[(str(r["county_fips"]).zfill(5), y)][doy] = (float(tmax) + float(tmin)) / 2.0

    out = {}
    for key, series in daily.items():
        feats = {}
        # Feature A: cumulative early-season GDD through cutoff, base = each threshold.
        for c in thr_grid_c:
            base = thr_grid_f[c]
            feats[f"early_season_gdd_b{c}"] = sum(
                max(m - base, 0.0) for doy, m in series.items() if doy <= cutoff
            )
        # Feature B: solid early-warm runs within [win0, win1]. A run breaks on a
        # missing day or a below-threshold day (consecutive calendar days).
        for c in thr_grid_c:
            thr = thr_grid_f[c]
            run = 0
            runs = []  # lengths of completed runs
            for doy in range(win0, win1 + 1):
                m = series.get(doy)
                if m is not None and m >= thr:
                    run += 1
                else:
                    if run:
                        runs.append(run)
                    run = 0
            if run:
                runs.append(run)
            for rd in run_days_grid:
                qualifying = [r for r in runs if r >= rd]
                feats[f"early_warm_run_count_t{c}_r{rd}"] = float(len(qualifying))
                feats[f"early_warm_run_days_t{c}_r{rd}"] = float(sum(qualifying))
        out[key] = feats
    return out, thr_grid_c, run_days_grid


def main():
    cfg = load_config()
    states = cfg["states"]
    inc, inc_missing = load_incidence(states)
    wx, thr_grid_c, run_days_grid = build_early_season_features(cfg)

    inc_counties = {f for f, _ in inc}
    wx_counties = {f for f, _ in wx}

    # Feature name lists per family.
    gdd_feats = [f"early_season_gdd_b{c}" for c in thr_grid_c]
    count_feats = [f"early_warm_run_count_t{c}_r{rd}" for c in thr_grid_c for rd in run_days_grid]
    days_feats = [f"early_warm_run_days_t{c}_r{rd}" for c in thr_grid_c for rd in run_days_grid]
    families = {
        "early_season_gdd": gdd_feats,
        "early_warm_run_count": count_feats,
        "early_warm_run_days": days_feats,
    }

    results = {
        "join": {
            "incidence_counties": len(inc_counties),
            "weather_counties": len(wx_counties),
            "incidence_without_weather": sorted(inc_counties - wx_counties),
            "weather_without_incidence": sorted(wx_counties - inc_counties),
            "incidence_missing_value_county_years": [f"{f}/{y}" for f, y in inc_missing],
        },
        "grid_axes": {"threshold_grid_c": thr_grid_c, "run_days_grid": run_days_grid},
        "segments": {},
    }

    for seg in cfg["segments"]:
        sname = seg["name"]
        five_yr = seg["end_year"] - seg["start_year"] + 1 >= 5
        results["segments"][sname] = {"lags": {}}
        for lag in cfg["lags"]:
            cells = {}
            for fam, names in families.items():
                for feature in names:
                    panel = build_panel(inc, wx, feature, lag, seg)
                    rho, n_pairs = pooled_spearman(panel)
                    lo, hi = bootstrap_ci(panel)
                    cell = {
                        "family": fam,
                        "rho": None if math.isnan(rho) else round(rho, 4),
                        "ci90": [None if math.isnan(lo) else round(lo, 4),
                                 None if math.isnan(hi) else round(hi, 4)],
                        "n_pairs": n_pairs,
                        "n_counties": len(panel),
                    }
                    if five_yr:
                        loo, stab = loo_year_stability(inc, wx, feature, lag, seg)
                        cell["loo_year_rho"] = loo
                        cell["stability"] = stab
                    else:
                        cell["stability"] = "INDETERMINATE_n2"
                    cells[feature] = cell
            results["segments"][sname]["lags"][f"lag{lag}"] = cells

    out_json = REPO / "build/early_season_signal_check_results.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2))

    # Console grid summary (per family x segment x lag: range across the grid).
    for sname, sblock in results["segments"].items():
        for lag, cells in sblock["lags"].items():
            for fam in families:
                rhos = [c["rho"] for c in cells.values() if c["family"] == fam and c["rho"] is not None]
                stabs = [c.get("stability") for c in cells.values() if c["family"] == fam]
                if rhos:
                    rhos_sorted = sorted(rhos)
                    med = rhos_sorted[len(rhos_sorted) // 2]
                    stable = sum(1 for s in stabs if s == "stable_sign")
                    print(f"{sname} {lag} {fam:22s} grid n={len(rhos)} "
                          f"rho[min/med/max]={min(rhos):+.3f}/{med:+.3f}/{max(rhos):+.3f} "
                          f"stable_sign_cells={stable}/{len(stabs)}")
    print(f"\nwrote {out_json}")
    return results


if __name__ == "__main__":
    main()
