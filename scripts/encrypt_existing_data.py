#!/usr/bin/env python
"""Migrate existing user data to encrypted format"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.api.v1.models.user import User
from app.core.encryption import get_db_encryption

def migrate_user_data():
    """Encrypt existing user email and full_name fields"""
    db = SessionLocal()
    encryption = get_db_encryption()
    
    try:
        # Check if migration already done
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='email_encrypted'"))
        if not result.fetchone():
            # Add encrypted columns
            db.execute(text("ALTER TABLE users ADD COLUMN email_encrypted BYTEA"))
            db.execute(text("ALTER TABLE users ADD COLUMN full_name_encrypted BYTEA"))
            db.commit()
            print("✅ Added encrypted columns")
        
        # Migrate existing data
        users = db.query(User).all()
        migrated_count = 0
        
        for user in users:
            # Check if already migrated
            if user.email_encrypted is None and user.email is not None:
                user.email = user.email  # This triggers encryption
                migrated_count += 1
        
        db.commit()
        print(f"✅ Migrated {migrated_count} users to encrypted format")
        
        # Optional: Drop old columns after verifying
        # db.execute(text("ALTER TABLE users DROP COLUMN email"))
        # db.execute(text("ALTER TABLE users DROP COLUMN full_name"))
        # print("✅ Dropped old plaintext columns")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_user_data()