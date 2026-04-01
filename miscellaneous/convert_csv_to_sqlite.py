"""
Convert all test CSV files to a SQLite database for testing
"""

import pandas as pd
import sqlite3
import os

# Configuration
CSV_DIR = "test_files"
DB_PATH = os.path.join(CSV_DIR, "test_validation.db")

print("="*60)
print("🔄 CONVERTING CSV TEST FILES TO SQLITE DATABASE")
print("="*60)

# Remove existing database if present
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"🗑️ Removed existing database: {DB_PATH}")

# Connect to SQLite (creates new database)
conn = sqlite3.connect(DB_PATH)
print(f"✅ Created new database: {DB_PATH}")

# Get all CSV files
csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith('.csv') and f != 'test_validation.db']
csv_files.sort()  # Sort to maintain order

print(f"\n📋 Found {len(csv_files)} CSV files to convert")

# Conversion mapping
test_scenarios = {
    "01_valid.csv": "valid_data",
    "02_missing_date.csv": "missing_date",
    "03_missing_revenue.csv": "missing_revenue", 
    "04_invalid_dates.csv": "invalid_dates",
    "05_non_numeric_revenue.csv": "non_numeric_revenue",
    "06_case_insensitive.csv": "case_insensitive",
    "07_extra_columns.csv": "extra_columns",
    "08_empty.csv": "empty_table",
    "09_large.csv": "large_table",
    "10_wide.csv": "wide_table"
}

# Convert each CSV to a table
for csv_file in csv_files:
    csv_path = os.path.join(CSV_DIR, csv_file)
    
    # Get table name from mapping or use filename without extension
    table_name = test_scenarios.get(csv_file, os.path.splitext(csv_file)[0].replace('-', '_'))
    
    print(f"\n📄 Processing: {csv_file} → {table_name}")
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"   📊 Read {len(df)} rows, {len(df.columns)} columns")
        
        # For SQLite, we need to handle data types appropriately
        # Convert any datetime columns to string to avoid issues
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str)
        
        # Write to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"   ✅ Written to table '{table_name}'")
        
        # Verify
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   🔍 Verified: {count} rows in table")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Create a metadata table with test case descriptions
print("\n" + "="*60)
print("📋 CREATING METADATA TABLE")
print("="*60)

metadata = [
    ("valid_data", "✅ Should PASS - Valid data with all required columns"),
    ("missing_date", "❌ Should FAIL - Missing date column"),
    ("missing_revenue", "❌ Should FAIL - Missing revenue column"),
    ("invalid_dates", "❌ Should FAIL - Invalid date formats"),
    ("non_numeric_revenue", "❌ Should FAIL - Non-numeric revenue values"),
    ("case_insensitive", "✅ Should PASS - Case-insensitive column names"),
    ("extra_columns", "✅ Should PASS - Extra columns should be ignored"),
    ("empty_table", "⚠️ Should WARN - Empty table (no rows)"),
    ("large_table", "❌ Should FAIL - Exceeds row limit (150,000 rows)"),
    ("wide_table", "❌ Should FAIL - Exceeds column limit (2000 columns)")
]

df_metadata = pd.DataFrame(metadata, columns=['table_name', 'expected_result'])
df_metadata.to_sql("test_metadata", conn, if_exists='replace', index=False)

print("✅ Created 'test_metadata' table with test case descriptions")

# Show summary
print("\n" + "="*60)
print("📊 DATABASE SUMMARY")
print("="*60)

cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"\n📋 Tables in database ({len(tables)}):")
for table in tables:
    table_name = table[0]
    if table_name != 'test_metadata':
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"  • {table_name:<20} ({len(columns)} columns, {count:,} rows)")

# Show metadata
print("\n📋 Test Cases:")
cursor.execute("SELECT * FROM test_metadata")
for row in cursor.fetchall():
    print(f"  • {row[0]:<20} {row[1]}")

conn.close()

print("\n" + "="*60)
print(f"✅ Conversion complete! Database saved to: {DB_PATH}")
print("="*60)