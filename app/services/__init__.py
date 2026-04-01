# services/__init__.py (optional - not necessary)
from .email import EmailService
from .ab_testing import ABTestService
from .secrets_manager import get_secrets_manager
from .key_rotation import get_key_rotation_service

__all__ = [
    'EmailService',
    'ABTestService', 
    'get_secrets_manager',
    'get_key_rotation_service'
]