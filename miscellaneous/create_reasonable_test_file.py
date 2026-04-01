import pandas as pd
import numpy as np
import os

# Create a test file with reasonable dimensions
rows = 1000
cols = 500  # Well under SQLite's 2000 column limit

print("="*60)
print("📂 Creating reasonable test file")
print("="*60)

# Generate random data
data = np.random.rand(rows, cols)
df = pd.DataFrame(data, columns=[f"col_{i}" for i in range(cols)])

# Add the required columns for your validation
print("\n📝 Adding required columns...")
df['date'] = pd.date_range('2024-01-01', periods=rows)
df['revenue'] = np.random.randint(100, 1000, rows)
df['customer'] = np.random.choice(['Acme Corp', 'BetaCo', 'Delta Inc', 'Gamma LLC'], rows)
df['product'] = np.random.choice(['Premium Plan', 'Basic Plan', 'Enterprise Plan'], rows)
df['region'] = np.random.choice(['US', 'EU', 'APAC'], rows)
df['cost'] = np.random.randint(50, 500, rows)
df['currency'] = np.random.choice(['USD', 'EUR', 'JPY'], rows)
df['quantity'] = np.random.randint(1, 10, rows)
df['payment_status'] = np.random.choice(['paid', 'pending', 'overdue'], rows)
df['notes'] = ''

print(f"✅ Final shape: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"✅ Columns include: {list(df.columns)[:10]}...")

# Save as CSV
output_file = "reasonable_test.csv"
df.to_csv(output_file, index=False)
print(f"\n✅ Saved to {output_file}")
print(f"📁 Full path: {os.path.abspath(output_file)}")

# Also save a smaller version for quick tests
small_df = df.head(100)
small_df.to_csv("reasonable_test_small.csv", index=False)
print(f"✅ Also saved small version (100 rows) to reasonable_test_small.csv")