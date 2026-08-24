# FinOps — Cloud Cost Forecasting & Spend Anomaly Detection

A production-ready, multi-cloud FinOps analytics platform for forecasting cloud spending and detecting spend anomalies with financial-impact prioritization.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-20%2F20%20passing-brightgreen)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

---

## Overview

**FinOps** is a production-ready FinOps analytics platform that helps engineering and finance teams:

- **Forecast** cloud spending with Prophet-based time-series models
- **Detect** anomalous spend patterns using Isolation Forest on forecast residuals
- **Prioritize** anomalies by estimated financial impact (not just statistical deviation)
- **Explain** anomalies with transparent, deterministic reasoning
- **Track** all experiments reproducibly via MLflow

---

## Problem

Cloud spending is growing unpredictably. Engineering teams lack visibility into:

- **Future spend** — no reliable forecasts for budgeting
- **Anomalous spikes** — unexpected cost surges go undetected until the bill arrives
- **Prioritization** — statistical anomaly scores don't reflect business impact ($)
- **Root cause** — anomalies lack explainable context for fast triage

FinOps solves this with a unified pipeline: **ingest → forecast → detect → prioritize → explain**.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-cloud ingestion** | AWS CUR + GCP Billing Export CSV → unified schema |
| **Forecasting** | Prophet with 80% confidence intervals, 7–30 day horizon |
| **Anomaly detection** | Isolation Forest on forecast residuals (test-period only) |
| **Cost-impact prioritization** | Ranks anomalies by estimated $ impact, not just statistical score |
| **Explainable anomalies** | Transparent explanations: observed vs expected, excess cost, persistence, rank |
| **Cost-impact severity tiers** | Critical / High / Medium / Low based on $ impact × confidence |
| **MLflow experiment tracking** | Parameters, metrics, artifacts, and ranking logs |
| **Interactive Streamlit dashboard** | Forecasts, anomalies, explanations, cost-impact ranking |
| **Reproducible experiments** | Rolling-origin evaluation, baselines, MLflow tracking |

---

## Architecture

```
┌─────────────┐
│  AWS CUR    │
│  GCP Billing│
└──────┬──────┘
       ▼
┌─────────────────┐
│  Data Ingestion │  (AWS CUR / GCP Billing Export → unified schema)
└────────┬────────┘
         ▼
┌─────────────────────┐
│  Preprocessing      │  (chronological sort, type coercion, validation)
└────────┬────────────┘
         ▼
┌──────────────────────────┐
│  Forecasting (Prophet)   │  Rolling-origin eval, 80% CI, 7-30 day horizon
└───────────┬──────────────┘
            ▼
┌──────────────────────────────┐
│  Anomaly Detection (IF)      │  Isolation Forest on test-period residuals
└───────────┬──────────────────┘
            ▼
┌──────────────────────────────────┐
│  Cost-Impact Ranking             │  gated additive: score + α·excess·conf·gate
└───────────┬──────────────────────┘
            ▼
┌────────────────────────────┐
│  Explanation Layer           │  Observed vs Expected, excess, rank, severity
└───────────┬──────────────────┘
            ▼
┌────────────────────┐
│  Streamlit Dashboard │  Forecasts, anomalies, rankings, explanations
└──────────────────────┘
            ▼
┌────────────┐
│  MLflow    │  Params, metrics, artifacts, rankings
└────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Forecasting | Facebook Prophet 1.3+ |
| Anomaly Detection | scikit-learn Isolation Forest |
| Explanations | SHAP-ready (tree explainer), deterministic templates |
| Experiment Tracking | MLflow 2.12+ (local SQLite, cloud-ready) |
| Dashboard | Streamlit 1.35+ / Plotly 5.20+ |
| Data Processing | pandas 2.2+, NumPy 1.26+ |
| Experiment Tracking | MLflow 2.12+ (local SQLite, cloud-ready) |

**Pinned dependencies** in `requirements.txt` for reproducibility.

---

## Quick Start

### Prerequisites
- Python 3.10+
- `pip` / `venv`

### Installation
```bash
# Clone
git clone https://github.com/Aathish14/FinOps.git
cd FinOps

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies (pinned versions)
pip install -r cloud-cost-forecasting/requirements.txt
```

### Run Locally
```bash
cd cloud-cost-forecasting
streamlit run app.py
# Opens http://localhost:8501
```

### With MLflow UI
```bash
mlflow ui  # http://localhost:5000
```

---

## Usage

### 1. Sample Data (included)
```bash
# Click "Load Sample Data" in sidebar, or:
# cloud-cost-forecasting/data/samples/sample_aws_billing.csv
# cloud-cost-forecasting/data/samples/sample_gcp_billing.csv
```
> **Note:** Sample data = 4 days per provider (synthetic). For meaningful forecasts, provide 60+ days of real billing history.

### 2. Your Data
1. Export AWS CUR (CSV) or GCP Billing Export (CSV)
2. Click **Upload Data** in sidebar → select CSV(s)
3. Set forecast horizon (7–30 days)
4. Click **Run Analysis**

---

## Methodology

### Data Ingestion
- Auto-detects AWS CUR vs GCP Billing Export format
- Normalizes to unified schema:
  `[date, cloud_provider, service_name, account_id, region, environment, usage_quantity, usage_unit, cost_usd]`
- Type coercion, date parsing, basic validation

### Forecasting (Prophet)
- Default seasonality, 80% confidence intervals
- Daily forecasts, 7–30 day horizon
- **Chronological 80/20 train/test split** — no random shuffling
- Rolling-origin walk-forward evaluation (12 folds × 2 providers)

### Anomaly Detection
- **Isolation Forest** on forecast residuals (test period only)
- Features: residual, lag-1, rolling mean/std (7-day window)
- Configurable contamination (default 5%)
- Trained **only on test-period residuals** — no data leakage

### Cost-Impact Ranking (Validated Contribution)
- **Gated additive scoring**: `norm_score + α × norm_excess_cost × confidence × gate`
- Gate activates only when anomaly evidence exceeds threshold
- Prevents high-cost normal days from dominating ranking
- **Validated**: AWS PR-AUC 1.000, Cost@3 capture +68% vs baseline

### Explanations
Deterministic, template-based explanations per anomaly:
- Observed vs expected cost, excess amount, relative deviation
- Anomaly score, persistence, cost-impact score, priority rank
- No fabricated root causes — only observable facts

### Experiment Tracking (MLflow)
- Experiment: `finops_forecasting_anomaly`
- Logged: params, metrics (MAE/RMSE/MAPE/PR-AUC), artifacts (fold CSVs), model
- Local SQLite backend; cloud deployment → managed tracking server

---

## Validation Results (Verified)

### Forecasting (Rolling-Origin, 12 folds × 2 providers)
| Model | AWS MAE | GCP MAE | AWS MAPE | GCP MAPE |
|-------|--------:|--------:|---------:|---------:|
| **Prophet** | **23.66** | **24.07** | **4.6%** | **5.6%** |
| MA(14) | 41.26 | 35.57 | 7.97% | 8.16% |
| MA(7) | 42.67 | 34.58 | 8.29% | 8.02% |
| Naive | 65.31 | 50.22 | 12.6% | 11.1% |

### Anomaly Detection (70/30 split, ground-truth synthetic anomalies)

| Method | AWS PR-AUC | GCP PR-AUC | AWS Cost@3 | GCP Cost@3 |
|--------|-----------:|-----------:|-----------:|-----------:|
| RawCost_IF | 0.792 | 0.283 | $108.65 | $108.65 |
| Residual_IF | 0.417 | 0.258 | $108.65 | $108.65 |
| **Cost-Aware (Validated)** | **1.000** | **0.300** | **$182.44** | **$182.44** |

**Key Finding**: Cost-aware ranking captures **68% more financial impact** in Top-3 on AWS, while maintaining GCP performance.

### Anomaly Ranking Quality
| Provider | True Anomalies | Ranked Top-3 | Ranked Top-4 |
|----------|---------------:|-------------:|-------------:|
| AWS | 3 | ✅ 3/3 | ✅ 3/3 |
| GCP | 10 | 1/10 | 3/10 |

---

## Installation

```bash
git clone https://github.com/Aathish14/FinOps.git
cd FinOps

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r cloud-cost-forecasting/requirements.txt
```

### Run Tests
```bash
pytest tests/ -v
# 20/20 passing
```

### Run Application
```bash
cd cloud-cost-forecasting
streamlit run app.py
# → http://localhost:8501
```

### MLflow UI
```bash
mlflow ui  # http://localhost:5000
```

---

## Project Structure

```
FinOps/
├── cloud-cost-forecasting/
│   ├── app.py                    # Streamlit entrypoint
│   ├── requirements.txt          # Pinned dependencies
│   ├── .streamlit/config.toml    # Streamlit config
│   ├── app/
│   │   ├── __init__.py
│   │   ├── ingest/               # AWS/GCP ingestion
│   │   ├── forecasting/          # Prophet model
│   │   ├── anomaly/              # Isolation Forest + cost-aware ranking
│   │   │   ├── cost_aware.py     # Gated additive scoring
    │   │   └── explanations.py   # Deterministic explanations
│   │   ├── forecasting/          # Prophet wrapper
│   │   ├── ingest/               # AWS CUR / GCP Billing parsers
│   │   ├── tracking/             # MLflow wrapper
│   │   └── visualization/        # Plotly charts
│   ├── data/
│   │   └── samples/              # Sample AWS/GCP CSVs
│   └── .streamlit/config.toml
├── experiments/
│   ├── data/                     # Synthetic benchmark + ground truth
│   ├── forecasting/              # Baselines: Naive, MA, Prophet
│   ├── anomaly/                  # Threshold, RawCost_IF, Residual_IF
│   ├── results/                  # CSV/JSON experiment outputs
│   └── run_experiments.py        # Full experiment runner
├── tests/                        # 20 tests (9 core + 11 explanations)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ML_METHODOLOGY.md
│   ├── EXPERIMENTAL_VALIDATION.md
│   └── FEATURES.md
├── requirements.txt              # Pinned deps (root)
├── .gitignore
└── README.md
```

---

## Configuration

All configuration via `cloud-cost-forecasting/.streamlit/config.toml`:

```toml
[server]
headless = true
port = 8501
enableCORS = true
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `MLFLOW_TRACKING_URI` | MLflow backend URI | `sqlite:///mlflow.db` (local) |
| `MLFLOW_EXPERIMENT_NAME` | Experiment name | `finops_forecasting_anomaly` |

> **No secrets in code.** All credentials via environment variables. `.env` is gitignored.

---

## Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect repo to [Streamlit Cloud](https://streamlit.io/cloud)
3. Entrypoint: `cloud-cost-forecasting/app.py`
4. Branch: `main` (or configure deployment branch)

> **Note:** MLflow local SQLite won't persist on Streamlit Cloud. For production, use a managed MLflow server (DagsHub, Dagster Cloud, self-hosted).

### Local MLflow
```bash
mlflow ui  # http://localhost:5000
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/ARCHITECTURE.md` | Pipeline diagram, module responsibilities |
| `docs/ML_METHODOLOGY.md` | Models, baselines, evaluation, formulation |
| `docs/EXPERIMENTAL_VALIDATION.md` | 180-day benchmark, rolling-origin, ablation |
| `docs/FEATURES.md` | Buyer-facing feature matrix |
| `COST_AWARE_PHASE3B_REPORT.md` | Phase 3B validation details |
| `PHASE_4_FINAL_REPORT.md` | Phase 4 integration summary |

---

## Limitations (Honest Disclosure)

| Limitation | Status |
|------------|--------|
| Sample data = 4 days (synthetic) | ☐ Will not produce meaningful forecasts |
| No ARIMA / SARIMA fallback | Only Prophet implemented |
| MLflow = local SQLite only | Cloud deployment needs managed server |
| No authentication / RBAC | Designed for internal use |
| Single-series forecasting | Aggregates all services; per-service not implemented |
| Synthetic benchmark only | 180-day synthetic data; real billing validation pending |
| No CI/CD pipeline | GitHub Actions not configured |
| No authentication/SSO | Internal use assumption |

> **We don't hide limitations.** This is an MVP with validated core — not a finished enterprise product.

---

## Commercial Use

### What You Receive
- Complete, runnable source code (MIT licensed)
- Reproducible experimental framework
- Reproducible ML pipeline with MLflow
- Interactive Streamlit dashboard
- Documented architecture, methodology, experiments
- Test suite (20 tests passing)

### What You Don't Get
- Real cloud billing data (you provide yours)
- Managed MLflow / cloud deployment
- Authentication / multi-tenancy
- Per-service forecasting
- CI/CD pipelines
- Warranty or SLA

### Target Buyer
- FinOps teams building internal tooling
- Platform engineering teams adding cost observability
- ML engineers studying cost-impact anomaly ranking
- Researchers extending forecasting/anomaly baselines

---

## License

MIT License — see [LICENSE](LICENSE) (add your own).

---

## Acknowledgements

- [Prophet](https://facebook.github.io/prophet/) — time series forecasting
- [scikit-learn](https://scikit-learn.org/) — Isolation Forest
- [MLflow](https://mlflow.org/) — experiment tracking
- [Streamlit](https://streamlit.io/) — web app framework
- [Plotly](https://plotly.com/) — interactive visualizations

---

## Support / Contact

For questions, issues, or commercial inquiries:
- GitHub Issues: [github.com/Aathish14/FinOps/issues](https://github.com/Aathish14/FinOps/issues)
- Email: (add your contact)

---

*FinOps — Making cloud costs predictable, anomalies explainable, and financial impact actionable.*