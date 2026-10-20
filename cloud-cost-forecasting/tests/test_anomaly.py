"""
Tests for anomaly detection and cost-impact ranking.

Covers:
  - Anomaly type classification (SPIKE vs DROP with emoji labels)
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

        # All anomalies should be classified as SPIKE (with emoji)
        assert (ranked['anomaly_type'] == '📈 SPIKE').all()
        # All should have positive cost_deviation (magnitude)
        assert (ranked['cost_deviation'] > 0).all()
        # Cost impact label should indicate excess spend
        assert all('Excess Spend' in label for label in ranked['cost_impact_label'])
        # excess_cost should be numeric (for calculations)
        assert pd.api.types.is_numeric_dtype(ranked['excess_cost'])
        # cost_impact_label should be formatted as +$X.XX Excess Spend
        assert all(label.startswith('+$') for label in ranked['cost_impact_label'])

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

        # All anomalies should be classified as DROP (with emoji)
        assert (ranked['anomaly_type'] == '📉 DROP').all()
        # All should have positive cost_deviation (magnitude)
        assert (ranked['cost_deviation'] > 0).all()
        # Cost impact label should indicate drop
        assert all('Drop' in label for label in ranked['cost_impact_label'])
        assert all('Possible Outage/Idle' in label for label in ranked['cost_impact_label'])
        # excess_cost should be numeric (for calculations)
        assert pd.api.types.is_numeric_dtype(ranked['excess_cost'])
        # cost_impact_label should be formatted as -$X.XX Drop
        assert all(label.startswith('-$') for label in ranked['cost_impact_label'])

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
        assert (ranked['anomaly_type'].iloc[[0, 2, 4]] == '📈 SPIKE').all()
        # Rows 1,3,5: observed < expected → DROP
        assert (ranked['anomaly_type'].iloc[[1, 3, 5]] == '📉 DROP').all()

        # SPIKE rows should have positive cost_deviation
        spike_rows = ranked[ranked['anomaly_type'] == '📈 SPIKE']
        assert (spike_rows['cost_deviation'] > 0).all()
        assert all(label.startswith('+$') for label in spike_rows['cost_impact_label'])

        # DROP rows should have positive cost_deviation
        drop_rows = ranked[ranked['anomaly_type'] == '📉 DROP']
        assert (drop_rows['cost_deviation'] > 0).all()
        assert all(label.startswith('-$') for label in drop_rows['cost_impact_label'])

    def test_cost_impact_score_uses_type_appropriate_deviation(self):
        """Cost-impact scoring should use cost_deviation magnitude for both types."""
        # Create data where a DROP anomaly has large cost deviation
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

        # DROP anomalies should have positive cost_deviation
        drop_rows = ranked[ranked['anomaly_type'] == '📉 DROP']
        assert len(drop_rows) == 2
        assert (drop_rows['cost_deviation'] > 0).all()
        assert all(label.startswith('-$') for label in drop_rows['cost_impact_label'])

    def test_production_scenario_spike_and_drop(self):
        """Production scenario: SPIKE row ($1108 vs $407) and DROP row ($399 vs $433)."""
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=2, freq='D'),
            'cost_usd': [1108.0, 399.0],
        })
        anomaly_scores = np.array([-0.9, -0.8])
        anomaly_labels = np.array([1, 1])
        actual_costs = test_data['cost_usd'].values
        # Row 0: observed=1108 > expected=407 → SPIKE, cost_deviation = 701
        # Row 1: observed=399 < expected=433 → DROP, cost_deviation = 34
        expected_costs = np.array([407.0, 433.0])

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        spike_row = ranked[ranked['anomaly_type'] == '📈 SPIKE'].iloc[0]
        drop_row = ranked[ranked['anomaly_type'] == '📉 DROP'].iloc[0]

        # SPIKE: cost_deviation = 1108 - 407 = 701 > 700
        assert spike_row['cost_deviation'] > 700
        # SPIKE severity contains "Overspend"
        assert 'Overspend' in spike_row['severity']

        # DROP: cost_deviation = 433 - 399 = 34
        assert drop_row['cost_deviation'] == 34.0
        # DROP severity contains "Underspend"
        assert 'Underspend' in drop_row['severity']

        # Verify formatted labels
        assert '+$701.00 Excess Spend' in spike_row['cost_impact_label']
        assert '-$34.00 Drop (Possible Outage/Idle)' in drop_row['cost_impact_label']


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
            'excess_cost': '-$200.00 Drop (Possible Outage/Idle)',
            'cost_deviation': 200.0,
            'anomaly_type': '📉 DROP',
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
            'excess_cost': '-$200.00 Drop (Possible Outage/Idle)',
            'cost_deviation': 200.0,
            'anomaly_type': '📉 DROP',
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
        assert result['excess_cost'] == '-$200.00 Drop (Possible Outage/Idle)'

    def test_spike_anomaly_explanation(self):
        """SPIKE anomaly explanation should mention excess spend amount."""
        from app.anomaly.explanations import AnomalyExplainer

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': '+$150.00 Excess Spend',
            'cost_deviation': 150.0,
            'anomaly_type': '📈 SPIKE',
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.9,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 0.0,
        })

        explainer = AnomalyExplainer()
        explanation = explainer.explain_anomaly(row)

        # Should mention excess spend
        assert 'exceeded expected' in explanation
        assert '$150.00' in explanation

    def test_format_explanation_for_ui_spike(self):
        """format_explanation_for_ui should show excess financial summary for SPIKE anomalies."""
        from app.anomaly.explanations import format_anomaly_for_ui

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': '+$150.00 Excess Spend',
            'cost_deviation': 150.0,
            'anomaly_type': '📈 SPIKE',
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.9,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 0.0,
        })

        result = format_anomaly_for_ui(row)

        # Financial summary should mention excess
        assert 'excess' in result['financial_summary'].lower()
        assert '$150.00' in result['financial_summary']
        assert result['excess_cost'] == '+$150.00 Excess Spend'


class TestAnomalyExpanderStringFormatting:
    """Tests for safe excess_cost formatting in UI explainers.

    Regression test for crash: ValueError: Unknown format code 'f' for object
    of type 'str' when excess_cost is a pre-formatted string (e.g. "+$701.93 Excess Spend")
    instead of a raw float.
    """

    def test_explanation_dict_string_excess_cost(self):
        """explanation dict with string excess_cost should format safely in expander title."""
        from app.anomaly.explanations import format_anomaly_for_ui

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 1108.0,
            'expected_cost': 407.0,
            'excess_cost': '+$701.93 Excess Spend',  # pre-formatted string
            'cost_deviation': 701.93,
            'anomaly_type': '📈 SPIKE',
            'relative_deviation': 1.72,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.92,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 701.93,
        })

        # format_explanation_for_ui must not crash on string excess_cost
        result = format_anomaly_for_ui(row)
        assert result['excess_cost'] == '+$701.93 Excess Spend'

        # Simulate the app.py expander title construction with type-safe formatting
        excess_val = result.get('excess_cost', 0)
        if isinstance(excess_val, str):
            excess_display = excess_val
        else:
            excess_display = f"${excess_val:,.2f} excess"

        assert excess_display == '+$701.93 Excess Spend'

    def test_explanation_dict_float_excess_cost(self):
        """explanation dict with float excess_cost should format safely in expander title."""
        from app.anomaly.explanations import format_anomaly_for_ui

        row = pd.Series({
            'date': pd.Timestamp('2024-02-15'),
            'provider': 'AWS',
            'observed_cost': 650.0,
            'expected_cost': 500.0,
            'excess_cost': 150.0,  # raw float
            'cost_deviation': 150.0,
            'anomaly_type': '📈 SPIKE',
            'relative_deviation': 0.3,
            'anomaly_score': -0.85,
            'anomaly_label': 1,
            'cost_impact_score': 0.9,
            'cost_impact_rank': 1,
            'cumulative_excess_cost': 150.0,
        })

        result = format_anomaly_for_ui(row)
        # Float excess_cost gets formatted as "$150.00" by format_anomaly_for_ui
        assert result['excess_cost'] == '$150.00'

        # Simulate the app.py expander title construction with type-safe formatting
        excess_val = result.get('excess_cost', 0)
        if isinstance(excess_val, str):
            excess_display = excess_val
        else:
            excess_display = f"${excess_val:,.2f} excess"

        assert excess_display == '$150.00'


class TestSchemaRegression:
    """Regression tests for the anomaly schema fix (numeric excess_cost + formatted label separation)."""

    def test_excess_cost_is_numeric_for_summation(self):
        """Verify ranked_results['excess_cost'].sum() works as float without ValueError.

        Regression test for: ValueError: could not convert string to float
        when excess_cost was stored as pre-formatted strings.
        """
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=5, freq='D'),
            'cost_usd': [500.0, 600.0, 700.0, 800.0, 900.0],
        })
        anomaly_scores = np.random.uniform(-1.0, 1.0, 5)
        anomaly_labels = np.array([1, 1, 0, 1, 0])
        actual_costs = test_data['cost_usd'].values
        expected_costs = actual_costs * 0.9  # observed > expected (SPIKE)

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=test_data,
            anomaly_scores=anomaly_scores,
            anomaly_labels=anomaly_labels,
            actual_costs=actual_costs,
            expected_costs=expected_costs,
            mape=0.05
        )

        # excess_cost should be numeric (float/int)
        assert pd.api.types.is_numeric_dtype(ranked['excess_cost'])
        
        # Summation should work without ValueError
        total_excess = ranked['excess_cost'].sum()
        assert isinstance(total_excess, (int, float))
        assert not np.isnan(total_excess)
        
        # Safe conversion with pd.to_numeric (as used in app.py)
        total_excess_safe = float(pd.to_numeric(ranked['excess_cost'], errors='coerce').fillna(0).sum())
        assert isinstance(total_excess_safe, float)
        assert not np.isnan(total_excess_safe)
        
        # Verify the sum matches expected SPIKE excess costs for ALL rows
        # excess_cost is max(observed - expected, 0) for all rows
        expected_total = sum(
            max(actual - expected, 0) 
            for actual, expected in zip(actual_costs, actual_costs * 0.9)
        )
        assert abs(total_excess - expected_total) < 0.01

    def test_cost_impact_label_is_formatted_string(self):
        """Verify cost_impact_label contains formatted strings for UI display."""
        test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-02-10', periods=2, freq='D'),
            'cost_usd': [1108.0, 399.0],
        })
        anomaly_scores = np.array([-0.9, -0.8])
        anomaly_labels = np.array([1, 1])
        actual_costs = np.array([1108.0, 399.0])
        expected_costs = np.array([407.0, 433.0])

        scorer = CostImpactScorer()
        ranked = scorer.rank_anomalies(
            test_data=pd.DataFrame({'date': test_data['date'], 'cost_usd': test_data['cost_usd']}),
            anomaly_scores=np.array([-0.9, -0.8]),
            anomaly_labels=np.array([1, 1]),
            actual_costs=np.array([1108.0, 399.0]),
            expected_costs=np.array([407.0, 433.0]),
            mape=0.05
        )

        spike_row = ranked[ranked['anomaly_type'] == '📈 SPIKE'].iloc[0]
        drop_row = ranked[ranked['anomaly_type'] == '📉 DROP'].iloc[0]

        # cost_impact_label should be formatted strings
        assert isinstance(spike_row['cost_impact_label'], str)
        assert '+$701.00 Excess Spend' in spike_row['cost_impact_label']
        
        assert isinstance(drop_row['cost_impact_label'], str)
        assert '-$34.00 Drop (Possible Outage/Idle)' in drop_row['cost_impact_label']
        
        # excess_cost should be numeric
        assert pd.api.types.is_numeric_dtype(ranked['excess_cost'])
        assert spike_row['excess_cost'] == 701.0
        assert drop_row['excess_cost'] == 0.0
