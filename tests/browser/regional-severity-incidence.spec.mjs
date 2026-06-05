// Unit tests for the Option A severity/interval helpers.
// Part 2: the county forecast interval is shown as an incidence range
// (per 100k), never as the saturating self-history percentile ranks.
// Part 1 support: the dominant framing is the score's absolute category.

import { createRequire } from "module";
import { expect, test } from "@playwright/test";

const require = createRequire(import.meta.url);
const {
  regionalForecastIntervalIncidenceText,
  regionalScoreSeverityLabel,
} = require("../../public/regional-research.js");

test("interval renders incidence-per-100k bounds, not percentile ranks", () => {
  // Henrico 2026 verified bounds (RESULTS 2026-06-03).
  const text = regionalForecastIntervalIncidenceText({
    lower_80_incidence_per_100k: 0,
    upper_80_incidence_per_100k: 61.121852,
    lower_95_incidence_per_100k: 0,
    upper_95_incidence_per_100k: 148.702309,
  });
  expect(text).toContain("per 100k");
  expect(text).toContain("61.12"); // 80% upper magnitude
  expect(text).toContain("148.70"); // 95% upper magnitude
  expect(text).toContain("80% range");
  expect(text).toContain("95% range");
  // Never expressed as self-history percentile ranks.
  expect(text).not.toContain("percentile");
});

test("interval text degrades safely when bounds are missing", () => {
  expect(regionalForecastIntervalIncidenceText(null)).toBe("unavailable.");
  expect(
    regionalForecastIntervalIncidenceText({
      lower_80_incidence_per_100k: null,
      upper_80_incidence_per_100k: null,
      lower_95_incidence_per_100k: null,
      upper_95_incidence_per_100k: null,
    })
  ).toBe("unavailable.");
});

test("score category label matches the regional 1-10 scale bands", () => {
  // root.score_scale.categories: 1-2 very_low .. 9-10 very_high.
  expect(regionalScoreSeverityLabel(1)).toBe("very low");
  expect(regionalScoreSeverityLabel(2)).toBe("very low");
  expect(regionalScoreSeverityLabel(3)).toBe("low");
  expect(regionalScoreSeverityLabel(5)).toBe("moderate");
  expect(regionalScoreSeverityLabel(7)).toBe("high");
  expect(regionalScoreSeverityLabel(10)).toBe("very high");
  expect(regionalScoreSeverityLabel(Number.NaN)).toBe("unavailable");
});


// Lab note 13 — plausible-score-range width clamp (display-only).
const { regionalScoreRangeLabel } = require("../../public/regional-research.js");

test("score-range width clamp matches lab note 13 worked examples", () => {
  // width <= 4: untouched.
  expect(regionalScoreRangeLabel(1, 2)).toBe("1-2/10"); // Henrico/VBeach floored
  expect(regionalScoreRangeLabel(6, 10)).toBe("6-10/10"); // Tucker, width 4
  // low == high: single value.
  expect(regionalScoreRangeLabel(5, 5)).toBe("5/10");
  // width 6: center round((2+8)/2)=5, ±1.
  expect(regionalScoreRangeLabel(2, 8)).toBe("4-6/10");
  // width 7: center round(5.5)=6, ±2.
  expect(regionalScoreRangeLabel(2, 9)).toBe("4-8/10");
  // width 9 (Cecil, mid): center round(5.5)=6, ±2 -> was 1-10/10.
  expect(regionalScoreRangeLabel(1, 10)).toBe("4-8/10");
  // width 5 high in scale: center round((5+10)/2)=8, ±1 -> 7-9 (no clamp needed).
  expect(regionalScoreRangeLabel(5, 10)).toBe("7-9/10");
});

test("score-range clamp keeps every valid band inside 1-10 (clamp is defensive)", () => {
  // For all valid 1<=low<=high<=10 the centered band already lands in [1,10];
  // the [1,10] clamp branch never fires on valid input (lab note 13 edge case 4
  // is a documented hypothetical). Assert the invariant holds and never inverts.
  for (let low = 1; low <= 10; low++) {
    for (let high = low; high <= 10; high++) {
      const label = regionalScoreRangeLabel(low, high);
      const ends = label.replace("/10", "").split("-").map(Number);
      for (const e of ends) {
        expect(e).toBeGreaterThanOrEqual(1);
        expect(e).toBeLessThanOrEqual(10);
      }
      if (ends.length === 2) expect(ends[0]).toBeLessThanOrEqual(ends[1]);
    }
  }
});
