# Plausible-Score-Range Width Clamp (v2 Display)

Status: draft
Primary sources: `cc_tasks/2026-06-04_v2-finish-provenance-render-capture-handoff.md` (`fc6b0c5e`, the render that surfaced the defect); `cc_tasks/2026-06-05_v2-gate-render-and-capture.md` (gate render, SHIP-CLEAR on floored counties); this note (algorithm of record); implementation task `cc_tasks/2026-06-05_v2-score-range-width-clamp.md`
Reviewer focus: this is a **display-layer imputation** on an uncertainty band, not a model change. The underlying `risk_score_low/high` fields are untouched. The clamp affects only the rendered "Plausible score range" string in the bite calculator.
Last checked against commit: Option A live @ `28ef7a6`; v2 ready-but-unshipped at time of writing (2026-06-05)

## Why this exists

The v2 bundle populates `risk_score_low/high` (verified faithful, commit `338ea5c`,
0 mismatches across 44,997 records — see lab note 12). These fields feed the bite
calculator's "Plausible score range" label via `regionalScoreRangeLabel(low, high)`
in `public/regional-research.js`.

The `fc6b0c5e` render exposed the defect. Four representative peak-week bands:

| County | low · score · high | width = high−low | raw render |
|---|---|---|---|
| Henrico 51087 (floored) | 1 · 1 · 2 | 1 | 1–2/10 |
| Virginia Beach 51810 (floored) | 1 · 1 · 2 | 1 | 1–2/10 |
| Tucker 54093 (high) | 6 · 10 · 10 | 4 | 6–10/10 |
| Cecil 24015 (mid) | 1 · 6 · 10 | 9 | **1–10/10** |

The gate (lab note 12, carried to `fc6b0c5e`) was set to catch a *floored* county
inheriting region-wide pooled residuals and showing an absurd upper band. That risk
did NOT materialize — floored counties render 1–2, narrow and honest. The actual
defect landed on **mid-incidence** counties: Cecil's band spans the entire 1–10
scale. "Plausible score range: 1–10/10" conveys nothing and reads as a hedge or an
alarm. It is arguably worse than the documented floor/ceiling collapse, because it
is wide rather than merely saturated.

Root cause is the same pooled-residual transfer assumption from lab note 12: the
band's `low` collapses to the floor (1) via the floor artifact while `high` rises
toward the ceiling via shared regional variance, so the *width* — not the position —
blows up. The point score (Cecil 6) is unaffected; only the band's spread is noise.

## The decision

Clamp the **rendered band width** when it is implausibly wide, treating an
over-wide band as small-sample / pooled-transfer noise rather than information.
Averaging the endpoints is a standard imputation move: when a band is too wide to
be informative, its most defensible single summary is its center, and a fixed
narrow spread around that center communicates "uncertain, roughly here" without
either (a) spanning the whole scale or (b) anchoring on a floor-collapsed `low`.

Rejected alternatives (and why):
- **Anchor on `low` (high = low+3).** Rejected: the `low` is the floor artifact;
  anchoring on it propagates the lie. Also amputates genuine highs (Tucker 6–10 →
  6–9, hiding a real 10).
- **Anchor on the point score (high = min(high, score+2)).** Cleaner on highs, but
  leaves Cecil at 1–8 (still floor-anchored low) and requires passing the score
  into the label function (signature change). Rejected for the wider case.
- **Midpoint imputation (chosen).** Uses only `low`/`high` (no signature change),
  centers on the band's own midpoint, and applies only when the band is wide
  enough to be uninformative. Tucker (width 4) is left alone — its width is
  legitimate signal, not noise.

## The algorithm (of record)

Input: integer `low`, integer `high`, with `1 ≤ low ≤ high ≤ 10`.
Output: a rendered band `[lo, hi]` for the "Plausible score range" label.

```
width = high - low

if width <= 4:
    # tight enough; legitimate, not noise. Leave as-is.
    lo, hi = low, high

elif 5 <= width <= 6:
    # wide: collapse to a 3-integer band (half-width 1) centered on the midpoint.
    center = round_half_up((low + high) / 2)
    lo, hi = center - 1, center + 1

else:  # width >= 7
    # really wide: collapse to a 5-integer band (half-width 2) centered on midpoint.
    center = round_half_up((low + high) / 2)
    lo, hi = center - 2, center + 2

# Clamp to display scale WITHOUT re-expanding the other end.
if lo < 1:  lo = 1
if hi > 10: hi = 10

# Degenerate / collapsed bands render as a single value, as before.
# (low == high reaches the width<=4 branch untouched; the label function's
#  existing low==high -> "{n}/10" path is preserved.)
```

Tier rationale and the "really wide" cut at width ≥ 7:
- A band of width ≤ 4 (≤ 5 integers, e.g. 6–10) is plausibly real spread for a
  high county and is left alone.
- A band of width 5–6 is collapsed to a 3-integer spread (center±1).
- A band of width ≥ 7 (≥ 8 integers, i.e. most of the scale) is the pathological
  case; collapsed to a 5-integer spread (center±2). The wider allowance at the
  worst tier is deliberate: a near-full-scale band genuinely carries more residual
  uncertainty, so center±2 (width 4) is the honest minimum, not center±1.

**Naming note for reviewers:** "spread" in conversation was ambiguous. The note of
record uses **width = high − low** (an integer count of steps, NOT a count of
distinct integers). center±1 ⇒ width 2; center±2 ⇒ width 4. There is no symmetric
integer band of width 3 around a single center, which is why the tiers are width-2
and width-4, not width-3.

## Rounding

`round_half_up`: midpoints landing on `.5` round up. Matches JS `Math.round`
(`Math.round(5.5) === 6`). Chosen so an even-width band's center does not drift
*down* into the floor it is meant to escape.

## Worked examples (the verification targets)

| County | low·score·high | width | tier | center | rendered |
|---|---|---|---|---|---|
| Henrico (floored) | 1·1·2 | 1 | ≤4 untouched | — | **1–2/10** |
| Virginia Beach (floored) | 1·1·2 | 1 | ≤4 untouched | — | **1–2/10** |
| Tucker (high) | 6·10·10 | 4 | ≤4 untouched | — | **6–10/10** |
| Cecil (mid) | 1·6·10 | 9 | ≥7 center±2 | round(5.5)=6 | **4–8/10** |

## Edge cases (pinned, so they are not re-litigated)

1. **low == high (width 0).** Reaches `width <= 4`, untouched. Existing label path
   renders `"{n}/10"`. No change.
2. **Width exactly 4 (e.g. Tucker 6–10).** `<= 4` branch — untouched. The boundary
   is inclusive at 4 by design (4-step bands are legitimate, not noise).
3. **Width exactly 6 vs 7.** 6 → center±1 (width 2); 7 → center±2 (width 4). The
   cut is `>= 7` for the wider tier.
4. **Centering pushes an end out of [1,10].** Clamp only the offending end; do NOT
   re-expand the opposite end to preserve a target width. Example: a hypothetical
   wide band centered at 9 with ±2 → 7–11 → clamp hi to 10 → renders **7–10**
   (width 3), not 6–10. Rationale: re-expanding would re-introduce reach toward the
   floor/ceiling the clamp exists to suppress.
5. **Even-width midpoint (e.g. 2–9, width 7).** center round(5.5)=6, ±2 → 4–8.
   The half-up rule makes this deterministic.
6. **Asymmetry after clamp is acceptable.** The output band need not stay symmetric
   once clamped to scale (edge case 4). Symmetry is a property of the *imputation*,
   not a guarantee of the *rendered* band.

## Scope boundary (what this is NOT)

- NOT a model change. `risk_score_low/high` in the bundle and
  `single_bite_risk_score_low/high` in the bite estimator are unchanged. The clamp
  lives only in `regionalScoreRangeLabel` (display).
- NOT applied to the always-visible county panel — that surface does not render the
  score range (lab note 12; the range is bite-calculator-only). No Option A
  interaction.
- NOT a fix to the floor/ceiling collapse (lab note 12 documents that separately and
  it stays unfixed — POC-class, accepted).
- Provenance of the underlying fields (`338ea5c`, `[SETTLED: verified]`) is
  undisturbed; this note adds a display rule on top, it does not revise the data.

## Status of the v2 ship after this clamp

With the clamp, the v2 "plausible score range" reads honestly across all four
representative counties (floored narrow, high intact, mid collapsed to a centered
4-wide band). The mid-county full-scale artifact — the one remaining objection in
the `fc6b0c5e` handoff to shipping v2 as-is — is resolved. The deliberate one-time
v2 promote remains a separate, manual step (armed-but-manual; do not auto-publish).
