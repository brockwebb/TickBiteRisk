const state = {
  weekly: null,
  counties: null,
  modelCard: null,
  sourceCatalog: null,
  selectedCounty: "24003",
  selectedWeek: 1,
  byCountyWeek: new Map(),
  biteEstimateRequested: false,
};

const dataPaths = {
  weekly: "data/md_county_risk_weekly.json",
  counties: "data/md_counties.geojson",
  modelCard: "data/model_card.json",
  sourceCatalog: "data/source_catalog.json",
};

const flagLabels = {
  relative_seasonal_baseline: "Relative seasonal forecast",
  static_seasonality_prior:
    "Uses static CDC onset seasonality and is not county-specific",
  not_weather_adjusted: "This is not a weather-adjusted forecast",
  intervention_caveat: "Prevention and intervention effects are not modeled",
  intervention_history_unmodeled:
    "Prevention and intervention effects are not modeled",
  surveillance_change_caveat:
    "Surveillance and reporting changes can affect comparisons",
  surveillance_reporting_sensitive:
    "Surveillance and reporting changes can affect comparisons",
  lyme_case_definition_change:
    "Lyme case definitions changed over time, which affects comparisons",
  current_status_retrospective_proxy:
    "Current tick status is used as retrospective context, not historical proof",
  status_only_not_prevalence:
    "Tick surveillance status indicates presence categories, not infection prevalence",
  no_records_not_absence:
    "No tick record does not prove the tick or pathogen is absent",
  national_curve_not_county_specific:
    "CDC national onset seasonality is not county-specific",
  shares_normalized_by_annual_total:
    "Seasonal shares are normalized from annual totals",
  empirical_prediction_band:
    "Uncertainty bands are empirical model intervals, not clinical confidence for an individual bite",
  deer_prior_season_derived_total:
    "Deer harvest is a prior-season ecological proxy, not a direct disease driver",
  partial_weather_year:
    "Weather features are partial for this year",
  missing_deer_harvest_prior_season:
    "Prior-season deer harvest data are missing for this county-year",
  observational_not_causal:
    "This observational forecast does not prove causes",
  population_structure_proxy:
    "Age structure is a population context proxy, not a direct exposure measure",
  human_exposure_context_only:
    "Human exposure context, not observed tick encounters",
  not_tick_bite_counts: "Not tick-bite counts",
  census_vintage_revision_sensitive:
    "Census estimate vintages can be revised",
  mdh_probable_only_2024:
    "2024 MDH row is probable-only and not directly comparable to final CDC public-use data",
  state_source_not_cdc_public_use:
    "State source row, not CDC public-use data",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setDefaultDate();
  document.getElementById("date-input").addEventListener("change", handleDateChange);
  document.getElementById("bite-form").addEventListener("submit", handleBiteSubmit);

  try {
    const [weekly, counties, modelCard, sourceCatalog] = await Promise.all([
      fetchJson(dataPaths.weekly),
      fetchJson(dataPaths.counties),
      fetchJson(dataPaths.modelCard),
      fetchJson(dataPaths.sourceCatalog),
    ]);

    state.weekly = weekly;
    state.counties = counties;
    state.modelCard = modelCard;
    state.sourceCatalog = sourceCatalog;
    indexWeeklyRecords(weekly.records || []);
    selectDefaultCounty();
    renderMap();
    renderCountyList();
    renderSources();
    renderValidationSummary();
    renderForecastExplainer();
    selectCounty(state.selectedCounty);
  } catch (error) {
    renderLoadError(error);
  }
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Could not load ${path}`);
  }
  return response.json();
}

function setDefaultDate() {
  const input = document.getElementById("date-input");
  const today = new Date();
  input.value = today.toISOString().slice(0, 10);
  const [, week] = mmwrYearWeek(input.value);
  state.selectedWeek = week;
  updateWeekLabel();
}

function handleDateChange(event) {
  const [, week] = mmwrYearWeek(event.target.value);
  state.selectedWeek = week;
  updateWeekLabel();
  renderMap();
  renderCountyList();
  selectCounty(state.selectedCounty);
  if (state.biteEstimateRequested) renderBiteResult();
}

function handleBiteSubmit(event) {
  event.preventDefault();
  state.biteEstimateRequested = true;
  renderBiteResult();
}

function mmwrYearWeek(dateString) {
  const date = new Date(`${dateString}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return [new Date().getUTCFullYear(), 1];
  }
  const calendarYear = date.getUTCFullYear();
  const yearStart = firstMmwrSunday(calendarYear);
  const nextYearStart = firstMmwrSunday(calendarYear + 1);
  let mmwrYear = calendarYear;
  if (date < yearStart) {
    mmwrYear = calendarYear - 1;
  } else if (date >= nextYearStart) {
    mmwrYear = calendarYear + 1;
  }
  const firstSunday = firstMmwrSunday(mmwrYear);
  const millisecondsPerWeek = 7 * 24 * 60 * 60 * 1000;
  const week = Math.floor((date - firstSunday) / millisecondsPerWeek) + 1;

  return [mmwrYear, week];
}

function firstMmwrSunday(year) {
  const jan1 = new Date(Date.UTC(year, 0, 1, 12));
  const jan1Day = jan1.getUTCDay();
  const firstSunday = new Date(jan1);
  if (jan1Day <= 3) {
    firstSunday.setUTCDate(jan1.getUTCDate() - jan1Day);
  } else {
    firstSunday.setUTCDate(jan1.getUTCDate() + (7 - jan1Day));
  }
  return firstSunday;
}

function updateWeekLabel() {
  document.getElementById("week-label").textContent = `Using MMWR week ${state.selectedWeek}`;
}

function indexWeeklyRecords(records) {
  state.byCountyWeek.clear();
  for (const record of records) {
    state.byCountyWeek.set(`${record.county_fips}:${record.mmwr_week}`, record);
  }
}

function selectDefaultCounty() {
  const firstFeature = state.counties && state.counties.features[0];
  if (!state.byCountyWeek.has(`${state.selectedCounty}:${state.selectedWeek}`) && firstFeature) {
    state.selectedCounty = firstFeature.properties.county_fips;
  }
}

function getRecord(countyFips) {
  return state.byCountyWeek.get(`${countyFips}:${state.selectedWeek}`);
}

function riskClass(score) {
  if (score >= 9) return "risk-very-high";
  if (score >= 7) return "risk-high";
  if (score >= 5) return "risk-moderate";
  if (score >= 3) return "risk-low";
  return "risk-very-low";
}

function renderMap() {
  const container = document.getElementById("risk-map");
  if (!state.counties) return;

  const features = state.counties.features || [];
  const bounds = geoBounds(features);
  const width = 720;
  const height = 520;
  const paths = features.map((feature) => countyPath(feature, bounds, width, height)).join("");

  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="group" aria-label="Maryland counties colored by relative Lyme forecast">${paths}</svg>`;
  container.querySelectorAll("[data-county]").forEach((shape) => {
    shape.addEventListener("click", () => selectCounty(shape.dataset.county));
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCounty(shape.dataset.county);
      }
    });
  });
  updateSelectedControls();
}

function countyPath(feature, bounds, width, height) {
  const props = feature.properties;
  const record = getRecord(props.county_fips);
  const score = record ? record.risk_score : 0;
  const label = record
    ? `${props.county_name}, ${categoryLabel(record.risk_category)}, ${score} of 10`
    : `${props.county_name}, no forecast available`;

  return `<path
    class="county-shape ${record ? riskClass(score) : "risk-unavailable"}"
    d="${geometryPath(feature.geometry, bounds, width, height)}"
    data-county="${escapeHtml(props.county_fips)}"
    role="button"
    tabindex="0"
    aria-label="${escapeHtml(label)}"
    aria-pressed="${props.county_fips === state.selectedCounty ? "true" : "false"}">
    <title>${escapeHtml(label)}</title>
  </path>`;
}

function renderCountyList() {
  const list = document.getElementById("county-list");
  const features = state.counties ? state.counties.features || [] : [];
  list.innerHTML = features.map(countyListButton).join("");
  list.querySelectorAll("button[data-county]").forEach((button) => {
    button.addEventListener("click", () => selectCounty(button.dataset.county));
  });
  updateSelectedControls();
}

function countyListButton(feature) {
  const props = feature.properties;
  const record = getRecord(props.county_fips);
  const score = record ? record.risk_score : "NA";
  const category = record ? categoryLabel(record.risk_category) : "unavailable";
  const badgeClass = record ? riskClass(record.risk_score) : "risk-unavailable";

  return `<button type="button" data-county="${escapeHtml(props.county_fips)}" aria-pressed="${props.county_fips === state.selectedCounty ? "true" : "false"}">
    <span>${escapeHtml(props.county_name)}<br><small>${escapeHtml(category)}</small></span>
    <span class="score-badge ${badgeClass}">${escapeHtml(score)}/10</span>
  </button>`;
}

function selectCounty(countyFips) {
  state.selectedCounty = countyFips;
  const record = getRecord(countyFips);
  const feature = findCountyFeature(countyFips);
  const countyName = feature ? feature.properties.county_name : countyFips;
  const panel = document.getElementById("panel-content");

  if (!record) {
    panel.innerHTML = `<p>No forecast row available for ${escapeHtml(countyName)} in MMWR week ${state.selectedWeek}.</p>`;
    updateSelectedControls();
    return;
  }

  const interval95 = record.predicted_weekly_incidence_95_interval || [0, 0];
  panel.innerHTML = `<div class="score-card">
    <p class="muted">MMWR week ${escapeHtml(record.mmwr_week)}, data year ${escapeHtml(record.data_year)}</p>
    <h3>${escapeHtml(record.county_name)}</h3>
    <p><span class="score-badge ${riskClass(record.risk_score)}">${escapeHtml(record.risk_score)}/10</span> ${escapeHtml(categoryLabel(record.risk_category))}</p>
    <p>${escapeHtml(sentenceCase(record.risk_category))} relative seasonal forecast for Lyme reports in Maryland counties like this one during this week.</p>
    <p>Predicted weekly incidence: ${formatNumber(record.predicted_weekly_incidence_per_100k)} per 100k.</p>
    <p>95% empirical interval: ${formatNumber(interval95[0])} to ${formatNumber(interval95[1])} per 100k.</p>
    ${renderModelLineage(record)}
    ${renderFlagCaveats(record)}
    <p class="disclaimer">This is not a per-bite infection probability, diagnosis, or medical advice.</p>
  </div>`;
  updateSelectedControls();
  if (state.biteEstimateRequested) renderBiteResult();
}

function renderBiteResult() {
  const target = document.getElementById("bite-result");
  const record = getRecord(state.selectedCounty);
  if (!record) {
    target.innerHTML = "<p>Select a county/date with an available forecast first.</p>";
    return;
  }
  const result = estimateSingleBiteRisk(record, readBiteInputs());
  const criteriaItems = result.pep_criteria
    .map(
      (criterion) => `<li>
        <span class="criteria-status">${escapeHtml(criterion.status)}</span>
        <span>${escapeHtml(readableModelName(criterion.criterion))}</span>
        <small>${escapeHtml(criterion.explanation)}</small>
      </li>`
    )
    .join("");

  target.innerHTML = `<section aria-labelledby="bite-result-title">
    <h4 id="bite-result-title">Single-bite Lyme score</h4>
    <p><span class="score-badge ${riskClass(result.single_bite_risk_score)}">${escapeHtml(result.single_bite_risk_score)}/10</span> ${escapeHtml(result.single_bite_risk_band)}</p>
    <p>${escapeHtml(result.risk_interpretation)}</p>
    <p><b>CDC criteria:</b> ${escapeHtml(readableModelName(result.pep_consideration))}</p>
    <ul class="criteria-list">${criteriaItems}</ul>
    ${renderBiteCaveats(result.caveats)}
    <p class="disclaimer">This is not an absolute infection probability, diagnosis, or treatment recommendation.</p>
  </section>`;
}

function renderBiteCaveats(caveats) {
  if (!caveats || !caveats.length) return "";
  const items = caveats
    .map((caveat) => `<li>${escapeHtml(readableBiteCaveat(caveat))}</li>`)
    .join("");
  return `<section class="bite-caveats" aria-labelledby="bite-caveats-title">
    <h5 id="bite-caveats-title">Bite-specific caveats</h5>
    <ul>${items}</ul>
  </section>`;
}

function readableBiteCaveat(caveat) {
  const labels = {
    maryland_high_incidence_geography_floor:
      "Maryland high-incidence context keeps this from being treated as a near-zero bite concern.",
    non_ixodes_lyme_vector_unlikely: "non ixodes Lyme vector unlikely",
    not_calibrated_absolute_probability:
      "not calibrated as an absolute infection probability",
    not_diagnosis_or_treatment_recommendation:
      "not a diagnosis or treatment recommendation",
  };
  return labels[caveat] || sentenceCase(String(caveat).replaceAll("_", " "));
}

function readBiteInputs() {
  return {
    tick_species: document.getElementById("bite-tick-species").value,
    tick_stage: document.getElementById("bite-tick-stage").value,
    attachment_hours: optionalNumber("bite-attachment-hours"),
    engorgement: document.getElementById("bite-engorgement").value,
    hours_since_removal: optionalNumber("bite-hours-since-removal"),
    doxycycline_safe: optionalBoolean("bite-doxycycline-safe"),
    tick_count: optionalNumber("bite-tick-count") || 1,
  };
}

function estimateSingleBiteRisk(record, input) {
  const modifiers = {
    location_season: locationSeasonModifier(record),
    tick_species: speciesModifier(input.tick_species),
    tick_stage: stageModifier(input.tick_stage),
    attachment: attachmentModifier(input.attachment_hours, input.engorgement),
  };
  const rawSingle = Math.min(
    1,
    Math.max(
      0,
      modifiers.location_season *
        modifiers.tick_species *
        modifiers.tick_stage *
        modifiers.attachment
    )
  );
  const tickCount = Math.min(20, Math.max(1, Number(input.tick_count || 1)));
  const combined = 1 - (1 - rawSingle) ** tickCount;
  const scoreRaw = Number((combined * 10).toFixed(6));
  const score = Math.max(1, Math.min(10, Math.ceil(scoreRaw)));
  const criteria = pepCriteria(record, input);
  return {
    single_bite_risk_score: score,
    single_bite_risk_band: biteRiskBand(score),
    single_bite_risk_score_raw: scoreRaw,
    pep_consideration: pepConsideration(criteria),
    pep_criteria: criteria,
    evidence_modifiers: modifiers,
    caveats: biteCaveats(record, input),
    risk_interpretation:
      "This score combines the selected county-week forecast with tick identity, stage, attachment, engorgement, and tick count. It is not an absolute infection probability.",
  };
}

function locationSeasonModifier(record) {
  const baseline = Number(record.risk_score || 1) / 10;
  if (String(record.county_fips || "").startsWith("24")) {
    return Math.max(baseline, 0.45);
  }
  return baseline;
}

function speciesModifier(species) {
  if (species === "ixodes_scapularis") return 1;
  if (species === "possible_ixodes") return 0.75;
  if (species === "unknown") return 0.5;
  return 0.05;
}

function stageModifier(stage) {
  if (stage === "nymph") return 1;
  if (stage === "adult") return 0.85;
  if (stage === "larva") return 0.1;
  return 0.7;
}

function attachmentModifier(hours, engorgement) {
  let base = 0.7;
  if (hours !== null && hours < 24) base = 0.15;
  if (hours !== null && hours >= 24 && hours < 36) base = 0.45;
  if (hours !== null && hours >= 36 && hours < 48) base = 1;
  if (hours !== null && hours >= 48 && hours < 72) base = 1.25;
  if (hours !== null && hours >= 72) base = 1.4;
  if (engorgement === "flat") return Math.min(base, 0.2);
  if (engorgement === "slightly_engorged") return Math.max(base, 0.75);
  if (engorgement === "engorged") return Math.max(base, 1.15);
  return base;
}

function pepCriteria(record, input) {
  return [
    {
      criterion: "lyme_common_area",
      status: String(record.county_fips || "").startsWith("24") ? "meets" : "uncertain",
      explanation: "Maryland is treated as Lyme-common geography in this Maryland-only product.",
    },
    tickIdentityCriterion(input),
    attachmentCriterion(input),
    {
      criterion: "removal_window",
      status:
        input.hours_since_removal === null
          ? "uncertain"
          : input.hours_since_removal <= 72
            ? "meets"
            : "not_met",
      explanation: "CDC consideration is most relevant within 72 hours after removal.",
    },
    {
      criterion: "doxycycline_safety",
      status:
        input.doxycycline_safe === null
          ? "uncertain"
          : input.doxycycline_safe
            ? "meets"
            : "not_met",
      explanation: "A healthcare professional must decide whether doxycycline is safe.",
    },
  ];
}

function tickIdentityCriterion(input) {
  let status = "uncertain";
  if (
    input.tick_species === "ixodes_scapularis" &&
    (input.tick_stage === "nymph" || input.tick_stage === "adult")
  ) {
    status = "meets";
  }
  if (input.tick_species === "not_ixodes" || input.tick_stage === "larva") {
    status = "not_met";
  }
  return {
    criterion: "tick_identity",
    status,
    explanation: "CDC Lyme prophylaxis guidance focuses on adult or nymphal blacklegged ticks.",
  };
}

function attachmentCriterion(input) {
  let status = "uncertain";
  if (
    input.engorgement === "engorged" ||
    (input.attachment_hours !== null && input.attachment_hours >= 36)
  ) {
    status = "meets";
  }
  if (
    input.engorgement === "flat" ||
    (input.attachment_hours !== null && input.attachment_hours < 24)
  ) {
    status = "not_met";
  }
  return {
    criterion: "attachment_duration",
    status,
    explanation: "CDC guidance treats 36+ hours or engorgement as a key consideration.",
  };
}

function pepConsideration(criteria) {
  const statuses = new Set(criteria.map((criterion) => criterion.status));
  if (statuses.size === 1 && statuses.has("meets")) {
    return "meets_cdc_consideration_criteria";
  }
  if (statuses.has("not_met")) {
    return "does_not_meet_cdc_consideration_criteria";
  }
  return "partially_meets_cdc_consideration_criteria";
}

function biteRiskBand(score) {
  if (score >= 9) return "high";
  if (score >= 7) return "elevated";
  if (score >= 5) return "moderate";
  if (score >= 3) return "low";
  return "very low";
}

function biteCaveats(record, input) {
  const caveats = [
    "not_calibrated_absolute_probability",
    "not_diagnosis_or_treatment_recommendation",
  ];
  if (String(record.county_fips || "").startsWith("24") && Number(record.risk_score) < 5) {
    caveats.push("maryland_high_incidence_geography_floor");
  }
  if (input.tick_species === "not_ixodes") {
    caveats.push("non_ixodes_lyme_vector_unlikely");
  }
  return caveats;
}

function renderModelLineage(record) {
  const annualSource =
    (state.modelCard && state.modelCard.annual_prediction_source) || {};
  const lineageSource = Object.keys(annualSource).length ? annualSource : record;
  const sourceCatalog = state.sourceCatalog || {};
  const modelName =
    annualSource.model_name || record.model_name || (state.weekly && state.weekly.model_name) || "unknown model";
  const modelFamily = annualSource.model_family || record.model_family || "model";
  const validationSummary =
    (state.modelCard && state.modelCard.validation_summary) || {};
  const evaluationMode = validationContextLabel(validationSummary, lineageSource);
  const weatherMode = annualSource.weather_mode || record.weather_mode || "";
  const sourceLabel = annualSourceLabel(lineageSource, sourceCatalog);

  return `<section class="lineage-strip" aria-labelledby="lineage-heading">
    <h4 id="lineage-heading">Model source</h4>
    <dl class="lineage-grid">
      <div>
        <dt>Annual forecast method</dt>
        <dd>${escapeHtml(readableModelName(modelName))} (${escapeHtml(readableModelName(modelFamily))})</dd>
      </div>
      <div>
        <dt>Validation</dt>
        <dd>${escapeHtml(readableModelName(evaluationMode || "rolling origin prior years"))}</dd>
      </div>
      <div>
        <dt>Weather</dt>
        <dd>${escapeHtml(readableWeatherMode(weatherMode))}</dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>${escapeHtml(sourceLabel)}</dd>
      </div>
    </dl>
  </section>`;
}

function annualSourceLabel(annualSource, sourceCatalog) {
  const source = annualSource || {};
  const catalog = sourceCatalog || {};
  const runId = source.run_id || catalog.source_prediction_run_id || "";
  if (
    String(runId).startsWith("annual_forecast_") ||
    source.evaluation_mode === "annual_forecast_no_observed_target"
  ) {
    return "forecast source run";
  }
  return runId ? "validation source run" : "forecast source";
}

function readableModelName(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function readableWeatherMode(value) {
  if (value === "not_used_by_lagged_model" || !value) {
    return "not weather-adjusted";
  }
  return readableModelName(value);
}

function renderFlagCaveats(record) {
  const flags = new Set([
    ...(record.feature_quality_flags || []),
    ...(record.backtest_assumption_flags || []),
  ]);
  if (!flags.size) return "";

  const items = Array.from(flags)
    .map((flag) => `<li>${escapeHtml(readableFlagLabel(flag))}</li>`)
    .join("");

  return `<section class="flag-caveats" aria-labelledby="flag-caveats-heading">
    <h4 id="flag-caveats-heading">What to know about this score</h4>
    <ul class="flag-list">${items}</ul>
  </section>`;
}

function readableFlagLabel(flag) {
  return flagLabels[flag] || sentenceCase(String(flag).replaceAll("_", " "));
}

function findCountyFeature(countyFips) {
  if (!state.counties) return null;
  return state.counties.features.find(
    (feature) => feature.properties.county_fips === countyFips
  );
}

function updateSelectedControls() {
  document.querySelectorAll("[data-county]").forEach((element) => {
    const isSelected = element.dataset.county === state.selectedCounty;
    element.setAttribute("aria-pressed", String(isSelected));
    element.classList.toggle("is-selected", isSelected);
  });
}

function renderSources() {
  const target = document.getElementById("source-content");
  const guidanceLinks =
    (state.sourceCatalog && state.sourceCatalog.guidance_links) ||
    (state.weekly && state.weekly.guidance_links) ||
    [];
  const sourceRows = (state.sourceCatalog && state.sourceCatalog.sources) || [];
  const sourceChain = sourceChainItems(sourceRows)
    .map(
      (source) => `<li>
        <b>${escapeHtml(source.title)}</b>
        <span>${escapeHtml(source.description)}</span>
      </li>`
    )
    .join("");
  const links = guidanceLinks
    .map((link) => `<li><a href="${escapeAttribute(safeUrl(link.url))}">${escapeHtml(link.title)}</a></li>`)
    .join("");
  const sources = sourceRows
    .map(
      (source) =>
        `<li><b>${escapeHtml(readableSourceTitle(source.source_id))}</b>: ${escapeHtml(readablePublicSourceNote(source))}</li>`
    )
    .join("");

  target.innerHTML = `<section class="source-chain" aria-labelledby="source-chain-title">
      <h3 id="source-chain-title">Public source chain</h3>
      <ol>${sourceChain}</ol>
    </section>
    <p>${escapeHtml(state.modelCard.score_interpretation)}</p>
    <ul>${links}</ul>
    ${sources ? `<ul class="source-detail-list">${sources}</ul>` : ""}
    <p>Forecast source: selected annual prediction branch with CDC onset seasonality prior.</p>`;
}

function sourceChainItems(sourceRows) {
  const byId = new Map(sourceRows.map((source) => [source.source_id, source]));
  const baseline = byId.get("county_week_seasonal_risk_baseline") || {};
  const annualPrediction = byId.get("annual_prediction_branch") || {};
  const seasonality =
    sourceRows.find((source) => String(source.source_id || "").includes("seasonality")) ||
    {};
  return [
    {
      title: "Selected annual forecast",
      description:
        readablePublicSourceNote(annualPrediction) ||
        "Selected annual no-observed-target forecast rows; historical backtests are separate validation evidence.",
    },
    {
      title: "CDC Lyme onset seasonality",
      description:
        seasonality.notes ||
        "CDC national Lyme disease onset timing allocates annual predictions across MMWR weeks.",
    },
    {
      title: "Derived county-week risk forecast",
      description:
        baseline.notes ||
        "Public-safe county-week score derived from selected predictions and seasonality.",
    },
    {
      title: "US Census TIGERweb county geometry",
      description:
        "Maryland county boundaries are simplified to public map geometry and county labels.",
    },
  ];
}

function readableSourceTitle(sourceId) {
  const labels = {
    annual_prediction_branch: "Selected annual forecast",
    cdc_seasonality_week_2023: "CDC Lyme onset seasonality",
    county_week_seasonal_risk_baseline: "Derived county-week risk forecast",
  };
  return labels[sourceId] || readableModelName(sourceId);
}

function readablePublicSourceNote(source) {
  source = source || {};
  const notes = {
    annual_prediction_branch:
      "Selected annual no-observed-target forecast rows; historical backtests are separate validation evidence, not the forecast source.",
    county_week_seasonal_risk_baseline:
      "Derived from the selected annual forecast and CDC onset seasonality prior.",
    cdc_seasonality_week_2023:
      "CDC national onset seasonality prior; not county-specific.",
  };
  return source.notes || source.public_notes || notes[source.source_id] || "Public derived forecast input.";
}

function renderValidationSummary() {
  const target = document.getElementById("validation-content");
  const modelCard = state.modelCard || {};
  const annualSource = modelCard.annual_prediction_source || {};
  const validation = modelCard.validation_summary || {};
  const selectedModel = readableModelName(
    validation.forecast_model_name || annualSource.model_name || modelCard.model_name
  );
  const evaluationMode = validationContextLabel(validation, annualSource);
  const weatherMode = readableWeatherMode(annualSource.weather_mode || "");
  const outcomeItems = validationOutcomeItems(selectedModel, evaluationMode, validation);
  const limitItems = validationLimitItems(modelCard, weatherMode);

  target.innerHTML = `<div class="validation-grid">
    <section aria-labelledby="validation-outcomes-title">
      <h3 id="validation-outcomes-title">What the v0 score supports</h3>
      <ul class="validation-list">${outcomeItems.map(renderValidationItem).join("")}</ul>
    </section>
    <section aria-labelledby="validation-limits-title">
      <h3 id="validation-limits-title">Limits before release</h3>
      <ul class="validation-list">${limitItems.map(renderValidationItem).join("")}</ul>
    </section>
  </div>
  <p class="validation-note">Validation and limits are part of the public score, not hidden operator notes.</p>`;
}

function renderForecastExplainer() {
  const container = document.getElementById("forecast-content");
  if (!container) return;
  const status = state.modelCard && state.modelCard.forecasting_status;
  const policy =
    state.sourceCatalog && state.sourceCatalog.data_lag_and_update_policy;
  const statusCode =
    status && status.status ? status.status : "risk_forecasting_tool";
  const statusText =
    status && status.public_score_role
      ? status.public_score_role
      : "relative county-week Lyme risk forecast with source-lag and update diagnostics";
  const policyText =
    policy && policy.summary
      ? policy.summary
      : "Official Lyme surveillance data lag real-world exposure conditions.";
  const whyForecastingText =
    policy && policy.why_forecasting
      ? policy.why_forecasting
      : "Forecasting gives timely prevention context while reviewed county-level data catch up.";
  const updatePolicyText =
    status && status.update_policy
      ? status.update_policy
      : "New surveillance, ecology, exposure, and calibration evidence are reconciled against prior forecasts and backtests before they are considered for future reviewed estimates.";
  const reconciliationText =
    policy && policy.reconciliation_policy
      ? policy.reconciliation_policy
      : "New observed reports are reconciled against prior forecasts using surveillance-regime diagnostics, calibration backtests, and source quality flags.";
  const boundaryText =
    policy && policy.forecast_boundary
      ? policy.forecast_boundary
      : "Forecast-safe branches use prior-year and trailing data.";

  container.innerHTML = `
    <p data-forecast-status="${escapeHtml(statusCode)}"><b>Lyme risk forecasting tool.</b> ${escapeHtml(whyForecastingText)}</p>
    <p>${escapeHtml(policyText)}</p>
    <p>${escapeHtml(statusText)}.</p>
    <h3>How new data updates the model</h3>
    <p>${escapeHtml(updatePolicyText)}</p>
    <p>${escapeHtml(reconciliationText)}</p>
    <p>${escapeHtml(boundaryText)}</p>
    <p>Forecasts are informational estimates, not diagnosis, treatment advice, or certainty about an individual bite.</p>
  `;
}

function validationContextLabel(validation, annualSource) {
  const role = validation && validation.validation_role;
  const matchType = validation && validation.validation_match_type;
  if (role === "historical_model_comparison") {
    if (matchType === "annual_forecast_model_name") {
      return "historical model comparison (annual forecast model-name match)";
    }
    if (matchType === "selected_prediction_run") {
      return "historical model comparison (selected prediction run)";
    }
    return "historical model comparison";
  }

  const source = annualSource || {};
  if (source.evaluation_mode === "rolling_origin_prior_years") {
    return "rolling-origin prior-years validation";
  }
  if (source.evaluation_mode === "annual_forecast_no_observed_target") {
    return "annual forecast without observed target";
  }
  return readableModelName(source.evaluation_mode || "not specified");
}

function validationOutcomeItems(selectedModel, evaluationMode, validation) {
  return [
    {
      label: "selected forecast method",
      value: selectedModel || "unknown",
    },
    {
      label: "rank_by_mae",
      value: publishedMetricValue(validation.rank_by_mae, (value) => `${value} by MAE`),
    },
    {
      label: "mae_incidence_per_100k",
      value: publishedMetricValue(
        validation.mae_incidence_per_100k,
        (value) => `${formatNumber(value)} per 100k`
      ),
    },
    {
      label: "n_predictions",
      value: publishedMetricValue(
        validation.n_predictions,
        (value) => `${value} held-out county-years`
      ),
    },
    {
      label: "Validation evidence",
      value: evaluationMode || "rolling-origin prior-years validation",
    },
    {
      label: "Intended signal",
      value: "prevention timing and Maryland county-season context",
    },
  ];
}

function publishedMetricValue(value, formatValue) {
  if (value === undefined || value === null) return "not published";
  return formatValue(value);
}

function validationLimitItems(modelCard, weatherMode) {
  const notFor = new Set(modelCard.not_for || []);
  return [
    {
      label: "Weather",
      value: weatherMode || "not weather-adjusted",
    },
    {
      label: "Medical boundary",
      value: "not a diagnosis or treatment recommendation",
    },
    {
      label: "Bite probability",
      value: notFor.has("per-bite infection probability")
        ? "not an absolute infection probability"
        : "not calibrated as a personal infection probability",
    },
  ];
}

function renderValidationItem(item) {
  return `<li><b>${escapeHtml(item.label)}</b><span>${escapeHtml(item.value)}</span></li>`;
}

function renderLoadError(error) {
  document.getElementById("risk-map").innerHTML = `<p role="alert">${escapeHtml(error.message)}</p>`;
  document.getElementById("county-list").innerHTML = "";
  document.getElementById("panel-content").innerHTML = "<p>Forecast data bundle is unavailable.</p>";
  document.getElementById("validation-content").innerHTML = "<p>Validation notes are unavailable.</p>";
  document.getElementById("source-content").innerHTML = "<p>Source notes are unavailable.</p>";
}

function geoBounds(features) {
  const points = features.flatMap((feature) => coordinates(feature.geometry));
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function coordinates(geometry) {
  if (geometry.type === "Polygon") return geometry.coordinates.flat();
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(2);
  if (geometry.type === "Point") return [geometry.coordinates];
  return [];
}

function geometryPath(geometry, bounds, width, height) {
  if (geometry.type === "Polygon") {
    return polygonPath(geometry.coordinates, bounds, width, height);
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => polygonPath(polygon, bounds, width, height))
      .join(" ");
  }
  const [x, y] = projectPoint(geometry.coordinates, bounds, width, height);
  return `M ${x - 3} ${y - 3} h 6 v 6 h -6 Z`;
}

function polygonPath(rings, bounds, width, height) {
  return rings
    .map(
      (ring) =>
        ring
          .map((point, index) => {
            const [x, y] = projectPoint(point, bounds, width, height);
            return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
          })
          .join(" ") + " Z"
    )
    .join(" ");
}

function projectPoint(point, bounds, width, height) {
  const padding = 20;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const rangeX = bounds.maxX - bounds.minX || 1;
  const rangeY = bounds.maxY - bounds.minY || 1;
  const x = padding + ((point[0] - bounds.minX) / rangeX) * usableWidth;
  const y = padding + ((bounds.maxY - point[1]) / rangeY) * usableHeight;
  return [x, y];
}

function sentenceCase(value) {
  const text = categoryLabel(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function categoryLabel(value) {
  return String(value).replaceAll("_", " ");
}

function formatNumber(value) {
  return Number(value).toFixed(2);
}

function optionalNumber(id) {
  const value = document.getElementById(id).value;
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function optionalBoolean(id) {
  const value = document.getElementById(id).value;
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function safeUrl(value) {
  const rawValue = String(value || "");
  if (rawValue.startsWith("/") || rawValue.startsWith("./")) {
    return rawValue;
  }
  try {
    const base =
      typeof window === "undefined" ? "https://tickbiterisk.local/" : window.location.href;
    const url = new URL(rawValue, base);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.href;
    }
  } catch {
    return "about:blank";
  }
  return "about:blank";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return replacements[char];
  });
}
