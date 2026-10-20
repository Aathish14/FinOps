"""Tests for the Download Analysis export module.

Covers:
  - CSV output content and columns
  - Excel workbook validity and sheet contents
  - PDF generation and non-empty output
  - JSON validity and serialization of supported data types
  - Graceful handling of missing or partial results
  - Empty result tables
  - Filename sanitization and formula-injection protection

All tests run offline with no external API dependencies.
"""

import io
import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Ensure the repository root is on sys.path so `app.export.exporter` is
# importable from the tests/ directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.export.exporter import AnalysisExporter, compute_input_hash  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_ranked_results() -> pd.DataFrame:
    """A ranked anomalies DataFrame as produced by CostImpactScorer."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-06-04", "2024-06-05", "2024-06-06"]),
            "provider": ["AWS", "AWS", "GCP"],
            "observed_cost": [667.67, 692.08, 536.78],
            "expected_cost": [575.55, 601.76, 480.36],
            "excess_cost": [92.12, 90.32, 56.42],
            "relative_deviation": [0.16, 0.15, 0.117],
            "anomaly_score": [-0.73, -0.77, -0.71],
            "anomaly_label": [1, 1, 1],
            "cost_impact_score": [1.13, 1.25, 0.97],
            "is_anomaly": [True, True, True],
            "cumulative_excess_cost": [92.12, 182.44, 56.42],
            "cost_impact_rank": [2, 1, 3],
            "anomaly_score_rank": [53, 55, 54],
            "excess_cost_rank": [1, 2, 1],
        }
    )


@pytest.fixture
def sample_forecast_data() -> pd.DataFrame:
    """A forecast DataFrame as produced by ForecastingModel.predict()."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-07-01", "2024-07-02", "2024-07-03"]),
            "forecast_cost_usd": [520.50, 535.20, 510.80],
            "lower_bound_80": [490.10, 500.30, 480.20],
            "upper_bound_80": [550.90, 570.10, 541.40],
        }
    )


@pytest.fixture
def sample_daily_data() -> pd.DataFrame:
    """Daily aggregated spend data."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
            "cost_usd": [500.0, 520.0, 480.0],
        }
    )


@pytest.fixture
def sample_raw_data() -> pd.DataFrame:
    """Raw ingested billing data."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-06-01", "2024-06-01", "2024-06-01"]),
            "cloud_provider": ["AWS", "AWS", "GCP"],
            "service_name": ["AmazonEC2", "AmazonS3", "Compute Engine"],
            "account_id": ["123456789012", "123456789012", "project-beta"],
            "region": ["us-east-1", "eu-west-1", "us-central1"],
            "environment": ["production", "production", "production"],
            "usage_quantity": [100.0, 80.0, 120.0],
            "usage_unit": ["hours", "GB-month", "hours"],
            "cost_usd": [150.0, 25.0, 48.0],
        }
    )


@pytest.fixture
def complete_results(
    sample_ranked_results,
    sample_forecast_data,
    sample_daily_data,
    sample_raw_data,
) -> dict:
    """A complete results dictionary as stored in session state."""
    return {
        "source_file": "sample_aws_billing.csv",
        "generated_at": datetime(2024, 6, 15, 10, 30, 0),
        "config": {
            "forecast_horizon": 30,
            "interval_width": 0.95,
            "seasonality_mode": "additive",
            "weekly_seasonality": "auto",
            "yearly_seasonality": "auto",
            "contamination": 0.05,
            "n_estimators": 100,
        },
        "raw_data": sample_raw_data,
        "daily_data": sample_daily_data,
        "forecast_data": sample_forecast_data,
        "eval_metrics": {"mape": 0.046, "rmse": 23.66, "mae": 18.50},
        "ranked_results": sample_ranked_results,
        "explanations": [
            {
                "date": pd.Timestamp("2024-06-05"),
                "provider": "AWS",
                "cost_impact_rank": 1,
                "explanation": "On 2024-06-05 (AWS): Observed cost ($692.08) exceeded expected cost ($601.76) by $90.32 (15.0%).",
                "cost_impact_score": 1.25,
                "excess_cost": 90.32,
                "anomaly_label": 1,
            },
        ],
        "anomaly_count": 3,
        "total_excess_cost": 238.86,
    }


@pytest.fixture
def minimal_results() -> dict:
    """Minimal results with only ranked data, no forecast or raw data."""
    return {
        "source_file": "test.csv",
        "generated_at": datetime(2024, 6, 15, 10, 30, 0),
        "config": {"forecast_horizon": 30, "contamination": 0.05},
        "ranked_results": pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-06-05"]),
                "provider": ["AWS"],
                "observed_cost": [692.08],
                "expected_cost": [601.76],
                "excess_cost": [90.32],
                "relative_deviation": [0.15],
                "anomaly_score": [-0.77],
                "anomaly_label": [1],
                "cost_impact_score": [1.25],
                "is_anomaly": [True],
                "cumulative_excess_cost": [90.32],
                "cost_impact_rank": [1],
                "anomaly_score_rank": [1],
                "excess_cost_rank": [1],
            }
        ),
        "explanations": [],
        "anomaly_count": 1,
        "total_excess_cost": 90.32,
    }


@pytest.fixture
def empty_results() -> dict:
    """Results with no data at all."""
    return {
        "source_file": "empty.csv",
        "generated_at": datetime(2024, 6, 15, 10, 30, 0),
        "config": {"forecast_horizon": 30},
        "raw_data": pd.DataFrame(),
        "daily_data": pd.DataFrame(),
        "forecast_data": pd.DataFrame(),
        "eval_metrics": {},
        "ranked_results": pd.DataFrame(),
        "explanations": [],
        "anomaly_count": 0,
        "total_excess_cost": 0.0,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExportCSV:
    """Tests for CSV export."""

    def test_csv_contains_ranked_results(self, complete_results):
        exporter = AnalysisExporter(complete_results)
        data = exporter.to_csv()
        assert len(data) > 0
        text = data.decode("utf-8")
        assert "observed_cost" in text
        assert "expected_cost" in text
        assert "excess_cost" in text
        assert "cost_impact_score" in text
        assert "692.08" in text or "667.67" in text

    def test_csv_with_empty_results(self, empty_results):
        exporter = AnalysisExporter(empty_results)
        data = exporter.to_csv()
        text = data.decode("utf-8")
        # Should not crash; should produce some output (header or message)
        assert len(text) > 0

    def test_csv_formula_injection_protection(self):
        """Cells starting with formula characters should be prefixed with tab."""
        results = {
            "source_file": "test.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "observed_cost": [100.0],
                    "expected_cost": [50.0],
                    "excess_cost": [50.0],
                    "relative_deviation": [1.0],
                    "anomaly_score": [-0.5],
                    "anomaly_label": [1],
                    "cost_impact_score": [0.8],
                    "is_anomaly": [True],
                    "cumulative_excess_cost": [50.0],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                    "provider": ['=HACK()'],  # formula injection attempt
                }
            ),
            "anomaly_count": 1,
            "total_excess_cost": 50.0,
        }
        exporter = AnalysisExporter(results)
        data = exporter.to_csv()
        text = data.decode("utf-8")
        # The formula-starting character should be neutralized with a tab prefix
        assert '\t=HACK()' in text or '=HACK()' not in text.replace('\t', '')


class TestExportExcel:
    """Tests for Excel export."""

    def test_excel_is_valid_workbook(self, complete_results):
        exporter = AnalysisExporter(complete_results)
        data = exporter.to_excel()
        assert len(data) > 0
        # Verify it can be reopened
        wb = __import__("openpyxl").load_workbook(io.BytesIO(data))
        assert len(wb.sheetnames) > 0
        sheet_names = set(wb.sheetnames)
        assert "Summary" in sheet_names

    def test_excel_has_summary_sheet(self, complete_results):
        exporter = AnalysisExporter(complete_results)
        data = exporter.to_excel()
        wb = __import__("openpyxl").load_workbook(io.BytesIO(data))
        assert "Summary" in wb.sheetnames
        ws = wb["Summary"]
        # Check that some config values made it into the sheet
        found_horizon = False
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell == "forecast_horizon":
                    found_horizon = True
        assert found_horizon

    def test_excel_with_empty_results(self, empty_results):
        exporter = AnalysisExporter(empty_results)
        data = exporter.to_excel()
        assert len(data) > 0
        wb = __import__("openpyxl").load_workbook(io.BytesIO(data))
        assert len(wb.sheetnames) >= 1  # At least Summary sheet


class TestExportPDF:
    """Tests for PDF export."""

    def test_pdf_generates_non_empty_output(self, complete_results):
        exporter = AnalysisExporter(complete_results)
        data = exporter.to_pdf()
        assert len(data) > 0
        assert data.startswith(b"%PDF")  # PDF magic bytes

    def test_pdf_with_empty_results(self, empty_results):
        exporter = AnalysisExporter(empty_results)
        data = exporter.to_pdf()
        assert len(data) > 0
        assert data.startswith(b"%PDF")


class TestExportJSON:
    """Tests for JSON export."""

    def test_json_is_valid(self, complete_results):
        exporter = AnalysisExporter(complete_results)
        text = exporter.to_json()
        data = json.loads(text)
        assert "generated_at" in data
        assert "source_file" in data
        assert data["source_file"] == "sample_aws_billing.csv"
        assert "config" in data
        assert data["config"]["forecast_horizon"] == 30

    def test_json_handles_numpy_types(self):
        """JSON serialization should handle numpy types without error."""
        results = {
            "source_file": "test.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {"forecast_horizon": np.int64(30), "contamination": np.float64(0.05)},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "observed_cost": [np.float64(692.08)],
                    "expected_cost": [np.float64(601.76)],
                    "excess_cost": [np.float64(90.32)],
                    "relative_deviation": [np.float64(0.15)],
                    "anomaly_score": [np.float64(-0.77)],
                    "anomaly_label": [np.int64(1)],
                    "cost_impact_score": [np.float64(1.25)],
                    "is_anomaly": [np.bool_(True)],
                    "cumulative_excess_cost": [np.float64(90.32)],
                    "cost_impact_rank": [np.int64(1)],
                    "anomaly_score_rank": [np.int64(1)],
                    "excess_cost_rank": [np.int64(1)],
                    "provider": ["AWS"],
                }
            ),
            "explanations": [],
            "anomaly_count": np.int64(1),
            "total_excess_cost": np.float64(90.32),
        }
        exporter = AnalysisExporter(results)
        text = exporter.to_json()
        data = json.loads(text)
        assert data["config"]["forecast_horizon"] == 30
        assert data["config"]["contamination"] == 0.05

    def test_json_with_nan_and_inf(self):
        """JSON export should handle NaN/Inf gracefully (convert to null)."""
        results = {
            "source_file": "test.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "observed_cost": [np.nan],
                    "expected_cost": [np.inf],
                    "excess_cost": [np.nan],
                    "relative_deviation": [np.nan],
                    "anomaly_score": [np.float64(-0.5)],
                    "anomaly_label": [np.int64(0)],
                    "cost_impact_score": [np.float64(0.0)],
                    "is_anomaly": [np.bool_(False)],
                    "cumulative_excess_cost": [np.float64(0.0)],
                    "cost_impact_rank": [np.int64(1)],
                    "anomaly_score_rank": [np.int64(1)],
                    "excess_cost_rank": [np.int64(1)],
                    "provider": ["AWS"],
                }
            ),
            "explanations": [],
            "anomaly_count": 0,
            "total_excess_cost": np.nan,
        }
        exporter = AnalysisExporter(results)
        text = exporter.to_json()
        data = json.loads(text)  # Should not raise
        # NaN/Inf values should be converted to None/null
        assert data["ranked_results"][0]["observed_cost"] is None
        assert data["ranked_results"][0]["expected_cost"] is None


class TestExportStaleResults:
    """Tests for stale-result prevention."""

    def test_different_datasets_produce_different_exports(self, complete_results, minimal_results):
        exporter1 = AnalysisExporter(complete_results)
        exporter2 = AnalysisExporter(minimal_results)
        csv1 = exporter1.to_csv()
        csv2 = exporter2.to_csv()
        assert csv1 != csv2


class TestExportFilenameSanitization:
    """Tests for filename sanitization."""

    def test_sanitized_filename(self):
        results = {
            "source_file": "../../evil/../sample_aws_billing.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "observed_cost": [100.0],
                    "expected_cost": [50.0],
                    "excess_cost": [50.0],
                    "relative_deviation": [1.0],
                    "anomaly_score": [-0.5],
                    "anomaly_label": [1],
                    "cost_impact_score": [0.8],
                    "is_anomaly": [True],
                    "cumulative_excess_cost": [50.0],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                    "provider": ["AWS"],
                }
            ),
            "anomaly_count": 1,
            "total_excess_cost": 50.0,
        }
        exporter = AnalysisExporter(results)
        csv_data = exporter.to_csv()
        assert len(csv_data) > 0  # Should not crash on weird filename


# ---------------------------------------------------------------------------
# ComputeInputHash tests
# ---------------------------------------------------------------------------


class TestComputeInputHash:
    """Tests for deterministic fingerprinting of analysis inputs."""

    def _config(self) -> dict:
        return {
            "forecast_horizon": 30,
            "interval_width": 0.95,
            "seasonality_mode": "additive",
            "weekly_seasonality": "auto",
            "yearly_seasonality": "auto",
            "contamination": 0.05,
            "n_estimators": 100,
        }

    def test_same_inputs_produce_same_hash(self):
        """Identical inputs must always produce the same digest."""
        files = {"sample_aws_billing.csv": b"a,b,c\n1,2,3\n"}
        cfg = self._config()
        h1 = compute_input_hash(files, cfg)
        h2 = compute_input_hash(files, cfg)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_changed_file_contents_change_hash(self):
        """Changing file content (even with same name and size) changes hash."""
        files_a = {"data.csv": b"a,b,c\n1,2,3\n"}
        files_b = {"data.csv": b"x,y,z\n9,9,9\n"}  # same name, same size, diff content
        cfg = self._config()
        assert compute_input_hash(files_a, cfg) != compute_input_hash(files_b, cfg)

    def test_changed_config_changes_hash(self):
        """Changing any hyperparameter changes the hash."""
        files = {"data.csv": b"a,b,c\n1,2,3\n"}
        cfg_a = self._config()
        cfg_b = self._config()
        cfg_b["contamination"] = 0.1  # different contamination
        assert compute_input_hash(files, cfg_a) != compute_input_hash(files, cfg_b)

    def test_file_order_independence(self):
        """Reordering files must not change the digest."""
        files = {
            "file_a.csv": b"content_a",
            "file_b.csv": b"content_b",
            "file_c.csv": b"content_c",
        }
        cfg = self._config()
        h_forward = compute_input_hash(files, cfg)
        files_reversed = {
            "file_c.csv": b"content_c",
            "file_b.csv": b"content_b",
            "file_a.csv": b"content_a",
        }
        h_reverse = compute_input_hash(files_reversed, cfg)
        assert h_forward == h_reverse

    def test_multiple_files_all_contribute(self):
        """Each file's contents must contribute to the hash."""
        files_a = {"a.csv": b"aaa", "b.csv": b"bbb"}
        files_b = {"a.csv": b"aaa", "b.csv": b"bbc"}  # only b changed
        cfg = self._config()
        assert compute_input_hash(files_a, cfg) != compute_input_hash(files_b, cfg)

    def test_empty_file_list_still_produces_digest(self):
        """No files should still produce a valid hash from config alone."""
        cfg = self._config()
        h = compute_input_hash({}, cfg)
        assert len(h) == 64
        assert h != ""  # non-empty digest


# ---------------------------------------------------------------------------
# PDF escaping tests
# ---------------------------------------------------------------------------


class TestExportPDFEscaping:
    """Tests for PDF text escaping of user-provided content."""

    def test_html_sensitive_provider_name(self, complete_results):
        """Provider names with XML-special characters must not break PDF."""
        results = dict(complete_results)
        results["ranked_results"] = complete_results["ranked_results"].copy()
        results["ranked_results"].loc[0, "provider"] = 'ACME & Co <script>'
        exporter = AnalysisExporter(results)
        data = exporter.to_pdf()
        assert len(data) > 0
        assert data.startswith(b"%PDF")  # valid PDF

    def test_ampersand_in_filename(self):
        """Filename with ampersand must produce valid PDF."""
        results = {
            "source_file": "A&B Consulting.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "provider": ["AWS"],
                    "observed_cost": [100.0],
                    "expected_cost": [50.0],
                    "excess_cost": [50.0],
                    "relative_deviation": [1.0],
                    "anomaly_score": [-0.5],
                    "anomaly_label": [1],
                    "cost_impact_score": [0.8],
                    "is_anomaly": [True],
                    "cumulative_excess_cost": [50.0],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                }
            ),
            "anomaly_count": 1,
            "total_excess_cost": 50.0,
        }
        exporter = AnalysisExporter(results)
        data = exporter.to_pdf()
        assert len(data) > 0
        assert data.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Excel header sanitization tests
# ---------------------------------------------------------------------------


class TestExportExcelHeaders:
    """Tests for Excel header sanitization."""

    def test_header_formula_injection(self):
        """Column headers starting with formula chars must be neutralized."""
        results = {
            "source_file": "test.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "=HACK()": [100.0],  # formula injection in header
                    "expected_cost": [50.0],
                    "excess_cost": [50.0],
                    "relative_deviation": [1.0],
                    "anomaly_score": [-0.5],
                    "anomaly_label": [1],
                    "cost_impact_score": [0.8],
                    "is_anomaly": [True],
                    "cumulative_excess_cost": [50.0],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                    "provider": ["AWS"],
                }
            ),
            "anomaly_count": 1,
            "total_excess_cost": 50.0,
        }
        exporter = AnalysisExporter(results)
        data = exporter.to_excel()
        assert len(data) > 0
        wb = __import__("openpyxl").load_workbook(io.BytesIO(data))
        # Anomalies sheet should exist and have sanitized header
        assert "Anomalies" in wb.sheetnames
        ws = wb["Anomalies"]
        header_row = [cell.value for cell in ws[1]]
        assert "=HACK()" not in header_row
        assert "\t=HACK()" in header_row  # tab-prefixed, not a formula


# ---------------------------------------------------------------------------
# JSON edge-case tests
# ---------------------------------------------------------------------------


class TestExportJSONEdgeCases:
    """Tests for JSON serialization of tricky data types."""

    def test_numpy_bool_serialization(self):
        """np.bool_ values must serialize correctly."""
        results = {
            "source_file": "test.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "observed_cost": [100.0],
                    "expected_cost": [50.0],
                    "excess_cost": [50.0],
                    "relative_deviation": [1.0],
                    "anomaly_score": [-0.5],
                    "anomaly_label": [np.bool_(True)],
                    "cost_impact_score": [0.8],
                    "is_anomaly": [np.bool_(True)],
                    "cumulative_excess_cost": [50.0],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                    "provider": ["AWS"],
                }
            ),
            "explanations": [],
            "anomaly_count": 1,
            "total_excess_cost": 50.0,
        }
        exporter = AnalysisExporter(results)
        text = exporter.to_json()
        data = json.loads(text)  # must not raise
        assert data["ranked_results"][0]["anomaly_label"] is True


# ---------------------------------------------------------------------------
# File read error handling tests
# ---------------------------------------------------------------------------


class TestFileReadErrors:
    """Tests for handling of unreadable input files."""

    def test_unreadable_sample_file_produces_empty_bytes(self):
        """Unreadable sample file must yield empty bytes, not crash."""
        file_contents = {}
        try:
            with open("/nonexistent/path/to/file.csv", "rb") as fh:
                file_contents["/nonexistent/path/to/file.csv"] = fh.read()
        except OSError:
            file_contents["/nonexistent/path/to/file.csv"] = b""
        cfg = {"forecast_horizon": 30}
        # Must not raise
        h = compute_input_hash(file_contents, cfg)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# End-to-end synthetic end-to-end test
# ---------------------------------------------------------------------------


class TestEndToEndExport:
    """End-to-end export test simulating a full analysis run."""

    def test_full_export_from_sample_data(self):
        """Export all four formats from a complete result set."""
        results = {
            "source_file": "sample_aws_billing.csv",
            "generated_at": datetime(2024, 6, 15, 10, 30, 0),
            "config": {
                "forecast_horizon": 30,
                "interval_width": 0.95,
                "seasonality_mode": "additive",
                "weekly_seasonality": "auto",
                "yearly_seasonality": "auto",
                "contamination": 0.05,
                "n_estimators": 100,
            },
            "raw_data": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-01", "2024-06-01"]),
                    "cloud_provider": ["AWS", "AWS"],
                    "service_name": ["AmazonEC2", "AmazonS3"],
                    "account_id": ["123456789012", "123456789012"],
                    "region": ["us-east-1", "eu-west-1"],
                    "environment": ["prod", "prod"],
                    "usage_quantity": [100.0, 80.0],
                    "usage_unit": ["hours", "GB-month"],
                    "cost_usd": [150.0, 25.0],
                }
            ),
            "daily_data": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-01"]),
                    "cost_usd": [175.0],
                }
            ),
            "forecast_data": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-07-01", "2024-07-02"]),
                    "forecast_cost_usd": [520.50, 535.20],
                    "lower_bound_80": [490.10, 500.30],
                    "upper_bound_80": [550.90, 570.10],
                }
            ),
            "eval_metrics": {"mape": 0.046, "rmse": 23.66, "mae": 18.50},
            "ranked_results": pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-06-05"]),
                    "provider": ["AWS"],
                    "observed_cost": [692.08],
                    "expected_cost": [601.76],
                    "excess_cost": [90.32],
                    "relative_deviation": [0.15],
                    "anomaly_score": [-0.77],
                    "anomaly_label": [1],
                    "cost_impact_score": [1.25],
                    "is_anomaly": [True],
                    "cumulative_excess_cost": [90.32],
                    "cost_impact_rank": [1],
                    "anomaly_score_rank": [1],
                    "excess_cost_rank": [1],
                }
            ),
            "explanations": [
                {
                    "date": pd.Timestamp("2024-06-05"),
                    "provider": "AWS",
                    "cost_impact_rank": 1,
                    "explanation": "Observed cost exceeded expected.",
                    "cost_impact_score": 1.25,
                    "excess_cost": 90.32,
                    "anomaly_label": 1,
                }
            ],
            "anomaly_count": 1,
            "total_excess_cost": 90.32,
        }

        exporter = AnalysisExporter(results)

        csv_bytes = exporter.to_csv()
        assert len(csv_bytes) > 0
        assert csv_data_contains("692.08", csv_bytes)

        xlsx_bytes = exporter.to_excel()
        assert len(xlsx_bytes) > 0
        wb = __import__("openpyxl").load_workbook(io.BytesIO(xlsx_bytes))
        assert "Summary" in wb.sheetnames
        assert "Anomalies" in wb.sheetnames

        pdf_bytes = exporter.to_pdf()
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

        json_str = exporter.to_json()
        parsed = json.loads(json_str)
        assert parsed["source_file"] == "sample_aws_billing.csv"
        assert parsed["summary"]["anomaly_count"] == 1


def csv_data_contains(needle: str, data: bytes) -> bool:
    return needle in data.decode("utf-8")