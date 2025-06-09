# contributing to tickbiterisk

Thank you for considering a contribution!  We welcome pull‑requests, issues, and discussion threads from **first‑timers through domain experts**.  This file explains the ground rules.

---

## 1 getting started

1. **Fork** the repo → `git clone` your fork.
2. Create a feature branch: `git checkout -b feat/short-topic`.
3. Install dev deps: `pip install -e .[dev]` (requires Python ≥3.11).
4. Pre‑commit hooks: `pre-commit install` (runs lint & type‑check before every commit).

---

## 2 coding guidelines

| Topic    | Rule                                                                    |
| -------- | ----------------------------------------------------------------------- |
| Language | Python 3.11+ only.                                                      |
| Style    | `black` formatter, `ruff` linter.  Run automatically by pre‑commit.     |
| Types    | All new functions must have type hints.  `mypy` strict mode enforced.   |
| Tests    | Add `pytest` unit tests for any new logic; target coverage ≥85 % lines. |
| Commits  | Present‑tense, <72 chars summary.  Squash on merge.                     |

### commit sign‑off (DCO)

By committing, you certify you wrote the code or have the right to license it under MIT.  Use the `-s` flag or set `git config --global commit.gpgsign false` and include:

```
Signed-off-by: Your Name <email@example.com>
```

---

## 3 pull‑request checklist

* [ ] Lint passes: `ruff check .`
* [ ] Type‑check passes: `mypy app/`
* [ ] `pytest -q` green (unit + mini‑model)
* [ ] Added/updated docs if behaviour changes
* [ ] Linked issue or explained motivation in PR description

CI will run lint + unit tests on every PR.  The nightly and weekly workflows will pick up deeper integration tests after merge.

---

## 4 reporting bugs / feature requests

1. Check open issues first.
2. File a new issue using the template; include:

   * OS and Python version
   * Exact Docker tag or git SHA
   * Steps to reproduce
3. Tag severity (`bug`, `enhancement`, `docs`).

---

## 5 code of conduct

We follow the [Contributor Covenant v2.1](code_of_conduct.md).  By participating you agree to abide by its terms.

---

## 6 good first issues

Issues labelled **`good first issue`** or **`help wanted`** are ideal for newcomers—often docs, small bug fixes, or adding county-level tests.

---

## 7 contact

Questions?  Open a GitHub Discussion or ping `@yourhandle`.

Happy coding!  🎉
