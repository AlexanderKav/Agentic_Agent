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

# 🔥 Change from argon2 to bcrypt (more reliable on Render)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    last_login = Column(DateTime, nullable=True)  # Add this column

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
        print(f"✅ Password hashed for user {self.username}")

    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        result = pwd_context.verify(password, self.hashed_password)
        print(f"🔐 Password verification for {self.username}: {result}")
        return result

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
        print(f"🔐 Reset token generated for {self.username}, expires at {self.reset_token_expires}")
        return self.reset_token

    def verify_reset_token(self, token: str) -> bool:
        """Verify reset token is valid"""
        if not self.reset_token or not self.reset_token_expires:
            print(f"❌ Reset token verification failed: missing token or expiry for {self.username}")
            return False
        
        token_valid = self.reset_token == token
        not_expired = datetime.utcnow() < self.reset_token_expires
        
        print(f"🔐 Reset token verification for {self.username}:")
        print(f"   Token matches: {token_valid}")
        print(f"   Not expired: {not_expired} (expires at {self.reset_token_expires}, now {datetime.utcnow()})")
        
        return token_valid and not_expired

    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<User(id={self.id}, username={self.username}, is_verified={self.is_verified})>"


__all__ = ['User']