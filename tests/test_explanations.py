#!/usr/bin/env python3
"""
Tests for the anomaly explanation layer.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'experiments'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from anomaly.explanations import (
    AnomalyExplainer,
    format_anomaly_for_ui,
    generate_explanations_for_ranking
)


class TestAnomalyExplainer:
    """Tests for the AnomalyExplainer class."""
    
    def create_sample_anomaly(self, **overrides) -> pd.Series:
        """Create a sample anomaly row with default values."""
        base = {
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.75,
            'anomaly_label': 1,
            'cost_impact_score': 0.85,
            'cost_impact_rank': 1,
            'anomaly_score_rank': 2,
            'excess_cost_rank': 1,
            'cumulative_excess_cost': 300.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'anomaly_score_rank': 1,
            'excess_cost_rank': 1,
            'cumulative_excess_cost': 500.0,
        }
        base.update(overrides)
        return pd.Series(base)
    
    def test_explain_normal_observation(self):
        """Test explanation for a normal (non-anomalous) observation."""
        explainer = AnomalyExplainer()
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 480.0,
            'expected_cost': 500.0,
            'excess_cost': 0.0,
            'relative_deviation': -0.04,
            'anomaly_score': -0.1,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 50,
            'anomaly_score_rank': 45,
            'excess_cost_rank': 40,
            'cumulative_excess_cost': 0.0,
            'relative_deviation': -0.04,
            'anomaly_score': -0.1,
            'anomaly_label': 0,
            'cost_impact_score': 0.05,
            'cost_impact_rank': 50,
            'anomaly_score_rank': 45,
            'excess_cost_rank': 40,
            'cumulative_excess_cost': 0.0,
        })
        
        explanation = AnomalyExplainer().explain_anomaly(row)
        
        assert 'AWS' in explanation
        assert 'within expected range' in explanation or 'within expected' in explanation
        assert 'below threshold' in explanation or 'below threshold' in explanation.lower()
        assert 'Priority rank' in explanation
    
    def test_explain_genuine_anomaly(self):
        """Test explanation for a genuine anomaly with high excess cost."""
        explainer = AnomalyExplainer()
        row = self.create_sample_anomaly()
        
        explanation = explainer.explain_anomaly(row)
        
        assert 'AWS' in explanation
        assert '$150.00' in explanation or '150.00' in explanation
        assert '30.0%' in explanation or '30.0%' in explanation
        assert 'anomalous' in explanation.lower()
        assert 'Priority rank' in explanation
        assert 'Cost-impact score' in explanation
        assert 'cumulative excess' in explanation.lower()
    
    def test_explain_high_cost_normal(self):
        """Test explanation for high-cost but normal observation (gate should prevent ranking)."""
        explainer = AnomalyExplainer()
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 1000.0,
            'expected_cost': 1000.0,
            'excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.1,  # Low anomaly score (not anomalous)
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 30,
            'anomaly_score_rank': 40,
            'excess_cost_rank': 20,
            'cumulative_excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.1,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 30,
            'anomaly_score_rank': 30,
            'excess_cost_rank': 20,
            'cumulative_excess_cost': 0.0,
        })
        
        explanation = AnomalyExplainer().explain_anomaly(row)
        
        # Should mention it's within expected range
        assert 'within expected' in explanation or 'within expected' in explanation.lower()
        # Should not claim it's an anomaly
        assert 'anomalous' not in explanation.lower() or 'not anomalous' in explanation.lower()
    
    def test_explain_zero_excess_cost(self):
        """Test explanation handles zero excess cost correctly."""
        explainer = AnomalyExplainer()
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'GCP',
            'observed_cost': 400.0,
            'expected_cost': 400.0,
            'excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.5,
            'anomaly_label': 0,
            'cost_impact_score': 0.2,
            'cost_impact_rank': 25,
            'anomaly_score_rank': 20,
            'excess_cost_rank': 30,
            'cumulative_excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.3,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 25,
            'anomaly_score_rank': 20,
            'excess_cost_rank': 30,
            'cumulative_excess_cost': 0.0,
        })
        
        explanation = AnomalyExplainer().explain_anomaly(row)
        
        assert 'GCP' in explanation
        assert '$0.00' in explanation or '0.00' in explanation
    
    def test_explain_with_persistence(self):
        """Test explanation includes persistence information."""
        explainer = AnomalyExplainer()
        row = self.create_sample_anomaly(cumulative_excess_cost=1500.0)
        
        explanation = AnomalyExplainer().explain_anomaly(row)
        
        assert 'cumulative' in explanation.lower()
        assert '1,500.00' in explanation or '1500.00' in explanation
    
    def test_explain_batch(self):
        """Test batch explanation generation."""
        explainer = AnomalyExplainer()
        
        # Create multiple anomalies
        rows = []
        for i in range(5):
            row = self.create_sample_anomaly(
                date=pd.Timestamp(f'2024-06-{15+i}'),
                cost_impact_rank=i+1,
                cost_impact_score=0.9 - i*0.1
            )
            rows.append(row)
        
        df = pd.DataFrame(rows)
        explanations = AnomalyExplainer().explain_batch(pd.DataFrame(rows), top_k=3)
        
        assert len(explanations) == 3
        for exp in explanations:
            assert 'explanation' in exp
            assert 'cost_impact_score' in exp
            assert 'date' in exp
    
    def test_format_for_ui(self):
        """Test UI formatting function."""
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 500.0,
        })
        
        ui_format = format_anomaly_for_ui(pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 500.0,
        }))
        
        assert ui_format['severity'] == 'ANOMALY'
        assert ui_format['excess_cost'] == '$150.00'
        assert ui_format['relative_deviation'] == '30.0%'
        assert ui_format['priority_rank'] == '#1'
        assert 'ANOMALY' in ui_format['severity']
    
    def test_explain_zero_excess_cost(self):
        """Test explanation handles zero excess cost correctly."""
        explainer = AnomalyExplainer()
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'GCP',
            'observed_cost': 400.0,
            'expected_cost': 400.0,
            'excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.3,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 25,
            'anomaly_score_rank': 20,
            'excess_cost_rank': 30,
            'cumulative_excess_cost': 0.0,
            'relative_deviation': 0.0,
            'anomaly_score': -0.3,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 25,
            'anomaly_score_rank': 20,
            'excess_cost_rank': 30,
            'cumulative_excess_cost': 0.0,
        })
        
        explanation = AnomalyExplainer().explain_anomaly(row)
        
        assert 'GCP' in explanation
        assert '$0.00' in explanation or '0.00' in explanation
    
    def test_generate_explanations_for_ranking(self):
        """Test batch explanation generation for ranked results."""
        # Create ranked DataFrame
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10, freq='D'),
            'provider': ['AWS'] * 10,
            'observed_cost': np.random.uniform(400, 600, 10),
            'expected_cost': np.random.uniform(400, 500, 10),
            'anomaly_score': np.random.uniform(-0.8, -0.2, 10),
            'anomaly_label': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
            'cost_impact_score': np.random.uniform(0.1, 1.0, 10),
            'anomaly_label': [0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        })
        df['excess_cost'] = np.maximum(
            np.random.uniform(0, 200, 10), 0
        )
        df['relative_deviation'] = np.random.uniform(-0.1, 0.5, 10)
        df['anomaly_score'] = np.random.uniform(-0.8, -0.2, 10)
        df['anomaly_label'] = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        df['cost_impact_score'] = np.random.uniform(0.1, 1.0, 10)
        df['anomaly_label'] = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        df['cost_impact_rank'] = range(1, 11)
        df['anomaly_score_rank'] = range(1, 11)
        df['excess_cost_rank'] = range(1, 11)
        df['cumulative_excess_cost'] = 0
        
        explanations = generate_explanations_for_ranking(df, top_k=3)
        
        assert len(explanations) == 3
        for exp in explanations:
            assert 'explanation' in exp
            assert 'cost_impact_score' in exp
            assert 'date' in exp
    
    def test_deterministic_output(self):
        """Test that explanations are deterministic."""
        explainer = AnomalyExplainer()
        row = self.create_sample_anomaly()
        
        exp1 = explainer.explain_anomaly(row)
        exp2 = explainer.explain_anomaly(row)
        
        assert exp1 == exp2


class TestFormatAnomalyForUI:
    """Tests for the format_anomaly_for_ui function."""
    
    def test_format_anomaly(self):
        """Test UI formatting for an anomaly."""
        row = pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 500.0,
        })
        
        ui_format = format_anomaly_for_ui(pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 500.0,
        }))
        
        assert ui_format['severity'] == 'ANOMALY'
        assert ui_format['excess_cost'] == '$150.00'
        assert ui_format['relative_deviation'] == '30.0%'
        assert ui_format['priority_rank'] == '#1'
        assert ui_format['is_anomaly'] is True
        assert ui_format['cumulative_excess'] == '$500.00'
    
    def test_format_normal(self):
        """Test UI formatting for normal (non-anomalous) observation."""
        ui_format = format_anomaly_for_ui(pd.Series({
            'date': pd.Timestamp('2024-06-15'),
            'provider': 'AWS',
            'observed_cost': 480.0,
            'expected_cost': 500.0,
            'excess_cost': 0.0,
            'relative_deviation': -0.04,
            'anomaly_score': -0.1,
            'anomaly_label': 0,
            'cost_impact_score': 0.1,
            'cost_impact_rank': 50,
            'cumulative_excess_cost': 0.0,
        }))
        
        assert ui_format['severity'] == 'Normal'
        assert ui_format['excess_cost'] == '$0.00'
        assert ui_format['is_anomaly'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])