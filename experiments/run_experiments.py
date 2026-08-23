#!/usr/bin/env python3
"""
Main Experimental Runner

Orchestrates:
1. Data loading (synthetic benchmark)
2. Forecasting baseline comparison (rolling-origin)
3. Anomaly detection comparison
4. MLflow experiment tracking
5. Results storage
"""

import os
import sys
import json
import logging
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.forecasting.baselines import (
    evaluate_all_models, compare_models, rolling_origin_evaluation,
    NaiveForecaster, MovingAverageForecaster, ProphetForecaster
)
from experiments.anomaly.baselines import (
    run_anomaly_comparison, create_ground_truth_labels
)
from experiments.anomaly.cost_aware import run_cost_aware_comparison

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentConfig:
    """Configuration for experiments."""
    
    def __init__(self):
        # Data
        self.benchmark_path = 'experiments/data/synthetic_benchmark.csv'
        self.detailed_path = 'experiments/data/synthetic_benchmark_detailed.csv'
        self.anomaly_path = 'experiments/data/ground_truth_anomalies.csv'
        
        # Rolling-origin parameters
        self.initial_train_days = 90
        self.test_horizon = 7
        self.step = 7
        self.min_train_days = 60
        
        # Models
        self.forecast_models = ['Naive', 'MovingAverage_7', 'MovingAverage_14', 'MovingAverage_30', 'Prophet']
        self.anomaly_methods = ['Threshold', 'RawCost_IF', 'Residual_IF']
        self.contamination = 0.05
        
        # MLflow
        self.experiment_name = 'finops_forecasting_anomaly'
        self.run_name_prefix = 'exp'
        
        # Output
        self.results_dir = 'experiments/results'
        self.plots_dir = 'experiments/plots'


def setup_mlflow(config: ExperimentConfig):
    """Setup MLflow experiment."""
    mlflow.set_experiment(config.experiment_name)
    logger.info(f"MLflow experiment: {config.experiment_name}")


def log_forecasting_results(model_name: str, fold_results: List[Dict], config: ExperimentConfig):
    """Log forecasting results to MLflow."""
    with mlflow.start_run(run_name=f"{config.run_name_prefix}_forecast_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        # Log parameters
        mlflow.log_param('model', model_name)
        mlflow.log_param('initial_train_days', config.initial_train_days)
        mlflow.log_param('test_horizon', config.test_horizon)
        mlflow.log_param('step', config.step)
        mlflow.log_param('min_train_days', config.min_train_days)
        mlflow.log_param('n_folds', len(fold_results))
        
        # Aggregate metrics
        if fold_results:
            metrics = ['mae', 'rmse', 'mape', 'smape']
            for metric in metrics:
                values = [r[metric] for r in fold_results if r[metric] is not None]
                if values:
                    mlflow.log_metric(f'{metric}_mean', float(np.mean(values)))
                    mlflow.log_metric(f'{metric}_std', float(np.std(values)))
                    mlflow.log_metric(f'{metric}_min', float(np.min(values)))
                    mlflow.log_metric(f'{metric}_max', float(np.max(values)))
            
            # Log per-fold details as artifact
            fold_df = pd.DataFrame(fold_results)
            fold_path = f'/tmp/fold_results_{model_name}.csv'
            fold_df.to_csv(fold_path, index=False)
            mlflow.log_artifact(fold_path, 'fold_results')
            os.remove(fold_path)


def log_anomaly_results(method_name: str, metrics: Dict, config: ExperimentConfig):
    """Log anomaly detection results to MLflow."""
    with mlflow.start_run(run_name=f"{config.run_name_prefix}_anomaly_{method_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
        mlflow.log_param('method', method_name)
        mlflow.log_param('contamination', config.contamination)
        
        for k, v in metrics.items():
            if v is not None:
                mlflow.log_metric(k, float(v) if isinstance(v, (int, float, np.number)) else 0)


def run_forecasting_experiments(config: ExperimentConfig) -> Dict:
    """Run all forecasting baseline experiments."""
    logger.info("=" * 60)
    logger.info("STARTING FORECASTING EXPERIMENTS")
    logger.info("=" * 60)
    
    # Load data
    data = pd.read_csv(config.benchmark_path)
    
    all_results = {}
    
    for provider in ['AWS', 'GCP']:
        provider_data = data[data['provider'] == provider][['date', 'daily_cost_usd']].copy()
        provider_data = provider_data.rename(columns={'daily_cost_usd': 'cost_usd'})
        
        logger.info(f"\nEvaluating provider: {provider} ({len(provider_data)} days)")
        
        # Run rolling-origin evaluation
        results = evaluate_all_models(
            provider_data,
            initial_train_days=config.initial_train_days,
            test_horizon=config.test_horizon,
            step=config.step
        )
        
        all_results[provider] = results
        
        # Log to MLflow
        for model_name, fold_results in results.items():
            log_forecasting_results(f"{provider}_{model_name}", fold_results, config)
    
    return all_results


def run_anomaly_experiments(config: ExperimentConfig) -> Dict:
    """Run anomaly detection comparison experiments."""
    logger.info("=" * 60)
    logger.info("STARTING ANOMALY DETECTION EXPERIMENTS")
    logger.info("=" * 60)
    
    # Load data
    detailed = pd.read_csv(config.detailed_path)
    anomalies = pd.read_csv(config.anomaly_path)
    
    all_results = {}
    
    for provider in ['AWS', 'GCP']:
        logger.info(f"\nEvaluating anomaly detection for {provider}")
        
        # Prepare data
        provider_data = detailed[detailed['provider'] == provider].copy()
        daily_data = provider_data.groupby('date')['cost_usd'].sum().reset_index()
        daily_data = daily_data.rename(columns={'cost_usd': 'y'})
        
        # Create ground truth labels
        provider_anomalies = anomalies[anomalies['provider'] == provider]
        daily_labeled = create_ground_truth_labels(daily_data, provider_anomalies, provider=provider)
        
        # Split into train/test (chronological)
        train_size = int(len(daily_labeled) * 0.7)
        train_data = daily_labeled.iloc[:train_size].copy()
        test_data = daily_labeled.iloc[train_size:].copy()
        
        logger.info(f"Train: {len(train_data)} days, Test: {len(test_data)} days")
        
        # Fit Prophet on training data
        prophet = ProphetForecaster()
        prophet.fit(train_data)
        
        # Generate predictions on test set
        test_dates = test_data[['date']].copy()
        test_dates = test_dates.rename(columns={'date': 'ds'})
        preds = prophet.predict(len(test_data))
        test_actual = test_data['y'].values
        test_predicted = preds['yhat'].values
        
        # Prepare test data for anomaly detection
        test_data_for_anomaly = test_data.copy()
        test_data_for_anomaly = test_data_for_anomaly.rename(columns={'y': 'cost_usd'})
        
        # Run anomaly comparison
        logger.info(f"Running anomaly comparison for {provider}...")
        results = run_anomaly_comparison(
            test_data_for_anomaly,
            test_actual,
            test_predicted,
            test_data,
            contamination=config.contamination
        )
        
        # Run cost-aware comparison
        logger.info(f"Running cost-aware anomaly comparison for {provider}...")
        cost_aware_results = run_cost_aware_comparison(
            test_data_for_anomaly,
            test_actual,
            test_predicted,
            test_data,
            contamination=config.contamination
        )
        
        # Merge cost-aware results
        results.update(cost_aware_results)
        
        all_results[provider] = results
        
        # Log to MLflow
        for method, metrics in results.items():
            if isinstance(metrics, dict) and 'precision' in metrics:
                log_anomaly_results(f"{provider}_{method}", metrics, config)
    
    return all_results


def save_results(forecast_results: Dict, anomaly_results: Dict, config: ExperimentConfig):
    """Save all results to CSV files."""
    os.makedirs(config.results_dir, exist_ok=True)
    
    # Forecasting results
    for provider, models in forecast_results.items():
        for model_name, fold_results in models.items():
            if fold_results:
                df = pd.DataFrame(fold_results)
                path = os.path.join(config.results_dir, f'forecast_{provider}_{model_name}.csv')
                df.to_csv(path, index=False)
                logger.info(f"Saved: {path}")
        
        # Comparison summary
        comparison = compare_models(models)
        comp_path = os.path.join(config.results_dir, f'forecast_comparison_{provider}.csv')
        comparison.to_csv(comp_path, index=False)
        logger.info(f"Saved: {comp_path}")
    
    # Anomaly results
    for provider, methods in anomaly_results.items():
        rows = []
        ranking_data = None
        for method, metrics in methods.items():
            if isinstance(metrics, list):
                # This is ranking data, save separately
                ranking_data = metrics
            elif isinstance(metrics, dict):
                row = {'provider': provider, 'method': method, **metrics}
                rows.append(row)
        
        anomaly_df = pd.DataFrame(rows)
        path = os.path.join(config.results_dir, f'anomaly_comparison_{provider}.csv')
        anomaly_df.to_csv(path, index=False)
        logger.info(f"Saved: {path}")
        
        # Save ranking data separately if present
        if ranking_data is not None:
            ranking_df = pd.DataFrame(ranking_data)
            ranking_path = os.path.join(config.results_dir, f'anomaly_ranking_{provider}.csv')
            ranking_df.to_csv(ranking_path, index=False)
            logger.info(f"Saved: {ranking_path}")
    
    # Combined summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'initial_train_days': config.initial_train_days,
            'test_horizon': config.test_horizon,
            'step': config.step,
            'contamination': config.contamination,
        },
        'forecast_summary': {},
        'anomaly_summary': {}
    }
    
    for provider, models in forecast_results.items():
        summary['forecast_summary'][provider] = {}
        for model_name, fold_results in models.items():
            if fold_results:
                agg = {}
                for metric in ['mae', 'rmse', 'mape', 'smape']:
                    values = [r[metric] for r in fold_results if r[metric] is not None]
                    if values:
                        agg[metric] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values))
                        }
                summary['forecast_summary'][provider][model_name] = agg
    
    for provider, methods in anomaly_results.items():
        summary['anomaly_summary'][provider] = {}
        for method, metrics in methods.items():
            summary['anomaly_summary'][provider][method] = metrics
    
    summary_path = os.path.join(config.results_dir, 'experiment_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved: {summary_path}")


def print_summary(forecast_results: Dict, anomaly_results: Dict):
    """Print summary of all results."""
    print("\n" + "=" * 80)
    print("EXPERIMENTAL RESULTS SUMMARY")
    print("=" * 80)
    
    # Forecasting
    print("\n--- FORECASTING RESULTS ---")
    for provider, models in forecast_results.items():
        print(f"\n{provider}:")
        comparison = compare_models(models)
        print(comparison[['model', 'mae_mean', 'mae_std', 'rmse_mean', 'rmse_std', 'mape_mean', 'mape_std']].to_string(index=False))
    
    # Anomaly
    print("\n--- ANOMALY DETECTION RESULTS ---")
    for provider, methods in anomaly_results.items():
        print(f"\n{provider}:")
        for method, metrics in methods.items():
            if isinstance(metrics, dict):
                print(f"  {method}: Precision={metrics.get('precision', 0):.3f}, "
                      f"Recall={metrics.get('recall', 0):.3f}, "
                      f"F1={metrics.get('f1', 0):.3f}, "
                      f"PR-AUC={metrics.get('pr_auc', 0):.3f}")
            elif isinstance(metrics, list):
                print(f"  {method}: Ranking data ({len(metrics)} records)")


def main():
    """Main experiment runner."""
    config = ExperimentConfig()
    
    # Setup MLflow
    setup_mlflow(config)
    
    # Run experiments
    logger.info("Starting experimental validation...")
    
    # 1. Forecasting experiments
    forecast_results = run_forecasting_experiments(config)
    
    # 2. Anomaly detection experiments
    anomaly_results = run_anomaly_experiments(config)
    
    # 3. Save results
    save_results(forecast_results, anomaly_results, config)
    
    # 4. Print summary
    print_summary(forecast_results, anomaly_results)
    
    logger.info("\nAll experiments completed successfully!")
    
    return forecast_results, anomaly_results


if __name__ == '__main__':
    main()