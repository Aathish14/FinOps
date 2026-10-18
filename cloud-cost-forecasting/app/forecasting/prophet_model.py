import pandas as pd
import numpy as np
from prophet import Prophet
import logging
from typing import Dict
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, mean_absolute_error

logger = logging.getLogger(__name__)

class ForecastingModel:
    def __init__(self, model_type: str = 'prophet'):
        self.model_type = model_type
        self.model = None
        self.is_fitted = False

    def fit(self, train_data: pd.DataFrame, **kwargs) -> 'ForecastingModel':
        """Fit the forecasting model."""
        logger.info(f"Fitting {self.model_type} model with {len(train_data)} samples")

        if self.model_type == 'prophet':
            self.model = Prophet(**kwargs)
            # Prophet expects columns 'ds' and 'y'
            df = train_data.rename(columns={'date': 'ds', 'cost_usd': 'y'})
            # Normalize ds to timezone-naive UTC for Prophet compatibility.
            # User-uploaded CSVs may contain timezone-aware timestamps (e.g.,
            # "2026-04-07T00:00:00Z"), which Prophet rejects. Convert to UTC
            # and strip timezone metadata while preserving timestamp instants.
            df['ds'] = pd.to_datetime(df['ds'], utc=True).dt.tz_localize(None)
            self.model.fit(df)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        self.is_fitted = True
        return self

    def predict(self, periods: int, freq: str = 'D') -> pd.DataFrame:
        """Generate forecasts."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")

        logger.info(f"Generating forecast for {periods} periods with frequency {freq}")

        if self.model_type == 'prophet':
            future = self.model.make_future_dataframe(periods=periods, freq=freq)
            forecast = self.model.predict(future)
            # Rename columns to match our expected output
            forecast = forecast.rename(columns={
                'ds': 'date',
                'yhat': 'forecast_cost_usd',
                'yhat_lower': 'lower_bound_80',
                'yhat_upper': 'upper_bound_80'
            })
            # Select and return the required columns
            result = forecast[['date', 'forecast_cost_usd', 'lower_bound_80', 'upper_bound_80']]
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        return result

    def predict_on_dates(self, dates: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions for specific dates (used for evaluation on test set)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")

        if self.model_type == 'prophet':
            # Create future dataframe with the specific dates
            future_ds = pd.to_datetime(dates['date'], utc=True).dt.tz_localize(None)
            future = pd.DataFrame({'ds': future_ds})
            forecast = self.model.predict(future)
            return forecast[['ds', 'yhat']].rename(columns={'ds': 'date', 'yhat': 'predicted'})
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """Evaluate the model on test data using genuine metrics."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before evaluation")

        logger.info(f"Evaluating model on {len(test_data)} test samples")

        # Generate predictions for the test dates
        predictions_df = self.predict_on_dates(test_data[['date']].copy())

        # Merge predictions with actuals
        eval_df = test_data[['date', 'cost_usd']].copy()
        # Normalize eval_df['date'] to timezone-naive UTC so it can merge with
        # predictions_df['date'], which predict_on_dates() already normalizes.
        # Both dataframes must use the same datetime representation before the
        # inner join; otherwise pandas raises a ValueError on mixed timezone
        # awareness.
        eval_df['date'] = pd.to_datetime(eval_df['date'], utc=True).dt.tz_localize(None)

        # Validate: no duplicate dates in test_data
        if eval_df['date'].duplicated().any():
            dup_dates = eval_df.loc[eval_df['date'].duplicated(keep=False), 'date'].tolist()
            raise ValueError(
                f"Duplicate dates found in test data: {dup_dates}. "
                f"Each test date must be unique for evaluation."
            )

        eval_df = eval_df.merge(predictions_df, on='date', how='inner')

        # Validate: all test dates must have predictions
        n_test = len(test_data)
        n_matched = len(eval_df)
        if n_matched < n_test:
            missing_dates = set(test_data['date']) - set(eval_df['date'])
            raise ValueError(
                f"Evaluation failed: {n_test - n_matched} of {n_test} test dates "
                f"have missing predictions. Missing dates: {sorted(missing_dates)}. "
                f"This may indicate forecast model did not produce predictions "
                f"for all requested dates."
            )

        if len(eval_df) == 0:
            logger.warning("No overlapping dates for evaluation")
            return {'mape': np.nan, 'rmse': np.nan, 'mae': np.nan}

        y_true = eval_df['cost_usd'].values
        y_pred = eval_df['predicted'].values

        # Calculate genuine metrics
        # Handle zero values for MAPE
        mask = y_true != 0
        if mask.any():
            mape = mean_absolute_percentage_error(y_true[mask], y_pred[mask])
        else:
            mape = np.nan

        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)

        metrics = {
            'mape': float(mape) if not np.isnan(mape) else None,
            'rmse': float(rmse),
            'mae': float(mae)
        }

        logger.info(f"Evaluation metrics: MAPE={metrics['mape']}, RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")
        return metrics

def create_forecasting_model(model_type: str = 'prophet') -> ForecastingModel:
    """Factory function to create a forecasting model."""
    return ForecastingModel(model_type=model_type)
