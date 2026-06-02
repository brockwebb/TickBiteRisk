#!/usr/bin/env python3
"""70 F unseasonable-early-warm-spell magnitude signal check (third check).

cc_tasks/2026-06-01_warm70-county-magnitude-check.md. Tests whether a rare,
high-threshold (>=70 F daily-MAX), sustained (>=5-day) early-season warm spell
associates with annual Lyme-incidence MAGNITUDE, three pre-committed forms, on
the existing six-state county panel.

HONEST FRAMING (encoded here and in RESULTS): early-season warmth is mechanically
a TIMING signal — the spring questing nymph cohort's SIZE was set the prior year.
So a lag-0 association is confound-suspect by construction; only lag-1 is
mechanically coherent for magnitude. The one thing new vs. the early-season GDD
check: a >=70 F sustained spell captures an anomalous heat EVENT, not "generally
warmer spring" (a place-proxy) — a different confound profile, not a removed lag
mismatch. EVERY form x lag x segment is reported (no winner cell).

REUSES the accepted machinery (rank / pooled Spearman / bootstrap CI / LOO /
join / n=2 gate) from within_segment_signal_check.py via import; only the three
feature definitions + the config block are new.
"""

from __future__ import annotations

import csv
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

FORMS = ["warm70_onset_doy", "warm70_spell_count", "warm70_presence"]


def build_warm70_features(cfg):
    w = cfg["warm70"]
    thr = w["threshold_max_f"]
    run_days = w["run_days"]
    win0, win1 = w["window_start_doy"], w["window_end_doy"]
    no_spell_onset = win1 + 1  # sentinel: "no early hot spell" ranks latest

    # (fips, year) -> {doy: tmax_f} within [win0, win1]
    daily: dict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    with WEATHER.open() as f:
        for r in csv.DictReader(f):
            y = int(r["date"][:4])
            if not (2016 <= y <= 2023):
                continue
            tmax = r["tmax_f"]
            if tmax in (None, ""):
                continue
            d = date.fromisoformat(r["date"][:10])
            doy = (d - date(y, 1, 1)).days + 1
            if win0 <= doy <= win1:
                daily[(str(r["county_fips"]).zfill(5), y)][doy] = float(tmax)

    out = {}
    for key, series in daily.items():
        # Walk the window in calendar order; a spell is a run of >= run_days
        # consecutive in-window days with tmax >= threshold.
        spells = []  # (start_doy, length)
        run = 0
        run_start = None
        for doy in range(win0, win1 + 1):
            t = series.get(doy)
            if t is not None and t >= thr:
                if run == 0:
                    run_start = doy
                run += 1
            else:
                if run >= run_days:
                    spells.append((run_start, run))
                run = 0
        if run >= run_days:
            spells.append((run_start, run))

        onset = spells[0][0] if spells else no_spell_onset
        out[key] = {
            "warm70_onset_doy": float(onset),
            "warm70_spell_count": float(len(spells)),
            "warm70_presence": 1.0 if spells else 0.0,
        }
    return out


def main():
    cfg = load_config()
    inc, inc_missing = load_incidence(cfg["states"])
    wx = build_warm70_features(cfg)

    inc_counties = {f for f, _ in inc}
    wx_counties = {f for f, _ in wx}
    results = {
        "join": {
            "incidence_counties": len(inc_counties),
            "weather_counties": len(wx_counties),
            "incidence_without_weather": sorted(inc_counties - wx_counties),
            "weather_without_incidence": sorted(wx_counties - inc_counties),
            "incidence_missing_value_county_years": [f"{f}/{y}" for f, y in inc_missing],
        },
        "config": cfg["warm70"],
        "segments": {},
    }

    for seg in cfg["segments"]:
        sname = seg["name"]
        five_yr = seg["end_year"] - seg["start_year"] + 1 >= 5
        results["segments"][sname] = {"lags": {}}
        for lag in cfg["lags"]:
            block = {}
            for form in FORMS:
                panel = build_panel(inc, wx, form, lag, seg)
                rho, n_pairs = pooled_spearman(panel)
                lo, hi = bootstrap_ci(panel)
                entry = {
                    "rho": None if math.isnan(rho) else round(rho, 4),
                    "ci90": [None if math.isnan(lo) else round(lo, 4),
                             None if math.isnan(hi) else round(hi, 4)],
                    "n_pairs": n_pairs,
                    "n_counties": len(panel),
                }
                if five_yr:
                    loo, stab = loo_year_stability(inc, wx, form, lag, seg)
                    entry["loo_year_rho"] = loo
                    entry["stability"] = stab
                else:
                    entry["stability"] = "INDETERMINATE_n2"
                block[form] = entry
            results["segments"][sname]["lags"][f"lag{lag}"] = block

    out_json = REPO / "build/warm70_signal_check_results.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2))

    for sname, sblock in results["segments"].items():
        for lag, block in sblock["lags"].items():
            for form, e in block.items():
                print(f"{sname} {lag} {form:20s} rho={e['rho']!s:>8} ci90={e['ci90']} "
                      f"n={e['n_pairs']} cty={e['n_counties']} stab={e['stability']}")
    print(f"\njoin: inc={results['join']['incidence_counties']} wx={results['join']['weather_counties']} "
          f"no-weather={results['join']['incidence_without_weather']} "
          f"missing={len(results['join']['incidence_missing_value_county_years'])}")
    print(f"wrote {out_json}")
    return results


if __name__ == "__main__":
    main()
