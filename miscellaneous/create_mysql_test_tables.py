"""
Create test tables in MySQL for schema validation testing.
Run this script to populate your test-mysql container with various test tables.
"""

from sqlalchemy import create_engine, text, inspect
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# MySQL connection (using pymysql driver)
conn_string = "mysql+pymysql://root:testpass@localhost:3307/testdb"
engine = create_engine(conn_string)

print("🚀 Creating test tables in MySQL...")

# ==================== 01_valid_data ====================
print("\n📊 Creating 01_valid_data...")
valid_data = pd.DataFrame({
    'date': [
        '2024-01-03', '2024-01-05', '2024-01-08', '2024-01-12', '2024-01-15',
        '2024-01-18', '2024-01-20', '2024-01-22'
    ],
    'customer': [
        'Acme Corp', 'BetaCo', 'Delta Inc', 'Gamma LLC', 'Acme Corp',
        'Zeta Corp', 'BetaCo', None
    ],
    'product': [
        'Premium Plan', 'Basic Plan', 'Enterprise Plan', 'Premium Plan', 'Basic Plan',
        'Premium Plan', 'Enterprise Plan', 'Basic Plan'
    ],
    'region': ['US', 'EU', 'APAC', 'US', 'US', 'US', 'EU', 'LATAM'],
    'revenue': [1299.99, 849.5, 5999, 1349.99, 949.99, 1399.99, 5499, 459.5],
    'cost': [723.45, 412.3, 2850, 789.5, 502.3, 823.45, 2675, 289.3],
    'currency': ['USD', 'EUR', 'USD', 'USD', 'USD', 'USD', 'EUR', 'USD'],
    'quantity': [2, 3, 1, 2, 3, 2, 1, 2],
    'payment_status': ['paid', 'paid', 'paid', 'paid', 'pending', 'paid', 'paid', 'failed'],
    'notes': [None, 'First time customer', 'Annual contract', None, None, None, 'Quarterly payment', 'Missing customer']
})
valid_data.to_sql('01_valid_data', engine, if_exists='replace', index=False)
print(f"✅ Created with {len(valid_data)} rows")

# ==================== 02_missing_date ====================
print("\n📊 Creating 02_missing_date (missing date column)...")
missing_date = valid_data.copy()
missing_date = missing_date.drop(columns=['date'])
missing_date.to_sql('02_missing_date', engine, if_exists='replace', index=False)
print(f"✅ Created with columns: {list(missing_date.columns)}")

# ==================== 03_missing_revenue ====================
print("\n📊 Creating 03_missing_revenue (missing revenue column)...")
missing_revenue = valid_data.copy()
missing_revenue = missing_revenue.drop(columns=['revenue'])
missing_revenue.to_sql('03_missing_revenue', engine, if_exists='replace', index=False)
print(f"✅ Created with columns: {list(missing_revenue.columns)}")

# ==================== 04_invalid_dates ====================
print("\n📊 Creating 04_invalid_dates (invalid date formats)...")
invalid_dates = pd.DataFrame({
    'date': [
        'not a date', '2024/13/45', 'Jan-2024', '2024.01.99',
        '2024-01-15', '2024-01-18', '2024-01-20', '2024-01-22'
    ],
    'customer': valid_data['customer'].tolist(),
    'product': valid_data['product'].tolist(),
    'region': valid_data['region'].tolist(),
    'revenue': valid_data['revenue'].tolist(),
    'cost': valid_data['cost'].tolist(),
    'currency': valid_data['currency'].tolist(),
    'quantity': valid_data['quantity'].tolist(),
    'payment_status': valid_data['payment_status'].tolist(),
    'notes': valid_data['notes'].tolist()
})
invalid_dates.to_sql('04_invalid_dates', engine, if_exists='replace', index=False)
print(f"✅ Created with {len(invalid_dates)} rows")

# ==================== 05_non_numeric_revenue ====================
print("\n📊 Creating 05_non_numeric_revenue (non-numeric revenue)...")
non_numeric_revenue = pd.DataFrame({
    'date': valid_data['date'].tolist(),
    'customer': valid_data['customer'].tolist(),
    'product': valid_data['product'].tolist(),
    'region': valid_data['region'].tolist(),
    'revenue': [
        'one thousand', '$849.50', '5,999', 'N/A',
        '949.99', '1399.99', '5,499', 'four fifty nine'
    ],
    'cost': valid_data['cost'].tolist(),
    'currency': valid_data['currency'].tolist(),
    'quantity': valid_data['quantity'].tolist(),
    'payment_status': valid_data['payment_status'].tolist(),
    'notes': valid_data['notes'].tolist()
})
# Ensure revenue column is object type to allow strings
non_numeric_revenue = non_numeric_revenue.astype({'revenue': 'object'})
non_numeric_revenue.to_sql('05_non_numeric_revenue', engine, if_exists='replace', index=False)
print(f"✅ Created with {len(non_numeric_revenue)} rows")

# ==================== 06_case_insensitive ====================
print("\n📊 Creating 06_case_insensitive (uppercase DATE and REVENUE)...")
case_insensitive = pd.DataFrame({
    'DATE': valid_data['date'].tolist(),
    'CUSTOMER': valid_data['customer'].tolist(),
    'PRODUCT': valid_data['product'].tolist(),
    'REGION': valid_data['region'].tolist(),
    'REVENUE': valid_data['revenue'].tolist(),
    'COST': valid_data['cost'].tolist(),
    'CURRENCY': valid_data['currency'].tolist(),
    'QUANTITY': valid_data['quantity'].tolist(),
    'PAYMENT_STATUS': valid_data['payment_status'].tolist(),
    'NOTES': valid_data['notes'].tolist()
})
case_insensitive.to_sql('06_case_insensitive', engine, if_exists='replace', index=False)
print(f"✅ Created with columns: {list(case_insensitive.columns)}")

# ==================== 07_extra_columns ====================
print("\n📊 Creating 07_extra_columns (has extra columns)...")
extra_columns = valid_data.copy()
extra_columns['discount'] = [10, 0, 15, 5, 0, 10, 0, 0]
extra_columns['tax_rate'] = [0.08, 0.20, 0.08, 0.08, 0.08, 0.08, 0.20, 0.08]
extra_columns['margin'] = extra_columns['revenue'] - extra_columns['cost']
extra_columns.to_sql('07_extra_columns', engine, if_exists='replace', index=False)
print(f"✅ Created with columns: {list(extra_columns.columns)}")

# ==================== 08_empty_table ====================
print("\n📊 Creating 08_empty_table (no rows)...")
empty_table = valid_data.copy()
empty_table = empty_table.iloc[0:0]  # Keep structure but no rows
empty_table.to_sql('08_empty_table', engine, if_exists='replace', index=False)
print(f"✅ Created with {len(empty_table)} rows")

# ==================== 09_large_table ====================
print("\n📊 Creating 09_large_table (50,000 rows)...")
large_table = pd.DataFrame()
base_date = datetime(2024, 1, 1)
customers = ['Acme Corp', 'BetaCo', 'Delta Inc', 'Gamma LLC', 'Zeta Corp']
products = ['Basic Plan', 'Premium Plan', 'Enterprise Plan']
regions = ['US', 'EU', 'APAC']
currencies = ['USD', 'EUR']
payment_statuses = ['paid', 'pending', 'failed']

for i in range(50000):
    row_date = base_date + timedelta(days=i % 365)
    large_table.loc[i, 'date'] = row_date.strftime('%Y-%m-%d')
    large_table.loc[i, 'customer'] = np.random.choice(customers)
    large_table.loc[i, 'product'] = np.random.choice(products)
    large_table.loc[i, 'region'] = np.random.choice(regions)
    large_table.loc[i, 'revenue'] = round(np.random.uniform(100, 10000), 2)
    large_table.loc[i, 'cost'] = round(large_table.loc[i, 'revenue'] * np.random.uniform(0.4, 0.8), 2)
    large_table.loc[i, 'currency'] = np.random.choice(currencies)
    large_table.loc[i, 'quantity'] = np.random.randint(1, 10)
    large_table.loc[i, 'payment_status'] = np.random.choice(payment_statuses, p=[0.7, 0.2, 0.1])

large_table.to_sql('09_large_table', engine, if_exists='replace', index=False, chunksize=1000)
print(f"✅ Created with {len(large_table)} rows")

# ==================== 10_wide_table ====================
print("\n📊 Creating 10_wide_table (many columns)...")
wide_table = valid_data.copy()
for i in range(50):
    wide_table[f'extra_column_{i:03d}'] = np.random.rand(len(wide_table))
wide_table.to_sql('10_wide_table', engine, if_exists='replace', index=False)
print(f"✅ Created with {len(wide_table)} rows and {len(wide_table.columns)} columns")

# ==================== Verify all tables ====================
print("\n" + "="*60)
print("📋 VERIFYING ALL TABLES")
print("="*60)

with engine.connect() as conn:
    # Get all tables
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'testdb'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    
    print(f"\n✅ Created {len(tables)} test tables:")
    for table in tables:
        # Get row count
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        row_count = result.scalar()
        
        # Get columns
        result = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result]
        
        print(f"\n  📊 {table}:")
        print(f"     • Rows: {row_count:,}")
        print(f"     • Columns: {len(columns)}")
        print(f"     • Cols: {columns[:5]}{'...' if len(columns) > 5 else ''}")

print("\n" + "="*60)
print("✅ ALL TEST TABLES CREATED SUCCESSFULLY!")
print("="*60)