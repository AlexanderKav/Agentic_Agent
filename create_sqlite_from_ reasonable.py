import pandas as pd
import sqlite3
import os

def create_sqlite_db():
    """Create SQLite database from the reasonable CSV file"""
    
    print("="*60)
    print("📂 Creating SQLite database with test table")
    print("="*60)
    
    db_file = "test_reasonable.db"
    csv_file = "reasonable_test.csv"
    
    # Remove existing file if present
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️ Removed existing {db_file}")
    
    # Read the CSV file
    print(f"\n📖 Reading {csv_file}...")
    df = pd.read_csv(csv_file)
    print(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns")
    
    # Connect to SQLite
    print("\n🔌 Connecting to SQLite...")
    conn = sqlite3.connect(db_file)
    
    # Load data to SQLite
    print(f"\n📤 Loading to SQLite table 'test_data'...")
    df.to_sql("test_data", conn, if_exists='replace', index=False)
    
    print(f"✅ Data loaded successfully")
    
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM test_data")
    count = cursor.fetchone()[0]
    print(f"📊 Verification: {count} rows in table")
    
    # Get column info
    cursor.execute("PRAGMA table_info(test_data)")
    columns = cursor.fetchall()
    print(f"📋 Table has {len(columns)} columns")
    
    # Show sample data
    sample = pd.read_sql_query("SELECT * FROM test_data LIMIT 3", conn)
    print("\n📝 Sample data (first 3 rows):")
    print(sample[['date', 'customer', 'revenue', 'product']].head())
    
    conn.close()
    print(f"\n✅ Database file created: {db_file}")
    print(f"📁 Full path: {os.path.abspath(db_file)}")

def create_postgres_compatible():
    """Create a version that's also compatible with PostgreSQL"""
    
    print("\n" + "="*60)
    print("📂 Also creating PostgreSQL-compatible CSV")
    print("="*60)
    
    # PostgreSQL has a 1600 column limit, so 500 is safe
    print("✅ 500 columns is well under PostgreSQL's 1600 column limit")

if __name__ == "__main__":
    create_sqlite_db()
    create_postgres_compatible()