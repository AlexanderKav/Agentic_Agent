#!/usr/bin/env python
"""Run database migrations for the new schema"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal
from app.api.v1.models.analysis import AnalysisHistory

def add_raw_results_column():
    """Add raw_results column to analysis_history table"""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'analysis_history' 
                AND column_name = 'raw_results'
            """))
            
            if result.fetchone():
                print("✅ Column 'raw_results' already exists")
                return
            
            # Add the column
            conn.execute(text(
                "ALTER TABLE analysis_history ADD COLUMN raw_results JSONB"
            ))
            conn.commit()
            print("✅ Added raw_results column to analysis_history")
    except Exception as e:
        print(f"❌ Error adding column: {e}")

def migrate_existing_data():
    """Move existing results to raw_results"""
    db = SessionLocal()
    try:
        analyses = db.query(AnalysisHistory).filter(
            AnalysisHistory.raw_results.is_(None),
            AnalysisHistory.results.isnot(None)
        ).all()
        
        print(f"📊 Found {len(analyses)} analyses to migrate")
        
        for analysis in analyses:
            analysis.raw_results = analysis.results
            db.add(analysis)
        
        db.commit()
        print(f"✅ Migrated {len(analyses)} analyses")
    except Exception as e:
        print(f"❌ Error migrating data: {e}")
        db.rollback()
    finally:
        db.close()

def create_new_tables():
    """Create new tables (metrics, insights, charts)"""
    from app.api.v1.models.analysis import AnalysisMetric, AnalysisInsight, AnalysisChart
    
    try:
        # Create tables if they don't exist
        AnalysisMetric.__table__.create(bind=engine, checkfirst=True)
        AnalysisInsight.__table__.create(bind=engine, checkfirst=True)
        AnalysisChart.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created new tables (metrics, insights, charts)")
    except Exception as e:
        print(f"⚠️ Tables may already exist: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("Running Database Migration")
    print("=" * 50)
    
    add_raw_results_column()
    create_new_tables()
    migrate_existing_data()
    
    print("\n✅ Migration complete!")