#!/usr/bin/env python
"""Test script to connect to Docker PostgreSQL database and display data."""

import pandas as pd
from sqlalchemy import create_engine, text
import sys

def test_database_connection():
    """Test connection to PostgreSQL and display data."""
    
    # Connection parameters
    DB_CONNECTION = "postgresql://postgres:testpass@localhost:5432/testdb"
    
    print("=" * 60)
    print("🔌 Testing PostgreSQL Database Connection")
    print("=" * 60)
    
    try:
        # Create engine and connect
        print("\n📡 Connecting to database...")
        engine = create_engine(DB_CONNECTION)
        
        # Test connection with simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(" Connection successful!")
        
        # Query the sales table
        print("\n Fetching data from 'sales' table...")
        df = pd.read_sql_query("SELECT * FROM sales", engine)
        
        # Display results
        print(f"\n Found {len(df)} rows in table")
        print("\n" + "=" * 60)
        print(" DataFrame HEAD (first 5 rows):")
        print("=" * 60)
        print(df.head())
        
        # Show basic info about the data
        print("\n" + "=" * 60)
        print(" DataFrame Info:")
        print("=" * 60)
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Data types:\n{df.dtypes}")
        
        # Show summary statistics for numeric columns
        print("\n" + "=" * 60)
        print(" Summary Statistics (numeric columns):")
        print("=" * 60)
        print(df.describe())
        
        return df
        
    except Exception as e:
        print(f"\n Error: {e}")
        print("\n Troubleshooting tips:")
        print("  1. Make sure Docker container is running: docker ps")
        print("  2. Check if port 5432 is correct")
        print("  3. Verify credentials (postgres/testpass)")
        print("  4. Ensure database 'testdb' exists")
        return None

def check_docker_container():
    """Check if Docker container is running."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=test-postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if "test-postgres" in result.stdout:
            print("Docker container 'test-postgres' is running")
            return True
        else:
            print("Docker container 'test-postgres' is NOT running")
            print("   Run: docker start test-postgres")
            return False
    except Exception as e:
        print(f"Error checking Docker: {e}")
        return False

if __name__ == "__main__":
    print("\n Checking Docker container status...")
    if check_docker_container():
        df = test_database_connection()
        
        if df is not None:
            print("\n" + "=" * 60)
            print("Test completed successfully!")
            print("=" * 60)
    else:
        print("\n Cannot proceed without Docker container.")
        print("   Run: docker start test-postgres")