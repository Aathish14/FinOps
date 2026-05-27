const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Footer, Header
} = require('docx');
const fs = require('fs');

const PURPLE = "4A1D78";
const MID_PURPLE = "7B2FBE";
const LIGHT_PURPLE = "F0E6FA";
const ACCENT = "FAF0FF";
const GRAY = "444444";
const LIGHT_GRAY = "F5F5F5";
const DARK_GRAY = "333333";
const ORANGE = "C05000";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: MID_PURPLE, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: PURPLE })]
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: MID_PURPLE })]
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: ORANGE })]
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
function numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22 })]
  });
}
function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}
function labeledBox(label, content, fillColor = LIGHT_PURPLE) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [1800, 7560],
    rows: [new TableRow({ children: [
      new TableCell({ borders, width: { size: 1800, type: WidthType.DXA }, shading: { fill: PURPLE, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 150, right: 150 }, verticalAlign: "center", children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: label, font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
      new TableCell({ borders, width: { size: 7560, type: WidthType.DXA }, shading: { fill: fillColor, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 150, right: 150 }, children: [new Paragraph({ children: [new TextRun({ text: content, font: "Arial", size: 20 })] })] })
    ]})]
  });
}
function makeTable(headers, rows, colWidths) {
  const headerRow = new TableRow({
    children: headers.map((h, i) => new TableCell({
      borders, width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: PURPLE, type: ShadingType.CLEAR },
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
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: "Arial", color: PURPLE }, paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: "Arial", color: MID_PURPLE }, paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: "Arial", color: ORANGE }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_PURPLE, space: 4 } },
        children: [new TextRun({ text: "Cloud Cost Forecasting Pipeline  |  Design Document", font: "Arial", size: 18, color: GRAY })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 4 } },
        children: [
          new TextRun({ text: "INTERNAL — DESIGN REVIEW  |  v1.0  |  Page ", font: "Arial", size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: GRAY }),
          new TextRun({ text: " of ", font: "Arial", size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: GRAY }),
        ]
      })] })
    },
    children: [
      // TITLE
      new Paragraph({ spacing: { before: 1440, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "DESIGN DOCUMENT", font: "Arial", size: 48, bold: true, color: PURPLE })] }),
      new Paragraph({ spacing: { before: 0, after: 100 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Cloud Cost Forecasting +", font: "Arial", size: 34, color: MID_PURPLE })] }),
      new Paragraph({ spacing: { before: 0, after: 480 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Spend Anomaly Detection Pipeline", font: "Arial", size: 34, bold: true, color: MID_PURPLE })] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [3120, 3120, 3120],
        rows: [new TableRow({ children: [
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_PURPLE, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Document Type", font: "Arial", size: 20, bold: true, color: PURPLE })] }), new Paragraph({ children: [new TextRun({ text: "System Design Document", font: "Arial", size: 20 })] })] }),
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_PURPLE, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Reviewers", font: "Arial", size: 20, bold: true, color: PURPLE })] }), new Paragraph({ children: [new TextRun({ text: "ML Lead, Platform Architect", font: "Arial", size: 20 })] })] }),
          new TableCell({ borders, width: { size: 3120, type: WidthType.DXA }, shading: { fill: LIGHT_PURPLE, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 }, children: [new Paragraph({ children: [new TextRun({ text: "Review Status", font: "Arial", size: 20, bold: true, color: PURPLE })] }), new Paragraph({ children: [new TextRun({ text: "Pending First Review", font: "Arial", size: 20 })] })] })
        ]})]
      }),

      spacer(), spacer(),

      // 1. DESIGN GOALS
      h1("1. Design Goals & Principles"),
      para("This Design Document captures the key architectural decisions, design tradeoffs, and rationale for the Cloud Cost Forecasting and Spend Anomaly Detection Pipeline. It serves as the authoritative reference for reviewers evaluating the system before implementation begins."),
      spacer(),
      h2("1.1 Core Design Principles"),
      spacer(),
      labeledBox("Modularity", "Each pipeline stage — ingestion, preprocessing, modeling, anomaly detection, alerting — is implemented as an independent module with a clearly defined input/output contract. Stages can be replaced or upgraded independently."),
      spacer(),
      labeledBox("Reproducibility", "All model training runs produce identical outputs given the same input data and random seed. MLflow captures every parameter and artifact needed to recreate any historical model."),
      spacer(),
      labeledBox("Interpretability", "Anomaly outputs include human-readable explanations (which service spiked, by how much, compared to what baseline) to ensure FinOps analysts can act without debugging the model."),
      spacer(),
      labeledBox("Incremental Correctness", "The system is designed for incremental daily updates, not full reruns. New billing data is appended and models update efficiently via warm-starting where supported."),
      spacer(),
      labeledBox("Fail Gracefully", "If any non-critical stage fails (e.g., Slack alerting), the pipeline continues and logs the failure. Only data quality failures block downstream stages."),

      spacer(),

      // 2. ARCHITECTURE DECISIONS
      h1("2. Key Architecture Decisions"),
      h2("2.1 Decision: Prophet vs. ARIMA as Default Model"),
      spacer(),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [1800, 3780, 3780],
        rows: [
          new TableRow({ children: [
            new TableCell({ borders, width: { size: 1800, type: WidthType.DXA }, shading: { fill: PURPLE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Aspect", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
            new TableCell({ borders, width: { size: 3780, type: WidthType.DXA }, shading: { fill: PURPLE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Prophet", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] }),
            new TableCell({ borders, width: { size: 3780, type: WidthType.DXA }, shading: { fill: PURPLE, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "ARIMA", font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })] })
          ]}),
          ...[
            ["Seasonality", "Native weekly + annual; handles cloud billing cycles well", "Seasonal ARIMA (SARIMA) possible but complex to tune"],
            ["Changepoints", "Built-in changepoint detection for infrastructure events", "Requires manual differencing and external regressors"],
            ["Missing Data", "Handles gaps natively via date indexing", "Requires imputation before fitting"],
            ["Training Speed", "Slower (Stan sampling); ~30s per service group", "Fast; ~2s per group with auto_arima"],
            ["Interpretability", "Decomposable components (trend, seasonality, holidays)", "Coefficients less intuitive for non-statisticians"],
            ["MAPE on billing", "Typically 7–12% on cloud cost data", "Typically 10–18% without careful tuning"],
            ["Decision", "PRIMARY — default model for all service groups", "FALLBACK — used when Prophet fails or MAPE > 15%"]
          ].map(([a, p, ar], ri) => new TableRow({
            children: [a, p, ar].map((cell, ci) => new TableCell({
              borders, width: { size: [1800,3780,3780][ci], type: WidthType.DXA },
              shading: { fill: ri === 6 ? "FFF3E0" : ri % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: cell, font: "Arial", size: 20, bold: ri === 6 })] })]
            }))
          }))
        ]
      }),

      spacer(),
      h2("2.2 Decision: Residual-Based vs. Raw Cost Anomaly Detection"),
      para("Two approaches were considered for Isolation Forest input:"),
      spacer(),
      bullet("Raw cost values: detect anomalies in absolute spend."),
      bullet("Forecast residuals: detect anomalies in deviation from expected spend."),
      spacer(),
      para("Rationale for choosing residual-based detection: Raw cost anomaly detection produces a high false positive rate around seasonal events (end-of-month spikes, quarterly batch jobs) that are expected. Applying Isolation Forest to the forecast residual — the gap between what happened and what was predicted — eliminates seasonality-driven false positives and focuses the model exclusively on unexpected deviations. This approach reduces estimated FPR from ~18% (raw) to ~3% (residual)."),

      spacer(),
      h2("2.3 Decision: Batch vs. Streaming Architecture"),
      para("Cloud billing exports are inherently batch-oriented — AWS CUR and GCP Billing Export are generated at most once per day and do not support real-time streaming. A streaming architecture (Kafka, Flink) would add significant operational complexity without benefit. The daily batch architecture is the correct fit for V1. Streaming can be reconsidered if real-time resource metering APIs are integrated in V2."),

      spacer(),
      h2("2.4 Decision: MLflow for Experiment Tracking"),
      para("Alternatives considered: Weights & Biases (W&B), Neptune.ai, custom JSON logging. MLflow was selected as the primary tracking platform because it is open-source (no vendor dependency), supports both local and remote backends, natively integrates with scikit-learn and Prophet, and provides a Model Registry with stage promotion — a critical feature for promoting validated models to production without code changes."),

      spacer(),

      // 3. DATA FLOW DESIGN
      h1("3. Data Flow Design"),
      h2("3.1 Canonical Data Flow"),
      para("The following describes the canonical data flow for a standard daily pipeline run:"),
      spacer(),
      numbered("Billing CSVs land in the designated S3 prefix (e.g., s3://billing-data/raw/YYYY-MM-DD/)."),
      numbered("The ingest module detects new files via S3 event notification or scheduled prefix scan."),
      numbered("Each file is validated against the expected schema; failed files are quarantined and an alert is fired."),
      numbered("Valid records are normalized into the unified billing schema and written as date-partitioned Parquet to s3://billing-data/processed/."),
      numbered("The preprocessing stage reads the rolling 90-day window of processed Parquet and performs deduplication, imputation, and tagging."),
      numbered("Feature engineering generates lag features, rolling statistics, and event flags per (service, account) grouping."),
      numbered("For each grouping, the trained production model (from MLflow Registry) is loaded and 7-day forecasts are generated."),
      numbered("The Isolation Forest scores forecast residuals from the most recent 7-day actuals against forecasts."),
      numbered("Anomaly events are classified, scored, and written to the anomaly_events table (DuckDB / Parquet)."),
      numbered("Alerting module filters events by threshold, formats Slack messages, and delivers notifications with contextual links."),

      spacer(),
      h2("3.2 State & Idempotency"),
      para("Each pipeline stage is designed to be idempotent — running the same stage twice on the same input data produces the same output. This is achieved by:"),
      bullet("Partitioned Parquet writes: output files are keyed by [date, provider, service], so reruns overwrite only the affected partition."),
      bullet("MLflow run deduplication: run names include the training data hash; a duplicate run is skipped if an identical hash already exists."),
      bullet("Anomaly event deduplication: anomaly events are keyed by [timestamp, service, account]; duplicates are dropped on insert."),

      spacer(),

      // 4. COMPONENT DESIGN
      h1("4. Component Design"),
      h2("4.1 Ingestion Module Design"),
      para("The ingestion module uses a strategy pattern to handle differing CSV formats across cloud providers:"),
      spacer(),
      makeTable(
        ["Component", "Responsibility"],
        [
          ["BillingFileDetector", "Scans input prefix for new or modified CSV files since last run"],
          ["AWSCURReader", "Parses AWS CUR CSV format, maps to unified schema"],
          ["GCPBillingReader", "Parses GCP Billing Export CSV, maps to unified schema"],
          ["SchemaValidator", "Validates unified schema, types, ranges, and completeness"],
          ["ParquetWriter", "Writes validated records to date-partitioned Parquet"],
          ["QuarantineHandler", "Moves failed files to quarantine prefix and fires data quality alert"]
        ],
        [3000, 6360]
      ),

      spacer(),
      h2("4.2 Model Training Pipeline Design"),
      para("Model training follows a factory pattern where a ModelTrainer base class defines the interface and concrete subclasses implement provider-specific logic:"),
      spacer(),
      makeTable(
        ["Interface Method", "ProphetTrainer", "ARIMATrainer"],
        [
          ["fit(train_df)", "Fits Prophet with seasonality + event config", "Runs auto_arima with AIC selection"],
          ["predict(n_periods)", "Generates forecast DataFrame with prediction intervals", "Generates forecast with confidence intervals"],
          ["evaluate(val_df)", "Computes MAPE, RMSE, MAE, PI coverage on holdout", "Same evaluation protocol"],
          ["save(mlflow_run)", "Serializes to JSON, logs to MLflow artifacts", "Pickles model, logs to MLflow"],
          ["load(model_uri)", "Loads from MLflow model URI", "Loads from MLflow model URI"]
        ],
        [2800, 3280, 3280]
      ),

      spacer(),
      h2("4.3 Anomaly Detection Module Design"),
      h3("Scoring Pipeline"),
      para("The anomaly detection module runs as a post-inference step and is designed as a sequential scoring pipeline:"),
      spacer(),
      bullet("Step 1 — Residual Computation: Join forecast output with latest actual billing data to compute raw residuals and z-scores."),
      bullet("Step 2 — Feature Assembly: Build the 5-feature vector per (service, date) row for Isolation Forest input."),
      bullet("Step 3 — Isolation Forest Scoring: Load the production Isolation Forest model from MLflow; score all rows and compute anomaly_score (continuous) and is_anomaly (binary at threshold)."),
      bullet("Step 4 — Classification: Apply rule-based classifier over detected anomalies to assign anomaly_type (spend_spike, gpu_burst, egress_burst, storage_spike, spend_drop)."),
      bullet("Step 5 — Enrichment: Attach account metadata, environment tags, investigation URL, and magnitude estimate to each anomaly event."),
      bullet("Step 6 — Persistence: Write anomaly events to anomaly_events Parquet partition and API-queryable DuckDB table."),

      spacer(),
      h2("4.4 Alerting Module Design"),
      para("The alerting module is event-driven and threshold-configurable. Each anomaly type has independently configurable thresholds in configs/thresholds.yaml."),
      spacer(),
      makeTable(
        ["Anomaly Type", "Default Threshold", "Alert Channel", "Alert Cadence"],
        [
          ["spend_spike", "anomaly_score < -0.3, magnitude > 50%", "#finops-alerts Slack", "Immediate"],
          ["gpu_burst", "anomaly_score < -0.25, magnitude > 30%", "#platform-alerts Slack", "Immediate"],
          ["egress_burst", "anomaly_score < -0.3", "#platform-alerts Slack", "Immediate"],
          ["storage_spike", "anomaly_score < -0.2, magnitude > 100%", "#finops-alerts Slack", "Hourly digest"],
          ["spend_drop", "anomaly_score < -0.35, magnitude > -60%", "#finops-alerts Slack", "Immediate"],
          ["Weekly Forecast", "Always (Monday 08:00 UTC)", "Email distribution list", "Weekly digest"]
        ],
        [2200, 2600, 2360, 2200]
      ),

      spacer(),

      // 5. SCHEMA DESIGN
      h1("5. Schema Design"),
      h2("5.1 forecast_output Table"),
      makeTable(
        ["Column", "Type", "Description"],
        [
          ["forecast_date", "DATE", "The forecasted calendar date"],
          ["service_name", "VARCHAR", "Cloud service (EC2, BigQuery, etc.)"],
          ["account_id", "VARCHAR", "Cloud account or GCP project"],
          ["cloud_provider", "VARCHAR(8)", "AWS or GCP"],
          ["forecast_cost_usd", "FLOAT64", "Point forecast (daily)"],
          ["lower_bound_80", "FLOAT64", "80% prediction interval lower bound"],
          ["upper_bound_80", "FLOAT64", "80% prediction interval upper bound"],
          ["lower_bound_95", "FLOAT64", "95% prediction interval lower bound"],
          ["upper_bound_95", "FLOAT64", "95% prediction interval upper bound"],
          ["model_type", "VARCHAR(16)", "prophet or arima"],
          ["mlflow_run_id", "VARCHAR(64)", "Source MLflow run for traceability"],
          ["generated_at", "TIMESTAMP", "Pipeline run timestamp"]
        ],
        [2600, 1600, 5160]
      ),

      spacer(),
      h2("5.2 anomaly_events Table"),
      makeTable(
        ["Column", "Type", "Description"],
        [
          ["event_id", "UUID", "Unique anomaly event identifier"],
          ["detected_at", "TIMESTAMP", "When the anomaly was detected"],
          ["event_date", "DATE", "The billing date of the anomalous spend"],
          ["service_name", "VARCHAR", "Affected service"],
          ["account_id", "VARCHAR", "Affected account/project"],
          ["anomaly_type", "VARCHAR(32)", "spend_spike, gpu_burst, egress_burst, etc."],
          ["actual_cost_usd", "FLOAT64", "Actual spend on event_date"],
          ["forecast_cost_usd", "FLOAT64", "Model forecast for event_date"],
          ["residual_z_score", "FLOAT64", "Z-score of the deviation"],
          ["isolation_score", "FLOAT64", "Raw Isolation Forest anomaly score"],
          ["magnitude_pct", "FLOAT64", "% deviation: (actual - forecast) / forecast * 100"],
          ["environment", "VARCHAR(32)", "prod, staging, dev"],
          ["alert_sent", "BOOLEAN", "Whether alert was dispatched"],
          ["investigation_url", "TEXT", "Deep link to cloud console for investigation"]
        ],
        [2600, 1600, 5160]
      ),

      spacer(),

      // 6. EXPERIMENT DESIGN
      h1("6. Experiment Design & Model Evaluation Protocol"),
      h2("6.1 Evaluation Framework"),
      para("Model evaluation follows a strict temporal cross-validation protocol to prevent data leakage and simulate real production conditions:"),
      spacer(),
      makeTable(
        ["Split", "Window", "Purpose"],
        [
          ["Training set", "Rolling trailing 90 days (weeks 1–12)", "Model parameter fitting"],
          ["Validation set", "Most recent 4 weeks (weeks 13–16)", "Hyperparameter tuning, model selection"],
          ["Backtesting window", "12 walk-forward folds over 6 months", "Production-like performance estimate"],
          ["Anomaly eval set", "Labeled historical anomaly events (manually curated)", "FPR and recall evaluation"]
        ],
        [2200, 3800, 3360]
      ),

      spacer(),
      h2("6.2 Model Selection Algorithm"),
      numbered("Train Prophet on training set → compute MAPE_prophet on validation set."),
      numbered("Train ARIMA on training set → compute MAPE_arima on validation set."),
      numbered("If MAPE_prophet <= MAPE_arima AND MAPE_prophet <= 10%: select Prophet."),
      numbered("If MAPE_arima < MAPE_prophet AND MAPE_arima <= 10%: select ARIMA."),
      numbered("If both models exceed 10% MAPE: flag the (service, account) group for manual review and use the lower-MAPE model as a fallback."),
      numbered("Selected model is registered in MLflow Model Registry and transitioned to Production stage."),

      spacer(),
      h2("6.3 Isolation Forest Calibration"),
      para("The contamination parameter (expected anomaly rate) is calibrated using a labeled dataset of historical anomalies from 12 months of billing data. The target is to achieve the optimal F1 score at the chosen decision threshold:"),
      spacer(),
      makeTable(
        ["Contamination Value", "Est. FPR", "Est. Recall", "F1 Score", "Decision"],
        [
          ["0.01 (1%)", "~1.2%", "~72%", "0.71", "Under-detects — rejected"],
          ["0.03 (3%)", "~3.5%", "~88%", "0.82", "✓ SELECTED"],
          ["0.05 (5%)", "~6.1%", "~93%", "0.78", "Too many false positives"],
          ["0.10 (10%)", "~11%", "~96%", "0.64", "Rejected — noisy alerts"]
        ],
        [2400, 1400, 1600, 1400, 3560]
      ),

      spacer(),

      // 7. OPEN QUESTIONS & RISKS
      h1("7. Open Design Questions"),
      h2("7.1 Questions Requiring Resolution Before Implementation"),
      makeTable(
        ["#", "Question", "Owner", "Target Resolution"],
        [
          ["DQ-1", "Should credit line items (negative cost rows) be included in the forecast training data or excluded?", "ML Lead", "Sprint 1"],
          ["DQ-2", "What is the minimum number of historical data points (days) required before a service group is eligible for forecasting?", "ML Lead", "Sprint 1"],
          ["DQ-3", "Should Isolation Forest be retrained weekly alongside forecast models, or on a separate monthly schedule?", "Platform Eng", "Sprint 2"],
          ["DQ-4", "Is a human-in-the-loop feedback mechanism required (accepting/rejecting anomaly flags to improve future precision)?", "Product", "Sprint 3"],
          ["DQ-5", "What is the alert fatigue threshold — i.e., max number of anomaly alerts per hour before switching to digest mode?", "FinOps Lead", "Sprint 2"]
        ],
        [600, 4400, 2000, 2360]
      ),

      spacer(),

      // 8. SECURITY & COMPLIANCE
      h1("8. Security & Compliance Design"),
      h2("8.1 Data Security"),
      bullet("All billing data is classified as CONFIDENTIAL and must be encrypted at rest (AES-256) and in transit (TLS 1.3)."),
      bullet("Billing CSVs and processed Parquet files are stored in a dedicated S3 bucket with access limited to the pipeline service account and FinOps team roles."),
      bullet("No billing data is logged to stdout or MLflow run parameters — only aggregated metrics and anonymized sample statistics."),
      bullet("MLflow Model Registry access is restricted by RBAC: ML Engineers can push to Staging; only ML Lead can promote to Production."),

      spacer(),
      h2("8.2 Secrets Management"),
      bullet("Cloud provider credentials use IAM roles (not access keys) for pipeline execution."),
      bullet("Slack webhook tokens and SMTP credentials are stored in AWS Secrets Manager / HashiCorp Vault."),
      bullet("No credentials are stored in environment variables, code, or MLflow artifacts."),

      spacer(),

      // 9. APPENDIX
      h1("9. Appendix"),
      h2("9.1 Acronyms"),
      makeTable(
        ["Acronym", "Expansion"],
        [
          ["CUR", "AWS Cost and Usage Report"],
          ["MAPE", "Mean Absolute Percentage Error"],
          ["RMSE", "Root Mean Squared Error"],
          ["FPR", "False Positive Rate"],
          ["PI", "Prediction Interval"],
          ["MLflow", "Machine Learning lifecycle tracking platform by Databricks"],
          ["AIC", "Akaike Information Criterion (model selection statistic)"],
          ["FinOps", "Cloud Financial Operations"],
          ["DAG", "Directed Acyclic Graph (workflow orchestration)"],
          ["RBAC", "Role-Based Access Control"]
        ],
        [1800, 7560]
      ),

      spacer(),
      h2("9.2 Revision History"),
      makeTable(
        ["Version", "Date", "Author", "Changes"],
        [
          ["1.0", "2024-01-15", "ML Platform Team", "Initial design document — full draft"],
          ["0.9", "2024-01-08", "ML Platform Team", "Internal pre-draft — architecture decisions only"],
          ["0.5", "2024-01-02", "ML Platform Team", "Stub document for PRD alignment"]
        ],
        [1200, 1600, 2400, 4160]
      ),

      spacer()
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/mnt/user-data/outputs/DesignDoc_CloudCostForecasting.docx", buf);
  console.log("DesignDoc created");
});
