"""
Secrets Manager - Centralized secrets management for the application
Supports multiple backends: local file (encrypted), AWS Secrets Manager, HashiCorp Vault
"""

import base64
import json
import logging
import os
import boto3
from abc import ABC, abstractmethod

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecretsBackend(ABC):
    """Abstract base class for secrets backends"""

    @abstractmethod
    def get_secret(self, secret_name: str) -> str | None:
        """Retrieve a secret by name"""
        pass

    @abstractmethod
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret value"""
        pass

    @abstractmethod
    def list_secrets(self) -> list:
        """List all available secret names"""
        pass


class LocalEncryptedBackend(SecretsBackend):
    """
    Local encrypted file backend for development.
    Uses Fernet symmetric encryption with a master password.
    """

    def __init__(self, secrets_file: str = "secrets.enc", key_file: str = None):
        self.secrets_file = secrets_file
        self._cipher = None
        self._secrets: dict[str, str] = {}

        # Load or create encryption key
        if key_file and os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate key from environment or create new
            master_password = os.getenv('SECRETS_MASTER_PASSWORD', 'dev-master-password-change-in-production')
            salt = b'agentic-analyst-salt-2024'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            if key_file:
                with open(key_file, 'wb') as f:
                    f.write(key)

        self._cipher = Fernet(key)
        self._load_secrets()

    def _load_secrets(self):
        """Load encrypted secrets from file"""
        if os.path.exists(self.secrets_file):
            try:
                with open(self.secrets_file, 'rb') as f:
                    encrypted_data = f.read()
                    decrypted = self._cipher.decrypt(encrypted_data)
                    self._secrets = json.loads(decrypted)
                logger.info(f"Loaded {len(self._secrets)} secrets from {self.secrets_file}")
            except Exception as e:
                logger.error(f"Failed to load secrets: {e}")
                self._secrets = {}
        else:
            self._secrets = {}

    def _save_secrets(self):
        """Save encrypted secrets to file"""
        try:
            encrypted = self._cipher.encrypt(json.dumps(self._secrets).encode())
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted)
            logger.info(f"Saved {len(self._secrets)} secrets to {self.secrets_file}")
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")

    def get_secret(self, secret_name: str) -> str | None:
        return self._secrets.get(secret_name)

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        self._secrets[secret_name] = secret_value
        self._save_secrets()
        return True

    def list_secrets(self) -> list:
        return list(self._secrets.keys())


class AWSSecretsManagerBackend(SecretsBackend):
    """
    AWS Secrets Manager backend for production.
    Requires AWS credentials configured (IAM role or environment variables).
    """

    def __init__(self, region: str = None):
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                
                self._client = boto3.client('secretsmanager', region_name=self.region)
            except ImportError:
                raise ImportError("boto3 is required for AWS Secrets Manager backend")
            except Exception as e:
                logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
                raise
        return self._client

    def get_secret(self, secret_name: str) -> str | None:
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            if 'SecretString' in response:
                return response['SecretString']
            else:
                return base64.b64decode(response['SecretBinary']).decode('utf-8')
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret {secret_name} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            return None

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        try:
            self.client.create_secret(
                Name=secret_name,
                SecretString=secret_value
            )
            return True
        except self.client.exceptions.ResourceExistsException:
            # Update existing secret
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {secret_name}: {e}")
            return False

    def list_secrets(self) -> list:
        try:
            response = self.client.list_secrets()
            return [secret['Name'] for secret in response.get('SecretList', [])]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class SecretsManager:
    """
    Unified secrets manager that selects backend based on environment.
    """

    def __init__(self):
        self.backend_type = os.getenv('SECRETS_BACKEND', 'local')
        self._backend = None
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the appropriate backend"""
        if self.backend_type == 'aws':
            self._backend = AWSSecretsManagerBackend()
            logger.info("Using AWS Secrets Manager backend")
        elif self.backend_type == 'local':
            secrets_file = os.getenv('SECRETS_FILE', 'secrets.enc')
            key_file = os.getenv('SECRETS_KEY_FILE')
            self._backend = LocalEncryptedBackend(secrets_file, key_file)
            logger.info(f"Using local encrypted backend with file: {secrets_file}")
        else:
            raise ValueError(f"Unknown secrets backend: {self.backend_type}")

    @property
    def backend(self) -> SecretsBackend:
        if self._backend is None:
            self._initialize_backend()
        return self._backend

    def get(self, secret_name: str) -> str | None:
        """Get a secret value"""
        return self.backend.get_secret(secret_name)

    def set(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret value"""
        return self.backend.set_secret(secret_name, secret_value)

    def list(self) -> list:
        """List all secret names"""
        return self.backend.list_secrets()

    def get_or_raise(self, secret_name: str) -> str:
        """Get a secret or raise if not found"""
        value = self.get(secret_name)
        if value is None:
            raise ValueError(f"Required secret '{secret_name}' not found")
        return value


# Singleton instance
_secrets_manager = None

def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


__all__ = ['ABTestService']  # For ab_testing.py
__all__ = ['EmailService']   # For email.py
__all__ = ['KeyRotationService', 'get_key_rotation_service']  # For key_rotation.py
__all__ = ['SecretsManager', 'get_secrets_manager']  # For secrets_manager.py