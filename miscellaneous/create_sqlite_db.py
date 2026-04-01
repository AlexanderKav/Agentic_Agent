import pandas as pd
import sqlite3
import os

def create_sqlite_db():
    """Create SQLite database from the large CSV file"""
    
    print("="*60)
    print("📂 Creating SQLite database with large_test table")
    print("="*60)
    
    # Remove existing file if present
    db_file = "test.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️ Removed existing {db_file}")
    
    # Read the CSV file
    print("\n📖 Reading CSV file...")
    df = pd.read_csv("large_test_file.csv")
    print(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns")
    
    # Connect to SQLite (creates the file)
    print("\n🔌 Connecting to SQLite...")
    conn = sqlite3.connect(db_file)
    
    # Load data to SQLite
    print(f"\n📤 Loading to SQLite table 'large_test'...")
    df.to_sql("large_test", conn, if_exists='replace', index=False)
    
    print(f"✅ Data loaded successfully")
    
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM large_test")
    count = cursor.fetchone()[0]
    print(f"📊 Verification: {count} rows in table")
    
    # Get column info
    cursor.execute("PRAGMA table_info(large_test)")
    columns = cursor.fetchall()
    print(f"📋 Table has {len(columns)} columns")
    
    conn.close()
    print(f"\n✅ Database file created: {db_file}")
    print(f"📁 Full path: {os.path.abspath(db_file)}")

if __name__ == "__main__":
    create_sqlite_db()