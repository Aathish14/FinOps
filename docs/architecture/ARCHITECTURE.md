# FinOps Architecture

## System Overview

FinOps is a modular, multi-cloud FinOps analytics platform built as a pipeline:

```
AWS CUR / GCP Billing Export
         │
         ▼
    ┌─────────────────┐
    │ Data Ingestion  │  (AWS CUR / GCP Billing Export → Unified Schema)
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │  Preprocessing  │  (chronological sort, type coercion, validation)
    └────────┬────────┘
             ▼
    ┌───────────────────────┐
    │  Forecasting Engine   │  Prophet, 80% CI, 7-30 day horizon
    │  (Prophet)            │  Rolling-origin evaluation (12 folds)
    └───────────┬───────────┘
                ▼
    ┌──────────────────────────┐
    │  Anomaly Detection       │  Isolation Forest on test-period residuals
    │  (Isolation Forest)      │  Features: residual, lag-1, rolling 7-day μ/σ
    └───────────┬──────────────┘
                ▼
    ┌──────────────────────────────────┐
    │  Cost-Impact Ranking             │  Gated additive: score + α·excess·conf·gate
    │  (CostImpactScorer)              │  Gate prevents high-cost normals from dominating
    └─────────────┬────────────────────┘
                  ▼
    ┌────────────────────────┐
    │  Explanation Layer     │  Deterministic, template-based explanations
    │  (AnomalyExplainer)    │  Observed vs Expected, excess, rank, severity
    └───────────┬────────────┘
                ▼
    ┌──────────────────────┐
    │  Streamlit Dashboard │  Forecasts, anomalies, rankings, explanations
    └───────────┬──────────┘
                ▼
    ┌──────────────────────┐
    │  MLflow Tracking     │  Params, metrics, artifacts, rankings
    └──────────────────────┘
```

---

## Module Responsibilities

### `cloud-cost-forecasting/app/ingest/`
| Module | Responsibility |
|--------|----------------|
| `ingestor.py` | AWS CUR / GCP Billing Export → unified schema |
| `schema.py` | Unified schema definition (`date, cloud_provider, service_name, account_id, region, environment, usage_quantity, usage_unit, cost_usd`) |
| `__init__.py` | Package exports |

**Input formats:**
- AWS CUR: `bill/BillingPeriodStartDate`, `lineItem/ProductCode`, `lineItem/UsageAccountId`, `lineItem/UsageAmount`, `lineItem/UnblendedCost`, `product/region`
- GCP Billing Export: `usage_start_time`, `service.description`, `project.id`, `cost`, `usage.amount`, `usage.unit`

**Output:** Normalized DataFrame with columns: `date, cloud_provider, service_name, account_id, region, environment, usage_quantity, usage_unit, cost_usd`

---

### `cloud-cost-forecasting/app/forecasting/`
| Module | Responsibility |
|--------|----------------|
| `prophet_model.py` | `ForecastingModel` class wrapping Prophet; `fit()`, `predict()`, `predict_on_dates()`, `evaluate()` (MAE/RMSE/MAPE/sMAPE) |
| `baselines.py` (experiments) | Naive, MovingAverage(7/14/30), Prophet; rolling-origin evaluation |

**Forecasting Pipeline:**
1. Daily aggregation: `df.groupby('date')['cost_usd'].sum()`
2. Chronological 80/20 train/test split
2. Prophet fit on train, predict on test + future horizon
3. Evaluation on holdout test set: MAE, RMSE, MAPE, sMAPE
4. Rolling-origin: 12 folds, 90-day initial train, 7-day horizon, 7-day step

---

### `cloud-cost-forecasting/app/anomaly/`
| Module | Responsibility |
|--------|----------------|
| `isolation_forest.py` | `AnomalyDetector` wrapper: `fit()`, `predict()`, `score_samples()`, `evaluate()` |
| `cost_aware.py` | `CostImpactScorer` — gated additive scoring, ranking, top-K, cumulative cost capture |
| `explanations.py` | `AnomalyExplainer` — deterministic, template-based explanations |
| `baselines.py` (experiments) | Threshold, RawCost_IF, Residual_IF, evaluation metrics |

**Anomaly Pipeline:**
1. Compute residuals: `actual - predicted` on test period
2. Feature engineering: `residual`, `lag1`, `rolling_mean_7`, `rolling_std_7`
3. Isolation Forest fit on training residuals (contamination=0.05)
4. Cost-impact scoring: `norm_score + α × norm_excess × confidence × gate`
5. Gate: only applies cost weighting when `norm_score > gate_threshold`
6. Rank by `cost_impact_score`, generate explanations

---

### `cloud-cost-forecasting/app/tracking/`
| Module | Responsibility |
|--------|----------------|
| `tracker.py` | `ExperimentTracker` — MLflow wrapper: `start_run()`, `log_params()`, `log_metrics()`, `log_artifact()`, `log_model()`, `log_figure()`, `log_table()` |
| `__init__.py` | `get_tracker()` factory |

---

### `cloud-cost-forecasting/app/visualization/`
| Function | Purpose |
|----------|---------|
| `plot_historical_spending()` | Daily spend line chart |
| `plot_forecast_with_intervals()` | Historical + forecast + 80% CI bands |
| `plot_anomalies()` | Historical + anomaly markers |
| `create_spending_by_service_chart()` | Bar chart: total spend by service |
| `create_monthly_trend_chart()` | Monthly spend line chart |

---

### `cloud-cost-forecasting/app/tracking/`
| Module | Responsibility |
|--------|----------------|
| `tracker.py` | `ExperimentTracker` — MLflow wrapper: `start_run()`, `log_params()`, `log_metrics()`, `log_artifact()`, `log_model()`, `log_figure()`, `log_table()` |

---

### `experiments/`
| Module | Purpose |
|--------|---------|
| `forecasting/baselines.py` | Naive, MA(7/14/30), Prophet; rolling-origin evaluation |
| `anomaly/baselines.py` | Threshold, RawCost_IF, Residual_IF, evaluation |
| `anomaly/cost_aware.py` | CostImpactScorer, gated additive, ranking, evaluation |
| `anomaly/explanations.py` | AnomalyExplainer, batch explanations, UI formatting |
| `run_experiments.py` | Full pipeline: forecasting → anomaly → cost-aware → MLflow |

---

### `experiments/data/`
| File | Description |
|------|-------------|
| `synthetic_benchmark.csv` | 180 days, 2 providers, 10 services, daily aggregated |
| `synthetic_benchmark_detailed.csv` | Service-level detail (1800 rows) |
| `ground_truth_anomalies.csv` | 7 controlled anomaly events with metadata |
| `benchmark_metadata.json` | Generation parameters, seed, schema |

---

## Data Flow

```
Raw CSV (AWS CUR / GCP Billing)
         │
         ▼
┌─────────────────────────────────────┐
│ ingest_billing_data(file_paths)     │
│   → detect format (AWS/GCP)         │
│   → rename columns → unified schema │
│   → type coercion, date parsing     │
│   → add cloud_provider label        │
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│ daily_df = df.groupby('date').sum() │
│ daily_df = daily_df[['date','cost']]│
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ train/test split (80/20 chronological)     │
│ Prophet.fit(train)                    │
│ forecast = model.predict(horizon)     │
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ test_actual = test['y']             │
│ test_pred = model.predict(test)     │
│ residuals = test_actual - test_pred │
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ anomaly_features = residuals + lags │
│ IsolationForest.fit(anomaly_features)        │
│ anomaly_scores = model.score_samples()       │
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ CostImpactScorer.rank_anomalies()   │
│   excess = max(actual - pred, 0)    │
│   norm_score = normalize(anomaly)   │
│   gate = (norm_score > 0.5)         │
│   score = norm_score + α×cost×conf×gate       │
│   rank by cost_impact_score         │
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ AnomalyExplainer.explain_batch()    │
│   → human-readable explanations     │
└───────────┬─────────────────────────┘
            ▼
┌─────────────────────────────────────┐
│ Streamlit UI + MLflow logging       │
└─────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Chronological train/test split | Time-series integrity; no data leakage |
| Rolling-origin evaluation | Realistic production simulation |
| Prophet only (no ARIMA) | Simplicity; strong baseline; proven at scale |
| Isolation Forest on residuals | Removes trend/seasonality; isolates true anomalies |
| Gated additive scoring | Prevents high-cost normal days from dominating |
| Test-period residual IF | No data leakage; evaluates on unseen data |
| Additive cost-impact | Interpretable: score + cost contribution |
| Gate threshold (0.5) | Median anomaly score; prevents high-cost normals from dominating |
| Template explanations | Deterministic, auditable, no hallucination |
| MLflow local SQLite | Zero-config local dev; cloud-ready with managed server |

---

## Configuration

| File | Purpose |
|------|---------|
| `cloud-cost-forecasting/requirements.txt` | Pinned dependencies (includes `starlette<1.8.0` for Streamlit ASGI response ordering compatibility) |
| `cloud-cost-forecasting/.streamlit/config.toml` | Streamlit server config |
| `.streamlit/config.toml` | Server config (headless, port, CORS) |
| `.gitignore` | Excludes `__pycache__/`, `*.pyc`, `mlflow.db`, `test_env/`, `.env`, `*.log` |
| `.streamlit/config.toml` | `headless=true`, `port=8501`, `enableCORS=true` |

### Dual Requirements Setup

Dependency pins exist in two locations with identical contents:
- Root: `requirements.txt`
- App: `cloud-cost-forecasting/requirements.txt`

Install from `cloud-cost-forecasting/requirements.txt` (the CI workflow uses this path).

### Sample Datasets

Four sample CSV files are stored in `cloud-cost-forecasting/data/samples/` and discovered dynamically at runtime via `Path.glob("*.csv")`:

| File | Provider | Rows | Days | Services |
|------|----------|------|------|----------|
| `sample_aws_billing.csv` | AWS | 360 | 90 | 4 (EC2, S3, RDS, Lambda) |
| `sample_gcp_billing.csv` | GCP | 360 | 90 | 4 (Compute Engine, Cloud Storage, BigQuery, Cloud Functions) |
| `sample_test_1000.csv` | Mixed | 1,000 | — | — |
| `sample_test_2000.csv` | Mixed | 2,000 | — | — |

All sample data is synthetic. Sample data is loaded through the Streamlit sidebar "Load Sample Data" dropdown or via file upload.

---

## Deployment Considerations

| Aspect | Local | Streamlit Cloud |
|--------|-------|-----------------|
| MLflow | Local SQLite (`mlflow.db`) | Requires managed server (DagsHub, Dagster, self-hosted) |
| Data | Local files / upload | Upload via UI |
| Persistence | Local filesystem | Ephemeral (use external DB) |
| Auth | None (local) | Streamlit auth or custom |

**Streamlit Cloud deployment notes:**
- Entrypoint: `cloud-cost-forecasting/app.py`
- Default branch is `master` (not `main`) — configure Streamlit Cloud accordingly
- MLflow local SQLite does not persist across redeploys; use a managed tracking server for production

---

## Testing

| Suite | Command | Coverage |
|-------|---------|----------|
| Unit/Integration | `pytest tests/ -v` | 56 tests (44 root + 12 app) |
| Lint | `pyflakes app/` | Clean |
| Compile | `python -m compileall app/` | Clean |
| Smoke | `streamlit run app.py --server.headless true` | Manual |

---

## Extending the Platform

| Extension Point | Location |
|-----------------|----------|
| New forecast model | `app/forecasting/` + `create_forecasting_model()` |
| New anomaly method | `app/anomaly/` + `create_anomaly_detector()` |
| New explanation template | `app/anomaly/explanations.py` |
| New viz | `app/visualization/plots.py` |
| New tracking backend | `app/tracking/tracker.py` |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Quick start, features, usage |
| `docs/ML_METHODOLOGY.md` | Models, baselines, evaluation |
| `docs/EXPERIMENTAL_VALIDATION.md` | Benchmarks, rolling-origin, ablation |
| `docs/FEATURES.md` | Buyer-facing feature matrix |
| `COST_AWARE_PHASE3B_REPORT.md` | Phase 3B validation |
| `PHASE_4_FINAL_REPORT.md` | Phase 4 integration summary |