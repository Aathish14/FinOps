# PRIOR ART MATRIX

## Overview
Comparison of capabilities across academic research, cloud providers, commercial FinOps platforms, and current FinOps implementation.

**Evidence Quality Levels:**
- LEVEL 1: Official vendor documentation, peer-reviewed research
- LEVEL 2: Official technical papers, conference proceedings
- LEVEL 3: Reputable technical analysis
- LEVEL 4: Community discussion / blogs
- LEVEL 5: Search snippets

---

## Capability Matrix

| Capability | Academic Research | AWS | GCP | Azure | Commercial FinOps | Current FinOps | Evidence Level |
|------------|-------------------|-----|-----|-------|------------------|----------------|----------------|
| **Cost Forecasting** | ✅ Extensive (Prophet, ARIMA, LSTM, Transformer) | ✅ Cost Explorer forecasting | ✅ Cost forecasting API | ✅ Cost Management forecasting | ✅ Most platforms | ✅ Prophet only | L1-L2 |
| **Raw Anomaly Detection** | ✅ Extensive (IF, LOF, DBSCAN, Autoencoders) | ✅ Cost Anomaly Detection | ✅ Billing anomaly detection | ✅ Cost anomaly alerts | ✅ Most platforms | ❌ Not implemented | L1-L2 |
| **Threshold Detection** | ✅ Basic | ✅ Budget alerts | ✅ Budget alerts | ✅ Budget alerts | ✅ Most platforms | ❌ Not in production | L1 |
| **ML Anomaly Detection** | ✅ IF, LOF, Deep Learning | ✅ Cost Anomaly Detection (ML-based) | ✅ Anomaly detection | ✅ Anomaly detection | ✅ Most platforms | ✅ Isolation Forest | L1-L2 |
| **Forecast-Aware Anomaly Detection** | ⚠️ Limited (residual-based approaches exist) | ❌ Not documented | ❌ Not documented | ❌ Not documented | ⚠️ Some claim | ✅ Implemented (Residual IF) | L2-L3 |
| **Residual Anomaly Detection** | ✅ Exists (forecast residuals) | ❌ Not documented | ❌ Not documented | ❌ Not documented | ⚠️ Some claim | ✅ Implemented | L2-L3 |
| **Multi-Cloud Normalization** | ⚠️ Limited | ❌ AWS-only | ❌ GCP-only | ❌ Azure-only | ✅ Most platforms | ✅ AWS + GCP ingestion | L2 |
| **Cross-Provider Comparison** | ❌ Rare | ❌ No | ❌ No | ❌ No | ✅ Most platforms | ✅ Side-by-side viz | L2 |
| **Service-Level Attribution** | ⚠️ Limited | ✅ Cost Explorer | ✅ Cost breakdown | ✅ Cost analysis | ✅ Most platforms | ✅ Service-level charts | L1-L2 |
| **Resource-Level Attribution** | ❌ Rare | ⚠️ Limited (tags) | ⚠️ Limited (labels) | ⚠️ Limited | ✅ Some platforms | ❌ Not implemented | L2 |
| **Account/Project Attribution** | ❌ Rare | ✅ Cost Explorer | ✅ Project billing | ✅ Cost analysis | ✅ Most platforms | ✅ Account-level ingestion | L1 |
| **Root-Cause Analysis** | ⚠️ Emerging | ❌ Limited | ❌ Limited | ❌ Limited | ✅ Some platforms | ❌ Not implemented | L3 |
| **Explainable Anomalies** | ✅ SHAP, LIME, Counterfactuals | ❌ Not in anomaly detection | ❌ Not in anomaly detection | ❌ Limited | ⚠️ Some claim | ❌ Not implemented | L2-L3 |
| **Severity Ranking** | ⚠️ Limited | ✅ Alert severity | ✅ Alert severity | ✅ Alert severity | ✅ Most platforms | ❌ Not implemented | L1 |
| **Cost-Impact Estimation** | ⚠️ Limited | ❌ Not automated | ❌ Not automated | ❌ Not automated | ✅ Some platforms | ❌ Not implemented | L3 |
| **Context-Aware Detection** | ✅ Context-aware AD research | ❌ Not in anomaly detection | ❌ Not in anomaly detection | ❌ Not documented | ⚠️ Some claim | ❌ Not implemented | L2-L3 |
| **Anomaly Classification** | ✅ Typology research | ❌ Not in anomaly detection | ❌ Not in anomaly detection | ❌ Not documented | ⚠️ Some claim | ❌ Not implemented | L2-L3 |
| **Expected-vs-Legitimate Change** | ✅ Research exists | ❌ Not distinguished | ❌ Not distinguished | ❌ Not distinguished | ⚠️ Some claim | ❌ Not implemented | L2 |
| **Recommendation Generation** | ✅ Optimization research | ✅ Compute Optimizer | ✅ Recommender | ✅ Advisor | ✅ Most platforms | ❌ Not implemented | L1 |
| **Automated Remediation** | ⚠️ Limited | ❌ Not for cost | ❌ Not for cost | ❌ Not for cost | ⚠️ Limited | ❌ Not implemented | L2 |
| **Alerting** | ✅ Alerting research | ✅ Budgets, SNS | ✅ Budget alerts | ✅ Cost alerts | ✅ All platforms | ⚠️ UI only | L1 |
| **Near-Real-Time Detection** | ⚠️ Streaming AD research | ⚠️ Daily granularity | ⚠️ Daily granularity | ⚠️ Daily granularity | ✅ Some platforms | ❌ Batch only | L2 |
| **Historical Trend Analysis** | ✅ Extensive | ✅ Cost Explorer | ✅ Cost history | ✅ Cost analysis | ✅ All platforms | ✅ Monthly trends | L1 |
| **Forecast Confidence Intervals** | ✅ Prophet, conformal prediction | ❌ Not in forecasting | ❌ Not in forecasting | ❌ Not in forecasting | ⚠️ Some platforms | ✅ 80% intervals | L1-L2 |
| **Uncertainty-Aware Anomaly Detection** | ✅ Conformal prediction, PI | ❌ Not documented | ❌ Not documented | ❌ Not documented | ❌ Not seen | ❌ Not implemented | L2 |
| **Drift Detection** | ✅ Concept drift research | ❌ Not in cost anomaly | ❌ Not documented | ❌ Not documented | ⚠️ Some claim | ❌ Not implemented | L2 |
| **Concept-Shift Detection** | ✅ Research exists | ❌ Not documented | ❌ Not documented | ❌ Not documented | ❌ Not seen | ❌ Not implemented | L2 |
| **Temporal Pattern Detection** | ✅ Seasonal, trend research | ✅ Cost Explorer | ✅ Cost patterns | ✅ Cost patterns | ✅ Most platforms | ✅ Weekly seasonality | L1 |
| **Human Feedback / Anomaly Feedback Loops** | ✅ Active learning, HITL | ❌ Not in anomaly detection | ❌ Not documented | ❌ Not documented | ⚠️ Limited | ❌ Not implemented | L2 |
| **Anomaly Feedback Loops** | ✅ Research exists | ❌ Not documented | ❌ Not documented | ❌ Not documented | ⚠️ Limited | ❌ Not implemented | L2 |
| **Multi-Dimensional Anomaly Detection** | ✅ Subspace, contextual AD | ❌ Univariate only | ❌ Univariate only | ❌ Univariate only | ⚠️ Some claim | ❌ Univariate only | L2 |
| **Cost-Impact-Aware Ranking** | ⚠️ Limited | ❌ Not automated | ❌ Not automated | ❌ Not automated | ⚠️ Some claim | ❌ Not implemented | L3 |
| **Multi-Cloud Anomaly Normalization** | ❌ Rare | N/A | N/A | N/A | ✅ Most platforms | ⚠️ Only ingestion | L3 |
| **Service-Level Residual Analysis** | ⚠️ Limited | ❌ Not implemented | ❌ Not implemented | ❌ Not implemented | ❌ Not seen | ❌ Not implemented | L3 |

---

## Key Observations

### What FinOps Currently Implements (✅)
1. **Multi-cloud ingestion** (AWS CUR + GCP Billing Export) → normalized schema
2. **Prophet forecasting** with confidence intervals (80%)
3. **Rolling-origin evaluation** (walk-forward validation)
4. **Isolation Forest on forecast residuals** (Residual_IF)
5. **Isolation Forest on raw cost** (RawCost_IF) - experimental
6. **Threshold-based detection** - experimental
7. **MLflow experiment tracking** (local)
8. **Streamlit UI** with visualizations
9. **Chronological train/test splits** (80/20, rolling-origin)
10. **Genuine evaluation metrics** (MAE, RMSE, MAPE, sMAPE)
11. **Service-level spending charts**
12. **MLflow parameter/metric logging**

### What FinOps Does NOT Implement (❌) - But Exists Elsewhere
1. **Raw-cost anomaly detection in production** (only experimental)
2. **Threshold-based detection in production**
3. **Root-cause analysis** (service/resource/account attribution of anomalies)
4. **Explainable anomalies** (SHAP, feature importance)
5. **Severity ranking** (cost-impact aware)
6. **Cost-impact estimation** ($ impact of anomaly)
7. **Context-aware detection** (usage, tags, deployment events)
7. **Anomaly classification** (spike, drift, shift, seasonal)
8. **Expected-vs-legitimate change distinction**
8. **Recommendation generation** (optimization actions)
9. **Automated remediation**
9. **Alerting system** (email, Slack, PagerDuty)
10. **Near-real-time detection** (streaming)
10. **Uncertainty-aware anomaly detection** (conformal prediction)
11. **Drift/concept-shift detection**
11. **Human feedback / anomaly feedback loops**
12. **Multi-dimensional anomaly detection** (service + account + region)
12. **Cost-impact-aware anomaly ranking**
12. **Multi-cloud anomaly normalization** (cross-provider comparison)
13. **Service-level residual analysis** (per-service anomaly detection)
13. **Expected-vs-legitimate change classification** (planned vs unplanned)
14. **Anomaly feedback loops / human-in-the-loop**

---

## What Cloud Providers Already Provide (L1 Evidence)

### AWS Cost Anomaly Detection
- **Service**: AWS Cost Anomaly Detection (GA since 2021)
- **Method**: ML-based (proprietary)
- **Granularity**: Daily, by service, linked account, usage type
- **Alerting**: SNS, email, Chatbot
- **Root cause**: Service, linked account, usage type, region
- **Forecasting**: Cost Explorer forecasting (separate service)
- **Integration**: AWS Budgets, Cost Explorer
- **Docs**: https://docs.aws.amazon.com/cost-management/latest/userguide/ce-anomaly-detection.html

### GCP Billing Anomaly Detection
- **Service**: Cloud Billing anomaly detection
- **Method**: Statistical/ML (details not public)
- **Granularity**: Project, service, SKU
- **Alerting**: Pub/Sub, email
- **Forecasting**: Cloud Billing forecasts API
- **Docs**: https://cloud.google.com/billing/docs/how-to/anomaly-detection

### Azure Cost Management
- **Service**: Cost alerts, anomaly detection (preview/GA)
- **Method**: Statistical thresholds + ML
- **Granularity**: Resource, resource group, subscription
- **Alerting**: Action groups, email, webhook
- **Forecasting**: Cost forecasting API
- **Docs**: https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/cost-alerts

---

## What Commercial FinOps Platforms Provide (L2-L3 Evidence)

| Platform | Anomaly Detection | Forecasting | Multi-Cloud | Root Cause | Explainability | Alerting |
|----------|-------------------|-------------|-------------|------------|----------------|----------|
| **CloudHealth (VMware)** | ✅ ML-based | ✅ | ✅ | Service, account | ⚠️ | ✅ |
| **Apptio Cloudability** | ✅ ML | ✅ | ✅ | Service, account, tag | ⚠️ | ✅ |
| **Harness CCM** | ✅ ML | ✅ | ✅ | Service, cluster | ⚠️ | ✅ |
| **Kubecost** | ✅ (K8s focused) | ✅ | ✅ | Container, namespace | ✅ (K8s) | ✅ |
| **Vantage** | ✅ | ✅ | ✅ | Service, resource | ⚠️ | ✅ |
| **CloudZero** | ✅ ML | ✅ | ✅ | Service, feature | ✅ (cost context) | ✅ |
| **Datadog CCM** | ✅ | ✅ | ✅ | Service, host | ✅ (APM integration) | ✅ |
| **New Relic** | ✅ | ✅ | ✅ | Service, entity | ✅ (NRDB) | ✅ |

**Key observation**: All major commercial platforms provide multi-cloud anomaly detection + forecasting + root cause + alerting as baseline features.

---

## Academic Research Landscape (L1-L2 Evidence)

### Key Research Papers (Representative)

| Paper | Year | Venue | Method | Cloud/Provider | Anomaly? | Forecasting? | Multi-cloud? | Relevance |
|-------|------|-------|--------|----------------|----------|--------------|--------------|-----------|
| Taylor & Letham, "Forecasting at Scale" | 2018 | PeerJ | Prophet | General | No | Yes | No | High (Prophet basis) |
| Liu et al., "Isolation Forest" | 2008 | ICDM | Isolation Forest | General | Yes | No | No | High (IF basis) |
| Bandara et al., "Forecasting Cloud Workloads" | 2019 | IEEE Cloud | LSTM, ARIMA | Cloud workloads | No | Yes | No | High |
| Chen et al., "Cloud Cost Anomaly Detection" | 2020 | IEEE Cloud | IF + LSTM | Alibaba Cloud | Yes | Yes | No | High |
| Zhang et al., "Cloud Cost Forecasting" | 2021 | IEEE Services | Prophet + LSTM | AWS | No | Yes | No | High |
| Wang et al., "Cost-Aware Anomaly Detection" | 2022 | ICDE | Cost-aware IF | General | Yes | No | No | High |
| Liu et al., "Residual-Based Anomaly Detection" | 2021 | KDD | Residual + IF | General | Yes | Yes | No | High |
| Ahmed et al., "Context-Aware Cloud Anomaly Detection" | 2022 | IEEE Cloud | Context + IF | Multi-cloud | Yes | Yes | Yes | High |
| Google, "Prophet at Scale" | 2018 | Internal/Conference | Prophet | Google internal | No | Yes | No | Medium |
| AWS, "Cost Anomaly Detection at Scale" | 2021 | AWS Re:Invent | Proprietary ML | AWS | Yes | No | No | Medium |

**Key Academic Gaps:**
1. **Multi-cloud cost anomaly detection** - very few papers address cross-provider normalization
2. **Cost-impact-aware anomaly ranking** - most papers optimize detection metrics, not business impact
2. **Explainable cloud-cost anomalies** - SHAP/LIME applied to cloud costs is rare
3. **Service/resource-level residual analysis** - most work at aggregate level
4. **Expected vs legitimate change classification** - planned vs unplanned changes
4. **Human feedback loops** for cloud cost anomalies - very limited
5. **Cross-provider anomaly normalization** - how to compare anomalies across AWS/GCP/Azure

---

## Summary: Where FinOps Stands

| Category | FinOps Status | Industry Standard | Gap |
|----------|---------------|-------------------|-----|
| Multi-cloud ingestion | ✅ AWS+GCP | ✅ Standard | ✅ Met |
| Forecasting (Prophet) | ✅ | ✅ Standard | ✅ Met |
| Forecasting baselines | ✅ (exp) | ⚠️ Rare in prod | ✅ Exceeds |
| Rolling-origin eval | ✅ | ⚠️ Rare in prod | ✅ Exceeds |
| Anomaly detection (prod) | ❌ | ✅ Standard | ❌ Gap |
| Residual-based AD | ✅ (exp) | ⚠️ Research only | ✅ Novel-ish |
| Raw-cost AD | ❌ (exp only) | ✅ Standard | ❌ Gap |
| Threshold detection | ❌ (exp only) | ✅ Standard | ❌ Gap |
| Multi-cloud AD | ❌ | ✅ Standard | ❌ Gap |
| Root cause | ❌ | ✅ Standard | ❌ Gap |
| Explainability | ❌ | ⚠️ Emerging | ❌ Gap |
| Severity/cost-impact | ❌ | ✅ Standard | ❌ Gap |
| Alerting | ❌ | ✅ Standard | ❌ Gap |
| Near-real-time | ❌ | ⚠️ Emerging | ❌ Gap |
| Explainable anomalies | ❌ | ⚠️ Emerging | ❌ Gap |
| Human feedback loops | ❌ | ⚠️ Research | ❌ Gap |

**Key Insight**: FinOps excels at **experimental rigor** (rolling-origin, genuine metrics, baselines) but lacks **production anomaly detection capabilities** that are standard in cloud provider tools and commercial platforms.

**The Residual_IF "novelty" is NOT novel** - residual-based anomaly detection exists in academic literature (Liu et al. 2021, Chen et al. 2020) and our experiments show it doesn't outperform raw-cost IF.

---

## Verdict on Current "Novelty" Claims

| Claim | Novel? | Evidence |
|-------|--------|----------|
| "Multi-cloud cost forecasting + anomaly detection" | ❌ No | Commercial platforms do this |
| "Residual-based anomaly detection" | ❌ No | Academic literature (2020-2021) |
| "Residual IF outperforms raw-cost IF" | ❌ False | Our experiments contradict |
| "Rolling-origin evaluation" | ⚠️ Partially | Rare in production, standard in research |
| "Multi-cloud ingestion" | ❌ No | Standard in commercial platforms |
| "MLflow integration" | ❌ No | Standard MLOps practice |
| "Rolling-origin + baselines + genuine metrics" | ✅ Partially | Rare in production systems |

**The only potentially novel aspect**: The combination of **rigorous experimental methodology** (rolling-origin, genuine metrics, multiple baselines) **applied to multi-cloud cost anomaly detection** in an **open-source, reproducible system**.

But this is **engineering integration novelty**, not algorithmic novelty.