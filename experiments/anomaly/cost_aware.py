#!/usr/bin/env python3
"""
Cost-Impact-Aware Anomaly Ranking

Implements cost-impact-aware anomaly ranking that prioritizes anomalies
by estimated financial impact rather than just statistical deviation.

Core concept:
- excess_cost = max(observed - expected, 0)
- cost_impact_score = anomaly_score * excess_cost * confidence_weight
- Supports three ranking variants: score_only, excess_cost_only, combined
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CostImpactScorer:
    """
    Cost-impact-aware anomaly scorer.
    
    Transforms raw anomaly scores into cost-impact-aware rankings
    by incorporating financial impact (excess cost) and forecast confidence.
    """
    
    def __init__(
        self,
        confidence_weight: float = 1.0,
        cost_weight: float = 1.0,
        score_weight: float = 1.0,
        min_excess_cost: float = 0.01
    ):
        """
        Initialize cost-impact scorer.
        
        Args:
            confidence_weight: Weight for forecast confidence (1 - MAPE)
            cost_weight: Weight for excess cost magnitude
            score_weight: Weight for raw anomaly score
            min_excess_cost: Minimum excess cost to consider (avoids noise)
        """
        self.confidence_weight = confidence_weight
        self.cost_weight = cost_weight
        self.score_weight = score_weight
        self.min_excess_cost = min_excess_cost
        
    def compute_excess_cost(
        self,
        observed: np.ndarray,
        expected: np.ndarray
    ) -> np.ndarray:
        """
        Compute excess cost = max(observed - expected, 0).
        
        Args:
            observed: Actual observed costs
            expected: Expected/predicted costs
            
        Returns:
            Array of excess costs (negative values clipped to 0)
        """
        excess = observed - expected
        return np.maximum(excess, 0)
    
    def compute_relative_deviation(
        self,
        observed: np.ndarray,
        expected: np.ndarray
    ) -> np.ndarray:
        """
        Compute relative deviation = (observed - expected) / expected.
        Handles division by zero.
        """
        with np.errstate(divide='ignore', invalid='ignore'):
            rel_dev = (observed - expected) / np.where(expected != 0, expected, 1)
        return np.where(np.isfinite(rel_dev), rel_dev, 0)
    
    def compute_confidence_weight(
        self,
        mape: Optional[float],
        default_confidence: float = 0.5
    ) -> float:
        """
        Compute confidence weight from MAPE.
        Lower MAPE = higher confidence.
        """
        if mape is None or np.isnan(mape):
            return default_confidence
        # Confidence = 1 - MAPE, clipped to [0, 1]
        return float(np.clip(1 - mape, 0, 1))
    
    def compute_cost_impact_score(
        self,
        anomaly_scores: np.ndarray,
        excess_costs: np.ndarray,
        confidence: float,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Compute cost-impact score combining anomaly score, excess cost, and confidence.
        
        Formula: cost_impact = (score_weight * normalized_score) * 
                                (cost_weight * normalized_excess_cost) * 
                                (confidence_weight * confidence)
        
        Args:
            anomaly_scores: Raw anomaly scores (higher = more anomalous)
            excess_costs: Excess cost values
            confidence: Forecast confidence [0, 1]
            normalize: Whether to normalize components to [0, 1]
            
        Returns:
            Cost-impact scores
        """
        # Normalize anomaly scores to [0, 1] if requested
        if normalize and len(anomaly_scores) > 1:
            score_min, score_max = anomaly_scores.min(), anomaly_scores.max()
            if score_max > score_min:
                norm_scores = (anomaly_scores - score_min) / (score_max - score_min)
            else:
                norm_scores = np.ones_like(anomaly_scores) * 0.5
        else:
            # For Isolation Forest, scores are negative (more negative = more anomalous)
            # Convert to positive anomaly magnitude
            norm_scores = -anomaly_scores if anomaly_scores.min() < 0 else anomaly_scores
            if normalize and len(norm_scores) > 1:
                s_min, s_max = norm_scores.min(), norm_scores.max()
                if s_max > s_min:
                    norm_scores = (norm_scores - s_min) / (s_max - s_min)
                else:
                    norm_scores = np.ones_like(norm_scores) * 0.5
        
        # Normalize excess costs
        if normalize and len(excess_costs) > 1:
            cost_min, cost_max = excess_costs.min(), excess_costs.max()
            if cost_max > cost_min:
                norm_costs = (excess_costs - cost_min) / (cost_max - cost_min)
            else:
                norm_costs = np.ones_like(excess_costs) * 0.5
        else:
            norm_costs = excess_costs
            if normalize and len(norm_costs) > 1:
                c_min, c_max = norm_costs.min(), norm_costs.max()
                if c_max > c_min:
                    norm_costs = (norm_costs - c_min) / (c_max - c_min)
                else:
                    norm_costs = np.ones_like(norm_costs) * 0.5
        
        # Combine: multiplicative combination ensures all factors matter
        cost_impact = (
            (self.score_weight * norm_scores) *
            (self.cost_weight * norm_costs) *
            (self.confidence_weight * confidence)
        )
        
        return cost_impact
    
    def rank_anomalies(
        self,
        test_data: pd.DataFrame,
        anomaly_scores: np.ndarray,
        anomaly_labels: np.ndarray,
        actual_costs: np.ndarray,
        expected_costs: np.ndarray,
        mape: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Rank anomalies by cost-impact score.
        
        Args:
            test_data: DataFrame with test period data (must have 'date', 'cost_usd')
            anomaly_scores: Raw anomaly scores from detector
            anomaly_labels: Binary anomaly labels (1=anomaly, 0=normal)
            actual_costs: Actual observed costs
            expected_costs: Expected/predicted costs
            mape: MAPE of forecast model for confidence weighting
            
        Returns:
            DataFrame with anomaly rankings and cost-impact metrics
        """
        # Compute excess costs
        excess_costs = self.compute_excess_cost(
            np.array(actual_costs), np.array(expected_costs)
        )
        
        # Compute relative deviation
        relative_dev = self.compute_relative_deviation(
            np.array(actual_costs), np.array(expected_costs)
        )
        
        # Compute confidence weight
        confidence = self.compute_confidence_weight(mape)
        
        # Compute cost-impact scores
        cost_impact_scores = self.compute_cost_impact_score(
            anomaly_scores, excess_costs, confidence
        )
        
        # Create results DataFrame
        results = pd.DataFrame({
            'date': test_data['date'].values,
            'provider': test_data.get('provider', ['unknown'] * len(test_data)),
            'observed_cost': actual_costs,
            'expected_cost': expected_costs,
            'excess_cost': excess_costs,
            'relative_deviation': relative_dev,
            'anomaly_score': anomaly_scores,
            'anomaly_label': anomaly_labels,
            'cost_impact_score': cost_impact_scores,
            'is_anomaly': anomaly_labels.astype(bool)
        })
        
        # Add cumulative excess cost for multi-period anomalies
        results['cumulative_excess_cost'] = results.groupby(
            (results['is_anomaly'] != results['is_anomaly'].shift()).cumsum()
        )['excess_cost'].transform('sum')
        
        # Rank by cost-impact score (descending)
        results['cost_impact_rank'] = results['cost_impact_score'].rank(
            ascending=False, method='min'
        ).astype(int)
        
        # Also rank by raw anomaly score for comparison
        results['anomaly_score_rank'] = pd.Series(-anomaly_scores).rank(
            ascending=True, method='min'
        ).astype(int)
        
        # Rank by excess cost alone
        results['excess_cost_rank'] = results['excess_cost'].rank(
            ascending=False, method='min'
        ).astype(int)
        
        return results
    
    def get_top_k_anomalies(
        self,
        ranked_results: pd.DataFrame,
        k: int,
        rank_by: str = 'cost_impact_score'
    ) -> pd.DataFrame:
        """
        Get top-K anomalies by specified ranking.
        
        Args:
            ranked_results: DataFrame from rank_anomalies
            k: Number of top anomalies to return
            rank_by: Column to rank by ('cost_impact_score', 'anomaly_score', 'excess_cost')
            
        Returns:
            Top-K anomalies DataFrame
        """
        if rank_by not in ranked_results.columns:
            # Map common rank_by values to actual column names
            rank_column_map = {
                'cost_impact_score': 'cost_impact_rank',
                'anomaly_score': 'anomaly_score_rank',
                'excess_cost': 'excess_cost_rank'
            }
            if rank_by in rank_column_map:
                rank_by = rank_column_map[rank_by]
            else:
                raise ValueError(f"Rank column '{rank_by}' not found")
        
        top_k = ranked_results.nlargest(k, rank_by)
        # Select available columns
        available_cols = ['date', 'provider', 'observed_cost', 'expected_cost', 
                          'excess_cost', 'relative_deviation', 'anomaly_score',
                          'cost_impact_score', 'anomaly_label', 'cost_impact_rank',
                          'anomaly_score_rank', 'excess_cost_rank']
        available_cols = [c for c in available_cols if c in top_k.columns]
        return top_k[available_cols].copy()
    
    def compute_cumulative_excess_captured(
        self,
        ranked_results: pd.DataFrame,
        k_values: List[int],
        ground_truth: pd.DataFrame
    ) -> Dict[int, Dict]:
        """
        Compute cumulative excess cost captured in top-K for different K values.
        
        Args:
            ranked_results: DataFrame from rank_anomalies
            k_values: List of K values to evaluate
            ground_truth: DataFrame with 'is_anomaly' and 'excess_cost' columns
            
        Returns:
            Dictionary mapping K to cumulative excess cost metrics
        """
        results = {}
        
        # Merge with ground truth excess costs
        merged = ranked_results.merge(
            ground_truth[['date', 'excess_cost', 'is_anomaly']],
            on='date',
            how='left',
            suffixes=('', '_gt')
        )
        
        for k in k_values:
            top_k = ranked_results.nlargest(k, 'cost_impact_score')
            
            # Get ground truth excess costs for these dates
            top_k_dates = set(top_k['date'].values)
            gt_mask = ground_truth['date'].isin(top_k_dates)
            
            captured_excess = ground_truth.loc[gt_mask, 'excess_cost'].sum()
            total_excess = ground_truth['excess_cost'].sum()
            
            # Also compute how many true anomalies captured
            true_anomalies_in_topk = ground_truth.loc[gt_mask, 'is_anomaly'].sum()
            total_true_anomalies = ground_truth['is_anomaly'].sum()
            
            results[k] = {
                'k': k,
                'captured_excess_cost': float(captured_excess),
                'total_excess_cost': float(total_excess),
                'excess_cost_capture_rate': float(captured_excess / total_excess) if total_excess > 0 else 0.0,
                'true_anomalies_captured': int(true_anomalies_in_topk),
                'total_true_anomalies': int(total_true_anomalies),
                'anomaly_recall_at_k': float(true_anomalies_in_topk / total_true_anomalies) if total_true_anomalies > 0 else 0.0
            }
        
        return results


def create_cost_aware_ranker(
    confidence_weight: float = 1.0,
    cost_weight: float = 1.0,
    score_weight: float = 1.0
) -> CostImpactScorer:
    """Factory function to create a CostImpactScorer."""
    return CostImpactScorer(
        confidence_weight=confidence_weight,
        cost_weight=cost_weight,
        score_weight=score_weight
    )


def run_cost_aware_comparison(
    test_data: pd.DataFrame,
    test_actual: np.ndarray,
    test_predicted: np.ndarray,
    ground_truth: pd.DataFrame,
    mape: Optional[float] = None,
    contamination: float = 0.05
) -> Dict:
    """
    Run cost-aware anomaly ranking comparison with existing methods.
    
    Args:
        test_data: Test period DataFrame with 'cost_usd'
        test_actual: Actual cost values
        test_predicted: Predicted cost values
        ground_truth: DataFrame with anomaly labels
        mape: MAPE of forecast model for confidence weighting
        contamination: Contamination parameter for Isolation Forest
        
    Returns:
        Dictionary with results for each method including cost-aware rankings
    """
    from experiments.anomaly.baselines import (
        ThresholdAnomalyDetector,
        RawCostIsolationForest,
        ResidualIsolationForest,
        compute_residuals,
        evaluate_anomaly_detection,
        create_ground_truth_labels
    )
    
    # Prepare ground truth labels
    y_true = ground_truth['is_anomaly'].values if 'is_anomaly' in ground_truth.columns else np.zeros(len(test_data))
    
    # Compute residuals
    residuals = test_actual - test_predicted
    
    results = {}
    
    # Method A: Threshold
    logger.info("Running Threshold detector...")
    threshold_detector = ThresholdAnomalyDetector(k=2.0, window=30)
    threshold_detector.fit(test_data.rename(columns={'cost_usd': 'y'}))
    y_pred_a = threshold_detector.predict(test_data.rename(columns={'cost_usd': 'y'}))
    y_scores_a = threshold_detector.score_samples(test_data.rename(columns={'cost_usd': 'y'}))
    results['Threshold'] = evaluate_anomaly_detection(y_true, y_pred_a, y_scores_a)
    
    # Method B: Raw-cost Isolation Forest
    raw_if = RawCostIsolationForest(contamination=0.05)
    raw_if.fit(test_data)
    y_pred_b = raw_if.predict(test_data)
    y_scores_b = raw_if.score_samples(test_data)
    results['RawCost_IF'] = evaluate_anomaly_detection(y_true, y_pred_b, y_scores_b)
    
    # Method C: Residual Isolation Forest
    resid_if = ResidualIsolationForest(contamination=0.05)
    resid_if.fit(residuals)
    y_pred_c = resid_if.predict(residuals)
    y_scores_c = resid_if.score_samples(residuals)
    results['Residual_IF'] = evaluate_anomaly_detection(y_true, y_pred_c, y_scores_c)
    
    # Method D: Cost-Aware Ranking (using RawCost_IF scores)
    logger.info("Running Cost-Aware Ranking...")
    cost_scorer = CostImpactScorer()
    
    # Get RawCost_IF scores for cost-aware ranking
    raw_if_scores = raw_if.score_samples(test_data)
    
    # Rank anomalies using cost-impact scoring
    ranked_results = CostImpactScorer().rank_anomalies(
        test_data=test_data,
        anomaly_scores=raw_if_scores,
        anomaly_labels=results['RawCost_IF'].get('y_pred', np.zeros(len(test_data))),
        actual_costs=test_data['cost_usd'].values,
        expected_costs=test_predicted,
        mape=None  # Could pass MAPE here if available
    )
    
    # Evaluate cost-aware ranking
    y_pred_cost_aware = (ranked_results['cost_impact_score'] > 0).astype(int)
    # For cost-aware, we use the cost_impact_score as the score
    y_scores_cost_aware = ranked_results['cost_impact_score'].values
    results['CostAware_IF'] = evaluate_anomaly_detection(y_true, y_pred_cost_aware, y_scores_cost_aware)
    
    # Store ranking details
    results['CostAware_Ranking'] = ranked_results.to_dict('records')
    
    return results


if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    logging.basicConfig(level=logging.INFO)
    
    # Test with synthetic benchmark
    from experiments.anomaly.baselines import (
        ThresholdAnomalyDetector,
        RawCostIsolationForest,
        ResidualIsolationForest,
        compute_residuals,
        create_ground_truth_labels
    )
    from experiments.forecasting.baselines import ProphetForecaster
    
    # Load data
    detailed = pd.read_csv('experiments/data/synthetic_benchmark_detailed.csv')
    anomalies = pd.read_csv('experiments/data/ground_truth_anomalies.csv')
    
    # Test with AWS data
    aws_data = detailed[detailed['provider'] == 'AWS'].copy()
    aws_data = aws_data.groupby('date')['cost_usd'].sum().reset_index()
    aws_data = aws_data.rename(columns={'cost_usd': 'y'})
    
    # Create ground truth
    aws_anomalies = anomalies[anomalies['provider'] == 'AWS']
    aws_data_labeled = create_ground_truth_labels(aws_data, aws_anomalies, provider='AWS')
    
    # Fit Prophet on first 125 days (70%)
    train_size = int(len(aws_data_labeled) * 0.7)
    train_data = aws_data_labeled.iloc[:train_size].copy()
    test_data = aws_data_labeled.iloc[train_size:].copy()
    
    prophet = ProphetForecaster()
    prophet.fit(train_data)
    
    test_actual = test_data['y'].values
    preds = prophet.predict(len(test_data))
    test_predicted = preds['yhat'].values
    
    # Prepare test data for anomaly detection
    test_data_for_anomaly = test_data.copy()
    test_data_for_anomaly = test_data_for_anomaly.rename(columns={'y': 'cost_usd'})
    
    # Run cost-aware comparison
    from experiments.anomaly.baselines import evaluate_anomaly_detection
    
    # Compute residuals
    residuals = test_actual - test_predicted
    
    # RawCost_IF
    raw_if = RawCostIsolationForest(contamination=0.05)
    raw_if.fit(test_data_for_anomaly)
    raw_scores = raw_if.score_samples(test_data_for_anomaly)
    raw_preds = raw_if.predict(test_data_for_anomaly)
    
    # Evaluate
    y_true = test_data['is_anomaly'].values
    raw_metrics = evaluate_anomaly_detection(y_true, raw_preds, raw_if.score_samples(test_data_for_anomaly))
    print("RawCost_IF:", raw_metrics)
    
    # Cost-aware ranking
    cost_scorer = CostImpactScorer()
    ranked = cost_scorer.rank_anomalies(
        test_data=test_data_for_anomaly,
        anomaly_scores=raw_if.score_samples(test_data_for_anomaly),
        anomaly_labels=raw_preds,
        actual_costs=test_actual,
        expected_costs=test_predicted,
        mape=None
    )
    
    print("\nTop 5 anomalies by cost-impact score:")
    top5 = cost_scorer.get_top_k_anomalies(ranked, 5, 'cost_impact_score')
    print(top5.to_string())
    
    # Evaluate top-K cost capture using ranked results (which have excess_cost)
    k_results = cost_scorer.compute_cumulative_excess_captured(
        ranked, [1, 3, 5, 10], ranked
    )
    print("\nCumulative excess cost captured:")
    for k, metrics in k_results.items():
        print(f"  K={k}: ${metrics['captured_excess_cost']:.2f} "
              f"({metrics['excess_cost_capture_rate']*100:.1f}% of total), "
              f"Anomaly recall: {metrics['anomaly_recall_at_k']*100:.1f}%")