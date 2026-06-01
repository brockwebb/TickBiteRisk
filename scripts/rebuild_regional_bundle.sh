#!/usr/bin/env bash
# rebuild_regional_bundle.sh
#
# Deterministic, provenance-stamped rebuild + self-verify of the regional
# research dashboard bundle (the public/research-data/regional/ JSON/GeoJSON
# set). Think "rebuild and relaunch a container": build from a known commit,
# stamp what made it, verify before anyone deploys.
#
# WHAT IT DOES
#   1. Refuses to run on a dirty working tree (unless --allow-dirty) so a build
#      is always reproducible from a named commit.
#   2. Captures the producing commit (sha, time, branch, dirty flag).
#   3. Regenerates the regional county-week risk scores CSV from the on-disk
#      multi-year annual-forecast CSVs, then builds the regional research
#      asset bundle. (The asset/score layer is what changes most often; the
#      upstream multi-year annual forecast is consumed as a fixed input -- see
#      "SCOPE / PREREQUISITES" below.)
#   4. Stamps a build_provenance block into model_card.json AND
#      static_export_manifest.json in the freshly built bundle. This is what
#      permanently kills the "is the bundle fresh?" guessing game: every bundle
#      henceforth self-reports the commit that produced it.
#   5. Runs `seldon verify` and aborts if it fails.
#   6. Runs a self-check against the freshly built bundle: confirms the recorded
#      annual prediction/interval source SHAs match the on-disk source CSVs
#      (build wired the right source), and runs a contract check (files present,
#      weekly per-record keys, county_fips flow geojson<->weekly).
#   7. Prints "READY TO DEPLOY (commit <sha>)" or "BLOCKED: <reason>".
#   8. Does NOT deploy or push. Build-and-verify only; deploy stays a separate,
#      human-gated step (repo has a no-auto-publish posture).
#
# SCOPE / PREREQUISITES (read this before assuming a clean rebuild == fresh data)
#   This script rebuilds the SCORE + ASSET layer from these on-disk inputs:
#     - build/etl/regional-annual-forecast-multiyear/regional_annual_forecast_predictions.csv
#     - build/etl/regional-annual-forecast-multiyear/regional_annual_forecast_intervals.csv
#   Those multi-year (2024/2025/2026) forecast CSVs are themselves produced by an
#   upstream ETL chain whose multi-year combine step is NOT currently documented
#   in README.md (only the single-year `etl regional-annual-forecast --target-year
#   2026` recipe is). If the forecast modeling code changes, you must regenerate
#   those CSVs first; this script will detect that the recorded source SHAs no
#   longer match and report it, but it does not itself rebuild the forecast.
#   If a required input is missing, the script BLOCKS rather than fabricating it.
#
# USAGE
#   scripts/rebuild_regional_bundle.sh [--output-dir DIR] [--allow-dirty]
#   Default --output-dir is a scratch path; it NEVER writes the deployed bundle.
#   To promote a verified build, a human copies DIR -> public/research-data/regional/.

set -euo pipefail

# ---- resolve repo root (script lives in scripts/) ----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ---- defaults / args ---------------------------------------------------------
OUTPUT_DIR="build/regional-bundle-rebuild"   # scratch by default; not the deployed path
ALLOW_DIRTY=0
PY="python -m tickbiterisk.cli"

while [ $# -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "BLOCKED: unknown argument '$1'"; exit 2 ;;
  esac
done

block() { echo "BLOCKED: $1" >&2; exit 1; }

# ---- fixed inputs (README regional recipe) -----------------------------------
PRED="build/etl/regional-annual-forecast-multiyear/regional_annual_forecast_predictions.csv"
INTV="build/etl/regional-annual-forecast-multiyear/regional_annual_forecast_intervals.csv"
SEASON="build/etl/seasonality/seasonality_baseline.csv"
COUNTIES="build/etl/regional-county-adjacency/regional_counties.geojson"
INCID="build/etl/regional-incidence/midatlantic_lyme_incidence_county_year.csv"
REGIME_SUMMARY="build/etl/regional-annual-forecast/regional_spatial_regime_forecast_interval_summary.csv"
OBSFIT="build/etl/regional-forecast-observed-fit/regional_forecast_observed_fit_comparisons.csv"
TYP="build/etl/regional-forecast-typicality/regional_forecast_typicality.csv"
MODEL_NAME="empirical_bayes_spatial_regime_incidence"
SCORES_OUT="${OUTPUT_DIR}/regional-county-week-risk"

# ---- 1. clean-tree gate ------------------------------------------------------
if [ -n "$(git status --porcelain)" ] && [ "${ALLOW_DIRTY}" -ne 1 ]; then
  block "working tree is dirty; commit/stash first or pass --allow-dirty (a rebuild should be reproducible from a known commit)"
fi

# ---- 2. capture producing commit --------------------------------------------
GIT_COMMIT="$(git rev-parse HEAD)"
GIT_COMMIT_TIME="$(git log -1 --format=%cI HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ -n "$(git status --porcelain)" ]; then DIRTY=true; else DIRTY=false; fi
BUILT_AT="$(python -c 'import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())')"
echo "==> rebuild from commit ${GIT_COMMIT} (${BRANCH}, dirty=${DIRTY})"

# ---- input presence gate (do not fabricate inputs) ---------------------------
for f in "$PRED" "$INTV" "$SEASON" "$COUNTIES" "$INCID" "$REGIME_SUMMARY" "$OBSFIT" "$TYP"; do
  [ -f "$f" ] || block "missing required input: $f (regenerate the upstream ETL first)"
done

# ---- 3. regenerate score CSV, then build the asset bundle --------------------
mkdir -p "${OUTPUT_DIR}"
echo "==> regenerating regional county-week risk scores -> ${SCORES_OUT}"
${PY} etl county-week-risk \
  --predictions-path "$PRED" \
  --prediction-intervals-path "$INTV" \
  --seasonality-baseline-path "$SEASON" \
  --model-name "$MODEL_NAME" \
  --output-dir "$SCORES_OUT" --replace

echo "==> building regional research assets -> ${OUTPUT_DIR}"
${PY} dashboard build-regional-research-assets \
  --scores-path "${SCORES_OUT}/county_week_seasonal_risk_baseline.csv" \
  --regional-counties-geojson-path "$COUNTIES" \
  --regional-incidence-path "$INCID" \
  --spatial-regime-summary-path "$REGIME_SUMMARY" \
  --regional-annual-forecast-path "$PRED" \
  --regional-forecast-observed-fit-path "$OBSFIT" \
  --regional-forecast-typicality-path "$TYP" \
  --output-dir "${OUTPUT_DIR}"

# ---- 4. stamp build provenance ----------------------------------------------
# Self-reporting provenance is the durable fix for freshness guessing: every
# bundle now records the exact commit/time/branch that produced it.
echo "==> stamping build_provenance into model_card.json + static_export_manifest.json"
GIT_COMMIT="$GIT_COMMIT" GIT_COMMIT_TIME="$GIT_COMMIT_TIME" BUILT_AT="$BUILT_AT" \
BRANCH="$BRANCH" DIRTY="$DIRTY" OUTPUT_DIR="$OUTPUT_DIR" python - <<'PY'
import json, os
prov = {
    "git_commit": os.environ["GIT_COMMIT"],
    "git_commit_time": os.environ["GIT_COMMIT_TIME"],
    "built_at": os.environ["BUILT_AT"],
    "branch": os.environ["BRANCH"],
    "dirty": os.environ["DIRTY"] == "true",
}
out = os.environ["OUTPUT_DIR"]
for name in ("model_card.json", "static_export_manifest.json"):
    p = os.path.join(out, name)
    with open(p) as f:
        doc = json.load(f)
    doc["build_provenance"] = prov
    with open(p, "w") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")
print("   stamped:", prov)
PY

# ---- 5. seldon verify gate ---------------------------------------------------
echo "==> seldon verify"
if ! seldon verify --quiet; then
  block "seldon verify failed (project integrity check); not ready to deploy"
fi

# ---- 6. self-check: source-SHA match + contract ------------------------------
echo "==> self-check (source SHA + data contract)"
OUTPUT_DIR="$OUTPUT_DIR" PRED="$PRED" INTV="$INTV" python - <<'PY' || { echo "BLOCKED: self-check failed"; exit 1; }
import json, os, hashlib, sys
out = os.environ["OUTPUT_DIR"]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

mc = json.load(open(os.path.join(out, "model_card.json")))
src = mc.get("annual_prediction_source", {})
ok = True
# (a) the bundle's recorded source SHAs must match the on-disk source CSVs it claims to be built from
if src.get("sha256") != sha(os.environ["PRED"]):
    print("   FAIL: prediction source sha mismatch"); ok = False
if src.get("interval_sha256") != sha(os.environ["INTV"]):
    print("   FAIL: interval source sha mismatch"); ok = False

# (b) contract: required files present + weekly record keys + county_fips flow
weekly = json.load(open(os.path.join(out, "regional_county_risk_weekly.json")))
counties = json.load(open(os.path.join(out, "regional_counties.geojson")))
recs = weekly["records"]
req = ["county_fips", "mmwr_week", "risk_score", "risk_category",
       "predicted_weekly_incidence_per_100k",
       "predicted_weekly_incidence_80_interval",
       "predicted_weekly_incidence_95_interval",
       "predicted_annual_incidence_per_100k"]
miss = sum(1 for r in recs for k in req if k not in r or r[k] is None)
if miss:
    print(f"   FAIL: {miss} missing required weekly fields"); ok = False
A = {str(f["properties"]["county_fips"]) for f in counties["features"]}
B = {str(r["county_fips"]) for r in recs}
no_weekly = A - B
orphan = B - A
if orphan:
    print(f"   FAIL: {len(orphan)} weekly orphan FIPS not in geojson"); ok = False
sd = (weekly.get("score_scale") or {}).get("score_denominator")
if not (isinstance(sd, (int, float)) and sd > 0):
    print("   FAIL: score_denominator not a positive number"); ok = False

if ok:
    print(f"   source SHA: MATCH | contract: PASS | weekly={len(recs)} |A|={len(A)} |B|={len(B)} "
          f"counties-without-forecast={len(no_weekly)}")
    print("   CURRENT (built bundle is internally consistent and matches its declared source)")
sys.exit(0 if ok else 1)
PY

# ---- 7. final line -----------------------------------------------------------
echo ""
echo "READY TO DEPLOY (commit ${GIT_COMMIT})"
echo "  built bundle: ${OUTPUT_DIR}"
echo "  to deploy (human-gated): cp -r ${OUTPUT_DIR}/* public/research-data/regional/  # then commit"
