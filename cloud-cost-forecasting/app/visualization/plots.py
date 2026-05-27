import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

def plot_historical_spending(df: pd.DataFrame, title: str = "Historical Cloud Spend") -> go.Figure:
    """
    Create an interactive line chart of historical spending over time.
    
    Args:
        df: DataFrame with columns ['date', 'cost_usd'] (can have other columns for grouping)
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    # If we have multiple services/accounts, we can group by them
    if 'service_name' in df.columns and 'account_id' in df.columns:
        # Group by date and sum costs
        daily_df = df.groupby('date')['cost_usd'].sum().reset_index()
    else:
        daily_df = df[['date', 'cost_usd']].copy()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df['date'],
        y=daily_df['cost_usd'],
        mode='lines+markers',
        name='Daily Spend',
        line=dict(color='blue')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Cost (USD)',
        hovermode='x unified'
    )
    
    return fig

def plot_forecast_with_intervals(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    title: str = "Cloud Spend Forecast"
) -> go.Figure:
    """
    Create an interactive chart showing historical data, forecast, and confidence intervals.
    
    Args:
        historical_df: DataFrame with historical data (date, cost_usd)
        forecast_df: DataFrame with forecast data (date, forecast_cost_usd, lower_bound_80, upper_bound_80, etc.)
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    # Historical data
    if 'service_name' in historical_df.columns:
        hist_daily = historical_df.groupby('date')['cost_usd'].sum().reset_index()
    else:
        hist_daily = historical_df[['date', 'cost_usd']].copy()
    
    fig.add_trace(go.Scatter(
        x=hist_daily['date'],
        y=hist_daily['cost_usd'],
        mode='lines',
        name='Historical Spend',
        line=dict(color='blue')
    ))
    
    # Forecast
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['forecast_cost_usd'],
        mode='lines',
        name='Forecast',
        line=dict(color='orange')
    ))
    
    # Confidence intervals
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['upper_bound_80'],
        fill=None,
        mode='lines',
        line_color='rgba(0,100,80,0)',
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df['date'],
        y=forecast_df['lower_bound_80'],
        fill='tonexty',
        mode='lines',
        line_color='rgba(0,100,80,0)',
        name='80% Confidence Interval',
        fillcolor='rgba(255,165,0,0.2)'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Cost (USD)',
        hovermode='x unified'
    )
    
    return fig

def plot_anomalies(
    df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    title: str = "Cloud Spend Anomalies"
) -> go.Figure:
    """
    Create an interactive chart showing historical spending with anomaly points highlighted.
    
    Args:
        df: DataFrame with historical data (date, cost_usd)
        anomaly_df: DataFrame with anomaly data (date, cost_usd, anomaly_score, etc.)
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    # Historical data
    if 'service_name' in df.columns:
        hist_daily = df.groupby('date')['cost_usd'].sum().reset_index()
    else:
        hist_daily = df[['date', 'cost_usd']].copy()
    
    fig.add_trace(go.Scatter(
        x=hist_daily['date'],
        y=hist_daily['cost_usd'],
        mode='lines',
        name='Normal Spend',
        line=dict(color='blue')
    ))
    
    # Anomalies
    if not anomaly_df.empty:
        if 'service_name' in anomaly_df.columns:
            anomaly_daily = anomaly_df.groupby('date')['cost_usd'].sum().reset_index()
        else:
            anomaly_daily = anomaly_df[['date', 'cost_usd']].copy()
        
        fig.add_trace(go.Scatter(
            x=anomaly_daily['date'],
            y=anomaly_daily['cost_usd'],
            mode='markers',
            name='Anomalies',
            marker=dict(
                color='red',
                size=10,
                symbol='x',
                line=dict(width=2, color='DarkSlateGrey')
            )
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Cost (USD)',
        hovermode='x unified'
    )
    
    return fig

def create_spending_by_service_chart(df: pd.DataFrame, title: str = "Spending by Service") -> go.Figure:
    """
    Create a bar chart showing total spending by service.
    
    Args:
        df: DataFrame with columns ['service_name', 'cost_usd']
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    if 'service_name' not in df.columns:
        # Create a dummy service column if not present
        df = df.copy()
        df['service_name'] = 'Unknown'
    
    service_spend = df.groupby('service_name')['cost_usd'].sum().reset_index()
    service_spend = service_spend.sort_values('cost_usd', ascending=False)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=service_spend['service_name'],
        y=service_spend['cost_usd'],
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Service',
        yaxis_title='Total Cost (USD)',
        xaxis_tickangle=-45
    )
    
    return fig

def create_monthly_trend_chart(df: pd.DataFrame, title: str = "Monthly Spend Trend") -> go.Figure:
    """
    Create a line chart showing monthly spending trends.
    
    Args:
        df: DataFrame with columns ['date', 'cost_usd']
        title: Chart title
    
    Returns:
        Plotly figure object
    """
    df_copy = df.copy()
    df_copy['date'] = pd.to_datetime(df_copy['date'])
    df_copy['month'] = df_copy['date'].dt.to_period('M')
    
    monthly_spend = df_copy.groupby('month')['cost_usd'].sum().reset_index()
    monthly_spend['month_str'] = monthly_spend['month'].astype(str)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_spend['month_str'],
        y=monthly_spend['cost_usd'],
        mode='lines+markers',
        name='Monthly Spend',
        line=dict(color='green')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Month',
        yaxis_title='Total Cost (USD)'
    )
    
    return fig

def save_plot_as_html(fig: go.Figure, file_path: str):
    """
    Save a Plotly figure as an HTML file.
    
    Args:
        fig: Plotly figure object
        file_path: Path to save the HTML file
    """
    fig.write_html(file_path)
    logger.info(f"Saved plot to {file_path}")

def save_plot_as_image(fig: go.Figure, file_path: str, format: str = 'png', width: int = 1200, height: int = 800):
    """
    Save a Plotly figure as an image file.
    
    Args:
        fig: Plotly figure object
        file_path: Path to save the image file
        format: Image format (png, jpg, svg, pdf)
        width: Image width in pixels
        height: Image height in pixels
    """
    fig.write_image(file_path, format=format, width=width, height=height)
    logger.info(f"Saved plot to {file_path}")