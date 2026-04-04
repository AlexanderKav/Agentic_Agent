# app/api/v1/endpoints/auth.py
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.v1.models.user import User
from app.config import settings
from app.core.database import get_db
from app.services.email import EmailService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Use settings from config
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ==================== Pydantic Models ====================

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(..., min_length=8)
    full_name: str | None = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class VerificationResponse(BaseModel):
    message: str
    email: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ==================== Helper Functions ====================

def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    require_verified: bool = True
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    if require_verified and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your inbox for verification link."
        )

    return user


def get_current_user_unverified(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current user without requiring email verification."""
    return get_current_user(token, db, require_verified=False)


# ==================== Endpoints ====================

@router.post("/register", response_model=VerificationResponse)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email."""
    # Check if user exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()

    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Username already registered")
        else:
            # Resend verification email
            token = existing_user.generate_verification_token()
            db.commit()

            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_verification_email,
                existing_user.email,
                existing_user.username,
                token
            )

            return {
                "message": "Verification email resent. Please check your inbox.",
                "email": existing_user.email
            }

    # Create new user
    user = User(username=user_data.username, is_verified=False)
    user.email = user_data.email
    user.full_name = user_data.full_name
    user.set_password(user_data.password)

    token = user.generate_verification_token()

    db.add(user)
    db.commit()
    db.refresh(user)

    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,
        user.username,
        token
    )

    logger.info(f"User registered: {user.username} ({user.email})")

    return {
        "message": "Registration successful! Please check your email to verify your account.",
        "email": user.email
    }


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email with token and return user data."""
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    if not user.is_token_valid():
        raise HTTPException(status_code=400, detail="Verification token has expired")

    if not user.is_verified:
        user.verify()
        db.commit()
        logger.info(f"Email verified for user: {user.username}")

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "message": "Email verified successfully",
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "created_at": user.created_at
        }
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user - requires verification."""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not user.verify_password(form_data.password):
        logger.warning(f"Failed login attempt for {form_data.username} from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=401,
            detail="Please verify your email first. Check your inbox for the verification link."
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info(f"User logged in: {user.username} from {request.client.host}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "created_at": user.created_at
        }
    }


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend verification email."""
    # Note: This iterates over all users to decrypt emails
    # For production, consider adding an email hash index
    users = db.query(User).filter(User.is_verified == False).all()
    user = None

    for u in users:
        if u.email == request.email:
            user = u
            break

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    token = user.generate_verification_token()
    db.commit()

    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,
        user.username,
        token
    )

    logger.info(f"Verification email resent to {user.email}")

    return {"message": "Verification email resent"}


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile (requires verified email)."""
    return current_user


@router.get("/me/unverified", response_model=UserResponse)
async def get_profile_unverified(current_user: User = Depends(get_current_user_unverified)):
    """Get current user profile (doesn't require verification)."""
    return current_user


@router.delete("/unverified/{email}")
async def delete_unverified_user(email: str, db: Session = Depends(get_db)):
    """Delete an unverified user (admin only or for testing)."""
    users = db.query(User).filter(User.is_verified == False).all()
    user = None

    for u in users:
        if u.email == email:
            user = u
            break

    if not user:
        raise HTTPException(status_code=404, detail="Unverified user not found")

    db.delete(user)
    db.commit()

    logger.info(f"Deleted unverified user: {email}")

    return {"message": f"Unverified user {email} deleted"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset email."""
    # Find user by email (decrypts on the fly)
    users = db.query(User).all()
    user = None
    for u in users:
        if u.email == forgot_request.email:
            user = u
            break

    # Always return same message for security (don't reveal if user exists)
    if not user:
        return {"message": "If your email is registered, you'll receive a reset link"}

    token = user.generate_reset_token()
    db.commit()

    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        user.username,
        token
    )

    logger.info(f"Password reset email queued for {user.email}")

    return {"message": "If your email is registered, you'll receive a reset link"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using token."""
    user = db.query(User).filter(User.reset_token == request.token).first()

    if not user or not user.verify_reset_token(request.token):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.set_password(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    logger.info(f"Password reset for user: {user.username}")

    return {"message": "Password reset successfully"}


@router.get("/reset-password/verify")
async def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify if reset token is valid (without resetting)."""
    user = db.query(User).filter(User.reset_token == token).first()

    if not user or not user.verify_reset_token(token):
        return {"valid": False, "message": "Invalid or expired token"}

    return {"valid": True, "message": "Token is valid"}


__all__ = ['router']