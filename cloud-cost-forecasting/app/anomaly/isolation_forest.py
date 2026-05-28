import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import logging
from typing import Union, List
import mlflow
import mlflow.sklearn

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, contamination: float = 0.03, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=200,
            max_features=1.0,
            bootstrap=False
        )
        self.is_fitted = False
        
    def fit(self, feature_data: pd.DataFrame) -> 'AnomalyDetector':
        """Fit the Isolation Forest model."""
        logger.info(f"Fitting Isolation Forest with {len(feature_data)} samples")
        self.model.fit(feature_data)
        self.is_fitted = True
        return self
    
    def predict(self, feature_data: pd.DataFrame) -> np.ndarray:
        """Predict anomalies (-1 for anomalies, 1 for normal)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        return self.model.predict(feature_data)
    
    def score_samples(self, feature_data: pd.DataFrame) -> np.ndarray:
        """Return the anomaly scores of the samples."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before scoring samples")
        return self.model.score_samples(feature_data)
    
    def evaluate(self, feature_data: pd.DataFrame, true_labels: np.ndarray) -> dict:
        """Evaluate the model if true labels are available."""
        from sklearn.metrics import classification_report, confusion_matrix
        if not self.is_fitted:
            raise ValueError("Model must be fitted before evaluation")
        predictions = self.predict(feature_data)
        # Convert Isolation Forest output: -1 -> 1 (anomaly), 1 -> 0 (normal)
        y_pred = np.where(predictions == -1, 1, 0)
        report = classification_report(true_labels, y_pred, output_dict=True)
        cm = confusion_matrix(true_labels, y_pred)
        return {
            'classification_report': report,
            'confusion_matrix': cm.tolist()
        }

def create_anomaly_detector(contamination: float = 0.03, random_state: int = 42) -> AnomalyDetector:
    """Factory function to create an anomaly detector."""
    return AnomalyDetector(contamination=contamination, random_state=random_state)
