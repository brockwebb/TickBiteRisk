import { expect, test } from "@playwright/test";

const fixtures = {
  "regional_county_risk_weekly.json": {
    caveats: ["informational_only", "not_medical_advice"],
    export_type: "regional_county_week_risk",
    model_name: "empirical_bayes_spatial_regime_incidence",
    record_count: 13,
    forecast_basis: {
      analog_year_definition: {
        current_role: "comparison_or_research_branch_unless_selected",
        current_like_year_features: [
          "origin-year reported Lyme incidence",
          "trailing mean reported Lyme incidence",
        ],
        not_currently_matched_on: [
          "daily weather",
          "tick abundance",
          "infected tick prevalence",
          "observed county-month cases",
        ],
      },
      seasonal_allocation: {
        role:
          "allocates the annual county forecast across MMWR weeks; it is not observed county-week truth",
        scope: "national Lyme onset seasonality",
        source: "cdc_seasonality_week_2023",
      },
      selected_branch: {
        data_cutoff_date: "2023-12-31",
        evaluation_mode: "regional_annual_forecast_no_observed_target",
        forecast_origin_year: 2023,
        model_family: "empirical_bayes_spatial_regime",
        model_name: "empirical_bayes_spatial_regime_incidence",
        source_vintage: "cdc_lyme_county_dashboard_2023",
        update_mode: "pre_update",
      },
      signals_not_used: [
        "observed county-week Lyme cases",
        "observed county-week tick counts",
      ],
      signals_used: [
        "prior reported Lyme incidence",
        "trailing reported Lyme incidence",
        "county population denominator",
        "localized spatial-regime prior incidence",
        "empirical Bayes shrinkage toward a broader prior",
      ],
      target: {
        metric: "reported_lyme_incidence_per_100k",
      },
      uncertainty: {
        interval_method: "empirical_rolling_origin_residual_quantile",
        public_term: "forecast interval",
      },
      update_policy: {
        bayesian_update_method: "gamma_poisson_case_multiplier",
        bayesian_update_status: "research_backtest_only",
      },
    },
    records: [
      riskRecord(2024, "24001", "Allegany County", 21, 7, "high", 1.9, [0.9, 2.8], [0.4, 4.2]),
      riskRecord(2024, "42001", "Adams County", 21, 9, "very_high", 4.2565, [2.1, 5.3], [1.2, 7.1], {
        annualCases: 91.22,
        annualIncidence: 85.13,
      }),
      riskRecord(2024, "51810", "Virginia Beach city", 21, 3, "low", 0.5, [0.2, 0.8], [0.1, 1.1]),
      riskRecord(2025, "24001", "Allegany County", 21, 8, "high", 2.2, [1.1, 3.2], [0.6, 4.8]),
      riskRecord(2025, "51810", "Virginia Beach city", 21, 2, "very_low", 0.3, [0.1, 0.5], [0, 0.8]),
      riskRecord(2026, "24001", "Allegany County", 21, 9, "very_high", 2.6, [1.2, 3.8], [0.8, 5.4]),
      riskRecord(2026, "24023", "Garrett County", 21, 8, "high", 2.1, [1.0, 3.1], [0.6, 4.8]),
      riskRecord(2026, "51810", "Virginia Beach city", 21, 2, "very_low", 0.2, [0.05, 0.4], [0, 0.7]),
      riskRecord(2026, "24001", "Allegany County", 22, 10, "very_high", 3.12, [1.5, 4.3], [0.9, 6.2]),
      riskRecord(2026, "24023", "Garrett County", 22, 8, "high", 2.52, [1.1, 3.5], [0.7, 5.2]),
      riskRecord(2026, "51810", "Virginia Beach city", 22, 1, "very_low", 0.24, [0.02, 0.3], [0, 0.5]),
      riskRecord(2025, "24001", "Allegany County", 22, 8, "high", 2.64, [1.2, 3.6], [0.7, 5.1]),
      riskRecord(2025, "51810", "Virginia Beach city", 22, 2, "very_low", 0.36, [0.1, 0.6], [0, 0.9]),
    ],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
    score_scale: {
      range: [1, 10],
      score_denominator: 4.5,
    },
    selected_forecast_metadata: {
      forecast_origin_year: 2023,
    },
  },
  "regional_county_incidence_annual.json": {
    caveats: ["reported cases are not stable true incidence", "informational only"],
    county_count: 3,
    data_role: "observed_historical",
    export_type: "regional_county_incidence_annual",
    record_count: 3,
    records: [
      annualRecord("24001", "Allegany County", "MD", 2023, 35, 68000, 51.47, "top_quintile"),
      annualRecord("24023", "Garrett County", "MD", 2023, 22, 28500, 77.19, "top_decile"),
      annualRecord("42001", "Adams County", "PA", 2024, 128, 107154, 119.45, "top_decile"),
    ],
    research_status: {
      research_only: true,
      not_public_maryland_default: true,
    },
    year_range: [2023, 2024],
  },
  "regional_county_metadata.json": {
    county_count: 4,
    counties: [
      countyMetadata("24001", "Allegany County", "2024_regime_07", "Spatial regime 7", 7),
      countyMetadata("24023", "Garrett County", "2024_regime_07", "Spatial regime 7", 7),
      {
        ...countyMetadata(
          "42001",
          "Adams County",
          "2024_regime_07",
          "Spatial regime 7",
          7
        ),
        forecast_observed_fit: [
          {
            case_residual: 36.78,
            diagnostic_flags: [
              "partial_state_overlay",
              "post_forecast_diagnostic",
              "not_training_feature",
            ],
            diagnostic_scope: "pa_2024_partial_state_overlay",
            forecast_origin_year: 2023,
            forecast_year: 2024,
            incidence_residual_per_100k: 34.32,
            model_name: "empirical_bayes_spatial_regime_incidence",
            observed_cases: 128,
            observed_incidence_per_100k: 119.45,
            predicted_cases: 91.22,
            predicted_incidence_per_100k: 85.13,
          },
        ],
      },
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
      feature_count: 4,
      research_only: true,
      states: ["MD", "PA", "VA"],
    },
    features: [
      countyFeature("24001", "Allegany County", "MD", -79.5, 39.3),
      countyFeature("24023", "Garrett County", "MD", -79.2, 39.0),
      countyFeature("42001", "Adams County", "PA", -77.2, 39.9),
      countyFeature("51810", "Virginia Beach city", "VA", -76.0, 36.8),
    ],
  },
  "regional_states.geojson": {
    type: "FeatureCollection",
    metadata: {
      feature_count: 3,
      research_only: true,
      scope: "midatlantic_state_boundary",
    },
    features: [
      stateFeature("24", "MD", "Maryland", -79.8, 37.6, -75.0, 39.8),
      stateFeature("42", "PA", "Pennsylvania", -77.5, 39.6, -76.9, 40.2),
      stateFeature("51", "VA", "Virginia", -76.6, 36.2, -75.3, 37.4),
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
      "Research regional seasonal score derived from forecast-safe annual localized spatial regimes.",
    model_name: "empirical_bayes_spatial_regime_incidence",
    product_framing:
      "Lyme risk forecasting tool for Mid-Atlantic county annual disease pressure with seasonal allocation",
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

test("regional research dashboard renders annual forecasts, seasonal view, and regime intervals", async ({
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
    page.getByRole("heading", {
      name:
        "TickBiteRisk Regional Research: Lyme Disease Forecasting and Risk Assessment",
    })
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(
    "Research-only regional outputs are not the public Maryland default"
  );
  await expect(page.locator("body")).not.toContainText("not_public_maryland_default");
  await expect(page.locator("body")).not.toContainText("not public Maryland default");
  await expect(page.locator("body")).not.toContainText("Research only");
  const panel = page.locator("#regional-panel-content");
  const annualViewRadio = page.locator("#forecast-view-annual");
  const weeklyViewRadio = page.locator("#forecast-view-weekly");
  const regionScopeRadio = page.locator("#forecast-scope-region");
  const stateScopeRadio = page.locator("#forecast-scope-state");
  const regimeScopeRadio = page.locator("#forecast-scope-regime");
  const countyScopeRadio = page.locator("#forecast-scope-county");

  await expect(page.locator("#regional-risk-map path[data-county]")).toHaveCount(4);
  await expect(page.locator("#regional-risk-map .regional-state-boundary")).toHaveCount(3);
  await expect(page.locator(".regional-jump-links")).toContainText("Research notes");
  await expect(page.locator(".regional-jump-links")).toContainText("County details");
  await page.locator('.regional-jump-links a[href="#regional-source-title"]').click();
  await expect(page.locator("#regional-source-title")).toBeInViewport();
  await page.locator('.regional-source-section a[href="#regional-top"]').click();
  await expect(page.locator("#regional-top")).toBeInViewport();
  const mapBox = await page.locator(".regional-map-shell").boundingBox();
  const chartBox = await page.locator(".regional-chart-section").boundingBox();
  const panelBox = await page.locator("#regional-county-panel").boundingBox();
  const toolsBox = await page.locator(".regional-county-tools-section").boundingBox();
  expect(mapBox).not.toBeNull();
  expect(chartBox).not.toBeNull();
  expect(panelBox).not.toBeNull();
  expect(toolsBox).not.toBeNull();
  expect(Math.abs(chartBox.x - mapBox.x)).toBeLessThan(8);
  expect(chartBox.y).toBeGreaterThan(mapBox.y + mapBox.height - 8);
  expect(Math.abs(toolsBox.x - panelBox.x)).toBeLessThan(8);
  expect(toolsBox.y).toBeGreaterThan(panelBox.y + panelBox.height - 8);
  await expect(page.locator("#year-label")).toContainText("2026");
  await expect(page.locator("#year-mode-label")).toContainText("Forecast");
  await expect(page.locator(".forecast-view-radios")).toBeVisible();
  await expect(annualViewRadio).toBeChecked();
  await expect(weeklyViewRadio).toBeVisible();
  await expect(page.locator('label[for="forecast-view-annual"]')).toContainText(
    "Annual forecast"
  );
  await expect(page.locator('label[for="forecast-view-weekly"]')).toContainText(
    "Weekly seasonal risk"
  );
  await expect(page.locator("#forecast-view-label")).toContainText("Annual forecast");
  await page.locator('label[for="forecast-view-weekly"]').click();
  await expect(weeklyViewRadio).toBeChecked();
  await expect(page.locator("#forecast-view-label")).toContainText(
    "Weekly seasonal risk"
  );
  await page.locator('label[for="forecast-view-annual"]').click();
  await expect(annualViewRadio).toBeChecked();
  await expect(page.locator("#forecast-view-label")).toContainText("Annual forecast");
  await expect(page.locator(".forecast-scope-radios")).toBeVisible();
  await expect(regionScopeRadio).toBeChecked();
  await expect(stateScopeRadio).toBeVisible();
  await expect(regimeScopeRadio).toBeVisible();
  await expect(countyScopeRadio).toBeVisible();
  await expect(page.locator("#forecast-state-select")).toBeDisabled();
  await expect(page.locator("#forecast-county-select")).toBeDisabled();
  await expect(page.locator("#regional-regime-layer-toggle")).toBeChecked();
  await expect(page.locator("#regional-forecast-explainer")).toContainText(
    "Annual target"
  );
  await expect(page.locator("#regional-forecast-explainer")).toContainText(
    "empirical forecast-error ranges"
  );
  await expect(page.locator("#regional-forecast-explainer")).toContainText(
    "Map colors are display categories"
  );
  await expect(page.locator("#regional-forecast-explainer")).toContainText(
    "not automatic public score corrections"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Regional annual forecast"
  );
  await expect(page.locator("#regional-forecast-chart")).not.toHaveAttribute(
    "role",
    "img"
  );
  await expect(page.locator("#regional-forecast-chart svg")).toHaveAttribute(
    "aria-label",
    /Regional annual incidence forecast/
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "32.67 per 100k"
  );
  await expectWeekControlsDisabled(page);
  await expect(panel).toHaveAttribute(
    "aria-live",
    "polite"
  );

  await page.locator('path[data-county="24001"]').click();
  await expect(countyScopeRadio).toBeChecked();
  await expect(page.locator("#forecast-county-select")).toHaveValue("24001");
  await expect(panel).toContainText("Allegany County");
  await expect(panel).toContainText("MD");
  await expect(panel).toContainText("How bad is it?");
  await expect(panel).toContainText("Predicted score");
  await expect(panel).toContainText("10/10");
  await expect(panel).toContainText("peak seasonal score");
  await expect(panel).toContainText("Forecast percentile");
  await expect(panel).toContainText("82nd percentile");
  await expect(panel).toContainText("above typical");
  await expect(panel).toContainText("Predicted annual incidence");
  await expect(panel).toContainText("52.00 per 100k");
  await expect(panel).toContainText("Predicted annual cases");
  await expect(panel).not.toContainText("Predicted weekly incidence");
  await expect(panel).not.toContainText("MMWR week 21");
  await expect(panel).toContainText(
    "Why this forecast?"
  );
  await expect(panel).toContainText(
    "County level data are released as annual totals only"
  );
  await expect(panel).toContainText(
    "The most recent CDC county data available in this release are 2023"
  );
  await expect(panel).toContainText(
    "prior reported Lyme incidence"
  );
  await expect(panel).toContainText(
    "localized spatial-regime prior incidence"
  );
  await expect(panel).not.toContainText("Not used:");
  await expect(panel).not.toContainText("observed county-week Lyme cases");
  await expect(panel).toContainText(
    "Seasonal allocation"
  );
  await expect(panel).toContainText(
    "national Lyme onset seasonality"
  );
  await expect(panel).toContainText(
    "Bayesian updates"
  );
  await expect(panel).toContainText(
    "not part of the displayed score yet"
  );
    await expect(panel).toContainText(
      "Nearest comparable history"
    );
    await expect(panel).toContainText(
      "2018 origin -> 2021 observed outcome"
    );
    await expect(panel).toContainText(
      "How unusual is this forecast?"
    );
    await expect(panel).toContainText(
      "above typical"
    );
    await expect(panel).toContainText(
      "82nd percentile"
    );
    await expect(panel).toContainText(
      "likely range 65th percentile to 91st percentile"
    );
    await expect(panel).toContainText(
      "not tick abundance"
    );
  await expect(panel).toContainText(
    "Spatial regime 7"
  );
  await expect(panel).not.toContainText("Feature year");
  await expect(panel).not.toContainText("Forecast origin");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "Local forecast region"
  );
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "Forecast year 2026"
  );
  await expect(page.locator("#regional-regime-panel")).toContainText("2 counties");
  await expect(page.locator("#regional-regime-panel")).toContainText("Region counties");
  await expect(page.locator("#regional-regime-panel")).toContainText("Allegany County");
  await expect(page.locator("#regional-regime-panel")).toContainText("Garrett County");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "Region 95% interval: 8.20 to 31.50 per 100k"
  );
  await expect(page.locator("#regional-chart-summary")).not.toContainText(
    "weekly forecast window"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "The brown line is observed annual reported incidence"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "The blue dot is the selected annual forecast"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Allegany County annual forecast"
  );
  await page.locator('label[for="forecast-scope-region"]').click();
  await expect(regionScopeRadio).toBeChecked();
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Regional annual forecast"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "3 counties in this chart"
  );
  await page.locator('label[for="forecast-scope-state"]').click();
  await page.locator("#forecast-state-select").selectOption("MD");
  await expect(stateScopeRadio).toBeChecked();
  await expect(page.locator("#forecast-state-select")).toBeEnabled();
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "MD state annual forecast"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "47.00 per 100k"
  );
  await page.locator('label[for="forecast-scope-county"]').click();
  await page.locator("#forecast-county-select").selectOption("24001");
  await expect(countyScopeRadio).toBeChecked();
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Allegany County annual forecast"
  );

  await page.locator('label[for="forecast-view-weekly"]').click();
  await expect(page.locator("#forecast-view-label")).toContainText(
    "Weekly seasonal risk"
  );
  await expectWeekControlsEnabled(page);
  await expect(page.locator("#week-label")).toContainText("May 24-30, 2026");
  await expect(page.locator("#week-label")).toContainText("MMWR week 21");
  await expect(panel).toContainText("May 24-30, 2026");
  await expect(panel).toContainText("MMWR week 21");
  await expect(panel).toContainText("9/10");
  await expect(panel).toContainText("selected week score");
  await expect(panel).toContainText("Season peak");
  await expect(panel).toContainText("10/10");
  await expect(panel).toContainText("Predicted weekly incidence");
  await expect(panel).toContainText(
    "Linear score"
  );
  await expect(panel).toContainText(
    "score denominator 4.50"
  );
  await expect(panel).toContainText(
    "rounded and clamped to 1-10"
  );
  await expect(panel).toContainText(
    "95% empirical interval: 0.80 to 5.40 per 100k"
  );
  await expect(page.locator("#regional-forecast-chart svg")).toBeVisible();
  await expect(page.locator("#regional-forecast-chart .interval-band-95")).toHaveCount(1);
  await expect(page.locator("#regional-forecast-chart .county-forecast-line")).toHaveCount(1);
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "The green line is the predicted weekly Lyme incidence"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Dark blue band"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Light blue band"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "past forecast errors"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "not medical confidence intervals"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "The red dot marks the selected week"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText("MMWR weeks 21-22");
  await expect(page.locator("#regional-forecast-chart [data-active-week=\"21\"]")).toHaveCount(1);
  await expect(page.locator('path[data-county="24023"]')).toHaveClass(
    /is-same-regime/
  );
  await expect(page.locator('path[data-county="51810"]')).not.toHaveClass(
    /is-same-regime/
  );
  await page.locator("#regional-regime-layer-toggle").setChecked(false);
  await expect(page.locator('path[data-county="24023"]')).not.toHaveClass(
    /is-same-regime/
  );
  await page.locator("#regional-regime-layer-toggle").setChecked(true);
  await expect(page.locator('path[data-county="24023"]')).toHaveClass(
    /is-same-regime/
  );
  await page.locator('label[for="forecast-scope-regime"]').click();
  await expect(regimeScopeRadio).toBeChecked();
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Spatial regime 7 local region weekly forecast"
  );
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "MMWR weeks 21-22"
  );

  await page.locator("#week-slider").fill("22");
  await expect(page.locator("#week-label")).toContainText("May 31-Jun 6, 2026");
  await expect(page.locator("#week-label")).toContainText("MMWR week 22");
  await expect(panel).toContainText(
    "May 31-Jun 6, 2026"
  );
  await expect(panel).toContainText("10/10");
  await expect(panel).toContainText(
    "95% empirical interval: 0.90 to 6.20 per 100k"
  );
  await expect(page.locator("#regional-forecast-chart [data-active-week=\"22\"]")).toHaveCount(1);

  await page.locator('path[data-county="51810"]').click();
  await expect(panel).toContainText(
    "Virginia Beach city"
  );
  await expect(panel).toContainText("VA");
  await expect(page.locator("#regional-regime-panel")).toContainText("Spatial regime 2");
  await expect(page.locator("#regional-regime-panel")).toContainText("Virginia Beach city");
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Virginia Beach city weekly forecast"
  );

  await page.locator("#state-filter").selectOption("MD");
  await expect(page.locator("#regional-list-status")).toContainText("2 county choices");
  await expect(page.locator("#regional-county-list")).toHaveCount(0);
  await page.locator("#county-search").fill("Garrett");
  await expect(page.locator("#regional-list-status")).toContainText("1 county choice");
  await expect(page.locator("#regional-county-picker")).toContainText("Garrett County");
  await expect(page.locator("#regional-county-picker")).toHaveValue("24023");
  await expect(panel).toContainText("Garrett County");
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "Garrett County weekly forecast"
  );
  await page.locator("#regional-bite-tick-species").selectOption("ixodes_scapularis");
  await page.locator("#regional-bite-tick-stage").selectOption("nymph");
  await page.locator("#regional-bite-attachment-hours").fill("48");
  await page.locator("#regional-bite-engorgement").selectOption("engorged");
  await page.locator("#regional-bite-hours-since-removal").fill("24");
  await page.locator("#regional-bite-doxycycline-safe").selectOption("true");
  await page.locator("#regional-bite-tick-count").fill("1");
  await page.locator("#regional-bite-form button[type=\"submit\"]").click();
  await expect(page.locator("#regional-bite-result")).toContainText(
    "Bite concern score"
  );
  await expect(page.locator("#regional-bite-result")).toContainText(
    "CDC consideration context"
  );
  await expect(page.locator("#regional-bite-result")).toContainText(
    "Bite-specific caveats"
  );
  await expect(page.locator("#regional-bite-result")).toContainText(
    "not an absolute infection probability"
  );

  await expect(page.locator("#regional-source-content")).toContainText(
    "Forecast-safe branches use prior-year"
  );
  await expect(page.locator("#regional-source-content")).toContainText(
    "Predicted score footnote"
  );
  await expect(page.locator("#regional-source-content")).toContainText(
    "Annual view shows the peak weekly score"
  );
  await expect(page.locator("#regional-source-content")).toContainText(
    "not a personal infection probability"
  );
  await expect(page.locator("#regional-source-content")).not.toContainText(
    "not public Maryland default"
  );
  await expect(page.locator("#regional-forecast-provenance")).toContainText(
    "Data through 2023"
  );
  await expect(page.locator("#regional-forecast-provenance")).toContainText(
    "Forecast year 2026"
  );
  await expect(page.locator("#regional-forecast-provenance")).toContainText(
    "empirical bayes spatial regime incidence"
  );

  await page.locator("#year-select").selectOption("2023");
  await expect(page.locator("#year-label")).toContainText("2023");
  await expect(page.locator("#year-mode-label")).toContainText("Observed historical");
  await expect(page.locator("#forecast-view-label")).toContainText(
    "Observed historical annual data"
  );
  await expectWeekControlsDisabled(page);
  await expect(panel).toContainText(
    "Observed historical"
  );
  await expect(panel).toContainText("22 reported cases");
  await expect(panel).toContainText("77.19 per 100k");
  await expect(panel).toContainText("Surveillance protocol");
  await expect(panel).toContainText("2022 surveillance definition era");
  await expect(panel).not.toContainText("Feature year");
  await expect(panel).not.toContainText("Forecast origin");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "Forecast regions are shown only for forecast years"
  );
  await expect(page.locator("#regional-regime-panel")).not.toContainText("Feature year");
  await expect(page.locator('path[data-county="24001"]')).not.toHaveClass(
    /is-same-regime/
  );
  await expect(page.locator("#regional-forecast-chart .observed-history-line")).toHaveCount(1);
  await expect(page.locator("#regional-chart-summary")).toContainText(
    "observed annual incidence history"
  );
  await expect(page.locator("#regional-source-content")).toContainText(
    "reported cases are not stable true incidence"
  );

  await page.locator("#year-select").selectOption("2024");
  await expect(page.locator("#year-label")).toContainText("2024");
  await expect(page.locator("#year-mode-label")).toContainText(
    "Forecast with observed comparison"
  );
  await expect(page.locator("#forecast-view-label")).toContainText("Annual forecast");
  await expectWeekControlsDisabled(page);
  await page.locator('path[data-county="24001"]').click();
  await expect(panel).toContainText("Predicted score");
  await expect(panel).toContainText("7/10");
  await expect(panel).toContainText("Predicted annual incidence");
  await expect(panel).toContainText("38.00 per 100k");
  await expect(panel).toContainText("Predicted annual cases");
  await expect(panel).toContainText("How unusual is this forecast?");
  await expect(panel).toContainText("55th percentile");
  await expect(panel).not.toContainText("Feature year");
  await expect(panel).not.toContainText("Forecast origin");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "No local forecast region summary is available for 2024"
  );
  await expect(page.locator("#regional-regime-panel")).not.toContainText(
    "Region 95% interval"
  );
  await expect(panel).not.toContainText("Observed historical");
  await expect(panel).not.toContainText("Predicted weekly incidence");
  await expect(panel).not.toContainText(
    "PA 2024 forecast check"
  );
  await page.locator('path[data-county="42001"]').click();
  await expect(panel).toContainText(
    "Adams County"
  );
  await expect(panel).toContainText("PA");
  await expect(panel).toContainText("Predicted annual incidence");
  await expect(panel).toContainText("85.13 per 100k");
  await expect(panel).toContainText("Predicted annual cases");
  await expect(panel).toContainText("91.22");
  await expect(panel).toContainText(
    "PA 2024 forecast check"
  );
  await expect(panel).toContainText(
    "observed 119.45 per 100k vs forecast 85.13 per 100k"
  );
  await expect(panel).toContainText(
    "Cases: observed 128.00 vs forecast 91.22"
  );
  await expect(panel).toContainText(
    "post-forecast goodness-of-fit"
  );
  await expect(panel).not.toContainText("observed reported incidence");
  await expect(panel).not.toContainText("Predicted weekly incidence");
  await expect(page.locator("#regional-forecast-provenance")).toContainText(
    "Forecast with observed comparison"
  );

  await page.locator("#year-select").selectOption("2025");
  await expect(page.locator("#year-label")).toContainText("2025");
  await expect(page.locator("#year-mode-label")).toContainText("Forecast");
  await expect(page.locator("#forecast-view-label")).toContainText("Annual forecast");
  await expectWeekControlsDisabled(page);
  await page.locator('path[data-county="24001"]').click();
  await expect(panel).toContainText("Predicted score");
  await expect(panel).toContainText("8/10");
  await expect(panel).toContainText("Predicted annual incidence");
  await expect(panel).toContainText("44.00 per 100k");
  await expect(panel).toContainText("Predicted annual cases");
  await expect(panel).toContainText("65th percentile");
  await expect(page.locator("#regional-regime-panel")).toContainText(
    "No local forecast region summary is available for 2025"
  );
  await expect(panel).not.toContainText("Predicted weekly incidence");

  await page.locator("#year-select").selectOption("2026");
  await expect(page.locator("#year-label")).toContainText("2026");
  await expect(page.locator("#year-mode-label")).toContainText("Forecast");
  await expect(page.locator("#forecast-view-label")).toContainText("Annual forecast");
  await expectWeekControlsDisabled(page);
  await page.locator('path[data-county="24023"]').click();
  await expect(panel).toContainText("Predicted score");
  await expect(panel).toContainText("8/10");
  await expect(panel).toContainText("Predicted annual incidence");
  await expect(panel).toContainText("42.00 per 100k");
  await expect(panel).not.toContainText("Predicted weekly incidence");

  await page.locator("#regional-forecast-chart").scrollIntoViewIfNeeded();
  await expect(page.locator(".regional-time-toolbar")).toBeInViewport();
  await expect(page.locator("body")).not.toContainText("not_public_maryland_default");
  await expect(page.locator("body")).not.toContainText("not public Maryland default");
  await expect(page.locator("body")).not.toContainText("Research only");

  expect(consoleErrors).toEqual([]);
});

async function expectWeekControlsDisabled(page) {
  await expect(page.locator("#week-input")).toBeDisabled();
  await expect(page.locator("#week-slider")).toBeDisabled();
}

async function expectWeekControlsEnabled(page) {
  await expect(page.locator("#week-input")).toBeEnabled();
  await expect(page.locator("#week-slider")).toBeEnabled();
}

function riskRecord(
  year,
  countyFips,
  countyName,
  mmwrWeek,
  score,
  category,
  weeklyIncidence,
  interval80,
  interval95,
  options = {}
) {
  const annualIncidence =
    options.annualIncidence ?? weeklyIncidence / seasonalityShare(mmwrWeek);
  const annualCases = options.annualCases ?? annualIncidence;
  const weeklyCases = annualCases * seasonalityShare(mmwrWeek);

  return {
    backtest_assumption_flags: [
      "not_public_default",
      "not_public_maryland_default",
      "forecast_without_observed_target",
    ],
    county_fips: countyFips,
    county_name: countyName,
    data_year: year,
    feature_quality_flags: [
      "localized_spatial_regime_feature",
      "forecast_safe_prior_history_spatial_regime",
      "empirical_prediction_band",
    ],
    mmwr_week: mmwrWeek,
    week_start_date: mmwrWeek === 22 ? `${year}-05-31` : `${year}-05-24`,
    week_end_date: mmwrWeek === 22 ? `${year}-06-06` : `${year}-05-30`,
    predicted_weekly_incidence_80_interval: interval80,
    predicted_weekly_incidence_95_interval: interval95,
    predicted_annual_cases: annualCases,
    predicted_annual_incidence_per_100k: annualIncidence,
    predicted_weekly_cases: weeklyCases,
    predicted_weekly_incidence_per_100k: weeklyIncidence,
    risk_category: category,
    risk_score: score,
    year,
  };
}

function seasonalityShare(mmwrWeek) {
  return mmwrWeek === 22 ? 0.06 : 0.05;
}

function annualRecord(
  countyFips,
  countyName,
  stateAbbr,
  year,
  reportedCases,
  population,
  incidence,
  tier
) {
  return {
    county_fips: countyFips,
    county_name: countyName,
    data_role: "observed_historical",
    diagnostic_midatlantic_incidence_percentile: tier === "top_decile" ? 0.96 : 0.82,
    diagnostic_midatlantic_incidence_rank: tier === "top_decile" ? 6 : 30,
    diagnostic_midatlantic_incidence_tier: tier,
    feature_quality_flags: [
      "reported_cases_not_stable_true_incidence",
      "diagnostic_same_year_not_forecast_feature",
    ],
    incidence_per_100k: incidence,
    population,
    reported_cases: reportedCases,
    state_abbr: stateAbbr,
    state_fips: countyFips.slice(0, 2),
    state_name:
      stateAbbr === "MD"
        ? "Maryland"
        : stateAbbr === "PA"
          ? "Pennsylvania"
          : "Virginia",
    year,
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
    nearest_comparable_years: [
      {
        analog_model_name: "analog_year_county_incidence",
        basis: "horizon-matched reported-incidence history",
        forecast_horizon_years: 3,
        forecast_origin_year: 2023,
        forecast_year: 2026,
        match_distance: 2.75,
        match_observed_year: 2021,
        match_origin_year: 2018,
        predicted_incidence_per_100k: 42.5,
      },
    ],
    forecast_typicality: forecastTypicalityRows(),
  };
}

function forecastTypicalityRows() {
  return [
    forecastTypicalityRow(2024, 55, 30, 78, "typical", 38),
    forecastTypicalityRow(2025, 65, 42, 85, "typical", 44),
    forecastTypicalityRow(2026, 82, 65, 91, "above typical", 52),
  ];
}

function forecastTypicalityRow(year, percentile, lower, upper, label, incidence) {
  return {
    baseline_year_count: 23,
    comparison_scope: "county_prior_history",
    comparison_year_end: 2023,
    comparison_year_start: 2001,
    forecast_percentile_of_county_history: percentile,
    forecast_year: year,
    interval_severity_label: "typical to much higher than typical",
    lower_80_percentile_of_county_history: lower,
    model_name: "empirical_bayes_spatial_regime_incidence",
    predicted_incidence_per_100k: incidence,
    protocol_policy: "raw_with_surveillance_protocol_caveat",
    severity_label: label,
    typical_p75_incidence_per_100k: 45,
    typicality_evidence_level: "moderate",
    upper_80_percentile_of_county_history: upper,
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

function stateFeature(stateFips, stateAbbr, stateName, minLon, minLat, maxLon, maxLat) {
  return {
    type: "Feature",
    properties: {
      state_abbr: stateAbbr,
      state_fips: stateFips,
      state_name: stateName,
    },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [minLon, minLat],
          [maxLon, minLat],
          [maxLon, maxLat],
          [minLon, maxLat],
          [minLon, minLat],
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
