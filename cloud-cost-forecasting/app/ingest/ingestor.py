import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, List
import logging

from .schema import UNIFIED_SCHEMA, REQUIRED_COLUMNS

logger = logging.getLogger(__name__)

class BillingIngestor:
    """Handles ingestion of cloud billing data from various sources."""
    
    def __init__(self):
        self.schema = UNIFIED_SCHEMA
        self.required_columns = REQUIRED_COLUMNS
    
    def ingest_aws_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Ingest AWS Cost & Usage Report CSV."""
        logger.info(f"Ingesting AWS CSV from {file_path}")
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Map AWS CUR columns to unified schema
        column_mapping = {
            'bill/BillingPeriodStartDate': 'date',
            'lineItem/ProductCode': 'service_name',
            'lineItem/UsageAccountId': 'account_id',
            'lineItem/UsageAmount': 'usage_quantity',
            'lineItem/UnblendedCost': 'cost_usd',
            'product/region': 'region'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Add missing columns
        df['cloud_provider'] = 'AWS'
        df['environment'] = 'unknown'  # Would be derived from tags in real implementation
        df['usage_unit'] = 'unknown'   # Would need more detailed mapping
        
        # Select only required columns
        df = df[self.required_columns]
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"Successfully ingested {len(df)} rows from AWS CSV")
        return df
    
    def ingest_gcp_csv(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """Ingest GCP Billing Export CSV."""
        logger.info(f"Ingesting GCP CSV from {file_path}")
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Map GCP Billing Export columns to unified schema
        column_mapping = {
            'usage_start_time': 'date',
            'service.description': 'service_name',
            'project.id': 'account_id',
            'cost': 'cost_usd',
            'usage.amount': 'usage_quantity',
            'usage.unit': 'usage_unit'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Add missing columns
        df['cloud_provider'] = 'GCP'
        df['region'] = 'unknown'  # Would need more detailed mapping
        df['environment'] = 'unknown'  # Would be derived from labels in real implementation
        
        # Select only required columns
        df = df[self.required_columns]
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        
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
        with open(file_path, 'r') as f:
            first_line = f.readline().lower()
        
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