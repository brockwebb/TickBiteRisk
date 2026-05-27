# Maryland Weather Acquisition Design

Date: 2026-05-24

## Purpose

Build the weather data subsystem for the Maryland tick risk model. This subsystem creates reproducible daily weather records, primary ISO-week weather features, and slower monthly/seasonal context features for every Maryland county and Baltimore City.

Weather is a predictive input, not the product by itself. It feeds the Maryland 1-10 tick risk score together with disease history, vector status, habitat, host ecology, and source reconciliation.

## Scope

In scope:

- Daily weather backfill for Maryland jurisdictions.
- County/jurisdiction centroid-based pulls.
- NOAA CDO/GHCND as the primary observed historical source.
- Open-Meteo historical archive as a secondary comparison or gap-fill source.
- Derived ISO-week features for tick activity modeling, with monthly and seasonal context features retained.
- Provenance tracking for every weather pull.
- No credentials stored in code, docs, data files, or git history.

Out of scope for this subsystem:

- Frontend display.
- Final risk model coefficients.
- Real-time public API.
- Station-level interpolation beyond county centroid checks.
- Paid/commercial weather APIs.

## Source Strategy

### Primary: Open-Meteo Historical Weather API

Use Open-Meteo for the first complete Maryland backfill because it is coordinate-based, free for non-commercial use, does not require an API key, and avoids station matching.

Endpoint:

```text
https://archive-api.open-meteo.com/v1/archive
```

Initial backfill range:

```text
2000-01-01 through 2024-12-31
```

This range aligns with the strongest Maryland county Lyme source files already downloaded locally.

Model preference:

- Use a consistent historical reanalysis model for long-run features.
- Prefer `ERA5-Land` or the Open-Meteo archive default only after documenting the selected model in source metadata.
- Do not mix historical weather models inside the same feature table without a `weather_model` field.

### Validation: NOAA CDO

NOAA CDO is available as a validation branch because a local token can be provided through the environment.

Credential rule:

```text
NOAA_TOKEN
```

The token must only be read from the local environment. It must never be committed, written to `.env` in the repository, embedded in command examples, or logged.

Use NOAA CDO to validate Open-Meteo against selected Maryland stations, not as the first full historical backfill path. NOAA CDO requires station selection and has token/rate-limit constraints, so it is a better quality-check branch than a first-pass county product feed.

## Geography

Create one weather location per Maryland jurisdiction:

- 23 counties.
- Baltimore City.

Each location needs:

- `county_fips`
- `county_name`
- `centroid_lat`
- `centroid_lon`
- `state`
- `state_fips`
- `geography_source`

County centroids should come from a Census/TIGER-derived geometry source or the local Lyme county geodata file if it is sufficient. The centroid generation method must be recorded because coastal counties and Baltimore City may be sensitive to centroid placement.

## Raw Daily Variables

Pull daily values that directly support tick activity, survival, and host/habitat moisture features:

- `temperature_2m_mean`
- `temperature_2m_max`
- `temperature_2m_min`
- `relative_humidity_2m_mean`
- `relative_humidity_2m_max`
- `relative_humidity_2m_min`
- `dew_point_2m_mean`
- `precipitation_sum`
- `rain_sum`
- `snowfall_sum`
- `precipitation_hours`
- `soil_temperature_0_to_7cm_mean`
- `soil_moisture_0_to_7cm_mean`
- `et0_fao_evapotranspiration`
- `wind_speed_10m_mean`
- `wind_speed_10m_max`

Store temperature in Fahrenheit for product-facing features and keep source units in metadata. Store precipitation in millimeters unless a later schema standard changes it globally.

## Tables

### `weather_locations`

```text
id
county_fips
county_name
state
state_fips
centroid_lat
centroid_lon
geography_source
created_at
```

### `weather_daily`

```text
county_fips
date
source
weather_model
temp_mean_f
temp_max_f
temp_min_f
humidity_mean_pct
humidity_max_pct
humidity_min_pct
dew_point_mean_f
precipitation_mm
rain_mm
snowfall_mm
precipitation_hours
soil_temp_0_7cm_f
soil_moisture_0_7cm
evapotranspiration_mm
wind_mean_mph
wind_max_mph
source_url_hash
ingested_at
```

Primary key:

```text
county_fips, date, source, weather_model
```

### `weather_features_weekly`

Primary weather modeling grain. Uses ISO week numbering.

```text
county_fips
iso_year
iso_week
week_start_date
week_end_date
source
weather_model
days_observed
expected_days
week_complete
days_above_40f
days_50_65f
days_70_85f
degree_days_above_40f
freeze_thaw_days
precip_total_mm
rain_total_mm
snowfall_total_mm
precip_days
dry_spell_max_days
humidity_days_above_85pct
soil_moisture_mean
soil_temp_above_40f_days
evapotranspiration_total_mm
temp_anomaly_vs_10yr
precip_anomaly_vs_10yr
humidity_anomaly_vs_10yr
created_at
```

### `weather_features_monthly`

Secondary slower-context feature grain.

```text
county_fips
year
month
source
weather_model
days_observed
expected_days
month_complete
days_above_40f
days_50_65f
days_70_85f
degree_days_above_40f
freeze_thaw_days
precip_total_mm
rain_total_mm
snowfall_total_mm
precip_days
dry_spell_max_days
humidity_days_above_85pct
soil_moisture_mean
soil_temp_above_40f_days
evapotranspiration_total_mm
temp_anomaly_vs_10yr
precip_anomaly_vs_10yr
humidity_anomaly_vs_10yr
created_at
```

### `weather_features_seasonal`

```text
county_fips
year
season
source
weather_model
warmup_start_date
spring_degree_days_above_40f
spring_ideal_tick_temp_days
spring_humidity_days_above_85pct
winter_freeze_thaw_days
winter_min_temp_mean_f
summer_hot_dry_stress_days
fall_reactivation_days
created_at
```

Seasons for v0.1:

- `winter`: December through February, assigned to the year containing January.
- `spring`: March through May.
- `summer`: June through August.
- `fall`: September through November.

## Derived Feature Definitions

Use explicit, testable definitions:

- `days_above_40f`: count of days where `temp_max_f >= 40`.
- `days_50_65f`: count of days where `temp_mean_f` is between 50 and 65 inclusive.
- `days_70_85f`: count of days where `temp_mean_f` is between 70 and 85 inclusive.
- `degree_days_above_40f`: sum of `max(temp_mean_f - 40, 0)`.
- `freeze_thaw_days`: count of days with `temp_min_f < 32` and `temp_max_f > 32`.
- `precip_days`: count of days with `precipitation_mm > 0`.
- `dry_spell_max_days`: longest consecutive run of days with `precipitation_mm = 0`.
- `humidity_days_above_85pct`: count of days where `humidity_mean_pct >= 85`.
- `soil_temp_above_40f_days`: count of days where `soil_temp_0_7cm_f >= 40`.
- `hot_dry_stress_days`: count of days where `temp_max_f >= 90` and `humidity_mean_pct < 55`.

Anomaly features compare a county ISO week or county-month to the trailing 10-year average for the same county and period. For backtests, anomaly baselines must use only years available before the prediction year.

## Backtest Rules

Weather features must support two modes:

### Reconstruction Mode

Use full observed weather for a historical year to explain observed disease outcomes.

Example:

```text
Use 2019 observed weather to explain 2019 reported Lyme counts.
```

### Forecast Mode

Use only information that would have been available at prediction time.

Example:

```text
For a 2020 annual forecast made before spring, use prior-year disease history, habitat, host ecology, and climate normals.
For a mid-season 2020 update, use current-season-to-date weather plus historical seasonal expectations.
```

The backtest harness must label which mode it is using.

## Error Handling

Open-Meteo ingestion should:

- Retry transient HTTP failures with bounded exponential backoff.
- Save partial progress by county and year.
- Record failed county/year pulls in an ingest log.
- Refuse to silently fill missing weather days.
- Flag missing days in quality checks.

NOAA CDO validation should:

- Fail fast if `NOAA_TOKEN` is missing.
- Never print the token.
- Respect NOAA rate limits.
- Store station metadata separately from county daily weather.

## Testing

Required tests:

- Weather location records include exactly 24 Maryland jurisdictions.
- Open-Meteo URL construction includes required variables and date range.
- Daily response parsing preserves county/date/source/model keys.
- Monthly feature calculations match hand-computed fixtures.
- Dry-spell and freeze-thaw calculations handle month boundaries correctly.
- Anomaly calculations avoid future-year leakage in backtest mode.
- NOAA validation code errors clearly when `NOAA_TOKEN` is absent.
- No test requires live network access.

## Acceptance Criteria

- A local command can backfill Maryland daily Open-Meteo weather for a small fixture date range.
- A model-ready weekly feature table can be generated from daily fixture data.
- A full-run plan exists for 2000-2024 Maryland weather without exceeding normal public API limits.
- NOAA CDO token use is environment-only and secret-safe.
- Weather features can be joined to Maryland county-year Lyme outcomes by `county_fips`, `year`, and month/season rollups.

## References

- Open-Meteo Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- NOAA CDO API documentation: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
- Existing local API MVP design: `docs/superpowers/specs/2026-05-23-local-api-mvp-design.md`
