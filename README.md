# ** THIS IS A NEW PROJECT AND BEING BUILT OUT** June 8, 2025
# tickbiterisk

> **Root file** – this README lives at repo root, not in `/docs`.  All lowercase filename per project convention.

---

## mission

Estimate and communicate **per‑bite Lyme‑disease risk** for any U.S. county using open federal data and a transparent Bayesian model.  Built for hikers, scouts, clinicians, and data‑science learners—100 % open source.

This project ships as self-hosted code; we do not currently provide a public API.

## current build status

The active implementation is a Maryland-first ETL and modeling prototype. The current code focuses on source manifest parsing, Maryland Lyme county-year reconciliation, tick/vector status normalization, and a Postgres-ready warehouse schema. The API endpoint described below is roadmap behavior until the model-ready warehouse tables are built.

## quick start (docker)

```bash
# clone repository
git clone https://github.com/yourhandle/tickbiterisk.git
cd tickbiterisk

# spin up database, model fit, and API
docker compose up -d            # first run takes ~10 min for MCMC

# query risk (Anne Arundel, MD; 24‑h attachment)
curl 'http://localhost:8000/risk?fips=24003&tau=24'
```

Returns JSON:

```jsonc
{"risk": [0.022], "ci95": [[0.011, 0.041]], ...}
```

## quick start (python)

```bash
pipx install tickbiterisk        # pulls PyPI wheel
export TICKRISK_DB=~/tickrisk.db # SQLite mode for demos
tickbiterisk init-data           # fetches mini sample set
tickbiterisk runserver           # http://127.0.0.1:8000
```

## data sources

| feed                                             | cadence | licence          |
| ------------------------------------------------ | ------- | ---------------- |
| CDC Tick Surveillance CSV                        | annual  | US public domain |
| FARS deer collisions                             | annual  | US public domain |
| NSSP ED tick‑bite index                          | weekly  | US public domain |
| NLCD land‑cover                                  | static  | US public domain |
| ACS population                                   | annual  | US public domain |
| CAPC dog serology\*                              | monthly | CC‑BY‑NC 4.0     |
| \*CAPC not redistributed; fetch script provided. |         |                  |

Full details: [`/docs/data-sources.md`](docs/data-sources.md)

## maryland weather ETL

The Maryland weather ETL has two acquisition paths: NOAA CDO/GHCND for observed station history, and Open-Meteo as a secondary reanalysis/gap-fill source using Census Gazetteer county internal points. The planned NOAA backfill range is 1992-01-01 through the current year.

```bash
tickbiterisk etl weather-locations --output-dir build/etl
tickbiterisk etl weather-backfill-open-meteo --county-fips 24003 --start-date 2020-01-01 --end-date 2020-01-03 --output-dir build/etl/weather-smoke
tickbiterisk etl noaa-stations --county-fips 24003 --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa
tickbiterisk etl noaa-daily --county-fips 24003 --station-id GHCND:USW00093721 --start-date 1992-05-01 --end-date 1992-05-07 --output-dir build/etl/noaa
tickbiterisk etl noaa-backfill-county --county-fips 24003 --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa
tickbiterisk etl noaa-audit-stations --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa-station-audit
tickbiterisk etl noaa-backfill-maryland --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa --county-fips 24003 --dry-run
tickbiterisk etl noaa-backfill-maryland --start-date 1992-01-01 --end-date 2026-05-24 --output-dir build/etl/noaa  # planned full run after smoke checks
```

NOAA CDO/GHCND is the primary observed historical weather source and reads `NOAA_TOKEN` from the environment. `noaa-audit-stations` checks station metadata before a large daily pull; on 2026-05-24, the strict 1992-current internal-station audit found 11 of 24 Maryland jurisdictions ready and 13 needing fallback station logic. `noaa-backfill-county` discovers county stations, selects long-coverage stations, and writes raw station plus daily observation CSVs with append/dedupe semantics. `noaa-backfill-maryland` loops that same county runner across all Maryland jurisdictions, or a repeated `--county-fips` subset for smoke runs. NOAA daily pulls are split into calendar-year windows and paginated, but daily station observations are still raw input; modeling uses weekly, monthly, and seasonal aggregates. Open-Meteo does not require an API key and remains a secondary reanalysis/gap-fill path.

## api summary

* `GET /risk?fips=24003&tau=24` – one attachment duration
* `GET /risk?fips=24003&tau=12&tau=36&k=2` – multiple τ, two ticks
  See [`/api/api-spec.md`](api/api-spec.md).

## contribute

1. Fork → create feature branch → commit tests.
2. Run `pre-commit run --all-files`.
3. Open PR; CI must pass lint, unit, and mini‑model tests.

Good first issues are labelled **`help wanted`**.

## licence

* **Code:** MIT (see `LICENSE`).
* **Derived data:** CC‑BY 4.0.
* **Third‑party feeds:** retain their original public‑domain or CC terms.

## cite

```
@software{tickbiterisk,
  title = {TickBiteRisk: Bayesian per-bite Lyme-risk engine},
  author = {Webb, Brock and Contributors},
  year   = 2025,
  url    = {https://github.com/yourhandle/tickbiterisk},
  doi    = {10.5281/zenodo.xxxxxxx}
}
```

(Manuscript: *arXiv:2506.xxxxx*).

## ai-generated assistance

Large‑language‑model tools (OpenAI GPT‑4o, June 2025) were used to accelerate code scaffolding, literature search, and first‑draft text suggestions. All AI outputs were reviewed and revised by the human authors, who take full responsibility for the final content.

## disclaimer

This project offers **informational estimates only** and is **not medical advice**.  Users should consult a healthcare professional for diagnosis or treatment decisions.

---

*Logo & badge graphics forthcoming.*
