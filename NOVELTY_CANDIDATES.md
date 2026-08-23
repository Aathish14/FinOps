# NOVELTY CANDIDATES

## Overview
Five candidate research contributions derived from gap analysis. Each evaluated against novelty, evidence, implementability, and impact.

---

## Candidate 1: Cost-Impact-Aware Anomaly Ranking with Explanations

### Research Problem
Cloud cost anomalies are currently ranked by statistical deviation (Isolation Forest score, z-score, threshold breach), not by business impact. A $100 spike in a low-cost service may score higher than a $10,000 gradual drift in a critical service. FinOps teams need to prioritize by **estimated dollar impact**, not statistical significance.

### Existing Solutions
| Solution | Approach | Limitation |
|----------|----------|------------|
| Wang et al. 2022 (ICDE) | Cost-weighted Isolation Forest | Paper only, no open-source; weights by cost but no explanation |
| CloudZero | "Cost context" | Proprietary; no open benchmark |
| Commercial platforms | Show $ impact in UI | Proprietary; no SHAP explanations; no counterfactual |

### Gap
**No open-source implementation of cost-impact-aware anomaly detection with explanations for cloud costs.**

### Proposed Contribution
1. **Cost-weighted anomaly scoring**: `anomaly_score × cost_magnitude × forecast_confidence`
2. **SHAP explanations for cloud cost anomalies**: Feature importance on (service, account, usage_type, region, residual, trend_deviation)
3. **Counterfactual cost-impact estimation**: "What would cost be without this anomaly?" using forecast counterfactual
4. **Severity tiers**: Critical/High/Medium/Low based on `$ impact × statistical confidence`
5. **Open-source benchmark**: Synthetic + real data evaluation framework

### Why Novel
- **First open-source** cost-impact-aware anomaly detection for cloud costs
- **First SHAP explanations** adapted for cloud cost anomalies (service/account/usage features)
- **First counterfactual cost-impact estimation** for cloud anomalies
- **First open benchmark** for cost-impact-aware anomaly detection

### Evidence
- **Supporting**: Wang et al. 2022 (ICDE) proposes cost-weighted IF; CloudZero markets "cost context"; FinOps Foundation emphasizes cost optimization
- **Contradicting**: Commercial implementations proprietary; no open-source baseline

### Required Implementation
1. Cost-weighted anomaly scoring function in `anomaly/`
2. SHAP explainer for Isolation Forest (tree-based SHAP)
4. Counterfactual estimator: `cost_without_anomaly = forecast_without_anomaly_period`
5. Severity tier classification: `Critical/High/Medium/Low`
6. Experimental framework: compare cost-weighted vs statistical ranking

### Required Experiment
- **Dataset**: Real cloud billing data (AWS CUR + GCP Billing Export)
- **Baselines**: Raw-cost IF, Residual IF, Threshold
- **Metrics**: Precision@k on cost-weighted anomalies, explanation quality (human eval), counterfactual accuracy
- **Ablation**: cost-weighting vs residual vs raw-cost

### Risk
- Requires real cloud billing data for meaningful validation (synthetic insufficient for cost patterns)
- SHAP on Isolation Forest requires tree explainer (available but slower)
- Counterfactual estimation requires retraining forecast without anomaly period

### Research Value
**HIGH** - Addresses core FinOps pain point (prioritization by $ impact), first open implementation, measurable improvement over statistical ranking.

---

## Candidate 2: Expected-vs-Legitimate Change Classification

### Research Problem
Planned changes (new deployment, auto-scale event, reserved instance purchase, new service launch) are flagged as anomalies. FinOps teams waste time investigating "anomalies" that are actually expected business changes.

### Existing Solutions
| Solution | Approach | Limitation |
|----------|----------|------------|
| CI/CD webhook tagging | Manual tagging of deployments | Tags often missing/incomplete |
| AWS/GCP change calendars | Manual entry | Not automated; not linked to anomaly detection |
| Commercial platforms | "Planned change" UI | Proprietary; requires manual input |

### Gap
**No automated classification of "expected vs legitimate" changes for cloud cost anomalies.** No academic literature addresses this specific problem for cloud costs.

### Proposed Contribution
1. **Deployment event integration**: CI/CD webhooks (GitHub Actions, GitLab, Jenkins, ArgoCD) → change events
2. **Change type classification**: Deployment / Scale event / RI purchase / Config change / New service
4. **Expected change detection**: Correlate cost changes with deployment events within time window
5. **Legitimate change classification**: ML classifier (cost pattern + deployment context → expected/legitimate/anomalous)
5. **Anomaly suppression**: Expected changes excluded from anomaly alerts

### Why Novel
- **First automated** expected-vs-legitimate classification for cloud cost anomalies
- **First integration** of CI/CD deployment events with cost anomaly detection
- **First ML classifier** for "legitimate change" in cloud cost context

### Evidence
- **Supporting**: No academic papers on this; FinOps Foundation mentions "planned vs unplanned" but no tooling; CI/CD integration not in literature
- **Contradicting**: Could use tagging/webhooks without ML; tags often incomplete

### Required Implementation
1. Webhook receivers for major CI/CD platforms
2. Change event schema (timestamp, type, service, account, magnitude)
3. Temporal correlation engine (cost change ± deployment window)
4. Classifier: features = (cost_pattern, deployment_context, service_history) → label
5. UI: "Expected Changes" panel showing suppressed anomalies

### Required Experiment
- **Dataset**: Real deployment events + cost data (need partner organization)
- **Baselines**: Time-window correlation only, tag-based only
- **Metrics**: Precision/Recall on expected change detection; false suppression rate
- **Ablation**: ML classifier vs time-window only

### Risk
- Requires real deployment event data (CI/CD webhooks)
- ML classifier needs labeled data (expected vs anomalous changes)
- Deployment events often missing service/account context

### Research Value
**HIGH** - Addresses major FinOps pain point (alert fatigue from expected changes), first automated solution, high practical impact.

---

## Candidate 3: Cost-Impact-Aware Severity Ranking

### Research Problem
Anomalies need severity tiers (Critical/High/Medium/Low) that reflect business urgency, not just statistical deviation. Current approaches use fixed contamination rates or fixed thresholds.

### Existing Solutions
| Solution | Approach | Limitation |
|----------|----------|------------|
| Fixed contamination (5%) | Statistical | Ignores cost magnitude |
| Threshold (mean + 2σ) | Statistical | Ignores cost magnitude |
| Commercial platforms | $ impact tiers | Proprietary; no open standard |

### Gap
**No open standard for cost-impact-aware severity tiers** in cloud cost anomaly detection.

### Proposed Contribution
1. **Severity formula**: `Severity = f($impact, statistical_confidence, forecast_horizon)`
6. **Tiers**: Critical ($>10K/day + high confidence), High ($>1K/day), Medium ($>100/day), Low (<$100/day)
7. **Dynamic thresholds**: Adjust based on forecast uncertainty (wider PI → lower severity)
7. **Business context integration**: Budget utilization, reserved instance coverage

### Why Novel
- **First open severity framework** for cloud cost anomalies
- **First dynamic thresholding** based on forecast uncertainty

### Evidence
- **Supporting**: FinOps Foundation emphasizes cost optimization; commercial platforms show tiers but proprietary
- **Contradicting**: May be simple UI addition rather than research contribution

### Required Implementation
1. Severity calculation function: `severity = g(cost_impact, mape, forecast_horizon, budget_utilization)`
7. Tier definitions configurable per organization
8. UI: Severity badges, tiered alerting

### Required Experiment
- **Metric**: Does tiered severity improve FinOps team response time vs flat alerts?
- **Comparison**: Fixed threshold vs dynamic severity

### Risk
- May be engineering rather than research contribution
- Tier definitions highly organization-specific

### Research Value
**MEDIUM** - Practical but may be engineering rather than research novelty.

---

## Candidate 4: Multi-Cloud Anomaly Normalization & Correlation

### Research Problem
Cannot compare anomaly severity across AWS/GCP/Azure due to different pricing models, service granularity, and usage patterns. Cross-provider anomalies (e.g., same application deployed on AWS and GCP both spike) go undetected.

### Existing Solutions
| Solution | Approach | Limitation |
|----------|----------|------------|
| Li et al. 2023 | Multi-cloud VAE for detection | No severity normalization |
| Commercial platforms | Unified dashboards | Proprietary; no severity normalization |

### Gap
**No method to normalize anomaly severity across cloud providers** for fair comparison and cross-provider correlation.

### Proposed Contribution
1. **Cross-provider severity normalization**: Map provider-specific anomaly scores to common scale using pricing models
7. **Cross-provider correlation engine**: Detect same-application anomalies across providers
7. **Unified severity scale**: Provider-agnostic severity (0-100)

### Why Novel
- **First cross-provider anomaly normalization** method
- **First cross-provider correlation** for cloud cost anomalies

### Evidence
- **Supporting**: Li et al. 2023 does multi-cloud detection but not normalization; commercial platforms don't publish methods
- **Contradicting**: Hard problem - different pricing, services, granularity

### Required Implementation
1. Provider pricing model normalization (unit cost mapping)
7. Anomaly score calibration per provider
8. Cross-provider correlation engine (service name matching, deployment correlation)

### Required Experiment
- **Dataset**: Multi-cloud billing with same application on multiple providers
- **Metrics**: Normalization accuracy (human eval), correlation detection rate

### Risk
- **Hard problem**: Different services, pricing models, usage units
- **Data availability**: Need same app on multiple clouds

### Research Value
**MEDIUM** - Hard problem, practical value but high implementation risk.

---

## Candidate 5: Human Feedback Loops / Active Learning for Cloud Cost Anomalies

### Research Problem
Anomaly detection models don't improve from FinOps team feedback. No mechanism to label anomalies and retrain.

### Existing Solutions
| Solution | Approach | Limitation |
|----------|----------|------------|
| Active learning for AD | General ML | Not applied to cloud costs |
| Commercial platforms | "Mark as false positive" | No model retraining |

### Gap
**No human feedback loop / active learning for cloud cost anomaly detection.**

### Proposed Contribution
1. **Anomaly labeling UI**: FinOps team marks True Positive / False Positive / Expected Change
7. **Model retraining pipeline**: Periodic retraining with labeled data
7. **Active learning**: Query most uncertain anomalies for labeling
8. **Feedback-aware scoring**: Down-weight repeatedly false-positive patterns

### Why Novel
- **First active learning** for cloud cost anomaly detection
- **First human-in-the-loop** framework for cloud cost anomalies

### Evidence
- **Supporting**: Active learning for AD exists in other domains; FinOps practice implies human review
- **Contradicting**: Not applied to cloud costs; no prior work

### Required Implementation
1. Labeling UI in Streamlit (TP/FP/Expected Change)
7. Retraining scheduler (weekly/monthly)
8. Active learning query strategy (uncertainty sampling)
8. Feedback-weighted model ensemble

### Required Experiment
- **Simulation**: Inject synthetic feedback, measure model improvement over time
- **Metric**: Anomaly detection F1 improvement with feedback vs without

### Risk
- Requires human-in-the-loop (hard to simulate)
- Model retraining frequency vs stability tradeoff

### Research Value
**HIGH** - Clear gap, high practical value, no prior work.

---

## Summary Comparison

| Candidate | Novelty | Evidence | Implementability | Impact | Risk | Overall |
|-----------|---------|----------|------------------|--------|------|---------|
| **1. Cost-Impact-Aware Ranking + Explanations** | ⭐⭐⭐ | Strong | HIGH | HIGH | MEDIUM | ⭐⭐⭐ |
| **2. Expected-vs-Legitimate Classification** | ⭐⭐⭐ | Strong | MEDIUM | HIGH | MEDIUM | ⭐⭐⭐ |
| **3. Cost-Impact Severity Ranking** | ⭐⭐ | MEDIUM | HIGH | MEDIUM | LOW | ⭐⭐ |
| **4. Multi-Cloud Normalization** | ⭐⭐ | WEAK | LOW | MEDIUM | HIGH | ⭐ |
| **5. Human Feedback Loops** | ⭐⭐⭐ | WEAK | MEDIUM | HIGH | MEDIUM | ⭐⭐ |

---

## Recommended Selection

**Primary**: **Candidate 1 - Cost-Impact-Aware Anomaly Ranking with Explanations**
- Strongest evidence base
- Clear implementation path
- Measurable experimental validation
- Addresses core FinOps pain point ($ impact prioritization)
- Builds on experimental finding (Residual_IF fails because it ignores cost magnitude)

**Secondary**: **Candidate 2 - Expected-vs-Legitimate Change Classification**
- Complementary to Candidate 1
- Could be integrated (expected changes excluded from cost-impact ranking)

**Tertiary**: **Candidate 5 - Human Feedback Loops**
- Long-term value for model improvement
- Could be phased implementation

---

## What NOT to Claim as Novelty

| Claim | Why Not Novel |
|-------|---------------|
| "Multi-cloud anomaly detection" | Commercial platforms |
| "Residual-based anomaly detection" | Liu et al. 2021, Chen et al. 2020 |
| "Isolation Forest for cloud costs" | Standard application |
| "Prophet for cloud forecasting" | Standard application |
| "Rolling-origin evaluation" | Standard time series practice |
| "MLflow integration" | Standard MLOps |
| "Multi-cloud ingestion" | Standard engineering |
| "Streamlit UI" | Standard tooling |

---

## What IS Novel (If Implemented Well)

| Contribution | Why Novel |
|--------------|-----------|
| Cost-impact-weighted anomaly scoring for cloud costs | No open-source implementation |
| SHAP explanations for cloud cost anomalies | Kim et al. 2023 only paper; no open-source |
| Counterfactual cost-impact estimation | No paper on counterfactual cost for anomalies |
| Expected vs legitimate change classification | No literature; practical gap |
| Cost-impact-aware severity tiers | No standard; commercial proprietary |
| Open benchmark for cost-impact-aware AD | No public benchmark exists |

---

## Next Steps
1. **Select primary candidate** (Candidate 1 recommended)
2. **Define exact experimental protocol** for validation
3. **Identify real data source** (partner org or public dataset)
3. **Implement core contribution** in `experiments/` layer
4. **Run validation experiments** with real data
5. **Write research paper** if results support novelty