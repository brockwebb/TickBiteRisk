import { expect, test } from "@playwright/test";

const fixtures = {
  "regional_county_risk_weekly.json": {
    caveats: ["informational_only", "not_medical_advice"],
    export_type: "regional_county_week_risk",
    model_name: "empirical_bayes_spatial_regime_incidence",
    record_count: 6,
    records: [
      riskRecord("24001", "Allegany County", 21, 9, "very_high", 2.6, [1.2, 3.8], [0.8, 5.4]),
      riskRecord("24023", "Garrett County", 21, 8, "high", 2.1, [1.0, 3.1], [0.6, 4.8]),
      riskRecord("51810", "Virginia Beach city", 21, 2, "very_low", 0.2, [0.05, 0.4], [0, 0.7]),
      riskRecord("24001", "Allegany County", 22, 10, "very_high", 3.1, [1.5, 4.3], [0.9, 6.2]),
      riskRecord("24023", "Garrett County", 22, 8, "high", 2.4, [1.1, 3.5], [0.7, 5.2]),
      riskRecord("51810", "Virginia Beach city", 22, 1, "very_low", 0.12, [0.02, 0.3], [0, 0.5]),
    ],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
    score_scale: {
      min: 1,
      max: 10,
    },
    selected_forecast_metadata: {
      forecast_origin_year: 2023,
      forecast_year: 2026,
    },
  },
  "regional_county_metadata.json": {
    county_count: 3,
    counties: [
      countyMetadata("24001", "Allegany County", "2024_regime_07", "Spatial regime 7", 7),
      countyMetadata("24023", "Garrett County", "2024_regime_07", "Spatial regime 7", 7),
      countyMetadata(
        "51810",
        "Virginia Beach city",
        "2024_regime_02",
        "Spatial regime 2",
        2
      ),
    ],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
  },
  "regional_counties.geojson": {
    type: "FeatureCollection",
    metadata: {
      feature_count: 3,
      research_only: true,
      states: ["MD", "VA"],
    },
    features: [
      countyFeature("24001", "Allegany County", "MD", -79.5, 39.3),
      countyFeature("24023", "Garrett County", "MD", -79.2, 39.0),
      countyFeature("51810", "Virginia Beach city", "VA", -76.0, 36.8),
    ],
  },
  "regional_spatial_regime_overlays.json": {
    export_type: "regional_spatial_regime_overlays",
    model_name: "empirical_bayes_spatial_regime_incidence",
    record_count: 2,
    records: [
      regimeOverlay(
        "2024_regime_07",
        "Spatial regime 7",
        ["24001", "24023"],
        18.4,
        [12.1, 24.9],
        [8.2, 31.5]
      ),
      regimeOverlay(
        "2024_regime_02",
        "Spatial regime 2",
        ["51810"],
        1.3,
        [0.4, 2.2],
        [0, 3.8]
      ),
    ],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
  },
  "model_card.json": {
    clinical_disclaimer:
      "Informational only. Not medical advice. Follow CDC guidance and contact a healthcare professional about your situation.",
    method_summary:
      "Research regional county-week score derived from forecast-safe localized spatial regimes.",
    model_name: "empirical_bayes_spatial_regime_incidence",
    product_framing:
      "Lyme risk forecasting tool for Mid-Atlantic county-week conditions",
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
    score_interpretation:
      "Relative seasonal Lyme forecast on a 1 to 10 scale.",
  },
  "source_catalog.json": {
    data_lag_and_update_policy: {
      forecast_boundary:
        "Forecast-safe branches use prior-year and trailing regional data only.",
      why_forecasting:
        "Official county surveillance data lag real-world exposure conditions.",
    },
    guidance_links: [],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
    sources: [
      {
        source_id: "regional_county_adjacency",
        public_notes:
          "Census TIGERweb county geometry supports cross-border neighborhood and localized-regime features.",
      },
    ],
  },
};

test("regional research dashboard renders county risk, week slider, and regime intervals", async ({
  page,
}) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.route("**/research-data/regional/*", async (route) => {
    const filename = route.request().url().split("/").pop();
    const body = fixtures[filename];
    if (!body) {
      await route.fulfill({ status: 404, body: "missing fixture" });
      return;
    }
    await route.fulfill({
      body: JSON.stringify(body),
      contentType: filename.endsWith(".geojson")
        ? "application/geo+json"
        : "application/json",
    });
  });

  await page.goto("/regional-research.html");

  await expect(
    page.getByRole("heading", { name: "TickBiteRisk Regional Research" })
  ).toBeVisible();
  await expect(page.locator("#regional-risk-map path[data-county]")).toHaveCount(3);
  await expect(page.locator("#regional-panel-content")).toHaveAttribute(
    "aria-live",
    "polite"
  );

  await page.locator('path[data-county="24001"]').click();
  await expect(page.locator("#regional-panel-content")).toContainText("Allegany County");
  await expect(page.locator("#regional-panel-content")).toContainText("MD");
  await expect(page.locator("#regional-panel-content")).toContainText("9/10");
  await expect(page.locator("#regional-panel-content")).toContainText(
    "95% empirical interval: 0.80 to 5.40 per 100k"
  );
  await expect(page.locator("#regional-panel-content")).toContainText(
    "Spatial regime 7"
  );
  await expect(page.locator("#regional-regime-panel")).toContainText("2 counties");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "Regime 95% interval: 8.20 to 31.50 per 100k"
  );
  await expect(page.locator('path[data-county="24023"]')).toHaveClass(
    /is-same-regime/
  );
  await expect(page.locator('path[data-county="51810"]')).not.toHaveClass(
    /is-same-regime/
  );

  await page.locator("#week-slider").fill("22");
  await expect(page.locator("#week-label")).toContainText("MMWR week 22");
  await expect(page.locator("#regional-panel-content")).toContainText("10/10");
  await expect(page.locator("#regional-panel-content")).toContainText(
    "95% empirical interval: 0.90 to 6.20 per 100k"
  );

  await page.locator('path[data-county="51810"]').click();
  await expect(page.locator("#regional-panel-content")).toContainText(
    "Virginia Beach city"
  );
  await expect(page.locator("#regional-panel-content")).toContainText("VA");
  await expect(page.locator("#regional-regime-panel")).toContainText("Spatial regime 2");

  await expect(page.locator("#regional-source-content")).toContainText(
    "Forecast-safe branches use prior-year"
  );

  expect(consoleErrors).toEqual([]);
});

function riskRecord(
  countyFips,
  countyName,
  mmwrWeek,
  score,
  category,
  weeklyIncidence,
  interval80,
  interval95
) {
  return {
    backtest_assumption_flags: [
      "not_public_default",
      "forecast_without_observed_target",
    ],
    county_fips: countyFips,
    county_name: countyName,
    data_year: 2026,
    feature_quality_flags: [
      "localized_spatial_regime_feature",
      "forecast_safe_prior_history_spatial_regime",
      "empirical_prediction_band",
    ],
    mmwr_week: mmwrWeek,
    predicted_weekly_incidence_80_interval: interval80,
    predicted_weekly_incidence_95_interval: interval95,
    predicted_weekly_incidence_per_100k: weeklyIncidence,
    risk_category: category,
    risk_score: score,
    year: 2026,
  };
}

function countyMetadata(countyFips, countyName, regionId, regionName, rank) {
  return {
    available_mmwr_weeks: [21, 22],
    available_years: [2026],
    county_fips: countyFips,
    county_name: countyName,
    selected_spatial_regime: {
      forecast_origin_year: 2023,
      forecast_year: 2026,
      region_id: regionId,
      region_name: regionName,
      spatial_regime_feature_year: 2024,
      spatial_regime_rank: rank,
    },
  };
}

function countyFeature(countyFips, countyName, stateAbbr, longitude, latitude) {
  const size = 0.14;
  return {
    type: "Feature",
    properties: {
      county_fips: countyFips,
      county_name: countyName,
      state_abbr: stateAbbr,
      state_fips: countyFips.slice(0, 2),
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [longitude - size, latitude - size],
          [longitude + size, latitude - size],
          [longitude + size, latitude + size],
          [longitude - size, latitude + size],
          [longitude - size, latitude - size],
        ],
      ],
    },
  };
}

function regimeOverlay(regionId, regionName, counties, incidence, interval80, interval95) {
  return {
    county_fips_list: counties,
    forecast_origin_year: 2023,
    forecast_year: 2026,
    n_counties: counties.length,
    predicted_incidence_80_interval: interval80,
    predicted_incidence_95_interval: interval95,
    predicted_incidence_per_100k: incidence,
    region_id: regionId,
    region_name: regionName,
    spatial_regime_feature_year: 2024,
    spatial_regime_rank: Number(regionId.slice(-2)),
    summary_assumption_flags: [
      "localized_spatial_regime_research",
      "planning_aggregate_not_joint_posterior",
      "not_public_default",
    ],
  };
}
