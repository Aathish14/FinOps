import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os
from pathlib import Path
# Add the current directory to the path so we can import the app modules
sys.path.append(os.path.dirname(__file__))

from app.ingest.ingestor import ingest_billing_data, normalize_file_inputs
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
from app.anomaly.cost_aware import CostImpactScorer
from app.anomaly.explanations import AnomalyExplainer, format_anomaly_for_ui
from datetime import datetime

# Minimum data requirements
MIN_DAILY_OBSERVATIONS_FORECASTING = 30
MIN_DAILY_OBSERVATIONS_ANOMALY = 10
MAX_FORECAST_HORIZON_RATIO = 0.5  # Max forecast horizon as fraction of history

# Set page config
st.set_page_config(
     page_title="Cloud Cost Forecasting & Anomaly Detection",
     page_icon="📈",
     layout="wide"
 )

# Title and description
st.title("Cloud Cost Forecasting & Spend Anomaly Detection")
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

# Model hyperparameters
st.sidebar.header("Model Hyperparameters")

with st.sidebar.expander("Prophet Forecasting", expanded=True):
    forecast_horizon = st.slider(
        "Forecast Horizon (days)",
        min_value=7,
        max_value=90,
        value=30,
        help="Number of days to forecast into the future."
    )
    interval_width = st.slider(
        "Confidence Interval Width",
        min_value=0.80,
        max_value=0.99,
        value=0.95,
        step=0.01,
        help="Width of the uncertainty interval for forecasts."
    )
    seasonality_mode = st.selectbox(
        "Seasonality Mode",
        options=["additive", "multiplicative"],
        index=0,
        help="Additive or multiplicative seasonality."
    )
    weekly_seasonality = st.selectbox(
        "Weekly Seasonality",
        options=["auto", True, False],
        index=0,
        help="Include weekly seasonality."
    )
    yearly_seasonality = st.selectbox(
        "Yearly Seasonality",
        options=["auto", True, False],
        index=0,
        help="Include yearly seasonality."
    )

with st.sidebar.expander("Isolation Forest Anomaly Detection", expanded=True):
    contamination = st.slider(
        "Contamination (anomaly sensitivity)",
        min_value=0.01,
        max_value=0.15,
        value=0.05,
        step=0.01,
        help="Expected proportion of anomalies in the data."
    )
    n_estimators = st.slider(
        "Number of Estimators",
        min_value=50,
        max_value=300,
        value=100,
        step=50,
        help="Number of trees in the isolation forest."
    )

# Use sample data if no files uploaded
if not uploaded_files:
    st.sidebar.write("Or use sample data:")

    # Discover available sample CSV files dynamically
    samples_dir = Path(__file__).parent / "data" / "samples"
    sample_files = []
    if samples_dir.exists() and samples_dir.is_dir():
        sample_files = sorted([f for f in samples_dir.glob("*.csv") if f.is_file()])

    if sample_files:
        # Create a mapping of display names to file paths
        sample_options = {f.name: f for f in sample_files}
        selected_sample = st.sidebar.selectbox(
            "Sample Data CSV",
            options=list(sample_options.keys()),
            index=0,
            help="Select a sample CSV file to load"
        )

        if st.sidebar.button("Load Sample Data"):
            selected_path = sample_options[selected_sample]
            # Store in session state so it persists across reruns
            st.session_state["sample_data_files"] = [str(selected_path.resolve())]
            st.sidebar.success(f"Loaded: {selected_sample}")
    else:
        st.sidebar.warning("No sample CSV files found in data/samples directory")
        if st.sidebar.button("Load Sample Data"):
            st.sidebar.error("No sample CSV files available")

# Resolve the effective set of file inputs.
#   - User uploads always take precedence over sample data.
#   - Sample data (string paths) is kept in session state across reruns.
if uploaded_files:
    file_inputs = list(uploaded_files)
elif "sample_data_files" in st.session_state:
    file_inputs = list(st.session_state["sample_data_files"])
else:
    file_inputs = []

# Defensive filter: drop any input that is neither an UploadedFile-like object
# (exposes .name / .getbuffer) nor a str / os.PathLike path. Prevents
# AttributeError on .name when switching between st.file_uploader (UploadedFile)
# and sample data stored as plain str paths in session state.
file_inputs = [
    f for f in file_inputs
    if hasattr(f, "getbuffer") or isinstance(f, (str, os.PathLike))
]

# Process uploaded files
if file_inputs:
    # Normalize mixed inputs (UploadedFile objects and/or string paths)
    # into a consistent list of filesystem paths for ingestion.
    file_paths = normalize_file_inputs(file_inputs)

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
    # Normalize to timezone-naive UTC so downstream merges with
    # Prophet predictions (which are timezone-naive) do not fail with
    # "trying to merge on datetime64[ns, UTC] and datetime64[ns]".
    df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
    df = df.sort_values('date').reset_index(drop=True)

    # Validate data quality after ingestion
    if df['cost_usd'].isna().any():
        st.error("Ingested data contains NaN values in cost_usd. Please check your CSV files.")
        st.stop()
    if not np.isfinite(df['cost_usd']).all():
        st.error("Ingested data contains infinite values in cost_usd. Please check your CSV files.")
        st.stop()
    if df['usage_quantity'].isna().any():
        st.warning("Some rows have missing usage_quantity values. These will be treated as unknown.")
    if not np.isfinite(df['usage_quantity']).all():
        st.warning("Some rows have infinite usage_quantity values. These will be treated as unknown.")

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
                st.plotly_chart(historical_fig, width="stretch")

                # For forecasting, we'll use the total daily spend
                daily_df = df.groupby('date')['cost_usd'].sum().reset_index()
                daily_df = daily_df.sort_values('date').reset_index(drop=True)

                # Validate minimum data requirements
                n_daily = len(daily_df)
                if n_daily < MIN_DAILY_OBSERVATIONS_FORECASTING:
                    st.error(
                        f"Insufficient historical data: {n_daily} unique daily observations found. "
                        f"At least {MIN_DAILY_OBSERVATIONS_FORECASTING} are required for forecasting."
                    )
                    st.stop()

                # Validate forecast horizon
                max_horizon = int(n_daily * MAX_FORECAST_HORIZON_RATIO)
                if forecast_horizon > max_horizon:
                    st.error(
                        f"Forecast horizon ({forecast_horizon} days) is too large for the available history "
                        f"({n_daily} days). Maximum recommended horizon is {max_horizon} days "
                        f"({int(MAX_FORECAST_HORIZON_RATIO * 100)}% of history length)."
                    )
                    st.stop()

                # Chronological train/test split (80/20)
                # Use first 80% for training, last 20% for evaluation
                train_size = int(len(daily_df) * 0.8)
                train_data = daily_df[:train_size].copy()
                test_data = daily_df[train_size:].copy()

                st.info(f"Training on {len(train_data)} days, evaluating on {len(test_data)} days")

                # Create and fit forecasting model on training data
                forecast_model = create_forecasting_model('prophet')
                forecast_model.fit(
                    train_data,
                    interval_width=interval_width,
                    seasonality_mode=seasonality_mode,
                    weekly_seasonality=weekly_seasonality,
                    yearly_seasonality=yearly_seasonality
                )

                # Log model parameters to MLflow
                tracker.log_params({
                    'model_type': 'prophet',
                    'train_size': len(train_data),
                    'test_size': len(test_data),
                    'forecast_horizon': forecast_horizon,
                    'interval_width': interval_width,
                    'seasonality_mode': seasonality_mode,
                    'weekly_seasonality': str(weekly_seasonality),
                    'yearly_seasonality': str(yearly_seasonality)
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

                # ============================================================
                # ANOMALY DETECTION - CORRECT ARCHITECTURE (NO DATA LEAKAGE)
                # ============================================================
                # Step 1: Generate predictions on TRAINING dates to get training residuals
                train_predictions = forecast_model.predict_on_dates(train_data[['date']])
                train_with_pred = train_data.copy()
                # Normalize train date column to match predictions (both timezone-naive)
                train_with_pred['date'] = pd.to_datetime(train_with_pred['date'], utc=True).dt.tz_localize(None)
                train_with_pred = train_with_pred.merge(train_predictions, on='date', how='inner')
                train_with_pred['residual'] = train_with_pred['cost_usd'] - train_with_pred['predicted']

                # Step 2: Prepare features for anomaly detection on TRAINING residuals
                train_anomaly_features = train_with_pred[['residual']].copy()
                train_anomaly_features['residual_lag1'] = train_anomaly_features['residual'].shift(1)
                train_anomaly_features['residual_rolling_mean_7'] = train_anomaly_features['residual'].rolling(7, min_periods=1).mean()
                train_anomaly_features['residual_rolling_std_7'] = train_anomaly_features['residual'].rolling(7, min_periods=1).std()
                train_anomaly_features = train_anomaly_features.bfill().ffill()

                # Validate minimum training residuals for anomaly detection
                if len(train_anomaly_features) < MIN_DAILY_OBSERVATIONS_ANOMALY:
                    st.error(
                        f"Insufficient training data for anomaly detection: {len(train_anomaly_features)} training residuals. "
                        f"At least {MIN_DAILY_OBSERVATIONS_ANOMALY} are required."
                    )
                    st.stop()

                # Step 3: Fit anomaly detector on TRAINING residuals (NOT test data)
                anomaly_detector = create_anomaly_detector(contamination=contamination, n_estimators=n_estimators)
                anomaly_detector.fit(train_anomaly_features)

                # Step 4: Generate predictions on TEST dates to get test residuals
                test_predictions = forecast_model.predict_on_dates(test_data[['date']])
                test_with_pred = test_data.copy()
                # Normalize test date column to match predictions (both timezone-naive)
                test_with_pred['date'] = pd.to_datetime(test_with_pred['date'], utc=True).dt.tz_localize(None)
                test_with_pred = test_with_pred.merge(test_predictions, on='date', how='inner')
                test_with_pred['residual'] = test_with_pred['cost_usd'] - test_with_pred['predicted']

                # Step 5: Prepare features for anomaly detection on TEST residuals
                test_anomaly_features = test_with_pred[['residual']].copy()
                test_anomaly_features['residual_lag1'] = test_anomaly_features['residual'].shift(1)
                test_anomaly_features['residual_rolling_mean_7'] = test_anomaly_features['residual'].rolling(7, min_periods=1).mean()
                test_anomaly_features['residual_rolling_std_7'] = test_anomaly_features['residual'].rolling(7, min_periods=1).std()
                test_anomaly_features = test_anomaly_features.bfill().ffill()

                # Step 6: Score anomaly detector on TEST features (using already-fitted detector)
                anomaly_scores = anomaly_detector.score_samples(test_anomaly_features)
                anomaly_predictions = anomaly_detector.predict(test_anomaly_features)
                anomaly_labels = (anomaly_predictions == -1).astype(int)

                test_with_pred['anomaly_score'] = anomaly_scores
                test_with_pred['is_anomaly'] = anomaly_labels

                # Log anomaly detection metrics
                n_anomalies = int(anomaly_labels.sum())
                tracker.log_metrics({
                    'n_anomalies_detected': n_anomalies,
                    'anomaly_rate': n_anomalies / len(anomaly_labels) if len(anomaly_labels) > 0 else 0.0,
                    'contamination': contamination,
                    'n_estimators': n_estimators
                })

                # Cost-Impact Ranking
                st.subheader("Cost-Impact Anomaly Prioritization")
                cost_scorer = CostImpactScorer()
                # Prepare test data for cost-impact ranking
                test_actual = test_with_pred['cost_usd'].values
                test_predicted = test_with_pred['predicted'].values

                # Get anomaly scores from the detector (using test features)
                anomaly_scores = anomaly_detector.score_samples(test_anomaly_features)

                # Rank anomalies by cost-impact
                ranked_results = CostImpactScorer().rank_anomalies(
                    test_data=test_with_pred[['date', 'cost_usd']],
                    anomaly_scores=anomaly_scores,
                    anomaly_labels=anomaly_labels,
                    actual_costs=test_actual,
                    expected_costs=test_predicted,
                    mape=eval_metrics.get('mape')
                )

                # Generate explanations for top anomalies
                explainer = AnomalyExplainer()
                explanations = explainer.explain_batch(
                    ranked_results,
                    top_k=10
                )

                # Log cost-aware ranking metrics
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
                st.plotly_chart(forecast_fig, width="stretch")

                # Show cost-impact ranked anomalies
                st.subheader("Cost-Impact Anomaly Prioritization")

                # Filter to confirmed anomalies only (anomaly_label == 1).
                # The table is titled "Anomaly Prioritization" so it must
                # contain only confirmed anomalies, not high-cost normal days.
                anomaly_results = ranked_results[ranked_results['anomaly_label'] == 1]

                # Display top-K anomalies by cost-impact
                top_k = 10
                top_anomalies = anomaly_results.nlargest(top_k, 'cost_impact_score')

                # Display anomaly table with cost-impact prioritization
                if not top_anomalies.empty:
                    display_cols = ['date', 'observed_cost', 'expected_cost', 'excess_cost',
                                   'relative_deviation', 'anomaly_score', 'cost_impact_score',
                                   'anomaly_label', 'cost_impact_rank']
                    display_df = top_anomalies[['date', 'observed_cost', 'expected_cost', 'excess_cost',
                                                'relative_deviation', 'anomaly_score', 'cost_impact_score',
                                                'anomaly_label', 'cost_impact_rank']].copy()
                    display_df['date'] = display_df['date'].dt.date
                    display_df['observed_cost'] = display_df['observed_cost'].apply(lambda x: f"${x:,.2f}")
                    display_df['expected_cost'] = display_df['expected_cost'].apply(lambda x: f"${x:,.2f}")
                    display_df['excess_cost'] = display_df['excess_cost'].apply(lambda x: f"${x:,.2f}")
                    display_df['relative_deviation'] = display_df['relative_deviation'].apply(lambda x: f"{x:.1%}")
                    display_df['anomaly_score'] = display_df['anomaly_score'].apply(lambda x: f"{x:.3f}")
                    display_df['cost_impact_score'] = display_df['cost_impact_score'].apply(lambda x: f"{x:.3f}")
                    display_df['anomaly_label'] = display_df['anomaly_label'].apply(lambda x: "⚠️ ANOMALY" if x == 1 else "Normal")

                    # Add severity badge
                    display_df['severity'] = display_df['anomaly_label'].apply(lambda x: "🔥 HIGH" if x == 1 else "✅ Normal")

                    st.dataframe(display_df, width="stretch")

                    # Show explanations for top anomalies
                    st.subheader("Anomaly Explanations")
                    explainer = AnomalyExplainer()
                    explanations = explainer.explain_batch(ranked_results, top_k=5)

                    for exp in explanations:
                        with st.expander(f"Rank #{exp['cost_impact_rank']} - {exp['date']} ({exp['provider']}) - ${exp['excess_cost']:,.2f} excess"):
                            st.write(exp['explanation'])
                            st.caption(f"Cost-Impact Score: {exp['cost_impact_score']:.3f} | Excess: ${exp['excess_cost']:,.2f}")

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
                    st.plotly_chart(service_fig, width="stretch")
                with col2:
                    monthly_fig = create_monthly_trend_chart(df, "Monthly Spend Trend")
                    st.plotly_chart(monthly_fig, width="stretch")

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
