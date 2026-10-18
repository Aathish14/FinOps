# Recovery Plan — Cloud Cost Forecasting

**Repository:** `D:\FinOps`  
**Branch:** `master`  
**Target:** Restore correct, reliable, reproducible deployment of the FinOps Cloud Cost Forecasting Streamlit application  
**Date:** 2026-10-18

---

## 1. Root Causes and Affected Components

### Root Cause 1: Timezone-Inconsistent DateTime Handling

**Affected components:**
- `cloud-cost-forecasting/app.py` — date preprocessing at line 174, merge points at ~313 and ~341
- `cloud-cost-forecasting/app/ingest/ingestor.py` — AWS/GCP CSV ingestion at lines 295, 353
- `cloud-cost-forecasting/app/forecasting/prophet_model.py` — Prophet fit/predict/evaluate at lines 28, 67, 91
- `cloud-cost-forecasting/app/visualization/plots.py` — historical spend chart (line 72), monthly trend chart (line 322)

**Root cause:** `pd.to_datetime()` without `utc=True` preserves timezone metadata from CSV uploads. Prophet rejects tz-aware `ds` columns; pandas raises `ValueError` on mixed-awareness merges; Plotly may render tz-aware x-axes incorrectly.

**Fix applied:** `pd.to_datetime(series, utc=True).dt.tz_localize(None)` at every boundary where tz-aware input enters or where two datetime columns are merged. All 8 locations are now consistent.

---

## 2. Prioritized Workstreams

### Workstream A: Timezone Consistency (CRITICAL — COMPLETED)

**Changes:**
1. `app.py:174` — `pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)` at preprocessing
2. `app.py:~313` — Normalize `train_with_pred['date']` before train merge
3. `app.py:~341` — Normalize `test_with_pred['date']` before merge
4. `ingestor.py:295` — `pd.to_datetime(df['date'], utc=True, errors='coerce').dt.tz_localize(None)` in AWS ingestion
5. `ingestor.py:353` — Same in GCP ingestion
6. `prophet_model.py:28` — Normalize `df['ds']` before `Prophet.fit()` (prior fix)
7. `prophet_model.py:67` — Normalize `future_ds` in `predict_on_dates()` (prior fix)
8. `prophet_model.py:91` — Normalize `eval_df['date']` before merge in `evaluate()` (prior fix)
9. `plots.py:72` — Normalize `df['date']` in `plot_historical_spending()`
10. `plots.py:322` — Normalize `df_copy['date']` in `create_monthly_trend_chart()`

**Acceptance criteria:**
- All `pd.to_datetime()` calls use `utc=True`
- All `date` columns are `datetime64[ns]` (timezone-naive) before merging
- Prophet `fit()` and `predict_on_dates()` receive tz-naive `ds`
- All 51 tests pass (39 root + 12 app)

**Rollback:** Revert commit `4e14cb6` (timezone fix) and `ca324c2` (prior timezone fix)

---

### Workstream B: Test Coverage (CRITICAL — COMPLETED)

**Changes:**
- `tests/test_pipeline.py` — Added 4 regression tests:
  - `test_fit_with_timezone_aware_dates` — Prophet fits with tz-aware UTC dates
  - `test_fit_with_timezone_naive_dates` — Tz-naive dates still work (regression guard)
  - `test_fit_normalizes_ds_to_timezone_naive` — Mocks Prophet to verify `ds` is tz-naive when passed to `fit()`
  - `test_predict_on_dates_with_timezone_aware_dates` — `predict_on_dates()` normalizes tz-aware input
  - `test_evaluate_with_timezone_aware_test_dates` — Evaluation succeeds with tz-aware test dates
  - `test_evaluate_matches_correct_dates_after_normalization` — Matching dates remain matched after normalization
  - `test_evaluate_with_timezone_naive_test_dates` — Tz-naive evaluation still works

**Acceptance criteria:**
- All 4 new tests pass
- All existing 47 tests still pass (39 root + 12 app)
- Total: 51 tests pass

**Rollback:** Revert test additions to `tests/test_pipeline.py`

---

### Workstream C: Documentation (COMPLETED)

**Changes:**
- `docs/ROOT_CAUSE_INVESTIGATION.md` — Architecture, type-mismatch table, issue inventory, fix locations
- `docs/RECOVERY_PLAN.md` — This document: workstreams, acceptance criteria, rollback plan
- `docs/RECOVERY_VERIFICATION.md` — Verification commands, results, acceptance criteria (see below)

**Acceptance criteria:**
- All three documents exist and are internally consistent
- All references to moved/renamed files are accurate

---

### Workstream D: ASGI Protocol Error (UNCONFIRMED — MONITORING)

**Status:** Not reproducible locally. Error occurs in Streamlit's internal server (Starlette/Uvicorn), not application code.

**Next steps:**
- Monitor production logs at `https://finops-cloud-cost-forecast.streamlit.app/` for recurrence
- If correlated with large file uploads (>10MB), consider adding file size validation
- If correlated with specific user actions, capture full traceback

**Rollback:** Not applicable — no application code change required

---

### Workstream E: MLflow Datetime Warning (UNCONFIRMED — MONITORING)

**Status:** No datetime-conversion warning found in `tracker.py` source code. `mlflow.log_params()`, `mlflow.log_metrics()`, and `mlflow.log_artifact()` are called with string/numeric values only. `mlflow.sklearn.log_model()` may serialize datetime metadata internally.

**Next steps:**
- Monitor MLflow logs during model logging for datetime conversion warnings
- If warnings appear, investigate `mlflow.sklearn.log_model()` serialization of IsolationForest internals

**Rollback:** Not applicable — no application code change required

---

## 3. Dependencies and Execution Order

The workstreams are independent except:

1. **Workstream A** must be complete before **Workstream B** can validate the fix
2. **Workstream B** must pass before **Workstream D** and **E** can be meaningfully monitored
3. **Workstream C** is independent and can proceed in parallel

Execution order: A → B → C (with D and E monitored in parallel)

---

## 4. Risk Level and Rollback Strategy

| Risk | Level | Mitigation |
|------|-------|------------|
| Timezone normalization changes data semantics | Low | UTC conversion preserves timestamp instants; only strips timezone metadata |
| Prophet model behavior changes | Low | Prophet requires tz-naive `ds`; normalization is required for correct operation |
| Merge operations lose rows | Low | Inner join on normalized dates preserves all matching dates (verified by test `test_evaluate_matches_correct_dates_after_normalization`) |
| Plotting breaks with tz-naive dates | Low | Plotly handles tz-naive datetimes natively |

**Rollback procedure:**
```bash
git revert 4e14cb6  # Revert timezone fix
git revert ca324c2  # Revert prior timezone fix
git push origin master
```

---

## 5. Release Gates

Before deploying to production:

- [ ] All 51 tests pass (39 root + 12 app)
- [ ] `validate.ps1` exits with code 0
- [ ] `git diff --check` passes (no whitespace errors)
- [ ] End-to-end test with timezone-aware CSV completes successfully
- [ ] Commit pushed to `origin/master`
- [ ] Streamlit Cloud rebuild triggered automatically or via Reboot app
- [ ] Production smoke test: upload CSV, click "Run Analysis", verify no errors

---

## Documents Referenced

- `docs/ROOT_CAUSE_INVESTIGATION.md` — Detailed investigation findings
- `docs/RECOVERY_VERIFICATION.md` — Verification commands and results
- `tests/test_pipeline.py` — Regression test suite