import secrets
import string

# Generate a secure random key for SECRET_KEY
secret_key = secrets.token_urlsafe(32)
print(f"SECRET_KEY={secret_key}")

# Generate another for AUDIT_SECRET_KEY
audit_key = secrets.token_urlsafe(32)
print(f"AUDIT_SECRET_KEY={audit_key}")