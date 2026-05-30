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
  forecastView: "annual",
  forecastScope: "region",
  forecastScopeState: "",
  forecastScopeCounty: null,
  biteEstimateRequested: false,
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
};

const regionalHiddenFlagCaveats = new Set([
  "not_public_default",
  "not_public_maryland_default",
]);

const regionalSurveillanceProtocols = [
  {
    startYear: 2022,
    label: "2022 surveillance definition era",
    note:
      "High-incidence jurisdictions can rely more on laboratory reporting, so reported counts can rise because reporting changed.",
  },
  {
    startYear: 2008,
    label: "2008 surveillance definition era",
    note:
      "The national definition added probable cases and narrowed laboratory evidence, so counts are not perfectly comparable with earlier years.",
  },
  {
    startYear: 1996,
    label: "1996 surveillance definition era",
    note:
      "The national definition recommended two-step testing and changed how cases were counted for surveillance.",
  },
  {
    startYear: Number.NEGATIVE_INFINITY,
    label: "pre-1996 surveillance definition era",
    note:
      "Early national surveillance is useful history, but it should not be compared to later eras without caveats.",
  },
];

document.addEventListener("DOMContentLoaded", initRegionalResearch);

async function initRegionalResearch() {
  document
    .getElementById("year-select")
    .addEventListener("change", handleYearSelectChange);
  document
    .querySelectorAll('input[name="forecast-view"]')
    .forEach((input) => input.addEventListener("change", handleForecastViewChange));
  document
    .querySelectorAll('input[name="forecast-scope"]')
    .forEach((input) => input.addEventListener("change", handleForecastScopeChange));
  document
    .getElementById("forecast-state-select")
    .addEventListener("change", handleForecastStateChange);
  document
    .getElementById("forecast-county-select")
    .addEventListener("change", handleForecastCountyChange);
  document
    .getElementById("week-input")
    .addEventListener("input", handleWeekInputChange);
  document
    .getElementById("week-slider")
    .addEventListener("input", handleWeekSliderInput);
  document
    .getElementById("state-filter")
    .addEventListener("change", handleRegionalListFilterChange);
  document
    .getElementById("county-search")
    .addEventListener("input", handleRegionalListFilterChange);
  document
    .getElementById("regional-county-picker")
    .addEventListener("change", handleRegionalCountyPickerChange);
  document
    .getElementById("regional-bite-form")
    .addEventListener("submit", handleRegionalBiteSubmit);

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
    renderRegionalForecastScopeControls();
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
    regionalState.overlaysByRegime.set(
      `${Number(overlay.forecast_year)}:${overlay.region_id}`,
      overlay
    );
  }
}

function setRegionalWeekBounds(records) {
  const weeks = Array.from(new Set(records.map((record) => Number(record.mmwr_week))))
    .filter((week) => Number.isFinite(week))
    .sort((left, right) => left - right);
  const input = document.getElementById("week-input");
  const slider = document.getElementById("week-slider");
  if (!weeks.length) {
    regionalState.selectedWeek = Number(regionalState.selectedWeek) || 1;
    input.min = "1";
    input.max = "53";
    slider.min = "1";
    slider.max = "53";
    input.value = String(regionalState.selectedWeek);
    slider.value = String(regionalState.selectedWeek);
    updateRegionalWeekLabel();
    return;
  }
  input.min = String(weeks[0]);
  input.max = String(weeks[weeks.length - 1]);
  slider.min = String(weeks[0]);
  slider.max = String(weeks[weeks.length - 1]);
  regionalState.selectedWeek = regionalClampWeek(
    Number(regionalState.selectedWeek) || weeks[0]
  );
  syncRegionalWeekControls();
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
  updateRegionalForecastViewControl();
  updateRegionalYearLabel();
  updateRegionalWeekLabel();
}

function handleYearSelectChange(event) {
  regionalState.selectedYear = Number(event.target.value);
  updateRegionalForecastViewControl();
  setRegionalWeekBounds(regionalForecastRecordsForSelectedYear());
  updateRegionalYearLabel();
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  renderRegionalSources();
  renderRegionalForecastProvenance();
  selectRegionalCounty(regionalState.selectedCounty);
}

function handleForecastViewChange(event) {
  regionalState.forecastView =
    event.target.value === "weekly" ? "weekly" : "annual";
  updateRegionalForecastViewControl();
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  renderRegionalForecastProvenance();
  selectRegionalCounty(regionalState.selectedCounty);
}

function handleForecastScopeChange(event) {
  regionalState.forecastScope = regionalForecastScopeValue(event.target.value);
  if (regionalState.forecastScope === "county") {
    const countyFips =
      regionalState.forecastScopeCounty || regionalState.selectedCounty;
    regionalState.forecastScopeCounty = countyFips;
    if (countyFips && countyFips !== regionalState.selectedCounty) {
      selectRegionalCounty(countyFips);
      return;
    }
  }
  syncRegionalForecastScopeControls();
  renderRegionalForecastVisualization();
}

function handleForecastStateChange(event) {
  regionalState.forecastScope = "state";
  regionalState.forecastScopeState = event.target.value;
  syncRegionalForecastScopeControls();
  renderRegionalForecastVisualization();
}

function handleForecastCountyChange(event) {
  regionalState.forecastScope = "county";
  regionalState.forecastScopeCounty = event.target.value;
  syncRegionalForecastScopeControls();
  selectRegionalCounty(regionalState.forecastScopeCounty);
}

function handleWeekSliderInput(event) {
  regionalState.selectedWeek = regionalClampWeek(Number(event.target.value));
  syncRegionalWeekControls();
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  selectRegionalCounty(regionalState.selectedCounty);
}

function handleWeekInputChange(event) {
  regionalState.selectedWeek = regionalClampWeek(Number(event.target.value));
  syncRegionalWeekControls();
  updateRegionalWeekLabel();
  renderRegionalMap();
  renderRegionalCountyList();
  selectRegionalCounty(regionalState.selectedCounty);
}

function syncRegionalWeekControls() {
  const input = document.getElementById("week-input");
  const slider = document.getElementById("week-slider");
  input.value = String(regionalState.selectedWeek);
  slider.value = String(regionalState.selectedWeek);
}

function handleRegionalListFilterChange() {
  regionalState.stateFilter = document.getElementById("state-filter").value;
  regionalState.countySearch = document
    .getElementById("county-search")
    .value.trim()
    .toLowerCase();
  renderRegionalCountyList();
}

function handleRegionalCountyPickerChange(event) {
  const countyFips = event.target.value;
  regionalState.forecastScope = "county";
  regionalState.forecastScopeCounty = countyFips;
  syncRegionalForecastScopeControls();
  selectRegionalCounty(countyFips);
}

function handleRegionalBiteSubmit(event) {
  event.preventDefault();
  regionalState.biteEstimateRequested = true;
  renderRegionalBiteResult();
}

function updateRegionalWeekLabel() {
  const input = document.getElementById("week-input");
  const slider = document.getElementById("week-slider");
  const yearRecords = regionalForecastRecordsForSelectedYear();
  const hasWeeklyRows = yearRecords.length > 0;
  const view = selectedRegionalForecastView();
  const enableWeekControls = hasWeeklyRows && view === "weekly";
  input.disabled = !enableWeekControls;
  slider.disabled = !enableWeekControls;
  if (!enableWeekControls) {
    const mode = selectedRegionalDataMode();
    let message = "Weekly controls are disabled for annual views";
    if (mode === "forecast" || mode === "mixed") {
      message = isLatestRegionalForecastYear()
        ? "Choose Weekly seasonal risk to use MMWR week controls"
        : "Weekly seasonal risk is only available for the current forecast year";
    } else if (mode === "observed_historical") {
      message = "Observed historical years are annual only";
    }
    document.getElementById("week-label").textContent = message;
    return;
  }
  const activeRecord = yearRecords.find(
    (record) => Number(record.mmwr_week) === regionalState.selectedWeek
  );
  const dateRange = regionalWeekDateRange(activeRecord);
  const weekText = `MMWR week ${regionalState.selectedWeek}`;
  document.getElementById("week-label").textContent =
    dateRange ? `Using ${dateRange} (${weekText})` : `Using ${weekText}`;
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

function updateRegionalForecastViewControl() {
  const label = document.getElementById("forecast-view-label");
  const mode = selectedRegionalDataMode();
  const hasForecast = regionalForecastRecordsForSelectedYear().length > 0;
  const weeklyAvailable = hasForecast && isLatestRegionalForecastYear();
  if (!weeklyAvailable && regionalState.forecastView === "weekly") {
    regionalState.forecastView = "annual";
  }
  const view = selectedRegionalForecastView();
  syncRegionalForecastViewRadios(weeklyAvailable, view);
  if (view === "weekly") {
    label.textContent = "Weekly seasonal risk: seasonally allocated forecast";
  } else if (mode === "forecast" || mode === "mixed") {
    label.textContent =
      "Annual forecast: predicted annual incidence and cases";
  } else if (mode === "observed_historical") {
    label.textContent = "Observed historical annual data";
  } else {
    label.textContent = "No annual forecast or observed data for this year";
  }
}

function syncRegionalForecastViewRadios(weeklyAvailable, view) {
  const annual = document.getElementById("forecast-view-annual");
  const weekly = document.getElementById("forecast-view-weekly");
  annual.checked = view !== "weekly";
  weekly.checked = view === "weekly";
  weekly.disabled = !weeklyAvailable;
}

function syncRegionalForecastScopeControls() {
  const scope = regionalForecastScopeValue(regionalState.forecastScope);
  regionalState.forecastScope = scope;
  const region = document.getElementById("forecast-scope-region");
  const state = document.getElementById("forecast-scope-state");
  const county = document.getElementById("forecast-scope-county");
  const stateSelect = document.getElementById("forecast-state-select");
  const countySelect = document.getElementById("forecast-county-select");
  if (!region || !state || !county || !stateSelect || !countySelect) return;

  region.checked = scope === "region";
  state.checked = scope === "state";
  county.checked = scope === "county";
  stateSelect.disabled = scope !== "state";
  countySelect.disabled = scope !== "county";

  if (regionalState.forecastScopeState) {
    stateSelect.value = regionalState.forecastScopeState;
  } else if (stateSelect.options.length) {
    regionalState.forecastScopeState = stateSelect.value;
  }
  const countyFips = regionalForecastScopeCountyFips();
  if (countyFips) {
    countySelect.value = countyFips;
  }
}

function regionalForecastScopeValue(value) {
  return value === "state" || value === "county" ? value : "region";
}

function selectedRegionalYearMode() {
  return selectedRegionalDataMode();
}

function selectedRegionalDataMode() {
  return regionalDataModeForYear(regionalState.selectedYear);
}

function selectedRegionalForecastView() {
  const hasForecast = regionalForecastRecordsForSelectedYear().length > 0;
  if (!hasForecast) return "observed";
  if (regionalState.forecastView === "weekly" && isLatestRegionalForecastYear()) {
    return "weekly";
  }
  return "annual";
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
  const forecastRecord = getRegionalForecastRecord(countyFips);
  if (selectedMode === "mixed") {
    if (forecastRecord) return "forecast";
    if (annualRecord) return "observed_historical";
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
  if (mode === "mixed") return "Forecast with observed comparison";
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
  regionalState.forecastScopeCounty = regionalState.selectedCounty;
  const selectedFeature = findRegionalCountyFeature(regionalState.selectedCounty);
  regionalState.forecastScopeState =
    (selectedFeature && selectedFeature.properties.state_abbr) ||
    regionalState.forecastScopeState ||
    "";
  syncRegionalForecastScopeControls();
}

function getRegionalRecord(countyFips) {
  return regionalState.byCountyYearWeek.get(
    `${countyFips}:${regionalState.selectedYear}:${regionalState.selectedWeek}`
  );
}

function getRegionalForecastRecord(countyFips) {
  return getRegionalRecord(countyFips) || regionalCountyWeekRecords(countyFips)[0] || null;
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

function regionalTimeControlRecordsForSelectedYear() {
  return regionalForecastRecordsForSelectedYear();
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
    shape.addEventListener("click", () => selectRegionalCountyFromMap(shape.dataset.county));
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectRegionalCountyFromMap(shape.dataset.county);
      }
    });
  });
  document.getElementById("regional-map-meta").textContent =
    `${features.length} county-equivalents across DE, DC, MD, PA, VA, and WV`;
  renderRegionalLegend();
  updateRegionalSelectedControls();
}

function selectRegionalCountyFromMap(countyFips) {
  regionalState.forecastScope = "county";
  regionalState.forecastScopeCounty = countyFips;
  syncRegionalForecastScopeControls();
  selectRegionalCounty(countyFips);
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
  const regime = regionalSelectedRegimeForYear(metadata);
  const selectedRegime = selectedRegionalRegimeId();
  const stateAbbr = props.state_abbr || "";
  const annualRecord = getRegionalAnnualRecord(countyFips);
  const countyMode = regionalCountyDataMode(countyFips);
  const forecastView = selectedRegionalForecastView();
  const annualSummary = regionalAnnualForecastSummary(countyFips);
  let displayClass = "risk-unavailable";
  let label = `${props.county_name}, ${stateAbbr}, no observed or forecast row available for ${regionalState.selectedYear}`;
  if (countyMode === "forecast" && forecastView === "weekly" && record) {
    displayClass = regionalRiskClass(record.risk_score);
    label = `${props.county_name}, ${stateAbbr}, ${regionalCategoryLabel(record.risk_category)}, ${record.risk_score} of 10`;
  } else if (countyMode === "forecast" && annualSummary.record) {
    displayClass = regionalAnnualIncidenceClass(
      annualSummary.predictedAnnualIncidence
    );
    label = `${props.county_name}, ${stateAbbr}, predicted annual incidence ${regionalFormatNumber(annualSummary.predictedAnnualIncidence)} per 100k in ${regionalState.selectedYear}`;
  } else if (countyMode === "observed_historical" && annualRecord) {
    displayClass = regionalObservedRiskClass(annualRecord);
    label = `${props.county_name}, ${stateAbbr}, observed reported incidence ${regionalFormatNumber(annualRecord.incidence_per_100k)} per 100k in ${regionalState.selectedYear}`;
  }
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
  const picker = document.getElementById("regional-county-picker");
  const features = filteredRegionalFeatures();
  picker.innerHTML = features.map(regionalCountyPickerOption).join("");
  const selectedInResults = features.some(
    (feature) => (feature.properties || {}).county_fips === regionalState.selectedCounty
  );
  if (selectedInResults) {
    picker.value = regionalState.selectedCounty;
  } else if (features.length) {
    picker.value = (features[0].properties || {}).county_fips;
  }
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

function renderRegionalForecastScopeControls() {
  const stateSelect = document.getElementById("forecast-state-select");
  const countySelect = document.getElementById("forecast-county-select");
  const features = regionalState.counties ? regionalState.counties.features || [] : [];
  const states = Array.from(
    new Set(features.map((feature) => feature.properties && feature.properties.state_abbr))
  )
    .filter(Boolean)
    .sort();
  stateSelect.innerHTML = states
    .map((stateAbbr) => `<option value="${regionalEscapeHtml(stateAbbr)}">${regionalEscapeHtml(stateAbbr)}</option>`)
    .join("");
  countySelect.innerHTML = features
    .slice()
    .sort((left, right) =>
      regionalCountySortLabel(left).localeCompare(regionalCountySortLabel(right))
    )
    .map((feature) => {
      const props = feature.properties || {};
      const label = `${props.county_name || props.county_fips}, ${props.state_abbr || ""}`;
      return `<option value="${regionalEscapeHtml(props.county_fips)}">${regionalEscapeHtml(label)}</option>`;
    })
    .join("");
  if (!regionalState.forecastScopeState && states.length) {
    regionalState.forecastScopeState = states[0];
  }
  syncRegionalForecastScopeControls();
}

function regionalCountySortLabel(feature) {
  const props = feature.properties || {};
  return `${props.state_abbr || ""} ${props.county_name || ""} ${props.county_fips || ""}`;
}

function renderRegionalListStatus(count) {
  const status = document.getElementById("regional-list-status");
  const noun = count === 1 ? "county choice" : "county choices";
  status.textContent = `${count} ${noun}`;
}

function regionalCountyPickerOption(feature) {
  const props = feature.properties || {};
  const record = getRegionalRecord(props.county_fips);
  const annualRecord = getRegionalAnnualRecord(props.county_fips);
  const countyMode = regionalCountyDataMode(props.county_fips);
  const forecastView = selectedRegionalForecastView();
  const annualSummary = regionalAnnualForecastSummary(props.county_fips);
  const score = countyMode === "forecast"
    ? forecastView === "weekly" && record
      ? `${record.risk_score}/10`
      : annualSummary.record &&
          Number.isFinite(annualSummary.predictedAnnualIncidence)
        ? `${regionalFormatNumber(annualSummary.predictedAnnualIncidence)}/100k`
        : "NA"
    : countyMode === "observed_historical" &&
        annualRecord &&
        annualRecord.incidence_per_100k !== null
      ? `${regionalFormatNumber(annualRecord.incidence_per_100k)}/100k`
      : "NA";
  const category = countyMode === "forecast"
    ? forecastView === "weekly" && record
      ? regionalCategoryLabel(record.risk_category)
      : annualSummary.record
        ? "annual forecast"
        : "unavailable"
    : countyMode === "observed_historical" && annualRecord
      ? regionalReadableName(annualRecord.diagnostic_midatlantic_incidence_tier)
      : "unavailable";

  return `<option value="${regionalEscapeHtml(props.county_fips)}">${regionalEscapeHtml(props.county_name)}${props.state_abbr ? `, ${regionalEscapeHtml(props.state_abbr)}` : ""} - ${regionalEscapeHtml(category)} - ${regionalEscapeHtml(score)}</option>`;
}

function selectRegionalCounty(countyFips) {
  if (!countyFips) return;
  regionalState.selectedCounty = countyFips;
  if (regionalState.forecastScope === "county" || !regionalState.forecastScopeCounty) {
    regionalState.forecastScopeCounty = countyFips;
  }
  syncRegionalForecastScopeControls();
  const record = getRegionalRecord(countyFips);
  const feature = findRegionalCountyFeature(countyFips);
  const metadata = regionalState.metadataByCounty.get(countyFips);
  const props = feature ? feature.properties : {};
  const countyName = props.county_name || (metadata && metadata.county_name) || countyFips;
  const stateAbbr = props.state_abbr || "";
  const panel = document.getElementById("regional-panel-content");
  const countyMode = regionalCountyDataMode(countyFips);
  const forecastView = selectedRegionalForecastView();

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

  if (countyMode === "forecast" && forecastView === "annual") {
    renderRegionalAnnualForecastCounty({
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
      renderRegionalForecastVisualization();
    } else {
      renderRegionalForecastVisualization();
    }
    renderRegionalMap();
    updateRegionalSelectedControls();
    return;
  }

  const interval80 = record.predicted_weekly_incidence_80_interval || [0, 0];
  const interval95 = record.predicted_weekly_incidence_95_interval || [0, 0];
  const dateRange = regionalWeekDateRange(record);
  const periodText = dateRange
    ? `${dateRange} (MMWR week ${record.mmwr_week})`
    : `MMWR week ${record.mmwr_week}`;
  panel.innerHTML = `<div class="score-card">
    <p class="muted">${regionalEscapeHtml(periodText)}, forecast year ${regionalEscapeHtml(record.data_year || record.year)}</p>
    <h3>${regionalEscapeHtml(countyName)}${stateAbbr ? `, ${regionalEscapeHtml(stateAbbr)}` : ""}</h3>
    <p><span class="score-badge ${regionalRiskClass(record.risk_score)}">${regionalEscapeHtml(record.risk_score)}/10</span> ${regionalEscapeHtml(regionalCategoryLabel(record.risk_category))}</p>
    <p>Predicted weekly incidence: ${regionalFormatNumber(record.predicted_weekly_incidence_per_100k)} per 100k.</p>
    <p>80% empirical interval: ${regionalFormatNumber(interval80[0])} to ${regionalFormatNumber(interval80[1])} per 100k.</p>
    <p>95% empirical interval: ${regionalFormatNumber(interval95[0])} to ${regionalFormatNumber(interval95[1])} per 100k.</p>
    ${renderRegionalScaleDiagnostics(record)}
    ${renderRegionalProtocolNote(record.data_year || record.year)}
    ${renderRegionalForecastBasis(record)}
    ${renderRegionalComparableYear(record, metadata)}
    ${renderRegionalForecastTypicality(metadata)}
    ${renderRegionalCountyRegime(metadata)}
    ${renderRegionalFlagCaveats(record)}
    <p class="disclaimer">Informational only. This is not a per-bite infection probability, diagnosis, or treatment recommendation.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalForecastVisualization();
  renderRegionalMap();
  updateRegionalSelectedControls();
}

function renderRegionalAnnualForecastCounty({
  countyFips,
  countyName,
  stateAbbr,
  metadata,
  panel,
}) {
  const summary = regionalAnnualForecastSummary(countyFips);
  const record = summary.record;
  if (!record) {
    panel.innerHTML = `<p>No annual forecast row is available for ${regionalEscapeHtml(countyName)} in ${regionalEscapeHtml(regionalState.selectedYear)}.</p>`;
    renderRegionalRegime(metadata);
    renderRegionalForecastVisualization();
    renderRegionalMap();
    updateRegionalSelectedControls();
    return;
  }
  const annualClass = regionalAnnualIncidenceClass(summary.predictedAnnualIncidence);
  const casesText = Number.isFinite(summary.predictedAnnualCases)
    ? regionalFormatNumber(summary.predictedAnnualCases)
    : "unavailable in this bundle";
  const weeklyHint = isLatestRegionalForecastYear()
    ? "<p>Use Weekly seasonal risk to see how this annual forecast is allocated across the current forecast season.</p>"
    : "<p>Weekly seasonal risk is shown only for the current forecast year; this year stays annual.</p>";
  panel.innerHTML = `<div class="score-card">
    <p class="muted">Annual forecast for ${regionalEscapeHtml(record.data_year || record.year)}</p>
    <h3>${regionalEscapeHtml(countyName)}${stateAbbr ? `, ${regionalEscapeHtml(stateAbbr)}` : ""}</h3>
    <p><span class="score-badge ${annualClass}">${regionalFormatNumber(summary.predictedAnnualIncidence)}/100k</span> predicted annual incidence</p>
    <p>Predicted annual incidence: ${regionalFormatNumber(summary.predictedAnnualIncidence)} per 100k.</p>
    <p>Predicted annual cases: ${regionalEscapeHtml(casesText)}.</p>
    ${weeklyHint}
    ${renderRegionalObservedAnnualContext(countyFips)}
    ${renderRegionalForecastCheck(metadata)}
    ${renderRegionalProtocolNote(record.data_year || record.year)}
    ${renderRegionalForecastBasis(record)}
    ${renderRegionalComparableYear(record, metadata)}
    ${renderRegionalForecastTypicality(metadata)}
    ${renderRegionalCountyRegime(metadata)}
    ${renderRegionalFlagCaveats(record)}
    <p class="disclaimer">Informational only. This is a forecast of reported Lyme disease pressure, not a per-bite infection probability, diagnosis, or treatment recommendation.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalForecastVisualization();
  renderRegionalMap();
  updateRegionalSelectedControls();
}

function regionalAnnualForecastSummary(countyFips) {
  const records = regionalCountyWeekRecords(countyFips);
  const selectedRecord =
    records.find((record) => Number(record.mmwr_week) === regionalState.selectedWeek) ||
    records[0] ||
    null;
  if (!selectedRecord) {
    return {
      record: null,
      records,
      predictedAnnualCases: null,
      predictedAnnualIncidence: null,
    };
  }
  const predictedAnnualIncidence = Number(
    selectedRecord.predicted_annual_incidence_per_100k
  );
  let predictedAnnualCases = Number(selectedRecord.predicted_annual_cases);
  if (!Number.isFinite(predictedAnnualCases)) {
    const weeklyCasesForSelectedRecord = Number(selectedRecord.predicted_weekly_cases);
    const weeklyIncidenceForSelectedRecord = Number(
      selectedRecord.predicted_weekly_incidence_per_100k
    );
    if (
      Number.isFinite(weeklyCasesForSelectedRecord) &&
      Number.isFinite(weeklyIncidenceForSelectedRecord) &&
      Number.isFinite(predictedAnnualIncidence) &&
      weeklyIncidenceForSelectedRecord > 0
    ) {
      predictedAnnualCases =
        weeklyCasesForSelectedRecord *
        (predictedAnnualIncidence / weeklyIncidenceForSelectedRecord);
    }
  }
  if (!Number.isFinite(predictedAnnualCases)) {
    const weeklyCases = records
      .map((record) => Number(record.predicted_weekly_cases))
      .filter((value) => Number.isFinite(value));
    predictedAnnualCases = weeklyCases.length
      ? weeklyCases.reduce((total, value) => total + value, 0)
      : Number.NaN;
  }
  return {
    record: selectedRecord,
    records,
    predictedAnnualCases,
    predictedAnnualIncidence,
  };
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

function renderRegionalForecastBasis(record) {
  const basis = (regionalState.weekly && regionalState.weekly.forecast_basis) ||
    (regionalState.modelCard && regionalState.modelCard.forecast_basis) ||
    {};
  const branch = basis.selected_branch || {};
  const seasonal = basis.seasonal_allocation || {};
  const uncertainty = basis.uncertainty || {};
  const updatePolicy = basis.update_policy || {};
  const forecastOrigin =
    branch.forecast_origin_year ||
    (regionalState.weekly &&
      regionalState.weekly.selected_forecast_metadata &&
      regionalState.weekly.selected_forecast_metadata.forecast_origin_year) ||
    record.forecast_origin_year ||
    "unknown";
  const dataCutoff =
    branch.data_cutoff_date ||
    (regionalState.weekly &&
      regionalState.weekly.selected_forecast_metadata &&
      regionalState.weekly.selected_forecast_metadata.data_cutoff_date) ||
    "unknown";
  const modelName =
    branch.model_name ||
    record.model_name ||
    (regionalState.weekly && regionalState.weekly.model_name) ||
    "selected forecast branch";
  const signalsUsed = regionalForecastBasisList(
    basis.signals_used,
    "prior reported Lyme incidence"
  );
  const seasonalityScope =
    seasonal.scope || "national Lyme onset seasonality";
  const seasonalityRole =
    seasonal.role ||
    "allocates the annual county forecast across MMWR weeks";
  const intervalMethod =
    uncertainty.interval_method ||
    record.annual_interval_method ||
    "empirical forecast residuals";
  const bayesianMethod =
    updatePolicy.bayesian_update_method || "gamma_poisson_case_multiplier";
  const latestCdcYear = regionalLatestCdcCountyYear(forecastOrigin, dataCutoff);

  return `<section class="lineage-strip forecast-basis" aria-labelledby="regional-forecast-basis-heading">
    <h4 id="regional-forecast-basis-heading">Why this forecast?</h4>
    <p><b>County data:</b> County level data are released as annual totals only. The most recent CDC county data available in this release are ${regionalEscapeHtml(latestCdcYear)}.</p>
    <p><b>What the model uses:</b> ${signalsUsed}. Selected model: ${regionalEscapeHtml(regionalReadableName(modelName))}.</p>
    <p><b>Weekly estimates:</b> Weekly estimates are based on known tick activity cycles. The annual county forecast is spread across MMWR weeks using ${regionalEscapeHtml(seasonalityScope)}.</p>
    <p><b>Seasonal allocation:</b> ${regionalEscapeHtml(seasonalityRole)}.</p>
    <p><b>Forecast interval:</b> ${regionalEscapeHtml(regionalReadableName(intervalMethod))}; bands show model uncertainty around reported-incidence estimates.</p>
    <p><b>Bayesian updates:</b> ${regionalEscapeHtml(regionalReadableName(bayesianMethod))} is not part of the displayed score yet. It is reserved for backtests and future updates when new annual data arrive.</p>
  </section>`;
}

function regionalLatestCdcCountyYear(forecastOrigin, dataCutoff) {
  const originYear = Number(forecastOrigin);
  if (Number.isFinite(originYear)) return String(originYear);
  const cutoffMatch = String(dataCutoff || "").match(/^(\d{4})-/);
  return cutoffMatch ? cutoffMatch[1] : "unknown";
}

function regionalForecastBasisList(items, fallback) {
  const values = Array.isArray(items) && items.length ? items : [fallback];
  return values.map((item) => regionalEscapeHtml(String(item))).join(", ");
}

function renderRegionalComparableYear(record, metadata) {
  const matches =
    metadata && Array.isArray(metadata.nearest_comparable_years)
      ? metadata.nearest_comparable_years
      : [];
  const forecastYear = Number(record.data_year || record.year);
  const match = matches.find(
    (candidate) => Number(candidate.forecast_year) === forecastYear
  );
  if (!match) return "";
  const distance =
    match.match_distance === undefined || match.match_distance === null
      ? "unknown distance"
      : `distance ${regionalFormatNumber(match.match_distance)}`;
  const horizon =
    match.forecast_horizon_years === undefined || match.forecast_horizon_years === null
      ? "horizon-matched"
      : `${regionalEscapeHtml(match.forecast_horizon_years)}-year horizon`;
  return `<section class="lineage-strip comparable-year" aria-labelledby="regional-comparable-year-heading">
    <h4 id="regional-comparable-year-heading">Nearest comparable history</h4>
    <p>${regionalEscapeHtml(match.match_origin_year)} origin -&gt; ${regionalEscapeHtml(match.match_observed_year)} observed outcome (${horizon}; ${regionalEscapeHtml(distance)}).</p>
    <p>Basis: ${regionalEscapeHtml(match.basis || "horizon-matched reported-incidence history")} from ${regionalEscapeHtml(regionalReadableName(match.analog_model_name || "analog_year_county_incidence"))}.</p>
  </section>`;
}

function renderRegionalForecastTypicality(metadata) {
  const typicality = regionalForecastTypicalityForYear(metadata);
  if (!typicality) return "";
  const percentile = regionalOrdinalPercentile(
    typicality.forecast_percentile_of_county_history
  );
  const lower = regionalOrdinalPercentile(
    typicality.lower_80_percentile_of_county_history
  );
  const upper = regionalOrdinalPercentile(
    typicality.upper_80_percentile_of_county_history
  );
  const comparisonYears =
    typicality.comparison_year_start && typicality.comparison_year_end
      ? `${typicality.comparison_year_start}-${typicality.comparison_year_end}`
      : "prior reported years";
  const evidence = typicality.typicality_evidence_level || "limited";
  return `<section class="lineage-strip forecast-typicality" aria-labelledby="regional-forecast-typicality-heading">
    <h4 id="regional-forecast-typicality-heading">How unusual is this forecast?</h4>
    <p>Compared with this county's prior reported Lyme years (${regionalEscapeHtml(comparisonYears)}), this forecast is <b>${regionalEscapeHtml(typicality.severity_label || "not classified")}</b> (${regionalEscapeHtml(percentile)} percentile).</p>
    <p><b>Forecast interval range:</b> likely range ${regionalEscapeHtml(lower)}-${regionalEscapeHtml(upper)} percentile; evidence ${regionalEscapeHtml(evidence)}.</p>
    <p>This compares reported annual Lyme incidence. It is not tick abundance, infected tick prevalence, or individual infection probability.</p>
  </section>`;
}

function regionalForecastTypicalityForYear(metadata) {
  const records =
    metadata && Array.isArray(metadata.forecast_typicality)
      ? metadata.forecast_typicality
      : [];
  const selectedYear = Number(regionalState.selectedYear);
  return (
    records.find((record) => Number(record.forecast_year) === selectedYear) ||
    null
  );
}

function regionalSelectedRegimeForYear(metadata) {
  const regime = metadata && metadata.selected_spatial_regime;
  const selectedYear = Number(regionalState.selectedYear);
  const regimeYearMatches =
    regime && Number(regime.forecast_year) === selectedYear;
  if (
    !regime ||
    !Number.isFinite(selectedYear) ||
    !regimeYearMatches
  ) {
    return null;
  }
  return regime;
}

function regionalSelectedRegimeOverlay(regime) {
  if (!regime) return null;
  const selectedYear = Number(regionalState.selectedYear);
  if (!Number.isFinite(selectedYear)) return null;
  const overlay = regionalState.overlaysByRegime.get(
    `${selectedYear}:${regime.region_id}`
  );
  const overlayYearMatches =
    overlay && Number(overlay.forecast_year) === selectedYear;
  if (!overlay || !overlayYearMatches) return null;
  return overlay;
}

function regionalOrdinalPercentile(value) {
  const percentile = Number(value);
  if (!Number.isFinite(percentile)) return "unknown";
  const rounded = Math.round(percentile);
  const mod100 = rounded % 100;
  if (mod100 >= 11 && mod100 <= 13) {
    return `${rounded}th`;
  }
  const mod10 = rounded % 10;
  if (mod10 === 1) return `${rounded}st`;
  if (mod10 === 2) return `${rounded}nd`;
  if (mod10 === 3) return `${rounded}rd`;
  return `${rounded}th`;
}

function regionalWeekDateRange(record) {
  if (!record) return "";
  return formatRegionalDateRange(record.week_start_date, record.week_end_date);
}

function formatRegionalDateRange(startIso, endIso) {
  const start = regionalDateParts(startIso);
  const end = regionalDateParts(endIso);
  if (!start || !end) return "";
  if (start.year === end.year && start.month === end.month) {
    return `${start.monthName} ${start.day}-${end.day}, ${end.year}`;
  }
  if (start.year === end.year) {
    return `${start.monthName} ${start.day}-${end.monthName} ${end.day}, ${end.year}`;
  }
  return `${start.monthName} ${start.day}, ${start.year}-${end.monthName} ${end.day}, ${end.year}`;
}

function regionalDateParts(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))) return null;
  const [year, month, day] = String(value).split("-").map(Number);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
    return null;
  }
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return {
    day,
    month,
    monthName: date.toLocaleString("en-US", { month: "short", timeZone: "UTC" }),
    year,
  };
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
    renderRegionalForecastVisualization();
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
    ${renderRegionalForecastCheck(metadata)}
    ${renderRegionalProtocolNote(annualRecord.year)}
    ${renderRegionalHistoricalRegimeNotice()}
    ${renderRegionalFlagCaveats(annualRecord)}
    <p class="disclaimer">Reported cases are not stable true incidence. This historical layer is informational only, not medical advice, and not a forecast-safe feature for the selected year.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalForecastVisualization();
  renderRegionalMap();
  updateRegionalSelectedControls();
}

function renderRegionalForecastCheck(metadata) {
  const fit = getRegionalForecastObservedFit(metadata);
  if (!fit) return "";
  const observed = Number(fit.observed_incidence_per_100k);
  const forecast = Number(fit.predicted_incidence_per_100k);
  const residual = Number(fit.incidence_residual_per_100k);
  if (
    !Number.isFinite(observed) ||
    !Number.isFinite(forecast) ||
    !Number.isFinite(residual)
  ) {
    return "";
  }
  const residualText = `${residual >= 0 ? "+" : ""}${regionalFormatNumber(residual)}`;
  const observedCases = Number(fit.observed_cases);
  const predictedCases = Number(fit.predicted_cases);
  const caseText =
    Number.isFinite(observedCases) && Number.isFinite(predictedCases)
      ? `<p>Cases: observed ${regionalFormatNumber(observedCases)} vs forecast ${regionalFormatNumber(predictedCases)}.</p>`
      : "";
  return `<section class="lineage-strip forecast-check" aria-labelledby="regional-forecast-check-heading">
    <h4 id="regional-forecast-check-heading">PA 2024 forecast check</h4>
    <p>Artifact-backed partial state-source overlay: observed ${regionalFormatNumber(observed)} per 100k vs forecast ${regionalFormatNumber(forecast)} per 100k; residual ${regionalEscapeHtml(residualText)} per 100k.</p>
    ${caseText}
    <p>This is post-forecast goodness-of-fit context, not regional truth, model training data, or automatic calibration.</p>
  </section>`;
}

function getRegionalForecastObservedFit(metadata) {
  const records =
    metadata && Array.isArray(metadata.forecast_observed_fit)
      ? metadata.forecast_observed_fit
      : [];
  const selectedYear = Number(regionalState.selectedYear);
  return (
    records.find((record) => Number(record.forecast_year) === selectedYear) ||
    null
  );
}

function renderRegionalProtocolNote(year) {
  const protocol = regionalSurveillanceProtocolForYear(year);
  return `<details class="lineage-strip protocol-note" open>
    <summary>Surveillance protocol</summary>
    <p><b>Protocol era:</b> ${regionalEscapeHtml(protocol.label)}.</p>
    <p>${regionalEscapeHtml(protocol.note)}</p>
    <p>Major Lyme surveillance definition breaks include 1996, 2008, and 2022. Cross-era comparisons should use source-regime terms or a harmonized index, not silent case-count correction.</p>
  </details>`;
}

function regionalSurveillanceProtocolForYear(year) {
  const selectedYear = Number(year);
  if (!Number.isFinite(selectedYear)) {
    return {
      label: "unknown surveillance definition era",
      note:
        "The selected year is unavailable, so cross-year comparability should be treated as unknown.",
    };
  }
  return regionalSurveillanceProtocols.find(
    (protocol) => selectedYear >= protocol.startYear
  );
}

function renderRegionalObservedAnnualContext(countyFips) {
  const annualRecord = getRegionalAnnualRecord(countyFips);
  if (!annualRecord) {
    return "<p>No observed annual context is available for this county.</p>";
  }
  return `<section class="lineage-strip" aria-labelledby="regional-observed-annual-heading">
    <h4 id="regional-observed-annual-heading">Observed annual context</h4>
    <p>${regionalEscapeHtml(annualRecord.year)} reported ${regionalEscapeHtml(annualRecord.reported_cases)} cases at ${regionalFormatNumber(annualRecord.incidence_per_100k)} per 100k.</p>
  </section>`;
}

function renderRegionalCountyRegime(metadata) {
  if (!regionalShowForecastRegimeContext()) {
    return renderRegionalHistoricalRegimeNotice();
  }
  const regime = regionalSelectedRegimeForYear(metadata);
  if (!regime) {
    return `<section class="lineage-strip" aria-labelledby="regional-lineage-heading">
      <h4 id="regional-lineage-heading">Local forecast region</h4>
      <p>No local forecast region summary is available for ${regionalEscapeHtml(regionalState.selectedYear || "the selected forecast year")}.</p>
    </section>`;
  }
  const dataThrough = regime.forecast_origin_year || "the latest complete CDC county year";
  return `<section class="lineage-strip" aria-labelledby="regional-lineage-heading">
    <h4 id="regional-lineage-heading">Local forecast region</h4>
    <dl class="lineage-grid">
      <div>
        <dt>Model region</dt>
        <dd>${regionalEscapeHtml(regime.region_name || regime.region_id)}</dd>
      </div>
      <div>
        <dt>Forecast year</dt>
        <dd>${regionalEscapeHtml(regime.forecast_year || regionalState.selectedYear)}</dd>
      </div>
      <div>
        <dt>Data through</dt>
        <dd>${regionalEscapeHtml(dataThrough)}</dd>
      </div>
    </dl>
  </section>`;
}

function renderRegionalHistoricalRegimeNotice() {
  return `<section class="lineage-strip" aria-labelledby="regional-historical-regime-heading">
    <h4 id="regional-historical-regime-heading">Forecast region context</h4>
    <p>Forecast regions are shown only for forecast years. The selected historical map is observed annual data, so forecast feature years and forecast origins are hidden here.</p>
  </section>`;
}

function renderRegionalRegime(metadata) {
  const target = document.getElementById("regional-regime-panel");
  if (!regionalShowForecastRegimeContext()) {
    target.innerHTML = `<h3 id="regional-regime-title">Forecast region context</h3>
      <p class="muted">Forecast regions are shown only for forecast years. This view is observed annual data for ${regionalEscapeHtml(regionalState.selectedYear || "the selected year")}.</p>`;
    return;
  }
  const regime = regionalSelectedRegimeForYear(metadata);
  if (!regime) {
    target.innerHTML = `<h3 id="regional-regime-title">Local forecast region</h3><p class="muted">No local forecast region summary is available for ${regionalEscapeHtml(regionalState.selectedYear || "the selected forecast year")}.</p>`;
    return;
  }
  const overlay = regionalSelectedRegimeOverlay(regime);
  if (!overlay) {
    target.innerHTML = `<h3 id="regional-regime-title">Local forecast region</h3>
      <p><b>${regionalEscapeHtml(regime.region_name || regime.region_id)}</b></p>
      <p class="muted">No local forecast region summary is available for ${regionalEscapeHtml(regionalState.selectedYear || "the selected forecast year")}.</p>`;
    return;
  }
  const interval80 = overlay.predicted_incidence_80_interval || [0, 0];
  const interval95 = overlay.predicted_incidence_95_interval || [0, 0];
  const countyNames = regionalRegimeCountyNames(overlay);
  const countyItems = countyNames
    .map((countyName) => `<li>${regionalEscapeHtml(countyName)}</li>`)
    .join("");
  target.innerHTML = `<h3 id="regional-regime-title">Local forecast region</h3>
    <p><b>${regionalEscapeHtml(overlay.region_name || overlay.region_id)}</b></p>
    <p>Forecast year ${regionalEscapeHtml(overlay.forecast_year || regionalState.selectedYear)}. Region includes ${regionalEscapeHtml(overlay.n_counties)} counties with similar local history.</p>
    <section class="regional-regime-counties" aria-labelledby="regional-regime-counties-title">
      <h4 id="regional-regime-counties-title">Region counties</h4>
      <ul>${countyItems}</ul>
    </section>
    <dl class="regional-regime-metrics">
      <div>
        <dt>Region incidence</dt>
        <dd>${regionalFormatNumber(overlay.predicted_incidence_per_100k)} per 100k</dd>
      </div>
      <div>
        <dt>Region 80% interval</dt>
        <dd>${regionalFormatNumber(interval80[0])} to ${regionalFormatNumber(interval80[1])} per 100k</dd>
      </div>
      <div>
        <dt>Region 95% interval</dt>
        <dd>Region 95% interval: ${regionalFormatNumber(interval95[0])} to ${regionalFormatNumber(interval95[1])} per 100k</dd>
      </div>
    </dl>
    <p class="muted">States remain display and reporting rollups; this region is a local modeling group.</p>`;
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
  for (const hiddenFlag of regionalHiddenFlagCaveats) {
    flags.delete(hiddenFlag);
  }
  if (!flags.size) return "";
  const items = Array.from(flags)
    .map((flag) => `<li>${regionalEscapeHtml(regionalReadableFlag(flag))}</li>`)
    .join("");
  return `<section class="flag-caveats" aria-labelledby="regional-flag-heading">
    <h4 id="regional-flag-heading">What to know about this score</h4>
    <ul class="flag-list">${items}</ul>
  </section>`;
}

function renderRegionalBiteResult() {
  const target = document.getElementById("regional-bite-result");
  const record = regionalBiteForecastRecord();
  if (!record) {
    target.innerHTML =
      "<p>Select a county with a current forecast before estimating bite concern.</p>";
    return;
  }
  const result = estimateRegionalSingleBiteRisk(record, readRegionalBiteInputs());
  const criteriaItems = result.pep_criteria
    .map(
      (criterion) => `<li>
        <span class="criteria-status">${regionalEscapeHtml(criterion.status)}</span>
        <span>${regionalEscapeHtml(regionalReadableName(criterion.criterion))}</span>
        <small>${regionalEscapeHtml(criterion.explanation)}</small>
      </li>`
    )
    .join("");
  const dateRange = regionalWeekDateRange(record);
  const periodText = dateRange
    ? `${dateRange} (MMWR week ${record.mmwr_week})`
    : `MMWR week ${record.mmwr_week}`;

  target.innerHTML = `<section aria-labelledby="regional-bite-result-title">
    <h4 id="regional-bite-result-title">Bite concern score</h4>
    <p class="muted">Uses ${regionalEscapeHtml(periodText)} forecast context for ${regionalEscapeHtml(record.county_name || record.county_fips)}.</p>
    <p><span class="score-badge ${regionalRiskClass(result.single_bite_risk_score)}">${regionalEscapeHtml(result.single_bite_risk_score)}/10</span> ${regionalEscapeHtml(result.single_bite_risk_band)}</p>
    <p>${regionalEscapeHtml(result.risk_interpretation)}</p>
    <p><b>CDC consideration context:</b> ${regionalEscapeHtml(regionalReadableName(result.pep_consideration))}</p>
    <ul class="criteria-list">${criteriaItems}</ul>
    ${renderRegionalBiteCaveats(result.caveats)}
    <p class="disclaimer">This is not an absolute infection probability, diagnosis, or treatment recommendation.</p>
  </section>`;
}

function readRegionalBiteInputs() {
  return {
    attachment_hours: regionalOptionalNumber("regional-bite-attachment-hours"),
    doxycycline_safe: regionalOptionalBoolean("regional-bite-doxycycline-safe"),
    engorgement: document.getElementById("regional-bite-engorgement").value,
    hours_since_removal: regionalOptionalNumber("regional-bite-hours-since-removal"),
    tick_count: regionalOptionalNumber("regional-bite-tick-count") || 1,
    tick_species: document.getElementById("regional-bite-tick-species").value,
    tick_stage: document.getElementById("regional-bite-tick-stage").value,
  };
}

function estimateRegionalSingleBiteRisk(record, input) {
  const modifiers = {
    attachment: regionalAttachmentModifier(
      input.attachment_hours,
      input.engorgement
    ),
    location_season: regionalLocationSeasonModifier(record),
    tick_species: regionalSpeciesModifier(input.tick_species),
    tick_stage: regionalStageModifier(input.tick_stage),
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
  const criteria = regionalPepCriteria(record, input);
  return {
    caveats: regionalBiteCaveats(record, input),
    evidence_modifiers: modifiers,
    pep_consideration: regionalPepConsideration(criteria),
    pep_criteria: criteria,
    risk_interpretation:
      "This score combines the selected county-week forecast with tick identity, stage, attachment, engorgement, and tick count. It is not an absolute infection probability.",
    single_bite_risk_band: regionalBiteRiskBand(score),
    single_bite_risk_score: score,
    single_bite_risk_score_raw: scoreRaw,
  };
}

function regionalBiteForecastRecord() {
  const countyFips = regionalState.selectedCounty;
  if (!countyFips) return null;
  const selectedRecord = getRegionalRecord(countyFips);
  if (selectedRecord && isLatestRegionalForecastYear()) return selectedRecord;
  const latestYear = latestRegionalForecastYear();
  const records = (regionalState.recordsByCounty.get(countyFips) || []).filter(
    (record) => regionalRecordYear(record) === latestYear
  );
  return (
    records.find((record) => Number(record.mmwr_week) === regionalState.selectedWeek) ||
    records[0] ||
    null
  );
}

function regionalLocationSeasonModifier(record) {
  const scoreBaseline = Number(record.risk_score || 1) / 10;
  const annualIncidence = Number(record.predicted_annual_incidence_per_100k);
  if (Number.isFinite(annualIncidence) && annualIncidence >= 50) {
    return Math.max(scoreBaseline, 0.55);
  }
  if (Number.isFinite(annualIncidence) && annualIncidence >= 25) {
    return Math.max(scoreBaseline, 0.35);
  }
  return scoreBaseline;
}

function regionalSpeciesModifier(species) {
  if (species === "ixodes_scapularis") return 1;
  if (species === "possible_ixodes") return 0.75;
  if (species === "unknown") return 0.5;
  return 0.05;
}

function regionalStageModifier(stage) {
  if (stage === "nymph") return 1;
  if (stage === "adult") return 0.85;
  if (stage === "larva") return 0.1;
  return 0.7;
}

function regionalAttachmentModifier(hours, engorgement) {
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

function regionalPepCriteria(record, input) {
  return [
    regionalLymeCommonAreaCriterion(record),
    regionalTickIdentityCriterion(input),
    regionalAttachmentCriterion(input),
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

function regionalLymeCommonAreaCriterion(record) {
  const annualIncidence = Number(record.predicted_annual_incidence_per_100k);
  const riskScore = Number(record.risk_score);
  const status =
    riskScore >= 5 || annualIncidence >= 25
      ? "meets"
      : riskScore >= 3
        ? "uncertain"
        : "not_met";
  return {
    criterion: "local_forecast_context",
    explanation:
      "Uses the selected county's forecast context because public county-week tick infection prevalence is not available.",
    status,
  };
}

function regionalTickIdentityCriterion(input) {
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
    explanation:
      "CDC Lyme prophylaxis guidance focuses on adult or nymphal blacklegged ticks.",
    status,
  };
}

function regionalAttachmentCriterion(input) {
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
    explanation: "CDC guidance treats 36+ hours or engorgement as a key consideration.",
    status,
  };
}

function regionalPepConsideration(criteria) {
  const statuses = new Set(criteria.map((criterion) => criterion.status));
  if (statuses.size === 1 && statuses.has("meets")) {
    return "meets_cdc_consideration_criteria";
  }
  if (statuses.has("not_met")) {
    return "does_not_meet_cdc_consideration_criteria";
  }
  return "partially_meets_cdc_consideration_criteria";
}

function regionalBiteRiskBand(score) {
  if (score >= 9) return "high";
  if (score >= 7) return "elevated";
  if (score >= 5) return "moderate";
  if (score >= 3) return "low";
  return "very low";
}

function regionalBiteCaveats(record, input) {
  const caveats = [
    "not_calibrated_absolute_probability",
    "not_diagnosis_or_treatment_recommendation",
    "regional_forecast_context_not_tick_test",
  ];
  if (input.tick_species === "not_ixodes") {
    caveats.push("non_ixodes_lyme_vector_unlikely");
  }
  if (!isLatestRegionalForecastYear(regionalRecordYear(record))) {
    caveats.push("uses_latest_available_forecast_context");
  }
  return caveats;
}

function renderRegionalBiteCaveats(caveats) {
  if (!caveats || !caveats.length) return "";
  const items = caveats
    .map((caveat) => `<li>${regionalEscapeHtml(regionalReadableBiteCaveat(caveat))}</li>`)
    .join("");
  return `<section class="bite-caveats" aria-labelledby="regional-bite-caveats-title">
    <h5 id="regional-bite-caveats-title">Bite-specific caveats</h5>
    <ul>${items}</ul>
  </section>`;
}

function regionalReadableBiteCaveat(caveat) {
  const labels = {
    non_ixodes_lyme_vector_unlikely: "non blacklegged tick Lyme vector unlikely",
    not_calibrated_absolute_probability:
      "not calibrated as an absolute infection probability",
    not_diagnosis_or_treatment_recommendation:
      "not a diagnosis or treatment recommendation",
    regional_forecast_context_not_tick_test:
      "county forecast context is not a tick test or infected-tick prevalence measurement",
    uses_latest_available_forecast_context:
      "uses the latest available weekly forecast context for this county",
  };
  return labels[caveat] || regionalSentenceCase(String(caveat).replaceAll("_", " "));
}

function renderRegionalForecastVisualization() {
  syncRegionalForecastScopeControls();
  const view = selectedRegionalForecastView();
  if (view === "weekly") {
    renderRegionalWeeklyScopeChart(regionalAggregateWeeklyForecastRecords());
    return;
  }
  if (selectedRegionalDataMode() === "observed_historical") {
    renderRegionalObservedScopeHistoryChart(regionalAggregateObservedAnnualRecords());
    return;
  }
  renderRegionalAnnualScopeChart(regionalAggregateAnnualForecastSummary());
}

function regionalForecastScopeCountyFips() {
  return regionalState.forecastScopeCounty || regionalState.selectedCounty;
}

function regionalForecastScopeFeatures() {
  const features = regionalState.counties ? regionalState.counties.features || [] : [];
  const scope = regionalForecastScopeValue(regionalState.forecastScope);
  if (scope === "state") {
    const stateAbbr = regionalState.forecastScopeState;
    return features.filter(
      (feature) => (feature.properties || {}).state_abbr === stateAbbr
    );
  }
  if (scope === "county") {
    const countyFips = regionalForecastScopeCountyFips();
    return features.filter(
      (feature) => (feature.properties || {}).county_fips === countyFips
    );
  }
  return features;
}

function regionalForecastScopeLabel() {
  const scope = regionalForecastScopeValue(regionalState.forecastScope);
  if (scope === "state") {
    return `${regionalState.forecastScopeState || "Selected"} state`;
  }
  if (scope === "county") {
    const feature = findRegionalCountyFeature(regionalForecastScopeCountyFips());
    return (
      (feature && feature.properties && feature.properties.county_name) ||
      regionalForecastScopeCountyFips() ||
      "Selected county"
    );
  }
  return "Regional";
}

function regionalForecastScopeCountyCountText(count) {
  const noun = count === 1 ? "county" : "counties";
  return `${count} ${noun} in this chart`;
}

function regionalForecastScopeAnnualTitle(scopeLabel) {
  if (scopeLabel === "Regional") return "Regional annual forecast";
  return `${scopeLabel} annual forecast`;
}

function regionalAggregateAnnualForecastSummary() {
  const features = regionalForecastScopeFeatures();
  const countySummaries = features
    .map((feature) =>
      regionalAnnualForecastSummary((feature.properties || {}).county_fips)
    )
    .filter(
      (summary) =>
        summary.record &&
        Number.isFinite(Number(summary.predictedAnnualIncidence))
    );
  let totalCases = 0;
  let totalPopulation = 0;
  let weightedValueCount = 0;
  let incidenceTotal = 0;
  let forecastYear = null;
  for (const summary of countySummaries) {
    forecastYear =
      forecastYear ||
      Number(summary.record.data_year || summary.record.year) ||
      regionalState.selectedYear;
    const incidence = Number(summary.predictedAnnualIncidence);
    const cases = Number(summary.predictedAnnualCases);
    const population = regionalPopulationFromCasesAndIncidence(cases, incidence);
    if (Number.isFinite(population) && population > 0 && Number.isFinite(cases)) {
      totalCases += cases;
      totalPopulation += population;
      weightedValueCount += 1;
    } else if (Number.isFinite(incidence)) {
      incidenceTotal += incidence;
    }
  }
  const fallbackAverage = countySummaries.length
    ? incidenceTotal / countySummaries.length
    : Number.NaN;
  const predictedAnnualIncidence =
    totalPopulation > 0 ? (totalCases / totalPopulation) * 100000 : fallbackAverage;
  return {
    countyCount: countySummaries.length,
    forecastYear: forecastYear || regionalState.selectedYear,
    observedRecords: regionalAggregateObservedAnnualRecords(features),
    predictedAnnualCases: weightedValueCount ? totalCases : Number.NaN,
    predictedAnnualIncidence,
    scopeLabel: regionalForecastScopeLabel(),
  };
}

function regionalAggregateObservedAnnualRecords(features = regionalForecastScopeFeatures()) {
  const recordsByYear = new Map();
  for (const feature of features) {
    const countyFips = (feature.properties || {}).county_fips;
    for (const record of regionalCountyAnnualRecords(countyFips)) {
      const year = Number(record.year);
      if (!Number.isFinite(year)) continue;
      if (!recordsByYear.has(year)) {
        recordsByYear.set(year, {
          incidenceFallbackTotal: 0,
          incidenceFallbackCount: 0,
          population: 0,
          reported_cases: 0,
          year,
        });
      }
      const aggregate = recordsByYear.get(year);
      const incidence = Number(record.incidence_per_100k);
      const cases = Number(record.reported_cases);
      const population = Number(record.population);
      if (
        Number.isFinite(cases) &&
        Number.isFinite(population) &&
        population > 0
      ) {
        aggregate.reported_cases += cases;
        aggregate.population += population;
      } else if (Number.isFinite(incidence)) {
        aggregate.incidenceFallbackTotal += incidence;
        aggregate.incidenceFallbackCount += 1;
      }
    }
  }
  return Array.from(recordsByYear.values())
    .map((record) => {
      const incidence =
        record.population > 0
          ? (record.reported_cases / record.population) * 100000
          : record.incidenceFallbackCount
            ? record.incidenceFallbackTotal / record.incidenceFallbackCount
            : Number.NaN;
      return {
        incidence_per_100k: incidence,
        population: record.population,
        reported_cases: record.reported_cases,
        year: record.year,
      };
    })
    .filter((record) => Number.isFinite(record.incidence_per_100k))
    .sort((left, right) => Number(left.year) - Number(right.year));
}

function regionalAggregateWeeklyForecastRecords() {
  const recordsByWeek = new Map();
  for (const feature of regionalForecastScopeFeatures()) {
    const countyFips = (feature.properties || {}).county_fips;
    for (const record of regionalCountyWeekRecords(countyFips)) {
      const week = Number(record.mmwr_week);
      if (!Number.isFinite(week)) continue;
      if (!recordsByWeek.has(week)) {
        recordsByWeek.set(week, {
          interval80LowerCases: 0,
          interval80UpperCases: 0,
          interval95LowerCases: 0,
          interval95UpperCases: 0,
          population: 0,
          predicted_weekly_cases: 0,
          week_end_date: record.week_end_date,
          week_start_date: record.week_start_date,
          mmwr_week: week,
        });
      }
      const aggregate = recordsByWeek.get(week);
      const population = regionalForecastPopulation(record);
      const weeklyCases = Number(record.predicted_weekly_cases);
      const weeklyIncidence = Number(record.predicted_weekly_incidence_per_100k);
      const cases = Number.isFinite(weeklyCases)
        ? weeklyCases
        : Number.isFinite(population) && population > 0 && Number.isFinite(weeklyIncidence)
          ? (weeklyIncidence / 100000) * population
          : Number.NaN;
      if (!Number.isFinite(population) || population <= 0 || !Number.isFinite(cases)) {
        continue;
      }
      aggregate.population += population;
      aggregate.predicted_weekly_cases += cases;
      regionalAddIntervalCases(
        aggregate,
        record.predicted_weekly_incidence_80_interval,
        population,
        "interval80LowerCases",
        "interval80UpperCases"
      );
      regionalAddIntervalCases(
        aggregate,
        record.predicted_weekly_incidence_95_interval,
        population,
        "interval95LowerCases",
        "interval95UpperCases"
      );
    }
  }
  return Array.from(recordsByWeek.values())
    .map((record) => ({
      mmwr_week: record.mmwr_week,
      predicted_weekly_incidence_80_interval:
        regionalIntervalCasesToRates(
          record.interval80LowerCases,
          record.interval80UpperCases,
          record.population
        ),
      predicted_weekly_incidence_95_interval:
        regionalIntervalCasesToRates(
          record.interval95LowerCases,
          record.interval95UpperCases,
          record.population
        ),
      predicted_weekly_incidence_per_100k:
        record.population > 0
          ? (record.predicted_weekly_cases / record.population) * 100000
          : Number.NaN,
      week_end_date: record.week_end_date,
      week_start_date: record.week_start_date,
    }))
    .filter((record) =>
      Number.isFinite(Number(record.predicted_weekly_incidence_per_100k))
    )
    .sort((left, right) => Number(left.mmwr_week) - Number(right.mmwr_week));
}

function regionalForecastPopulation(record) {
  const annualCases = Number(record.predicted_annual_cases);
  const annualIncidence = Number(record.predicted_annual_incidence_per_100k);
  const annualPopulation =
    regionalPopulationFromCasesAndIncidence(annualCases, annualIncidence);
  if (Number.isFinite(annualPopulation)) return annualPopulation;
  const weeklyCases = Number(record.predicted_weekly_cases);
  const weeklyIncidence = Number(record.predicted_weekly_incidence_per_100k);
  return regionalPopulationFromCasesAndIncidence(weeklyCases, weeklyIncidence);
}

function regionalPopulationFromCasesAndIncidence(cases, incidence) {
  const numericCases = Number(cases);
  const numericIncidence = Number(incidence);
  if (
    !Number.isFinite(numericCases) ||
    !Number.isFinite(numericIncidence) ||
    numericIncidence <= 0
  ) {
    return Number.NaN;
  }
  return (numericCases / numericIncidence) * 100000;
}

function regionalAddIntervalCases(aggregate, interval, population, lowerKey, upperKey) {
  const lower = Number(interval && interval[0]);
  const upper = Number(interval && interval[1]);
  if (Number.isFinite(lower)) {
    aggregate[lowerKey] += (lower / 100000) * population;
  }
  if (Number.isFinite(upper)) {
    aggregate[upperKey] += (upper / 100000) * population;
  }
}

function regionalIntervalCasesToRates(lowerCases, upperCases, population) {
  if (!Number.isFinite(population) || population <= 0) return [0, 0];
  return [(lowerCases / population) * 100000, (upperCases / population) * 100000];
}

function renderRegionalAnnualScopeChart(scopeSummary) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  if (
    !scopeSummary ||
    !Number.isFinite(Number(scopeSummary.predictedAnnualIncidence))
  ) {
    target.innerHTML = "<p>No annual forecast summary is available for this chart scope.</p>";
    summary.textContent = `${regionalForecastScopeAnnualTitle(regionalForecastScopeLabel())} unavailable`;
    return;
  }
  const observedRecords = scopeSummary.observedRecords || [];
  const forecastYear = Number(scopeSummary.forecastYear || regionalState.selectedYear);
  const points = [
    ...observedRecords.map((record) => ({
      kind: "observed",
      value: Number(record.incidence_per_100k),
      year: Number(record.year),
    })),
    {
      kind: "forecast",
      value: scopeSummary.predictedAnnualIncidence,
      year: forecastYear,
    },
  ].filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value));
  if (!points.length) {
    target.innerHTML = "<p>No annual forecast summary is available for this chart scope.</p>";
    summary.textContent = `${regionalForecastScopeAnnualTitle(scopeSummary.scopeLabel)} unavailable`;
    return;
  }
  const title = regionalForecastScopeAnnualTitle(scopeSummary.scopeLabel);
  const chart = regionalAnnualChartSvg({
    activeClass: "annual-forecast-point",
    activeTitle: `${forecastYear} forecast: ${regionalFormatNumber(scopeSummary.predictedAnnualIncidence)} per 100k`,
    activeValue: scopeSummary.predictedAnnualIncidence,
    activeYear: forecastYear,
    ariaLabel: `${scopeSummary.scopeLabel} annual incidence forecast and observed history`,
    observedRecords,
    points,
    xLabelPrefix: "Annual incidence",
  });
  target.innerHTML = chart;
  const casesText = Number.isFinite(Number(scopeSummary.predictedAnnualCases))
    ? regionalFormatNumber(scopeSummary.predictedAnnualCases)
    : "unavailable";
  summary.textContent = `${title} for ${forecastYear}. The brown line is observed annual reported incidence. The blue dot is the selected annual forecast: ${regionalFormatNumber(scopeSummary.predictedAnnualIncidence)} per 100k and ${casesText} predicted cases. ${regionalForecastScopeCountyCountText(scopeSummary.countyCount)}. County level CDC data are annual, so historical weeks or months are not shown.`;
}

function renderRegionalWeeklyScopeChart(records) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  const scopeLabel = regionalForecastScopeLabel();
  if (!records.length) {
    target.innerHTML = "<p>No weekly forecast rows are available for this chart scope.</p>";
    summary.textContent = `${scopeLabel} weekly forecast window unavailable`;
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

  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${regionalEscapeHtml(scopeLabel)} weekly forecast curve with empirical interval bands">
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
  summary.textContent = `${scopeLabel} weekly forecast, MMWR weeks ${minWeek}-${maxWeek}. The green line is the predicted weekly Lyme incidence. Dark blue band: narrower expected range from past forecast errors. Light blue band: wider expected range from past forecast errors. The red dot marks the selected week ${activeRecord.mmwr_week}, with a wider range of ${regionalFormatNumber(activeInterval[0])} to ${regionalFormatNumber(activeInterval[1])} per 100k. These ranges are uncertainty around reported-incidence forecasts, not medical confidence intervals.`;
}

function renderRegionalObservedScopeHistoryChart(records) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  const scopeLabel = regionalForecastScopeLabel();
  if (!records.length) {
    target.innerHTML = "<p>No observed annual incidence rows are available for this chart scope.</p>";
    summary.textContent = `${scopeLabel} observed annual incidence history unavailable`;
    return;
  }
  const activeRecord =
    records.find((record) => Number(record.year) === regionalState.selectedYear) ||
    records[records.length - 1];
  target.innerHTML = regionalAnnualChartSvg({
    activeClass: "active-week-marker",
    activeTitle: `${activeRecord.year}: ${regionalFormatNumber(activeRecord.incidence_per_100k)} per 100k`,
    activeValue: activeRecord.incidence_per_100k,
    activeYear: activeRecord.year,
    ariaLabel: `${scopeLabel} observed annual incidence history`,
    observedRecords: records,
    points: records.map((record) => ({
      kind: "observed",
      value: Number(record.incidence_per_100k),
      year: Number(record.year),
    })),
    xLabelPrefix: "Observed years",
  });
  const years = records.map((record) => Number(record.year));
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  summary.textContent = `${scopeLabel} observed annual incidence history, ${minYear}-${maxYear}; selected year ${activeRecord.year} reported ${regionalFormatNumber(activeRecord.incidence_per_100k)} per 100k.`;
}

function regionalAnnualChartSvg({
  activeClass,
  activeTitle,
  activeValue,
  activeYear,
  ariaLabel,
  observedRecords,
  points,
  xLabelPrefix,
}) {
  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 22, bottom: 34, left: 46 };
  const years = points.map((point) => Number(point.year));
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxValue = Math.max(1, ...points.map((point) => Number(point.value)));
  const xScale = (year) =>
    padding.left +
    ((Number(year) - minYear) / Math.max(1, maxYear - minYear)) *
      (width - padding.left - padding.right);
  const yScale = (value) =>
    height -
    padding.bottom -
    (Number(value || 0) / maxValue) * (height - padding.top - padding.bottom);
  const observedPath = observedRecords
    .filter((record) => Number.isFinite(Number(record.incidence_per_100k)))
    .map((record, index) => {
      const x = xScale(record.year).toFixed(2);
      const y = yScale(record.incidence_per_100k).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  const observedLine = observedPath
    ? `<path class="observed-history-line" d="${observedPath}"><title>Observed annual incidence history</title></path>`
    : "";
  const activeX = xScale(activeYear);
  const activeY = yScale(activeValue);
  const activeYearAttribute =
    activeClass === "annual-forecast-point" ? "data-active-year" : "data-active-year";
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${regionalEscapeHtml(ariaLabel)}">
    ${observedLine}
    <line class="chart-axis" x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"></line>
    <line class="chart-axis" x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"></line>
    <circle class="${regionalEscapeHtml(activeClass)}" ${activeYearAttribute}="${regionalEscapeHtml(activeYear)}" cx="${activeX.toFixed(2)}" cy="${activeY.toFixed(2)}" r="6">
      <title>${regionalEscapeHtml(activeTitle)}</title>
    </circle>
    <text class="chart-label" x="${padding.left}" y="${height - 10}">${regionalEscapeHtml(xLabelPrefix)} ${regionalEscapeHtml(minYear)}-${regionalEscapeHtml(maxYear)}</text>
    <text class="chart-label" x="${padding.left}" y="13">${regionalFormatNumber(maxValue)} per 100k</text>
  </svg>`;
}

function renderRegionalAnnualForecastChart(countyFips, annualSummary) {
  const target = document.getElementById("regional-forecast-chart");
  const summary = document.getElementById("regional-chart-summary");
  const feature = findRegionalCountyFeature(countyFips);
  const countyName =
    (feature && feature.properties && feature.properties.county_name) || countyFips;
  const observedRecords = regionalCountyAnnualRecords(countyFips).filter(
    (record) => record.incidence_per_100k !== null
  );
  const forecastRecord = annualSummary.record;
  if (!forecastRecord || !Number.isFinite(annualSummary.predictedAnnualIncidence)) {
    target.innerHTML = "<p>No annual forecast summary is available for this county.</p>";
    summary.textContent = `${countyName} annual forecast unavailable`;
    return;
  }

  const forecastYear = Number(forecastRecord.data_year || forecastRecord.year);
  const points = [
    ...observedRecords.map((record) => ({
      kind: "observed",
      value: Number(record.incidence_per_100k),
      year: Number(record.year),
    })),
    {
      kind: "forecast",
      value: annualSummary.predictedAnnualIncidence,
      year: forecastYear,
    },
  ].filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value));
  if (!points.length) {
    target.innerHTML = "<p>No annual forecast summary is available for this county.</p>";
    summary.textContent = `${countyName} annual forecast unavailable`;
    return;
  }

  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 22, bottom: 34, left: 46 };
  const years = points.map((point) => point.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxValue = Math.max(1, ...points.map((point) => point.value));
  const xScale = (year) =>
    padding.left +
    ((Number(year) - minYear) / Math.max(1, maxYear - minYear)) *
      (width - padding.left - padding.right);
  const yScale = (value) =>
    height -
    padding.bottom -
    (Number(value || 0) / maxValue) * (height - padding.top - padding.bottom);
  const observedPath = observedRecords
    .filter((record) => Number.isFinite(Number(record.incidence_per_100k)))
    .map((record, index) => {
      const x = xScale(record.year).toFixed(2);
      const y = yScale(record.incidence_per_100k).toFixed(2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  const forecastX = xScale(forecastYear);
  const forecastY = yScale(annualSummary.predictedAnnualIncidence);
  const observedLine = observedPath
    ? `<path class="observed-history-line" d="${observedPath}"><title>Observed annual incidence history</title></path>`
    : "";

  target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${regionalEscapeHtml(countyName)} annual incidence forecast and observed history">
    ${observedLine}
    <line class="chart-axis" x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"></line>
    <line class="chart-axis" x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"></line>
    <circle class="annual-forecast-point" data-active-year="${regionalEscapeHtml(forecastYear)}" cx="${forecastX.toFixed(2)}" cy="${forecastY.toFixed(2)}" r="6">
      <title>${regionalEscapeHtml(forecastYear)} forecast: ${regionalFormatNumber(annualSummary.predictedAnnualIncidence)} per 100k</title>
    </circle>
    <text class="chart-label" x="${padding.left}" y="${height - 10}">Annual incidence ${regionalEscapeHtml(minYear)}-${regionalEscapeHtml(maxYear)}</text>
    <text class="chart-label" x="${padding.left}" y="13">${regionalFormatNumber(maxValue)} per 100k</text>
  </svg>`;
  summary.textContent = `${countyName} annual forecast for ${forecastYear}. The brown line is observed annual reported incidence. The blue dot is the selected annual forecast: ${regionalFormatNumber(annualSummary.predictedAnnualIncidence)} per 100k and ${Number.isFinite(annualSummary.predictedAnnualCases) ? regionalFormatNumber(annualSummary.predictedAnnualCases) : "unavailable"} predicted cases. County level CDC data are annual, so historical weeks or months are not shown.`;
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
  summary.textContent = `${countyName} weekly forecast, MMWR weeks ${minWeek}-${maxWeek}. The green line is the predicted weekly Lyme incidence. Dark blue band: narrower expected range from past forecast errors. Light blue band: wider expected range from past forecast errors. The red dot marks the selected week ${activeRecord.mmwr_week}, with a wider range of ${regionalFormatNumber(activeInterval[0])} to ${regionalFormatNumber(activeInterval[1])} per 100k. These ranges are uncertainty around reported-incidence forecasts, not medical confidence intervals.`;
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
  target.innerHTML = `<p><b>Score role:</b> ${regionalEscapeHtml(modelCard.score_interpretation || "Relative seasonal Lyme forecast on a 1 to 10 scale.")}</p>
    <p><b>Map unit:</b> Annual forecast and historical years use reported Lyme incidence per 100k. Weekly seasonal risk is an optional current-year view that allocates the annual forecast across the season.</p>
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
        <dt>Map boundary</dt>
        <dd>DE, DC, MD, PA, VA, and WV counties; states are reporting and display rollups</dd>
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
        <dd>Forecast with observed comparison</dd>
      </div>`
      : "";
  target.innerHTML = `<dl class="regional-provenance-grid">
    ${mixedNote}
    <div>
      <dt>View</dt>
      <dd>${regionalEscapeHtml(selectedRegionalForecastView() === "weekly" ? "Weekly seasonal risk" : "Annual forecast")}</dd>
    </div>
    <div>
      <dt>Model</dt>
      <dd>${regionalEscapeHtml(regionalReadableName(modelName))}</dd>
    </div>
    <div>
      <dt>Data through</dt>
      <dd>Data through ${regionalEscapeHtml(selectedForecast.forecast_origin_year || "unknown")}</dd>
    </div>
    <div>
      <dt>Forecast year</dt>
      <dd>Forecast year ${regionalEscapeHtml(forecastYear || "unknown")}</dd>
    </div>
    <div>
      <dt>Map boundary</dt>
      <dd>DE, DC, MD, PA, VA, and WV counties; states are reporting and display rollups</dd>
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

function latestRegionalForecastYear() {
  const years = regionalForecastYearsFromRecords();
  return years.length ? years[years.length - 1] : null;
}

function isLatestRegionalForecastYear(year = regionalState.selectedYear) {
  const latestYear = latestRegionalForecastYear();
  return latestYear !== null && Number(year) === latestYear;
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
  if (!regionalShowForecastRegimeContext()) return null;
  const metadata = regionalState.metadataByCounty.get(regionalState.selectedCounty);
  const regime = regionalSelectedRegimeForYear(metadata);
  return regime && regime.region_id;
}

function regionalShowForecastRegimeContext() {
  if (!regionalState.selectedCounty) return false;
  return regionalCountyDataMode(regionalState.selectedCounty) === "forecast";
}

function updateRegionalSelectedControls() {
  document.querySelectorAll("[data-county]").forEach((element) => {
    const isSelected = element.dataset.county === regionalState.selectedCounty;
    element.setAttribute("aria-pressed", String(isSelected));
    element.classList.toggle("is-selected", isSelected);
  });
  const picker = document.getElementById("regional-county-picker");
  if (picker && regionalState.selectedCounty) {
    picker.value = regionalState.selectedCounty;
  }
  if (regionalState.biteEstimateRequested) {
    renderRegionalBiteResult();
  }
}

function findRegionalCountyFeature(countyFips) {
  if (!regionalState.counties) return null;
  return regionalState.counties.features.find(
    (feature) => feature.properties.county_fips === countyFips
  );
}

function renderRegionalLoadError(error) {
  document.getElementById("regional-risk-map").innerHTML = `<p role="alert">${regionalEscapeHtml(error.message)}</p>`;
  document.getElementById("regional-county-picker").innerHTML = "";
  document.getElementById("regional-panel-content").innerHTML =
    "<p>Regional research data bundle is unavailable.</p>";
  document.getElementById("regional-regime-panel").innerHTML =
    '<h3 id="regional-regime-title">Local forecast region</h3><p class="muted">Regional forecast region data are unavailable.</p>';
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

function regionalRiskFillColor(record) {
  if (!record) return "risk-unavailable";
  if (selectedRegionalForecastView() === "weekly") {
    return regionalRiskClass(record.risk_score);
  }
  return regionalAnnualIncidenceClass(record.predicted_annual_incidence_per_100k);
}

function regionalAnnualIncidenceClass(value) {
  const incidence = Number(value);
  if (!Number.isFinite(incidence)) return "risk-unavailable";
  if (incidence >= 200) return "risk-very-high";
  if (incidence >= 100) return "risk-high";
  if (incidence >= 50) return "risk-moderate";
  if (incidence >= 25) return "risk-low";
  return "risk-very-low";
}

function regionalObservedRiskClass(record) {
  if (!record) return "risk-unavailable";
  return regionalAnnualIncidenceClass(record.incidence_per_100k);
}

function renderRegionalLegend() {
  const legend = document.getElementById("regional-risk-legend");
  if (!legend) return;
  if (selectedRegionalForecastView() === "weekly") {
    legend.setAttribute("aria-label", "Weekly seasonal risk score legend");
    legend.innerHTML = `<span><b class="swatch risk-very-low"></b>1-2 very low</span>
      <span><b class="swatch risk-low"></b>3-4 low</span>
      <span><b class="swatch risk-moderate"></b>5-6 moderate</span>
      <span><b class="swatch risk-high"></b>7-8 high</span>
      <span><b class="swatch risk-very-high"></b>9-10 very high</span>`;
    return;
  }
  legend.setAttribute("aria-label", "Annual incidence per 100k legend");
  legend.innerHTML = `<span><b class="swatch risk-very-low"></b>&lt;25 per 100k</span>
    <span><b class="swatch risk-low"></b>25-49 per 100k</span>
    <span><b class="swatch risk-moderate"></b>50-99 per 100k</span>
    <span><b class="swatch risk-high"></b>100-199 per 100k</span>
    <span><b class="swatch risk-very-high"></b>200+ per 100k</span>`;
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

function regionalOptionalNumber(id) {
  const value = document.getElementById(id).value;
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function regionalOptionalBoolean(id) {
  const value = document.getElementById(id).value;
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
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
