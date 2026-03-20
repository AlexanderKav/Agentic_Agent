#!/usr/bin/env python
"""
Initialize database tables for Agentic Analyst
Run this script to create all necessary tables.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from app.api.v1.models.user import Base as UserBase
from app.api.v1.models.analysis import Base as AnalysisBase
from sqlalchemy import inspect

def init_db():
    """Create all tables"""
    print("🚀 Creating database tables...")
    
    try:
        # Create tables
        UserBase.metadata.create_all(bind=engine)
        AnalysisBase.metadata.create_all(bind=engine)
        
        print("✅ Tables created successfully!")
        
        # List all tables
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📋 Tables created: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    init_db()