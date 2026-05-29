const regionalState = {
  weekly: null,
  annual: null,
  counties: null,
  states: null,
  countyMetadata: null,
  overlays: null,
  modelCard: null,
  sourceCatalog: null,
  selectedCounty: null,
  selectedYear: null,
  selectedWeek: 1,
  availableYears: [],
  stateFilter: "",
  countySearch: "",
  byCountyWeek: new Map(),
  byCountyYearWeek: new Map(),
  recordsByCounty: new Map(),
  annualByCountyYear: new Map(),
  annualRecordsByCounty: new Map(),
  metadataByCounty: new Map(),
  overlaysByRegime: new Map(),
};

const defaultRegionalDataBase = "research-data/regional";
const defaultRegionalDataPaths = {
  weekly: "research-data/regional/regional_county_risk_weekly.json",
  annual: "research-data/regional/regional_county_incidence_annual.json",
  counties: "research-data/regional/regional_counties.geojson",
  states: "research-data/regional/regional_states.geojson",
  countyMetadata: "research-data/regional/regional_county_metadata.json",
  overlays: "research-data/regional/regional_spatial_regime_overlays.json",
  modelCard: "research-data/regional/model_card.json",
  sourceCatalog: "research-data/regional/source_catalog.json",
};

const regionalDataPaths = regionalResearchDataPaths();

const regionalFlagLabels = {
  empirical_prediction_band:
    "Empirical prediction intervals summarize historical forecast residuals",
  forecast_safe_prior_history_spatial_regime:
    "Forecast-safe prior spatial-regime history",
  localized_spatial_regime_feature:
    "Localized spatial-regime research feature",
  not_public_default: "Research layer, not public default",
};

document.addEventListener("DOMContentLoaded", initRegionalResearch);

async function initRegionalResearch() {
  document
    .getElementById("year-select")
    .addEventListener("change", handleYearSelectChange);
  document
    .getElementById("week-input")
    .addEventListener("input", handleWeekInputChange);
  document
    .getElementById("week-prev")
    .addEventListener("click", () => adjustRegionalWeek(-1));
  document
    .getElementById("week-next")
    .addEventListener("click", () => adjustRegionalWeek(1));
  document
    .getElementById("state-filter")
    .addEventListener("change", handleRegionalListFilterChange);
  document
    .getElementById("county-search")
    .addEventListener("input", handleRegionalListFilterChange);

  try {
    const [
      weekly,
      annual,
      counties,
      states,
      countyMetadata,
      overlays,
      modelCard,
      sourceCatalog,
    ] =
      await Promise.all([
        fetchRegionalJson(regionalDataPaths.weekly),
        fetchRegionalJson(regionalDataPaths.annual),
        fetchRegionalJson(regionalDataPaths.counties),
        fetchRegionalJson(regionalDataPaths.states),
        fetchRegionalJson(regionalDataPaths.countyMetadata),
        fetchRegionalJson(regionalDataPaths.overlays),
        fetchRegionalJson(regionalDataPaths.modelCard),
        fetchRegionalJson(regionalDataPaths.sourceCatalog),
      ]);

    regionalState.weekly = weekly;
    regionalState.annual = annual;
    regionalState.counties = counties;
    regionalState.states = states;
    regionalState.countyMetadata = countyMetadata;
    regionalState.overlays = overlays;
    regionalState.modelCard = modelCard;
    regionalState.sourceCatalog = sourceCatalog;
    indexRegionalRecords(weekly.records || []);
    indexRegionalAnnualRecords(annual.records || []);
    indexRegionalMetadata(countyMetadata.counties || []);
    indexRegionalOverlays(overlays.records || []);
    setRegionalYearBounds(weekly.records || [], annual.records || []);
    setRegionalWeekBounds(regionalForecastRecordsForSelectedYear());
    renderRegionalStateFilter();
    selectDefaultRegionalCounty();
    renderRegionalMap();
    renderRegionalCountyList();
    renderRegionalSources();
    renderRegionalForecastProvenance();
    selectRegionalCounty(regionalState.selectedCounty);
  } catch (error) {
    renderRegionalLoadError(error);
  }
}

function regionalResearchDataPaths() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("dataBase");
  if (!requested) return defaultRegionalDataPaths;
  const regionalDataBase = requested.replace(/\/+$/, "");
  if (regionalDataBase === defaultRegionalDataBase) return defaultRegionalDataPaths;
  return {
    weekly: `${regionalDataBase}/regional_county_risk_weekly.json`,
    annual: `${regionalDataBase}/regional_county_incidence_annual.json`,
    counties: `${regionalDataBase}/regional_counties.geojson`,
    states: `${regionalDataBase}/regional_states.geojson`,
    countyMetadata: `${regionalDataBase}/regional_county_metadata.json`,
    overlays: `${regionalDataBase}/regional_spatial_regime_overlays.json`,
    modelCard: `${regionalDataBase}/model_card.json`,
    sourceCatalog: `${regionalDataBase}/source_catalog.json`,
  };
}

async function fetchRegionalJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Could not load ${path}`);
  }
  return response.json();
}

function indexRegionalRecords(records) {
  regionalState.byCountyWeek.clear();
  regionalState.byCountyYearWeek.clear();
  regionalState.recordsByCounty.clear();
  for (const record of records) {
    const dataYear = regionalRecordYear(record);
    regionalState.byCountyWeek.set(
      `${record.county_fips}:${record.mmwr_week}`,
      record
    );
    regionalState.byCountyYearWeek.set(
      `${record.county_fips}:${dataYear}:${record.mmwr_week}`,
      record
    );
    if (!regionalState.recordsByCounty.has(record.county_fips)) {
      regionalState.recordsByCounty.set(record.county_fips, []);
    }
    regionalState.recordsByCounty.get(record.county_fips).push(record);
  }
  for (const countyRecords of regionalState.recordsByCounty.values()) {
    countyRecords.sort(
      (left, right) =>
        regionalRecordYear(left) - regionalRecordYear(right) ||
        Number(left.mmwr_week) - Number(right.mmwr_week)
    );
  }
}

function indexRegionalAnnualRecords(records) {
  regionalState.annualByCountyYear.clear();
  regionalState.annualRecordsByCounty.clear();
  for (const record of records) {
    regionalState.annualByCountyYear.set(
      `${record.county_fips}:${record.year}`,
      record
    );
    if (!regionalState.annualRecordsByCounty.has(record.county_fips)) {
      regionalState.annualRecordsByCounty.set(record.county_fips, []);
    }
    regionalState.annualRecordsByCounty.get(record.county_fips).push(record);
  }
  for (const countyRecords of regionalState.annualRecordsByCounty.values()) {
    countyRecords.sort((left, right) => Number(left.year) - Number(right.year));
  }
}

function indexRegionalMetadata(counties) {
  regionalState.metadataByCounty.clear();
  for (const county of counties) {
    regionalState.metadataByCounty.set(county.county_fips, county);
  }
}

function indexRegionalOverlays(records) {
  regionalState.overlaysByRegime.clear();
  for (const overlay of records) {
    regionalState.overlaysByRegime.set(overlay.region_id, overlay);
  }
}

function setRegionalWeekBounds(records) {
  const weeks = Array.from(new Set(records.map((record) => Number(record.mmwr_week))))
    .filter((week) => Number.isFinite(week))
    .sort((left, right) => left - right);
  const input = document.getElementById("week-input");
  if (!weeks.length) {
    regionalState.selectedWeek = Number(regionalState.selectedWeek) || 1;
    input.min = "1";
    input.max = "53";
    input.value = String(regionalState.selectedWeek);
    updateRegionalWeekLabel();
    return;
  }
  input.min = String(weeks[0]);
  input.max = String(weeks[weeks.length - 1]);
  regionalState.selectedWeek = regionalClampWeek(
    Number(regionalState.selectedWeek) || weeks[0]
  );
  input.value = String(regionalState.selectedWeek);
  updateRegionalWeekLabel();
}

function setRegionalYearBounds(weeklyRecords, annualRecords) {
  const years = Array.from(
    new Set([
      ...annualRecords.map((record) => Number(record.year)),
      ...weeklyRecords.map((record) => Number(record.data_year || record.year)),
    ])
  )
    .filter((year) => Number.isFinite(year))
    .sort((left, right) => left - right);
  regionalState.availableYears = years;
  const select = document.getElementById("year-select");
  if (!years.length) {
    select.innerHTML = "";
    updateRegionalYearLabel();
    return;
  }
  select.innerHTML = years
    .map(
      (year) =>
        `<option value="${regionalEscapeHtml(year)}">${regionalEscapeHtml(
          regionalYearOptionLabel(year)
        )}</option>`
    )
    .join("");
  const forecastYears = regionalForecastYearsFromRecords();
  const latestForecastYear = forecastYears[forecastYears.length - 1];
  const defaultYear =
    latestForecastYear && years.includes(latestForecastYear)
      ? latestForecastYear
      : years[years.length - 1];
  regionalState.selectedYear = defaultYear;
  select.value = String(defaultYear);
  updateRegionalYearLabel();
  updateRegionalWeekLabel();
}

function handleYearSelectChange(event) {
  regionalState.selectedYear = Number(event.target.value);
  setRegionalWeekBounds(regionalForecastRecordsForSelectedYear());
  updateRegionalYearLabel();
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  renderRegionalSources();
  renderRegionalForecastProvenance();
  selectRegionalCounty(regionalState.selectedCounty);
}

function handleWeekInputChange(event) {
  regionalState.selectedWeek = regionalClampWeek(Number(event.target.value));
  event.target.value = String(regionalState.selectedWeek);
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  selectRegionalCounty(regionalState.selectedCounty);
}

function adjustRegionalWeek(delta) {
  const input = document.getElementById("week-input");
  if (input.disabled) return;
  regionalState.selectedWeek = regionalClampWeek(
    Number(regionalState.selectedWeek) + delta
  );
  input.value = String(regionalState.selectedWeek);
  handleWeekInputChange({ target: input });
}

function handleRegionalListFilterChange() {
  regionalState.stateFilter = document.getElementById("state-filter").value;
  regionalState.countySearch = document
    .getElementById("county-search")
    .value.trim()
    .toLowerCase();
  renderRegionalCountyList();
}

function updateRegionalWeekLabel() {
  const input = document.getElementById("week-input");
  const previous = document.getElementById("week-prev");
  const next = document.getElementById("week-next");
  const mode = selectedRegionalDataMode();
  const hasForecastRows = regionalForecastRecordsForSelectedYear().length > 0;
  const enableWeekControls =
    hasForecastRows && (mode === "forecast" || mode === "mixed");
  input.disabled = !enableWeekControls;
  previous.disabled = !enableWeekControls;
  next.disabled = !enableWeekControls;
  if (!enableWeekControls) {
    document.getElementById("week-label").textContent =
      "Week controls apply to forecast years";
    return;
  }
  const suffix =
    mode === "mixed" ? " for forecast counties" : "";
  document.getElementById("week-label").textContent =
    `Using MMWR week ${regionalState.selectedWeek}${suffix}`;
}

function updateRegionalYearLabel() {
  const mode = selectedRegionalDataMode();
  const label = document.getElementById("year-label");
  const modeLabel = document.getElementById("year-mode-label");
  const selectedYear = regionalState.selectedYear || "Loading";
  label.textContent = `Using ${selectedYear}`;
  modeLabel.textContent = regionalModeLabel(mode);
  modeLabel.classList.toggle("forecast-mode", mode === "forecast");
  modeLabel.classList.toggle("observed-mode", mode === "observed_historical");
  modeLabel.classList.toggle("mixed-mode", mode === "mixed");
  modeLabel.classList.toggle("unavailable-mode", mode === "unavailable");
}

function selectedRegionalYearMode() {
  return selectedRegionalDataMode();
}

function selectedRegionalDataMode() {
  return regionalDataModeForYear(regionalState.selectedYear);
}

function regionalDataModeForYear(year) {
  const hasForecast = regionalForecastRecordsForYear(year).length > 0;
  const hasObserved = regionalAnnualRecordsForYear(year).length > 0;
  if (hasForecast && hasObserved) return "mixed";
  if (hasForecast) return "forecast";
  if (hasObserved) return "observed_historical";
  return "unavailable";
}

function regionalCountyDataMode(countyFips) {
  const selectedMode = selectedRegionalDataMode();
  const annualRecord = getRegionalAnnualRecord(countyFips);
  const forecastRecord = getRegionalRecord(countyFips);
  if (selectedMode === "mixed") {
    if (annualRecord) return "observed_historical";
    if (forecastRecord) return "forecast";
    return "unavailable";
  }
  if (selectedMode === "observed_historical") {
    return annualRecord ? "observed_historical" : "unavailable";
  }
  if (selectedMode === "forecast") {
    return forecastRecord ? "forecast" : "unavailable";
  }
  return "unavailable";
}

function regionalModeLabel(mode) {
  if (mode === "forecast") return "Forecast";
  if (mode === "mixed") return "Mixed observed/forecast";
  if (mode === "observed_historical") return "Observed historical";
  return "Unavailable";
}

function regionalYearOptionLabel(year) {
  return `${year} - ${regionalModeLabel(regionalDataModeForYear(year))}`;
}

function regionalClampWeek(value) {
  const input = document.getElementById("week-input");
  const minimum = Number(input.min || 1);
  const maximum = Number(input.max || 53);
  const fallback = Number(regionalState.selectedWeek) || minimum;
  const week = Number.isFinite(value) ? Math.round(value) : fallback;
  return Math.min(maximum, Math.max(minimum, week));
}

function selectDefaultRegionalCounty() {
  const features = (regionalState.counties && regionalState.counties.features) || [];
  const firstWithRecord = features.find((feature) =>
    getRegionalRecord(feature.properties.county_fips)
  );
  const firstWithAnnual = features.find((feature) =>
    getRegionalAnnualRecord(feature.properties.county_fips)
  );
  regionalState.selectedCounty = firstWithRecord
    ? firstWithRecord.properties.county_fips
    : firstWithAnnual
      ? firstWithAnnual.properties.county_fips
    : features[0] && features[0].properties.county_fips;
}

function getRegionalRecord(countyFips) {
  return regionalState.byCountyYearWeek.get(
    `${countyFips}:${regionalState.selectedYear}:${regionalState.selectedWeek}`
  );
}

function getRegionalAnnualRecord(countyFips) {
  return regionalState.annualByCountyYear.get(
    `${countyFips}:${regionalState.selectedYear}`
  );
}

function regionalCountyWeekRecords(countyFips) {
  const selectedYear = Number(regionalState.selectedYear);
  return (regionalState.recordsByCounty.get(countyFips) || []).filter(
    (record) => regionalRecordYear(record) === selectedYear
  );
}

function regionalCountyAnnualRecords(countyFips) {
  return regionalState.annualRecordsByCounty.get(countyFips) || [];
}

function regionalForecastRecordsForSelectedYear() {
  return regionalForecastRecordsForYear(regionalState.selectedYear);
}

function regionalForecastRecordsForYear(year) {
  const selectedYear = Number(year);
  if (!Number.isFinite(selectedYear)) return [];
  return ((regionalState.weekly && regionalState.weekly.records) || []).filter(
    (record) => regionalRecordYear(record) === selectedYear
  );
}

function regionalAnnualRecordsForYear(year) {
  const selectedYear = Number(year);
  if (!Number.isFinite(selectedYear)) return [];
  return ((regionalState.annual && regionalState.annual.records) || []).filter(
    (record) => Number(record.year) === selectedYear
  );
}

function regionalRecordYear(record) {
  return Number(record && (record.data_year || record.year));
}

function renderRegionalMap() {
  const container = document.getElementById("regional-risk-map");
  if (!regionalState.counties) return;

  const features = regionalState.counties.features || [];
  const bounds = regionalGeoBounds(features);
  const width = 760;
  const height = 560;
  const paths = features
    .map((feature) => regionalCountyPath(feature, bounds, width, height))
    .join("");
  const statePaths = ((regionalState.states && regionalState.states.features) || [])
    .map((feature) => regionalStateBoundaryPath(feature, bounds, width, height))
    .join("");
  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="group" aria-label="Mid-Atlantic counties colored by regional Lyme forecast research">
    <g class="regional-county-layer">${paths}</g>
    <g class="regional-state-boundary-layer" aria-hidden="true">${statePaths}</g>
  </svg>`;
  container.querySelectorAll("[data-county]").forEach((shape) => {
    shape.addEventListener("click", () => selectRegionalCounty(shape.dataset.county));
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectRegionalCounty(shape.dataset.county);
      }
    });
  });
  document.getElementById("regional-map-meta").textContent =
    `${features.length} county-equivalents across DE, DC, MD, PA, VA, and WV`;
  updateRegionalSelectedControls();
}

function regionalStateBoundaryPath(feature, bounds, width, height) {
  const props = feature.properties || {};
  const label = `${props.state_name || props.state_abbr || "State"} boundary`;
  return `<path
    class="regional-state-boundary"
    d="${regionalGeometryPath(feature.geometry, bounds, width, height)}"
    data-state="${regionalEscapeHtml(props.state_abbr || props.state_fips || "")}">
    <title>${regionalEscapeHtml(label)}</title>
  </path>`;
}

function regionalCountyPath(feature, bounds, width, height) {
  const props = feature.properties || {};
  const countyFips = props.county_fips;
  const record = getRegionalRecord(countyFips);
  const metadata = regionalState.metadataByCounty.get(countyFips);
  const regime = metadata && metadata.selected_spatial_regime;
  const selectedRegime = selectedRegionalRegimeId();
  const stateAbbr = props.state_abbr || "";
  const annualRecord = getRegionalAnnualRecord(countyFips);
  const countyMode = regionalCountyDataMode(countyFips);
  const displayClass = countyMode === "forecast"
    ? record
      ? regionalRiskClass(record.risk_score)
      : "risk-unavailable"
    : countyMode === "observed_historical"
      ? regionalObservedRiskClass(annualRecord)
      : "risk-unavailable";
  const label = countyMode === "forecast"
    ? record
      ? `${props.county_name}, ${stateAbbr}, ${regionalCategoryLabel(record.risk_category)}, ${record.risk_score} of 10`
      : `${props.county_name}, ${stateAbbr}, no forecast available`
    : countyMode === "observed_historical" && annualRecord
      ? `${props.county_name}, ${stateAbbr}, observed reported incidence ${regionalFormatNumber(annualRecord.incidence_per_100k)} per 100k in ${regionalState.selectedYear}`
      : `${props.county_name}, ${stateAbbr}, no observed or forecast row available for ${regionalState.selectedYear}`;
  const classes = [
    "county-shape",
    "regional-county-shape",
    displayClass,
    regime && regime.region_id === selectedRegime ? "is-same-regime" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return `<path
    class="${classes}"
    d="${regionalGeometryPath(feature.geometry, bounds, width, height)}"
    data-county="${regionalEscapeHtml(countyFips)}"
    data-regime="${regionalEscapeHtml(regime ? regime.region_id : "")}"
    role="button"
    tabindex="0"
    aria-label="${regionalEscapeHtml(label)}"
    aria-pressed="${countyFips === regionalState.selectedCounty ? "true" : "false"}">
    <title>${regionalEscapeHtml(label)}</title>
  </path>`;
}

function renderRegionalCountyList() {
  const list = document.getElementById("regional-county-list");
  const features = filteredRegionalFeatures();
  list.innerHTML = features.map(regionalCountyListButton).join("");
  list.querySelectorAll("button[data-county]").forEach((button) => {
    button.addEventListener("click", () => selectRegionalCounty(button.dataset.county));
  });
  renderRegionalListStatus(features.length);
  updateRegionalSelectedControls();
}

function filteredRegionalFeatures() {
  const features = regionalState.counties ? regionalState.counties.features || [] : [];
  return features.filter((feature) => {
    const props = feature.properties || {};
    const stateMatches =
      !regionalState.stateFilter || props.state_abbr === regionalState.stateFilter;
    const searchText = `${props.county_name || ""} ${props.county_fips || ""}`.toLowerCase();
    const searchMatches =
      !regionalState.countySearch || searchText.includes(regionalState.countySearch);
    return stateMatches && searchMatches;
  });
}

function renderRegionalStateFilter() {
  const select = document.getElementById("state-filter");
  const features = regionalState.counties ? regionalState.counties.features || [] : [];
  const states = Array.from(
    new Set(features.map((feature) => feature.properties && feature.properties.state_abbr))
  )
    .filter(Boolean)
    .sort();
  select.innerHTML =
    '<option value="">All states</option>' +
    states
      .map((stateAbbr) => `<option value="${regionalEscapeHtml(stateAbbr)}">${regionalEscapeHtml(stateAbbr)}</option>`)
      .join("");
}

function renderRegionalListStatus(count) {
  const status = document.getElementById("regional-list-status");
  const noun = count === 1 ? "county" : "counties";
  status.textContent = `${count} ${noun} shown`;
}

function regionalCountyListButton(feature) {
  const props = feature.properties || {};
  const record = getRegionalRecord(props.county_fips);
  const annualRecord = getRegionalAnnualRecord(props.county_fips);
  const countyMode = regionalCountyDataMode(props.county_fips);
  const score = countyMode === "forecast"
    ? record
      ? `${record.risk_score}/10`
      : "NA"
    : countyMode === "observed_historical" &&
        annualRecord &&
        annualRecord.incidence_per_100k !== null
      ? `${regionalFormatNumber(annualRecord.incidence_per_100k)}/100k`
      : "NA";
  const category = countyMode === "forecast"
    ? record
      ? regionalCategoryLabel(record.risk_category)
      : "unavailable"
    : countyMode === "observed_historical" && annualRecord
      ? regionalReadableName(annualRecord.diagnostic_midatlantic_incidence_tier)
      : "unavailable";
  const badgeClass = countyMode === "forecast"
    ? record
      ? regionalRiskClass(record.risk_score)
      : "risk-unavailable"
    : countyMode === "observed_historical"
      ? regionalObservedRiskClass(annualRecord)
      : "risk-unavailable";

  return `<button type="button" data-county="${regionalEscapeHtml(props.county_fips)}" aria-pressed="${props.county_fips === regionalState.selectedCounty ? "true" : "false"}">
    <span>${regionalEscapeHtml(props.county_name)}<br><small>${regionalEscapeHtml(props.state_abbr || "")} · ${regionalEscapeHtml(category)}</small></span>
    <span class="score-badge ${badgeClass}">${regionalEscapeHtml(score)}</span>
  </button>`;
}

function selectRegionalCounty(countyFips) {
  if (!countyFips) return;
  regionalState.selectedCounty = countyFips;
  const record = getRegionalRecord(countyFips);
  const feature = findRegionalCountyFeature(countyFips);
  const metadata = regionalState.metadataByCounty.get(countyFips);
  const props = feature ? feature.properties : {};
  const countyName = props.county_name || (metadata && metadata.county_name) || countyFips;
  const stateAbbr = props.state_abbr || "";
  const panel = document.getElementById("regional-panel-content");
  const countyMode = regionalCountyDataMode(countyFips);

  if (countyMode === "observed_historical") {
    renderRegionalObservedCounty({
      countyFips,
      countyName,
      stateAbbr,
      metadata,
      panel,
    });
    return;
  }

  if (countyMode !== "forecast" || !record) {
    panel.innerHTML = `<p>No observed or forecast row is available for ${regionalEscapeHtml(countyName)} in ${regionalEscapeHtml(regionalState.selectedYear)}.</p>`;
    renderRegionalRegime(metadata);
    if (regionalCountyWeekRecords(countyFips).length) {
      renderRegionalForecastChart(countyFips);
    } else {
      renderRegionalObservedHistoryChart(countyFips);
    }
    renderRegionalMap();
    updateRegionalSelectedControls();
    return;
  }

  const interval80 = record.predicted_weekly_incidence_80_interval || [0, 0];
  const interval95 = record.predicted_weekly_incidence_95_interval || [0, 0];
  panel.innerHTML = `<div class="score-card">
    <p class="muted">MMWR week ${regionalEscapeHtml(record.mmwr_week)}, forecast year ${regionalEscapeHtml(record.data_year || record.year)}</p>
    <h3>${regionalEscapeHtml(countyName)}${stateAbbr ? `, ${regionalEscapeHtml(stateAbbr)}` : ""}</h3>
    <p><span class="score-badge ${regionalRiskClass(record.risk_score)}">${regionalEscapeHtml(record.risk_score)}/10</span> ${regionalEscapeHtml(regionalCategoryLabel(record.risk_category))}</p>
    <p>Predicted weekly incidence: ${regionalFormatNumber(record.predicted_weekly_incidence_per_100k)} per 100k.</p>
    <p>80% empirical interval: ${regionalFormatNumber(interval80[0])} to ${regionalFormatNumber(interval80[1])} per 100k.</p>
    <p>95% empirical interval: ${regionalFormatNumber(interval95[0])} to ${regionalFormatNumber(interval95[1])} per 100k.</p>
    ${renderRegionalScaleDiagnostics(record)}
    ${renderRegionalCountyRegime(metadata)}
    ${renderRegionalFlagCaveats(record)}
    <p class="disclaimer">Research only. This is not a per-bite infection probability, diagnosis, treatment recommendation, or public Maryland default.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalForecastChart(countyFips);
  renderRegionalMap();
  updateRegionalSelectedControls();
}

function renderRegionalScaleDiagnostics(record) {
  const scale = (regionalState.weekly && regionalState.weekly.score_scale) || {};
  const denominator = scale.score_denominator;
  const rawScore = record.risk_score_raw;
  const rawScoreText =
    rawScore === undefined || rawScore === null
      ? "unavailable raw score"
      : `raw score ${regionalFormatNumber(rawScore)}`;
  const denominatorText =
    denominator === undefined || denominator === null
      ? "unknown score denominator"
      : `score denominator ${regionalFormatNumber(denominator)}`;
  return `<section class="lineage-strip scale-diagnostic" aria-labelledby="regional-scale-heading">
    <h4 id="regional-scale-heading">Linear score</h4>
    <p>This forecast score is linear: predicted weekly incidence is divided by the regional ${regionalEscapeHtml(denominatorText)}, then rounded and clamped to 1-10.</p>
    <p>${regionalEscapeHtml(rawScoreText)}; displayed score ${regionalEscapeHtml(record.risk_score)}/10.</p>
  </section>`;
}

function renderRegionalObservedCounty({
  countyFips,
  countyName,
  stateAbbr,
  metadata,
  panel,
}) {
  const annualRecord = getRegionalAnnualRecord(countyFips);
  if (!annualRecord) {
    panel.innerHTML = `<p>No observed historical incidence row available for ${regionalEscapeHtml(countyName)} in ${regionalEscapeHtml(regionalState.selectedYear)}.</p>`;
    renderRegionalRegime(metadata);
    renderRegionalObservedHistoryChart(countyFips);
    renderRegionalMap();
    updateRegionalSelectedControls();
    return;
  }
  panel.innerHTML = `<div class="score-card observed-card">
    <p class="muted">Observed historical, reported surveillance year ${regionalEscapeHtml(annualRecord.year)}</p>
    <h3>${regionalEscapeHtml(countyName)}${stateAbbr ? `, ${regionalEscapeHtml(stateAbbr)}` : ""}</h3>
    <p><span class="score-badge ${regionalObservedRiskClass(annualRecord)}">${regionalFormatNumber(annualRecord.incidence_per_100k)}/100k</span> observed reported incidence</p>
    <p>Observed reported incidence: ${regionalFormatNumber(annualRecord.incidence_per_100k)} per 100k.</p>
    <p>${regionalEscapeHtml(annualRecord.reported_cases)} reported cases; population denominator ${regionalFormatNumber(annualRecord.population)}.</p>
    <p>Mid-Atlantic diagnostic tier: ${regionalEscapeHtml(regionalReadableName(annualRecord.diagnostic_midatlantic_incidence_tier))}.</p>
    ${renderRegionalCountyRegime(metadata)}
    ${renderRegionalFlagCaveats(annualRecord)}
    <p class="disclaimer">Reported cases are not stable true incidence. This historical layer is informational only, not medical advice, and not a forecast-safe feature for the selected year.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalObservedHistoryChart(countyFips);
  renderRegionalMap();
  updateRegionalSelectedControls();
}

function renderRegionalCountyRegime(metadata) {
  const regime = metadata && metadata.selected_spatial_regime;
  if (!regime) return "";
  return `<section class="lineage-strip" aria-labelledby="regional-lineage-heading">
    <h4 id="regional-lineage-heading">Localized spatial regime</h4>
    <dl class="lineage-grid">
      <div>
        <dt>Research region</dt>
        <dd>${regionalEscapeHtml(regime.region_name || regime.region_id)}</dd>
      </div>
      <div>
        <dt>Feature year</dt>
        <dd>${regionalEscapeHtml(regime.spatial_regime_feature_year)}</dd>
      </div>
      <div>
        <dt>Forecast origin</dt>
        <dd>${regionalEscapeHtml(regime.forecast_origin_year)}</dd>
      </div>
    </dl>
  </section>`;
}

function renderRegionalRegime(metadata) {
  const target = document.getElementById("regional-regime-panel");
  const regime = metadata && metadata.selected_spatial_regime;
  if (!regime) {
    target.innerHTML = `<h3 id="regional-regime-title">Localized spatial regime</h3><p class="muted">No spatial-regime membership is available for this county.</p>`;
    return;
  }
  const overlay = regionalState.overlaysByRegime.get(regime.region_id);
  if (!overlay) {
    target.innerHTML = `<h3 id="regional-regime-title">Localized spatial regime</h3>
      <p><b>${regionalEscapeHtml(regime.region_name || regime.region_id)}</b></p>
      <p class="muted">Regime interval summary is unavailable in this bundle.</p>`;
    return;
  }
  const interval80 = overlay.predicted_incidence_80_interval || [0, 0];
  const interval95 = overlay.predicted_incidence_95_interval || [0, 0];
  const countyNames = regionalRegimeCountyNames(overlay);
  const countyItems = countyNames
    .map((countyName) => `<li>${regionalEscapeHtml(countyName)}</li>`)
    .join("");
  target.innerHTML = `<h3 id="regional-regime-title">Localized spatial regime</h3>
    <p><b>${regionalEscapeHtml(overlay.region_name || overlay.region_id)}</b></p>
    <p>${regionalEscapeHtml(overlay.n_counties)} counties in this localized research cluster.</p>
    <section class="regional-regime-counties" aria-labelledby="regional-regime-counties-title">
      <h4 id="regional-regime-counties-title">Regime counties</h4>
      <ul>${countyItems}</ul>
    </section>
    <dl class="regional-regime-metrics">
      <div>
        <dt>Regime incidence</dt>
        <dd>${regionalFormatNumber(overlay.predicted_incidence_per_100k)} per 100k</dd>
      </div>
      <div>
        <dt>Regime 80% interval</dt>
        <dd>${regionalFormatNumber(interval80[0])} to ${regionalFormatNumber(interval80[1])} per 100k</dd>
      </div>
      <div>
        <dt>Regime 95% interval</dt>
        <dd>Regime 95% interval: ${regionalFormatNumber(interval95[0])} to ${regionalFormatNumber(interval95[1])} per 100k</dd>
      </div>
    </dl>
    <p class="muted">States remain display and reporting rollups; this regime is a localized research grouping.</p>`;
}

function regionalRegimeCountyNames(overlay) {
  const countyFipsList = overlay.county_fips_list || [];
  const countyNames = countyFipsList.map((countyFips) => {
    const feature = findRegionalCountyFeature(countyFips);
    const metadata = regionalState.metadataByCounty.get(countyFips);
    const countyName =
      (feature && feature.properties && feature.properties.county_name) ||
      (metadata && metadata.county_name) ||
      countyFips;
    const stateAbbr = feature && feature.properties && feature.properties.state_abbr;
    return stateAbbr ? `${countyName}, ${stateAbbr}` : countyName;
  });
  if (countyNames.length <= 8) {
    return countyNames;
  }
  return [...countyNames.slice(0, 8), `${countyNames.length - 8} more counties`];
}

function renderRegionalFlagCaveats(record) {
  const flags = new Set([
    ...(record.feature_quality_flags || []),
    ...(record.backtest_assumption_flags || []),
  ]);
  if (!flags.size) return "";
  const items = Array.from(flags)
    .map((flag) => `<li>${regionalEscapeHtml(regionalReadableFlag(flag))}</li>`)
    .join("");
  return `<section class="flag-caveats" aria-labelledby="regional-flag-heading">
    <h4 id="regional-flag-heading">What to know about this score</h4>
    <ul class="flag-list">${items}</ul>
  </section>`;
}

function renderRegionalForecastChart(countyFips) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  const records = regionalCountyWeekRecords(countyFips);
  const feature = findRegionalCountyFeature(countyFips);
  const countyName =
    (feature && feature.properties && feature.properties.county_name) || countyFips;
  if (!records.length) {
    target.innerHTML = "<p>No weekly forecast rows are available for this county.</p>";
    summary.textContent = `${countyName} weekly forecast window unavailable`;
    return;
  }

  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 22, bottom: 34, left: 46 };
  const weeks = records.map((record) => Number(record.mmwr_week));
  const minWeek = Math.min(...weeks);
  const maxWeek = Math.max(...weeks);
  const maxValue = Math.max(
    1,
    ...records.map((record) => {
      const interval95 = record.predicted_weekly_incidence_95_interval || [0, 0];
      return Math.max(
        Number(record.predicted_weekly_incidence_per_100k || 0),
        Number(interval95[1] || 0)
      );
    })
  );
  const xScale = (week) =>
    padding.left +
    ((Number(week) - minWeek) / Math.max(1, maxWeek - minWeek)) *
      (width - padding.left - padding.right);
  const yScale = (value) =>
    height -
    padding.bottom -
    (Number(value || 0) / maxValue) * (height - padding.top - padding.bottom);
  const linePath = regionalLinePath(records, xScale, yScale);
  const band95 = regionalIntervalBandPath(
    records,
    "predicted_weekly_incidence_95_interval",
    xScale,
    yScale
  );
  const band80 = regionalIntervalBandPath(
    records,
    "predicted_weekly_incidence_80_interval",
    xScale,
    yScale
  );
  const activeRecord =
    records.find((record) => Number(record.mmwr_week) === regionalState.selectedWeek) ||
    records[0];
  const activeX = xScale(activeRecord.mmwr_week);
  const activeY = yScale(activeRecord.predicted_weekly_incidence_per_100k);
  const activeInterval = activeRecord.predicted_weekly_incidence_95_interval || [0, 0];

  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${regionalEscapeHtml(countyName)} weekly forecast curve with empirical interval bands">
    <path class="interval-band-95" d="${band95}"><title>95% empirical interval band</title></path>
    <path class="interval-band-80" d="${band80}"><title>80% empirical interval band</title></path>
    <path class="county-forecast-line" d="${linePath}"><title>Predicted weekly incidence</title></path>
    <line class="chart-axis" x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"></line>
    <line class="chart-axis" x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"></line>
    <circle class="active-week-marker" data-active-week="${regionalEscapeHtml(activeRecord.mmwr_week)}" cx="${activeX.toFixed(2)}" cy="${activeY.toFixed(2)}" r="5">
      <title>MMWR week ${regionalEscapeHtml(activeRecord.mmwr_week)}: ${regionalFormatNumber(activeRecord.predicted_weekly_incidence_per_100k)} per 100k</title>
    </circle>
    <text class="chart-label" x="${padding.left}" y="${height - 10}">MMWR weeks ${regionalEscapeHtml(minWeek)}-${regionalEscapeHtml(maxWeek)}</text>
    <text class="chart-label" x="${padding.left}" y="13">${regionalFormatNumber(maxValue)} per 100k</text>
  </svg>`;
  summary.textContent = `${countyName} weekly forecast window, MMWR weeks ${minWeek}-${maxWeek}; selected week ${activeRecord.mmwr_week} has 95% empirical interval ${regionalFormatNumber(activeInterval[0])} to ${regionalFormatNumber(activeInterval[1])} per 100k.`;
}

function renderRegionalObservedHistoryChart(countyFips) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  const records = regionalCountyAnnualRecords(countyFips).filter(
    (record) => record.incidence_per_100k !== null
  );
  const feature = findRegionalCountyFeature(countyFips);
  const countyName =
    (feature && feature.properties && feature.properties.county_name) || countyFips;
  if (!records.length) {
    target.innerHTML = "<p>No observed annual incidence rows are available for this county.</p>";
    summary.textContent = `${countyName} observed annual incidence history unavailable`;
    return;
  }

  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 22, bottom: 34, left: 46 };
  const years = records.map((record) => Number(record.year));
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxValue = Math.max(
    1,
    ...records.map((record) => Number(record.incidence_per_100k || 0))
  );
  const xScale = (year) =>
    padding.left +
    ((Number(year) - minYear) / Math.max(1, maxYear - minYear)) *
      (width - padding.left - padding.right);
  const yScale = (value) =>
    height -
    padding.bottom -
    (Number(value || 0) / maxValue) * (height - padding.top - padding.bottom);
  const linePath = records
    .map((record, index) => {
      const x = xScale(record.year).toFixed(2);
      const y = yScale(record.incidence_per_100k).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  const activeRecord =
    records.find((record) => Number(record.year) === regionalState.selectedYear) ||
    records[records.length - 1];
  const activeX = xScale(activeRecord.year);
  const activeY = yScale(activeRecord.incidence_per_100k);

  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${regionalEscapeHtml(countyName)} observed annual incidence history">
    <path class="observed-history-line" d="${linePath}"><title>Observed reported annual incidence</title></path>
    <line class="chart-axis" x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"></line>
    <line class="chart-axis" x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"></line>
    <circle class="active-week-marker" data-active-year="${regionalEscapeHtml(activeRecord.year)}" cx="${activeX.toFixed(2)}" cy="${activeY.toFixed(2)}" r="5">
      <title>${regionalEscapeHtml(activeRecord.year)}: ${regionalFormatNumber(activeRecord.incidence_per_100k)} per 100k</title>
    </circle>
    <text class="chart-label" x="${padding.left}" y="${height - 10}">Observed years ${regionalEscapeHtml(minYear)}-${regionalEscapeHtml(maxYear)}</text>
    <text class="chart-label" x="${padding.left}" y="13">${regionalFormatNumber(maxValue)} per 100k</text>
  </svg>`;
  summary.textContent = `${countyName} observed annual incidence history, ${minYear}-${maxYear}; selected year ${activeRecord.year} reported ${regionalFormatNumber(activeRecord.incidence_per_100k)} per 100k.`;
}

function regionalLinePath(records, xScale, yScale) {
  return records
    .map((record, index) => {
      const x = xScale(record.mmwr_week).toFixed(2);
      const y = yScale(record.predicted_weekly_incidence_per_100k).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
}

function regionalIntervalBandPath(records, field, xScale, yScale) {
  const upper = records.map((record, index) => {
    const interval = record[field] || [0, 0];
    return `${index === 0 ? "M" : "L"} ${xScale(record.mmwr_week).toFixed(2)} ${yScale(interval[1]).toFixed(2)}`;
  });
  const lower = records
    .slice()
    .reverse()
    .map((record) => {
      const interval = record[field] || [0, 0];
      return `L ${xScale(record.mmwr_week).toFixed(2)} ${yScale(interval[0]).toFixed(2)}`;
    });
  return `${upper.join(" ")} ${lower.join(" ")} Z`;
}

function renderRegionalSources() {
  const target = document.getElementById("regional-source-content");
  const modelCard = regionalState.modelCard || {};
  const sourceCatalog = regionalState.sourceCatalog || {};
  const annual = regionalState.annual || {};
  const policy = sourceCatalog.data_lag_and_update_policy || {};
  const sources = sourceCatalog.sources || [];
  const annualCaveat = (annual.caveats || []).find((caveat) =>
    String(caveat).toLowerCase().includes("reported cases")
  );
  const sourceItems = sources
    .map(
      (source) =>
        `<li><b>${regionalEscapeHtml(regionalReadableName(source.source_id))}</b>: ${regionalEscapeHtml(source.public_notes || source.notes || "Derived research input.")}</li>`
    )
    .join("");
  target.innerHTML = `<p><b>Research only:</b> ${regionalEscapeHtml(modelCard.score_interpretation || "Relative seasonal Lyme forecast on a 1 to 10 scale.")} This is not public Maryland default.</p>
    <p>${regionalEscapeHtml(policy.why_forecasting || "Official county surveillance data lag real-world exposure conditions.")}</p>
    <p>${regionalEscapeHtml(policy.forecast_boundary || "Forecast-safe branches use prior-year and trailing regional data only.")}</p>
    ${annualCaveat ? `<p>${regionalEscapeHtml(annualCaveat)}</p>` : ""}
    <p>${regionalEscapeHtml(modelCard.method_summary || "Regional forecast-safe county-week risk research layer.")}</p>
    ${sourceItems ? `<ul class="source-detail-list">${sourceItems}</ul>` : ""}`;
}

function renderRegionalForecastProvenance() {
  const target = document.getElementById("regional-forecast-provenance");
  const mode = selectedRegionalDataMode();
  if (mode === "observed_historical" || mode === "unavailable") {
    target.innerHTML = `<dl class="regional-provenance-grid">
      <div>
        <dt>Data mode</dt>
        <dd>${regionalEscapeHtml(regionalModeLabel(mode))}${mode === "observed_historical" ? " reported incidence" : ""}</dd>
      </div>
      <div>
        <dt>Selected year</dt>
        <dd>${regionalEscapeHtml(regionalState.selectedYear || "unknown")}</dd>
      </div>
      <div>
        <dt>Boundary</dt>
        <dd>Research only, not public Maryland default</dd>
      </div>
    </dl>`;
    return;
  }
  const weekly = regionalState.weekly || {};
  const modelCard = regionalState.modelCard || {};
  const selectedForecast = weekly.selected_forecast_metadata || {};
  const modelName =
    modelCard.model_name || weekly.model_name || "regional research forecast";
  const forecastYear = regionalState.selectedYear || selectedForecast.forecast_year;
  const mixedNote =
    mode === "mixed"
      ? `<div>
        <dt>Data mode</dt>
        <dd>Mixed observed/forecast</dd>
      </div>`
      : "";
  target.innerHTML = `<dl class="regional-provenance-grid">
    ${mixedNote}
    <div>
      <dt>Model</dt>
      <dd>${regionalEscapeHtml(regionalReadableName(modelName))}</dd>
    </div>
    <div>
      <dt>Forecast origin</dt>
      <dd>Forecast origin ${regionalEscapeHtml(selectedForecast.forecast_origin_year || "unknown")}</dd>
    </div>
    <div>
      <dt>Forecast year</dt>
      <dd>Forecast year ${regionalEscapeHtml(forecastYear || "unknown")}</dd>
    </div>
    <div>
      <dt>Boundary</dt>
      <dd>Research only, not public Maryland default</dd>
    </div>
  </dl>`;
}

function regionalForecastYearFromRecords() {
  const years = regionalForecastYearsFromRecords();
  if (years.length === 1) {
    return String(years[0]);
  }
  if (years.length > 1) {
    return `${years[0]}-${years[years.length - 1]}`;
  }
  return "";
}

function regionalForecastYearsFromRecords() {
  return Array.from(
    new Set(
      ((regionalState.weekly && regionalState.weekly.records) || [])
        .map((record) => regionalRecordYear(record))
        .filter((year) => Number.isFinite(year))
    )
  ).sort((left, right) => left - right);
}

function selectedRegionalRegimeId() {
  const metadata = regionalState.metadataByCounty.get(regionalState.selectedCounty);
  const regime = metadata && metadata.selected_spatial_regime;
  return regime && regime.region_id;
}

function updateRegionalSelectedControls() {
  document.querySelectorAll("[data-county]").forEach((element) => {
    const isSelected = element.dataset.county === regionalState.selectedCounty;
    element.setAttribute("aria-pressed", String(isSelected));
    element.classList.toggle("is-selected", isSelected);
  });
}

function findRegionalCountyFeature(countyFips) {
  if (!regionalState.counties) return null;
  return regionalState.counties.features.find(
    (feature) => feature.properties.county_fips === countyFips
  );
}

function renderRegionalLoadError(error) {
  document.getElementById("regional-risk-map").innerHTML = `<p role="alert">${regionalEscapeHtml(error.message)}</p>`;
  document.getElementById("regional-county-list").innerHTML = "";
  document.getElementById("regional-panel-content").innerHTML =
    "<p>Regional research data bundle is unavailable.</p>";
  document.getElementById("regional-regime-panel").innerHTML =
    '<h3 id="regional-regime-title">Localized spatial regime</h3><p class="muted">Regional regime data are unavailable.</p>';
  document.getElementById("regional-source-content").innerHTML =
    "<p>Regional source notes are unavailable.</p>";
  document.getElementById("regional-forecast-provenance").innerHTML =
    "<p>Regional forecast provenance is unavailable.</p>";
}

function regionalGeoBounds(features) {
  const bounds = {
    minX: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
  };
  for (const feature of features) {
    for (const point of regionalCoordinates(feature.geometry)) {
      expandRegionalBounds(bounds, point);
    }
  }
  if (!Number.isFinite(bounds.minX)) {
    return {
      minX: 0,
      maxX: 1,
      minY: 0,
      maxY: 1,
    };
  }
  return bounds;
}

function expandRegionalBounds(bounds, point) {
  const x = Number(point && point[0]);
  const y = Number(point && point[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return;
  }
  if (x < bounds.minX) bounds.minX = x;
  if (x > bounds.maxX) bounds.maxX = x;
  if (y < bounds.minY) bounds.minY = y;
  if (y > bounds.maxY) bounds.maxY = y;
}

function regionalCoordinates(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates.flat();
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(2);
  if (geometry.type === "Point") return [geometry.coordinates];
  return [];
}

function regionalGeometryPath(geometry, bounds, width, height) {
  if (geometry.type === "Polygon") {
    return regionalPolygonPath(geometry.coordinates, bounds, width, height);
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => regionalPolygonPath(polygon, bounds, width, height))
      .join(" ");
  }
  const [x, y] = regionalProjectPoint(geometry.coordinates, bounds, width, height);
  return `M ${x - 3} ${y - 3} h 6 v 6 h -6 Z`;
}

function regionalPolygonPath(rings, bounds, width, height) {
  return rings
    .map(
      (ring) =>
        ring
          .map((point, index) => {
            const [x, y] = regionalProjectPoint(point, bounds, width, height);
            return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
          })
          .join(" ") + " Z"
    )
    .join(" ");
}

function regionalProjectPoint(point, bounds, width, height) {
  const padding = 24;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const rangeX = bounds.maxX - bounds.minX || 1;
  const rangeY = bounds.maxY - bounds.minY || 1;
  const x = padding + ((point[0] - bounds.minX) / rangeX) * usableWidth;
  const y = padding + ((bounds.maxY - point[1]) / rangeY) * usableHeight;
  return [x, y];
}

function regionalRiskClass(score) {
  if (score >= 9) return "risk-very-high";
  if (score >= 7) return "risk-high";
  if (score >= 5) return "risk-moderate";
  if (score >= 3) return "risk-low";
  return "risk-very-low";
}

function regionalObservedRiskClass(record) {
  if (!record) return "risk-unavailable";
  const tier = String(record.diagnostic_midatlantic_incidence_tier || "");
  if (tier === "top_decile") return "risk-very-high";
  if (tier === "top_quintile") return "risk-high";
  if (tier === "upper_half") return "risk-moderate";
  if (tier === "lower_half") return "risk-low";
  return "risk-unavailable";
}

function regionalReadableFlag(flag) {
  return (
    regionalFlagLabels[flag] ||
    regionalSentenceCase(String(flag).replaceAll("_", " "))
  );
}

function regionalReadableName(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function regionalSentenceCase(value) {
  const text = regionalCategoryLabel(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function regionalCategoryLabel(value) {
  return String(value).replaceAll("_", " ");
}

function regionalFormatNumber(value) {
  return Number(value || 0).toFixed(2);
}

function regionalEscapeHtml(value) {
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
