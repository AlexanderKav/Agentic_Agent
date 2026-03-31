"""
Key Rotation Service - Automatically rotate API keys and secrets
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
from app.services.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class KeyRotationService:
    """
    Manages automatic rotation of API keys and secrets.
    Supports rotation with grace period (old key remains valid for overlap period).
    """
    
    def __init__(self):
        self.secrets = get_secrets_manager()
        self.rotation_interval_days = int(os.getenv('KEY_ROTATION_DAYS', 90))
        self.grace_period_days = int(os.getenv('KEY_GRACE_PERIOD_DAYS', 1))
        self._rotation_status = {}
    
    def _get_key_metadata(self, key_name: str) -> Dict:
        """Get metadata for a key"""
        metadata_key = f"{key_name}_metadata"
        metadata = self.secrets.get(metadata_key)
        if metadata:
            return json.loads(metadata)
        return {
            'current_version': 1,
            'last_rotation': None,
            'previous_key': None,
            'previous_key_expires': None
        }
    
    def _save_key_metadata(self, key_name: str, metadata: Dict):
        """Save key metadata"""
        metadata_key = f"{key_name}_metadata"
        self.secrets.set(metadata_key, json.dumps(metadata))
    
    def _generate_new_key(self, key_name: str) -> str:
        """Generate a new key value - override for specific key types"""
        # Default: generate random 32-character hex string
        import secrets
        return secrets.token_hex(32)
    
    def rotate_key(self, key_name: str, key_value: str = None) -> bool:
        """
        Rotate a key.
        
        Args:
            key_name: Name of the key to rotate
            key_value: Optional new key value (if None, auto-generate)
        
        Returns:
            bool: True if rotation succeeded
        """
        try:
            metadata = self._get_key_metadata(key_name)
            current_version = metadata['current_version']
            
            # Get current key value
            current_key = self.secrets.get(key_name)
            
            # Generate or use new key
            new_key = key_value or self._generate_new_key(key_name)
            
            # Store previous key with expiration
            if current_key:
                previous_key_expires = datetime.utcnow() + timedelta(days=self.grace_period_days)
                self.secrets.set(f"{key_name}_previous", current_key)
                self.secrets.set(f"{key_name}_previous_expires", previous_key_expires.isoformat())
            
            # Store new key
            self.secrets.set(key_name, new_key)
            
            # Update metadata
            metadata['current_version'] = current_version + 1
            metadata['last_rotation'] = datetime.utcnow().isoformat()
            metadata['previous_key'] = current_key
            metadata['previous_key_expires'] = (datetime.utcnow() + timedelta(days=self.grace_period_days)).isoformat()
            self._save_key_metadata(key_name, metadata)
            
            logger.info(f"Rotated key {key_name} to version {current_version + 1}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate key {key_name}: {e}")
            return False
    
    def verify_key(self, key_name: str, key_value: str) -> bool:
        """
        Verify a key, checking both current and previous (within grace period).
        
        Args:
            key_name: Name of the key to verify
            key_value: The key value to check
        
        Returns:
            bool: True if key is valid (current or previous within grace period)
        """
        # Check current key
        current_key = self.secrets.get(key_name)
        if current_key and current_key == key_value:
            return True
        
        # Check previous key if within grace period
        metadata = self._get_key_metadata(key_name)
        previous_key = self.secrets.get(f"{key_name}_previous")
        previous_key_expires = metadata.get('previous_key_expires')
        
        if previous_key and previous_key == key_value:
            if previous_key_expires:
                expires = datetime.fromisoformat(previous_key_expires)
                if datetime.utcnow() <= expires:
                    logger.info(f"Key {key_name} verified using previous key (within grace period)")
                    return True
                else:
                    # Clean up expired previous key
                    self.secrets.set(f"{key_name}_previous", None)
                    self._save_key_metadata(key_name, {})
        
        return False
    
    def check_and_rotate_if_needed(self, key_name: str) -> bool:
        """
        Check if a key needs rotation and rotate if necessary.
        
        Args:
            key_name: Name of the key to check
        
        Returns:
            bool: True if rotation was performed
        """
        metadata = self._get_key_metadata(key_name)
        last_rotation = metadata.get('last_rotation')
        
        if last_rotation:
            last_rotation_date = datetime.fromisoformat(last_rotation)
            days_since_rotation = (datetime.utcnow() - last_rotation_date).days
            
            if days_since_rotation >= self.rotation_interval_days:
                logger.info(f"Key {key_name} needs rotation (last rotated {days_since_rotation} days ago)")
                return self.rotate_key(key_name)
        
        return False
    
    def get_current_key(self, key_name: str) -> Optional[str]:
        """Get the current key value"""
        return self.secrets.get(key_name)
    
    def get_rotation_status(self, key_name: str) -> Dict:
        """Get rotation status for a key"""
        metadata = self._get_key_metadata(key_name)
        return {
            'key_name': key_name,
            'current_version': metadata.get('current_version', 1),
            'last_rotation': metadata.get('last_rotation'),
            'next_rotation_due': None,
            'has_previous_key': metadata.get('previous_key') is not None
        }
    
    def get_all_rotation_status(self) -> Dict:
        """Get rotation status for all tracked keys"""
        # Keys that should be tracked for rotation
        tracked_keys = [
            'SECRET_KEY',
            'AUDIT_SECRET_KEY',
            'OPENAI_API_KEY',
            'GOOGLE_CREDENTIALS'
        ]
        
        status = {}
        for key in tracked_keys:
            status[key] = self.get_rotation_status(key)
        
        return status


# Singleton instance
_key_rotation = None

def get_key_rotation_service() -> KeyRotationService:
    """Get the global key rotation service instance"""
    global _key_rotation
    if _key_rotation is None:
        _key_rotation = KeyRotationService()
    return _key_rotation