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

The Maryland weather ETL derives county daily weather from the Open-Meteo historical archive using Census Gazetteer county internal points as stable query locations. The planned full backfill range is 2000-01-01 through 2024-12-31.

```bash
tickbiterisk etl weather-locations --output-dir build/etl
tickbiterisk etl weather-backfill-open-meteo --county-fips 24003 --start-date 2020-01-01 --end-date 2020-01-03 --output-dir build/etl/weather-smoke
```

Open-Meteo does not require an API key for the historical archive path. NOAA CDO is validation-only; the ETL validates `NOAA_TOKEN` from the environment and never reads tokens from files or CLI arguments.

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
