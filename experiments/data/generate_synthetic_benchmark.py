#!/usr/bin/env python3
"""
Synthetic Cloud Billing Benchmark Generator

Generates realistic multi-cloud billing data for experimental validation.
This is SYNTHETIC BENCHMARK DATA - NOT real AWS/GCP billing data.

Characteristics:
- 180 days of daily data
- AWS and GCP providers
- Multiple services per provider
- Realistic trends, weekly seasonality, noise
- Controlled anomalies with ground truth labels
- Deterministic and reproducible (fixed seed)

Output:
- synthetic_benchmark.csv: Daily aggregated cost data
- synthetic_benchmark_detailed.csv: Service-level detail
- ground_truth_anomalies.csv: Anomaly metadata for evaluation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# Fixed seed for reproducibility
SEED = 42
np.random.seed(SEED)

# Configuration
N_DAYS = 180
START_DATE = datetime(2024, 1, 1)
FORECAST_HORIZON = 14

# Provider configurations
PROVIDERS = {
    'AWS': {
        'services': {
            'AmazonEC2': {'base_cost': 150, 'trend': 0.5, 'seasonal_amp': 30, 'noise_std': 15},
            'AmazonS3': {'base_cost': 40, 'trend': 0.2, 'seasonal_amp': 8, 'noise_std': 5},
            'AmazonRDS': {'base_cost': 80, 'trend': 0.3, 'seasonal_amp': 15, 'noise_std': 10},
            'AmazonCloudFront': {'base_cost': 25, 'trend': 0.1, 'seasonal_amp': 5, 'noise_std': 3},
            'AmazonDynamoDB': {'base_cost': 35, 'trend': 0.15, 'seasonal_amp': 7, 'noise_std': 5},
        }
    },
    'GCP': {
        'services': {
            'Compute Engine': {'base_cost': 120, 'trend': 0.4, 'seasonal_amp': 25, 'noise_std': 12},
            'Cloud Storage': {'base_cost': 30, 'trend': 0.15, 'seasonal_amp': 6, 'noise_std': 4},
            'BigQuery': {'base_cost': 60, 'trend': 0.25, 'seasonal_amp': 12, 'noise_std': 8},
            'Cloud SQL': {'base_cost': 45, 'trend': 0.2, 'seasonal_amp': 9, 'noise_std': 6},
            'Cloud Run': {'base_cost': 20, 'trend': 0.1, 'seasonal_amp': 4, 'noise_std': 3},
        }
    }
}

# Anomaly configurations
ANOMALY_CONFIG = [
    # (day_offset, provider, service, anomaly_type, magnitude_multiplier, duration_days)
    (25, 'AWS', 'AmazonEC2', 'sudden_spike', 3.0, 1),
    (45, 'GCP', 'Compute Engine', 'sustained_increase', 2.0, 7),
    (65, 'AWS', 'AmazonRDS', 'temporary_surge', 2.5, 3),
    (85, 'GCP', 'BigQuery', 'gradual_drift', 1.5, 14),
    (110, 'AWS', 'AmazonS3', 'sudden_spike', 4.0, 1),
    (135, 'GCP', 'Cloud Storage', 'sustained_increase', 1.8, 10),
    (155, 'AWS', 'AmazonCloudFront', 'temporary_surge', 3.0, 2),
]


def generate_daily_costs():
    """Generate daily cost data for all providers and services."""
    dates = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]
    
    all_records = []
    anomaly_records = []
    
    # Create anomaly lookup for quick access
    anomaly_lookup = {}
    for day_offset, provider, service, a_type, magnitude, duration in ANOMALY_CONFIG:
        for d in range(duration):
            day = day_offset + d
            if 0 <= day < N_DAYS:
                key = (day, provider, service)
                if key not in anomaly_lookup:
                    anomaly_lookup[key] = []
                anomaly_lookup[key].append({
                    'type': a_type,
                    'magnitude': magnitude,
                    'day_in_anomaly': d,
                    'total_duration': duration
                })
    
    for day_idx, date in enumerate(dates):
        day_of_week = date.weekday()  # 0=Monday
        is_weekend = day_of_week >= 5
        
        for provider, config in PROVIDERS.items():
            for service, params in config['services'].items():
                # Base cost with trend
                trend = params['trend'] * day_idx
                base = params['base_cost'] + trend
                
                # Weekly seasonality (lower on weekends for cloud)
                seasonal = params['seasonal_amp'] * np.sin(2 * np.pi * day_idx / 7)
                if is_weekend:
                    seasonal *= 0.7  # Reduced weekend usage
                
                # Noise
                noise = np.random.normal(0, params['noise_std'])
                
                # Base cost
                cost = max(base + seasonal + noise, 1.0)
                
                # Apply anomalies
                anomaly_info = anomaly_lookup.get((day_idx, provider, service), [])
                is_anomaly = len(anomaly_info) > 0
                anomaly_type = None
                anomaly_magnitude = 1.0
                
                if is_anomaly:
                    # Use the first anomaly (should only be one per day/service)
                    a = anomaly_info[0]
                    anomaly_type = a['type']
                    anomaly_magnitude = a['magnitude']
                    cost *= anomaly_magnitude
                    
                    # Record anomaly details
                    anomaly_records.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'provider': provider,
                        'service': service,
                        'anomaly_type': anomaly_type,
                        'magnitude_multiplier': anomaly_magnitude,
                        'duration_days': a['total_duration'],
                        'day_in_anomaly': a['day_in_anomaly'],
                        'base_cost': base + seasonal + noise,
                        'anomalous_cost': cost,
                        'cost_increase_pct': (anomaly_magnitude - 1) * 100
                    })
                
                # Usage quantity (simulated)
                usage_qty = cost / np.random.uniform(0.8, 1.2)
                
                all_records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'provider': provider,
                    'service': service,
                    'cost_usd': round(cost, 2),
                    'usage_quantity': round(usage_qty, 2),
                    'usage_unit': 'units',
                    'is_anomaly': is_anomaly,
                    'anomaly_type': anomaly_type if anomaly_type else '',
                    'anomaly_magnitude': anomaly_magnitude if is_anomaly else 1.0
                })
    
    df = pd.DataFrame(all_records)
    anomaly_df = pd.DataFrame(anomaly_records)
    
    return df, anomaly_df


def create_daily_aggregated(df):
    """Create daily aggregated cost per provider."""
    daily = df.groupby(['date', 'provider'])['cost_usd'].sum().reset_index()
    daily = daily.rename(columns={'cost_usd': 'daily_cost_usd'})
    daily = daily.sort_values(['provider', 'date']).reset_index(drop=True)
    return daily


def create_provider_aggregated(df):
    """Create daily aggregated cost across all providers."""
    daily = df.groupby('date')['cost_usd'].sum().reset_index()
    daily = daily.rename(columns={'cost_usd': 'total_daily_cost_usd'})
    daily = daily.sort_values('date').reset_index(drop=True)
    return daily


def save_datasets():
    """Generate and save all benchmark datasets."""
    print("Generating synthetic benchmark data...")
    
    # Generate detailed service-level data
    detailed_df, anomaly_df = generate_daily_costs()
    
    # Create aggregated versions
    daily_provider = create_daily_aggregated(detailed_df)
    daily_total = create_provider_aggregated(detailed_df)
    
    # Save files
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Main benchmark (provider-level daily)
    benchmark_path = os.path.join(output_dir, 'synthetic_benchmark.csv')
    daily_provider.to_csv(benchmark_path, index=False)
    print(f"Saved: {benchmark_path} ({len(daily_provider)} rows)")
    
    # Detailed service-level
    detailed_path = os.path.join(output_dir, 'synthetic_benchmark_detailed.csv')
    detailed_df.to_csv(detailed_path, index=False)
    print(f"Saved: {detailed_path} ({len(detailed_df)} rows)")
    
    # Total daily
    total_path = os.path.join(output_dir, 'synthetic_benchmark_total.csv')
    daily_total.to_csv(total_path, index=False)
    print(f"Saved: {total_path} ({len(daily_total)} rows)")
    
    # Ground truth anomalies
    anomaly_path = os.path.join(output_dir, 'ground_truth_anomalies.csv')
    anomaly_df.to_csv(anomaly_path, index=False)
    print(f"Saved: {anomaly_path} ({len(anomaly_df)} anomaly records)")
    
    # Metadata
    metadata = {
        'generation_date': datetime.now().isoformat(),
        'seed': SEED,
        'n_days': N_DAYS,
        'start_date': START_DATE.strftime('%Y-%m-%d'),
        'end_date': (START_DATE + timedelta(days=N_DAYS-1)).strftime('%Y-%m-%d'),
        'providers': list(PROVIDERS.keys()),
        'services_per_provider': {p: list(c['services'].keys()) for p, c in PROVIDERS.items()},
        'anomaly_config': [
            {
                'day_offset': a[0],
                'provider': a[1],
                'service': a[2],
                'type': a[3],
                'magnitude': a[4],
                'duration': a[5]
            } for a in ANOMALY_CONFIG
        ],
        'total_anomaly_days': len(anomaly_df),
        'data_type': 'SYNTHETIC_BENCHMARK',
        'description': 'Realistic synthetic cloud billing data for experimental validation. NOT real AWS/GCP data.'
    }
    
    metadata_path = os.path.join(output_dir, 'benchmark_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved: {metadata_path}")
    
    # Print summary
    print("\n--- Dataset Summary ---")
    print(f"Total days: {N_DAYS}")
    print(f"Date range: {metadata['start_date']} to {metadata['end_date']}")
    print(f"Providers: {metadata['providers']}")
    print(f"Services: {metadata['services_per_provider']}")
    print(f"Total detailed rows: {len(detailed_df)}")
    print(f"Total provider-daily rows: {len(daily_provider)}")
    print(f"Anomaly records: {len(anomaly_df)}")
    print(f"Unique anomaly events: {len(ANOMALY_CONFIG)}")
    
    return detailed_df, daily_provider, daily_total, anomaly_df


if __name__ == '__main__':
    save_datasets()