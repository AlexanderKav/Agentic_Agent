# scripts/generate_keys.py
import secrets
import string
import json

def generate_secure_key(length=32):
    """Generate a cryptographically secure random string"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=32):
    """Generate a hex key (for DB encryption)"""
    return secrets.token_hex(16)  # 32 hex characters

print("=" * 50)
print("Generate these keys and save them securely:")
print("=" * 50)
print()
print("# MASTER KEYS (Save these securely - they won't rotate)")
print(f"SECRETS_MASTER_PASSWORD={generate_secure_key(20)}")
print(f"DB_ENCRYPTION_KEY={generate_hex_key()}")
print()
print("# INITIAL SECRETS (These will auto-rotate)")
print(f"SECRET_KEY={generate_secure_key(32)}")
print(f"AUDIT_SECRET_KEY={generate_secure_key(32)}")
print()
print("# EXTERNAL API KEYS (Get from providers)")
print("OPENAI_API_KEY=sk-... (get from platform.openai.com)")
print("GOOGLE_CREDENTIALS='{...}' (from Google Cloud Console)")