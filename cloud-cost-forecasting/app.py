import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os
# Add the current directory to the path so we can import the app modules
sys.path.append(os.path.dirname(__file__))

from app.ingest.ingestor import ingest_billing_data
from app.forecasting.prophet_model import create_forecasting_model
from app.anomaly.isolation_forest import create_anomaly_detector
from app.visualization.plots import (
    plot_historical_spending,
    plot_forecast_with_intervals,
    plot_anomalies,
    create_spending_by_service_chart,
    create_monthly_trend_chart
)
from app.tracking.tracker import get_tracker
import tempfile
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Cloud Cost Forecasting & Anomaly Detection",
    page_icon="💰",
    layout="wide"
)

# Title and description
st.title("☁️ Cloud Cost Forecasting & Spend Anomaly Detection")
st.markdown("""
This application helps you forecast cloud spending and detect anomalies in your AWS and GCP billing data.
Upload your billing CSV files to get started.
""")

# Sidebar
st.sidebar.header("About")
st.sidebar.info(
    """
    This app is part of the Cloud Cost Forecasting & Spend Anomaly Detection MVP.
    It uses:
    - Prophet for time series forecasting
    - Isolation Forest for anomaly detection
    """
)

# File uploader
st.sidebar.header("Upload Data")
uploaded_files = st.sidebar.file_uploader(
    "Upload AWS or GCP billing CSV files",
    type=['csv'],
    accept_multiple_files=True,
    help="You can upload multiple CSV files. The app will automatically detect the format (AWS CUR or GCP Billing Export)."
)

# Use sample data if no files uploaded
if not uploaded_files:
    st.sidebar.write("Or use sample data:")
    if st.sidebar.button("Load Sample Data"):
        # Load sample data - use paths relative to this script
        base_dir = os.path.dirname(__file__)
        aws_file = os.path.join(base_dir, "data", "samples", "sample_aws_billing.csv")
        gcp_file = os.path.join(base_dir, "data", "samples", "sample_gcp_billing.csv")
        uploaded_files = [aws_file, gcp_file]
        st.sidebar.success("Sample data loaded!")

# Process uploaded files
if uploaded_files:
    # Save uploaded files to temporary location
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_paths.append(file_path)
    
    # Ingest data
    with st.spinner("Ingesting billing data..."):
        try:
            df = ingest_billing_data(file_paths)
            st.success(f"Successfully ingested {len(df)} rows of billing data!")
        except Exception as e:
            st.error(f"Error ingesting data: {str(e)}")
            st.stop()
    
    # Show raw data
    if st.checkbox("Show raw data"):
        st.subheader("Raw Data")
        st.dataframe(df)
    
    # Preprocessing: ensure date is datetime and sort
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Show data info
    st.subheader("Data Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Rows", len(df))
    with col2:
        st.metric("Date Range", f"{df['date'].min().date()} to {df['date'].max().date()}")
    with col3:
        st.metric("Cloud Providers", df['cloud_provider'].nunique())
    with col4:
        st.metric("Total Spend (USD)", f"${df['cost_usd'].sum():,.2f}")
    
    # Forecasting and Anomaly Detection
    st.subheader("Forecasting & Anomaly Detection")
    
    # Let user select forecasting horizon
    forecast_horizon = st.slider("Forecast Horizon (days)", 7, 30, 14)
    
    # Run analysis
    if st.button("Run Analysis", type="primary"):
        with st.spinner("Running forecasting and anomaly detection..."):
            try:
                # Initialize MLflow tracker
                tracker = get_tracker()
                run_id = tracker.start_run(run_name=f"forecasting_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                
                # We'll analyze each service/account group separately
                # For simplicity, we'll aggregate by date and service
                # In a real system, we might want to do per service/account
                
                # Prepare data for visualization
                # Historical spending chart
                historical_fig = plot_historical_spending(df, "Historical Cloud Spend")
                st.plotly_chart(historical_fig, use_container_width=True)
                
                # For forecasting, we'll use the total daily spend
                daily_df = df.groupby('date')['cost_usd'].sum().reset_index()
                daily_df = daily_df.rename(columns={'date': 'ds', 'cost_usd': 'y'})
                daily_df = daily_df.sort_values('ds').reset_index(drop=True)
                
                # Chronological train/test split (80/20)
                # Use first 80% for training, last 20% for evaluation
                train_size = int(len(daily_df) * 0.8)
                train_data = daily_df[:train_size].copy()
                test_data = daily_df[train_size:].copy()
                
                st.info(f"Training on {len(train_data)} days, evaluating on {len(test_data)} days")
                
                # Create and fit forecasting model on training data
                forecast_model = create_forecasting_model('prophet')
                forecast_model.fit(train_data)
                
                # Log model parameters to MLflow
                tracker.log_params({
                    'model_type': 'prophet',
                    'train_size': len(train_data),
                    'test_size': len(test_data),
                    'forecast_horizon': forecast_horizon
                })
                
                # Generate forecast for the future (beyond all historical data)
                forecast_df = forecast_model.predict(periods=forecast_horizon, freq='D')
                # Rename columns for consistency with our visualization function
                forecast_df = forecast_df.rename(columns={
                    'ds': 'date',
                    'yhat': 'forecast_cost_usd',
                    'yhat_lower': 'lower_bound_80',
                    'yhat_upper': 'upper_bound_80'
                })
                
                # Evaluate on test set (holdout period)
                eval_metrics = forecast_model.evaluate(test_data)
                
                # Log evaluation metrics to MLflow
                tracker.log_metrics({
                    'mape': eval_metrics['mape'] if eval_metrics['mape'] is not None else 0.0,
                    'rmse': eval_metrics['rmse'],
                    'mae': eval_metrics['mae']
                })
                
                # Display evaluation metrics
                st.subheader("Forecast Evaluation (on Holdout Test Set)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    mape_str = f"{eval_metrics['mape']:.2%}" if eval_metrics['mape'] is not None else "N/A (zero actuals)"
                    st.metric("MAPE", mape_str)
                with col2:
                    st.metric("RMSE", f"${eval_metrics['rmse']:.2f}")
                with col3:
                    st.metric("MAE", f"${eval_metrics['mae']:.2f}")
                
                # Compute residuals on TEST data for anomaly detection
                # Get predictions on test dates
                test_predictions = forecast_model.predict_on_dates(test_data[['ds']].rename(columns={'ds': 'date'}))
                test_with_pred = test_data.copy()
                test_with_pred = test_with_pred.merge(test_predictions, on='date', how='inner')
                test_with_pred['residual'] = test_with_pred['y'] - test_with_pred['predicted']
                
                # Prepare features for anomaly detection on TEST residuals
                anomaly_features = test_with_pred[['residual']].copy()
                anomaly_features['residual_lag1'] = anomaly_features['residual'].shift(1)
                anomaly_features['residual_rolling_mean_7'] = anomaly_features['residual'].rolling(7, min_periods=1).mean()
                anomaly_features['residual_rolling_std_7'] = anomaly_features['residual'].rolling(7, min_periods=1).std()
                # Fill NaN values
                anomaly_features = anomaly_features.bfill().ffill()
                
                # Fit anomaly detector on TEST residuals (not training data)
                anomaly_detector = create_anomaly_detector(contamination=0.05)
                anomaly_detector.fit(anomaly_features)
                
                # Get anomaly scores and predictions on TEST data
                anomaly_scores = anomaly_detector.score_samples(anomaly_features)
                anomaly_predictions = anomaly_detector.predict(anomaly_features)
                anomaly_labels = (anomaly_predictions == -1).astype(int)
                
                test_with_pred['anomaly_score'] = anomaly_scores
                test_with_pred['is_anomaly'] = anomaly_labels
                
                # Log anomaly detection metrics
                n_anomalies = int(anomaly_labels.sum())
                tracker.log_metrics({
                    'n_anomalies_detected': n_anomalies,
                    'anomaly_rate': n_anomalies / len(anomaly_labels) if len(anomaly_labels) > 0 else 0.0
                })
                
                # Create forecast visualization (historical + forecast)
                forecast_fig = plot_forecast_with_intervals(
                    historical_df=daily_df.rename(columns={'ds': 'date', 'y': 'cost_usd'}),
                    forecast_df=forecast_df,
                    title="Cloud Spend Forecast with Confidence Intervals"
                )
                st.plotly_chart(forecast_fig, use_container_width=True)
                
                # Show anomalies in TEST/holdout period
                anomalies_df = test_with_pred[test_with_pred['is_anomaly'] == 1]
                if not anomalies_df.empty:
                    anomaly_fig = plot_anomalies(
                        df=daily_df.rename(columns={'ds': 'date', 'y': 'cost_usd'}),
                        anomaly_df=anomalies_df[['date', 'y']].rename(columns={'y': 'cost_usd'}),
                        title="Anomalies Detected in Holdout Period (Test Set)"
                    )
                    st.plotly_chart(anomaly_fig, use_container_width=True)
                    
                    st.subheader("Detected Anomalies in Holdout Period")
                    st.dataframe(anomalies_df[['date', 'y', 'predicted', 'residual', 'anomaly_score']].rename(columns={'y': 'actual_cost', 'predicted': 'forecasted_cost'}))
                else:
                    st.info("No anomalies detected in the holdout test period.")
                
                # Show forecast table
                st.subheader("Future Forecast Values")
                forecast_display = forecast_df[['date', 'forecast_cost_usd', 'lower_bound_80', 'upper_bound_80']].copy()
                forecast_display['date'] = forecast_display['date'].dt.date
                st.dataframe(forecast_display)
                
                # Additional visualizations
                st.subheader("Additional Insights")
                col1, col2 = st.columns(2)
                with col1:
                    service_fig = create_spending_by_service_chart(df, "Spending by Service")
                    st.plotly_chart(service_fig, use_container_width=True)
                with col2:
                    monthly_fig = create_monthly_trend_chart(df, "Monthly Spend Trend")
                    st.plotly_chart(monthly_fig, use_container_width=True)
                
                # End MLflow run
                tracker.end_run()
                st.success(f"MLflow run completed: {run_id}")
                    
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.exception(e)

else:
    st.info("Please upload billing CSV files to begin analysis, or click 'Load Sample Data' in the sidebar to try with sample data.")
    
    # Show sample data info
    st.subheader("Sample Data Format")
    st.write("The app expects AWS Cost & Usage Report (CUR) or GCP Billing Export CSV files.")
    st.write("Sample AWS CUR columns: bill/BillingPeriodStartDate, lineItem/ProductCode, lineItem/UsageAccountId, lineItem/UsageAmount, lineItem/UnblendedCost, product/region")
    st.write("Sample GCP Billing Export columns: usage_start_time, service.description, project.id, cost, usage.amount, usage.unit")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Cloud Cost Forecasting & Spend Anomaly Detection MVP</p>
        <p>Built with Streamlit, Prophet, scikit-learn, and Plotly</p>
    </div>
    """,
    unsafe_allow_html=True
)