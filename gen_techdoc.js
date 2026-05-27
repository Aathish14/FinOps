const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Footer, Header
} = require('docx');
const fs = require('fs');

const BLUE = "1A3C5E";
const DARK_GREEN = "1E5631";
const MID_GREEN = "2D8A4E";
const LIGHT_GREEN = "E8F5ED";
const ACCENT_DARK = "0D3349";
const GRAY = "444444";
const LIGHT_GRAY = "F5F5F5";
const CODE_BG = "1E1E1E";
const BORDER_COLOR = "BBBBBB";

const border = { style: BorderStyle.SINGLE, size: 1, color: BORDER_COLOR };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: MID_GREEN, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: BLUE })]
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: MID_GREEN })]
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: GRAY })]
  });
}
function para(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22 })]
  });
}
function bullet(text, prefix = "") {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      ...(prefix ? [new TextRun({ text: prefix, font: "Arial", size: 22, bold: true })] : []),
      new TextRun({ text, font: "Arial", size: 22 })
    ]
  });
}
function code(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    shading: { fill: "EFEFEF", type: ShadingType.CLEAR },
    children: [new TextRun({ text, font: "Courier New", size: 18, color: "1A1A1A" })]
  });
}
function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}
function makeTable(headers, rows, colWidths) {
  const headerRow = new TableRow({
    children: headers.map((h, i) => new TableCell({
      borders, width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: h, font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })]
    }))
  });
  const dataRows = rows.map((row, ri) => new TableRow({
    children: row.map((cell, ci) => new TableCell({
      borders, width: { size: colWidths[ci], type: WidthType.DXA },
      shading: { fill: ri % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: cell, font: "Arial", size: 20 })] })]
    }))
  }));
  return new Table({
    width: { size: colWidths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: colWidths, rows: [headerRow, ...dataRows]
  });
}

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: "Arial", color: BLUE }, paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: "Arial", color: MID_GREEN }, paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: "Arial", color: GRAY }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_GREEN, space: 4 } },
        children: [new TextRun({ text: "Cloud Cost Forecasting Pipeline  |  Technical Design Document", font: "Arial", size: 18, color: GRAY })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 4 } },
        children: [
          new TextRun({ text: "INTERNAL — ENGINEERING USE ONLY  |  v1.0  |  Page ", font: "Arial", size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: GRAY }),
          new TextRun({ text: " of ", font: "Arial", size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: GRAY }),
        ]
      })] })
    },
    children: [
      // TITLE
      new Paragraph({ spacing: { before: 1440, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "TECHNICAL DESIGN DOCUMENT", font: "Arial", size: 48, bold: true, color: BLUE })] }),
      new Paragraph({ spacing: { before: 0, after: 100 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Cloud Cost Forecasting +", font: "Arial", size: 34, color: MID_GREEN })] }),
      new Paragraph({ spacing: { before: 0, after: 480 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Spend Anomaly Detection Pipeline", font: "Arial", size: 34, bold: true, color: MID_GREEN })] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [3120, 3120, 3120],
        rows: [new TableRow({ children: [
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_GREEN, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Document Type", font: "Arial", size: 20, bold: true, color: BLUE })] }), new Paragraph({ children: [new TextRun({ text: "Technical Design Doc", font: "Arial", size: 20 })] })] }),
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_GREEN, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Audience", font: "Arial", size: 20, bold: true, color: BLUE })] }), new Paragraph({ children: [new TextRun({ text: "ML + Platform Engineers", font: "Arial", size: 20 })] })] }),
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_GREEN, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Stack", font: "Arial", size: 20, bold: true, color: BLUE })] }), new Paragraph({ children: [new TextRun({ text: "Python / MLflow / Airflow", font: "Arial", size: 20 })] })] })
        ]})]
      }),
      spacer(), spacer(),

      // 1. SYSTEM OVERVIEW
      h1("1. System Overview"),
      para("The Cloud Cost Forecasting and Anomaly Detection Pipeline is a batch ML system that processes cloud billing export files daily, trains and evaluates time-series forecasting models, and applies anomaly detection algorithms to flag irregular spending patterns. The system is built on a modular pipeline architecture with distinct stages for ingestion, preprocessing, feature engineering, model training, inference, and alerting."),
      spacer(),
      h2("1.1 High-Level Architecture"),
      para("The pipeline consists of six loosely coupled stages orchestrated by Apache Airflow (or equivalent DAG scheduler). Each stage is independently deployable and communicates via structured file artifacts stored in a shared object store (S3-compatible)."),
      spacer(),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [1200, 2200, 2200, 3760],
        rows: [
          new TableRow({ children: [
            new TableCell({ borders, width: { size: 1200, type: WidthType.DXA }, shading: { fill: BLUE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Stage", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
            new TableCell({ borders, width: { size: 2200, type: WidthType.DXA }, shading: { fill: BLUE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Module", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
            new TableCell({ borders, width: { size: 2200, type: WidthType.DXA }, shading: { fill: BLUE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Input", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
            new TableCell({ borders, width: { size: 3760, type: WidthType.DXA }, shading: { fill: BLUE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Output", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] })
          ]}),
          ...[ ["01", "ingest", "Raw billing CSVs", "Validated Parquet partitioned by date/provider"],
               ["02", "preprocess", "Validated Parquet", "Normalized feature DataFrame (Parquet)"],
               ["03", "feature_eng", "Normalized DataFrame", "Feature matrix with lag features, rolling stats"],
               ["04", "train_eval", "Feature matrix", "Trained Prophet/ARIMA models, MLflow run IDs"],
               ["05", "infer_detect", "Trained models + new data", "Forecast CSV + anomaly flags JSON"],
               ["06", "alert_report", "Anomaly flags + forecast", "Slack alerts + weekly digest email"]
          ].map(([s, m, inp, out], ri) => new TableRow({
            children: [s, m, inp, out].map((cell, ci) => new TableCell({
              borders, width: { size: [1200,2200,2200,3760][ci], type: WidthType.DXA },
              shading: { fill: ri % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: cell, font: ci === 1 ? "Courier New" : "Arial", size: 20 })] })]
            }))
          }))
        ]
      }),

      spacer(),

      // 2. DATA LAYER
      h1("2. Data Layer"),
      h2("2.1 Input Data Sources"),
      h3("AWS Cost & Usage Report (CUR)"),
      bullet("Format: CSV or CSV.GZ, partitioned by billing period."),
      bullet("Key columns: bill/BillingPeriodStartDate, lineItem/ProductCode, lineItem/UsageAccountId, lineItem/UsageAmount, lineItem/UnblendedCost, lineItem/LineItemDescription, product/region."),
      bullet("Public sample available on Kaggle: aws-billing-data dataset (~2GB compressed)."),
      spacer(),
      h3("GCP Billing Export"),
      bullet("Format: CSV exported from BigQuery billing export table."),
      bullet("Key columns: usage_start_time, service.description, project.id, cost, usage.amount, usage.unit, labels."),
      bullet("Public sample: GCP Cloud Billing Export dataset on Kaggle."),

      spacer(),
      h2("2.2 Unified Billing Schema"),
      para("Both sources are normalized into the following schema after ingestion:"),
      spacer(),
      makeTable(
        ["Column", "Type", "Description", "Source Mapping"],
        [
          ["date", "DATE", "Usage date (UTC)", "AWS: UsageStartDate; GCP: usage_start_time::date"],
          ["cloud_provider", "VARCHAR(8)", "Provider identifier: AWS or GCP", "Inferred from file source"],
          ["service_name", "VARCHAR(128)", "Normalized service name", "AWS: ProductCode; GCP: service.description"],
          ["account_id", "VARCHAR(64)", "Account or project ID", "AWS: UsageAccountId; GCP: project.id"],
          ["region", "VARCHAR(64)", "Cloud region", "AWS: product/region; GCP: location.region"],
          ["environment", "VARCHAR(32)", "Env tag (prod/staging/dev)", "Derived from account tags"],
          ["cost_usd", "FLOAT64", "Total cost in USD", "AWS: UnblendedCost; GCP: cost"],
          ["usage_quantity", "FLOAT64", "Resource usage amount", "AWS: UsageAmount; GCP: usage.amount"],
          ["usage_unit", "VARCHAR(32)", "Unit of usage (GB-hrs, vCPU-hrs)", "AWS: UsageType; GCP: usage.unit"]
        ],
        [2000, 1400, 2600, 3360]
      ),

      spacer(),
      h2("2.3 Data Quality Checks"),
      para("The ingestion module runs the following validation gates before promoting data to the preprocessing stage:"),
      bullet("Schema completeness: all required columns present and correctly typed."),
      bullet("Date range validity: no future-dated records; no records older than 25 months."),
      bullet("Cost non-negativity: cost_usd must be >= 0 (negative values from credits are handled separately)."),
      bullet("Duplicate row detection: deduplication by [date, service_name, account_id, region] key."),
      bullet("Sparsity check: alert if any service has > 30% missing daily values over the trailing 30 days."),

      spacer(),

      // 3. FEATURE ENGINEERING
      h1("3. Feature Engineering"),
      h2("3.1 Time-Series Feature Set"),
      para("For each (service_name, account_id) grouping, the following features are derived on the daily cost_usd time series:"),
      makeTable(
        ["Feature", "Description", "Window"],
        [
          ["lag_1d", "Cost from previous day", "t-1"],
          ["lag_7d", "Cost from same day last week", "t-7"],
          ["lag_30d", "Cost from same day last month", "t-30"],
          ["rolling_mean_7d", "7-day rolling average cost", "t-7 to t-1"],
          ["rolling_std_7d", "7-day rolling standard deviation", "t-7 to t-1"],
          ["rolling_mean_30d", "30-day rolling average cost", "t-30 to t-1"],
          ["dow_encoding", "Day-of-week integer (0=Mon)", "current"],
          ["is_month_end", "Boolean flag for last 3 days of month", "current"],
          ["is_event_day", "Boolean flag from holiday/event calendar", "current"],
          ["cost_diff_1d", "Day-over-day cost delta", "t vs t-1"],
          ["cost_pct_change_7d", "7-day percentage change", "t vs t-7"]
        ],
        [2400, 4400, 2560]
      ),

      spacer(),

      // 4. FORECASTING MODELS
      h1("4. Forecasting Models"),
      h2("4.1 Prophet"),
      para("Facebook Prophet is the primary forecasting candidate due to its native support for weekly and annual seasonality, holiday effects, and changepoint detection — all highly relevant to cloud cost patterns (e.g., end-of-month billing cycles, quarterly capacity events)."),
      spacer(),
      h3("Key Configuration"),
      code("from prophet import Prophet"),
      code("model = Prophet("),
      code("    seasonality_mode='multiplicative',   # Cost spikes scale with baseline"),
      code("    changepoint_prior_scale=0.05,        # Controls trend flexibility"),
      code("    seasonality_prior_scale=10.0,        # Weekly seasonality strength"),
      code("    holidays=events_df,                  # Planned infrastructure events"),
      code("    interval_width=0.95                  # 95% prediction interval"),
      code(")"),
      code("model.add_seasonality(name='weekly', period=7, fourier_order=3)"),
      code("model.add_seasonality(name='monthly', period=30.5, fourier_order=5)"),

      spacer(),
      h2("4.2 ARIMA"),
      para("ARIMA serves as the secondary model and baseline comparator. The auto_arima function from pmdarima is used to identify optimal (p, d, q) parameters via AIC minimization on the training set."),
      spacer(),
      code("from pmdarima import auto_arima"),
      code("model = auto_arima("),
      code("    train_series,"),
      code("    start_p=1, max_p=5,"),
      code("    d=None,              # Auto-detect differencing order"),
      code("    start_q=1, max_q=5,"),
      code("    seasonal=True, m=7,  # Weekly seasonality"),
      code("    information_criterion='aic',"),
      code("    error_action='ignore', suppress_warnings=True"),
      code(")"),

      spacer(),
      h2("4.3 Model Selection & Evaluation"),
      para("Both models are trained on a rolling 80/20 train-validation split. The 20% validation window is always the most recent 4 weeks (temporal holdout — no random shuffling). Model selection is automated by comparing MAPE on the validation set."),
      spacer(),
      makeTable(
        ["Metric", "Formula", "Acceptable Threshold"],
        [
          ["MAPE", "mean(|actual - forecast| / actual) * 100", "< 10%"],
          ["RMSE", "sqrt(mean((actual - forecast)²))", "< 15% of mean daily spend"],
          ["MAE", "mean(|actual - forecast|)", "Informational"],
          ["Coverage", "% of actuals within 95% PI", "> 90%"]
        ],
        [1800, 4000, 3560]
      ),

      spacer(),

      // 5. ANOMALY DETECTION
      h1("5. Anomaly Detection — Isolation Forest"),
      h2("5.1 Approach"),
      para("Anomaly detection is applied to the residuals of the forecast — specifically the z-score normalized difference between actual spend and the point forecast. This residual-based approach ensures the Isolation Forest is detecting deviations relative to expected patterns, not absolute cost magnitudes."),
      spacer(),
      h3("Input Feature Vector for Isolation Forest"),
      bullet("forecast_residual: (actual_cost - forecast_cost) / forecast_std"),
      bullet("cost_pct_change_1d: day-over-day percentage change in actual cost"),
      bullet("rolling_z_score_7d: z-score of current cost vs 7-day rolling stats"),
      bullet("service_relative_change: cost change relative to same service 7 days ago"),
      bullet("account_relative_share: current service cost as % of total account daily cost"),

      spacer(),
      h3("Isolation Forest Configuration"),
      code("from sklearn.ensemble import IsolationForest"),
      code("iso_forest = IsolationForest("),
      code("    n_estimators=200,"),
      code("    contamination=0.03,    # Expect ~3% anomaly rate in billing data"),
      code("    max_features=1.0,"),
      code("    random_state=42,       # Deterministic for MLflow reproducibility"),
      code("    bootstrap=False"),
      code(")"),

      spacer(),
      h2("5.2 Anomaly Classification"),
      para("Detected anomalies are classified into categories for actionable alerting:"),
      makeTable(
        ["Anomaly Type", "Detection Signal", "Likely Cause"],
        [
          ["Spend Spike", "residual > +2σ, cost_pct_change_1d > +50%", "Orphaned resource, auto-scaling event, data job"],
          ["GPU Burst", "service=EC2/Compute Engine AND residual > +2σ", "Uncontrolled training job, mining, misconfigured spot"],
          ["Egress Burst", "service=Data Transfer AND anomaly_score < -0.3", "Data pipeline misconfiguration, public bucket access"],
          ["Storage Spike", "service=S3/GCS AND residual > +1.5σ", "Log accumulation, backup misconfiguration"],
          ["Spend Drop", "residual < -2σ", "Service outage, credential expiry, billing anomaly"]
        ],
        [2200, 3400, 3760]
      ),

      spacer(),

      // 6. MLFLOW INTEGRATION
      h1("6. MLflow Experiment Tracking"),
      h2("6.1 Experiment Structure"),
      para("MLflow experiments are organized by provider and service to allow per-service model comparison and promotion."),
      spacer(),
      code("Experiment naming: cloud_forecast_{provider}_{service}_{YYYYMMDD}"),
      code("Example:  cloud_forecast_aws_ec2_20240115"),
      code("          cloud_forecast_gcp_bigquery_20240115"),

      spacer(),
      h2("6.2 Logged Artifacts per Run"),
      makeTable(
        ["Artifact", "Type", "Description"],
        [
          ["params.model_type", "Parameter", "prophet or arima"],
          ["params.train_start / train_end", "Parameter", "Training data date range"],
          ["params.changepoint_prior_scale", "Parameter", "Prophet-specific tuning"],
          ["params.arima_order", "Parameter", "ARIMA (p,d,q) selected by auto_arima"],
          ["params.contamination", "Parameter", "Isolation Forest contamination value"],
          ["metrics.mape", "Metric", "Mean Absolute Percentage Error on validation"],
          ["metrics.rmse", "Metric", "Root Mean Squared Error on validation"],
          ["metrics.mae", "Metric", "Mean Absolute Error on validation"],
          ["metrics.false_positive_rate", "Metric", "Anomaly FPR on labeled events"],
          ["metrics.coverage_95", "Metric", "% of validation actuals inside 95% PI"],
          ["artifacts/model/", "Artifact", "Serialized model (Prophet JSON or ARIMA pickle)"],
          ["artifacts/forecast.csv", "Artifact", "7-day forward forecast with prediction intervals"],
          ["artifacts/validation_plot.png", "Artifact", "Forecast vs actual visualization"]
        ],
        [3200, 1600, 4560]
      ),

      spacer(),
      h2("6.3 Model Registry & Promotion"),
      code("import mlflow"),
      code("# Register model"),
      code("mlflow.register_model(f'runs:/{run_id}/model', f'forecast_{provider}_{service}')"),
      code(""),
      code("# Promote to Production if MAPE < threshold"),
      code("client = mlflow.tracking.MlflowClient()"),
      code("client.transition_model_version_stage("),
      code("    name=f'forecast_{provider}_{service}',"),
      code("    version=latest_version,"),
      code("    stage='Production'"),
      code(")"),

      spacer(),

      // 7. PIPELINE ORCHESTRATION
      h1("7. Pipeline Orchestration"),
      h2("7.1 Airflow DAG Structure"),
      code("cloud_cost_forecast_dag"),
      code("├── ingest_billing_csvs              # Ingest + validate AWS & GCP CSVs"),
      code("├── preprocess_and_normalize         # Schema unification, cleaning"),
      code("├── feature_engineering              # Lag features, rolling stats, events"),
      code("├── train_forecast_models            # Prophet + ARIMA per service group"),
      code("│   ├── train_prophet_<service>"),
      code("│   └── train_arima_<service>"),
      code("├── evaluate_and_select              # Compare MAPE, register best model"),
      code("├── run_inference                    # 7-day forecast + residual compute"),
      code("├── anomaly_detection                # Isolation Forest scoring"),
      code("└── alert_and_report                 # Slack, email digest, API publish"),

      spacer(),
      h2("7.2 Schedule & Triggers"),
      bullet("Daily run: 02:00 UTC — processes prior day's billing export, updates rolling forecast."),
      bullet("Weekly full retrain: Sunday 22:00 UTC — full model retrain with latest 90-day window."),
      bullet("On-demand trigger: REST API endpoint /api/v1/pipeline/trigger for ad-hoc retraining."),
      bullet("Backfill support: Airflow --start-date parameter for historical gap filling."),

      spacer(),

      // 8. DIRECTORY STRUCTURE
      h1("8. Repository Structure"),
      code("cloud-cost-forecasting/"),
      code("├── data/"),
      code("│   ├── raw/                  # Raw billing CSVs (git-ignored)"),
      code("│   ├── processed/            # Normalized Parquet files"),
      code("│   └── samples/              # Kaggle sample data for dev/testing"),
      code("├── src/"),
      code("│   ├── ingest/               # CSV readers, schema validators"),
      code("│   ├── preprocess/           # Normalization, dedup, quality checks"),
      code("│   ├── features/             # Feature engineering functions"),
      code("│   ├── models/"),
      code("│   │   ├── prophet_model.py  # Prophet training + evaluation"),
      code("│   │   ├── arima_model.py    # ARIMA training + evaluation"),
      code("│   │   └── model_selector.py # Auto-selection by MAPE"),
      code("│   ├── anomaly/"),
      code("│   │   ├── isolation_forest.py"),
      code("│   │   └── classifier.py     # Anomaly type classification"),
      code("│   ├── tracking/             # MLflow wrappers + registry utils"),
      code("│   ├── alerting/             # Slack, email, webhook clients"),
      code("│   └── api/                  # FastAPI REST endpoints"),
      code("├── dags/                     # Airflow DAG definitions"),
      code("├── tests/"),
      code("│   ├── unit/"),
      code("│   └── integration/"),
      code("├── notebooks/                # EDA, model exploration"),
      code("├── mlruns/                   # MLflow local tracking (dev)"),
      code("├── configs/"),
      code("│   ├── services.yaml         # Service groupings to model"),
      code("│   └── thresholds.yaml       # Anomaly alert thresholds"),
      code("├── Dockerfile"),
      code("├── docker-compose.yml"),
      code("└── requirements.txt"),

      spacer(),

      // 9. TECH STACK
      h1("9. Technology Stack"),
      makeTable(
        ["Layer", "Technology", "Version", "Purpose"],
        [
          ["Language", "Python", "3.11+", "All pipeline components"],
          ["Forecasting", "Prophet (neuralprophet)", "1.1.x", "Primary time-series model"],
          ["Forecasting", "pmdarima (auto_arima)", "2.0.x", "ARIMA candidate model"],
          ["Anomaly Detection", "scikit-learn", "1.4+", "IsolationForest implementation"],
          ["Experiment Tracking", "MLflow", "2.10+", "Run tracking, model registry"],
          ["Orchestration", "Apache Airflow", "2.8+", "DAG scheduling"],
          ["Data Processing", "Pandas / PyArrow", "2.x / 15.x", "DataFrame operations, Parquet I/O"],
          ["API Layer", "FastAPI", "0.110+", "Forecast + anomaly REST API"],
          ["Alerting", "slack_sdk / smtplib", "Latest", "Slack and email alerts"],
          ["Object Store", "MinIO (local) / S3", "—", "Artifact and data storage"],
          ["Containerization", "Docker + Compose", "24+", "Local dev + CI environments"]
        ],
        [1800, 2400, 1400, 3760]
      ),

      spacer(),

      // 10. TESTING STRATEGY
      h1("10. Testing Strategy"),
      h2("10.1 Unit Tests"),
      bullet("Schema validation: assert normalized output matches unified billing schema for both AWS and GCP inputs."),
      bullet("Feature engineering: verify lag features, rolling stats, and event flags produce correct values on synthetic time series."),
      bullet("Model training: smoke test with 90-day synthetic series; assert MAPE is computed and logged without error."),
      bullet("Isolation Forest: assert contamination ratio matches expected flag rate on controlled spike injection."),

      spacer(),
      h2("10.2 Integration Tests"),
      bullet("End-to-end pipeline test with Kaggle sample data: assert forecast CSV and anomaly flags JSON are produced in < 15 minutes."),
      bullet("MLflow logging: assert all parameters, metrics, and artifacts are present after a training run."),
      bullet("Alert routing: mock Slack webhook and assert anomaly events trigger correctly formatted messages."),

      spacer(),
      h2("10.3 Model Evaluation Tests"),
      bullet("Backtesting: walk-forward validation over 12-week historical window; assert average MAPE < 10%."),
      bullet("Anomaly precision: inject synthetic spikes into validation data; assert Isolation Forest flags ≥ 85% with ≤ 5% FPR."),

      spacer()
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/mnt/user-data/outputs/TechDoc_CloudCostForecasting.docx", buf);
  console.log("TechDoc created");
});
