#!/usr/bin/env bash
# rebuild_and_publish_regional_bundle.sh
#
# Full-automation path for the regional bundle: regen -> validate -> TEVV
# materiality report -> promote -> commit, with NO routine human gate. This is
# the automated wrapper around scripts/rebuild_regional_bundle.sh; it does NOT
# replace or weaken any of that script's gates -- it removes only the manual
# "copy the 11 files" step, and adds a by-exception TEVV report.
#
# SAFETY MODEL (read before wiring this anywhere that publishes)
#   * The inner rebuild_regional_bundle.sh is the SOLE gate before ship: it runs
#     the clean-tree caveat, input-presence check, build, source-SHA match,
#     data contract, file-set check, and `seldon verify`. ANY of those failing
#     exits non-zero and ABORTS this wrapper BEFORE promotion. No commit on red.
#   * Promotion copies ONLY the explicit 11 BUNDLE_FILES (never the intermediate
#     score CSVs) and is all-or-nothing: the prior public bundle is backed up
#     and restored if any copy fails, so the public dir is never half-updated.
#   * The TEVV materiality report (committed outside the validated 11-file set,
#     under reports/) is the human-by-exception surface: normal runs auto-ship;
#     a REVIEW_RECOMMENDED banner flags material change for after-the-fact review.
#   * This script COMMITS LOCALLY ONLY. It does NOT push and does NOT deploy.
#
# TODO(publish-trigger): wiring this to Pages (CI-on-merge or cron) is a
#   SEPARATE decision Brock makes after reviewing this machinery. Do not add a
#   push/deploy step here without that explicit go.
#
# USAGE
#   scripts/rebuild_and_publish_regional_bundle.sh [--dry-run] [--allow-dirty]
#     --dry-run     build + validate + write the TEVV report, but do NOT promote
#                   or commit (prints what WOULD be promoted). Safe to run anytime.
#     --allow-dirty forwarded to the inner rebuild (a rebuild should normally run
#                   from a clean, named commit).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

DRY_RUN=0
ALLOW_DIRTY_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --allow-dirty) ALLOW_DIRTY_ARG="--allow-dirty"; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "BLOCKED: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

abort() { echo "BLOCKED: $1" >&2; exit 1; }

SCRATCH="build/regional-bundle-rebuild"
DEPLOYED_DIR="public/research-data/regional"
REPORT_DIR="reports/regional-bundle-tevv"
REPORT_MD="${REPORT_DIR}/regional_bundle_tevv_report.md"
REPORT_JSON="${REPORT_DIR}/regional_bundle_tevv_report.json"
PY="python -m tickbiterisk.cli"

# The exact 11 deployed-bundle files (mirror of rebuild_regional_bundle.sh's
# BUNDLE_FILES). Promotion copies ONLY these; never glob, never the score CSVs.
BUNDLE_FILES=(
  model_card.json
  regional_counties.geojson
  regional_county_incidence_annual.json
  regional_states.geojson
  regional_county_metadata.json
  regional_county_risk_weekly.json
  regional_forecast_observed_fit.json
  regional_forecast_typicality.json
  regional_spatial_regime_overlays.json
  source_catalog.json
  static_export_manifest.json
)

# ---- 1. inner rebuild (the blocking gate) -----------------------------------
echo "==> running gated rebuild (scripts/rebuild_regional_bundle.sh)"
if ! "${SCRIPT_DIR}/rebuild_regional_bundle.sh" --output-dir "${SCRATCH}" ${ALLOW_DIRTY_ARG}; then
  abort "gated rebuild failed (see BLOCKED reason above); no promotion, no commit"
fi
for f in "${BUNDLE_FILES[@]}"; do
  [ -f "${SCRATCH}/${f}" ] || abort "built bundle missing expected file: ${SCRATCH}/${f}"
done

# ---- 2. TEVV materiality report (deployed vs freshly built) ------------------
echo "==> generating TEVV materiality report"
DEPLOYED_ARG=()
if [ -f "${DEPLOYED_DIR}/model_card.json" ]; then
  DEPLOYED_ARG=(--deployed-dir "${DEPLOYED_DIR}")
fi
${PY} dashboard tevv-materiality-report \
  --new-dir "${SCRATCH}" \
  "${DEPLOYED_ARG[@]}" \
  --out-md "${REPORT_MD}" \
  --out-json "${REPORT_JSON}"

REVIEW="$(python -c 'import json,sys;print("yes" if json.load(open(sys.argv[1]))["review_recommended"] else "no")' "${REPORT_JSON}")"
WEEKLY_COUNT="$(python -c 'import json,sys;print(json.load(open(sys.argv[1])).get("record_count","?"))' "${SCRATCH}/regional_county_risk_weekly.json")"
GIT_COMMIT="$(git rev-parse HEAD)"
echo "==> TEVV: REVIEW_RECOMMENDED=${REVIEW}  (report: ${REPORT_MD})"

if [ "${DRY_RUN}" -eq 1 ]; then
  echo "==> DRY-RUN: would promote ${#BUNDLE_FILES[@]} files -> ${DEPLOYED_DIR} and commit."
  echo "    (no promotion, no commit performed)"
  exit 0
fi

# ---- 3. promote: all-or-nothing copy scratch -> public -----------------------
echo "==> promoting ${#BUNDLE_FILES[@]} bundle files -> ${DEPLOYED_DIR}"
BACKUP="$(mktemp -d)"
trap 'rm -rf "${BACKUP}"' EXIT
for f in "${BUNDLE_FILES[@]}"; do
  [ -f "${DEPLOYED_DIR}/${f}" ] && cp "${DEPLOYED_DIR}/${f}" "${BACKUP}/${f}"
done
promote_failed=0
for f in "${BUNDLE_FILES[@]}"; do
  if ! cp "${SCRATCH}/${f}" "${DEPLOYED_DIR}/${f}"; then
    promote_failed=1
    break
  fi
done
if [ "${promote_failed}" -ne 0 ]; then
  echo "==> promotion failed mid-copy; restoring prior bundle" >&2
  for f in "${BUNDLE_FILES[@]}"; do
    [ -f "${BACKUP}/${f}" ] && cp "${BACKUP}/${f}" "${DEPLOYED_DIR}/${f}"
  done
  abort "promotion copy failed; public bundle restored to prior state"
fi

# ---- 4. commit (local only; never push/deploy) -------------------------------
echo "==> committing promoted bundle + TEVV report"
DEPLOYED_PATHS=()
for f in "${BUNDLE_FILES[@]}"; do DEPLOYED_PATHS+=("${DEPLOYED_DIR}/${f}"); done
git add "${DEPLOYED_PATHS[@]}" "${REPORT_MD}" "${REPORT_JSON}"

if git diff --cached --quiet; then
  echo "==> no change to promote (bundle byte-identical to deployed); nothing committed."
  exit 0
fi

git commit -q -m "chore: auto-rebuild regional bundle from ${GIT_COMMIT:0:12}

Automated regen->validate->promote of the regional research bundle.
weekly record_count: ${WEEKLY_COUNT}
TEVV REVIEW_RECOMMENDED: ${REVIEW}  (report: ${REPORT_MD})

Gated by scripts/rebuild_regional_bundle.sh (source-SHA match, data contract,
file-set, seldon verify). Local commit only; not pushed/deployed.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
echo "==> committed. REVIEW_RECOMMENDED=${REVIEW}. Not pushed (publish is a separate human go)."
