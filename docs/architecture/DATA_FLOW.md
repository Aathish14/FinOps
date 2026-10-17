# Data Flow

This document describes the actual data flow through the FinOps Cloud Cost
Forecasting application, based on the implementation in
`cloud-cost-forecasting/app.py` and the modules under
`cloud-cost-forecasting/app/`.

## 1. Data Ingestion

**Source files:** `cloud-cost-forecasting/app/ingest/ingestor.py`

The application accepts AWS Cost & Usage Report (CUR) CSV files and GCP Billing
Export CSV files. Uploads arrive through Streamlit's `st.file_uploader` as
`UploadedFile` objects; sample data is loaded from `cloud-cost-forecasting/data/samples/`
as plain filesystem path strings.

The `normalize_file_inputs()` function performs defensive type discrimination:

| Input type | Detection | Handling |
|------------|-----------|----------|
| `UploadedFile` | `hasattr(f, "getbuffer")` | Buffer written to temp dir, path returned |
| `str` / `os.PathLike` | `isinstance(f, (str, os.PathLike))` | Path validated for existence, returned as-is |
| Other | Neither check matches | Dropped silently |

This prevents `AttributeError` when switching between `st.file_uploader` and
sample-data session state (plain `str` paths have no `.name` or `.getbuffer()`).

Ingested CSVs are mapped to a unified schema:

| Source column (AWS) | Source column (GCP) | Unified column |
|---------------------|---------------------|----------------|
| `bill/BillingPeriodStartDate` | `usage_start_time` | `date` |
| `lineItem/ProductCode` | `service.description` | `service_name` |
| `lineItem/UsageAccountId` | `project.id` | `account_id` |
| `lineItem/UsageAmount` | `usage.amount` | `usage_quantity` |
| `lineItem/UnblendedCost` | `cost` | `cost_usd` |
| `product/region` | — | `region` |

Additional columns added: `cloud_provider` (`AWS`/`GCP`), `environment` (`"unknown"`),
`usage_unit` (`"unknown"`).

## 2. Preprocessing

**Source file:** `cloud-cost-forecasting/app.py` (lines after ingestion)

- `date` column converted to `datetime64[ns]`
- Data sorted chronologically by `date`
- Quality validation: `cost_usd` checked for NaN and infinite values
- `usage_quantity` checked for NaN and infinite values (warnings only)

## 3. Forecasting

**Source file:** `cloud-cost-forecasting/app/forecasting/prophet_model.py`

Daily total spend is computed by grouping on `date` and summing `cost_usd`.
A chronological 80/20 train/test split is applied (first 80% for training,
last 20% for evaluation — no random shuffling, no data leakage).

Prophet is fitted on training data with user-configurable hyperparameters
from the Streamlit sidebar:

| Sidebar control | Prophet parameter | Default |
|-----------------|-------------------|---------|
| Forecast Horizon (days) | `periods` in `make_future_dataframe()` | 30 |
| Confidence Interval Width | `interval_width` | 0.95 |
| Seasonality Mode | `seasonality_mode` | `"additive"` |
| Weekly Seasonality | `weekly_seasonality` | `"auto"` |
| Yearly Seasonality | `yearly_seasonality` | `"auto"` |

Forecast output columns: `date`, `forecast_cost_usd`, `lower_bound_80`,
`upper_bound_80`.

Evaluation metrics computed on the holdout test set: MAPE, RMSE, MAE.

## 4. Anomaly Detection

**Source file:** `cloud-cost-forecasting/app/anomaly/isolation_forest.py`

Residuals are computed as `actual - predicted` on test-period dates only.
Features engineered from residuals: `residual`, `residual_lag1`,
`residual_rolling_mean_7`, `residual_rolling_std_7`.

Isolation Forest is fitted on training residuals only (no data leakage).
User-configurable hyperparameters from the sidebar:

| Sidebar control | sklearn parameter | Default |
|-----------------|-------------------|---------|
| Contamination | `contamination` | 0.05 |
| Number of Estimators | `n_estimators` | 100 |

Anomaly labels: `-1` (anomaly) / `1` (normal).

## 5. Cost-Impact Ranking

**Source file:** `cloud-cost-forecasting/app/anomaly/cost_aware.py`

Anomalies are ranked by a gated additive score:

```
score = norm_score + alpha * norm_excess_cost * confidence * gate
```

The gate activates only when anomaly evidence exceeds a threshold, preventing
high-cost normal days from dominating the ranking.

## 6. Explanations

**Source file:** `cloud-cost-forecasting/app/anomaly/explanations.py`

Deterministic, template-based explanations per anomaly. No SHAP or model
internals are used. Explanations include:
- Observed vs expected cost
- Excess amount and relative deviation
- Anomaly score and cost-impact score
- Priority rank

## 7. Experiment Tracking

**Source file:** `cloud-cost-forecasting/app/tracking/tracker.py`

MLflow logs parameters, metrics, and artifacts. Local SQLite backend
(`mlflow.db`) by default. `MLFLOW_TRACKING_URI` environment variable can
redirect to a managed tracking server.

## 8. Visualization

**Source file:** `cloud-cost-forecasting/app/visualization/plots.py`

Plotly charts render: historical spending, forecast with confidence intervals,
spending by service, monthly trend, and anomalies.

## Failure Modes

| Condition | Behavior |
|-----------|----------|
| `cost_usd` contains NaN | `st.error()`, `st.stop()` |
| `cost_usd` contains infinite values | `st.error()`, `st.stop()` |
| Fewer than 30 daily observations | `st.error()`, forecasting skipped |
| Forecast horizon exceeds 50% of history | `st.error()`, analysis stopped |
| Fewer than 10 training residuals | `st.error()`, anomaly detection skipped |
