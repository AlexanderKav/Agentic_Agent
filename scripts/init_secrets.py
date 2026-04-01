# scripts/init_secrets.py
import os
import sys

sys.path.append('/app')

from app.services.secrets_manager import get_secrets_manager

def init_secrets():
    print("=== Initializing Secrets Manager ===")
    
    secrets = get_secrets_manager()
    print(f"Backend: {secrets.backend_type}")
    print(f"Secrets found before: {secrets.list()}")
    
    # Set a test secret to trigger file creation
    secrets.set('TEST_SECRET', 'test-value-123')
    print(f"Test secret saved")
    
    print(f"Secrets found after: {secrets.list()}")
    
    # Check if secrets.enc was created
    if os.path.exists('/app/data/secrets.enc'):
        size = os.path.getsize('/app/data/secrets.enc')
        print(f"✅ secrets.enc created! Size: {size} bytes")
    else:
        print("❌ secrets.enc still missing")
    
    # Check directory permissions
    print(f"Data directory writable: {os.access('/app/data', os.W_OK)}")

if __name__ == "__main__":
    init_secrets()