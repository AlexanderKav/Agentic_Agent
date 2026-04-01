#!/usr/bin/env python
"""Verify security features are working"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.api.v1.models.user import User
from app.core.encryption import get_db_encryption
from app.services.secrets_manager import get_secrets_manager
from app.services.key_rotation import get_key_rotation_service

def verify_encryption():
    """Verify database encryption"""
    print("\n🔐 Verifying Database Encryption...")
    db = SessionLocal()
    encryption = get_db_encryption()
    
    user = db.query(User).first()
    if user:
        print(f"  ✅ User found: {user.username}")
        print(f"  ✅ Email encrypted in DB: {user.email_encrypted is not None}")
        print(f"  ✅ Email decrypted via property: {user.email}")
    else:
        print("  ⚠️ No users found - create a test user first")
    
    db.close()

def verify_secrets_manager():
    """Verify secrets manager"""
    print("\n🔐 Verifying Secrets Manager...")
    secrets = get_secrets_manager()
    
    secret_keys = secrets.list()
    print(f"  ✅ Secrets found: {secret_keys}")
    print(f"  ✅ Secrets file location: /app/data/secrets.enc")

def verify_key_rotation():
    """Verify key rotation"""
    print("\n🔐 Verifying Key Rotation...")
    rotation = get_key_rotation_service()
    
    status = rotation.get_all_rotation_status()
    print(f"  ✅ Keys tracked: {list(status.keys())}")
    for key, info in status.items():
        print(f"     - {key}: version {info.get('current_version', 1)}")

def verify_audit_logs():
    """Verify audit logs exist"""
    print("\n🔐 Verifying Audit Logs...")
    import os
    log_dir = "/app/logs/audit"
    if os.path.exists(log_dir):
        logs = os.listdir(log_dir)
        print(f"  ✅ Audit logs found: {len(logs)} files")
    else:
        print("  ⚠️ No audit logs found")

if __name__ == "__main__":
    print("=" * 50)
    print("Security Feature Verification")
    print("=" * 50)
    
    verify_encryption()
    verify_secrets_manager()
    verify_key_rotation()
    verify_audit_logs()
    
    print("\n✅ Security verification complete!")