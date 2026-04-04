# tests/fixtures/sample_data.py
"""Shared test datasets for integration tests."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_transaction_data():
    """Realistic transaction data for testing"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
    
    return pd.DataFrame({
        'date': dates,
        'customer': np.random.choice(['Acme Corp', 'Beta Inc', 'Gamma LLC', 'Delta Ltd'], len(dates)),
        'product': np.random.choice(['Widget Pro', 'Widget Basic', 'Widget Enterprise', 'Gadget'], len(dates)),
        'region': np.random.choice(['North America', 'Europe', 'Asia', 'South America'], len(dates)),
        'revenue': np.random.randint(500, 5000, len(dates)),
        'cost': np.random.randint(200, 3000, len(dates)),
        'quantity': np.random.randint(1, 20, len(dates)),
        'payment_status': np.random.choice(['paid', 'pending', 'overdue'], len(dates))
    })


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-03-31', freq='D')
    np.random.seed(42)
    
    data = []
    customers = ['Customer A', 'Customer B', 'Customer C']
    products = ['Product X', 'Product Y', 'Product Z']
    regions = ['North', 'South', 'East', 'West']
    payment_statuses = ['paid', 'pending', 'overdue']
    
    for i, date in enumerate(dates):
        data.append({
            'date': date,
            'customer': customers[i % 3],
            'product': products[i % 3],
            'region': regions[i % 4],
            'revenue': 100 + (i % 10) * 10,
            'cost': 50 + (i % 8) * 5,
            'quantity': 1 + (i % 5),
            'payment_status': payment_statuses[i % 3]
        })
    
    # Add anomalies
    data[15]['revenue'] = 1000
    data[45]['revenue'] = 1500
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_dataframe_long():
    """Create a longer sample dataframe for forecasting (15+ months)"""
    dates = pd.date_range(start='2023-01-01', end='2024-03-31', freq='D')
    np.random.seed(42)
    
    data = []
    for i, date in enumerate(dates):
        # Add some seasonality
        seasonal = 100 * np.sin(2 * np.pi * i / 30) + 200
        trend = i * 0.5
        revenue = max(50, seasonal + trend + np.random.normal(0, 20))
        
        data.append({
            'date': date,
            'customer': f'Customer {i % 3}',
            'product': f'Product {i % 3}',
            'region': f'Region {i % 4}',
            'revenue': revenue,
            'cost': revenue * 0.6,
            'quantity': i % 5 + 1,
            'payment_status': 'paid' if i % 3 != 0 else 'pending'
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def minimal_dataframe():
    """Create a minimal dataframe"""
    return pd.DataFrame({
        'date': ['2024-01-01', '2024-01-02'],
        'revenue': [100, 200],
        'cost': [50, 100],
        'customer': ['A', 'A'],
        'product': ['X', 'X'],
        'region': ['North', 'North'],
        'quantity': [1, 2],
        'payment_status': ['paid', 'paid']
    })


@pytest.fixture
def sample_dataframe_with_costs():
    """DataFrame with revenue and costs for profit calculations"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'revenue': [100, 200, 150, 300, 250, 175, 225, 275, 125, 195],
        'cost': [50, 100, 75, 150, 125, 87, 112, 137, 62, 97],
        'customer': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'product': ['X', 'Y', 'X', 'Z', 'Y', 'X', 'Z', 'Y', 'X', 'Z'],
        'region': ['North', 'South', 'East', 'West', 'North', 'South', 'East', 'West', 'North', 'South'],
        'quantity': [1, 2, 1, 3, 2, 1, 3, 2, 1, 2],
        'payment_status': ['paid', 'paid', 'pending', 'paid', 'paid', 'pending', 'paid', 'paid', 'failed', 'paid']
    })


@pytest.fixture
def varied_data():
    """Data with various types to test format compatibility"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'revenue': [100.50, 200.75, 150.25, 300.00, 250.50, 175.25, 225.75, 275.00, 125.50, 195.25],
        'cost': [50.25, 100.50, 75.25, 150.00, 125.25, 87.50, 112.75, 137.50, 62.75, 97.50],
        'customer': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'product': ['X', 'Y', 'X', 'Z', 'Y', 'X', 'Z', 'Y', 'X', 'Z'],
        'region': ['North', 'South', 'East', 'West', 'North', 'South', 'East', 'West', 'North', 'South'],
        'quantity': [1, 2, 1, 3, 2, 1, 3, 2, 1, 2],
        'payment_status': ['paid', 'paid', 'pending', 'paid', 'paid', 'pending', 'paid', 'paid', 'failed', 'paid']
    })


@pytest.fixture
def sample_business_data():
    """Sample business data for insight agent testing"""
    return {
        "compute_kpis": {
            "total_revenue": 150000.0,
            "total_cost": 85000.0,
            "total_profit": 65000.0,
            "profit_margin": 0.43,
            "avg_order_value": 1250.0,
            "total_transactions": 120,
            "total_customers": 45
        },
        "monthly_revenue": {
            "2024-01": 45000,
            "2024-02": 52000,
            "2024-03": 53000
        },
        "monthly_profit": {
            "2024-01": 20000,
            "2024-02": 25000,
            "2024-03": 28000
        },
        "monthly_growth": {
            "2024-01": 0,
            "2024-02": 0.15,
            "2024-03": 0.02
        },
        "revenue_by_customer": {
            "Acme Corp": 75000,
            "Beta Inc": 45000,
            "Gamma LLC": 30000
        },
        "revenue_by_product": {
            "Enterprise Plan": 214265.0,
            "Premium Plan": 64793.0,
            "Basic Plan": 28913.0
        },
        "revenue_by_region": {
            "North America": 150000,
            "Europe": 80000,
            "Asia": 50000
        },
        "detect_revenue_spikes": {
            "2024-02-15": 15000,
            "2024-03-01": 18000
        },
        "revenue_by_payment_status": {
            "paid": 250000,
            "pending": 25000,
            "failed": 5000
        }
    }


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data for testing forecast methods"""
    return {
        "forecast_revenue_by_product": {
            "forecasts": {
                "Product A": {
                    "forecast_sum": 45000,
                    "forecast": [15000, 15000, 15000],
                    "forecast_months": ["January 2025", "February 2025", "March 2025"],
                    "method": "ARIMA",
                    "historical_avg": 12000,
                    "latest_monthly": 14000
                },
                "Product B": {
                    "forecast_sum": 30000,
                    "forecast": [10000, 10000, 10000],
                    "forecast_months": ["January 2025", "February 2025", "March 2025"],
                    "method": "Moving Average",
                    "historical_avg": 8000,
                    "latest_monthly": 9000
                }
            },
            "period": "Q1 2025",
            "top_product": "Product A",
            "top_product_forecast": 45000
        }
    }


@pytest.fixture
def bad_data():
    """Problematic data to test error handling"""
    return pd.DataFrame({
        'date': ['2024-01-01', 'invalid-date', None, '2024-01-04'],
        'revenue': [100, -500, None, 'invalid'],
        'cost': [50, None, 'invalid', 75],
        'customer': ['A', '', None, 'D'],
        'product': ['X', 'Y', None, 'Z'],
        'region': ['North', 'South', None, 'East'],
        'quantity': [1, -5, None, 3],
        'payment_status': ['paid', 'unknown', None, 'paid']
    })


@pytest.fixture
def empty_dataframe():
    """Empty dataframe"""
    return pd.DataFrame()


@pytest.fixture
def missing_columns_data():
    """Data with missing required columns"""
    return pd.DataFrame({
        'some_column': [1, 2, 3],
        'another_column': ['x', 'y', 'z'],
        'extra_column': [True, False, True]
    })


@pytest.fixture
def single_row_data():
    """Data with only one row (edge case)"""
    return pd.DataFrame({
        'date': ['2024-01-01'],
        'revenue': [1000],
        'cost': [400],
        'customer': ['A'],
        'product': ['X'],
        'region': ['North'],
        'quantity': [5],
        'payment_status': ['paid']
    })


@pytest.fixture
def multi_currency_data():
    """Data with multiple currencies for conversion testing"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'revenue': [100, 200, 150, 300, 250, 175, 225, 275, 125, 195],
        'currency': ['USD', 'EUR', 'USD', 'GBP', 'USD', 'EUR', 'GBP', 'USD', 'EUR', 'USD'],
        'customer': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'product': ['X', 'Y', 'X', 'Z', 'Y', 'X', 'Z', 'Y', 'X', 'Z']
    })


@pytest.fixture
def sample_data_with_anomalies():
    """Transaction data with known anomalies for detection testing"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='D')
    
    data = []
    for i, date in enumerate(dates):
        base_revenue = 1000 + (i * 2)
        revenue = base_revenue + np.random.normal(0, 100)
        
        # Add anomalies
        if i == 15:
            revenue = 5000
        elif i == 30:
            revenue = 200
        elif i == 45:
            revenue = 4500
        
        data.append({
            'date': date,
            'customer': f'Customer_{i % 5}',
            'product': f'Product_{i % 3}',
            'region': f'Region_{i % 4}',
            'revenue': revenue,
            'cost': revenue * 0.6,
            'quantity': np.random.randint(1, 10),
            'payment_status': np.random.choice(['paid', 'pending', 'failed'], p=[0.7, 0.2, 0.1])
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def long_time_series_data():
    """Long time series data (24+ months) for seasonality detection"""
    dates = pd.date_range('2022-01-01', '2024-12-31', freq='D')
    np.random.seed(42)
    
    data = []
    for i, date in enumerate(dates):
        month = date.month
        seasonal_factor = {
            1: 0.8, 2: 0.85, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.2,
            7: 1.25, 8: 1.2, 9: 1.1, 10: 1.0, 11: 0.9, 12: 0.85
        }.get(month, 1.0)
        
        revenue = 10000 * seasonal_factor + np.random.normal(0, 500)
        
        data.append({
            'date': date,
            'customer': f'Customer_{i % 5}',
            'product': f'Product_{i % 3}',
            'region': f'Region_{i % 4}',
            'revenue': revenue,
            'cost': revenue * 0.6,
            'quantity': np.random.randint(1, 20),
            'payment_status': np.random.choice(['paid', 'pending'], p=[0.9, 0.1])
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def temp_chart_dir():
    """Temporary directory for chart output"""
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def create_custom_dataframe(
    rows: int = 100,
    start_date: str = "2024-01-01",
    include_anomalies: bool = False,
    anomaly_indices: list = None,
    seed: int = 42
) -> pd.DataFrame:
    """
    Create a custom dataframe for testing.
    
    Args:
        rows: Number of rows to generate
        start_date: Start date for time series
        include_anomalies: Whether to include anomalies
        anomaly_indices: Specific indices to place anomalies
        seed: Random seed for reproducibility
    
    Returns:
        Generated DataFrame
    """
    np.random.seed(seed)
    dates = pd.date_range(start=start_date, periods=rows, freq='D')
    
    base_revenue = 1000 + np.arange(rows) * 2
    revenue = base_revenue + np.random.normal(0, 100, rows)
    
    if include_anomalies and anomaly_indices:
        for idx in anomaly_indices:
            if 0 <= idx < rows:
                revenue[idx] *= 3
    
    return pd.DataFrame({
        'date': dates,
        'revenue': revenue,
        'cost': revenue * 0.6,
        'customer': [f'Customer_{i % 5}' for i in range(rows)],
        'product': [f'Product_{i % 3}' for i in range(rows)],
        'region': [f'Region_{i % 4}' for i in range(rows)],
        'quantity': np.random.randint(1, 20, rows),
        'payment_status': np.random.choice(['paid', 'pending', 'failed'], rows, p=[0.8, 0.15, 0.05])
    })


__all__ = [
    'sample_transaction_data',
    'sample_dataframe',
    'sample_dataframe_long',
    'minimal_dataframe',
    'sample_dataframe_with_costs',
    'varied_data',
    'sample_business_data',
    'sample_forecast_data',
    'bad_data',
    'empty_dataframe',
    'missing_columns_data',
    'single_row_data',
    'multi_currency_data',
    'sample_data_with_anomalies',
    'long_time_series_data',
    'temp_chart_dir',
    'create_custom_dataframe'
]