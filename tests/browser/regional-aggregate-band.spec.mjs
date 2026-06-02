// Unit test for the regional aggregate interval-band fix (Change 3).
// Bug: bands were divided by the line's total population, so a county with
// weekly cases but missing interval fields inflated the denominator and pulled
// the aggregate band inward (below the line). The band must use its own
// population (only counties that contributed finite interval cases), so it
// brackets the population-weighted line.

import { createRequire } from "module";
import { expect, test } from "@playwright/test";

const require = createRequire(import.meta.url);
const { regionalAggregateWeekContributions } = require(
  "../../public/regional-research.js"
);

test("aggregate band brackets the line when a county lacks interval fields", () => {
  // County A: rate 500/100k, intervals present and bracketing its rate.
  // County B: same rate (500/100k) but NO interval fields (the dilution case).
  const week = regionalAggregateWeekContributions([
    {
      population: 1000,
      cases: 5, // (5/1000)*1e5 = 500/100k
      interval80: [400, 600],
      interval95: [300, 700],
    },
    {
      population: 9000,
      cases: 45, // (45/9000)*1e5 = 500/100k
      interval80: null,
      interval95: null,
    },
  ]);

  const line = week.predicted_weekly_incidence_per_100k;
  const [lo80, hi80] = week.predicted_weekly_incidence_80_interval;
  const [lo95, hi95] = week.predicted_weekly_incidence_95_interval;

  expect(line).toBeCloseTo(500, 6);
  // The band must bracket the line (lower <= line <= upper), not collapse below it.
  expect(lo80).toBeLessThanOrEqual(line);
  expect(hi80).toBeGreaterThanOrEqual(line);
  expect(lo95).toBeLessThanOrEqual(line);
  expect(hi95).toBeGreaterThanOrEqual(line);
  // And the 95 band is at least as wide as the 80 band.
  expect(lo95).toBeLessThanOrEqual(lo80);
  expect(hi95).toBeGreaterThanOrEqual(hi80);
});

test("band is absent (zero) when no county has interval fields", () => {
  const week = regionalAggregateWeekContributions([
    { population: 1000, cases: 5, interval80: null, interval95: null },
  ]);
  expect(week.predicted_weekly_incidence_80_interval).toEqual([0, 0]);
});
