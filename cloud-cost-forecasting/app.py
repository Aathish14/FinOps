import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
import tempfile
import os
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
    - MLflow for experiment tracking (not shown in UI)
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
        # Load sample data
        aws_file = "data/samples/sample_aws_billing.csv"
        gcp_file = "data/samples/sample_gcp_billing.csv"
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
            
            # Split data for forecasting (use last 30% as test, but we'll forecast forward)
            # We'll use all data to train, then forecast forward
            train_size = int(len(daily_df) * 0.8)
            train_data = daily_df[:train_size]
            # We don't have test data for future dates, so we'll just train on all data for forecasting
            # But for evaluation we could hold out some recent points
            
            # Create and fit forecasting model
            forecast_model = create_forecasting_model('prophet')
            forecast_model.fit(train_data)
            
            # Generate forecast
            forecast_df = forecast_model.predict(periods=forecast_horizon, freq='D')
            # Rename columns for consistency with our visualization function
            forecast_df = forecast_df.rename(columns={
                'ds': 'date',
                'yhat': 'forecast_cost_usd',
                'yhat_lower': 'lower_bound_80',
                'yhat_upper': 'upper_bound_80'
            })
            
            # Calculate residuals for anomaly detection (on training data)
            # We need to get predictions on the training data to compute residuals
            train_pred = forecast_model.predict(periods=0, freq='D')  # This doesn't work as expected
            # Instead, let's get in-sample predictions
            # We'll create a future dataframe that includes the training dates
            train_future = forecast_model.model.make_future_dataframe(periods=0)
            train_forecast = forecast_model.model.predict(train_future)
            # Merge with actuals
            train_with_pred = train_data.copy()
            train_with_pred['predicted'] = train_forecast['yhat'].values
            train_with_pred['residual'] = train_with_pred['y'] - train_with_pred['predicted']
            
            # Prepare features for anomaly detection
            # We'll use: residual, residual_lag1, residual_rolling_mean_7, etc.
            # For simplicity, we'll use just the residual and some basic features
            anomaly_features = train_with_pred[['residual']].copy()
            anomaly_features['residual_lag1'] = anomaly_features['residual'].shift(1)
            anomaly_features['residual_rolling_mean_7'] = anomaly_features['residual'].rolling(7, min_periods=1).mean()
            anomaly_features['residual_rolling_std_7'] = anomaly_features['residual'].rolling(7, min_periods=1).std()
            # Fill NaN values
            anomaly_features = anomaly_features.fillna(method='bfill').fillna(method='ffill')
            
            # Fit anomaly detector
            anomaly_detector = create_anomaly_detector(contamination=0.05)  # Expect 5% anomalies
            anomaly_detector.fit(anomaly_features)
            
            # Get anomaly scores and predictions
            anomaly_scores = anomaly_detector.score_samples(anomaly_features)
            anomaly_predictions = anomaly_detector.predict(anomaly_features)
            # Convert to binary: 1 for anomaly, 0 for normal
            anomaly_labels = (anomaly_predictions == -1).astype(int)
            
            # Add to dataframe
            train_with_pred['anomaly_score'] = anomaly_scores
            train_with_pred['is_anomaly'] = anomaly_labels
            
            # For future dates (forecast period), we don't have actuals, so we can't compute residuals
            # We'll just show the forecast without anomaly detection for future dates
            
            # Create forecast visualization
            forecast_fig = plot_forecast_with_intervals(
                historical_df=daily_df.rename(columns={'ds': 'date', 'y': 'cost_usd'}),
                forecast_df=forecast_df,
                title="Cloud Spend Forecast with Confidence Intervals"
            )
            st.plotly_chart(forecast_fig, use_container_width=True)
            
            # Show anomalies in historical data
            anomalies_df = train_with_pred[train_with_pred['is_anomaly'] == 1]
            if not anomalies_df.empty:
                anomaly_fig = plot_anomalies(
                    df=daily_df.rename(columns={'ds': 'date', 'y': 'cost_usd'}),
                    anomaly_df=anomalies_df[['date', 'cost_usd']],
                    title="Historical Spend with Detected Anomalies"
                )
                st.plotly_chart(anomaly_fig, use_container_width=True)
                
                st.subheader("Detected Anomalies")
                st.dataframe(anomalies_df[['date', 'cost_usd', 'anomaly_score']])
            else:
                st.info("No anomalies detected in the historical data.")
            
            # Show forecast table
            st.subheader("Forecast Values")
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