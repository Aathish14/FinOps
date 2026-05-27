const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Footer, Header
} = require('docx');
const fs = require('fs');

const BLUE = "1F4E79";
const LIGHT_BLUE = "D6E4F0";
const MID_BLUE = "2E75B6";
const ACCENT = "E8F4FD";
const GRAY = "595959";
const LIGHT_GRAY = "F2F2F2";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLUE, space: 4 } },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: BLUE })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: MID_BLUE })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 180, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: GRAY })]
  });
}

function para(text, options = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: "000000", ...options })]
  });
}

function bullet(text, bold_prefix = "") {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      ...(bold_prefix ? [new TextRun({ text: bold_prefix, font: "Arial", size: 22, bold: true })] : []),
      new TextRun({ text, font: "Arial", size: 22 })
    ]
  });
}

function spacer() {
  return new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun("")] });
}

function infoBox(label, value, fillColor = ACCENT) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2000, 7360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 2000, type: WidthType.DXA },
            shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: label, font: "Arial", size: 20, bold: true, color: BLUE })] })]
          }),
          new TableCell({
            borders,
            width: { size: 7360, type: WidthType.DXA },
            shading: { fill: fillColor, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: value, font: "Arial", size: 20 })] })]
          })
        ]
      })
    ]
  });
}

function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    children: headers.map((h, i) => new TableCell({
      borders,
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: h, font: "Arial", size: 20, bold: true, color: "FFFFFF" })] })]
    }))
  });

  const dataRows = rows.map((row, ri) => new TableRow({
    children: row.map((cell, ci) => new TableCell({
      borders,
      width: { size: colWidths[ci], type: WidthType.DXA },
      shading: { fill: ri % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: cell, font: "Arial", size: 20 })] })]
    }))
  }));

  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows]
  });
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      },
      {
        reference: "numbers",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: MID_BLUE },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: GRAY },
        paragraph: { spacing: { before: 180, after: 60 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: MID_BLUE, space: 4 } },
            children: [
              new TextRun({ text: "Cloud Cost Forecasting + Spend Anomaly Detection Pipeline", font: "Arial", size: 18, color: GRAY }),
              new TextRun({ text: "   |   Product Requirements Document", font: "Arial", size: 18, color: MID_BLUE })
            ]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 4 } },
            children: [
              new TextRun({ text: "CONFIDENTIAL  |  Version 1.0  |  Page ", font: "Arial", size: 18, color: GRAY }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: GRAY }),
              new TextRun({ text: " of ", font: "Arial", size: 18, color: GRAY }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: GRAY }),
            ]
          })
        ]
      })
    },
    children: [
      // TITLE PAGE
      new Paragraph({ spacing: { before: 1440, after: 240 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "PRODUCT REQUIREMENTS DOCUMENT", font: "Arial", size: 48, bold: true, color: BLUE })] }),
      new Paragraph({ spacing: { before: 0, after: 120 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Cloud Cost Forecasting +", font: "Arial", size: 36, color: MID_BLUE })] }),
      new Paragraph({ spacing: { before: 0, after: 480 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Spend Anomaly Detection Pipeline", font: "Arial", size: 36, bold: true, color: MID_BLUE })] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ children: [
            new TableCell({ borders, width: { size: 4680, type: WidthType.DXA }, shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 },
              children: [new Paragraph({ children: [new TextRun({ text: "Document Version", font: "Arial", size: 20, bold: true, color: BLUE })] }),
                         new Paragraph({ children: [new TextRun({ text: "1.0 — Initial Release", font: "Arial", size: 20 })] })] }),
            new TableCell({ borders, width: { size: 4680, type: WidthType.DXA }, shading: { fill: ACCENT, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 },
              children: [new Paragraph({ children: [new TextRun({ text: "Status", font: "Arial", size: 20, bold: true, color: BLUE })] }),
                         new Paragraph({ children: [new TextRun({ text: "Draft — In Review", font: "Arial", size: 20 })] })] })
          ]}),
          new TableRow({ children: [
            new TableCell({ borders, width: { size: 4680, type: WidthType.DXA }, shading: { fill: LIGHT_GRAY, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 },
              children: [new Paragraph({ children: [new TextRun({ text: "Domain", font: "Arial", size: 20, bold: true, color: BLUE })] }),
                         new Paragraph({ children: [new TextRun({ text: "FinOps / MLOps / Cloud Infrastructure", font: "Arial", size: 20 })] })] }),
            new TableCell({ borders, width: { size: 4680, type: WidthType.DXA }, shading: { fill: LIGHT_GRAY, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 },
              children: [new Paragraph({ children: [new TextRun({ text: "Target Teams", font: "Arial", size: 20, bold: true, color: BLUE })] }),
                         new Paragraph({ children: [new TextRun({ text: "Platform Engineering, FinOps, Data Science", font: "Arial", size: 20 })] })] })
          ]})
        ]
      }),

      spacer(), spacer(),

      // 1. EXECUTIVE SUMMARY
      h1("1. Executive Summary"),
      para("Cloud infrastructure spend has become one of the largest and fastest-growing cost centers for engineering organizations. Without visibility into spending patterns and early warning signals for anomalies, engineering teams face bill shock, budget overruns, and reactive cost management. This document defines the requirements for a Cloud Cost Forecasting and Spend Anomaly Detection Pipeline — a production-grade ML system that proactively forecasts next-week cloud spend and automatically flags abnormal usage patterns across AWS and GCP environments."),
      spacer(),
      para("The system ingests raw billing CSV exports, applies time-series forecasting models (Prophet / ARIMA), layers anomaly detection (Isolation Forest) on top of forecasted values, and surfaces actionable alerts to FinOps and platform engineering teams. All model experiments are tracked and reproducible via MLflow."),

      spacer(),

      // 2. PROBLEM STATEMENT
      h1("2. Problem Statement"),
      h2("2.1 Current Pain Points"),
      bullet(" Cloud bills arrive at the end of the billing cycle with no forward visibility.", "Reactive Spend Management: "),
      bullet(" GPU clusters, data pipelines, and autoscaling groups can spike unexpectedly, going undetected for hours or days.", "Blind Spot on Anomalous Usage: "),
      bullet(" FinOps, Platform, and Dev teams use fragmented dashboards with no unified signal.", "Siloed Cost Data: "),
      bullet(" Manual reviews of line-item billing reports are time-consuming and error-prone.", "No Automated Alerting: "),
      bullet(" Costs shift between services and accounts with no explainability layer.", "Attribution Gaps: "),

      spacer(),
      h2("2.2 Business Impact"),
      makeTable(
        ["Impact Area", "Current State", "Target State"],
        [
          ["Budget Overruns", "Discovered end-of-month", "Detected within 24 hours"],
          ["Forecast Accuracy", "Manual estimation ±40%", "MAPE < 10% for weekly forecast"],
          ["Anomaly Detection", "None / manual", "Automated, < 5% false positive rate"],
          ["Response Time", "2–5 business days", "< 4 hours with alert routing"],
          ["Model Reproducibility", "Non-existent", "Full MLflow experiment tracking"]
        ],
        [2800, 3280, 3280]
      ),

      spacer(),

      // 3. GOALS & NON-GOALS
      h1("3. Goals & Non-Goals"),
      h2("3.1 Goals"),
      bullet("Ingest and normalize AWS Cost & Usage Reports (CUR) and GCP Billing Export CSV files into a unified schema."),
      bullet("Forecast next-week aggregate cloud spend per service, account, and environment using Prophet or ARIMA."),
      bullet("Detect spend anomalies — including GPU usage spikes, data egress bursts, and storage cost jumps — using Isolation Forest."),
      bullet("Track all model training runs, hyperparameters, and evaluation metrics (MAPE, RMSE, false positive rate) in MLflow."),
      bullet("Provide alerting hooks (Slack / PagerDuty) when anomalies exceed configurable thresholds."),
      bullet("Support model retraining on a weekly cadence using fresh billing data."),

      spacer(),
      h2("3.2 Non-Goals"),
      bullet("Real-time streaming ingestion (billing exports are batch — daily/weekly cadence is sufficient for V1)."),
      bullet("Cost optimization recommendations (rightsizing, reserved instance suggestions) — planned for V2."),
      bullet("Multi-tenant SaaS offering — this is an internal platform tool."),
      bullet("Direct integration with cloud provider APIs for automated remediation."),

      spacer(),

      // 4. USER PERSONAS
      h1("4. User Personas & Use Cases"),
      h2("4.1 Primary Personas"),
      makeTable(
        ["Persona", "Role", "Primary Need", "Key Interaction"],
        [
          ["Alex", "FinOps Analyst", "Weekly spend forecast by service", "Dashboard + weekly email digest"],
          ["Priya", "Platform Engineer", "GPU anomaly alerts before budget breach", "Slack alerts + threshold config"],
          ["Marcus", "Engineering Manager", "Month-end budget forecast accuracy", "Executive summary report"],
          ["Deepa", "ML Engineer", "Reproduce and improve forecast models", "MLflow UI + model registry"],
          ["Sam", "SRE", "Correlate spend spikes with incidents", "API query + runbook integration"]
        ],
        [1500, 2200, 2800, 2860]
      ),

      spacer(),
      h2("4.2 Key User Stories"),
      para("As an Alex (FinOps Analyst), I want to see a 7-day rolling forecast of total cloud spend broken down by AWS service and GCP project so that I can proactively notify stakeholders of projected overruns before end-of-month."),
      spacer(),
      para("As a Priya (Platform Engineer), I want to receive a Slack alert within 2 hours of a GPU cluster cost anomaly exceeding 2 standard deviations so that I can investigate and terminate orphaned instances before significant waste occurs."),
      spacer(),
      para("As a Deepa (ML Engineer), I want all model training experiments — including hyperparameters, MAPE scores, and artifact paths — to be logged in MLflow so that I can compare runs and promote the best model to production."),

      spacer(),

      // 5. FUNCTIONAL REQUIREMENTS
      h1("5. Functional Requirements"),
      h2("5.1 Data Ingestion"),
      bullet("FR-01: System SHALL accept AWS CUR CSV exports (compressed .csv.gz or .csv) and GCP Billing Export CSVs as inputs."),
      bullet("FR-02: Ingestion pipeline SHALL normalize heterogeneous schemas into a unified billing schema: [date, cloud_provider, service, account_id, region, cost_usd, usage_quantity, usage_unit]."),
      bullet("FR-03: System SHALL validate ingested data for completeness, schema conformance, and outlier rows (e.g., negative costs, future dates)."),
      bullet("FR-04: Historical data SHALL be retained for a minimum of 24 months to support seasonality modeling."),

      spacer(),
      h2("5.2 Forecasting Engine"),
      bullet("FR-05: System SHALL train and evaluate both Prophet and ARIMA models per service/account grouping."),
      bullet("FR-06: Model selection SHALL be automated based on lowest MAPE on a 4-week holdout validation set."),
      bullet("FR-07: Forecasts SHALL be produced at daily granularity for the next 7 calendar days, aggregated to weekly totals."),
      bullet("FR-08: Forecast outputs SHALL include point estimates plus 80% and 95% prediction intervals."),
      bullet("FR-09: System SHALL support override inputs for planned events (e.g., product launches, data migrations) via a holiday/event calendar."),

      spacer(),
      h2("5.3 Anomaly Detection"),
      bullet("FR-10: Isolation Forest SHALL be applied to the residuals of the forecast (actual - forecasted spend) to flag anomalous spend deviations."),
      bullet("FR-11: Anomaly scoring SHALL produce a continuous contamination score, with threshold configurable per environment/service."),
      bullet("FR-12: System SHALL classify anomalies by type: spend spike, spend drop, service-specific burst (GPU, egress, storage)."),
      bullet("FR-13: Each anomaly event SHALL include: timestamp, affected service, account, magnitude (% deviation), isolation score, and suggested investigation link."),

      spacer(),
      h2("5.4 Experiment Tracking (MLflow)"),
      bullet("FR-14: Every model training run SHALL log: model type, hyperparameters, training data range, MAPE, RMSE, MAE, false positive rate, and artifact path."),
      bullet("FR-15: Best-performing model per service grouping SHALL be registered in the MLflow Model Registry with stage promotion (Staging → Production)."),
      bullet("FR-16: MLflow experiment names SHALL follow the convention: cloud_forecast_{provider}_{service}_{YYYYMMDD}."),

      spacer(),
      h2("5.5 Alerting & Reporting"),
      bullet("FR-17: System SHALL send Slack/webhook notifications when anomaly score exceeds the configured threshold."),
      bullet("FR-18: Weekly forecast digest SHALL be generated every Monday at 08:00 UTC and distributed to configured FinOps distribution lists."),
      bullet("FR-19: A REST API endpoint SHALL expose forecast data and anomaly flags for consumption by downstream dashboards."),

      spacer(),

      // 6. NON-FUNCTIONAL REQUIREMENTS
      h1("6. Non-Functional Requirements"),
      makeTable(
        ["Category", "Requirement", "Target"],
        [
          ["Performance", "End-to-end pipeline runtime (ingest → forecast → alert)", "< 15 minutes per daily run"],
          ["Accuracy", "Weekly aggregate forecast MAPE", "< 10%"],
          ["Precision", "Anomaly false positive rate", "< 5%"],
          ["Recall", "True anomaly detection rate", "> 85%"],
          ["Availability", "Pipeline uptime (excluding planned maintenance)", "99.5%"],
          ["Scalability", "Billing rows processable per run", "Up to 10M rows"],
          ["Latency", "Anomaly alert delivery after detection", "< 30 minutes"],
          ["Reproducibility", "Model training reproducibility (same seed/data)", "100% deterministic"],
          ["Data Retention", "Billing data retained for trend analysis", "24 months minimum"],
          ["Security", "Billing data encryption at rest and in transit", "AES-256 / TLS 1.3"]
        ],
        [2400, 4200, 2760]
      ),

      spacer(),

      // 7. SUCCESS METRICS
      h1("7. Success Metrics & KPIs"),
      h2("7.1 Launch Criteria (MVP)"),
      bullet("Forecast MAPE ≤ 10% on weekly aggregated spend across top 5 AWS services and GCP projects."),
      bullet("Anomaly false positive rate ≤ 5% over a 30-day evaluation window."),
      bullet("True positive anomaly detection rate ≥ 85% on labeled historical anomaly events."),
      bullet("100% of training runs logged in MLflow with full parameter and metric capture."),
      bullet("Pipeline end-to-end runtime < 15 minutes on a sample of 1M billing rows."),

      spacer(),
      h2("7.2 Business KPIs (90-Day Post-Launch)"),
      makeTable(
        ["KPI", "Baseline", "Target (90 days)", "Measurement"],
        [
          ["Avg time to detect anomaly", "2–5 business days", "< 4 hours", "Alert delivery timestamp"],
          ["Monthly forecast accuracy", "±40% (manual)", "±10% (model)", "MAPE vs actuals"],
          ["Undetected budget overruns", "~3/quarter", "0", "Finance reconciliation"],
          ["FinOps team hours on anomaly triage", "~8 hrs/week", "< 2 hrs/week", "Team time tracking"],
          ["Model retraining coverage", "N/A", "100% weekly", "MLflow run logs"]
        ],
        [2800, 1800, 1800, 2960]
      ),

      spacer(),

      // 8. TIMELINE
      h1("8. Milestones & Timeline"),
      makeTable(
        ["Phase", "Duration", "Deliverables", "Owner"],
        [
          ["Phase 1: Data Foundation", "Week 1–2", "Ingestion pipeline, schema normalization, data quality checks", "Data Engineering"],
          ["Phase 2: Forecasting Models", "Week 3–4", "Prophet + ARIMA training, MLflow integration, model evaluation", "ML Engineering"],
          ["Phase 3: Anomaly Detection", "Week 5–6", "Isolation Forest layer, anomaly classification, scoring API", "ML Engineering"],
          ["Phase 4: Alerting & Reporting", "Week 7–8", "Slack integration, digest reports, REST API, dashboard connector", "Platform Eng"],
          ["Phase 5: Hardening & Launch", "Week 9–10", "Load testing, runbooks, SLA validation, stakeholder sign-off", "All Teams"]
        ],
        [2400, 1400, 3960, 1600]
      ),

      spacer(),

      // 9. DEPENDENCIES & RISKS
      h1("9. Dependencies & Risks"),
      h2("9.1 Dependencies"),
      bullet("Access to AWS Cost & Usage Report (CUR) S3 bucket exports or equivalent billing CSV samples."),
      bullet("GCP Billing Export enabled and accessible from BigQuery or direct CSV download."),
      bullet("MLflow server provisioned (self-hosted or Databricks Managed MLflow)."),
      bullet("Slack workspace and webhook tokens for alert delivery."),

      spacer(),
      h2("9.2 Risk Register"),
      makeTable(
        ["Risk", "Probability", "Impact", "Mitigation"],
        [
          ["Billing data schema changes by AWS/GCP", "Medium", "High", "Schema versioning + validation tests"],
          ["Insufficient historical data for seasonality", "Low", "High", "Use Kaggle public billing datasets as seed"],
          ["High false positive rate on anomaly alerts", "Medium", "Medium", "Tune contamination parameter; human-in-loop feedback"],
          ["MLflow server unavailability", "Low", "Medium", "Fallback to local file logging with async sync"],
          ["Model drift over time", "High", "Medium", "Weekly automated retraining + MAPE monitoring"]
        ],
        [2800, 1400, 1400, 3760]
      ),

      spacer(),

      // 10. GLOSSARY
      h1("10. Glossary"),
      makeTable(
        ["Term", "Definition"],
        [
          ["CUR", "AWS Cost & Usage Report — detailed billing data export in CSV format"],
          ["MAPE", "Mean Absolute Percentage Error — primary forecast accuracy metric"],
          ["RMSE", "Root Mean Squared Error — secondary forecast error metric"],
          ["Prophet", "Facebook open-source time-series forecasting library with seasonality support"],
          ["ARIMA", "AutoRegressive Integrated Moving Average — classical time-series model"],
          ["Isolation Forest", "Ensemble anomaly detection algorithm that isolates outliers via random feature splits"],
          ["MLflow", "Open-source platform for managing the ML lifecycle including experiments, models, and deployment"],
          ["FinOps", "Cloud Financial Operations — discipline of maximizing business value from cloud spend"],
          ["Contamination", "Isolation Forest parameter defining expected proportion of anomalies in data"],
          ["False Positive Rate", "Percentage of normal events incorrectly flagged as anomalies"]
        ],
        [2000, 7360]
      ),

      spacer()
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/mnt/user-data/outputs/PRD_CloudCostForecasting.docx", buf);
  console.log("PRD created");
});
