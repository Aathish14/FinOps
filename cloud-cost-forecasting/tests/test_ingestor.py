"""
PyTest suite for the Cloud Cost Forecasting ingestion layer.

Covers:
  - Mocked Streamlit UploadedFile normalization (has .getbuffer / .name)
  - Plain str and os.PathLike filesystem path normalization
  - Invalid/malformed input rejection (None, int, non-existent paths, bad extensions)
  - Real sample CSV ingestion (AWS + GCP) into standardized DataFrames

All tests run offline with no external API dependencies.
"""

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Ensure the repository root is on sys.path so `app.ingest.ingestor` is importable
# from the tests/ directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.ingest.ingestor import ingest_billing_data, normalize_file_inputs
from app.ingest.schema import REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_aws_path() -> str:
    """Absolute path to the sample AWS billing CSV."""
    return os.path.join(REPO_ROOT, "data", "samples", "sample_aws_billing.csv")


@pytest.fixture
def sample_gcp_path() -> str:
    """Absolute path to the sample GCP billing CSV."""
    return os.path.join(REPO_ROOT, "data", "samples", "sample_gcp_billing.csv")


@pytest.fixture
def mock_uploaded_file() -> MagicMock:
    """
    Mock a Streamlit UploadedFile.

    Exposes .name (str) and .getbuffer() (bytes) so normalize_file_inputs()
    recognizes it as an UploadedFile-like object.
    """
    mock = MagicMock()
    mock.name = "test_billing.csv"
    mock.getbuffer.return_value = b"bill/BillingPeriodStartDate,lineItem/ProductCode\n2024-01-01,AmazonEC2,1,100.00,us-east-1\n"
    return mock


# ---------------------------------------------------------------------------
# normalize_file_inputs() tests
# ---------------------------------------------------------------------------


class TestNormalizeFileInputs:
    """Type validation and filtering for normalize_file_inputs()."""

    def test_none_input_returns_empty_list(self):
        """None input returns an empty list instead of raising AttributeError."""
        result = normalize_file_inputs(None)
        assert result == []

    def test_empty_list_returns_empty_list(self):
        """Empty input list returns an empty list."""
        assert normalize_file_inputs([]) == []

    def test_uploaded_file_normalization(self, mock_uploaded_file):
        """
        UploadedFile-like objects with .getbuffer() pass type validation
        and are written to a temp staging path.
        """
        result = normalize_file_inputs([mock_uploaded_file])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], str)
        assert os.path.isfile(result[0])
        assert result[0].lower().endswith(".csv")

    def test_string_path_normalization(self, sample_aws_path):
        """Plain str file paths pass type validation and are returned as absolute paths."""
        result = normalize_file_inputs([sample_aws_path])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == os.path.abspath(sample_aws_path)

    def test_pathlike_normalization(self, sample_aws_path):
        """os.PathLike objects pass type validation."""
        result = normalize_file_inputs([Path(sample_aws_path)])
        assert isinstance(result, list)
        assert len(result) == 1
        assert os.path.abspath(result[0]) == os.path.abspath(sample_aws_path)

    def test_mixed_uploaded_and_string_inputs(self, mock_uploaded_file, sample_aws_path):
        """Mixed UploadedFile and str inputs are both normalized to filesystem paths."""
        result = normalize_file_inputs([mock_uploaded_file, sample_aws_path])
        assert len(result) == 2
        assert all(isinstance(r, str) for r in result)

    def test_invalid_type_raises_typeerror(self):
        """Objects lacking .getbuffer() and not str/PathLike raise TypeError."""
        with pytest.raises(TypeError):
            normalize_file_inputs([12345])

    def test_nonexistent_path_raises_valueerror(self):
        """Non-existent file paths raise ValueError."""
        with pytest.raises(ValueError):
            normalize_file_inputs(["/nonexistent/path/to/file.csv"])

    def test_unsupported_extension_raises_valueerror(self):
        """Files with unsupported extensions raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not a csv file")
            tmp_path = tmp.name
        try:
            with pytest.raises(ValueError):
                normalize_file_inputs([tmp_path])
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Sample data ingestion tests
# ---------------------------------------------------------------------------


class TestSampleDataIngestion:
    """End-to-end ingestion of real sample CSV files."""

    def test_sample_aws_csv_ingestion(self, sample_aws_path):
        """AWS sample CSV ingests into a DataFrame containing all required schema columns."""
        df = ingest_billing_data([sample_aws_path])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing required column: {col}"
        assert df["cloud_provider"].iloc[0] == "AWS"

    def test_sample_gcp_csv_ingestion(self, sample_gcp_path):
        """GCP sample CSV ingests into a DataFrame containing all required schema columns."""
        df = ingest_billing_data([sample_gcp_path])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing required column: {col}"
        assert df["cloud_provider"].iloc[0] == "GCP"

    def test_both_sample_files_ingestion(self, sample_aws_path, sample_gcp_path):
        """Both sample files can be ingested together into a combined DataFrame."""
        df = ingest_billing_data([sample_aws_path, sample_gcp_path])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing required column: {col}"
        assert df["cloud_provider"].nunique() == 2
