from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta 
from app.core.database import Base
from passlib.context import CryptContext
import secrets
import hashlib

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)  # Add expiration
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)  # Track when verified
    
    analyses = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password):
        """Hash and set password using Argon2"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password):
        """Verify password using Argon2"""
        return pwd_context.verify(password, self.hashed_password)
    
    def generate_verification_token(self):
        """Generate a unique verification token with expiration"""
        self.verification_token = secrets.token_urlsafe(32)
        # Token expires in 24 hours
        self.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.verification_token
    
    def is_token_valid(self):
        """Check if verification token is still valid"""
        if not self.verification_token_expires:
            return False
        return datetime.utcnow() < self.verification_token_expires
    
    def verify(self):
        """Mark user as verified"""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        self.verification_token = None
        self.verification_token_expires = None