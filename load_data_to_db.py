import pandas as pd
from sqlalchemy import create_engine
import os

# Your database connection (matches your Docker container)
DB_CONNECTION = "postgresql://postgres:testpass@localhost:5432/testdb"

# Path to your CSV/Excel file
FILE_PATH = "data.csv"  # Change this to your file path

def load_csv_to_db():
    """Load CSV file to PostgreSQL"""
    print(f"📂 Reading {FILE_PATH}...")
    
    # Read the file (works for both CSV and Excel)
    if FILE_PATH.endswith('.csv'):
        df = pd.read_csv(FILE_PATH)
    else:
        df = pd.read_excel(FILE_PATH)
    
    print(f"✅ Loaded {len(df)} rows")
    print(f"📋 Columns: {list(df.columns)}")
    
    # Create database connection
    engine = create_engine(DB_CONNECTION)
    
    # Write to database - replaces table if exists
    print("💾 Writing to database...")
    df.to_sql('sales_data', engine, if_exists='replace', index=False)
    
    print("✅ Data loaded successfully!")
    
    # Verify
    result = pd.read_sql("SELECT COUNT(*) FROM sales_data", engine)
    print(f"📊 Verified: {result.iloc[0,0]} rows in database")

def load_with_schema_matching():
    """Load data using your existing SchemaMapper"""
    from agents.schema_mapper import SchemaMapper
    
    print("📂 Reading file...")
    if FILE_PATH.endswith('.csv'):
        df = pd.read_csv(FILE_PATH)
    else:
        df = pd.read_excel(FILE_PATH)
    
    # Use your SchemaMapper to clean the data first!
    print("🧹 Applying SchemaMapper...")
    mapper = SchemaMapper(df)
    clean_df, mapping, warnings = mapper.map_schema()
    
    print(f"✅ Cleaned data shape: {clean_df.shape}")
    print(f"🔄 Column mapping: {mapping}")
    
    if warnings:
        print(f"⚠️ Warnings: {warnings}")
    
    # Connect to database
    engine = create_engine(DB_CONNECTION)
    
    # Write cleaned data to database
    clean_df.to_sql('sales_cleaned', engine, if_exists='replace', index=False)
    
    print("✅ Cleaned data loaded successfully!")

if __name__ == "__main__":
    # Choose which method to use:
    
    # Method 1: Simple load
    load_csv_to_db()
    
    # Method 2: Load with SchemaMapper (preserves your data cleaning logic)
    # load_with_schema_matching()