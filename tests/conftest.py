import pytest
import pandas as pd

import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture
def dummy_df():
    data = [
        ["2024-01-03", "Acme Corp", "Premium Plan", "US", 1299.99, 723.45, "USD", 2, "paid", ""],
        ["2024-01-05", "BetaCo", "Basic Plan", "EU", 849.5, 412.3, "EUR", 3, "paid", "First time customer"],
        ["2024-01-08", "Delta Inc", "Enterprise Plan", "APAC", 5999, 2850, "USD", 1, "paid", "Annual contract"],
        ["2024-01-18", "Zeta Corp", "Premium Plan", "US", 1399.99, 823.45, "USD", 2, "paid", ""],
    ]
    columns = ["date", "customer", "product", "region", "revenue", "cost",
               "currency", "quantity", "payment_status", "notes"]
    df = pd.DataFrame(data, columns=columns)
    df["date"] = pd.to_datetime(df["date"])
    return df