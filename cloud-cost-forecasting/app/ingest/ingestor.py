import os
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, List
import logging
import uuid

from .schema import UNIFIED_SCHEMA, REQUIRED_COLUMNS

logger = logging.getLogger(__name__)

# Maximum filename length (Windows MAX_PATH is 260, but we'll be more conservative)
MAX_FILENAME_LENGTH = 200
ALLOWED_EXTENSIONS = {'.csv'}


def _sanitize_filename(name: str) -> str:
    """
    Sanitize a filename for safe filesystem usage.
    
    - Removes null bytes
    - Truncates to maximum length
    - Replaces problematic characters
    - Ensures non-empty result
    """
    if not name:
        return "uploaded_file"
    
    # Remove null bytes
    name = name.replace('\x00', '')
    
    # Get basename only (strip directory components)
    name = os.path.basename(name)
    
    # Replace problematic characters
    # Keep alphanumeric, dots, underscores, hyphens
    safe_chars = []
    for ch in name:
        if ch.isalnum() or ch in '._-':
            safe_chars.append(ch)
        else:
            safe_chars.append('_')
    
    name = ''.join(safe_chars)
    
    # Truncate if too long (preserve extension)
    if len(name) > MAX_FILENAME_LENGTH:
        base, ext = os.path.splitext(name)
        max_base = MAX_FILENAME_LENGTH - len(ext)
        if max_base > 0:
            name = base[:max_base] + ext
        else:
            name = name[:MAX_FILENAME_LENGTH]
    
    # Ensure non-empty
    if not name or name == '.':
        name = "uploaded_file"
    
    return name


def _validate_file_extension(filename: str) -> bool:
    """Validate that the file has an allowed extension."""
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def normalize_file_inputs(files, temp_dir: Union[str, None] = None) -> List[str]:
    """
    Normalize a mixed collection of file inputs into a list of filesystem
    paths suitable for ingestion.

    Accepts a mix of:

      - Streamlit ``UploadedFile`` objects (expose ``.name`` and
        ``.getbuffer()``) — these are written to a temporary directory
        so the ingestion layer can read them by path.
      - string paths
      - ``os.PathLike`` paths

    Path-like inputs are returned as-is (already point at real files).
    Uploaded-file objects are copied to ``temp_dir`` (or a freshly created
    ``tempfile.mkdtemp()``) using a sanitized basename to avoid path
    traversal and collisions.

    Args:
        files: An iterable of UploadedFile objects and/or path-like inputs.
        temp_dir: Optional directory used to stage UploadedFile contents.
            If omitted, a new temporary directory is created.

    Returns:
        A list of string filesystem paths, one per input.

    Raises:
        TypeError: If an unsupported file type is provided.
        ValueError: If a file has an unsupported extension or invalid name.
    """
    if files is None:
        return []

    files = list(files)

    # Lazily create the staging directory only when an UploadedFile is present.
    staging_dir = temp_dir
    normalized = []
    seen_paths = set()

    for f in files:
        if hasattr(f, "getbuffer"):
            # Streamlit UploadedFile (or any byte buffer exposing .name/.getbuffer)
            if staging_dir is None:
                staging_dir = tempfile.mkdtemp()
            
            # Sanitize the filename
            original_name = str(f.name)
            safe_name = _sanitize_filename(original_name)
            
            # Validate extension
            if not _validate_file_extension(safe_name):
                raise ValueError(
                    f"Unsupported file extension for '{original_name}'. "
                    f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Handle duplicate filenames by appending UUID
            dest = os.path.join(staging_dir, safe_name)
            if dest in seen_paths or os.path.exists(dest):
                base, ext = os.path.splitext(safe_name)
                unique_name = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
                dest = os.path.join(staging_dir, unique_name)
            
            seen_paths.add(dest)
            
            try:
                with open(dest, "wb") as out:
                    out.write(f.getbuffer())
            except OSError as e:
                raise ValueError(f"Failed to write uploaded file '{original_name}': {e}")
            
            normalized.append(dest)
        
        elif isinstance(f, (str, os.PathLike)):
            path_str = os.fspath(f)
            
            # Validate string paths
            if not path_str:
                raise ValueError("Empty file path provided")
            
            # Check for null bytes
            if '\x00' in path_str:
                raise ValueError("File path contains null bytes")
            
            # Convert to absolute path for consistency
            abs_path = os.path.abspath(path_str)
            
            # Check if path exists
            if not os.path.exists(abs_path):
                raise ValueError(f"File does not exist: {path_str}")
            
            # Check if it's a file (not a directory)
            if not os.path.isfile(abs_path):
                raise ValueError(f"Path is not a file: {path_str}")
            
            # Validate extension
            if not _validate_file_extension(abs_path):
                raise ValueError(
                    f"Unsupported file extension for '{path_str}'. "
                    f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Check for duplicates
            if abs_path in seen_paths:
                logger.warning(f"Duplicate file path ignored: {path_str}")
                continue
            
            seen_paths.add(abs_path)
            normalized.append(abs_path)
        
        else:
            raise TypeError(
                f"Unsupported uploaded file type: {type(f)!r}. "
                "Expected a Streamlit UploadedFile or a file path."
            )

    return normalized


class BillingIngestor:
    """Handles ingestion of cloud billing data from various sources."""
    
    def __init__(self):
        self.schema = UNIFIED_SCHEMA
        self.required_columns = REQUIRED_COLUMNS
    
    def _validate_dataframe(self, df: pd.DataFrame, source: str) -> None:
        """Validate the ingested DataFrame for data quality issues."""
        # Check required columns
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"{source}: Missing required columns after ingestion: {missing_cols}. "
                f"Available columns: {list(df.columns)}"
            )
        
        # Check for NaN in required numeric columns
        if 'cost_usd' in df.columns:
            if df['cost_usd'].isna().any():
                nan_count = df['cost_usd'].isna().sum()
                raise ValueError(
                    f"{source}: Found {nan_count} NaN values in 'cost_usd' column. "
                    f"Please check your CSV data."
                )
            if not np.isfinite(df['cost_usd']).all():
                inf_count = (~np.isfinite(df['cost_usd'])).sum()
                raise ValueError(
                    f"{source}: Found {inf_count} infinite values in 'cost_usd' column. "
                    f"Please check your CSV data."
                )
        
        if 'usage_quantity' in df.columns:
            if df['usage_quantity'].isna().any():
                nan_count = df['usage_quantity'].isna().sum()
                logger.warning(
                    f"{source}: Found {nan_count} NaN values in 'usage_quantity' column. "
                    f"These will be treated as unknown."
                )
            if not np.isfinite(df['usage_quantity']).all():
                inf_count = (~np.isfinite(df['usage_quantity'])).sum()
                logger.warning(
                    f"{source}: Found {inf_count} infinite values in 'usage_quantity' column. "
                    f"These will be treated as unknown."
                )
        
        # Check date column
        if 'date' in df.columns:
            if df['date'].isna().any():
                nan_count = df['date'].isna().sum()
                raise ValueError(
                    f"{source}: Found {nan_count} unparseable dates in 'date' column. "
                    f"Please check your CSV data."
                )
    
    def ingest_aws_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Ingest AWS Cost & Usage Report CSV."""
        logger.info(f"Ingesting AWS CSV from {file_path}")
        
        # Read CSV with error handling
        try:
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError:
            raise ValueError(f"AWS CSV file is empty: {file_path}")
        except pd.errors.ParserError as e:
            raise ValueError(f"AWS CSV parse error in {file_path}: {e}")
        
        # Map AWS CUR columns to unified schema
        column_mapping = {
            'bill/BillingPeriodStartDate': 'date',
            'lineItem/ProductCode': 'service_name',
            'lineItem/UsageAccountId': 'account_id',
            'lineItem/UsageAmount': 'usage_quantity',
            'lineItem/UnblendedCost': 'cost_usd',
            'product/region': 'region'
        }
        
        # Check for required source columns
        missing_source_cols = [col for col in column_mapping if col not in df.columns]
        if missing_source_cols:
            raise ValueError(
                f"AWS CSV missing required columns: {missing_source_cols}. "
                f"Available columns: {list(df.columns)}"
            )
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Add missing columns
        df['cloud_provider'] = 'AWS'
        df['environment'] = 'unknown'  # Would be derived from tags in real implementation
        df['usage_unit'] = 'unknown'   # Would need more detailed mapping
        
        # Select only required columns
        df = df[self.required_columns]
        
        # Enforce schema dtypes
        for col, dtype in UNIFIED_SCHEMA.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to {dtype}: {e}")
        
        # Convert date column to timezone-naive datetime (already done in loop, but we do it again to be safe)
        df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce').dt.tz_localize(None)
        
        # Validate the result
        self._validate_dataframe(df, "AWS CSV")
        
        logger.info(f"Successfully ingested {len(df)} rows from AWS CSV")
        return df
    
    def ingest_gcp_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Ingest GCP Billing Export CSV."""
        logger.info(f"Ingesting GCP CSV from {file_path}")
        
        # Read CSV with error handling
        try:
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError:
            raise ValueError(f"GCP CSV file is empty: {file_path}")
        except pd.errors.ParserError as e:
            raise ValueError(f"GCP CSV parse error in {file_path}: {e}")
        
        # Map GCP Billing Export columns to unified schema
        column_mapping = {
            'usage_start_time': 'date',
            'service.description': 'service_name',
            'project.id': 'account_id',
            'cost': 'cost_usd',
            'usage.amount': 'usage_quantity',
            'usage.unit': 'usage_unit'
        }
        
        # Check for required source columns
        missing_source_cols = [col for col in column_mapping if col not in df.columns]
        if missing_source_cols:
            raise ValueError(
                f"GCP CSV missing required columns: {missing_source_cols}. "
                f"Available columns: {list(df.columns)}"
            )
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Add missing columns
        df['cloud_provider'] = 'GCP'
        df['region'] = 'unknown'  # Would need more detailed mapping
        df['environment'] = 'unknown'  # Would be derived from labels in real implementation
        
        # Select only required columns
        df = df[self.required_columns]
        
        # Enforce schema dtypes
        for col, dtype in UNIFIED_SCHEMA.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to {dtype}: {e}")
        
        # Convert date column to timezone-naive datetime (already done in loop, but we do it again to be safe)
        df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce').dt.tz_localize(None)
        
        # Validate the result
        self._validate_dataframe(df, "GCP CSV")
        
        logger.info(f"Successfully ingested {len(df)} rows from GCP CSV")
        return df
    
    def ingest_billing_data(self, file_paths: List[Union[str, Path]]) -> pd.DataFrame:
        """Ingest billing data from multiple files."""
        logger.info(f"Ingesting billing data from {len(file_paths)} files")
        
        dfs = []
        for file_path in file_paths:
            file_path = Path(file_path)
            if 'aws' in str(file_path).lower() or 'cur' in str(file_path).lower():
                df = self.ingest_aws_csv(file_path)
            elif 'gcp' in str(file_path).lower():
                df = self.ingest_gcp_csv(file_path)
            else:
                # Try to infer from content
                df = self._infer_and_ingest(file_path)
            dfs.append(df)
        
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by date
        combined_df = combined_df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"Successfully ingested total of {len(combined_df)} rows")
        return combined_df
    
    def _infer_and_ingest(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Infer file type and ingest accordingly."""
        # Simple inference based on first few lines
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline().lower()
        except Exception as e:
            raise ValueError(f"Could not read file {file_path} for format inference: {e}")
        
        if 'bill/billingperiodstartdate' in first_line or 'lineitem/productcode' in first_line:
            return self.ingest_aws_csv(file_path)
        elif 'usage_start_time' in first_line or 'service.description' in first_line:
            return self.ingest_gcp_csv(file_path)
        else:
            # Default to AWS format
            logger.warning(f"Could not infer format for {file_path}, defaulting to AWS")
            return self.ingest_aws_csv(file_path)


def ingest_billing_data(file_paths: List[Union[str, Path]]) -> pd.DataFrame:
    """Convenience function to ingest billing data."""
    ingestor = BillingIngestor()
    return ingestor.ingest_billing_data(file_paths)