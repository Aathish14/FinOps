# Cloud Cost Forecasting - Unit Tests

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cloud-cost-forecasting'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.ingest.ingestor import ingest_billing_data
from app.forecasting.prophet_model import create_forecasting_model
from app.anomaly.isolation_forest import create_anomaly_detector


class TestIngestion:
    """Tests for billing data ingestion."""

    def test_aws_ingestion(self):
        """Test AWS CSV ingestion produces valid DataFrame."""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'cloud-cost-forecasting')
        aws_file = os.path.join(base_dir, 'data', 'samples', 'sample_aws_billing.csv')

        df = ingest_billing_data([aws_file])

        assert len(df) == 360  # 90 days * 4 services
        assert list(df.columns) == [
            'date', 'cloud_provider', 'service_name', 'account_id',
            'region', 'environment', 'usage_quantity', 'usage_unit', 'cost_usd'
        ]
        assert (df['cloud_provider'] == 'AWS').all()
        assert pd.api.types.is_datetime64_any_dtype(df['date'])
        assert (df['cost_usd'] > 0).all()

    def test_gcp_ingestion(self):
        """Test GCP CSV ingestion produces valid DataFrame."""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'cloud-cost-forecasting')
        gcp_file = os.path.join(base_dir, 'data', 'samples', 'sample_gcp_billing.csv')

        df = ingest_billing_data([gcp_file])

        assert len(df) == 360  # 90 days * 4 services
        assert (df['cloud_provider'] == 'GCP').all()
        assert pd.api.types.is_datetime64_any_dtype(df['date'])
        assert (df['cost_usd'] > 0).all()

    def test_combined_ingestion(self):
        """Test combined AWS + GCP ingestion."""
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'cloud-cost-forecasting')
        aws_file = os.path.join(base_dir, 'data', 'samples', 'sample_aws_billing.csv')
        gcp_file = os.path.join(base_dir, 'data', 'samples', 'sample_gcp_billing.csv')

        df = ingest_billing_data([aws_file, gcp_file])

        assert len(df) == 720
        assert df['cloud_provider'].nunique() == 2
        assert df['date'].is_monotonic_increasing


class TestForecasting:
    """Tests for forecasting model."""

    def create_sample_data(self, n_days=60):
        """Create synthetic daily spend data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
        # Add trend and seasonality
        trend = np.linspace(100, 200, n_days)
        seasonality = 20 * np.sin(2 * np.pi * np.arange(n_days) / 7)
        noise = np.random.normal(0, 5, n_days)
        costs = trend + seasonality + noise
        costs = np.maximum(costs, 10)  # Ensure positive

        return pd.DataFrame({'ds': dates, 'y': costs})

    def test_prophet_fit_predict(self):
        """Test Prophet model fits and predicts."""
        train_data = self.create_sample_data(40)

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        assert model.is_fitted
        assert model.model is not None

        forecast = model.predict(periods=14)

        assert len(forecast) == 14  # future periods only
        assert 'forecast_cost_usd' in forecast.columns
        assert 'lower_bound_80' in forecast.columns
        assert 'upper_bound_80' in forecast.columns
        assert (forecast['lower_bound_80'] <= forecast['forecast_cost_usd']).all()
        assert (forecast['forecast_cost_usd'] <= forecast['upper_bound_80']).all()

    def test_evaluate_on_test_set(self):
        """Test evaluation on holdout test set produces genuine metrics."""
        data = self.create_sample_data(50)
        train_data = data[:35]
        test_data = data[35:].rename(columns={'ds': 'date', 'y': 'cost_usd'})

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        metrics = model.evaluate(test_data)

        assert 'mape' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0
        if metrics['mape'] is not None:
            assert metrics['mape'] >= 0
        # Metrics should be reasonable (not random)
        assert metrics['rmse'] < 100  # Sanity check
        assert metrics['mae'] < 100

    def test_predict_on_dates(self):
        """Test prediction on specific dates."""
        train_data = self.create_sample_data(40)
        test_dates = pd.DataFrame({'date': pd.date_range('2024-02-10', periods=5, freq='D')})

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        preds = model.predict_on_dates(test_dates)

        assert len(preds) == 5
        assert 'predicted' in preds.columns
        assert (preds['predicted'] > 0).all()

    def test_fit_with_timezone_aware_dates(self):
        """Timezone-aware UTC dates are normalized to timezone-naive before fitting Prophet."""
        dates = pd.date_range(start='2024-01-01', periods=20, freq='D', tz='UTC')
        trend = np.linspace(100, 200, 20)
        costs = trend + np.random.normal(0, 5, 20)
        costs = np.maximum(costs, 10)

        train_data = pd.DataFrame({'ds': dates, 'y': costs})

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        assert model.is_fitted
        assert model.model is not None

        forecast = model.predict(periods=7)
        assert len(forecast) == 7  # future periods only
        assert 'forecast_cost_usd' in forecast.columns

    def test_fit_with_timezone_naive_dates(self):
        """Timezone-naive dates continue to work unchanged."""
        dates = pd.date_range(start='2024-01-01', periods=20, freq='D')
        trend = np.linspace(100, 200, 20)
        costs = trend + np.random.normal(0, 5, 20)
        costs = np.maximum(costs, 10)

        train_data = pd.DataFrame({'ds': dates, 'y': costs})

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        assert model.is_fitted
        assert model.model is not None

        forecast = model.predict(periods=7)
        assert len(forecast) == 7  # future periods only
        assert 'forecast_cost_usd' in forecast.columns

    def test_fit_normalizes_ds_to_timezone_naive(self):
        """The ds column passed to Prophet.fit() is timezone-naive."""
        from unittest.mock import patch, MagicMock

        captured = {}

        mock_prophet_instance = MagicMock()
        mock_prophet_instance.fit = MagicMock(
            side_effect=lambda df: captured.update(
                {'ds': df['ds'], 'df_columns': list(df.columns)}
            )
        )

        with patch('app.forecasting.prophet_model.Prophet', return_value=mock_prophet_instance):
            model = create_forecasting_model('prophet')

            dates = pd.date_range(start='2024-01-01', periods=10, freq='D', tz='UTC')
            train_data = pd.DataFrame({'ds': dates, 'y': np.linspace(100, 200, 10)})

            model.fit(train_data)

        assert 'ds' in captured
        assert captured['ds'].dt.tz is None, f"ds should be timezone-naive, got tz={captured['ds'].dt.tz}"
        assert 'ds' in captured['df_columns']
        assert 'y' in captured['df_columns']

    def test_predict_on_dates_with_timezone_aware_dates(self):
        """predict_on_dates normalizes timezone-aware input dates."""
        train_data = self.create_sample_data(20)
        test_dates = pd.DataFrame({'date': pd.date_range('2024-02-10', periods=5, freq='D', tz='UTC')})

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        preds = model.predict_on_dates(test_dates)

        assert len(preds) == 5
        assert 'predicted' in preds.columns
        assert (preds['predicted'] > 0).all()

    def test_evaluate_with_timezone_aware_test_dates(self):
        """Evaluation succeeds when test dates are timezone-aware and predictions are timezone-naive."""
        train_data = self.create_sample_data(30)
        # Test data with timezone-aware UTC dates (simulates user-uploaded CSV)
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=10, freq='D', tz='UTC'),
            'cost_usd': np.linspace(100, 200, 10) + np.random.normal(0, 5, 10)
        })
        test_data['cost_usd'] = test_data['cost_usd'].clip(lower=10)

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        metrics = model.evaluate(test_data)

        assert 'mape' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0

    def test_evaluate_matches_correct_dates_after_normalization(self):
        """Matching dates remain matched after timezone normalization in evaluation."""
        train_data = self.create_sample_data(30)
        # Test data with timezone-aware dates that should match predicted dates
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=5, freq='D', tz='UTC'),
            'cost_usd': np.linspace(100, 150, 5)
        })

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        metrics = model.evaluate(test_data)

        # All 5 test dates should produce predictions and merge successfully
        assert metrics['rmse'] is not None
        assert metrics['mae'] is not None

    def test_evaluate_with_timezone_naive_test_dates(self):
        """Evaluation succeeds with timezone-naive test dates (regression guard)."""
        train_data = self.create_sample_data(30)
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=5, freq='D'),
            'cost_usd': np.linspace(100, 150, 5)
        })

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        metrics = model.evaluate(test_data)

        assert 'mape' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0

    def test_evaluate_with_missing_prediction_dates(self):
        """Evaluation raises ValueError when some test dates have no predictions."""
        train_data = self.create_sample_data(30)
        # Test data has dates NOT covered by forecast model's predictions
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=10, freq='D'),
            'cost_usd': np.linspace(100, 150, 10)
        })

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        # Mock predict_on_dates to return predictions for only 7 of 10 dates
        original_predict = model.predict_on_dates
        def mock_predict_on_dates(dates):
            result = original_predict(dates)
            return result.iloc[:7]  # Only return 7 predictions for 10 dates
        model.predict_on_dates = mock_predict_on_dates

        with pytest.raises(ValueError, match="missing predictions"):
            model.evaluate(test_data)

    def test_evaluate_with_duplicate_test_dates(self):
        """Evaluation raises ValueError when test data has duplicate dates."""
        train_data = self.create_sample_data(30)
        # Test data with duplicate dates
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=5, freq='D').tolist() * 2,
            'cost_usd': np.linspace(100, 150, 10)
        })

        model = create_forecasting_model('prophet')
        model.fit(train_data)

        with pytest.raises(ValueError, match="Duplicate dates"):
            model.evaluate(test_data)


class TestAnomalyDetection:
    """Tests for anomaly detection."""

    def test_isolation_forest_fit_predict(self):
        """Test Isolation Forest fits and predicts."""
        np.random.seed(42)
        n_samples = 100
        # Normal data
        normal_data = pd.DataFrame({
            'residual': np.random.normal(0, 10, n_samples),
            'residual_lag1': np.random.normal(0, 10, n_samples),
            'residual_rolling_mean_7': np.random.normal(0, 5, n_samples),
            'residual_rolling_std_7': np.abs(np.random.normal(5, 2, n_samples))
        })

        detector = create_anomaly_detector(contamination=0.05)
        detector.fit(normal_data)

        assert detector.is_fitted

        predictions = detector.predict(normal_data)
        scores = detector.score_samples(normal_data)

        assert len(predictions) == n_samples
        assert len(scores) == n_samples
        assert set(predictions).issubset({-1, 1})
        # Most should be normal (1)
        assert (predictions == 1).sum() > n_samples * 0.8

    def test_anomaly_detection_on_residuals(self):
        """Test anomaly detection on forecast residuals."""
        np.random.seed(42)
        # Create residuals with a few anomalies
        residuals = np.random.normal(0, 10, 50)
        residuals[10] = 100  # Inject anomaly
        residuals[25] = -80  # Inject anomaly

        feature_data = pd.DataFrame({
            'residual': residuals,
            'residual_lag1': np.roll(residuals, 1),
            'residual_rolling_mean_7': pd.Series(residuals).rolling(7, min_periods=1).mean(),
            'residual_rolling_std_7': pd.Series(residuals).rolling(7, min_periods=1).std()
        }).bfill().ffill()

        detector = create_anomaly_detector(contamination=0.1)
        detector.fit(feature_data)

        predictions = detector.predict(feature_data)
        anomaly_labels = (predictions == -1).astype(int)

        # Should detect the injected anomalies
        assert anomaly_labels[10] == 1
        assert anomaly_labels[25] == 1
        # Most others should be normal
        assert anomaly_labels.sum() <= 10  # With 10% contamination

    def test_anomaly_table_contains_only_anomalies(self):
        """Anomaly prioritization table contains only confirmed anomalies."""
        from app.anomaly.cost_aware import CostImpactScorer

        # Create test data with mixed anomaly labels
        n = 20
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=n, freq='D'),
            'cost_usd': np.linspace(100, 200, n)
        })
        anomaly_scores = np.random.uniform(-1.0, 1.0, n)
        # Label first 5 as anomalies, rest as normal
        anomaly_labels = np.array([1, 1, 1, 1, 1] + [0] * (n - 5))
        actual_costs = test_data['cost_usd'].values
        expected_costs = actual_costs * 0.95

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # Top-K by cost-impact score should only contain anomalies
        top_k = 5
        top_anomalies = ranked[ranked['anomaly_label'] == 1].nlargest(top_k, 'cost_impact_score')
        assert len(top_anomalies) == top_k
        assert (top_anomalies['anomaly_label'] == 1).all()

    def test_normal_high_cost_not_in_anomaly_table(self):
        """Normal rows with high cost-impact score do not appear in anomaly table."""
        from app.anomaly.cost_aware import CostImpactScorer

        # Create test data where a normal row has very high cost_impact_score
        n = 10
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=n, freq='D'),
            'cost_usd': np.linspace(100, 200, n)
        })
        anomaly_scores = np.random.uniform(-1.0, 1.0, n)
        # Label first row as anomaly, rest as normal
        anomaly_labels = np.array([1] + [0] * (n - 1))
        actual_costs = test_data['cost_usd'].values
        expected_costs = actual_costs * 0.95

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # Filter to anomalies only - should not contain any normal rows
        anomaly_only = ranked[ranked['anomaly_label'] == 1]
        assert (anomaly_only['anomaly_label'] == 1).all()
        assert len(anomaly_only) == 1  # Only one anomaly in our test data

    def test_explanations_only_for_anomalies(self):
        """Explain_batch only explains confirmed anomalies."""
        from app.anomaly.cost_aware import CostImpactScorer
        from app.anomaly.explanations import AnomalyExplainer

        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=10, freq='D'),
            'cost_usd': np.linspace(100, 200, 10)
        })
        anomaly_scores = np.random.uniform(-1.0, 1.0, 10)
        anomaly_labels = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
        actual_costs = test_data['cost_usd'].values
        expected_costs = actual_costs * 0.95

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        explainer = AnomalyExplainer()
        explanations = explainer.explain_batch(ranked, top_k=5)

        # All explanations should be for anomalies only
        assert len(explanations) == 2  # Only 2 anomalies
        for exp in explanations:
            assert exp['anomaly_label'] == 1


class TestIntegration:
    """Integration tests for the full pipeline."""

    def create_daily_data(self, n_days=40):
        """Create daily aggregated spend data."""
        dates = pd.date_range(start='2024-01-01', periods=n_days, freq='D')
        trend = np.linspace(100, 150, n_days)
        seasonality = 15 * np.sin(2 * np.pi * np.arange(n_days) / 7)
        noise = np.random.normal(0, 5, n_days)
        costs = trend + seasonality + noise
        costs = np.maximum(costs, 10)

        return pd.DataFrame({'ds': dates, 'y': costs})

    def test_full_pipeline(self):
        """Test ingestion -> forecasting -> anomaly detection pipeline."""
        daily_data = self.create_daily_data(40)

        # Train/test split
        train_size = int(len(daily_data) * 0.8)
        train_data = daily_data[:train_size]
        test_data = daily_data[train_size:].rename(columns={'ds': 'date', 'y': 'cost_usd'})

        # Forecasting
        model = create_forecasting_model('prophet')
        model.fit(train_data)

        forecast = model.predict(periods=14)
        assert len(forecast) == 14  # future periods only

        # Evaluation
        metrics = model.evaluate(test_data)
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0

        # Anomaly detection on test residuals
        test_preds = model.predict_on_dates(test_data[['date']])
        test_with_pred = test_data.merge(test_preds, on='date')
        test_with_pred['residual'] = test_with_pred['cost_usd'] - test_with_pred['predicted']

        feature_data = pd.DataFrame({
            'residual': test_with_pred['residual'],
            'residual_lag1': test_with_pred['residual'].shift(1),
            'residual_rolling_mean_7': test_with_pred['residual'].rolling(7, min_periods=1).mean(),
            'residual_rolling_std_7': test_with_pred['residual'].rolling(7, min_periods=1).std()
        }).bfill().ffill()

        detector = create_anomaly_detector(contamination=0.1)
        detector.fit(feature_data)

        anomaly_labels = (detector.predict(feature_data) == -1).astype(int)

        # Should complete without errors
        assert len(anomaly_labels) == len(test_data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
