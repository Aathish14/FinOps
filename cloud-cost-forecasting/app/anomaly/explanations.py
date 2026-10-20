#!/usr/bin/env python3
"""
Explanation Layer for Cost-Impact-Aware Anomaly Ranking

Generates human-readable explanations for prioritized anomalies
using transparent, deterministic reasoning based on cost-impact scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AnomalyExplainer:
    """
    Generates deterministic, transparent explanations for cost-impact-ranked anomalies.
    
    Uses only observable data: observed vs expected costs, excess cost,
    relative deviation, anomaly score, persistence, and cost-impact score.
    Does NOT infer root causes or make causal claims beyond what the data shows.
    """
    
    def __init__(self):
        """Initialize the explainer."""
        pass
    
    def explain_anomaly(
        self,
        anomaly_row: pd.Series,
        include_financial: bool = True,
        include_persistence: bool = True,
        include_ranking: bool = True
    ) -> str:
        """
        Generate a human-readable explanation for a single anomaly.
        
        Args:
            anomaly_row: Row from cost-impact ranking DataFrame
            include_financial: Include financial impact details
            include_persistence: Include persistence information
            include_ranking: Include priority ranking
            
        Returns:
            Human-readable explanation string
        """
        parts = []
        
        # Basic identification
        date_str = anomaly_row.get('date', 'Unknown date')
        if hasattr(date_str, 'strftime'):
            date_str = date_str.strftime('%Y-%m-%d')
        provider = anomaly_row.get('provider', 'Unknown')
        
        # Financial impact
        if include_financial:
            observed = anomaly_row.get('observed_cost', 0)
            expected = anomaly_row.get('expected_cost', 0)
            excess = anomaly_row.get('excess_cost', 0)
            cost_deviation = anomaly_row.get('cost_deviation', 0)
            anomaly_type = anomaly_row.get('anomaly_type', None)
            rel_dev = anomaly_row.get('relative_deviation', 0)
            
            if anomaly_type == '📈 SPIKE':
                financial_part = (
                    f"Observed cost (${observed:,.2f}) exceeded expected cost (${expected:,.2f}) "
                    f"by ${cost_deviation:,.2f} ({rel_dev:.1%})."
                )
            elif anomaly_type == '📉 DROP':
                financial_part = (
                    f"Observed cost (${observed:,.2f}) was below expected cost (${expected:,.2f}) "
                    f"by ${cost_deviation:,.2f} ({abs(rel_dev):.1%} below expected). "
                    f"Possible outage or idle resource."
                )
            elif isinstance(excess, (int, float)) and excess > 0:
                # Fallback for rows without anomaly_type column
                financial_part = (
                    f"Observed cost (${observed:,.2f}) exceeded expected cost (${expected:,.2f}) "
                    f"by ${excess:,.2f} ({rel_dev:.1%})."
                )
            else:
                financial_part = (
                    f"Observed cost (${observed:,.2f}) was within expected range "
                    f"(${expected:,.2f})."
                )
            parts.append(financial_part)
        
        # Anomaly evidence
        anomaly_score = anomaly_row.get('anomaly_score', None)
        if anomaly_score is not None:
            # For Isolation Forest, more negative = more anomalous
            if anomaly_row.get('anomaly_label', 0) == 1:
                parts.append(
                    f"Anomaly detection flagged this as anomalous (score: {anomaly_row.get('anomaly_score', 'N/A'):.3f})."
                )
            else:
                parts.append(
                    f"Anomaly detection score: {anomaly_row.get('anomaly_score', 'N/A'):.3f} (below threshold)."
                )
        
        # Persistence
        if include_persistence:
            cum_excess = anomaly_row.get('cumulative_excess_cost', 0)
            if isinstance(cum_excess, (int, float)) and cum_excess > 0:
                parts.append(
                    f"Cumulative excess cost over this anomaly period: ${cum_excess:,.2f}."
                )
        
        # Cost-impact ranking
        if include_ranking:
            rank = anomaly_row.get('cost_impact_rank', None)
            if rank is not None:
                parts.append(
                    f"Priority rank: #{int(rank)} by cost-impact score ({anomaly_row.get('cost_impact_score', 0):.3f})."
                )
        
        # Cost-impact score details
        cost_impact = anomaly_row.get('cost_impact_score', 0)
        if anomaly_row.get('anomaly_label', 0) == 1:
            parts.append(
                f"Cost-impact score: {cost_impact:.3f} — driven by anomaly evidence and financial impact."
            )
        else:
            parts.append(
                f"Cost-impact score: {cost_impact:.3f} (no anomaly flag)."
            )
        
        # Build final explanation
        prefix = f"On {date_str} ({provider}): "
        explanation = prefix + " ".join(parts)
        
        return explanation
    
    def explain_batch(
        self,
        ranked_results: pd.DataFrame,
        top_k: Optional[int] = None,
        include_all: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate explanations for a batch of ranked anomalies.
        
        Args:
            ranked_results: DataFrame from CostImpactScorer.rank_anomalies()
            top_k: Number of top anomalies to explain (None = all anomalies)
            include_all: If True, explain all rows; if False, only anomalies
            
        Returns:
            List of explanation dictionaries
        """
        df = ranked_results.copy()
        
        if not include_all:
            df = df[df['anomaly_label'] == 1]
        
        if top_k is not None:
            df = df.nlargest(top_k, 'cost_impact_score')
        
        explanations = []
        for _, row in df.iterrows():
            explanation = self.explain_anomaly(row)
            explanations.append({
                'date': row.get('date'),
                'provider': row.get('provider'),
                'cost_impact_rank': row.get('cost_impact_rank'),
                'explanation': explanation,
                'cost_impact_score': row.get('cost_impact_score'),
                'excess_cost': row.get('excess_cost'),
                'anomaly_label': row.get('anomaly_label')
            })
        
        return explanations
    
    def format_explanation_for_ui(
        self,
        anomaly_row: pd.Series,
        max_length: int = 300
    ) -> Dict[str, str]:
        """
        Format explanation for UI display with structured fields.
        
        Returns:
            Dictionary with structured explanation components
        """
        date_str = anomaly_row.get('date', 'Unknown')
        if hasattr(date_str, 'strftime'):
            date_str = date_str.strftime('%Y-%m-%d')
        provider = anomaly_row.get('provider', 'Unknown')
        
        observed = anomaly_row.get('observed_cost', 0)
        expected = anomaly_row.get('expected_cost', 0)
        excess = anomaly_row.get('excess_cost', 0)
        rel_dev = anomaly_row.get('relative_deviation', 0)
        anomaly_score = anomaly_row.get('anomaly_score', None)
        cost_impact_score = anomaly_row.get('cost_impact_score', 0)
        rank = anomaly_row.get('cost_impact_rank', None)
        is_anomaly = bool(anomaly_row.get('anomaly_label', 0))
        cum_excess = anomaly_row.get('cumulative_excess_cost', 0)
        
        # Build summary
        anomaly_type = anomaly_row.get('anomaly_type', None)
        cost_deviation = anomaly_row.get('cost_deviation', 0)
        if anomaly_type == '📈 SPIKE':
            financial_summary = f"${cost_deviation:,.2f} excess ({rel_dev:.1%} above expected)"
        elif anomaly_type == '📉 DROP':
            financial_summary = f"${cost_deviation:,.2f} drop ({abs(rel_dev):.1%} below expected) — possible outage/idle"
        elif isinstance(excess, (int, float)) and excess > 0:
            # Fallback for rows without anomaly_type column
            financial_summary = f"${excess:,.2f} excess ({rel_dev:.1%} above expected)"
        else:
            financial_summary = "Within expected range"
        
        severity = "ANOMALY" if anomaly_row.get('anomaly_label', 0) == 1 else "Normal"
        
        # Build narrative
        narrative_parts = []
        anomaly_type = anomaly_row.get('anomaly_type', None)
        cost_deviation = anomaly_row.get('cost_deviation', 0)
        if anomaly_type == '📈 SPIKE':
            narrative_parts.append(f"Cost exceeded expected by ${cost_deviation:,.2f} ({rel_dev:.1%})")
        elif anomaly_type == '📉 DROP':
            narrative_parts.append(f"Cost below expected by ${cost_deviation:,.2f} ({abs(rel_dev):.1%}) — possible outage/idle")
        if anomaly_row.get('anomaly_label', 0) == 1:
            narrative_parts.append(f"Anomaly score: {anomaly_row.get('anomaly_score', 'N/A'):.3f}")
        if anomaly_row.get('cumulative_excess_cost', 0) > 0:
            narrative_parts.append(f"Persistent for ${anomaly_row['cumulative_excess_cost']:,.2f}")
        
        narrative = ". ".join(narrative_parts) + "."
        
        # Format excess_cost for display: may already be a formatted string from rank_anomalies
        excess = anomaly_row.get('excess_cost', 0)
        if isinstance(excess, str):
            excess_cost_display = excess  # Already formatted (e.g., "+$150.00 Excess Spend")
        elif isinstance(excess, (int, float)) and excess > 0:
            excess_cost_display = f"${excess:,.2f}"
        else:
            excess_cost_display = "$0.00"

        return {
            'date': date_str,
            'provider': provider,
            'severity': severity,
            'observed_cost': f"${observed:,.2f}",
            'expected_cost': f"${expected:,.2f}",
            'excess_cost': excess_cost_display,
            'relative_deviation': f"{rel_dev:.1%}",
            'anomaly_score': f"{anomaly_score:.3f}" if anomaly_score is not None else "N/A",
            'cost_impact_score': f"{cost_impact_score:.3f}",
            'priority_rank': f"#{int(rank)}" if rank is not None else "N/A",
            'is_anomaly': is_anomaly,
            'cumulative_excess': f"${cum_excess:,.2f}" if cum_excess > 0 else "$0.00",
            'financial_summary': financial_summary,
            'narrative': narrative
        }


def format_anomaly_for_ui(anomaly_row: pd.Series) -> Dict[str, Any]:
    """Convenience function to format a single anomaly for UI display."""
    explainer = AnomalyExplainer()
    return explainer.format_explanation_for_ui(anomaly_row)


def generate_explanations_for_ranking(
    ranked_df: pd.DataFrame,
    top_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Generate explanations for top-K anomalies in a ranked DataFrame."""
    explainer = AnomalyExplainer()
    return explainer.explain_batch(ranked_df, top_k=top_k)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Quick test with synthetic data
    import pandas as pd
    
    # Quick test with synthetic data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    sample_data = pd.DataFrame({
        'date': dates,
        'provider': ['AWS'] * 10,
        'observed_cost': np.random.uniform(400, 600, 10),
        'expected_cost': np.random.uniform(400, 500, 10),
        'anomaly_score': np.random.uniform(-0.8, -0.2, 10),
        'anomaly_label': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        'cost_impact_score': np.random.uniform(0.1, 1.0, 10),
    })
    
    # Add required columns
    sample_df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'provider': ['AWS'] * 10,
        'observed_cost': [450, 480, 520, 480, 490, 650, 470, 460, 620, 480],
        'expected_cost': [440, 470, 480, 485, 490, 550, 465, 460, 580, 475],
        'anomaly_score': np.random.uniform(-0.8, -0.2, 10),
        'anomaly_label': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
    })
    sample_df['excess_cost'] = np.maximum(sample_df['observed_cost'] - sample_df['expected_cost'], 0)
    sample_df['relative_deviation'] = (sample_df['observed_cost'] - sample_df['expected_cost']) / sample_df['expected_cost']
    sample_df['cost_impact_score'] = np.random.uniform(0.3, 1.0, 10)
    sample_df['anomaly_label'] = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
    sample_df['cost_impact_rank'] = range(1, 11)
    sample_df['anomaly_score_rank'] = range(1, 11)
    sample_df['excess_cost_rank'] = range(1, 11)
    sample_df['cumulative_excess_cost'] = 0
    
    explainer = AnomalyExplainer()
    explanations = explainer.explain_batch(sample_df, top_k=3)
    
    for exp in explanations:
        print(f"Date: {exp['date']}, Rank: {exp['cost_impact_rank']}")
        print(f"  {exp['explanation']}")
        print()