# Unified schema for cloud billing data
UNIFIED_SCHEMA = {
    'date': 'datetime64[ns]',
    'cloud_provider': 'string',
    'service_name': 'string',
    'account_id': 'string',
    'region': 'string',
    'environment': 'string',
    'usage_quantity': 'float64',
    'usage_unit': 'string',
    'cost_usd': 'float64'
}

# Required columns that must be present after ingestion
REQUIRED_COLUMNS = [
    'date',
    'cloud_provider', 
    'service_name',
    'account_id',
    'region',
    'environment',
    'usage_quantity',
    'usage_unit',
    'cost_usd'
]