# ADR-0001: Project Structure

## Status

Proposed

## Context

The FinOps repository had accumulated duplicated configuration files,
scattered research reports, and test files in multiple locations without a
clear ownership model. The repository needed a clean, maintainable structure
that separates production code, tests, research, documentation, and tooling
while preserving the working Streamlit deployment.

## Decision

Adopt the following structure:

```
FinOps/
├── .github/workflows/ci.yml          # CI: test on push/PR
├── .editorconfig                     # Editor consistency
├── .gitignore                        # Ignore generated/local state
├── CONTRIBUTING.md                   # Contribution guide
├── CHANGELOG.md                      # Changelog from git history
├── LICENSE                           # (to be added by repo owner)
├── README.md                         # Main project entry point
├── requirements.txt                  # Canonical dependencies (root)
├── runtime.txt                       # Python version pin (root)
├── .streamlit/config.toml            # Streamlit config (root)
├── cloud-cost-forecasting/           # Deployable Streamlit application
│   ├── app.py                        # Entrypoint (unchanged path)
│   ├── requirements.txt              # App-specific dependencies
│   ├── runtime.txt                   # Python version pin
│   ├── .streamlit/config.toml        # Streamlit config
│   ├── app/                          # Production Python package
│   ├── data/samples/                 # Sample billing CSVs
│   └── tests/                        # App-specific tests (12 tests)
├── tests/                            # Shared integration/regression tests
├── docs/
│   ├── architecture/                 # Architecture docs
│   ├── research/                     # Research reports (moved from root)
│   └── ML_METHODOLOGY.md, ...
├── experiments/                      # Research source code and outputs
├── scripts/                          # PowerShell tooling
```

## Rationale

1. **Entrypoint preserved at `cloud-cost-forecasting/app.py`** — No change to the
   deployed application path. Streamlit Cloud deploys from this path.

2. **Duplicate configuration files retained** — `requirements.txt`, `runtime.txt`,
   and `.streamlit/config.toml` exist at both root and `cloud-cost-forecasting/`
   because Streamlit Cloud searches the entrypoint directory first, then the root.
   Both copies are logically identical. Removing either could break deployment
   if the platform changes its search order.

3. **Research reports under `docs/research/`** — 14 research report markdown
   files were moved from the repository root to `docs/research/` to group
   research documentation together. README.md links were updated accordingly.

4. **Architecture doc under `docs/architecture/`** — `docs/ARCHITECTURE.md`
   moved to `docs/architecture/ARCHITECTURE.md` to group architecture
   documentation together.

5. **Experiment files NOT deduplicated** — `experiments/anomaly/cost_aware.py`
   and `experiments/anomaly/explanations.py` are byte-identical to
   `cloud-cost-forecasting/app/anomaly/cost_aware.py` and
   `cloud-cost-forecasting/app/anomaly/explanations.py`, but they are NOT
   standalone duplicates. `experiments/run_experiments.py` imports
   `from experiments.anomaly.cost_aware import run_cost_aware_comparison`,
   so the experiment files serve a distinct import path and purpose. They are
   preserved as-is.

6. **Two test directories retained** — Root `tests/` (shared integration and
   regression tests) and `cloud-cost-forecasting/tests/` (app-specific tests)
   serve different scopes. Both are run by CI. The existing
   `cloud-cost-forecasting/tests/run_tests.ps1` is not duplicated; a root-level
   `scripts/run-tests.ps1` delegates to both.

7. **`.gitignore` updated** — Added `streamlit*.out`, `streamlit*.err`,
   `tree.d`, `tree.md`, `current-tree.txt`, `*.zip` to ignore generated
   artifacts that were previously untracked noise.

## Consequences

### Positive

- Clear separation of concerns: production, tests, research, docs, tooling
- Research reports grouped under `docs/research/`
- Architecture docs grouped under `docs/architecture/`
- CI workflow provides automated testing on push/PR
- Validation script provides local pre-commit checks

### Negative

- README.md links updated for moved files; any external links to old paths
  will break
- Duplicate `requirements.txt`/`runtime.txt`/`.streamlit/config.toml` files
  remain (justified by deployment search order)

### Risks

- None identified. All moves are file relocations with updated references.
- Production code (`cloud-cost-forecasting/app.py` and modules) is unchanged.
- Research artifacts (datasets, ground truth, experiment outputs) are preserved
  without modification.

## Reviewers

None yet.

## References

- Streamlit Cloud app dependencies documentation
- Streamlit Cloud deploy documentation (Python version via UI Advanced settings)
