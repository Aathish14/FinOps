# Cloud Cost Forecasting & Spend Anomaly Detection

A production-style MVP for forecasting cloud spending and detecting anomalies in AWS and GCP billing data.

## Overview

This application helps FinOps and platform engineering teams proactively forecast cloud spend and automatically flag abnormal usage patterns. It ingests raw billing CSV exports, applies time-series forecasting models (Prophet), layers anomaly detection (Isolation Forest) on top of forecasted values, and surfaces actionable alerts.

## Features

- **Billing Data Ingestion**: Supports AWS Cost & Usage Report (CUR) and GCP Billing Export CSV formats
- **Forecasting Engine**: Uses Prophet for accurate time series forecasting with confidence intervals
- **Anomaly Detection**: Applies Isolation Forest to forecast residuals to detect unusual spending patterns
- **Visualization**: Interactive charts showing historical spending, forecasts, and anomalies
- **Experiment Tracking**: MLflow integration for reproducible model experiments
- **User Interface**: Built with Streamlit for easy interaction

## Architecture

```
cloud-cost-forecasting/
├── app/
│   ├── ingest/           # Billing data ingestion modules
│   ├── forecasting/      # Time series forecasting models
│   ├── anomaly/          # Anomaly detection algorithms
│   ├── tracking/         # Experiment tracking with MLflow
│   ├── visualization/    # Plotting and charting utilities
│   └── utils/            # Helper functions
├── data/
│   ├── raw/              # Uploaded billing CSV files
│   ├── processed/        # Cleaned and normalized data
│   └── outputs/          # Forecast and anomaly results
├── experiments/          # MLflow experiment tracking
├── models/               # Saved models
├── notebooks/            # Exploratory analysis
├── screenshots/          # UI screenshots
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
   pip install -r requirements.txt
   ```

## Usage

### Local Development

Run the Streamlit application:
```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`.

### Sample Data

The repository includes sample AWS and GCP billing CSV files in `data/samples/` for testing.

### With Your Data

1. Click "Upload Data" in the sidebar
2. Select your AWS CUR or GCP Billing Export CSV files
3. Adjust the forecast horizon if needed
4. Click "Run Analysis"

## Deployment

The application is deployed publicly at: [https://share.streamlit.io/aathish14/finops/main/app.py](https://share.streamlit.io/aathish14/finops/main/app.py)

### Local Run Instructions
To run the application locally:
```bash
streamlit run app.py
```

### Deployment Notes
The deployment URL above follows the Streamlit Cloud format. The application is configured for automatic deployment from the `main` branch of the GitHub repository.

## Sample Output

![Dashboard](screenshots/dashboard.png)

## Technical Details

### Data Ingestion
- Automatically detects AWS CUR vs GCP Billing Export format
- Normalizes to unified schema: `[date, cloud_provider, service, account_id, region, cost_usd, usage_quantity, usage_unit]`
- Handles missing values and basic validation

### Forecasting
- Uses Facebook Prophet with multiplicative seasonality
- Generates daily forecasts for the next 7-30 days
- Provides 80% confidence intervals
- Automatic model fitting and prediction

### Anomaly Detection
- Isolation Forest applied to forecast residuals
- Features include residual, lagged residual, and rolling statistics
- Configurable contamination rate (default: 5%)
- Anomaly scoring and classification

### Experiment Tracking
- MLflow integration for parameter, metric, and artifact logging
- Experiment naming convention: `cloud_cost_forecasting`
- Automatic logging of model parameters and evaluation metrics

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## License

MIT

## Acknowledgements

- [Prophet](https://facebook.github.io/prophet/) for time series forecasting
- [scikit-learn](https://scikit-learn.org/) for Isolation Forest
- [MLflow](https://mlflow.org/) for experiment tracking
- [Streamlit](https://streamlit.io/) for the web application framework
- [Plotly](https://plotly.com/) for interactive visualizations