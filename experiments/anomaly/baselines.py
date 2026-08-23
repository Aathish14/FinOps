#!/usr/bin/env python3
"""
Anomaly Detection Baselines and Evaluation Framework

Implements:
- Method A: Simple threshold (cost > mean + k*std)
- Method B: Isolation Forest on raw cost
- Method C: Isolation Forest on forecast residuals (current approach)
- Evaluation with ground truth labels
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, precision_recall_curve, auc
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ThresholdAnomalyDetector:
    """Simple threshold-based anomaly detection: cost > mean + k*std."""
    
    def __init__(self, k: float = 2.0, window: int = 30):
        self.k = k
        self.window = window
        self.mean = None
        self.std = None
        self.is_fitted = False
    
    def fit(self, data: pd.DataFrame) -> 'ThresholdAnomalyDetector':
        """Compute threshold from training data."""
        if 'cost_usd' in data.columns:
            values = data['cost_usd'].values
        elif 'y' in data.columns:
            values = data['y'].values
        else:
            values = data.iloc[:, -1].values
        
        self.mean = np.mean(values)
        self.std = np.std(values)
        self.threshold = self.mean + self.k * self.std
        self.is_fitted = True
        logger.info(f"Threshold detector fitted: mean={self.mean:.2f}, std={self.std:.2f}, threshold={self.threshold:.2f}")
        return self
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomalies (1=anomaly, 0=normal)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        if 'cost_usd' in data.columns:
            values = data['cost_usd'].values
        elif 'y' in data.columns:
            values = data['y'].values
        else:
            values = data.iloc[:, -1].values
        
        return (values > self.threshold).astype(int)
    
    def score_samples(self, data: pd.DataFrame) -> np.ndarray:
        """Return anomaly scores (distance from threshold, normalized)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        if 'cost_usd' in data.columns:
            values = data['cost_usd'].values
        elif 'y' in data.columns:
            values = data['y'].values
        else:
            values = data.iloc[:, -1].values
        
        # Score = how many stds above mean (negative = normal)
        scores = (values - self.mean) / (self.std + 1e-8)
        return scores


class RawCostIsolationForest:
    """Isolation Forest on raw cost values."""
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42, **kwargs):
        self.contamination = contamination
        self.random_state = random_state
        self.kwargs = kwargs
        self.model = None
        self.is_fitted = False
    
    def fit(self, data: pd.DataFrame) -> 'RawCostIsolationForest':
        """Fit Isolation Forest on raw cost."""
        if 'cost_usd' in data.columns:
            X = data[['cost_usd']].values
        elif 'y' in data.columns:
            X = data[['y']].values
        else:
            X = data.iloc[:, -1:].values
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            **self.kwargs
        )
        self.model.fit(X)
        self.is_fitted = True
        logger.info(f"Raw-cost IF fitted on {len(X)} samples, contamination={self.contamination}")
        return self
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomalies (1=anomaly, 0=normal)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        if 'cost_usd' in data.columns:
            X = data[['cost_usd']].values
        elif 'y' in data.columns:
            X = data[['y']].values
        else:
            X = data.iloc[:, -1:].values
        
        preds = self.model.predict(X)
        return (preds == -1).astype(int)  # Convert -1/1 to 1/0
    
    def score_samples(self, data: pd.DataFrame) -> np.ndarray:
        """Return anomaly scores (more negative = more anomalous)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        if 'cost_usd' in data.columns:
            X = data[['cost_usd']].values
        elif 'y' in data.columns:
            X = data[['y']].values
        else:
            X = data.iloc[:, -1:].values
        
        return self.model.score_samples(X)


class ResidualIsolationForest:
    """Isolation Forest on forecast residuals."""
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42, **kwargs):
        self.contamination = contamination
        self.random_state = random_state
        self.kwargs = kwargs
        self.model = None
        self.is_fitted = False
    
    def fit(self, residuals: np.ndarray) -> 'ResidualIsolationForest':
        """Fit Isolation Forest on residuals."""
        X = residuals.reshape(-1, 1)
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            **self.kwargs
        )
        self.model.fit(X)
        self.is_fitted = True
        logger.info(f"Residual IF fitted on {len(X)} samples, contamination={self.contamination}")
        return self
    
    def predict(self, residuals: np.ndarray) -> np.ndarray:
        """Predict anomalies (1=anomaly, 0=normal)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        X = residuals.reshape(-1, 1)
        preds = self.model.predict(X)
        return (preds == -1).astype(int)
    
    def score_samples(self, residuals: np.ndarray) -> np.ndarray:
        """Return anomaly scores."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        X = residuals.reshape(-1, 1)
        return self.model.score_samples(X)


def compute_residuals(actual: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """Compute residuals = actual - predicted."""
    return actual - predicted


def evaluate_anomaly_detection(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_scores: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """Evaluate anomaly detection with ground truth labels."""
    metrics = {}
    
    # Basic metrics
    metrics['precision'] = float(precision_score(y_true, y_pred, zero_division=0))
    metrics['recall'] = float(recall_score(y_true, y_pred, zero_division=0))
    metrics['f1'] = float(f1_score(y_true, y_pred, zero_division=0))
    
    # PR-AUC if scores available
    if y_scores is not None:
        # For Isolation Forest, more negative = more anomalous
        # Convert to positive anomaly scores
        anomaly_scores = -y_scores if y_scores.min() < 0 else y_scores
        try:
            precision, recall, _ = precision_recall_curve(y_true, anomaly_scores)
            metrics['pr_auc'] = float(auc(recall, precision))
        except Exception as e:
            logger.warning(f"Could not compute PR-AUC: {e}")
            metrics['pr_auc'] = None
    else:
        metrics['pr_auc'] = None
    
    # Count metrics
    metrics['n_true_anomalies'] = int(y_true.sum())
    metrics['n_predicted_anomalies'] = int(y_pred.sum())
    metrics['n_true_positives'] = int((y_true & y_pred).sum())
    metrics['n_false_positives'] = int((~y_true & y_pred).sum())
    metrics['n_false_negatives'] = int((y_true & ~y_pred).sum())
    
    return metrics


def run_anomaly_comparison(
    test_data: pd.DataFrame,
    test_actual: np.ndarray,
    test_predicted: np.ndarray,
    ground_truth: pd.DataFrame,
    contamination: float = 0.05
) -> Dict:
    """
    Run all three anomaly detection methods and compare.
    
    Args:
        test_data: DataFrame with 'cost_usd' column
        test_actual: Actual cost values
        test_predicted: Forecasted cost values
        ground_truth: DataFrame with anomaly labels
        contamination: Contamination parameter for Isolation Forest
    
    Returns:
        Dictionary with results for each method
    """
    # Prepare ground truth labels
    y_true = ground_truth['is_anomaly'].values if 'is_anomaly' in ground_truth.columns else np.zeros(len(test_data))
    
    # Compute residuals
    residuals = compute_residuals(test_actual, test_predicted)
    
    results = {}
    
    # Method A: Threshold
    logger.info("Running Threshold detector...")
    threshold_detector = ThresholdAnomalyDetector(k=2.0, window=30)
    threshold_detector.fit(test_data)
    y_pred_a = threshold_detector.predict(test_data)
    y_scores_a = threshold_detector.score_samples(test_data)
    results['Threshold'] = evaluate_anomaly_detection(y_true, y_pred_a, y_scores_a)
    
    # Method B: Raw-cost Isolation Forest
    logger.info("Running Raw-cost Isolation Forest...")
    raw_if = RawCostIsolationForest(contamination=contamination)
    raw_if.fit(test_data)
    y_pred_b = raw_if.predict(test_data)
    y_scores_b = raw_if.score_samples(test_data)
    results['RawCost_IF'] = evaluate_anomaly_detection(y_true, y_pred_b, y_scores_b)
    
    # Method C: Residual Isolation Forest
    logger.info("Running Residual Isolation Forest...")
    resid_if = ResidualIsolationForest(contamination=contamination)
    resid_if.fit(residuals)
    y_pred_c = resid_if.predict(residuals)
    y_scores_c = resid_if.score_samples(residuals)
    results['Residual_IF'] = evaluate_anomaly_detection(y_true, y_pred_c, y_scores_c)
    
    return results


def create_ground_truth_labels(
    test_data: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    provider: Optional[str] = None
) -> pd.DataFrame:
    """Create ground truth labels for test period from anomaly metadata."""
    test_data = test_data.copy()
    test_data['is_anomaly'] = 0
    test_data['anomaly_type'] = ''
    
    for _, anomaly in anomaly_df.iterrows():
        if provider is not None:
            # For provider-specific data, just match date
            mask = (test_data['date'] == anomaly['date'])
        else:
            # For combined data, match both date and provider
            mask = (test_data['date'] == anomaly['date']) & (test_data['provider'] == anomaly['provider'])
        test_data.loc[mask, 'is_anomaly'] = 1
        test_data.loc[mask, 'anomaly_type'] = anomaly['anomaly_type']
    
    return test_data


def run_rolling_anomaly_evaluation(
    data: pd.DataFrame,
    forecast_results: Dict,
    anomaly_df: pd.DataFrame,
    initial_train_days: int = 90,
    test_horizon: int = 7,
    step: int = 7,
    contamination: float = 0.05
) -> Dict:
    """
    Run rolling-origin anomaly detection evaluation.
    
    For each fold, compute residuals on test period and evaluate
    all three anomaly detection methods.
    """
    # This is a simplified version - in practice would need to
    # re-fit forecasting model for each fold
    pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test with synthetic benchmark
    detailed = pd.read_csv('data/synthetic_benchmark_detailed.csv')
    anomalies = pd.read_csv('data/ground_truth_anomalies.csv')
    
    # Test with AWS data
    aws_data = detailed[detailed['provider'] == 'AWS'].copy()
    aws_data = aws_data.groupby('date')['cost_usd'].sum().reset_index()
    aws_data = aws_data.rename(columns={'cost_usd': 'y'})
    
    # Create ground truth for anomaly evaluation
    aws_anomalies = anomalies[anomalies['provider'] == 'AWS']
    aws_data_labeled = create_ground_truth_labels(aws_data, aws_anomalies)
    
    # Use simple forecast for testing (naive)
    from experiments.forecasting.baselines import NaiveForecaster
    
    # Train naive forecaster on first 90 days
    train_data = aws_data_labeled.iloc[:90].copy()
    test_data = aws_data_labeled.iloc[90:].copy()
    
    naive = NaiveForecaster()
    naive.fit(train_data)
    
    test_actual = test_data['y'].values
    preds = naive.predict(len(test_data))
    test_predicted = preds['yhat'].values
    
    # Run anomaly comparison
    test_actual_series = test_actual
    test_data_for_anomaly = test_data.copy()
    test_data_for_anomaly = test_data_for_anomaly.rename(columns={'y': 'cost_usd'})
    
    results = run_anomaly_comparison(
        test_data_for_anomaly,
        test_actual_series,
        test_predicted,
        test_data_labeled,
        contamination=0.05
    )
    
    print("\n=== Anomaly Detection Comparison ===")
    for method, metrics in results.items():
        print(f"\n{method}:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")