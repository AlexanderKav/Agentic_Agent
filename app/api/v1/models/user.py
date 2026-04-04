# app/api/v1/models/user.py
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.encryption import get_db_encryption

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Encrypted fields
    email_encrypted = Column(LargeBinary, nullable=True)
    full_name_encrypted = Column(LargeBinary, nullable=True)

    # Password reset fields
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    #last_login = Column(DateTime, nullable=True)  # Optional: track last login

    analyses = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")

    @property
    def email(self) -> Optional[str]:
        """Decrypt email when accessed"""
        if self.email_encrypted:
            return get_db_encryption().decrypt_column(self.email_encrypted)
        return None

    @email.setter
    def email(self, value: Optional[str]) -> None:
        """Encrypt email when set"""
        if value:
            self.email_encrypted = get_db_encryption().encrypt_column(value)
        else:
            self.email_encrypted = None

    @property
    def full_name(self) -> Optional[str]:
        """Decrypt full name when accessed"""
        if self.full_name_encrypted:
            return get_db_encryption().decrypt_column(self.full_name_encrypted)
        return None

    @full_name.setter
    def full_name(self, value: Optional[str]) -> None:
        """Encrypt full name when set"""
        if value:
            self.full_name_encrypted = get_db_encryption().encrypt_column(value)
        else:
            self.full_name_encrypted = None

    def set_password(self, password: str) -> None:
        """Set hashed password"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.hashed_password)

    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.verification_token

    def is_token_valid(self) -> bool:
        """Check if verification token is still valid"""
        if not self.verification_token_expires:
            return False
        return datetime.utcnow() < self.verification_token_expires

    def verify(self) -> None:
        """Mark user as verified"""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        self.verification_token = None
        self.verification_token_expires = None

    def generate_reset_token(self) -> str:
        """Generate a password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token

    def verify_reset_token(self, token: str) -> bool:
        """Verify reset token is valid"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return (self.reset_token == token and
                datetime.utcnow() < self.reset_token_expires)

    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<User(id={self.id}, username={self.username}, is_verified={self.is_verified})>"


__all__ = ['User']