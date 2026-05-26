const state = {
  weekly: null,
  counties: null,
  modelCard: null,
  sourceCatalog: null,
  selectedCounty: "24003",
  selectedWeek: 1,
  byCountyWeek: new Map(),
};

const dataPaths = {
  weekly: "data/md_county_risk_weekly.json",
  counties: "data/md_counties.geojson",
  modelCard: "data/model_card.json",
  sourceCatalog: "data/source_catalog.json",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setDefaultDate();
  document.getElementById("date-input").addEventListener("change", handleDateChange);

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
}

function mmwrYearWeek(dateString) {
  const date = new Date(`${dateString}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return [new Date().getUTCFullYear(), 1];
  }

  const day = date.getUTCDay();
  const sunday = new Date(date);
  sunday.setUTCDate(date.getUTCDate() - day);

  const thursday = new Date(sunday);
  thursday.setUTCDate(sunday.getUTCDate() + 4);
  const mmwrYear = thursday.getUTCFullYear();

  const jan4 = new Date(Date.UTC(mmwrYear, 0, 4, 12));
  const firstSunday = new Date(jan4);
  firstSunday.setUTCDate(jan4.getUTCDate() - jan4.getUTCDay());
  const millisecondsPerWeek = 7 * 24 * 60 * 60 * 1000;
  const week = Math.floor((sunday - firstSunday) / millisecondsPerWeek) + 1;

  return [mmwrYear, week];
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

  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Maryland counties colored by relative Lyme seasonal baseline">${paths}</svg>`;
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
    : `${props.county_name}, no baseline available`;

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
    <span class="score-badge ${badgeClass}">${score}/10</span>
  </button>`;
}

function selectCounty(countyFips) {
  state.selectedCounty = countyFips;
  const record = getRecord(countyFips);
  const feature = findCountyFeature(countyFips);
  const countyName = feature ? feature.properties.county_name : countyFips;
  const panel = document.getElementById("panel-content");

  if (!record) {
    panel.innerHTML = `<p>No baseline row available for ${escapeHtml(countyName)} in MMWR week ${state.selectedWeek}.</p>`;
    updateSelectedControls();
    return;
  }

  const interval95 = record.predicted_weekly_incidence_95_interval || [0, 0];
  panel.innerHTML = `<div class="score-card">
    <p class="muted">MMWR week ${record.mmwr_week}, data year ${record.data_year}</p>
    <h3>${escapeHtml(record.county_name)}</h3>
    <p><span class="score-badge ${riskClass(record.risk_score)}">${record.risk_score}/10</span> ${escapeHtml(categoryLabel(record.risk_category))}</p>
    <p>${escapeHtml(sentenceCase(record.risk_category))} relative seasonal baseline for Lyme reports in Maryland counties like this one during this week.</p>
    <p>Predicted weekly incidence: ${formatNumber(record.predicted_weekly_incidence_per_100k)} per 100k.</p>
    <p>95% empirical interval: ${formatNumber(interval95[0])} to ${formatNumber(interval95[1])} per 100k.</p>
    <p class="disclaimer">This is not a personal infection probability or medical advice.</p>
  </div>`;
  updateSelectedControls();
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
  const links = guidanceLinks
    .map((link) => `<li><a href="${escapeAttribute(link.url)}">${escapeHtml(link.title)}</a></li>`)
    .join("");
  const sources = sourceRows
    .map((source) => `<li>${escapeHtml(source.source_id)}: ${escapeHtml(source.notes || source.artifact_type)}</li>`)
    .join("");

  target.innerHTML = `<p>${escapeHtml(state.modelCard.score_interpretation)}</p>
    <ul>${links}</ul>
    ${sources ? `<ul>${sources}</ul>` : ""}
    <p>Source branch: ${escapeHtml(state.weekly.model_name)} / ${escapeHtml(state.weekly.seasonality_source_id)}</p>`;
}

function renderLoadError(error) {
  document.getElementById("risk-map").innerHTML = `<p role="alert">${escapeHtml(error.message)}</p>`;
  document.getElementById("county-list").innerHTML = "";
  document.getElementById("panel-content").innerHTML = "<p>Dashboard data bundle is unavailable.</p>";
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

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
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
