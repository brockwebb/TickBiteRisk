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
    .getElementById("forecast-view-select")
    .addEventListener("change", handleForecastViewChange);
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
  const select = document.getElementById("forecast-view-select");
  const label = document.getElementById("forecast-view-label");
  const mode = selectedRegionalDataMode();
  const hasForecast = regionalForecastRecordsForSelectedYear().length > 0;
  const weeklyAvailable = hasForecast && isLatestRegionalForecastYear();
  if (!weeklyAvailable && regionalState.forecastView === "weekly") {
    regionalState.forecastView = "annual";
  }
  const view = selectedRegionalForecastView();
  select.value = view === "weekly" ? "weekly" : "annual";
  select.disabled = !weeklyAvailable;
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
  renderRegionalLegend();
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
  const badgeClass = countyMode === "forecast"
    ? forecastView === "weekly" && record
      ? regionalRiskClass(record.risk_score)
      : regionalAnnualIncidenceClass(annualSummary.predictedAnnualIncidence)
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
  renderRegionalForecastChart(countyFips);
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
    renderRegionalObservedHistoryChart(countyFips);
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
  renderRegionalAnnualForecastChart(countyFips, summary);
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
    ${renderRegionalForecastCheck(metadata)}
    ${renderRegionalProtocolNote(annualRecord.year)}
    ${renderRegionalHistoricalRegimeNotice()}
    ${renderRegionalFlagCaveats(annualRecord)}
    <p class="disclaimer">Reported cases are not stable true incidence. This historical layer is informational only, not medical advice, and not a forecast-safe feature for the selected year.</p>
  </div>`;
  renderRegionalRegime(metadata);
  renderRegionalObservedHistoryChart(countyFips);
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
  summary.textContent = `${countyName} weekly forecast, MMWR weeks ${minWeek}-${maxWeek}. The green line is the predicted weekly Lyme incidence. The blue bands show the forecast interval. The red dot marks the selected week ${activeRecord.mmwr_week}, with a 95% empirical interval of ${regionalFormatNumber(activeInterval[0])} to ${regionalFormatNumber(activeInterval[1])} per 100k.`;
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
