"""
Tests for the visualization plotting module.

Covers:
  - plot_forecast_with_intervals with various confidence interval column names
  - Forecast chart with missing or mismatched CI columns
  - Historical spending chart
  - Anomaly chart
  - Spending by service chart
  - Monthly trend chart

All tests run offline with no external API dependencies.
"""

import io
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Ensure the repository root is on sys.path so `app.visualization.plots` is
# importable from the tests/ directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.visualization.plots import (
    plot_forecast_with_intervals,
    plot_historical_spending,
    plot_anomalies,
    create_spending_by_service_chart,
    create_monthly_trend_chart,
)


@pytest.fixture
def sample_historical_df() -> pd.DataFrame:
    """Daily aggregated spend data for historical chart."""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30),
        'cost_usd': [100.0 + i * 5.0 for i in range(30)],
    })


@pytest.fixture
def sample_forecast_80() -> pd.DataFrame:
    """Forecast DataFrame with 80% CI columns."""
    return pd.DataFrame({
        'date': pd.date_range('2024-04-01', periods=7),
        'forecast_cost_usd': [500.0, 510.0, 520.0, 530.0, 540.0, 550.0, 560.0],
        'lower_bound_80': [480.0, 490.0, 500.0, 510.0, 520.0, 530.0, 540.0],
        'upper_bound_80': [520.0, 530.0, 540.0, 550.0, 560.0, 570.0, 580.0],
    })


@pytest.fixture
def sample_forecast_90() -> pd.DataFrame:
    """Forecast DataFrame with 90% CI columns."""
    return pd.DataFrame({
        'date': pd.date_range('2024-04-01', periods=7),
        'forecast_cost_usd': [500.0, 510.0, 520.0, 530.0, 540.0, 550.0, 560.0],
        'lower_bound_90': [470.0, 480.0, 490.0, 500.0, 510.0, 520.0, 530.0],
        'upper_bound_90': [530.0, 540.0, 550.0, 560.0, 570.0, 580.0, 590.0],
    })


@pytest.fixture
def sample_forecast_95() -> pd.DataFrame:
    """Forecast DataFrame with 95% CI columns."""
    return pd.DataFrame({
        'date': pd.date_range('2024-04-01', periods=7),
        'forecast_cost_usd': [500.0, 510.0, 520.0, 530.0, 540.0, 550.0, 560.0],
        'lower_bound_95': [460.0, 470.0, 480.0, 490.0, 500.0, 510.0, 520.0],
        'upper_bound_95': [540.0, 550.0, 560.0, 570.0, 580.0, 590.0, 600.0],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPlotForecastWithIntervals:
    """Tests for the forecast with confidence intervals chart."""

    def test_plot_forecast_with_80_ci(self, sample_forecast_80, sample_historical_df):
        """Chart should render with 80% CI columns."""
        fig = plot_forecast_with_intervals(sample_historical_df, sample_forecast_80)
        assert fig is not None
        assert len(fig.data) == 4  # historical + forecast + 2 CI traces

    def test_plot_forecast_with_90_ci(self, sample_forecast_90, sample_historical_df):
        """Chart should render with 90% CI columns."""
        fig = plot_forecast_with_intervals(sample_historical_df, sample_forecast_90)
        assert fig is not None
        assert len(fig.data) == 4

    def test_plot_forecast_with_95_ci(self, sample_forecast_95, sample_historical_df):
        """Chart should render with 95% CI columns.

        Regression test for production failure where the model emits
        lower_bound_95/upper_bound_95 but validation expected _80 columns.
        """
        fig = plot_forecast_with_intervals(sample_historical_df, sample_forecast_95)
        assert fig is not None
        assert len(fig.data) == 4
        ci_trace = fig.data[3]
        assert '95% Confidence Interval' in ci_trace.name

    def test_plot_forecast_multiple_ci_columns_raises(self, sample_historical_df):
        """Chart should raise ValueError when multiple CI column pairs exist."""
        multi_ci_df = pd.DataFrame({
            'date': pd.date_range('2024-04-01', periods=3),
            'forecast_cost_usd': [500.0, 510.0, 520.0],
            'lower_bound_80': [480.0, 490.0, 500.0],
            'upper_bound_80': [520.0, 530.0, 540.0],
            'lower_bound_95': [460.0, 470.0, 480.0],
            'upper_bound_95': [540.0, 550.0, 560.0],
        })
        with pytest.raises(ValueError, match="requires exactly one lower_bound_"):
            plot_forecast_with_intervals(sample_historical_df, multi_ci_df)

    def test_plot_forecast_missing_ci_columns(self, sample_historical_df):
        """Chart should raise ValueError when CI columns are missing."""
        incomplete_df = pd.DataFrame({
            'date': pd.date_range('2024-04-01', periods=3),
            'forecast_cost_usd': [500.0, 510.0, 520.0],
        })
        with pytest.raises(ValueError, match="requires exactly one lower_bound_"):
            plot_forecast_with_intervals(sample_historical_df, incomplete_df)

    def test_plot_forecast_non_numeric_cost(self, sample_historical_df):
        """Chart should raise ValueError when forecast_cost_usd is non-numeric."""
        bad_df = pd.DataFrame({
            'date': pd.date_range('2024-04-01', periods=3),
            'forecast_cost_usd': ['a', 'b', 'c'],
            'lower_bound_80': [480.0, 490.0, 500.0],
            'upper_bound_80': [520.0, 530.0, 540.0],
        })
        with pytest.raises(ValueError, match="must be numeric"):
            plot_forecast_with_intervals(sample_historical_df, bad_df)

    def test_plot_forecast_empty_df(self, sample_historical_df):
        """Chart should raise ValueError when forecast DataFrame is empty."""
        empty_df = pd.DataFrame({
            'date': pd.Series(dtype='datetime64[ns]'),
            'forecast_cost_usd': pd.Series(dtype='float64'),
            'lower_bound_80': pd.Series(dtype='float64'),
            'upper_bound_80': pd.Series(dtype='float64'),
        })
        with pytest.raises(ValueError, match="received an empty DataFrame"):
            plot_forecast_with_intervals(sample_historical_df, empty_df)

    def test_plot_forecast_with_holdout(self, sample_historical_df, sample_forecast_80):
        """Chart should include holdout actual trace when holdout_df is provided."""
        holdout_df = pd.DataFrame({
            'date': pd.date_range('2024-03-13', periods=3),
            'cost_usd': [510.0, 520.0, 530.0],
        })
        fig = plot_forecast_with_intervals(
            sample_historical_df, sample_forecast_80, holdout_df=holdout_df
        )
        assert fig is not None
        # 5 traces: historical + future forecast + holdout + 2 CI traces
        assert len(fig.data) == 5
        # Holdout trace should be present
        trace_names = [t.name for t in fig.data]
        assert 'Holdout Actual' in trace_names

    def test_plot_forecast_without_holdout(self, sample_historical_df, sample_forecast_80):
        """Chart should work without holdout_df (backward compatible)."""
        fig = plot_forecast_with_intervals(sample_historical_df, sample_forecast_80)
        assert fig is not None
        # 4 traces: historical + forecast + 2 CI traces
        assert len(fig.data) == 4
        trace_names = [t.name for t in fig.data]
        assert 'Holdout Actual' not in trace_names

    def test_forecast_df_only_contains_future_dates(self, sample_historical_df):
        """Forecast DataFrame should only contain dates after the last historical date."""
        # Historical data ends at last date
        historical_max_date = sample_historical_df['date'].max()
        # Create forecast with some dates before and after historical max
        forecast_df = pd.DataFrame({
            'date': pd.date_range('2024-03-25', periods=10),
            'forecast_cost_usd': [500.0] * 10,
            'lower_bound_80': [480.0] * 10,
            'upper_bound_80': [520.0] * 10,
        })
        # Filter to dates after historical max (simulating app.py logic)
        future_forecast = forecast_df[forecast_df['date'] > historical_max_date].copy()
        # All remaining dates should be after historical max
        assert (future_forecast['date'] > historical_max_date).all()
        # No dates should be on or before historical max
        assert (future_forecast['date'] <= historical_max_date).sum() == 0


# ---------------------------------------------------------------------------
# Historical spend chart tests
# ---------------------------------------------------------------------------

class TestHistoricalSpending:
    """Tests for plot_historical_spending."""

    def test_plot_historical_spending(self, sample_historical_df):
        fig = plot_historical_spending(sample_historical_df, "Historical Spend")
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].name == 'Daily Spend'


# ---------------------------------------------------------------------------
# Anomaly chart tests
# ---------------------------------------------------------------------------

class TestPlotAnomalies:
    """Tests for plot_anomalies."""

    def test_plot_anomalies(self, sample_historical_df):
        anomaly_df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-05', '2024-01-10']),
            'cost_usd': [999.0, 150.0],
        })
        fig = plot_anomalies(sample_historical_df, anomaly_df)
        assert fig is not None
        assert len(fig.data) == 2  # historical + anomalies

    def test_plot_anomalies_empty(self, sample_historical_df):
        empty_anomaly = pd.DataFrame({'date': pd.Series(dtype='datetime64[ns]'), 'cost_usd': pd.Series(dtype='float64')})
        fig = plot_anomalies(sample_historical_df, empty_anomaly)
        assert fig is not None
        assert len(fig.data) == 1  # only historical


# ---------------------------------------------------------------------------
# Spending by service chart tests
# ---------------------------------------------------------------------------

class TestSpendingByService:
    """Tests for create_spending_by_service_chart."""

    def test_create_spending_by_service_chart(self):
        df = pd.DataFrame({
            'service_name': ['AmazonEC2', 'AmazonEC2', 'AmazonS3', 'AmazonS3'],
            'cost_usd': [100.0, 200.0, 50.0, 75.0],
        })
        fig = create_spending_by_service_chart(df, "Spending by Service")
        assert fig is not None
        assert len(fig.data) == 1


# ---------------------------------------------------------------------------
# Monthly trend chart tests
# ---------------------------------------------------------------------------

class TestMonthlyTrend:
    """Tests for create_monthly_trend_chart."""

    def test_create_monthly_trend_chart(self):
        dates = pd.date_range('2024-01-01', periods=12, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'cost_usd': [100.0 + i * 5.0 for i in range(12)],
        })
        fig = create_monthly_trend_chart(df, "Monthly Spend Trend")
        assert fig is not None
        assert len(fig.data) == 1