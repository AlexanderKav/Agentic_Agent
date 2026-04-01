# scripts/migrate_secrets.py
import os
import sys

sys.path.append('/app')

from app.services.secrets_manager import get_secrets_manager

def migrate_secrets():
    print("=== Migrating Secrets to Secrets Manager ===")
    
    secrets = get_secrets_manager()
    
    # Read secrets from environment
    env_secrets = {
        'SECRET_KEY': os.environ.get('SECRET_KEY', ''),
        'AUDIT_SECRET_KEY': os.environ.get('AUDIT_SECRET_KEY', ''),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
        'GOOGLE_APPLICATION_CREDENTIALS': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
    }
    
    # Store each secret
    for name, value in env_secrets.items():
        if value:
            secrets.set(name, value)
            print(f"✅ Stored {name}")
        else:
            print(f"⚠️ {name} not found in environment")
    
    # Verify stored secrets
    print("\n=== Stored Secrets ===")
    stored = secrets.list()
    for name in stored:
        if name != 'TEST_SECRET':
            print(f"  - {name}")
    
    print(f"\n📁 secrets.enc size: {os.path.getsize('/app/data/secrets.enc')} bytes")

if __name__ == "__main__":
    migrate_secrets()