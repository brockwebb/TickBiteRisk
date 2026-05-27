import { expect, test } from "@playwright/test";

test("static dashboard renders map, bite score, validation, and sources", async ({
  page,
}) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "TickBiteRisk" })).toBeVisible();
  await expect(page.locator("#risk-map path[data-county]")).toHaveCount(24);
  await expect(page.locator("main[aria-live]")).toHaveCount(0);
  await expect(page.locator("#panel-content")).toHaveAttribute("aria-live", "polite");

  await page.locator('path[data-county="24003"]').click();
  await expect(page.locator("#panel-content")).toContainText("Anne Arundel");
  await expect(page.locator("#panel-content")).toContainText("Model source");

  await page.locator("#date-input").fill("2026-05-26");
  await expect(page.locator("#week-label")).toContainText("MMWR week 21");

  await page.locator("#bite-tick-species").selectOption("ixodes_scapularis");
  await page.locator("#bite-tick-stage").selectOption("nymph");
  await page.locator("#bite-attachment-hours").fill("40");
  await page.locator("#bite-engorgement").selectOption("engorged");
  await page.locator("#bite-hours-since-removal").fill("24");
  await page.locator("#bite-doxycycline-safe").selectOption("true");
  await page.getByRole("button", { name: "Calculate bite score" }).click();

  await expect(page.locator("#bite-result")).toContainText("Single-bite Lyme score");
  await expect(page.locator("#bite-result")).toContainText("CDC criteria");
  await expect(page.locator("#bite-result")).toContainText("Bite-specific caveats");

  await expect(page.locator("#validation-summary")).toContainText("rank_by_mae");
  await expect(page.locator("#validation-summary")).toContainText("18.24 per 100k");

  await expect(page.locator("#source-content")).toContainText("Public source chain");
  await expect(page.locator("#source-content")).toContainText(
    "US Census TIGERweb county geometry"
  );

  expect(consoleErrors).toEqual([]);
});
