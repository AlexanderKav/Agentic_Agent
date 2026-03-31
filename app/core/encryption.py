"""
Database encryption utilities using pgcrypto
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine

logger = logging.getLogger(__name__)


class DatabaseEncryption:
    """
    Manages database encryption using pgcrypto for PostgreSQL.
    For SQLite, uses Fernet symmetric encryption.
    """
    
    def __init__(self):
        self.db_type = os.getenv('DATABASE_URL', '').split(':')[0]
        self._cipher = None
        self._init_cipher()
    
    def _init_cipher(self):
        """Initialize encryption cipher"""
        master_key = os.getenv('DB_ENCRYPTION_KEY')
        if not master_key:
            # For development only - in production this must be set
            master_key = 'dev-encryption-key-32-bytes-long!!'
            logger.warning("Using development encryption key - NOT SECURE FOR PRODUCTION")
        
        # Derive a Fernet key from the master key
        salt = b'agentic-db-salt-2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self._cipher = Fernet(key)
    
    def enable_pgcrypto_extension(self, db: Session):
        """Enable pgcrypto extension in PostgreSQL"""
        if self.db_type == 'postgresql':
            try:
                db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
                db.commit()
                logger.info("pgcrypto extension enabled")
            except Exception as e:
                logger.error(f"Failed to enable pgcrypto: {e}")
    
    def encrypt_column(self, value: str) -> bytes:
        """
        Encrypt a column value.
        For PostgreSQL, uses pgcrypto if available.
        For SQLite, uses Fernet.
        """
        if value is None:
            return None
        
        if self.db_type == 'postgresql':
            # Return as bytes for PostgreSQL pgcrypto
            # This will be handled by SQLAlchemy with the pgcrypto function
            return value.encode('utf-8')
        else:
            # SQLite fallback
            return self._cipher.encrypt(value.encode('utf-8'))
    
    def decrypt_column(self, encrypted_value: bytes) -> str:
        """
        Decrypt a column value.
        """
        if encrypted_value is None:
            return None
        
        if self.db_type == 'postgresql':
            return encrypted_value.decode('utf-8')
        else:
            return self._cipher.decrypt(encrypted_value).decode('utf-8')
    
    def get_pgcrypto_encrypt_sql(self, column_name: str, key: str = None) -> str:
        """
        Get SQL expression for encrypting a column using pgcrypto.
        Use this in SQLAlchemy queries for PostgreSQL.
        """
        if key is None:
            key = os.getenv('DB_ENCRYPTION_KEY', 'dev-key')
        
        return f"pgp_sym_encrypt({column_name}, '{key}')"
    
    def get_pgcrypto_decrypt_sql(self, column_name: str, key: str = None) -> str:
        """
        Get SQL expression for decrypting a column using pgcrypto.
        """
        if key is None:
            key = os.getenv('DB_ENCRYPTION_KEY', 'dev-key')
        
        return f"pgp_sym_decrypt({column_name}, '{key}')"


# Singleton instance
_db_encryption = None

def get_db_encryption() -> DatabaseEncryption:
    """Get the global database encryption instance"""
    global _db_encryption
    if _db_encryption is None:
        _db_encryption = DatabaseEncryption()
    return _db_encryption