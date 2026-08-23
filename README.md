# Cloud Cost Forecasting & Spend Anomaly Detection

An MVP for forecasting cloud spending and detecting anomalies in AWS and GCP billing data.

## Overview

This application helps FinOps and platform engineering teams proactively forecast cloud spend and automatically flag abnormal usage patterns. It ingests raw billing CSV exports, applies time-series forecasting models (Prophet), layers anomaly detection (Isolation Forest) on forecast residuals, and surfaces actionable alerts.

## Features

- **Billing Data Ingestion**: Supports AWS Cost & Usage Report (CUR) and GCP Billing Export CSV formats
- **Forecasting Engine**: Uses Prophet for time series forecasting with confidence intervals
- **Anomaly Detection**: Applies Isolation Forest to forecast residuals on holdout test data
- **Visualization**: Interactive charts showing historical spending, forecasts, and anomalies
- **Experiment Tracking**: MLflow integration for reproducible model experiments (local development)
- **User Interface**: Built with Streamlit for easy interaction

## Architecture

```
cloud-cost-forecasting/
├── app/
│   ├── ingest/           # Billing data ingestion modules
│   ├── forecasting/      # Time series forecasting models (Prophet)
│   ├── anomaly/          # Anomaly detection algorithms (Isolation Forest)
│   ├── tracking/         # Experiment tracking with MLflow
│   └── visualization/    # Plotting and charting utilities
├── data/
│   └── samples/          # Sample AWS and GCP billing CSV files
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── app.py                # Main Streamlit application
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Aathish14/FinOps.git
   cd FinOps
   ```

2. Install dependencies:
   ```bash
   pip install -r cloud-cost-forecasting/requirements.txt
   ```

   Or from the root:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Local Development

Run the Streamlit application:
```bash
cd cloud-cost-forecasting
streamlit run app.py
```

Then open your browser to `http://localhost:8501`.

### Sample Data

The repository includes sample AWS and GCP billing CSV files in `cloud-cost-forecasting/data/samples/` for testing.

Note: Sample data is limited (4 days each) and intended for quick testing only. For meaningful forecasts, provide at least 60+ days of historical data.

### With Your Data

1. Click "Upload Data" in the sidebar
2. Select your AWS CUR or GCP Billing Export CSV files
3. Adjust the forecast horizon if needed
4. Click "Run Analysis"

## Methodology

### Data Ingestion
- Automatically detects AWS CUR vs GCP Billing Export format
- Normalizes to unified schema: `[date, cloud_provider, service_name, account_id, region, environment, usage_quantity, usage_unit, cost_usd]`
- Handles missing values and basic validation

### Forecasting
- Uses Facebook Prophet with default seasonality
- Generates daily forecasts for the next 7-30 days
- Provides 80% confidence intervals
- Chronological train/test split (80/20) for genuine evaluation

### Forecast Evaluation
- Evaluation metrics computed on holdout test set (not training data)
- Metrics: MAPE (Mean Absolute Percentage Error), RMSE (Root Mean Squared Error), MAE (Mean Absolute Error)
- Zero actuals handled gracefully for MAPE calculation

### Anomaly Detection
- Isolation Forest applied to forecast residuals on holdout test period
- Features: residual, lagged residual, rolling mean/std (7-day window)
- Configurable contamination rate (default: 5%)
- Anomaly scoring and classification on unseen test data only

### Experiment Tracking (Local)
- MLflow integration for parameter, metric, and artifact logging
- Experiment naming convention: `cloud_cost_forecasting`
- Automatic logging of model parameters, evaluation metrics, and anomaly detection results
- Note: MLflow tracking uses local SQLite backend; cloud deployment may require external tracking server

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt` (pinned versions for reproducibility)

## Deployment

### Streamlit Cloud
The application can be deployed to Streamlit Cloud:
1. Push this repository to GitHub
2. Connect to Streamlit Cloud
3. Set entrypoint to `cloud-cost-forecasting/app.py`
4. Ensure branch is `main` (or configure deployment branch)

### Local MLflow UI
To view MLflow experiments locally:
```bash
mlflow ui
```
Then open `http://localhost:5000`

## Limitations

- **Sample data is minimal** (4 days) - insufficient for production forecasting
- **No ARIMA fallback** - only Prophet is implemented
- **MLflow tracking** uses local SQLite; production deployments should use a managed tracking server
- **No authentication/authorization** - designed for internal/local use
- **Single-series forecasting** - aggregates all services; per-service forecasting not implemented

## License

MIT

## Acknowledgements

- [Prophet](https://facebook.github.io/prophet/) for time series forecasting
- [scikit-learn](https://scikit-learn.org/) for Isolation Forest
- [MLflow](https://mlflow.org/) for experiment tracking
- [Streamlit](https://streamlit.io/) for the web application framework
- [Plotly](https://plotly.com/) for interactive visualizations