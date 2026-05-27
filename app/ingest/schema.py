# Unified billing schema
UNIFIED_SCHEMA = {
    'date': 'datetime64[ns]',
    'cloud_provider': 'string',
    'service_name': 'string',
    'account_id': 'string',
    'region': 'string',
    'environment': 'string',
    'cost_usd': 'float64',
    'usage_quantity': 'float64',
    'usage_unit': 'string'
}

# Required columns in the unified schema
REQUIRED_COLUMNS = list(UNIFIED_SCHEMA.keys())
