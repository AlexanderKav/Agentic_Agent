# app/api/v1/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta 
from app.core.database import Base  # Import Base from database.py
from app.core.encryption import get_db_encryption
from passlib.context import CryptContext
import secrets

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Non-encrypted fields (searchable)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Encrypted fields - store sensitive data encrypted
    email_encrypted = Column(LargeBinary, nullable=True)
    full_name_encrypted = Column(LargeBinary, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    analyses = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def email(self):
        """Decrypt email when accessed"""
        if self.email_encrypted:
            return get_db_encryption().decrypt_column(self.email_encrypted)
        return None
    
    @email.setter
    def email(self, value):
        """Encrypt email when set"""
        if value:
            self.email_encrypted = get_db_encryption().encrypt_column(value)
        else:
            self.email_encrypted = None
    
    @property
    def full_name(self):
        """Decrypt full name when accessed"""
        if self.full_name_encrypted:
            return get_db_encryption().decrypt_column(self.full_name_encrypted)
        return None
    
    @full_name.setter
    def full_name(self, value):
        """Encrypt full name when set"""
        if value:
            self.full_name_encrypted = get_db_encryption().encrypt_column(value)
        else:
            self.full_name_encrypted = None
    
    def set_password(self, password):
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password):
        return pwd_context.verify(password, self.hashed_password)
    
    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.verification_token
    
    def is_token_valid(self):
        if not self.verification_token_expires:
            return False
        return datetime.utcnow() < self.verification_token_expires
    
    def verify(self):
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        self.verification_token = None
        self.verification_token_expires = None