import mlflow
import mlflow.sklearn
import logging
import os
from typing import Dict, Any, Optional
import json
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class ExperimentTracker:
    def __init__(self, experiment_name: str = "cloud_cost_forecasting", run_name: Optional[str] = None):
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.run = None
        self._setup_experiment()
    
    def _setup_experiment(self):
        """Set up the MLflow experiment."""
        try:
            mlflow.set_experiment(self.experiment_name)
            logger.info(f"Set MLflow experiment: {self.experiment_name}")
        except Exception as e:
            logger.warning(f"Failed to set MLflow experiment: {e}. Falling back to local tracking.")
    
    def start_run(self, run_name: Optional[str] = None) -> str:
        """Start a new MLflow run."""
        if run_name is None:
            run_name = self.run_name
        if run_name is None:
            run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            self.run = mlflow.start_run(run_name=run_name)
            logger.info(f"Started MLflow run: {self.run.info.run_id}")
            return self.run.info.run_id
        except Exception as e:
            logger.warning(f"Failed to start MLflow run: {e}. Falling back to local tracking.")
            self.run = None
            return ""
    
    def end_run(self):
        """End the current MLflow run."""
        if self.run is not None:
            try:
                mlflow.end_run()
                logger.info("Ended MLflow run")
            except Exception as e:
                logger.warning(f"Failed to end MLflow run: {e}")
            finally:
                self.run = None
    
    def log_params(self, params: Dict[str, Any]):
        """Log parameters to the current run."""
        if self.run is not None:
            try:
                mlflow.log_params(params)
                logger.debug(f"Logged parameters: {params}")
            except Exception as e:
                logger.warning(f"Failed to log parameters: {e}")
        else:
            logger.debug(f"No active run. Parameters not logged: {params}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to the current run."""
        if self.run is not None:
            try:
                mlflow.log_metrics(metrics, step=step)
                logger.debug(f"Logged metrics: {metrics}")
            except Exception as e:
                logger.warning(f"Failed to log metrics: {e}")
        else:
            logger.debug(f"No active run. Metrics not logged: {metrics}")
    
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """Log an artifact to the current run."""
        if self.run is not None:
            try:
                mlflow.log_artifact(local_path, artifact_path)
                logger.debug(f"Logged artifact: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to log artifact: {e}")
        else:
            logger.debug(f"No active run. Artifact not logged: {local_path}")
    
    def log_model(self, model, artifact_path: str = "model"):
        """Log a model to the current run."""
        if self.run is not None:
            try:
                mlflow.sklearn.log_model(model, artifact_path)
                logger.debug(f"Logged model to {artifact_path}")
            except Exception as e:
                logger.warning(f"Failed to log model: {e}")
        else:
            logger.debug(f"No active run. Model not logged.")
    
    def log_figure(self, figure, artifact_file: str):
        """Log a matplotlib figure to the current run."""
        if self.run is not None:
            try:
                mlflow.log_figure(figure, artifact_file)
                logger.debug(f"Logged figure: {artifact_file}")
            except Exception as e:
                logger.warning(f"Failed to log figure: {e}")
        else:
            logger.debug(f"No active run. Figure not logged: {artifact_file}")
    
    def log_table(self, data: pd.DataFrame, artifact_file: str):
        """Log a pandas DataFrame as a CSV artifact."""
        if self.run is not None:
            try:
                # Save DataFrame to a temporary CSV file
                temp_path = f"/tmp/{artifact_file}"
                data.to_csv(temp_path, index=False)
                mlflow.log_artifact(temp_path, os.path.dirname(artifact_file))
                # Clean up temp file
                os.remove(temp_path)
                logger.debug(f"Logged table as artifact: {artifact_file}")
            except Exception as e:
                logger.warning(f"Failed to log table: {e}")
        else:
            logger.debug(f"No active run. Table not logged: {artifact_file}")

def get_tracker(experiment_name: str = "cloud_cost_forecasting", run_name: Optional[str] = None) -> ExperimentTracker:
    """Factory function to get an experiment tracker."""
    return ExperimentTracker(experiment_name=experiment_name, run_name=run_name)
