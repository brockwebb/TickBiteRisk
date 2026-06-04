"""TEVV materiality report for the regional bundle (by-exception human surface).

Diffs a freshly-built regional bundle against the currently-deployed one and
emits a one-page report plus a machine-readable JSON. Normal (immaterial) runs
auto-ship; a loud ``REVIEW_RECOMMENDED`` banner trips when a change exceeds the
materiality thresholds Brock accepted (see constants below). This is a
circuit-breaker / visibility mechanism, NOT an approval gate.

Pure functions (``compare_bundle_metrics``, ``render_*``) take plain data so the
materiality rules are unit-testable without building real bundles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# --- Materiality thresholds (accepted by Brock; do NOT add others) -----------
# A county flags if ANY of (a)/(b)/(c) fire; the report banner trips on the
# region-level conditions. Sub-floor counties flag ONLY on a category change.
MATERIALITY_RELATIVE_THRESHOLD = 0.20  # (a) >20% relative incidence move
MATERIALITY_INCIDENCE_FLOOR = 1.0  # per 100k noise floor (small-denominator guard)
SCORE_BIN_MOVE_THRESHOLD = 2  # (c) >= 2 integer score bins
BANNER_FLAGGED_FRACTION = 0.15  # >15% of counties flagged -> review
BANNER_BIG_MOVER_RELATIVE = 0.50  # any one county >50% relative (>= floor) -> review
EXPECTED_COUNTY_COUNT = 283  # deploy-validator invariant

# Score band -> display risk-category (matches root.score_scale.categories).
_SCORE_BANDS = (
    (1, 2, "very_low"),
    (3, 4, "low"),
    (5, 6, "moderate"),
    (7, 8, "high"),
    (9, 10, "very_high"),
)

# Map annual-incidence display class (matches the dashboard map's
# regionalAnnualIncidenceClass): <25 / 25-49 / 50-99 / 100-199 / 200+.
_INCIDENCE_CLASS_BREAKS = ((25, "<25"), (50, "25-49"), (100, "50-99"), (200, "100-199"))


def score_to_category(score: int | None) -> str | None:
    """Map a peak score (1-10) to its display risk-category band."""
    if score is None:
        return None
    for low, high, label in _SCORE_BANDS:
        if low <= score <= high:
            return label
    return "out_of_range"


def incidence_to_class(incidence: float | None) -> str | None:
    """Map an annual incidence to the map's display class."""
    if incidence is None:
        return None
    for breakpoint, label in _INCIDENCE_CLASS_BREAKS:
        if incidence < breakpoint:
            return label
    return "200+"


@dataclass(frozen=True)
class CountyMetric:
    county_fips: str
    county_name: str
    state_abbr: str
    forecast_year: int
    predicted_incidence_per_100k: float | None
    peak_score: int | None

    @property
    def category(self) -> str | None:
        return score_to_category(self.peak_score)

    @property
    def incidence_class(self) -> str | None:
        return incidence_to_class(self.predicted_incidence_per_100k)


@dataclass(frozen=True)
class BundleMetrics:
    """Per-(county_fips, forecast_year) metrics plus bundle provenance."""

    counties: dict[tuple[str, int], CountyMetric]
    total_counties: int
    forecast_years: tuple[int, ...]
    record_counts: dict[str, int]
    commit: str | None
    generated_at: str | None


@dataclass(frozen=True)
class CountyFlag:
    metric_new: CountyMetric
    deployed_incidence: float | None
    deployed_score: int | None
    relative_move: float | None
    category_change: tuple[str | None, str | None] | None
    score_bin_move: int | None
    rules: tuple[str, ...]


@dataclass
class MaterialityResult:
    review_recommended: bool
    review_reasons: list[str] = field(default_factory=list)
    flags: list[CountyFlag] = field(default_factory=list)
    total_counties_new: int = 0
    total_counties_deployed: int | None = None
    rule_counts: dict[str, int] = field(default_factory=dict)
    score_floor_deployed: int | None = None
    score_floor_new: int = 0
    category_histogram_deployed: dict[str, int] = field(default_factory=dict)
    category_histogram_new: dict[str, int] = field(default_factory=dict)
    record_counts_deployed: dict[str, int] | None = None
    record_counts_new: dict[str, int] = field(default_factory=dict)
    record_count_changes: list[str] = field(default_factory=list)
    forecast_years: tuple[int, ...] = ()
    deployed_commit: str | None = None
    new_commit: str | None = None
    is_baseline: bool = False
    county_count_ok: bool = True


def _relative_move(deployed: float | None, new: float | None) -> float | None:
    if deployed is None or new is None or deployed == 0:
        return None
    return abs(new - deployed) / abs(deployed)


def _evaluate_county(deployed: CountyMetric | None, new: CountyMetric) -> CountyFlag | None:
    """Apply rules (a)/(b)/(c). Returns a CountyFlag if any rule fires."""
    if deployed is None:
        # A county/year that did not exist in the deployed bundle is surfaced
        # via record-count integrity, not the per-county relative rules.
        return None
    rules: list[str] = []
    new_inc = new.predicted_incidence_per_100k
    rel = _relative_move(deployed.predicted_incidence_per_100k, new_inc)
    below_floor = new_inc is not None and new_inc < MATERIALITY_INCIDENCE_FLOOR

    # (b) display risk-category change — categorical, any magnitude, always live.
    category_change = None
    if deployed.category != new.category:
        category_change = (deployed.category, new.category)
        rules.append("b")

    # Sub-floor counties flag ONLY via (b) (small-denominator noise guard).
    if not below_floor:
        # (a) >20% relative incidence move AND new >= 1.0 per 100k.
        if (
            rel is not None
            and rel > MATERIALITY_RELATIVE_THRESHOLD
            and new_inc is not None
            and new_inc >= MATERIALITY_INCIDENCE_FLOOR
        ):
            rules.append("a")
        # (c) peak score moved >= 2 integer bins.
        if (
            deployed.peak_score is not None
            and new.peak_score is not None
            and abs(new.peak_score - deployed.peak_score) >= SCORE_BIN_MOVE_THRESHOLD
        ):
            rules.append("c")

    if not rules:
        return None
    score_bin_move = (
        abs(new.peak_score - deployed.peak_score)
        if deployed.peak_score is not None and new.peak_score is not None
        else None
    )
    return CountyFlag(
        metric_new=new,
        deployed_incidence=deployed.predicted_incidence_per_100k,
        deployed_score=deployed.peak_score,
        relative_move=rel,
        category_change=category_change,
        score_bin_move=score_bin_move,
        rules=tuple(rules),
    )


def _score_floor_count(metrics: BundleMetrics) -> int:
    return sum(1 for m in metrics.counties.values() if m.peak_score == 1)


def _category_histogram(metrics: BundleMetrics) -> dict[str, int]:
    hist: dict[str, int] = {}
    for m in metrics.counties.values():
        key = m.category or "unknown"
        hist[key] = hist.get(key, 0) + 1
    return hist


def compare_bundle_metrics(
    deployed: BundleMetrics | None, new: BundleMetrics
) -> MaterialityResult:
    """Apply the materiality rules and banner conditions. Pure."""
    result = MaterialityResult(review_recommended=False)
    result.total_counties_new = new.total_counties
    result.forecast_years = new.forecast_years
    result.new_commit = new.commit
    result.record_counts_new = dict(new.record_counts)
    result.score_floor_new = _score_floor_count(new)
    result.category_histogram_new = _category_histogram(new)
    result.county_count_ok = new.total_counties == EXPECTED_COUNTY_COUNT

    if deployed is None:
        # First run: baseline report, no diff.
        result.is_baseline = True
        return result

    result.total_counties_deployed = deployed.total_counties
    result.deployed_commit = deployed.commit
    result.record_counts_deployed = dict(deployed.record_counts)
    result.score_floor_deployed = _score_floor_count(deployed)
    result.category_histogram_deployed = _category_histogram(deployed)

    for key, new_metric in sorted(new.counties.items()):
        flag = _evaluate_county(deployed.counties.get(key), new_metric)
        if flag is not None:
            result.flags.append(flag)

    rule_counts = {"a": 0, "b": 0, "c": 0}
    big_mover = False
    for flag in result.flags:
        for rule in flag.rules:
            rule_counts[rule] += 1
        if (
            flag.relative_move is not None
            and flag.relative_move > BANNER_BIG_MOVER_RELATIVE
            and flag.metric_new.predicted_incidence_per_100k is not None
            and flag.metric_new.predicted_incidence_per_100k
            >= MATERIALITY_INCIDENCE_FLOOR
        ):
            big_mover = True
    result.rule_counts = rule_counts

    # Record-count integrity (a county appearing/disappearing is material).
    for name, new_count in new.record_counts.items():
        dep_count = deployed.record_counts.get(name)
        if dep_count is not None and dep_count != new_count:
            result.record_count_changes.append(
                f"{name}: {dep_count} -> {new_count}"
            )

    flagged_fraction = (
        len({f.metric_new.county_fips for f in result.flags}) / new.total_counties
        if new.total_counties
        else 0.0
    )
    if flagged_fraction > BANNER_FLAGGED_FRACTION:
        result.review_recommended = True
        result.review_reasons.append(
            f">{int(BANNER_FLAGGED_FRACTION * 100)}% of counties flagged "
            f"({flagged_fraction:.1%})"
        )
    if big_mover:
        result.review_recommended = True
        result.review_reasons.append(
            f"a single county moved >{int(BANNER_BIG_MOVER_RELATIVE * 100)}% "
            "relative (>= 1.0 per 100k)"
        )
    if not result.county_count_ok:
        result.review_recommended = True
        result.review_reasons.append(
            f"county count {new.total_counties} != {EXPECTED_COUNTY_COUNT}"
        )
    if result.record_count_changes:
        result.review_recommended = True
        result.review_reasons.append("record_count changed between bundles")
    return result


# --- Bundle loading (I/O; the pure rules above don't need this) --------------


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_bundle_metrics(bundle_dir: Path) -> BundleMetrics:
    """Read per-county incidence (typicality) + peak score (weekly) + provenance."""
    typicality = _load_json(bundle_dir / "regional_forecast_typicality.json")
    weekly = _load_json(bundle_dir / "regional_county_risk_weekly.json")
    model_card = _load_json(bundle_dir / "model_card.json")

    typ_records = typicality["records"] if isinstance(typicality, dict) else typicality
    weekly_records = weekly["records"] if isinstance(weekly, dict) else weekly

    # Peak seasonal score per (county_fips, year).
    peak: dict[tuple[str, int], int] = {}
    for row in weekly_records:
        fips = str(row["county_fips"]).zfill(5)
        year = int(row.get("forecast_year", row.get("year")))
        score = row.get("risk_score")
        if score is None:
            continue
        key = (fips, year)
        peak[key] = max(peak.get(key, score), int(score))

    counties: dict[tuple[str, int], CountyMetric] = {}
    for row in typ_records:
        fips = str(row["county_fips"]).zfill(5)
        year = int(row["forecast_year"])
        key = (fips, year)
        inc = row.get("predicted_incidence_per_100k")
        counties[key] = CountyMetric(
            county_fips=fips,
            county_name=row.get("county_name", ""),
            state_abbr=row.get("state_abbr", ""),
            forecast_year=year,
            predicted_incidence_per_100k=(None if inc is None else float(inc)),
            peak_score=peak.get(key),
        )

    forecast_years = tuple(sorted({k[1] for k in counties}))
    total_counties = len({k[0] for k in counties})
    commit = None
    provenance = model_card.get("build_provenance") if isinstance(model_card, dict) else None
    if isinstance(provenance, dict):
        commit = provenance.get("git_commit")
    generated_at = model_card.get("generated_at") if isinstance(model_card, dict) else None

    record_counts = {}
    for name in (
        "regional_county_risk_weekly.json",
        "regional_forecast_typicality.json",
        "regional_county_incidence_annual.json",
    ):
        path = bundle_dir / name
        if path.exists():
            payload = _load_json(path)
            if isinstance(payload, dict) and "record_count" in payload:
                record_counts[name] = int(payload["record_count"])

    return BundleMetrics(
        counties=counties,
        total_counties=total_counties,
        forecast_years=forecast_years,
        record_counts=record_counts,
        commit=commit,
        generated_at=generated_at,
    )


# --- Rendering ---------------------------------------------------------------

_FLAG_TABLE_CAP = 25


def render_markdown(result: MaterialityResult) -> str:
    lines: list[str] = []
    banner = (
        "🚨 **REVIEW_RECOMMENDED: YES**"
        if result.review_recommended
        else "✅ REVIEW_RECOMMENDED: no"
    )
    lines.append("# Regional bundle TEVV materiality report")
    lines.append("")
    lines.append(banner)
    if result.review_reasons:
        for reason in result.review_reasons:
            lines.append(f"- {reason}")
    lines.append("")
    lines.append(f"- Built-from commit: `{result.new_commit or 'unknown'}`")
    lines.append(f"- Deployed commit: `{result.deployed_commit or 'none'}`")
    lines.append(f"- Forecast year(s): {', '.join(map(str, result.forecast_years)) or 'none'}")
    county_flag = "" if result.county_count_ok else "  ⚠️ EXPECTED 283"
    lines.append(f"- Total counties (new): {result.total_counties_new}{county_flag}")
    lines.append("")

    if result.is_baseline:
        lines.append("## Baseline (no deployed bundle to diff against)")
        lines.append("")
        lines.append(
            f"This is a first-run baseline: {result.total_counties_new} counties, "
            f"score-floor (score==1) count {result.score_floor_new}. No diff performed."
        )
        lines.append("")
        return "\n".join(lines) + "\n"

    flagged_counties = len({f.metric_new.county_fips for f in result.flags})
    pct = (
        flagged_counties / result.total_counties_new
        if result.total_counties_new
        else 0.0
    )
    lines.append("## Counts")
    lines.append("")
    lines.append(
        f"- Counties flagged: {flagged_counties} of {result.total_counties_new} "
        f"({pct:.1%})"
    )
    lines.append(
        f"- By rule — (a) relative-incidence: {result.rule_counts.get('a', 0)}; "
        f"(b) category-change: {result.rule_counts.get('b', 0)}; "
        f"(c) score-bin: {result.rule_counts.get('c', 0)}"
    )
    lines.append("")

    if not result.flags:
        lines.append("**No material change.** No county tripped rule (a), (b), or (c).")
        lines.append("")
    else:
        lines.append("## Flagged counties")
        lines.append("")
        lines.append(
            "| County | State | Incidence (dep→new) | Rel % | Score (dep→new) | "
            "Category change | Rules |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        ranked = sorted(
            result.flags,
            key=lambda f: (f.relative_move if f.relative_move is not None else -1),
            reverse=True,
        )
        for flag in ranked[:_FLAG_TABLE_CAP]:
            m = flag.metric_new
            dep_inc = "—" if flag.deployed_incidence is None else f"{flag.deployed_incidence:.2f}"
            new_inc = (
                "—"
                if m.predicted_incidence_per_100k is None
                else f"{m.predicted_incidence_per_100k:.2f}"
            )
            rel = "—" if flag.relative_move is None else f"{flag.relative_move:.0%}"
            cat = (
                f"{flag.category_change[0]}→{flag.category_change[1]}"
                if flag.category_change
                else "—"
            )
            lines.append(
                f"| {m.county_name} | {m.state_abbr} | {dep_inc}→{new_inc} | {rel} | "
                f"{flag.deployed_score}→{m.peak_score} | {cat} | "
                f"{', '.join(flag.rules)} |"
            )
        overflow = len(result.flags) - _FLAG_TABLE_CAP
        if overflow > 0:
            lines.append("")
            lines.append(f"…and {overflow} more flagged (table capped at {_FLAG_TABLE_CAP}).")
        lines.append("")

    lines.append("## Distribution shifts")
    lines.append("")
    lines.append(
        f"- Score-floor (score==1) population: {result.score_floor_deployed} → "
        f"{result.score_floor_new}"
    )
    lines.append(
        f"- Category histogram (deployed): {result.category_histogram_deployed}"
    )
    lines.append(f"- Category histogram (new): {result.category_histogram_new}")
    lines.append("")
    lines.append("## Provenance / integrity")
    lines.append("")
    if result.record_count_changes:
        for change in result.record_count_changes:
            lines.append(f"- ⚠️ record_count changed — {change}")
    else:
        lines.append("- record_counts unchanged between bundles")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_json(result: MaterialityResult) -> dict:
    return {
        "review_recommended": result.review_recommended,
        "review_reasons": result.review_reasons,
        "built_from_commit": result.new_commit,
        "deployed_commit": result.deployed_commit,
        "forecast_years": list(result.forecast_years),
        "total_counties_new": result.total_counties_new,
        "total_counties_deployed": result.total_counties_deployed,
        "county_count_ok": result.county_count_ok,
        "is_baseline": result.is_baseline,
        "flagged_county_count": len({f.metric_new.county_fips for f in result.flags}),
        "rule_counts": result.rule_counts,
        "score_floor_deployed": result.score_floor_deployed,
        "score_floor_new": result.score_floor_new,
        "category_histogram_deployed": result.category_histogram_deployed,
        "category_histogram_new": result.category_histogram_new,
        "record_count_changes": result.record_count_changes,
        "flags": [
            {
                "county_fips": f.metric_new.county_fips,
                "county_name": f.metric_new.county_name,
                "state_abbr": f.metric_new.state_abbr,
                "forecast_year": f.metric_new.forecast_year,
                "deployed_incidence": f.deployed_incidence,
                "new_incidence": f.metric_new.predicted_incidence_per_100k,
                "relative_move": f.relative_move,
                "deployed_score": f.deployed_score,
                "new_score": f.metric_new.peak_score,
                "category_change": list(f.category_change) if f.category_change else None,
                "score_bin_move": f.score_bin_move,
                "rules": list(f.rules),
            }
            for f in result.flags
        ],
    }


def build_tevv_report(
    *, new_dir: Path, deployed_dir: Path | None
) -> tuple[MaterialityResult, str, dict]:
    """Load both bundles, compare, and render. ``deployed_dir`` None/absent => baseline."""
    new_metrics = load_bundle_metrics(new_dir)
    deployed_metrics = None
    if deployed_dir is not None and (deployed_dir / "model_card.json").exists():
        deployed_metrics = load_bundle_metrics(deployed_dir)
    result = compare_bundle_metrics(deployed_metrics, new_metrics)
    return result, render_markdown(result), render_json(result)
