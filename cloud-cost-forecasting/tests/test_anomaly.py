"""
Tests for anomaly detection and cost-impact ranking.

Covers:
  - Anomaly type classification (SPIKE vs DROP)
  - Cost deviation calculation for DROP anomalies
  - Cost impact label formatting
  - Explanation generation for DROP anomalies

All tests run offline with no external API dependencies.
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# Ensure the repository root is on sys.path so `app.anomaly.cost_aware` is
# importable from the tests/ directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.anomaly.cost_aware import CostImpactScorer


@pytest.fixture
def spike_anomaly_data() -> pd.DataFrame:
    """Test data where observed > expected (SPIKE/overspend)."""
    return pd.DataFrame({
        'date': pd.date_range(start='2024-02-10', periods=5, freq='D'),
        'cost_usd': [500.0, 600.0, 700.0, 800.0, 900.0],
    })


@pytest.fixture
def drop_anomaly_data() -> pd.DataFrame:
    """Test data where observed < expected (DROP/underspend)."""
    return pd.DataFrame({
        'date': pd.date_range(start='2024-02-10', periods=5, freq='D'),
        'cost_usd': [300.0, 250.0, 200.0, 150.0, 100.0],
    })


@pytest.fixture
def mixed_anomaly_data() -> pd.DataFrame:
    """Test data with mix of SPIKE and DROP anomalies."""
    return pd.DataFrame({
        'date': pd.date_range(start='2024-02-10', periods=6, freq='D'),
        'cost_usd': [500.0, 300.0, 700.0, 200.0, 600.0, 150.0],
    })


class TestAnomalyTypeClassification:
    """Tests for SPIKE vs DROP anomaly type classification."""

    def test_spike_anomaly_classification(self, spike_anomaly_data):
        """Observed > expected should be classified as SPIKE."""
        n = len(spike_anomaly_data)
        anomaly_scores = np.random.uniform(-1.0, 1.0, n)
        anomaly_labels = np.array([1] * n)  # all anomalies
        actual_costs = spike_anomaly_data['cost_usd'].values
        expected_costs = actual_costs * 0.9  # observed > expected

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=spike_anomaly_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # All anomalies should be classified as SPIKE
        assert (ranked['anomaly_type'] == 'SPIKE').all()
        # All should have positive excess_cost
        assert (ranked['excess_cost'] > 0).all()
        # All should have zero cost_deviation
        assert (ranked['cost_deviation'] == 0).all()
        # Cost impact label should indicate excess spend
        assert all('Excess Spend' in label for label in ranked['cost_impact_label'])

    def test_drop_anomaly_classification(self, drop_anomaly_data):
        """Observed < expected should be classified as DROP."""
        n = len(drop_anomaly_data)
        anomaly_scores = np.random.uniform(-1.0, 1.0, n)
        anomaly_labels = np.array([1] * n)  # all anomalies
        actual_costs = drop_anomaly_data['cost_usd'].values
        expected_costs = actual_costs * 1.5  # observed < expected

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=drop_anomaly_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # All anomalies should be classified as DROP
        assert (ranked['anomaly_type'] == 'DROP').all()
        # All should have zero excess_cost
        assert (ranked['excess_cost'] == 0).all()
        # All should have positive cost_deviation
        assert (ranked['cost_deviation'] > 0).all()
        # Cost impact label should indicate drop
        assert all('Drop' in label for label in ranked['cost_impact_label'])
        assert all('Possible Outage/Idle' in label for label in ranked['cost_impact_label'])

    def test_mixed_anomaly_classification(self, mixed_anomaly_data):
        """Mixed observed > expected and observed < expected should classify correctly."""
        n = len(mixed_anomaly_data)
        anomaly_scores = np.random.uniform(-1.0, 1.0, n)
        anomaly_labels = np.array([1] * n)  # all anomalies
        actual_costs = mixed_anomaly_data['cost_usd'].values
        # Rows 0,2,4 are SPIKE (observed > expected), rows 1,3,5 are DROP (observed < expected)
        expected_costs = np.array([400.0, 400.0, 600.0, 300.0, 500.0, 300.0])

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=mixed_anomaly_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # Rows 0,2,4: observed > expected → SPIKE
        assert (ranked['anomaly_type'].iloc[[0, 2, 4]] == 'SPIKE').all()
        # Rows 1,3,5: observed < expected → DROP
        assert (ranked['anomaly_type'].iloc[[1, 3, 5]] == 'DROP').all()

        # SPIKE rows should have positive excess_cost, zero cost_deviation
        spike_rows = ranked[ranked['anomaly_type'] == 'SPIKE']
        assert (spike_rows['excess_cost'] > 0).all()
        assert (spike_rows['cost_deviation'] == 0).all()

        # DROP rows should have zero excess_cost, positive cost_deviation
        drop_rows = ranked[ranked['anomaly_type'] == 'DROP']
        assert (drop_rows['excess_cost'] == 0).all()
        assert (drop_rows['cost_deviation'] > 0).all()

    def test_cost_impact_score_uses_type_appropriate_deviation(self):
        """Cost-impact scoring should use excess_cost for SPIKE and cost_deviation for DROP."""
        # Create data where a DROP anomaly has large cost deviation
        # but zero excess_cost
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=3, freq='D'),
            'cost_usd': [100.0, 500.0, 100.0],
        })
        anomaly_scores = np.array([-0.9, -0.1, -0.9])
        anomaly_labels = np.array([1, 1, 1])
        actual_costs = test_data['cost_usd'].values
        # Row 0: observed=100 < expected=500 → DROP, large deviation
        # Row 1: observed=500 > expected=100 → SPIKE, large excess
        # Row 2: observed=100 < expected=500 → DROP, large deviation
        expected_costs = np.array([500.0, 100.0, 500.0])

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # DROP anomalies should still get cost-impact scoring boost
        # (via cost_deviation instead of excess_cost)
        drop_rows = ranked[ranked['anomaly_type'] == 'DROP']
        assert len(drop_rows) == 2
        assert (drop_rows['cost_deviation'] > 0).all()
        assert (drop_rows['excess_cost'] == 0).all()


class TestAnomalyExplanations:
    """Tests for anomaly explanation generation with anomaly types."""

    def test_drop_anomaly_explanation(self):
        """DROP anomaly explanation should mention drop amount and possible outage."""
        from app.anomaly.explanations import AnomalyExplainer

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 300.0,
            'expected_cost': 500.0,
            'excess_cost': 0.0,
            'cost_deviation': 200.0,
            'anomaly_type': 'DROP',
            'relative_deviation': -0.4,
            'anomaly_score': -0.7,
            'anomaly_label': 1,
            'cost_impact_score': 0.8,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 0.0,
        })

        explainer = AnomalyExplainer()
        explanation = explainer.explain_anomaly(row)

        # Should mention drop and possible outage
        assert 'below expected' in explanation
        assert '$200.00' in explanation
        assert 'outage' in explanation.lower() or 'idle' in explanation.lower()

    def test_format_explanation_for_ui_drop(self):
        """format_explanation_for_ui should show drop financial summary for DROP anomalies."""
        from app.anomaly.explanations import format_anomaly_for_ui

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 300.0,
            'expected_cost': 500.0,
            'excess_cost': 0.0,
            'cost_deviation': 200.0,
            'anomaly_type': 'DROP',
            'relative_deviation': -0.4,
            'anomaly_score': -0.7,
            'anomaly_label': 1,
            'cost_impact_score': 0.8,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 0.0,
        })

        result = format_anomaly_for_ui(row)

        # Financial summary should mention drop, not excess
        assert 'drop' in result['financial_summary'].lower()
        assert '$200.00' in result['financial_summary']
        assert result['excess_cost'] == '$0.00'
