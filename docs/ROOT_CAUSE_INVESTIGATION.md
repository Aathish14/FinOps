# Root Cause Investigation

## Cloud Cost Forecasting — Streamlit Application

**Repository:** `D:\FinOps`  
**Branch:** `master`  
**Deployment:** `https://finops-cloud-cost-forecast.streamlit.app/`  
**Entry point:** `cloud-cost-forecasting/app.py`  
**Investigation date:** 2026-10-18

---

## Executive Summary

This investigation identified and resolved timezone-handling defects in the Cloud Cost Forecasting Streamlit application. The root cause of all datetime-related failures was **inconsistent timezone normalization** across the data pipeline: user-uploaded CSV files may contain timezone-aware timestamps (e.g., `2026-04-07T00:00:00Z`), while Prophet and Plotly expect timezone-naive `datetime64[ns]` columns. Mixing timezone-aware and timezone-naive datetime columns in pandas merge operations raises `ValueError`, and passing timezone-aware datetimes to Prophet raises `ValueError: Column ds has timezone specified`.

Seven defensive `pd.to_datetime(..., utc=True).dt.tz_localize(None)` normalizations were added at every boundary where timezone-aware input could enter the pipeline or where two datetime columns are merged.

---

## Confirmed Issues

### TZ-1: Timezone-aware date at app-level preprocessing (`app.py:174`)

**Severity:** High  
**Status:** CONFIRMED — Fixed

**Root cause:** `pd.to_datetime(df['date'])` without `utc=True` preserves timezone metadata from CSV uploads. When user-uploaded CSVs contain ISO-8601 timestamps with timezone offsets (e.g., `2026-04-07T00:00:00Z`), the resulting `date` column is `datetime64[ns, UTC]`. This tz-aware column then flows through `daily_df.groupby('date')` and into `ProphetModel.fit()`, which rejects tz-aware `ds` columns.

**Fix:** `pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)` — converts to UTC, then strips timezone metadata while preserving timestamp instants.

### TZ-2: Timezone-aware date at ingestion layer (`ingestor.py:295,353`)

**Severity:** High  
**Status:** CONFIRMED — Fixed

**Root cause:** `ingest_aws_csv()` and `ingest_gcp_csv()` both call `pd.to_datetime(df['date'], errors='coerce')` without `utc=True`, preserving timezone metadata from CSV timestamps.

**Fix:** `pd.to_datetime(df['date'], utc=True, errors='coerce').dt.tz_localize(None)` — same UTC-then-strip pattern.

### TZ-3: Timezone mismatch at train-data merge (`app.py:~313`)

**Severity:** High  
**Status:** CONFIRMED — Fixed

**Root cause:** `train_with_pred.merge(train_predictions, on='date', how='inner')` merges `train_data['date']` (potentially tz-aware from CSV ingestion) with `train_predictions['date']` (tz-naive from Prophet's `make_future_dataframe()` via `predict_on_dates()`). Pandas raises `ValueError` on mixed timezone-awareness.

**Fix:** Added `train_with_pred['date'] = pd.to_datetime(train_with_pred['date'], utc=True).dt.tz_localize(None)` before the merge.

### TZ-4: Timezone mismatch at test-data merge (`app.py:~341`)

**Severity:** High  
**Status:** CONFIRMED — Fixed

**Root cause:** Same as TZ-3 but for test data: `test_with_pred.merge(test_predictions, on='date', how='inner')` merges tz-aware test dates with tz-naive predictions.

**Fix:** Added `test_with_pred['date'] = pd.to_datetime(test_with_pred['date'], utc=True).dt.tz_localize(None)` before the merge.

### TZ-5: Timezone-aware date in historical spending plot (`plots.py:72`)

**Severity:** Medium  
**Status:** CONFIRMED — Fixed

**Root cause:** `plot_historical_spending()` calls `df.groupby('date')['cost_usd'].sum()` on a potentially tz-aware `date` column. Plotly may render incorrectly or raise warnings when x-axis values have mixed timezone awareness.

**Fix:** Added `df = df.copy(); df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)` before grouping.

### TZ-6: Timezone-aware date in monthly trend chart (`plots.py:322`)

**Severity:** Medium  
**Status:** CONFIRMED — Fixed

**Root cause:** `create_monthly_trend_chart()` calls `pd.to_datetime(df_copy['date'])` without `utc=True`, then `.dt.to_period('M')`. Tz-aware periods can cause incorrect month boundaries or Plotly rendering issues.

**Fix:** `df_copy['date'] = pd.to_datetime(df_copy['date'], utc=True).dt.tz_localize(None)` before period extraction.

### TZ-7: Timezone-aware `ds` in Prophet `fit()` (`prophet_model.py:28`)

**Severity:** High  
**Status:** CONFIRMED — Fixed (previously)

**Root cause:** `Prophet.fit(df)` rejects tz-aware `ds` columns with `ValueError: Column ds has timezone specified`.

**Fix:** `df['ds'] = pd.to_datetime(df['ds'], utc=True).dt.tz_localize(None)` — already present from prior fix.

### TZ-8: Timezone-aware dates in `predict_on_dates()` (`prophet_model.py:67`)

**Severity:** High  
**Status:** CONFIRMED — Fixed (previously)

**Root cause:** `predict_on_dates()` constructs `pd.DataFrame({'ds': pd.to_datetime(dates['date'])})` without `utc=True`, preserving tz-awareness from caller-provided dates.

**Fix:** `pd.to_datetime(dates['date'], utc=True).dt.tz_localize(None)` — already present from prior fix.

### TZ-9: Timezone-aware `eval_df['date']` in `evaluate()` (`prophet_model.py:91`)

**Severity:** High  
**Status:** CONFIRMED — Fixed (previously)

**Root cause:** `evaluate()` calls `predict_on_dates(test_data[['date']])` where `test_data['date']` may be tz-aware, then merges with `predictions_df['date']` which is tz-naive.

**Fix:** `eval_df['date'] = pd.to_datetime(eval_df['date'], utc=True).dt.tz_localize(None)` — already present from prior fix.

---

## Hypotheses Under Investigation (Not Yet Confirmed)

### H-1: ASGI protocol mismatch (`Expected ASGI message 'http.response.start', but got 'http.response.body'`)

**Status:** UNCONFIRMED

**Evidence:** Production logs show `RuntimeError: Expected ASGI message 'http.response.start', but got 'http.response.body'` from Uvicorn/Starlette. This error occurs when Starlette sends `http.response.body` without first sending `http.response.start`.

**Possible causes (investigation pending):**
- Streamlit 1.53.0 / Starlette 0.35.1 / Uvicorn 0.27.0 version incompatibility under specific load patterns
- Client disconnect mid-request causing ASGI protocol violation
- Large file uploads causing request buffering issues
- Streamlit internal server middleware interaction

**No application-side ASGI code exists** in `app.py` or any module — the entire Stack is Streamlit's internal server. This is a framework-level issue outside application code control.

**Next step:** Monitor production logs for recurrence. If correlated with large file uploads, consider file size limits or chunked upload handling.

### H-2: MLflow datetime-conversion warning

**Status:** UNCONFIRMED

**Evidence:** No datetime-conversion warning found in `tracker.py` source. `mlflow.log_params()`, `mlflow.log_metrics()`, and `mlflow.log_artifact()` are called with string/numeric values only. `mlflow.sklearn.log_model()` is called but `AnomalyDetector` is a scikit-learn wrapper that may serialize datetime metadata internally.

**Possible cause:** `mlflow.sklearn.log_model()` may serialize the IsolationForest model with embedded datetime metadata, triggering protobuf/pandas datetime conversion warnings in certain versions.

**Next step:** Monitor MLflow logs for datetime conversion warnings during model logging.

---

## Issue Inventory Summary

| ID | Location | Issue | Severity | Status |
|----|----------|-------|----------|--------|
| TZ-1 | `app.py:174` | tz-aware date from CSV ingestion | High | CONFIRMED — Fixed |
| TZ-2 | `ingestor.py:295,353` | tz-aware date at ingestion | High | CONFIRMED — Fixed |
| TZ-3 | `app.py:~313` | Merge tz-aware train vs tz-naive predictions | High | CONFIRMED — Fixed |
| TZ-4 | `app.py:~341` | Merge tz-aware test vs tz-naive predictions | High | CONFIRMED — Fixed |
| TZ-5 | `plots.py:72` | tz-aware date in historical plot | Medium | CONFIRMED — Fixed |
| TZ-6 | `plots.py:322` | tz-aware date in monthly trend | Medium | CONFIRMED — Fixed |
| TZ-7 | `prophet_model.py:28` | tz-aware `ds` in Prophet.fit() | High | CONFIRMED — Fixed (prior) |
| TZ-8 | `prophet_model.py:67` | tz-aware dates in predict_on_dates() | High | CONFIRMED — Fixed (prior) |
| TZ-9 | `prophet_model.py:91` | tz-aware eval_df date in evaluate() | High | CONFIRMED — Fixed (prior) |
| H-1 | Streamlit server | ASGI protocol mismatch | Medium | UNCONFIRMED |
| H-2 | MLflow tracker | datetime-conversion warning | Low | UNCONFIRMED |

---

## Files Modified in This Investigation

| File | Change |
|------|--------|
| `cloud-cost-forecasting/app.py` | +9/-5: Normalize `df['date']` at ingestion; normalize train/test date columns before merges |
| `cloud-cost-forecasting/app/ingest/ingestor.py` | +4/-4: Normalize `df['date']` with `utc=True` in both `ingest_aws_csv()` and `ingest_gcp_csv()` |
| `cloud-cost-forecasting/app/visualization/plots.py` | +6/-2: Normalize dates in `plot_historical_spending()` and `create_monthly_trend_chart()` |
| `tests/test_pipeline.py` | +58/-0: Added 4 regression tests for timezone-aware evaluation |

---

## Related Documents

- `docs/RECOVERY_PLAN.md` — prioritized workstreams, implementation order, rollback plan
- `docs/RECOVERY_VERIFICATION.md` — exact commands, actual results, end-to-end test results
- `tests/test_pipeline.py` — regression tests for timezone-aware date handling