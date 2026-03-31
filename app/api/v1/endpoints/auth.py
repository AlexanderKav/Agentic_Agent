from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import os
from typing import Optional
from app.services.email import EmailService

from app.core.database import get_db
from app.api.v1.models.user import User

from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Use settings from config
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
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

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db),
    require_verified: bool = True
):
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
):
    return get_current_user(token, db, require_verified=False)

@router.post("/register", response_model=VerificationResponse)
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user and send verification email.
    User is created but marked as unverified.
    They cannot log in until they verify their email.
    """
    
    # Check if user exists AND is verified
    existing_user = db.query(User).filter(
        (User.username == user_data.username)  # Username is still plaintext for searching
    ).first()
    
    # Also check if email exists (but we need to decrypt to check)
    # This is more complex with encrypted data - we'll check username first
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Username already registered")
        else:
            # User exists but not verified - resend verification email
            token = existing_user.generate_verification_token()
            db.commit()
            
            email_service = EmailService()
            background_tasks.add_task(
                email_service.send_verification_email,
                existing_user.email,  # This auto-decrypts
                existing_user.username,
                token
            )
            
            return {
                "message": "Verification email resent. Please check your inbox.",
                "email": existing_user.email
            }
    
    # Create new user - use the property setter to encrypt
    user = User(
        username=user_data.username,
        is_verified=False
    )
    user.email = user_data.email  # This will encrypt automatically
    user.full_name = user_data.full_name  # This will encrypt automatically
    user.set_password(user_data.password)
    
    # Generate verification token
    token = user.generate_verification_token()
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification email in background
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,  # Auto-decrypts
        user.username,
        token
    )
    
    print(f"📧 Verification email queued for {user.email} with token: {token}")
    
    return {
        "message": "Registration successful! Please check your email to verify your account.",
        "email": user.email
    }

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email with token and return user data"""
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if not user.is_token_valid():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    
    if user.is_verified:
        pass
    else:
        user.verify()
        db.commit()
        print(f"✅ Email verified for user: {user.username}")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "message": "Email verified successfully",
        "email": user.email,  # Auto-decrypts
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
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Login user - requires verification"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.verify_password(form_data.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.is_verified:
        raise HTTPException(
            status_code=401, 
            detail="Please verify your email first. Check your inbox for the verification link."
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
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
    """Resend verification email"""
    # Since email is encrypted, we need to query all users and decrypt
    # This is inefficient but necessary for now. Consider adding an email hash index.
    users = db.query(User).filter(User.is_verified == False).all()
    user = None
    
    for u in users:
        if u.email == request.email:  # This will decrypt
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
    
    print(f"📧 Verification email resent to {user.email}")
    
    return {"message": "Verification email resent"}

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile (requires verified email)"""
    return current_user

@router.get("/me/unverified", response_model=UserResponse)
async def get_profile_unverified(current_user: User = Depends(get_current_user_unverified)):
    """Get current user profile (doesn't require verification)"""
    return current_user

@router.delete("/unverified/{email}")
async def delete_unverified_user(email: str, db: Session = Depends(get_db)):
    """Delete an unverified user (admin only or for testing)"""
    # Decrypt and check
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
    
    return {"message": f"Unverified user {email} deleted"}