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
