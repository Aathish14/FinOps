# ML Methodology

## Overview

This document describes the machine learning methodology behind FinOps, including forecasting models, anomaly detection approaches, evaluation methodology, and the validated cost-impact-aware anomaly ranking contribution.

---

## 1. Forecasting Models

### 1.1 Prophet (Primary)

**Library:** Facebook Prophet 1.3+
**Configuration:** Default seasonality, multiplicative option disabled, daily frequency

**Why Prophet:**
- Handles missing data, outliers, and seasonality automatically
- Interpretable components (trend, yearly/weekly seasonality, holidays)
- Robust to missing data and irregular timestamps
- Proven at scale (Facebook, Uber, Shopify, etc.)
- Native uncertainty intervals via MCMC sampling

**Configuration:**
```python
Prophet(
    yearly_seasonality='auto',
    weekly_seasonality='auto',
    daily_seasonality=False,
    seasonality_mode='additive',  # or 'multiplicative'
    interval_width=0.80,  # 80% confidence intervals
    changepoint_prior_scale=0.05
)
```

**Training:** Daily aggregated cost series, chronological 80/20 split
**Forecast Horizon:** 7–30 days (configurable via UI slider)
**Confidence Intervals:** 80% (configurable via `interval_width`)

---

### 1.2 Baseline Models (Experimental)

| Model | Implementation | Purpose |
|-------|---------------|---------|
| Naive | Last observed value | Sanity lower bound |
| MovingAverage(7) | 7-day rolling mean | Short-term baseline |
| MovingAverage(14) | 14-day rolling mean | Weekly seasonality baseline |
| MovingAverage(30) | 30-day rolling mean | Monthly trend baseline |

**No ARIMA/SARIMA** — intentionally omitted. Prophet outperforms ARIMA on cloud cost data with strong weekly seasonality and trend changes. Adding ARIMA would increase complexity without proven benefit on our benchmark.

---

## 2. Anomaly Detection

### 2.1 Isolation Forest

**Algorithm:** Isolation Forest (scikit-learn 1.4+)
**Principle:** Anomalies are "few and different" — easier to isolate in random partitioning

**Configuration:**
```python
IsolationForest(
    contamination=0.05,      # Expected anomaly proportion
    random_state=42,         # Reproducibility
    n_estimators=200,        # Ensemble size
    max_features=1.0,        # All features
    bootstrap=False          # Use full dataset per tree
)
```

**Why Isolation Forest:**
- Linear time complexity O(n)
- Handles high-dimensional data
- No distribution assumptions
- Robust to outliers in training data (they're isolated quickly)
- Native anomaly scores via `score_samples()`

---

### 2.2 Feature Engineering (Residual-Based)

**Input:** Forecast residuals on test period: `residual = actual - predicted`

**Features (4-dimensional):**
| Feature | Formula | Purpose |
|---------|---------|---------|
| `residual` | `actual - predicted` | Raw deviation |
| `residual_lag1` | `residual.shift(1)` | Temporal dependency |
| `rolling_mean_7` | `residual.rolling(7, min_periods=1).mean()` | Local trend |
| `rolling_std_7` | `residual.rolling(7, min_periods=1).std()` | Local volatility |

**Missing Value Handling:** `bfill().ffill()` (backfill then forward-fill)

**Why Residuals (Not Raw Cost):**
- Removes trend and seasonality → isolates true anomalies
- Normalizes across services with different spend magnitudes
- Forecast errors are more stationary than raw costs

---

### 2.3 Baseline Methods (Experimental Comparison)

| Method | Training Data | Anomaly Score |
|--------|---------------|---------------|
| **Threshold** | All historical | `cost > mean + 2×std` |
| **RawCost_IF** | Raw daily costs | Isolation Forest score |
| **Residual_IF** | Forecast residuals | Isolation Forest score |

---

## 3. Cost-Impact-Aware Anomaly Ranking (Validated Contribution)

### 3.1 Problem with Pure Statistical Ranking

Standard anomaly detectors rank by statistical deviation (z-score, IF score). **Problem:** A $100 anomaly in a $10M service ranks lower than a $10 anomaly in a $100 service — but the former costs 1000× more.

### 3.2 Original Formulation (Failed)

```
cost_impact = norm_score × norm_excess_cost × confidence  # MULTIPLICATIVE
```

**Problem:** Multiplicative form over-ranks high-cost normal days. If `norm_excess_cost ≈ 1` (high cost day) but `norm_score ≈ 0` (normal), product ≈ 0 — correct. But if `norm_score` has noise, high-cost days get boosted.

### 3.3 Gated Additive Formulation (Validated)

```
cost_impact = norm_score + α × norm_excess_cost × confidence × gate

where:
  norm_score = normalized anomaly magnitude [0, 1]
  norm_excess_cost = normalized excess cost [0, 1]
  confidence = 1 - MAPE (clipped to [0, 1])
  gate = 1 if norm_score > gate_threshold else 0
  α = 0.5 (scaling factor)
  gate_threshold = 0.5 (median anomaly evidence)
```

**Key Properties:**
1. **Additive** — anomaly evidence (`norm_score`) always contributes
2. **Gated** — cost weighting only activates when anomaly evidence > threshold
3. **Confidence-weighted** — uncertain forecasts reduce cost contribution
4. **Interpretable** — decomposable into evidence + financial impact

### 3.3 Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `alpha` | 0.5 | Balances evidence vs cost; not tuned per-provider |
| `gate_threshold` | 0.5 | Median normalized anomaly score; only top 50% get cost boost |
| `contamination` | 0.05 | Standard IF default; expects ~5% anomalies |
| `confidence_weight` | 1.0 | Full confidence weight |
| `cost_weight` | 1.0 | Full cost weight |
| `score_weight` | 1.0 | Full evidence weight |

---

## 4. Evaluation Methodology

### 4.1 Forecasting Evaluation

**Protocol:** Rolling-origin walk-forward validation
- **Initial train:** 90 days
- **Test horizon:** 7 days
- **Step:** 7 days (weekly)
- **Folds:** 12 per provider (180 days / 7 - 90/7 ≈ 12)
- **Minimum train:** 60 days

**Metrics:**
| Metric | Formula | Handling |
|--------|---------|----------|
| MAE | `mean(|y_true - y_pred|)` | Standard |
| RMSE | `sqrt(mean((y_true - y_pred)²))` | Standard |
| MAPE | `mean(|y_true - y_pred| / |y_true|)` | Zero actuals → NaN (excluded) |
| sMAPE | `2×mean(|y_true - y_pred| / (|y_true| + |y_pred|))` | Symmetric, handles zeros |

**No random splits** — strictly chronological to prevent leakage.

---

### 4.2 Anomaly Detection Evaluation

**Data Split:** 70/30 chronological (train/test)
**Ground Truth:** Synthetic anomalies injected with known timestamps

**Metrics:**
| Metric | Formula | Use Case |
|--------|---------|----------|
| Precision | TP / (TP + FP) | Alert fatigue |
| Recall | TP / (TP + FN) | Missed anomalies |
| F1 | 2×P×R / (P+R) | Balance |
| PR-AUC | Area under P-R curve | Threshold-independent |
| Cost@K | Σ excess_cost(top-K) / total_excess | Financial prioritization |

**Ground Truth:** Synthetic anomalies with known timestamps/magnitudes (7 events, 38 anomaly days)

---

### 4.3 Cost-Impact Evaluation (Novel)

**Primary Metric:** Cumulative Excess Cost Captured @ K
```
Cost@K = Σ_{i=1..K} excess_cost(rank_i) / total_excess_cost
```

**Secondary:** Anomaly Recall@K, Precision@K, PR-AUC

---

## 5. Experiment Design

### 5.1 Synthetic Benchmark (180 days)

| Property | Value |
|----------|-------|
| Duration | 180 days (Jan 1 – Jun 28, 2024) |
| Providers | AWS (5 services), GCP (5 services) |
| Frequency | Daily |
| Services | 10 (5 per provider) |
| Anomaly Events | 7 controlled events, 38 anomaly days |
| Anomaly Types | Sudden spike, sustained increase, temporary surge, gradual drift |

**Generation Parameters:**
- Seed: 42 (reproducible)
- Trend: Linear growth
- Seasonality: Weekly (sinusoidal, 7-day period)
- Noise: Gaussian, σ = 5-15% of base cost
- Anomalies: 7 events (spikes 3-4×, sustained 1.5-2×, drift 1.5× over 14 days)

**Why Synthetic?** Real cloud billing data contains PII, contractual restrictions, and cannot be shared. Synthetic data enables:
- Full reproducibility (seed=42)
- Known ground truth for anomaly evaluation
- Controlled anomaly types/magnitudes
- Public sharing without legal risk

> **Limitation:** Synthetic data lacks real-world complexity (holidays, multi-account, correlated services, contract changes). Real-world validation pending.

---

### 5.2 Rolling-Origin Validation

**Protocol:**
```
Fold 1: Train[0:90]   → Test[90:97]
Fold 2: Train[0:97]   → Test[97:104]
Fold 3: Train[0:104]  → Test[104:111]
...
Fold 12: Train[0:167] → Test[167:174]
```

- Initial train: 90 days
- Test horizon: 7 days
- Step: 7 days
- Min train: 60 days
- Total folds: 12 per provider

---

### 5.3 Anomaly Detection Evaluation

**Train/Test Split:** 70/30 chronological (125/55 days)
**Forecast Model:** Prophet (trained on train, predicts test)
**Anomaly Features:** Residual + lag + rolling μ/σ (7-day)
**Ground Truth:** Synthetic anomaly labels (known injection points)

---

## 6. Model Cards

### ProphetForecaster
| Aspect | Detail |
|--------|--------|
| Model | Facebook Prophet 1.3+ |
| Input | Daily cost series (ds, y) |
| Output | Forecast (yhat, yhat_lower, yhat_upper) |
| Horizon | 7-30 days (configurable) |
| Intervals | 80% (configurable) |
| Evaluation | Rolling-origin, 12 folds |

### IsolationForestAnomalyDetector
| Aspect | Detail |
|--------|--------|
| Model | sklearn.ensemble.IsolationForest |
| Input | Feature matrix (residual, lag1, roll_mean_7, roll_std_7) |
| Output | Predictions (-1/1), Scores (negative = anomalous) |
| Contamination | 0.05 (configurable) |
| Random State | 42 (reproducible) |

### CostImpactScorer
| Aspect | Detail |
|--------|--------|
| Formula | `norm_score + α × norm_excess × confidence × gate` |
| Alpha | 0.5 |
| Gate Threshold | 0.5 (median norm_score) |
| Normalization | Min-max to [0,1] per component |
| Gate | `norm_score > 0.5` |

---

## 7. Reproducibility

| Aspect | Implementation |
|--------|----------------|
| Random Seeds | `np.random.seed(42)`, `random_state=42` |
| Data Split | Fixed chronological splits (no random) |
| Model Config | All hyperparameters in code (no external config) |
| Dependencies | Pinned in `requirements.txt` (exact versions) |
| MLflow | Auto-logs params, metrics, artifacts |
| Synthetic Data | Deterministic generation (seed=42) |

---

## 8. Failed Approaches (Documented for Transparency)

| Approach | Why It Failed |
|----------|---------------|
| Multiplicative cost-impact (`score × cost × confidence`) | Over-ranks high-cost normal days on low-anomaly-density data |
| Residual-only Isolation Forest (no cost weighting) | Misses high-cost anomalies with moderate statistical deviation |
| Raw-cost Isolation Forest alone | Misses context; high-cost services always rank high |
| Fixed threshold (mean + kσ) | No adaptation to trend/seasonality; high FP rate |
| Residual-only ranking (no cost) | Misses high-impact anomalies with moderate statistical deviation |
| ARIMA forecasting | Underperforms Prophet on weekly-seasonal cloud data |
| SHAP explanations | No predictive model to explain (IF is unsupervised); template explanations used instead |

---

## 8. Hyperparameter Sensitivity

| Parameter | Tested Range | Selected | Sensitivity |
|-----------|--------------|----------|-------------|
| `alpha` | [0.25, 0.5, 0.75, 1.0] | 0.5 | Low (AWS stable) |
| `gate_threshold` | [0.25, 0.5, 0.75] | 0.5 | Medium (AWS sensitive) |
| `contamination` | [0.01, 0.05, 0.1] | 0.05 | Low |
| `contamination` (GCP) | [0.03, 0.05, 0.1] | 0.05 | Medium |

> **Note:** Parameters not tuned per-provider. Single config works for both AWS/GCP.