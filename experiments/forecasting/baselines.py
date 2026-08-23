#!/usr/bin/env python3
"""
Forecasting Baselines and Evaluation Framework

Implements:
- Naive forecast (last value)
- Moving Average forecast
- Prophet (existing)
- Rolling-origin / walk-forward validation
- MAE, RMSE, MAPE, sMAPE metrics
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NaiveForecaster:
    """Naive forecast: next value = last observed value."""
    
    def __init__(self):
        self.last_value = None
        self.is_fitted = False
    
    def fit(self, train_data: pd.DataFrame) -> 'NaiveForecaster':
        """Fit the model (store last value)."""
        self.last_value = train_data['y'].iloc[-1]
        self.is_fitted = True
        return self
    
    def predict(self, periods: int) -> pd.DataFrame:
        """Generate naive forecast."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        forecast = pd.DataFrame({
            'yhat': [self.last_value] * periods,
            'yhat_lower': [self.last_value] * periods,
            'yhat_upper': [self.last_value] * periods
        })
        return forecast


class MovingAverageForecaster:
    """Moving Average forecast with configurable window."""
    
    def __init__(self, window: int = 7):
        self.window = window
        self.last_values = None
        self.is_fitted = False
    
    def fit(self, train_data: pd.DataFrame) -> 'MovingAverageForecaster':
        """Fit the model (store last window values)."""
        self.last_values = train_data['y'].tail(self.window).values
        self.is_fitted = True
        return self
    
    def predict(self, periods: int) -> pd.DataFrame:
        """Generate moving average forecast."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        ma_value = np.mean(self.last_values)
        forecast = pd.DataFrame({
            'yhat': [ma_value] * periods,
            'yhat_lower': [ma_value] * periods,
            'yhat_upper': [ma_value] * periods
        })
        return forecast


class ProphetForecaster:
    """Wrapper for Prophet with consistent interface."""
    
    def __init__(self, **prophet_kwargs):
        self.prophet_kwargs = prophet_kwargs
        self.model = None
        self.is_fitted = False
    
    def fit(self, train_data: pd.DataFrame) -> 'ProphetForecaster':
        """Fit Prophet model."""
        self.model = Prophet(**self.prophet_kwargs)
        df = train_data.rename(columns={'date': 'ds', 'cost_usd': 'y'})
        self.model.fit(df)
        self.is_fitted = True
        return self
    
    def predict(self, periods: int, freq: str = 'D') -> pd.DataFrame:
        """Generate Prophet forecast."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        forecast = self.model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    
    def predict_on_dates(self, dates: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions for specific dates."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
        
        future = pd.DataFrame({'ds': pd.to_datetime(dates['date'])})
        forecast = self.model.predict(future)
        return forecast[['ds', 'yhat']].rename(columns={'ds': 'date', 'yhat': 'predicted'})


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate forecast evaluation metrics."""
    metrics = {}
    
    # MAE
    metrics['mae'] = float(mean_absolute_error(y_true, y_pred))
    
    # RMSE
    metrics['rmse'] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    
    # MAPE (handle zero actuals)
    mask = y_true != 0
    if mask.any():
        metrics['mape'] = float(mean_absolute_percentage_error(y_true[mask], y_pred[mask]))
    else:
        metrics['mape'] = None
    
    # sMAPE (symmetric MAPE, handles zeros better)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
    smape_mask = denominator != 0
    if smape_mask.any():
        metrics['smape'] = float(np.mean(2 * np.abs(y_pred[smape_mask] - y_true[smape_mask]) / denominator[smape_mask]))
    else:
        metrics['smape'] = None
    
    return metrics


def rolling_origin_evaluation(
    data: pd.DataFrame,
    model_class,
    model_kwargs: dict,
    initial_train_days: int = 90,
    test_horizon: int = 7,
    step: int = 7,
    min_train_days: int = 60
) -> List[Dict]:
    """
    Perform rolling-origin (walk-forward) evaluation.
    
    Args:
        data: DataFrame with 'date' and 'cost_usd' columns
        model_class: Forecaster class to instantiate
        model_kwargs: Keyword arguments for model constructor
        initial_train_days: Days in initial training set
        test_horizon: Days to forecast in each fold
        step: Days to advance between folds
        min_train_days: Minimum training days required
    
    Returns:
        List of fold results with metrics
    """
    data = data.copy()
    data['date'] = pd.to_datetime(data['date'])
    data = data.sort_values('date').reset_index(drop=True)
    
    # Prepare data in Prophet format
    df = data[['date', 'cost_usd']].rename(columns={'date': 'ds', 'cost_usd': 'y'})
    
    n = len(df)
    results = []
    
    # Start with initial training window
    train_end = initial_train_days
    
    fold = 0
    while train_end + test_horizon <= n:
        fold += 1
        
        # Training data
        train_data = df.iloc[:train_end].copy()
        
        # Test data
        test_data = df.iloc[train_end:train_end + test_horizon].copy()
        
        if len(train_data) < min_train_days:
            logger.warning(f"Fold {fold}: Insufficient training data ({len(train_data)} days)")
            break
        
        # Fit model
        model = model_class(**model_kwargs)
        model.fit(train_data)
        
        # Predict
        if hasattr(model, 'predict_on_dates'):
            # Prophet-style
            preds = model.predict_on_dates(test_data[['ds']].rename(columns={'ds': 'date'}))
            y_pred = preds['predicted'].values
        else:
            # Naive/MA style
            preds = model.predict(test_horizon)
            y_pred = preds['yhat'].values
        
        y_true = test_data['y'].values
        
        # Evaluate
        metrics = evaluate_forecast(y_true, y_pred)
        
        # Store results
        fold_result = {
            'fold': fold,
            'train_start': df['ds'].iloc[0],
            'train_end': df['ds'].iloc[train_end - 1],
            'test_start': test_data['ds'].iloc[0],
            'test_end': test_data['ds'].iloc[-1],
            'train_size': len(train_data),
            'test_size': len(test_data),
            **metrics,
            'y_true': y_true.tolist(),
            'y_pred': y_pred.tolist()
        }
        results.append(fold_result)
        
        mape_str = f"{metrics['mape']:.4f}" if metrics['mape'] is not None else 'N/A'
        logger.info(f"Fold {fold}: Train {len(train_data)} days, Test {len(test_data)} days, "
                    f"MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}, "
                    f"MAPE={mape_str}")
        
        # Advance
        train_end += step
    
    return results


def evaluate_all_models(
    data: pd.DataFrame,
    initial_train_days: int = 90,
    test_horizon: int = 7,
    step: int = 7
) -> Dict[str, List[Dict]]:
    """Evaluate all forecasting models with rolling-origin validation."""
    
    models = {
        'Naive': (NaiveForecaster, {}),
        'MovingAverage_7': (MovingAverageForecaster, {'window': 7}),
        'MovingAverage_14': (MovingAverageForecaster, {'window': 14}),
        'MovingAverage_30': (MovingAverageForecaster, {'window': 30}),
        'Prophet': (ProphetForecaster, {}),
    }
    
    all_results = {}
    
    for name, (model_class, kwargs) in models.items():
        logger.info(f"\nEvaluating {name}...")
        try:
            results = rolling_origin_evaluation(
                data, model_class, kwargs,
                initial_train_days=initial_train_days,
                test_horizon=test_horizon,
                step=step
            )
            all_results[name] = results
        except Exception as e:
            logger.error(f"Error evaluating {name}: {e}")
            all_results[name] = []
    
    return all_results


def aggregate_results(results: List[Dict]) -> Dict[str, float]:
    """Aggregate fold results into summary statistics."""
    if not results:
        return {}
    
    metrics = ['mae', 'rmse', 'mape', 'smape']
    agg = {}
    
    for metric in metrics:
        values = [r[metric] for r in results if r[metric] is not None]
        if values:
            agg[f'{metric}_mean'] = float(np.mean(values))
            agg[f'{metric}_std'] = float(np.std(values))
            agg[f'{metric}_min'] = float(np.min(values))
            agg[f'{metric}_max'] = float(np.max(values))
        else:
            agg[f'{metric}_mean'] = None
            agg[f'{metric}_std'] = None
            agg[f'{metric}_min'] = None
            agg[f'{metric}_max'] = None
    
    agg['n_folds'] = len(results)
    return agg


def compare_models(model_results: Dict[str, List[Dict]]) -> pd.DataFrame:
    """Create comparison table of all models."""
    rows = []
    
    for model_name, results in model_results.items():
        agg = aggregate_results(results)
        row = {'model': model_name, **agg}
        rows.append(row)
    
    return pd.DataFrame(rows)


if __name__ == '__main__':
    # Test with synthetic data
    logging.basicConfig(level=logging.INFO)
    
    # Load synthetic benchmark
    data = pd.read_csv('data/synthetic_benchmark.csv')
    
    # Test with AWS data only
    aws_data = data[data['provider'] == 'AWS'][['date', 'daily_cost_usd']].rename(
        columns={'daily_cost_usd': 'cost_usd'})
    
    print("Running rolling-origin evaluation on AWS data...")
    results = evaluate_all_models(aws_data, initial_train_days=90, test_horizon=7, step=7)
    
    comparison = compare_models(results)
    print("\n=== Model Comparison ===")
    print(comparison.to_string())
    
    # Save results
    comparison.to_csv('results/forecasting_comparison.csv', index=False)
    print("\nResults saved to results/forecasting_comparison.csv")