# Regression tests for the file-input normalization used by the Streamlit app.

import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cloud-cost-forecasting"))

from app.ingest.ingestor import ingest_billing_data, normalize_file_inputs

try:
    import pyarrow as pa
except Exception:  # pragma: no cover
    pa = None


class MockUploadedFile:
    """Minimal stand-in for a Streamlit UploadedFile.

    Mirrors the two attributes/methods used by app.py:
      - ``.name``  (filename string)
      - ``.getbuffer()`` (byte buffer)
    """

    def __init__(self, name, content):
        self.name = name
        if isinstance(content, str):
            content = content.encode("utf-8")
        self._content = content

    def getbuffer(self):
        return self._content

    def getvalue(self):
        return self._content


AWS_CSV = (
    "bill/BillingPeriodStartDate,lineItem/ProductCode,lineItem/UsageAccountId,"
    "lineItem/UsageAmount,lineItem/UnblendedCost,product/region\n"
    "2024-01-01,AmazonEC2,123456789012,10.5,15.75,us-east-1\n"
    "2024-01-02,AmazonS3,123456789012,5.2,2.10,us-east-1\n"
)

GCP_CSV = (
    "usage_start_time,service.description,project.id,cost,usage.amount,usage.unit\n"
    "2024-01-01,Compute Engine,my-gcp-project,12.50,8.0,hours\n"
    "2024-01-02,BigQuery,my-gcp-project,18.75,5.0,slots\n"
)


class TestNormalizeFileInputs:
    def test_string_paths_returned_as_is(self):
        """String paths should pass through unchanged."""
        base_dir = os.path.join(os.path.dirname(__file__), "..", "cloud-cost-forecasting")
        aws_path = os.path.join(base_dir, "data", "samples", "sample_aws_billing.csv")
        gcp_path = os.path.join(base_dir, "data", "samples", "sample_gcp_billing.csv")
        inputs = [aws_path, gcp_path]
        result = normalize_file_inputs(inputs)
        assert result == [os.path.abspath(aws_path), os.path.abspath(gcp_path)]

    def test_pathlike_inputs_returned_as_is(self):
        """os.PathLike inputs should be converted to strings."""
        base_dir = os.path.join(os.path.dirname(__file__), "..", "cloud-cost-forecasting")
        aws_path = os.path.join(base_dir, "data", "samples", "sample_aws_billing.csv")
        gcp_path = os.path.join(base_dir, "data", "samples", "sample_gcp_billing.csv")
        result = normalize_file_inputs([aws_path, gcp_path])
        assert result == [os.path.abspath(aws_path), os.path.abspath(gcp_path)]

    def test_uploaded_file_written_to_temp(self):
        """UploadedFile objects should be staged to disk as paths."""
        f = MockUploadedFile("sample_aws_billing.csv", AWS_CSV)
        result = normalize_file_inputs([f])
        assert len(result) == 1
        assert result[0].endswith("sample_aws_billing.csv")
        # The staged file must exist and match the original content.
        with open(result[0], "rb") as fh:
            assert fh.read().decode("utf-8") == AWS_CSV

    def test_mixed_inputs(self):
        """A mixed list of UploadedFile and string paths is handled."""
        f = MockUploadedFile("sample_aws_billing.csv", AWS_CSV)
        base_dir = os.path.join(os.path.dirname(__file__), "..", "cloud-cost-forecasting")
        path = os.path.join(base_dir, "data", "samples", "sample_gcp_billing.csv")
        result = normalize_file_inputs([f, path])
        assert len(result) == 2
        # UploadedFile staged first (has basename), string path kept as-is
        assert result[0].endswith("sample_aws_billing.csv")
        assert result[1] == os.path.abspath(path)

    def test_filename_sanitization(self):
        """Directory components in a filename are stripped (no traversal)."""
        f = MockUploadedFile("../evil/sample_aws_billing.csv", AWS_CSV)
        result = normalize_file_inputs([f])
        assert len(result) == 1
        # basename only, no "../" traversal
        assert ".." not in os.path.basename(result[0])
        assert result[0].endswith("sample_aws_billing.csv")

    def test_empty_input(self):
        """None or empty list yields an empty list."""
        assert normalize_file_inputs(None) == []
        assert normalize_file_inputs([]) == []

    def test_unsupported_type_raises(self):
        """An unsupported input type raises a clear TypeError."""
        with pytest.raises(TypeError):
            normalize_file_inputs([12345])


class TestSampleDataEndToEnd:
    """Verify the actual sample CSV files ingest correctly via normalization."""

    def _sample_path(self, name):
        base_dir = os.path.join(os.path.dirname(__file__), "..", "cloud-cost-forecasting")
        return os.path.join(base_dir, "data", "samples", name)

    def test_aws_sample_data_path(self):
        """String path to real AWS sample data ingests to AWS rows."""
        aws_path = self._sample_path("sample_aws_billing.csv")
        paths = normalize_file_inputs([aws_path])
        df = ingest_billing_data(paths)
        assert len(df) == 360
        assert (df["cloud_provider"] == "AWS").all()

    def test_gcp_sample_data_path(self):
        """String path to real GCP sample data ingests to GCP rows."""
        gcp_path = self._sample_path("sample_gcp_billing.csv")
        paths = normalize_file_inputs([gcp_path])
        df = ingest_billing_data(paths)
        assert len(df) == 360
        assert (df["cloud_provider"] == "GCP").all()

    def test_aws_sample_data_uploadedfile(self):
        """UploadedFile-like AWS sample content ingests correctly."""
        aws_path = self._sample_path("sample_aws_billing.csv")
        with open(aws_path, "rb") as fh:
            content = fh.read()
        f = MockUploadedFile("sample_aws_billing.csv", content)
        paths = normalize_file_inputs([f])
        df = ingest_billing_data(paths)
        assert len(df) == 360
        assert (df["cloud_provider"] == "AWS").all()

    def test_gcp_sample_data_uploadedfile(self):
        """UploadedFile-like GCP sample content ingests correctly."""
        gcp_path = self._sample_path("sample_gcp_billing.csv")
        with open(gcp_path, "rb") as fh:
            content = fh.read()
        f = MockUploadedFile("sample_gcp_billing.csv", content)
        paths = normalize_file_inputs([f])
        df = ingest_billing_data(paths)
        assert len(df) == 360
        assert (df["cloud_provider"] == "GCP").all()

    def test_combined_sample_data_strings(self):
        """Both sample data files (strings) ingest together to 720 rows."""
        aws_path = self._sample_path("sample_aws_billing.csv")
        gcp_path = self._sample_path("sample_gcp_billing.csv")
        paths = normalize_file_inputs([aws_path, gcp_path])
        df = ingest_billing_data(paths)
        assert len(df) == 720
        assert df["cloud_provider"].nunique() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])