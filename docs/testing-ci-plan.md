# TickBiteRisk – Testing & CI Plan

> **File location:** `/docs/testing-ci-plan.md`

---

## 1 Testing philosophy

* **Fail fast locally**: lint + type‑check on every pre‑commit.
* **Fast unit tests in CI** (<60 s) ensure PRs never break core logic.
* **Nightly integration run** fits a miniature model (2 counties, 4 weeks) to catch stochastic regressions.
* **Weekly full‑fit workflow** reproduces the entire pipeline on GitHub-hosted runners and archives artefacts.

---

## 2 Test tiers

| Tier                 | Scope                                                                               | Dataset                                  | Trigger                 | Expected runtime                           |
| -------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------- | ----------------------- | ------------------------------------------ |
| **Lint & static**    | Ruff (`flake8`, `isort`, `pydocstyle` rules) + MyPy type check                      | N/A                                      | Pre‑commit & every push | <10 s                                      |
| **Unit**             | Pure‑function tests: p(τ) logistic, FIPS validator, CAR adjacency builder           | Synthetic fixtures in `/tests/fixtures/` | Push & PR               | <30 s                                      |
| **Mini‑model**       | End‑to‑end ETL → PyMC fit on 2 counties (MD‑24003, CT‑09001) and 4 weeks of ED data | `tests/sample_data/` (6 KB)              | Nightly cron            | \~2 min                                    |
| **Full integration** | Complete annual + weekly workflow on latest datasets                                | Live fetch                               | Weekly Sunday           | \~15 min (runs on ‘ubuntu‑latest‑2xlarge’) |

All tests executed with `pytest -q` inside the repo’s Docker image to ensure parity with production.

---

## 3 GitHub Actions matrix

### 3.1 `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .[dev]
      - run: ruff check . && mypy app/
      - run: pytest -q tests/unit
```

### 3.2 `.github/workflows/nightly.yml`

Runs `make test-mini` at 02:00 UTC each night; uploads `mini_fit.nc` as artefact.

### 3.3 `.github/workflows/weekly.yml`

*Matrix* build (Python 3.11/3.12) + full ETL/fitting.  Artefacts: DB dump, NetCDF, OpenAPI JSON, Docker image push.

---

## 4 Mock & fixture strategy

* **`conftest.py`** creates an in‑memory SQLite clone with `theta_input` and `lambda_input` subset tables.
* Synthetic tick‑testing rows generated via NumPy’s binomial to stress low‑`nᵢ` cases.

---

## 5 Quality gates

| Gate                      | Required for merge into `main`   |
| ------------------------- | -------------------------------- |
| Lint + type‑check pass    | ✅                                |
| Unit tests pass           | ✅                                |
| Coverage ≥ 85 % lines     | ✅ (`pytest --cov`)               |
| OpenAPI schema diff clean | ✅ (bundled `schemathesis` check) |

Coverage enforcement via `fail_under = 85` in `pyproject.toml`.

---

*Last updated: 2025-06-08 (draft v0.1)*
